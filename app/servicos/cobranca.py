"""
=============================================================================
 servicos/cobranca.py — Cobrança automática por WhatsApp
=============================================================================
 Decide QUEM deve receber mensagem hoje:
   • Cobranças: responsáveis com parcelas em atraso que não foram cobrados
     nos últimos N dias (configuração "cobranca_intervalo_dias", padrão 7).
   • Lembretes: parcelas que vencem nos próximos N dias
     (configuração "lembrete_dias_antes", padrão 3) — um lembrete por período.

 No modo API, se "Cobrança automática" estiver ligada, isso roda sozinho
 sempre que o sistema é aberto (e a cada 1 hora enquanto estiver aberto).
 No modo LINK, a tela "Cobranças" mostra a fila e você envia com 1 clique.
=============================================================================
"""
from __future__ import annotations

from datetime import datetime, timedelta

from app.core.log import logger
from app.repositorios import configuracoes, financeiro
from app.servicos import whatsapp


def _pode_enviar(ultima: str | None, intervalo_dias: int) -> bool:
    if not ultima:
        return True
    try:
        quando = datetime.strptime(ultima[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return True
    return datetime.now() - quando >= timedelta(days=intervalo_dias)


def fila_cobrancas() -> list[dict]:
    """Responsáveis em atraso que estão 'liberados' para nova cobrança."""
    intervalo = int(configuracoes.obter_numero("cobranca_intervalo_dias", 7))
    return [g for g in financeiro.inadimplentes() if _pode_enviar(g.get("ultima_cobranca"), intervalo)]


def fila_lembretes() -> list[dict]:
    """Responsáveis com vencimento próximo que ainda não receberam lembrete."""
    dias = int(configuracoes.obter_numero("lembrete_dias_antes", 3))
    return [g for g in financeiro.a_vencer(dias) if _pode_enviar(g.get("ultima_cobranca"), dias + 1)]


def executar_automatico(incluir_lembretes: bool = True) -> dict:
    """
    Envia pela API tudo o que estiver na fila. Só funciona no modo API com a
    opção 'cobranca_automatica' ligada. Devolve um resumo do que aconteceu.
    """
    resumo = {"enviados": 0, "erros": 0, "detalhes": []}
    if configuracoes.obter("whatsapp_modo") != "api" or configuracoes.obter("cobranca_automatica") != "1":
        return resumo
    filas = [("atraso", fila_cobrancas())]
    if incluir_lembretes:
        filas.append(("lembrete", fila_lembretes()))
    for tipo, fila in filas:
        for grupo in fila:
            ok, detalhe = whatsapp.enviar_cobranca(grupo, tipo, forcar_modo="api")
            resumo["enviados" if ok else "erros"] += 1
            resumo["detalhes"].append(f"{grupo['responsavel']}: {detalhe}")
    if resumo["enviados"] or resumo["erros"]:
        logger().info("Cobrança automática: %s enviados, %s erros", resumo["enviados"], resumo["erros"])
    return resumo
