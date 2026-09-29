"""
=============================================================================
 servicos/whatsapp.py — Envio de mensagens pelo WhatsApp
=============================================================================
 O sistema oferece DOIS modos de envio (escolha em Configurações):

 1) MODO "LINK" (padrão, gratuito, não precisa de cadastro)
    O sistema monta a mensagem pronta e abre o WhatsApp Web (ou o aplicativo
    WhatsApp Desktop) já na conversa do responsável, com o texto preenchido.
    Basta conferir e apertar ENVIAR. Funciona com o WhatsApp/WhatsApp Business
    do celular do Espaço.

 2) MODO "API" (envio 100% automático)
    Usa a API oficial do WhatsApp (WhatsApp Cloud API, da Meta). As mensagens
    saem sozinhas, sem ninguém clicar. Exige:
      • conta no Meta for Developers + WhatsApp Business Platform;
      • um número de telefone dedicado à API;
      • um "token de acesso" e o "Phone Number ID";
      • um MODELO (template) de mensagem aprovado pela Meta para cobranças
        (a Meta só permite iniciar conversa com modelos aprovados).
    A Meta cobra por mensagem de modelo enviada. Veja docs/WHATSAPP.md.

 Obs.: não usamos "robôs" que controlam o WhatsApp Web, pois violam os termos
 do WhatsApp e podem causar o BLOQUEIO do número do Espaço.
=============================================================================
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

from app.core import utils
from app.core.log import logger
from app.repositorios import configuracoes, mensagens


class _DicionarioSeguro(dict):
    """Se o modelo tiver um {campo} desconhecido, deixa o texto como está."""
    def __missing__(self, chave):
        return "{" + chave + "}"


# ---------------------------------------------------------------------------
# Montagem dos textos
# ---------------------------------------------------------------------------

def _dados_clinica(cfg: dict) -> dict:
    return {
        "clinica": cfg.get("clinica_nome", ""),
        "pix_chave": cfg.get("pix_chave", ""),
        "pix_titular": cfg.get("pix_titular", ""),
        "pix_banco": cfg.get("pix_banco", ""),
        "telefone_clinica": cfg.get("clinica_telefone", ""),
    }


def preencher_modelo(modelo: str, dados: dict) -> str:
    """Troca os {campos} do modelo pelos valores. Ex.: {responsavel} -> 'Maria'."""
    return modelo.format_map(_DicionarioSeguro(**{k: ("" if v is None else v) for k, v in dados.items()}))


def texto_parcelas(parcelas: list[dict]) -> str:
    """Lista das parcelas em aberto, uma por linha, para a mensagem."""
    linhas = []
    for p in parcelas:
        atraso = f" – {p['dias_atraso']} dia(s) em atraso" if p.get("dias_atraso") else ""
        linhas.append(f"• {p['servico']} ({p['rotulo']}) – venc. {utils.data_br(p['vencimento'])}"
                      f" – {utils.formatar_moeda(p['saldo'])}{atraso}")
    return "\n".join(linhas)


def mensagem_cobranca(grupo: dict, tipo: str = "atraso", cfg: dict | None = None) -> str:
    """
    Monta a mensagem de cobrança (tipo='atraso') ou lembrete (tipo='lembrete')
    para um grupo vindo de financeiro.inadimplentes() / financeiro.a_vencer().
    """
    cfg = cfg or configuracoes.obter_todas()
    modelo = cfg.get("msg_atraso" if tipo == "atraso" else "msg_lembrete", "")
    dados = _dados_clinica(cfg)
    dados.update({
        "responsavel": utils.primeiro_nome(grupo["responsavel"]),
        "responsavel_completo": grupo["responsavel"],
        "paciente": " e ".join(grupo["pacientes"]),
        "lista_parcelas": texto_parcelas(grupo["parcelas"]),
        "total": utils.formatar_moeda(grupo["total"]),
        "vencimento": utils.data_br(grupo.get("vencimento_mais_antigo")),
        "dias_atraso": grupo.get("maior_atraso", 0),
    })
    return preencher_modelo(modelo, dados)


def mensagem_recibo(pagamento: dict, cfg: dict | None = None) -> str:
    """Mensagem de confirmação de pagamento (enviada junto com o recibo)."""
    cfg = cfg or configuracoes.obter_todas()
    dados = _dados_clinica(cfg)
    dados.update({
        "responsavel": utils.primeiro_nome(pagamento.get("responsavel") or pagamento["paciente"]),
        "paciente": pagamento["paciente"],
        "valor": utils.formatar_moeda(pagamento["valor"]),
        "servico": pagamento["servico"],
        "parcela": pagamento.get("rotulo", ""),
        "data": utils.data_br(pagamento["data_pagamento"]),
        "forma": pagamento["forma_pagamento"],
        "recibo": f"{pagamento.get('recibo_numero') or 0:06d}",
    })
    return preencher_modelo(cfg.get("msg_recibo", ""), dados)


# ---------------------------------------------------------------------------
# Envio — modo LINK (WhatsApp Web / Desktop)
# ---------------------------------------------------------------------------

def link_whatsapp(telefone: str, texto: str, abrir_em: str = "web") -> str:
    """Monta o endereço que abre a conversa com a mensagem já escrita."""
    texto_url = urllib.parse.quote(texto, safe="")
    if abrir_em == "app":  # aplicativo WhatsApp Desktop instalado no computador
        return f"whatsapp://send?phone={telefone}&text={texto_url}"
    return f"https://api.whatsapp.com/send?phone={telefone}&text={texto_url}"


def _enviar_link(telefone: str, texto: str, cfg: dict) -> tuple[bool, str]:
    url = link_whatsapp(telefone, texto, cfg.get("whatsapp_abrir_em", "web"))
    aberto = webbrowser.open(url)
    return aberto, "WhatsApp aberto para envio manual" if aberto else "Não foi possível abrir o navegador"


# ---------------------------------------------------------------------------
# Envio — modo API (WhatsApp Cloud API oficial)
# ---------------------------------------------------------------------------

def _post_api(cfg: dict, corpo: dict) -> tuple[bool, str]:
    versao = cfg.get("api_versao") or "v21.0"
    url = f"https://graph.facebook.com/{versao}/{cfg.get('api_phone_id', '').strip()}/messages"
    requisicao = urllib.request.Request(
        url, data=json.dumps(corpo).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {cfg.get('api_token', '').strip()}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(requisicao, timeout=20) as resposta:
            retorno = json.loads(resposta.read().decode("utf-8") or "{}")
            ident = (retorno.get("messages") or [{}])[0].get("id", "")
            return True, f"Enviado pela API (id {ident})"
    except urllib.error.HTTPError as erro:
        detalhe = erro.read().decode("utf-8", "ignore")
        try:
            detalhe = json.loads(detalhe)["error"]["message"]
        except Exception:  # noqa: BLE001 — mantém o texto original do erro
            pass
        return False, f"Erro da API ({erro.code}): {detalhe}"
    except Exception as erro:  # noqa: BLE001 — sem internet, timeout etc.
        return False, f"Falha de conexão: {erro}"


def _enviar_api(telefone: str, texto: str, cfg: dict, parametros_modelo: list[str] | None) -> tuple[bool, str]:
    if not cfg.get("api_token") or not cfg.get("api_phone_id"):
        return False, "API não configurada (token ou Phone Number ID em branco)."
    modelo = (cfg.get("api_template_atraso") or "").strip()
    if modelo and parametros_modelo is not None:
        # Mensagem por MODELO aprovado (permite iniciar a conversa)
        corpo = {
            "messaging_product": "whatsapp", "to": telefone, "type": "template",
            "template": {
                "name": modelo,
                "language": {"code": cfg.get("api_template_idioma") or "pt_BR"},
                "components": [{"type": "body", "parameters": [
                    {"type": "text", "text": str(p)} for p in parametros_modelo]}],
            },
        }
    else:
        # Texto livre (só é entregue se o cliente falou com o Espaço nas últimas 24h)
        corpo = {"messaging_product": "whatsapp", "to": telefone, "type": "text",
                 "text": {"preview_url": False, "body": texto}}
    return _post_api(cfg, corpo)


# ---------------------------------------------------------------------------
# Função principal de envio
# ---------------------------------------------------------------------------

def enviar(telefone_bruto: str, texto: str, tipo: str = "manual", responsavel_id: int | None = None,
           paciente_id: int | None = None, parametros_modelo: list[str] | None = None,
           forcar_modo: str | None = None) -> tuple[bool, str]:
    """
    Envia (ou abre) a mensagem e registra no histórico.
    Devolve (sucesso, descrição).
    """
    cfg = configuracoes.obter_todas()
    telefone = utils.telefone_whatsapp(telefone_bruto, cfg.get("ddd_padrao", "81"))
    if not telefone:
        return False, f"Telefone inválido para WhatsApp: '{telefone_bruto}'"
    modo = forcar_modo or cfg.get("whatsapp_modo", "link")
    if modo == "api":
        ok, detalhe = _enviar_api(telefone, texto, cfg, parametros_modelo)
        status = "enviado" if ok else "erro"
    else:
        ok, detalhe = _enviar_link(telefone, texto, cfg)
        status = "aberto" if ok else "erro"
    mensagens.registrar(tipo, modo, telefone, texto, status, responsavel_id, paciente_id, detalhe)
    if not ok:
        logger().warning("WhatsApp: %s", detalhe)
    return ok, detalhe


def enviar_cobranca(grupo: dict, tipo: str = "atraso", forcar_modo: str | None = None) -> tuple[bool, str]:
    """Atalho: monta e envia a cobrança/lembrete de um grupo (responsável)."""
    texto = mensagem_cobranca(grupo, tipo)
    # Parâmetros do modelo aprovado na Meta: {{1}} responsável, {{2}} paciente, {{3}} total, {{4}} PIX
    parametros = [utils.primeiro_nome(grupo["responsavel"]), " e ".join(grupo["pacientes"]),
                  utils.formatar_moeda(grupo["total"]), configuracoes.obter("pix_chave")]
    return enviar(grupo["whatsapp"], texto, tipo, grupo.get("responsavel_id"),
                  (grupo.get("paciente_ids") or [None])[0], parametros, forcar_modo)


def testar_api() -> tuple[bool, str]:
    """Confere se token e Phone Number ID estão corretos (consulta o número na Meta)."""
    cfg = configuracoes.obter_todas()
    if not cfg.get("api_token") or not cfg.get("api_phone_id"):
        return False, "Preencha o token e o Phone Number ID."
    url = f"https://graph.facebook.com/{cfg.get('api_versao') or 'v21.0'}/{cfg['api_phone_id'].strip()}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {cfg['api_token'].strip()}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
            return True, f"Conectado! Número: {dados.get('display_phone_number', '?')} " \
                         f"({dados.get('verified_name', '')})"
    except urllib.error.HTTPError as erro:
        return False, f"Erro {erro.code}: {erro.read().decode('utf-8', 'ignore')[:300]}"
    except Exception as erro:  # noqa: BLE001
        return False, f"Falha de conexão: {erro}"
