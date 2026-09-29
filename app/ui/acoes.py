"""
=============================================================================
 ui/acoes.py — Ações usadas em várias telas
=============================================================================
 Registrar pagamento, gerar recibo, cobrar no WhatsApp etc. aparecem no
 Painel, no Financeiro, na Ficha do paciente e em Cobranças. Para não repetir
 código, cada ação está aqui uma única vez. Todas recebem:
   • parent        → a janela/tela que chamou (para posicionar mensagens)
   • ao_concluir   → função chamada no fim para atualizar a tela
=============================================================================
"""
from __future__ import annotations

from app.core import config, utils
from app.core.database import consultar_um
from app.core.log import logger
from app.repositorios import configuracoes, financeiro
from app.servicos import recibos, whatsapp
from app.ui import componentes as ui


def _executar(ao_concluir):
    if ao_concluir:
        try:
            ao_concluir()
        except Exception:  # noqa: BLE001
            logger().exception("Erro ao atualizar a tela")


# ---------------------------------------------------------------------------
# Pagamentos e recibos
# ---------------------------------------------------------------------------

def registrar_pagamento(parent, parcela_id: int, ao_concluir=None) -> None:
    from app.ui.dialogos.pagamento import DialogoPagamento
    p = financeiro.obter_parcela(parcela_id)
    if not p:
        return
    if p["status"] == "paga":
        ui.info("Esta parcela já está quitada.", parent=parent)
        return
    if p["status"] == "cancelada":
        ui.aviso("Esta parcela está cancelada. Reabra-a antes de receber.", parent=parent)
        return
    resultado = DialogoPagamento(parent, parcela_id).aguardar()
    if not resultado:
        return
    _executar(ao_concluir)
    if resultado.get("gerar_recibo"):
        abrir_recibo(parent, resultado["pagamento_id"])
    if resultado.get("enviar_whatsapp"):
        enviar_recibo_whatsapp(parent, resultado["pagamento_id"])
    msg = "Pagamento registrado! " + ("Parcela quitada ✔" if resultado["quitada"] else
                                     f"Saldo restante: {utils.formatar_moeda(resultado['saldo_restante'])}")
    notificar(parent, msg)


def quitar_varias(parent, parcela_ids: list[int], ao_concluir=None) -> None:
    from app.ui.dialogos.pagamento import DialogoQuitarVarias
    parcelas = [financeiro.obter_parcela(int(i)) for i in parcela_ids]
    parcelas = [p for p in parcelas if p and p["status"] == "aberta"]
    if not parcelas:
        ui.aviso("Selecione parcelas em aberto (segure Ctrl para escolher várias).", parent=parent)
        return
    resultado = DialogoQuitarVarias(parent, parcelas).aguardar()
    if not resultado:
        return
    _executar(ao_concluir)
    if resultado.get("gerar_recibo"):
        for r in resultado["resultados"]:
            recibos.gerar_recibo(r["pagamento_id"])
        recibos.abrir_arquivo(config.RECIBOS_DIR)
    notificar(parent, f"{len(resultado['resultados'])} parcela(s) quitada(s).")


def abrir_recibo(parent, pagamento_id: int) -> None:
    try:
        recibos.gerar_recibo(pagamento_id, abrir=True)
    except Exception as e:  # noqa: BLE001
        logger().exception("Erro ao gerar recibo")
        ui.erro(f"Não foi possível gerar o recibo:\n{e}", parent=parent)


def recibo_da_parcela(parent, parcela_id: int) -> None:
    """Abre o recibo do último pagamento da parcela."""
    g = consultar_um("SELECT id FROM pagamentos WHERE parcela_id=? ORDER BY id DESC LIMIT 1", (parcela_id,))
    if not g:
        ui.aviso("Esta parcela ainda não tem pagamento registrado.", parent=parent)
        return
    abrir_recibo(parent, g["id"])


def estornar_pagamento(parent, pagamento_id: int, ao_concluir=None) -> None:
    g = financeiro.obter_pagamento(pagamento_id)
    if not g:
        return
    if not ui.confirmar(f"Estornar o pagamento de {utils.formatar_moeda(g['valor'])} "
                        f"(recibo nº {g['recibo_numero'] or 0:06d}) de {g['paciente']}?\n\n"
                        "A parcela voltará a ficar em aberto.", "Estornar pagamento", parent):
        return
    financeiro.estornar_pagamento(pagamento_id)
    _executar(ao_concluir)
    notificar(parent, "Pagamento estornado.")


# ---------------------------------------------------------------------------
# Parcelas
# ---------------------------------------------------------------------------

def editar_parcela(parent, parcela_id: int, ao_concluir=None) -> None:
    from app.ui.dialogos.diversos import DialogoParcela
    if DialogoParcela(parent, parcela_id).aguardar():
        _executar(ao_concluir)


def cancelar_ou_reabrir_parcela(parent, parcela_id: int, ao_concluir=None) -> None:
    p = financeiro.obter_parcela(parcela_id)
    if not p:
        return
    cancelar = p["status"] != "cancelada"
    pergunta = (f"Cancelar a {p['rotulo']} de {p['paciente']}? Ela deixará de ser cobrada."
                if cancelar else f"Reabrir a {p['rotulo']} de {p['paciente']}?")
    if not ui.confirmar(pergunta, parent=parent):
        return
    try:
        financeiro.cancelar_parcela(parcela_id, cancelar)
    except ValueError as e:
        ui.erro(str(e), parent=parent)
        return
    _executar(ao_concluir)


# ---------------------------------------------------------------------------
# WhatsApp
# ---------------------------------------------------------------------------

def enviar_com_previa(parent, destinatario: str, telefone: str, texto: str, tipo: str,
                      responsavel_id=None, paciente_id=None, grupo: dict | None = None) -> bool:
    """Mostra a mensagem para conferência e envia. Devolve True se enviou/abriu."""
    from app.ui.dialogos.diversos import DialogoMensagem
    modo = configuracoes.obter("whatsapp_modo", "link")
    dados = DialogoMensagem(parent, destinatario, telefone, texto, modo).aguardar()
    if not dados:
        return False
    parametros = None
    if grupo:
        parametros = [utils.primeiro_nome(grupo["responsavel"]), " e ".join(grupo["pacientes"]),
                      utils.formatar_moeda(grupo["total"]), configuracoes.obter("pix_chave")]
    ok, detalhe = whatsapp.enviar(dados["telefone"], dados["texto"], tipo, responsavel_id, paciente_id,
                                  parametros)
    if ok:
        notificar(parent, "Mensagem enviada ✔" if modo == "api" else "WhatsApp aberto – confira e envie.")
    else:
        ui.erro(detalhe, "WhatsApp", parent)
    return ok


def cobrar_responsavel(parent, responsavel_id: int | None, paciente_id: int | None = None,
                       ao_concluir=None) -> None:
    """
    Monta a cobrança de TODAS as parcelas em atraso do responsável.
    Se não houver atraso, oferece um lembrete das parcelas que vão vencer.
    """
    grupos = [g for g in financeiro.inadimplentes()
              if (responsavel_id and g["responsavel_id"] == responsavel_id)
              or (not responsavel_id and paciente_id in g["paciente_ids"])]
    tipo = "atraso"
    if not grupos:
        dias = int(configuracoes.obter_numero("lembrete_dias_antes", 3))
        grupos = [g for g in financeiro.a_vencer(max(dias, 31))
                  if (responsavel_id and g["responsavel_id"] == responsavel_id)
                  or (not responsavel_id and paciente_id in g["paciente_ids"])]
        tipo = "lembrete"
        if not grupos:
            ui.info("Este responsável não tem parcelas em atraso nem a vencer nos próximos 31 dias.",
                    parent=parent)
            return
        if not ui.confirmar("Não há parcelas em atraso. Deseja enviar um LEMBRETE de vencimento?",
                            parent=parent):
            return
    g = grupos[0]
    if tipo == "lembrete":
        g["parcelas"] = g["parcelas"][:1]
        g["total"] = g["parcelas"][0]["saldo"]
    if not g["whatsapp"]:
        ui.aviso("Responsável sem WhatsApp/telefone cadastrado.", parent=parent)
        return
    texto = whatsapp.mensagem_cobranca(g, tipo)
    if enviar_com_previa(parent, g["responsavel"], g["whatsapp"], texto, tipo, g["responsavel_id"],
                         g["paciente_ids"][0], g):
        _executar(ao_concluir)


def cobrar_parcela(parent, parcela_id: int, ao_concluir=None) -> None:
    p = financeiro.obter_parcela(parcela_id)
    if p:
        cobrar_responsavel(parent, p.get("responsavel_id"), p["paciente_id"], ao_concluir)


def enviar_recibo_whatsapp(parent, pagamento_id: int) -> None:
    g = financeiro.obter_pagamento(pagamento_id)
    if not g:
        return
    telefone = g.get("responsavel_whatsapp") or g.get("responsavel_telefone")
    if not telefone:
        ui.aviso("Responsável sem WhatsApp cadastrado.", parent=parent)
        return
    enviar_com_previa(parent, g.get("responsavel") or g["paciente"], telefone,
                      whatsapp.mensagem_recibo(g), "recibo", g.get("responsavel_id"), g["paciente_id"])


def conversar(parent, nome: str, telefone: str, responsavel_id=None, paciente_id=None) -> None:
    """Abre uma conversa em branco com o responsável."""
    if not telefone:
        ui.aviso("Sem telefone/WhatsApp cadastrado.", parent=parent)
        return
    texto = f"Olá, {utils.primeiro_nome(nome)}! Aqui é do *{configuracoes.obter('clinica_nome')}*. "
    enviar_com_previa(parent, nome, telefone, texto, "manual", responsavel_id, paciente_id)


# ---------------------------------------------------------------------------
# Pacientes / contratos
# ---------------------------------------------------------------------------

def novo_contrato(parent, paciente_id: int, nome: str = "", ao_concluir=None) -> None:
    from app.ui.dialogos.contrato import DialogoContrato
    if DialogoContrato(parent, paciente_id, nome).aguardar():
        _executar(ao_concluir)
        notificar(parent, "Serviço incluído e parcelas geradas ✔")


def abrir_ficha(parent, paciente_id: int, ao_fechar=None) -> None:
    from app.ui.dialogos.ficha import FichaFinanceira
    FichaFinanceira(parent, paciente_id).aguardar()
    _executar(ao_fechar)


_janela_principal = None


def registrar_janela_principal(janela) -> None:
    """Chamado pela janela principal ao abrir, para as notificações saberem onde aparecer."""
    global _janela_principal
    _janela_principal = janela


def notificar(_parent, texto: str, tipo: str = "sucesso") -> None:
    """Mostra o aviso flutuante no canto da janela principal."""
    if _janela_principal is not None:
        try:
            _janela_principal.notificar(texto, tipo)
        except Exception:  # noqa: BLE001
            pass
