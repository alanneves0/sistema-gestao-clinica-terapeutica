# Manual do Usuário

Sistema de Gestão — Espaço Terapêutico Shay Soares

---

## 1. Entrando no sistema

Abra pelo atalho da Área de Trabalho (ou `Executar.bat`). Informe usuário e senha.
No primeiro acesso use `admin` / `admin`; o sistema pede uma nova senha.

O **menu lateral** dá acesso a todas as telas. No rodapé do menu aparece quem está conectado e o botão **Sair**.

---

## 2. Painel

Visão geral do mês (use ◀ ▶ para trocar o mês):

- **Recebido no mês** – soma dos pagamentos lançados no mês.
- **A receber (em dia)** – parcelas do mês ainda não pagas e que não venceram.
- **Em atraso (total)** – tudo que está vencido, de qualquer mês.
- **Pacientes ativos** e quantas parcelas do mês já foram pagas.
- Gráfico **Recebido × Previsto** dos últimos 6 meses.
- **Responsáveis em atraso** → selecione e clique em **✉ Cobrar**.
- **Vencem nos próximos 7 dias** → selecione e clique em **$ Receber**.

---

## 3. Cadastro de pacientes

**Menu → Novo cadastro.** São 4 abas. Campos com `*` são obrigatórios.

1. **Paciente** – nome, nascimento (a idade aparece sozinha), sexo, CPF/RG/Cartão SUS, contato
   (para adolescentes e adultos), escola/série/turno, ocupação, convênio.
2. **Responsável e endereço**
   - **O paciente é o próprio responsável:** para adultos que pagam o tratamento. O WhatsApp de cobrança passa a ser o do paciente.
   - **Usar responsável já cadastrado:** para irmãos — as cobranças dos dois chegam numa mesma mensagem.
   - O **WhatsApp do responsável** é usado nas cobranças. Digite com DDD.
   - Digite o **CEP** e aperte **Enter** para preencher o endereço (precisa de internet).
3. **Informações clínicas** – marque os diagnósticos (TEA, TDAH, TOD, dislexia…), CID, nível de suporte, laudo, medicações, alergias, médico, quem encaminhou, queixa principal e observações.
4. **Emergência e autorizações** – contato de emergência, autorização de uso de imagem, **consentimento LGPD** e se o paciente está ativo.

Botões:
- **Salvar** – grava e volta para a lista.
- **Salvar e incluir serviço** – grava e já abre a contratação do serviço (gera as parcelas e o carnê).

---

## 4. Lista de pacientes

**Menu → Pacientes.** Busque por nome do paciente ou do responsável, CPF ou telefone.
Filtre por ativos/inativos, faixa etária (criança, adolescente, adulto) e diagnóstico.
A coluna **Financeiro** mostra: *Em dia ✔*, *Pendente (em dia)*, *⚠ Em atraso* ou *Sem cobranças*.

| Botão | O que faz |
|---|---|
| ✎ Editar (ou duplo clique) | Abre o cadastro |
| $ Ficha financeira | Tudo sobre o financeiro do paciente |
| + Incluir serviço | Contrata um novo serviço |
| ✉ WhatsApp | Abre uma conversa com o responsável |
| Inativar / Reativar | Paciente que saiu (mantém o histórico) |
| ✕ Excluir | Apaga tudo — só administrador. Prefira **Inativar**. |

---

## 5. Incluir serviço (contrato)

1. Escolha o **serviço** — os valores da tabela de preços são preenchidos sozinhos.
2. **Forma de contratação:**
   - **Mensal / Parcelado** – uma parcela por mês (ou o pacote dividido, como a Avaliação).
   - **À vista** – uma única parcela com o total. Para terapias mensais, o à vista usa o valor de pontualidade × nº de meses.
3. Ajuste **nº de parcelas**, **dia de vencimento** e **1º vencimento**.
4. Se quiser, dê um **desconto especial (%)** (ex.: irmãos, bolsa).
5. Informe profissional, dias e horário (opcional).
6. Marque **Cobrar também a Taxa de Adesão** para novos pacientes.
7. Confira a **simulação** à direita e clique em **Salvar contrato**. O carnê em PDF abre para imprimir.

> **Valor cheio × valor de pontualidade:** como nos carnês (ex.: Fono R$ 220,00 / R$ 200,00):
> pago **até o vencimento** vale R$ 200,00; **depois** vale R$ 220,00 (+ multa/juros, se configurados).

---

## 6. Financeiro

### Aba “Parcelas”
- Os cartões no topo mostram o total **Pago**, **Pendente (em dia)** e **Em atraso**.
- Filtre por situação, período de vencimento ou nome. “Em atraso” mostra **todos** os atrasos, de qualquer período.
- Cores: verde = pago · âmbar = pendente em dia · vermelho = atraso · cinza = cancelado.

| Botão | O que faz |
|---|---|
| **$ Registrar pagamento** (ou duplo clique) | Lança o pagamento da parcela |
| **Quitar selecionadas** | Segure **Ctrl**, selecione várias parcelas e quite todas de uma vez |
| **Recibo** | Abre o recibo do último pagamento da parcela |
| **✎ Editar** | Muda vencimento ou valores de uma parcela |
| **Cancelar / Reabrir** | Parcela que não será cobrada (ex.: férias, falta justificada) |
| **✉ Cobrar** | Mensagem de cobrança para o responsável |
| **⤓ Excel** | Exporta a lista filtrada |

### Registrar pagamento
- A **data** define o valor: até o vencimento aparece o valor de pontualidade; depois, o valor cheio.
- Escolha a **forma de pagamento**. Para *crédito parcelado*, *cheque* e *link de pagamento* informe o **nº de vezes**.
- **Desconto concedido**, **multa/juros** e **taxa da maquininha** são opcionais.
- Opções de quitação:
  - *Quitar automaticamente* (padrão) – quita se o valor cobrir o saldo; senão fica como pagamento parcial.
  - *Considerar QUITADA (acordo)* – quita mesmo com valor menor.
  - *Pagamento parcial* – mantém a parcela em aberto com o saldo restante.
- Marque **Gerar recibo em PDF** e/ou **Enviar confirmação no WhatsApp**.

### Aba “Recebimentos (caixa)”
Tudo o que entrou no período, com resumo por forma de pagamento. Reimprima recibos, envie
confirmação por WhatsApp ou **estorne** um lançamento feito por engano (a parcela volta a ficar em aberto).

---

## 7. Ficha financeira do paciente

Abra pela lista de pacientes ou pelo Financeiro. Mostra total pago, a vencer e em atraso;
os **serviços contratados** e as **parcelas**.

- Selecione um serviço para ver só as parcelas dele (**Ver todas** volta a mostrar tudo).
- **Carnê PDF** – imprime/reimprime o carnê.
- **↻ Renovar** – adiciona mais meses com os mesmos valores.
- **Encerrar** – o serviço terminou (parcelas em aberto continuam sendo cobradas).
- **Cancelar** – cancela o serviço e as parcelas em aberto sem pagamento.
- **Excluir** – só para contratos lançados por engano (sem pagamentos).

---

## 8. Cobranças por WhatsApp

**Menu → Cobranças WhatsApp.**

- **Em atraso:** responsáveis com parcelas vencidas. Irmãos aparecem juntos numa única mensagem.
- **Lembretes de vencimento:** parcelas que vencem nos próximos dias (padrão: 3 dias).
- **Histórico:** tudo o que foi enviado, com data, canal e status.

Com a chave *“Mostrar só quem não foi cobrado recentemente”* ligada, quem já recebeu cobrança
nos últimos 7 dias (configurável) sai da lista — evita mensagens repetidas.

| Botão | Modo manual (WhatsApp Web/App) | Modo API |
|---|---|---|
| Ver mensagem e enviar | Mostra o texto (pode editar) e abre o WhatsApp — clique **Enviar** lá | Envia na hora |
| Enviar para todos da lista | Abre uma conversa por vez; você confirma para ir ao próximo | Envia todas automaticamente |

Detalhes e configuração da API: [WHATSAPP.md](WHATSAPP.md).

---

## 9. Serviços e preços

Altere valores, crie serviços (ex.: Terapia Ocupacional) ou desative os que não usa.
Mudanças valem para **novos** contratos — os antigos mantêm o valor combinado
(para ajustar uma parcela existente use **Editar** no Financeiro).

- **Mensalidade:** o valor é cobrado por mês.
- **Pacote parcelado:** o valor total é dividido (ex.: Avaliação R$ 1.600 em 4×).
- **Cobrança única:** ex.: Taxa de Adesão.

---

## 10. Relatórios

Escolha o período e veja total recebido, quantidade, valor médio, totais por forma de pagamento
e por serviço. Exporte para Excel: recebimentos, parcelas, inadimplentes e pacientes.

---

## 11. Configurações

- **Espaço e PIX** – dados que aparecem nos recibos e mensagens. Preencha a **cidade** para o recibo sair “Recife, 29 de setembro de 2026”.
- **Regras financeiras** – tolerância (dias), multa (%), juros ao mês (%), próximo nº de recibo.
- **WhatsApp** – modo de envio, navegador ou aplicativo, DDD padrão, API oficial e automação.
- **Mensagens** – personalize os textos. Palavras entre chaves (`{responsavel}`, `{paciente}`, `{total}`, `{lista_parcelas}`…) são trocadas automaticamente. No WhatsApp, `*texto*` fica em **negrito**.
- **Usuários** – crie usuários (Administrador ou Recepção), troque senhas, desative.
- **Backup** – backup automático diário, backup manual, salvar cópia num pendrive e restaurar.

---

## 12. Backup — muito importante

O sistema faz **um backup por dia** automaticamente em `dados/backups`. Mesmo assim:

- Uma vez por semana, use **Configurações → Backup → Salvar cópia em… (pendrive)**, **ou**
- copie a pasta `dados` inteira para um pendrive / Google Drive / OneDrive.

Para trocar de computador: instale o sistema no novo computador e copie a pasta `dados` para dentro dele.

---

## 13. Dúvidas frequentes

**A parcela está “Pendente (em dia)” mas o responsável já pagou.**
Registre o pagamento em Financeiro → Registrar pagamento.

**Lancei um pagamento errado.** Financeiro → Recebimentos (caixa) → selecione → **Estornar**.

**O responsável pagou 3 meses juntos.** Financeiro → segure Ctrl e selecione as 3 parcelas → **Quitar selecionadas**.

**Paciente vai pagar tudo à vista.** Ao incluir o serviço escolha **À vista (pagamento único)**.

**O paciente saiu.** Pacientes → selecione → **Inativar**.

**O WhatsApp não abre.** Verifique se há um navegador padrão e se o WhatsApp Web está conectado. Em Configurações → WhatsApp você pode escolher o **aplicativo WhatsApp Desktop**.

**Apareceu uma mensagem de erro.** Os detalhes ficam em `dados/sistema.log` — envie esse arquivo para o suporte técnico.
