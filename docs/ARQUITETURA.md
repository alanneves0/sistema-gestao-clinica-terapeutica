# Arquitetura e Guia Técnico

Documento para quem vai **manter ou modificar** o código.

---

## 1. Visão geral

O sistema é organizado em **camadas**. Cada camada só conversa com a de baixo:

```
┌──────────────────────────────────────────────────────────┐
│  INTERFACE  (app/ui)             telas, botões, tabelas   │
│    paginas/  dialogos/  componentes.py  acoes.py  tema.py │
├──────────────────────────────────────────────────────────┤
│  SERVIÇOS   (app/servicos)       WhatsApp, PDF, Excel,    │
│                                  backup, cobrança auto.   │
├──────────────────────────────────────────────────────────┤
│  REPOSITÓRIOS (app/repositorios) regras de negócio + SQL  │
│    pacientes  servicos  financeiro  configuracoes  …      │
├──────────────────────────────────────────────────────────┤
│  NÚCLEO     (app/core)           config, banco, utilitários│
└──────────────────────────────────────────────────────────┘
                         │
                 dados/espaco_shay.db  (SQLite)
```

Vantagem: as regras financeiras não dependem da tela — por isso são testadas automaticamente
(`tests/test_logica.py`) e podem ser reaproveitadas no futuro (ex.: uma versão web).

---

## 2. Estrutura de pastas

```
EspacoShaySoares/
├── main.py                     Ponto de entrada (abre o sistema)
├── requirements.txt            Bibliotecas necessárias
├── Instalar.bat / Executar.bat / Executar_Demonstracao.bat / Gerar_Executavel.bat / Rodar_Testes.bat
├── assets/                     logo.png, icone.ico
├── app/
│   ├── core/
│   │   ├── config.py           Caminhos, CORES da marca, listas (formas de pagamento, diagnósticos…)
│   │   ├── database.py         Conexão SQLite, criação das tabelas, migrações, dados iniciais
│   │   ├── utils.py            Moeda, datas, CPF, telefone, valor por extenso
│   │   ├── seguranca.py        Hash de senhas (PBKDF2-SHA256)
│   │   ├── sessao.py           Usuário logado
│   │   ├── log.py              Registro de erros (dados/sistema.log)
│   │   └── demo.py             Dados fictícios do modo demonstração
│   ├── repositorios/
│   │   ├── pacientes.py        Pacientes + responsáveis (validação, busca)
│   │   ├── servicos.py         Tabela de preços
│   │   ├── financeiro.py       Contratos, parcelas, pagamentos, situação, indicadores
│   │   ├── configuracoes.py    Chave → valor
│   │   ├── usuarios.py         Login e usuários
│   │   └── mensagens.py        Histórico do WhatsApp
│   ├── servicos/
│   │   ├── whatsapp.py         Montagem das mensagens, envio por link ou API oficial
│   │   ├── cobranca.py         Filas de cobrança/lembrete e envio automático
│   │   ├── recibos.py          PDF de recibo (2 vias) e carnê (3 por folha)
│   │   ├── relatorios.py       Planilhas Excel
│   │   └── backup.py           Backup e restauração
│   └── ui/
│       ├── tema.py             Tema de cores do CustomTkinter + estilo das tabelas
│       ├── componentes.py      Botões, cartões, campos com máscara, Tabela, DialogoBase, gráfico
│       ├── acoes.py            Ações compartilhadas (receber, recibo, cobrar…)
│       ├── janela_principal.py Login, menu lateral, navegação, tarefas de fundo
│       ├── paginas/            painel, pacientes, cadastro, financeiro, cobrancas, servicos, relatorios, configuracoes
│       └── dialogos/           pagamento, contrato, ficha (financeira), diversos
├── tests/                      Testes automáticos (unittest)
└── docs/                       Documentação
```

---

## 3. Banco de dados (SQLite)

Arquivo: `dados/espaco_shay.db`. Pode ser aberto com o programa gratuito **DB Browser for SQLite**.

```
responsaveis 1 ───< N pacientes 1 ───< N contratos 1 ───< N parcelas 1 ───< N pagamentos
                                              │
                                        servicos (tabela de preços)
mensagens (histórico WhatsApp) · configuracoes (chave/valor) · usuarios · auditoria
```

| Tabela | Principais colunas |
|---|---|
| `responsaveis` | nome, cpf, rg, parentesco, whatsapp, telefone, email, endereço completo |
| `pacientes` | responsavel_id, proprio_responsavel, nome, nascimento, documentos, escola, convênio, diagnosticos (lista separada por `;`), cid, nivel_suporte, medicações, emergência, autoriza_imagem, consentimento_lgpd, ativo |
| `servicos` | nome, categoria, tipo_cobranca (`mensal`/`parcelado`/`unico`), valor_cheio, valor_pontualidade, parcelas_padrao, valor_entrada |
| `contratos` | paciente_id, servico_id, descricao, modalidade (`parcelado`/`a_vista`), dia_vencimento, num_parcelas, valor_total, desconto_percentual, profissional, horário, status (`ativo`/`encerrado`/`cancelado`) |
| `parcelas` | contrato_id, numero, vencimento, valor (cheio), valor_pontualidade, status (`aberta`/`paga`/`cancelada`), data_quitacao |
| `pagamentos` | parcela_id, data_pagamento, valor, desconto, acrescimo, forma_pagamento, parcelas_cartao, taxa_operadora, recibo_numero, usuario |
| `mensagens` | responsavel_id, paciente_id, telefone, tipo, canal (`link`/`api`), status, detalhe |

**Datas** são gravadas como texto `AAAA-MM-DD`; **valores** em reais como número decimal.

### Migrações
A versão da estrutura fica em `PRAGMA user_version`. Para acrescentar uma coluna no futuro:

```python
# app/core/database.py
VERSAO_SCHEMA = 2
MIGRACOES = {
    1: SCHEMA_V1,
    2: "ALTER TABLE pacientes ADD COLUMN religiao TEXT;",
}
```
Na próxima abertura o sistema aplica a migração sozinho, sem perder dados.

---

## 4. Regras financeiras (`app/repositorios/financeiro.py`)

### Geração das parcelas — `simular_parcelas()`
| Tipo de serviço | Mensal/Parcelado | À vista |
|---|---|---|
| `mensal` (terapias) | N parcelas iguais (valor cheio e de pontualidade) | 1 parcela = pontualidade × N |
| `parcelado` (avaliação) | total ÷ N (com entrada opcional; centavos ajustados na última) | 1 parcela = total |
| `unico` (taxa) | 1 parcela | 1 parcela |

O **desconto especial (%)** é aplicado sobre todos os valores. Vencimentos seguem o dia escolhido
(se o mês não tem o dia 30/31, usa o último dia do mês).

### Situação — `calcular_situacao()`
```
status = cancelada                          → Cancelado
status = paga                               → Pago
hoje ≤ vencimento + tolerância              → Pendente (em dia)   valor devido = pontualidade
hoje >  vencimento + tolerância             → Em atraso           valor devido = cheio + multa + juros
saldo = valor devido − total pago − descontos
```
Juros são proporcionais aos dias: `valor × juros_mês% ÷ 30 × dias`.

### Pagamento — `registrar_pagamento()`
- Calcula o saldo **na data do pagamento** (pagamento até o vencimento usa o valor de pontualidade).
- `quitar=None` quita automaticamente se valor + desconto cobrir o saldo; `True` força; `False` mantém parcial.
- Cada pagamento recebe um **número de recibo sequencial** (`configuracoes.proximo_recibo`).
- `estornar_pagamento()` apaga o lançamento e reabre a parcela.

---

## 5. Como fazer modificações comuns

| Quero… | Onde mexer |
|---|---|
| Mudar cores | `app/core/config.py` → dicionário `CORES` |
| Nova forma de pagamento | `config.FORMAS_PAGAMENTO` (e `FORMAS_COM_PARCELAS` se aceitar nº de vezes) |
| Novo diagnóstico na lista | `config.DIAGNOSTICOS` |
| Novo campo no cadastro | 1) migração em `database.py` · 2) nome da coluna em `CAMPOS_PACIENTE` (`repositorios/pacientes.py`) · 3) `self._campo(...)` na aba certa de `ui/paginas/cadastro.py` |
| Texto das mensagens | Pela tela Configurações → Mensagens (sem mexer no código) |
| Layout do recibo | `app/servicos/recibos.py` → `_via_recibo()` / `_boleto()` |
| Nova página no menu | criar classe herdando `Pagina` em `ui/paginas/` e acrescentar em `MENU` (`janela_principal.py`) |

---

## 6. Testes

```
python -m unittest discover -s tests -t . -v
```
- `tests/test_logica.py` – utilitários, cadastro, geração de parcelas, situação, multa/juros, pagamento parcial,
  estorno, inadimplência, WhatsApp, PDFs, Excel, backup, usuários.
- `tests/test_interface.py` – usa uma “tela falsa” (`tests/stub_tk.py`) para montar **todas** as páginas e
  diálogos, preencher formulários e acionar os botões, verificando o resultado no banco.
- Os testes usam um banco **temporário** — nunca tocam em `dados/`.

---

## 7. Segurança e LGPD

- Senhas com PBKDF2-SHA256 (200 mil iterações) + sal aleatório.
- Perfis: **Administrador** (tudo) e **Recepção** (sem excluir pacientes, alterar preços, configurações, restaurar backup).
- Tabela `auditoria` registra cadastros, pagamentos, estornos, alterações de configuração etc.
- Dados de saúde ficam **somente no computador**. Recomenda-se: senha no Windows, criptografia de disco
  (BitLocker) e backups guardados em local seguro. O `.gitignore` impede que a pasta `dados/` vá para repositórios.

---

## 8. Dependências

| Biblioteca | Uso |
|---|---|
| customtkinter ≥ 5.2 | Interface moderna sobre o Tkinter (que já vem com o Python) |
| pillow | Exibir a logo |
| reportlab | Recibos e carnês em PDF |
| openpyxl | Planilhas Excel |

Tudo o mais (SQLite, envio à API do WhatsApp, busca de CEP) usa apenas a biblioteca padrão do Python.
