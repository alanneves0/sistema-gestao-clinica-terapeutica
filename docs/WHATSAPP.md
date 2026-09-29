# Envio de mensagens pelo WhatsApp

O sistema envia três tipos de mensagem:

| Tipo | Quando | Texto padrão (editável em Configurações → Mensagens) |
|---|---|---|
| **Cobrança de atraso** | Parcelas vencidas | Lista as parcelas em aberto, o total e a chave PIX |
| **Lembrete de vencimento** | Alguns dias antes do vencimento (padrão 3) | Data de vencimento e valor com pontualidade |
| **Confirmação de pagamento** | Após registrar um pagamento | Valor, serviço, parcela e forma de pagamento |

Irmãos com o mesmo responsável recebem **uma única** mensagem com todas as parcelas.
Tudo fica registrado em **Cobranças → Histórico de mensagens**.

Existem **dois modos** de envio (Configurações → WhatsApp).

---

## Modo 1 — WhatsApp Web / App (manual) · *padrão, gratuito*

O sistema monta a mensagem e abre o WhatsApp **já na conversa do responsável, com o texto escrito**.
Você confere e clica em **Enviar**.

**Como preparar (uma vez só):**
1. No computador do Espaço, abra <https://web.whatsapp.com> e conecte o WhatsApp (Business) do Espaço
   lendo o QR Code com o celular — **ou** instale o aplicativo **WhatsApp para Windows**.
2. Em Configurações → WhatsApp, escolha **Navegador (WhatsApp Web)** ou **Aplicativo WhatsApp Desktop**.
3. Confira o **DDD padrão** (81) — usado quando um telefone foi cadastrado sem DDD.

**Enviar para vários:** em Cobranças, **Enviar para todos da lista** abre uma conversa por vez; depois de
enviar, volte ao sistema e confirme para abrir a próxima.

✅ Sem custo, sem cadastro, usa o número que os responsáveis já conhecem.
⚠️ Precisa de um clique em “Enviar” para cada mensagem.

> **Por que não automatizamos o WhatsApp Web com um “robô”?** Programas que clicam sozinhos no
> WhatsApp Web violam os termos de uso do WhatsApp e podem levar ao **bloqueio do número** do Espaço.
> Por segurança, o sistema só usa o modo manual ou a API oficial.

---

## Modo 2 — API oficial do WhatsApp (automático)

Usa a **WhatsApp Cloud API**, da Meta. As mensagens saem sozinhas, inclusive a **cobrança automática**:
ao abrir o sistema (e a cada 1 hora com ele aberto), quem estiver em atraso e não tiver sido cobrado nos
últimos N dias recebe a mensagem; lembretes de vencimento também são enviados.

### O que é necessário
- Conta no **Meta Business** (business.facebook.com) e um app em **developers.facebook.com** com o produto WhatsApp.
- Um **número de telefone** registrado na API (normalmente um número dedicado; a Meta tem oferecido um modo
  de “coexistência” com o app WhatsApp Business — verifique a disponibilidade para o seu número).
- **Verificação da empresa** na Meta para enviar em volume.
- Um **modelo de mensagem (template)** aprovado — a Meta só permite **iniciar** conversas com modelos aprovados.
- **Custo:** a Meta cobra por mensagem de modelo enviada (a categoria “Utilidade”, usada para lembretes de
  pagamento, é a mais barata). Consulte os preços atuais em developers.facebook.com.

### Passo a passo
1. Em developers.facebook.com → *Meus apps* → *Criar app* → tipo **Empresa** → adicione o produto **WhatsApp**.
2. Em *WhatsApp → Configuração da API*, adicione e verifique o número do Espaço.
   Anote o **Phone Number ID** (identificação do número de telefone).
3. Gere um **token permanente**: Configurações do Negócio → *Usuários do sistema* → crie um usuário do sistema
   administrador → *Gerar token* com as permissões `whatsapp_business_messaging` e `whatsapp_business_management`.
4. Em *WhatsApp → Modelos de mensagem*, crie um modelo, categoria **Utilidade**, idioma **Português (BR)**,
   por exemplo com o nome `cobranca_atraso`:

   ```
   Olá, {{1}}! Aqui é do Espaço Terapêutico Shay Soares.
   Identificamos pagamento em aberto referente ao atendimento de {{2}}, no total de {{3}}.
   Você pode pagar via PIX: {{4}}.
   Se já pagou, por favor desconsidere e nos envie o comprovante. Obrigada!
   ```
   O sistema preenche: **{{1}}** nome do responsável · **{{2}}** paciente(s) · **{{3}}** total em aberto · **{{4}}** chave PIX.
5. No sistema, em **Configurações → WhatsApp**:
   - Modo: **API oficial (automático)**
   - Token de acesso, Phone Number ID, nome do modelo (`cobranca_atraso`), idioma (`pt_BR`)
   - Clique em **Testar conexão com a API**
   - Ligue **Enviar cobranças e lembretes automaticamente**, se desejar
   - Ajuste **Repetir cobrança a cada (dias)** e **Lembrete quantos dias antes**
6. Clique em **Salvar configurações**.

> Sem o nome do modelo preenchido, o sistema envia o texto livre das Mensagens — mas a Meta só entrega
> texto livre para quem conversou com o Espaço nas **últimas 24 horas**.

### Problemas comuns
| Mensagem de erro | Causa provável |
|---|---|
| `API não configurada` | Token ou Phone Number ID em branco |
| `Erro da API (401)` | Token inválido ou expirado — gere um token permanente |
| `Erro da API (400) … template` | Nome/idioma do modelo errado ou modelo ainda não aprovado |
| `Erro da API (400) … 24 hours` | Enviando texto livre fora da janela de 24 h — use um modelo |
| `Falha de conexão` | Sem internet no momento |

Os erros aparecem em **Cobranças → Histórico** (coluna Detalhe) e em `dados/sistema.log`.

---

## Telefones

Cadastre o WhatsApp com DDD, em qualquer formato: `(81) 99999-8888`, `81999998888`, `81 9 9999-8888`.
O sistema converte para o formato internacional (`5581999998888`).
