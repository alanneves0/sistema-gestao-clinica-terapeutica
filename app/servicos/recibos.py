"""
=============================================================================
 servicos/recibos.py — Geração de RECIBOS e CARNÊS em PDF
=============================================================================
 • gerar_recibo(pagamento_id)  → recibo de um pagamento, em 2 vias
                                  (via do cliente e via do Espaço) numa folha A4.
 • gerar_carne(contrato_id)    → carnê com todas as parcelas de um contrato,
                                  3 por folha, no mesmo estilo dos carnês que o
                                  Espaço já usa (canhoto + recibo), porém já
                                  preenchido com nome, serviço, valor e vencimento.
 Os arquivos são salvos em dados/recibos/.
 Usa a biblioteca ReportLab.
=============================================================================
"""
from __future__ import annotations

import os
import subprocess
import sys
import unicodedata
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, Paragraph

from app.core import config, utils
from app.core.database import consultar, consultar_um
from app.repositorios import configuracoes, financeiro

C = {k: HexColor(v) for k, v in config.CORES.items()}
LARGURA, ALTURA = A4
MARGEM = 28
FAIXA_CARNE = (ALTURA - 40) / 3   # altura de cada parcela do carnê (3 por folha)


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------

def abrir_arquivo(caminho: Path | str) -> None:
    """Abre o PDF no programa padrão do computador (Windows, Mac ou Linux)."""
    caminho = str(caminho)
    try:
        if sys.platform.startswith("win"):
            os.startfile(caminho)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", caminho])
        else:
            subprocess.Popen(["xdg-open", caminho])
    except Exception:  # noqa: BLE001 — se não abrir, o arquivo continua salvo
        pass


def _nome_arquivo(texto: str) -> str:
    normal = unicodedata.normalize("NFKD", texto or "")
    base = "".join(ch for ch in normal if not unicodedata.combining(ch)).replace(" ", "_")
    return "".join(c for c in base if c.isalnum() or c in "_-")[:60]


def _logo(c: canvas.Canvas, x: float, y: float, tamanho: float) -> None:
    if config.LOGO_PATH.exists():
        c.drawImage(str(config.LOGO_PATH), x, y, tamanho, tamanho, mask="auto",
                    preserveAspectRatio=True)


def _paragrafo(c, texto, x, y, largura, altura, tamanho=10.5, entrelinha=15):
    estilo = ParagraphStyle("corpo", fontName="Helvetica", fontSize=tamanho, leading=entrelinha,
                            textColor=C["texto"], alignment=TA_JUSTIFY)
    frame = Frame(x, y, largura, altura, leftPadding=0, rightPadding=0, topPadding=0,
                  bottomPadding=0, showBoundary=0)
    frame.addFromList([Paragraph(texto, estilo)], c)


def _linha_campo(c, x, y, largura, rotulo, valor="", tamanho=8.5):
    """Desenha 'Rótulo: valor' sobre uma linha (estilo formulário)."""
    c.setFont("Helvetica", tamanho - 0.5)
    c.setFillColor(C["texto_suave"])
    c.drawString(x, y + 2, rotulo)
    lr = c.stringWidth(rotulo, "Helvetica", tamanho - 0.5) + 4
    c.setStrokeColor(C["destaque"])
    c.setLineWidth(0.6)
    c.line(x + lr, y, x + largura, y)
    if valor:
        c.setFont("Helvetica-Bold", tamanho)
        c.setFillColor(C["texto"])
        texto = str(valor)
        while c.stringWidth(texto, "Helvetica-Bold", tamanho) > largura - lr - 2 and len(texto) > 4:
            texto = texto[:-2]
        c.drawString(x + lr + 2, y + 2, texto)


# ---------------------------------------------------------------------------
# RECIBO de pagamento (2 vias)
# ---------------------------------------------------------------------------

def _via_recibo(c: canvas.Canvas, topo: float, g: dict, cfg: dict, rotulo_via: str) -> None:
    altura = ALTURA / 2 - 2 * MARGEM + 10
    x0, y0, w = MARGEM, topo - altura, LARGURA - 2 * MARGEM

    # Cartão com borda verde-água
    c.setFillColor(C["superficie"])
    c.setStrokeColor(C["primaria"])
    c.setLineWidth(1.2)
    c.roundRect(x0, y0, w, altura, 14, stroke=1, fill=1)
    # Faixa superior
    c.setFillColor(C["primaria_suave"])
    c.roundRect(x0 + 1, topo - 92, w - 2, 91, 13, stroke=0, fill=1)

    _logo(c, x0 + 14, topo - 86, 78)

    # Título
    c.setFillColor(C["primaria_profunda"])
    c.setFont("Helvetica-Bold", 24)
    c.drawString(x0 + 104, topo - 42, "RECIBO")
    c.setFont("Helvetica", 9.5)
    c.setFillColor(C["texto_suave"])
    c.drawString(x0 + 104, topo - 58, cfg.get("clinica_nome", ""))
    linha3 = " · ".join(x for x in (cfg.get("clinica_documento"), cfg.get("clinica_telefone")) if x)
    if linha3:
        c.drawString(x0 + 104, topo - 71, linha3)

    # Caixa com número e valor
    bx, bw = x0 + w - 190, 176
    c.setFillColor(C["destaque_claro"])
    c.roundRect(bx, topo - 82, bw, 68, 10, stroke=0, fill=1)
    c.setFillColor(C["destaque_escuro"])
    c.setFont("Helvetica-Bold", 9)
    c.drawString(bx + 12, topo - 30, f"Nº {g.get('recibo_numero') or 0:06d}")
    c.drawRightString(bx + bw - 12, topo - 30, rotulo_via.upper())
    c.setFillColor(C["primaria_profunda"])
    c.setFont("Helvetica-Bold", 22)
    c.drawString(bx + 12, topo - 64, utils.formatar_moeda(g["valor"]))

    # Corpo do recibo
    cpf = f", CPF {g['responsavel_cpf']}" if g.get("responsavel_cpf") else ""
    vezes = f" em {g['parcelas_cartao']}x" if (g.get("parcelas_cartao") or 1) > 1 else ""
    texto = (f"Recebi de <b>{g.get('responsavel') or g['paciente']}</b>{cpf}, a importância de "
             f"<b>{utils.formatar_moeda(g['valor'])}</b> ({utils.valor_por_extenso(g['valor'])}), "
             f"referente a <b>{g['servico']}</b> – {g['rotulo']} (vencimento "
             f"{utils.data_br(g['vencimento'])}), prestado ao(à) paciente <b>{g['paciente']}</b>. "
             f"Pagamento realizado em <b>{utils.data_br(g['data_pagamento'])}</b> via "
             f"<b>{g['forma_pagamento']}{vezes}</b>.")
    if g.get("desconto"):
        texto += f" Desconto concedido: {utils.formatar_moeda(g['desconto'])}."
    if g.get("acrescimo"):
        texto += f" Inclui multa/juros de {utils.formatar_moeda(g['acrescimo'])}."
    texto += " Para clareza, firmo o presente recibo."
    _paragrafo(c, texto, x0 + 22, topo - 168, w - 44, 64)

    # Quadro-resumo (paciente, serviço, parcela, forma de pagamento)
    itens = [("Paciente", g["paciente"]), ("Serviço", g["servico"]), ("Parcela", g["rotulo"]),
             ("Forma de pagamento", g["forma_pagamento"] + vezes)]
    larg = (w - 44 - 3 * 8) / 4
    for i, (rot, val) in enumerate(itens):
        bx_i = x0 + 22 + i * (larg + 8)
        c.setFillColor(C["primaria_suave"])
        c.roundRect(bx_i, topo - 212, larg, 34, 7, stroke=0, fill=1)
        c.setFillColor(C["texto_suave"])
        c.setFont("Helvetica", 7)
        c.drawString(bx_i + 8, topo - 190, rot.upper())
        c.setFillColor(C["texto"])
        c.setFont("Helvetica-Bold", 8.5)
        val = str(val)
        while c.stringWidth(val, "Helvetica-Bold", 8.5) > larg - 14 and len(val) > 4:
            val = val[:-2]
        c.drawString(bx_i + 8, topo - 204, val)

    # Local e data
    cidade = cfg.get("clinica_cidade", "").strip()
    local_data = f"{cidade + ', ' if cidade else ''}{utils.data_extenso(g['data_pagamento'])}."
    c.setFont("Helvetica", 10)
    c.setFillColor(C["texto"])
    c.drawRightString(x0 + w - 22, topo - 234, local_data)

    # Assinatura
    ax = x0 + w / 2
    c.setStrokeColor(C["texto_suave"])
    c.setLineWidth(0.7)
    c.line(ax - 130, topo - 272, ax + 130, topo - 272)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(ax, topo - 285, cfg.get("assinatura_nome", ""))
    c.setFont("Helvetica", 8.5)
    c.setFillColor(C["texto_suave"])
    c.drawCentredString(ax, topo - 297, cfg.get("assinatura_registro", ""))

    # Rodapé com PIX
    c.setFillColor(C["primaria_suave"])
    c.roundRect(x0 + 12, y0 + 10, w - 24, 26, 8, stroke=0, fill=1)
    c.setFillColor(C["primaria_profunda"])
    c.setFont("Helvetica", 8.5)
    rodape = f"PIX: {cfg.get('pix_chave', '')}   ·   {cfg.get('pix_titular', '')}   ·   {cfg.get('pix_banco', '')}"
    if cfg.get("clinica_endereco"):
        rodape += f"   ·   {cfg['clinica_endereco']}"
    c.drawCentredString(x0 + w / 2, y0 + 19, rodape[:150])


def gerar_recibo(pagamento_id: int, abrir: bool = False) -> Path:
    """Gera o PDF do recibo de um pagamento e devolve o caminho do arquivo."""
    g = financeiro.obter_pagamento(pagamento_id)
    if not g:
        raise ValueError("Pagamento não encontrado.")
    cfg = configuracoes.obter_todas()
    config.garantir_pastas()
    caminho = config.RECIBOS_DIR / f"Recibo_{g['recibo_numero'] or 0:06d}_{_nome_arquivo(g['paciente'])}.pdf"

    c = canvas.Canvas(str(caminho), pagesize=A4)
    c.setTitle(f"Recibo {g['recibo_numero'] or 0:06d} – {g['paciente']}")
    c.setAuthor(cfg.get("clinica_nome", ""))
    _via_recibo(c, ALTURA - MARGEM, g, cfg, "Via do cliente")
    # linha de corte
    c.setDash(4, 4)
    c.setStrokeColor(C["destaque"])
    c.line(MARGEM, ALTURA / 2, LARGURA - MARGEM, ALTURA / 2)
    c.setDash()
    _via_recibo(c, ALTURA / 2 - MARGEM + 10, g, cfg, "Via do Espaço")
    c.showPage()
    c.save()
    if abrir:
        abrir_arquivo(caminho)
    return caminho


# ---------------------------------------------------------------------------
# CARNÊ de parcelas (3 por página)
# ---------------------------------------------------------------------------

def _boleto(c: canvas.Canvas, topo: float, p: dict, contrato: dict, cfg: dict) -> None:
    altura = FAIXA_CARNE - 14
    y0 = topo - altura
    canhoto_w = 200
    x_c, x_r = MARGEM - 8, MARGEM - 8 + canhoto_w + 14
    w_r = LARGURA - x_r - MARGEM + 8

    # ---------- CANHOTO (fica com o Espaço) ----------
    c.setFillColor(C["primaria_suave"])
    c.roundRect(x_c, y0 + 38, canhoto_w, altura - 50, 12, stroke=0, fill=1)
    c.setFillColor(C["primaria"])
    c.roundRect(x_c + 10, topo - 34, 110, 24, 8, stroke=0, fill=1)
    c.setFillColor(C["texto_claro"])
    c.setFont("Helvetica-Bold", 12)
    rot = "Parcela única" if p["total_parcelas"] == 1 else f"Parcela {p['numero']:02d}/{p['total_parcelas']:02d}"
    c.drawString(x_c + 18, topo - 26, rot)

    yy = topo - 58
    valor_txt = utils.formatar_moeda(p["valor"])
    if abs(p["valor"] - p["valor_pontualidade"]) > 0.009:
        valor_txt = f"{utils.formatar_moeda(p['valor'])} / {utils.formatar_moeda(p['valor_pontualidade'])}"
    for rotulo, valor in (("Valor:", valor_txt), ("Cliente:", contrato["responsavel"]),
                          ("Paciente:", contrato["paciente"]), ("Serviço:", contrato["descricao"]),
                          ("Venc.:", utils.data_br(p["vencimento"])), ("Pago em:", "")):
        _linha_campo(c, x_c + 10, yy, canhoto_w - 20, rotulo, valor, 8.5)
        yy -= 21
    if abs(p["valor"] - p["valor_pontualidade"]) > 0.009:
        c.setFont("Helvetica-Oblique", 7)
        c.setFillColor(C["destaque_escuro"])
        c.drawString(x_c + 10, yy + 8, f"Até o vencimento: {utils.formatar_moeda(p['valor_pontualidade'])}")

    # ---------- RECIBO (fica com o cliente) ----------
    c.setFillColor(C["destaque_claro"])
    c.roundRect(x_r, y0 + 38, w_r, altura - 80, 12, stroke=0, fill=1)
    c.setFillColor(C["destaque_escuro"])
    c.roundRect(x_r, topo - 34, 96, 26, 8, stroke=0, fill=1)
    c.setFillColor(C["texto_claro"])
    c.setFont("Helvetica-BoldOblique", 14)
    c.drawString(x_r + 16, topo - 26, "Recibo")
    c.setFillColor(C["texto_suave"])
    c.setFont("Helvetica", 8)
    c.drawString(x_r + w_r - 190, topo - 25, "Nº ________")
    c.drawString(x_r + w_r - 110, topo - 25, "Valor R$ ____________")

    yy = topo - 64
    lw = w_r - 24
    _linha_campo(c, x_r + 12, yy, lw, "Recebi de:", contrato["responsavel"], 9)
    yy -= 22
    _linha_campo(c, x_r + 12, yy, lw, "a importância de:", "", 9)
    yy -= 22
    _linha_campo(c, x_r + 12, yy, lw, "referente a:",
                 f"{contrato['descricao']} – {rot} (venc. {utils.data_br(p['vencimento'])})", 9)
    yy -= 22
    _linha_campo(c, x_r + 12, yy, lw, "ao paciente:", contrato["paciente"], 9)
    yy -= 30
    cidade = cfg.get("clinica_cidade", "") or "______________"
    c.setFont("Helvetica", 9)
    c.setFillColor(C["texto"])
    c.drawString(x_r + 12, yy, f"{cidade}, ____ de _______________ de ______")
    c.setStrokeColor(C["texto_suave"])
    c.line(x_r + w_r - 200, yy - 28, x_r + w_r - 14, yy - 28)
    c.setFont("Helvetica", 7)
    c.drawCentredString(x_r + w_r - 107, yy - 37, cfg.get("assinatura_nome", "") or "Assinatura")

    # ---------- Rodapé PIX (nas duas partes) ----------
    for x in (x_c + 10, x_r + 12):
        c.setFillColor(C["primaria_profunda"])
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(x, y0 + 26, f"PIX: {cfg.get('pix_chave', '')}")
        c.setFont("Helvetica", 7.5)
        c.drawString(x, y0 + 16, cfg.get("pix_titular", ""))
        c.drawString(x, y0 + 6, cfg.get("pix_banco", ""))
    _logo(c, x_c + canhoto_w - 44, y0 + 2, 38)
    _logo(c, x_r + w_r - 44, y0 + 2, 38)

    # linha pontilhada entre canhoto e recibo e de corte inferior
    c.setDash(3, 3)
    c.setStrokeColor(C["destaque"])
    c.line(x_c + canhoto_w + 7, y0, x_c + canhoto_w + 7, topo)
    c.line(MARGEM - 8, y0 - 6, LARGURA - MARGEM + 8, y0 - 6)
    c.setDash()


def gerar_carne(contrato_id: int, somente_abertas: bool = False, abrir: bool = False) -> Path:
    """Gera o carnê (PDF) com as parcelas do contrato."""
    contrato = consultar_um("""
        SELECT c.*, p.nome AS paciente, COALESCE(r.nome, p.nome) AS responsavel
          FROM contratos c JOIN pacientes p ON p.id = c.paciente_id
          LEFT JOIN responsaveis r ON r.id = p.responsavel_id WHERE c.id = ?""", (contrato_id,))
    if not contrato:
        raise ValueError("Contrato não encontrado.")
    parcelas = consultar("SELECT * FROM parcelas WHERE contrato_id=? AND status<>'cancelada' "
                         "ORDER BY numero", (contrato_id,))
    total = consultar_um("SELECT COUNT(*) n FROM parcelas WHERE contrato_id=?", (contrato_id,))["n"]
    if somente_abertas:
        parcelas = [p for p in parcelas if p["status"] == "aberta"]
    if not parcelas:
        raise ValueError("Não há parcelas para imprimir.")
    cfg = configuracoes.obter_todas()
    config.garantir_pastas()
    caminho = config.RECIBOS_DIR / f"Carne_{_nome_arquivo(contrato['paciente'])}_{_nome_arquivo(contrato['descricao'])}_{contrato_id}.pdf"

    c = canvas.Canvas(str(caminho), pagesize=A4)
    c.setTitle(f"Carnê – {contrato['paciente']} – {contrato['descricao']}")
    for i, p in enumerate(parcelas):
        p["total_parcelas"] = total
        posicao = i % 3
        if i and posicao == 0:
            c.showPage()
        topo = ALTURA - 20 - posicao * FAIXA_CARNE
        _boleto(c, topo, p, contrato, cfg)
    c.showPage()
    c.save()
    if abrir:
        abrir_arquivo(caminho)
    return caminho
