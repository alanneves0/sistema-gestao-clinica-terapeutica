"""
=============================================================================
 servicos/relatorios.py — Exportação de relatórios para Excel
=============================================================================
 Gera planilhas .xlsx (abrem no Excel, LibreOffice ou Google Planilhas):
   • exportar_parcelas()   → situação financeira (pagos, pendentes, atrasados)
   • exportar_pagamentos() → livro-caixa (tudo que foi recebido no período)
   • exportar_pacientes()  → lista de pacientes e responsáveis
   • exportar_inadimplentes()
 Os arquivos ficam em dados/relatorios/.
=============================================================================
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.core import config, utils
from app.repositorios import financeiro, pacientes

_COR_CAB = config.CORES["primaria"].lstrip("#")
_COR_LINHA = config.CORES["primaria_suave"].lstrip("#")
_FMT_MOEDA = 'R$ #,##0.00;[Red]-R$ #,##0.00'
_FILL_SIT = {
    config.SITUACAO_PAGO: config.CORES["pago_claro"],
    config.SITUACAO_EM_DIA: config.CORES["em_dia_claro"],
    config.SITUACAO_ATRASO: config.CORES["atraso_claro"],
    config.SITUACAO_CANCELADO: config.CORES["cancelado_claro"],
}


def _planilha(titulo: str, subtitulo: str, colunas: list[tuple[str, int, str]],
              linhas: list[list], coluna_situacao: int | None = None,
              totais: dict[int, float] | None = None) -> Workbook:
    """
    Monta uma planilha formatada.
      colunas: (título, largura, tipo) — tipo: 'texto' | 'moeda' | 'data' | 'numero'
    """
    wb = Workbook()
    ws = wb.active
    ws.title = titulo[:30]
    borda = Border(bottom=Side(style="thin", color="DDDDDD"))

    ws.cell(1, 1, config.APP_NOME).font = Font(bold=True, size=14, color=config.CORES["primaria_profunda"].lstrip("#"))
    ws.cell(2, 1, subtitulo).font = Font(italic=True, color="777777")
    ws.cell(3, 1, f"Gerado em {datetime.now():%d/%m/%Y %H:%M}").font = Font(size=9, color="999999")

    cab = 5
    for i, (nome, largura, _tipo) in enumerate(colunas, start=1):
        cel = ws.cell(cab, i, nome)
        cel.font = Font(bold=True, color="FFFFFF")
        cel.fill = PatternFill("solid", fgColor=_COR_CAB)
        cel.alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = largura
    ws.row_dimensions[cab].height = 22

    for r, linha in enumerate(linhas, start=cab + 1):
        for i, valor in enumerate(linha, start=1):
            tipo = colunas[i - 1][2]
            if tipo == "data":
                valor = utils.para_date(valor)
            cel = ws.cell(r, i, valor)
            cel.border = borda
            if tipo == "moeda":
                cel.number_format = _FMT_MOEDA
            elif tipo == "data":
                cel.number_format = "DD/MM/YYYY"
                cel.alignment = Alignment(horizontal="center")
            if (r - cab) % 2 == 0:
                cel.fill = PatternFill("solid", fgColor=_COR_LINHA)
        if coluna_situacao is not None:
            sit = linha[coluna_situacao]
            if sit in _FILL_SIT:
                ws.cell(r, coluna_situacao + 1).fill = PatternFill("solid", fgColor=_FILL_SIT[sit].lstrip("#"))

    if totais and linhas:
        r = cab + len(linhas) + 1
        ws.cell(r, 1, "TOTAL").font = Font(bold=True)
        for col, valor in totais.items():
            cel = ws.cell(r, col + 1, valor)
            cel.font = Font(bold=True)
            cel.number_format = _FMT_MOEDA
    ws.freeze_panes = ws.cell(cab + 1, 1)
    ws.auto_filter.ref = f"A{cab}:{get_column_letter(len(colunas))}{cab + max(len(linhas), 1)}"
    return wb


def _salvar(wb: Workbook, nome: str) -> Path:
    config.garantir_pastas()
    caminho = config.RELATORIOS_DIR / f"{nome}_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    wb.save(caminho)
    return caminho


def exportar_parcelas(parcelas: list[dict], descricao: str = "") -> Path:
    colunas = [("Paciente", 28, "texto"), ("Responsável", 28, "texto"), ("WhatsApp", 17, "texto"),
               ("Serviço", 30, "texto"), ("Parcela", 14, "texto"), ("Vencimento", 13, "data"),
               ("Valor cheio", 13, "moeda"), ("Valor pontualidade", 13, "moeda"),
               ("Pago", 13, "moeda"), ("Saldo", 13, "moeda"), ("Situação", 18, "texto"),
               ("Dias em atraso", 10, "numero"), ("Forma pgto.", 22, "texto")]
    linhas = [[p["paciente"], p.get("responsavel") or "", p.get("responsavel_whatsapp") or "",
               p["servico"], p["rotulo"], p["vencimento"], p["valor"], p["valor_pontualidade"],
               p.get("total_pago") or 0, p["saldo"], p["situacao"], p.get("dias_atraso") or 0,
               p.get("forma_pagamento") or ""] for p in parcelas]
    totais = {8: sum(l[8] for l in linhas), 9: sum(l[9] for l in linhas)}
    wb = _planilha("Parcelas", descricao or "Situação financeira", colunas, linhas, 10, totais)
    return _salvar(wb, "Financeiro_Parcelas")


def exportar_pagamentos(data_ini: date, data_fim: date) -> Path:
    pagamentos = financeiro.listar_pagamentos(data_ini, data_fim)
    colunas = [("Data", 12, "data"), ("Recibo", 9, "numero"), ("Paciente", 28, "texto"),
               ("Responsável", 28, "texto"), ("Serviço", 30, "texto"), ("Parcela", 14, "texto"),
               ("Forma de pagamento", 26, "texto"), ("Vezes", 7, "numero"),
               ("Valor recebido", 14, "moeda"), ("Desconto", 12, "moeda"),
               ("Multa/juros", 12, "moeda"), ("Taxa operadora", 12, "moeda"), ("Usuário", 16, "texto")]
    linhas = [[g["data_pagamento"], g["recibo_numero"], g["paciente"], g.get("responsavel") or "",
               g["servico"], g["rotulo"], g["forma_pagamento"], g["parcelas_cartao"], g["valor"],
               g["desconto"], g["acrescimo"], g["taxa_operadora"], g.get("usuario") or ""]
              for g in pagamentos]
    totais = {8: sum(l[8] for l in linhas), 9: sum(l[9] for l in linhas),
              10: sum(l[10] for l in linhas), 11: sum(l[11] for l in linhas)}
    wb = _planilha("Recebimentos", f"Recebimentos de {utils.data_br(data_ini)} a {utils.data_br(data_fim)}",
                   colunas, linhas, None, totais)

    # Aba extra: resumo por forma de pagamento
    ws = wb.create_sheet("Por forma de pagamento")
    ws.append(["Forma de pagamento", "Quantidade", "Total"])
    for f in financeiro.por_forma_pagamento(data_ini, data_fim):
        ws.append([f["forma"], f["qtd"], f["total"]])
        ws.cell(ws.max_row, 3).number_format = _FMT_MOEDA
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["C"].width = 16
    for cel in ws[1]:
        cel.font = Font(bold=True, color="FFFFFF")
        cel.fill = PatternFill("solid", fgColor=_COR_CAB)
    return _salvar(wb, "Financeiro_Recebimentos")


def exportar_pacientes(somente_ativos: bool | None = True) -> Path:
    lista = pacientes.listar(somente_ativos=somente_ativos)
    colunas = [("Paciente", 30, "texto"), ("Nascimento", 12, "data"), ("Idade", 7, "numero"),
               ("Diagnósticos", 30, "texto"), ("CID", 10, "texto"), ("Convênio", 16, "texto"),
               ("Escola", 22, "texto"), ("Responsável", 28, "texto"), ("Parentesco", 14, "texto"),
               ("WhatsApp", 17, "texto"), ("CPF responsável", 16, "texto"), ("Cadastro", 12, "data"),
               ("Situação", 10, "texto")]
    linhas = [[p["nome"], p.get("data_nascimento"), p.get("idade"), p.get("diagnosticos") or "",
               p.get("cid") or "", p.get("convenio") or "", p.get("escola") or "",
               p.get("responsavel_nome") or "", p.get("responsavel_parentesco") or "",
               p.get("responsavel_whatsapp") or p.get("responsavel_telefone") or "",
               p.get("responsavel_cpf") or "", p.get("data_cadastro"),
               "Ativo" if p["ativo"] else "Inativo"] for p in lista]
    return _salvar(_planilha("Pacientes", "Cadastro de pacientes", colunas, linhas), "Pacientes")


def exportar_inadimplentes() -> Path:
    grupos = financeiro.inadimplentes()
    colunas = [("Responsável", 30, "texto"), ("WhatsApp", 17, "texto"), ("Paciente(s)", 34, "texto"),
               ("Parcelas em atraso", 12, "numero"), ("Maior atraso (dias)", 12, "numero"),
               ("Total em aberto", 15, "moeda"), ("Última cobrança", 18, "texto")]
    linhas = [[g["responsavel"], g["whatsapp"], ", ".join(g["pacientes"]), len(g["parcelas"]),
               g["maior_atraso"], g["total"], g.get("ultima_cobranca") or "nunca"] for g in grupos]
    wb = _planilha("Inadimplentes", "Responsáveis com pagamentos em atraso", colunas, linhas,
                   None, {5: sum(l[5] for l in linhas)})
    return _salvar(wb, "Inadimplentes")
