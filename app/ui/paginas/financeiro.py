"""
=============================================================================
 ui/paginas/financeiro.py — Controle financeiro
=============================================================================
 Aba "Parcelas":
   Filtre por situação (Pago / Pendente em dia / Em atraso / Cancelado),
   por período de vencimento e por nome. Daqui você:
     • registra pagamentos (PIX, cartão, dinheiro, parcelado…)
     • quita várias parcelas de uma vez
     • gera recibo, edita/cancela parcela e cobra no WhatsApp
     • exporta para Excel
 Aba "Recebimentos (caixa)":
   Tudo que entrou no período, com totais por forma de pagamento,
   reimpressão de recibo e estorno.
=============================================================================
"""
from __future__ import annotations

from datetime import date, timedelta

import customtkinter as ctk

from app.core import config, utils
from app.repositorios import financeiro
from app.servicos import recibos, relatorios
from app.ui import acoes
from app.ui import componentes as ui
from app.ui.paginas.base import Pagina
from app.ui.tema import fonte

COR = config.CORES

PERIODOS = ["Mês atual", "Mês anterior", "Próximo mês", "Próximos 30 dias", "Últimos 90 dias",
            "Ano atual", "Todos", "Personalizado"]


def intervalo_periodo(nome: str) -> tuple[date | None, date | None]:
    """Converte o nome do período em (data inicial, data final)."""
    h = utils.hoje()
    inicio_mes = date(h.year, h.month, 1)
    if nome == "Mês atual":
        return inicio_mes, utils.adicionar_meses(inicio_mes, 1, 1) - timedelta(days=1)
    if nome == "Mês anterior":
        ini = utils.adicionar_meses(inicio_mes, -1, 1)
        return ini, inicio_mes - timedelta(days=1)
    if nome == "Próximo mês":
        ini = utils.adicionar_meses(inicio_mes, 1, 1)
        return ini, utils.adicionar_meses(ini, 1, 1) - timedelta(days=1)
    if nome == "Próximos 30 dias":
        return h, h + timedelta(days=30)
    if nome == "Últimos 90 dias":
        return h - timedelta(days=90), h
    if nome == "Ano atual":
        return date(h.year, 1, 1), date(h.year, 12, 31)
    return None, None


class PaginaFinanceiro(Pagina):
    TITULO = "Financeiro"
    SUBTITULO = "Mensalidades, parcelas e recebimentos"

    def __init__(self, master, app):
        super().__init__(master, app)
        c = self.conteudo
        c.grid_columnconfigure(0, weight=1)
        c.grid_rowconfigure(0, weight=1)
        self.abas = ctk.CTkTabview(c, fg_color=COR["fundo"], corner_radius=14,
                                   segmented_button_fg_color=COR["primaria_clara"],
                                   segmented_button_selected_color=COR["primaria"],
                                   segmented_button_selected_hover_color=COR["primaria_escura"],
                                   segmented_button_unselected_color=COR["primaria_clara"],
                                   segmented_button_unselected_hover_color="#C8DFE0",
                                   text_color=COR["primaria_profunda"], command=self.atualizar)
        self.abas.grid(row=0, column=0, sticky="nsew")
        self.abas.add("Parcelas")
        self.abas.add("Recebimentos (caixa)")
        self._montar_parcelas(self.abas.tab("Parcelas"))
        self._montar_caixa(self.abas.tab("Recebimentos (caixa)"))

    # ================================================================ PARCELAS
    def _montar_parcelas(self, aba):
        aba.grid_columnconfigure(0, weight=1)
        aba.grid_rowconfigure(3, weight=1)

        # Totais por situação
        cards = ctk.CTkFrame(aba, fg_color="transparent")
        cards.grid(row=0, column=0, sticky="ew", pady=(4, 10))
        cards.grid_columnconfigure((0, 1, 2), weight=1)
        self.card_pago = ui.CartaoIndicador(cards, "Pago", COR["pago"], "✔")
        self.card_dia = ui.CartaoIndicador(cards, "Pendente (em dia)", COR["em_dia"], "⏳")
        self.card_atraso = ui.CartaoIndicador(cards, "Em atraso", COR["atraso"], "⚠")
        for i, card in enumerate((self.card_pago, self.card_dia, self.card_atraso)):
            card.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0 if i == 2 else 6))

        # Filtros
        filtros = ui.Cartao(aba)
        filtros.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.seg_situacao = ctk.CTkSegmentedButton(
            filtros, values=["Todas", config.SITUACAO_PAGO, config.SITUACAO_EM_DIA, config.SITUACAO_ATRASO,
                             config.SITUACAO_CANCELADO], command=lambda _v: self.atualizar(), font=fonte(12))
        self.seg_situacao.set("Todas")
        self.seg_situacao.grid(row=0, column=0, columnspan=6, sticky="w", padx=14, pady=(12, 6))
        self.periodo = ui.combo(filtros, PERIODOS, 170, self._periodo_mudou, valor_inicial="Mês atual")
        self.periodo.grid(row=1, column=0, padx=(14, 6), pady=(0, 12))
        self.data_ini = ui.CampoData(filtros, 120)
        self.data_ini.grid(row=1, column=1, padx=4, pady=(0, 12))
        self.data_fim = ui.CampoData(filtros, 120)
        self.data_fim.grid(row=1, column=2, padx=4, pady=(0, 12))
        ui.botao(filtros, "Filtrar", self.atualizar, "secundario", 80).grid(row=1, column=3, padx=4, pady=(0, 12))
        self.busca = ui.Campo(filtros, 260, placeholder_text="Paciente, responsável ou serviço")
        self.busca.grid(row=1, column=4, padx=4, pady=(0, 12))
        self.busca.bind("<KeyRelease>", lambda _e: self._agendar())
        self.lbl_qtd = ui.subtitulo(filtros, "")
        self.lbl_qtd.grid(row=1, column=5, padx=10, pady=(0, 12))

        ui.barra_botoes(aba, [
            ("$ Registrar pagamento", self._receber, "primario", 180),
            ("Quitar selecionadas", self._quitar, "secundario", 160),
            ("Recibo", self._recibo, "secundario", 100),
            ("✎ Editar", self._editar, "secundario", 90),
            ("Cancelar / Reabrir", self._cancelar, "perigo", 150),
            ("✉ Cobrar", self._cobrar, "whatsapp", 100),
            ("Ficha do paciente", self._ficha, "fantasma", 140),
            ("⤓ Excel", self._exportar, "fantasma", 90),
        ]).grid(row=2, column=0, sticky="w", pady=(0, 8))

        self.tabela = ui.Tabela(aba, [
            ("pac", "Paciente", 180, "w"), ("resp", "Responsável", 160, "w"),
            ("serv", "Serviço", 190, "w"), ("parc", "Parcela", 95, "center"),
            ("venc", "Vencimento", 95, "center"), ("valor", "Valor devido", 105, "e"),
            ("pago", "Pago", 95, "e"), ("saldo", "Saldo", 95, "e"),
            ("sit", "Situação", 150, "center"), ("forma", "Forma pgto.", 140, "w")],
            altura=14, multipla=True, ao_duplo_clique=self._receber)
        self.tabela.grid(row=3, column=0, sticky="nsew")
        self._job = None
        self._periodo_mudou("Mês atual")

    def _agendar(self):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(300, self.atualizar)

    def _periodo_mudou(self, nome):
        ini, fim = intervalo_periodo(nome)
        if nome != "Personalizado":
            self.data_ini.definir(ini)
            self.data_fim.definir(fim)
        estado = "normal" if nome == "Personalizado" else "disabled"
        self.data_ini.configure(state=estado)
        self.data_fim.configure(state=estado)
        self.atualizar()

    def _datas(self) -> tuple[date | None, date | None]:
        try:
            return self.data_ini.data(), self.data_fim.data()
        except ValueError:
            return None, None

    def atualizar(self, **kwargs):
        if kwargs.get("situacao"):
            self.seg_situacao.set(kwargs["situacao"])
        if self.abas.get() == "Recebimentos (caixa)":
            self._atualizar_caixa()
            return
        ini, fim = self._datas()
        # Para "Em atraso" mostramos TODOS os atrasos, independente do período
        situacao = self.seg_situacao.get()
        if situacao == config.SITUACAO_ATRASO and self.periodo.get() != "Personalizado":
            ini, fim = None, None
        parcelas = financeiro.listar_parcelas(None, self.busca.valor(), ini, fim,
                                              incluir_canceladas=situacao in ("Todas", config.SITUACAO_CANCELADO))
        # totais antes de filtrar a situação
        tot = {s: 0.0 for s in config.SITUACOES}
        qtd = {s: 0 for s in config.SITUACOES}
        for p in parcelas:
            tot[p["situacao"]] += (float(p.get("total_pago") or 0) if p["situacao"] == config.SITUACAO_PAGO
                                   else p["saldo"])
            qtd[p["situacao"]] += 1
        self.card_pago.definir(utils.formatar_moeda(tot[config.SITUACAO_PAGO]),
                               f"{qtd[config.SITUACAO_PAGO]} parcela(s) no período")
        self.card_dia.definir(utils.formatar_moeda(tot[config.SITUACAO_EM_DIA]),
                              f"{qtd[config.SITUACAO_EM_DIA]} parcela(s) a vencer")
        atrasos = financeiro.listar_parcelas(config.SITUACAO_ATRASO)
        self.card_atraso.definir(utils.formatar_moeda(sum(p["saldo"] for p in atrasos)),
                                 f"{len(atrasos)} parcela(s) – todos os períodos")

        if situacao != "Todas":
            parcelas = [p for p in parcelas if p["situacao"] == situacao]
        self.parcelas = {str(p["id"]): p for p in parcelas}
        self.tabela.carregar([{
            "iid": p["id"],
            "valores": (p["paciente"], p.get("responsavel") or "", p["servico"], p["rotulo"],
                        utils.data_br(p["vencimento"]), utils.formatar_moeda(p["valor_devido"]),
                        utils.formatar_moeda(p.get("total_pago") or 0), utils.formatar_moeda(p["saldo"]),
                        p["situacao"] + (f" ({p['dias_atraso']}d)" if p.get("dias_atraso") else "")
                        + (" · parcial" if p.get("parcial") else ""),
                        p.get("forma_pagamento") or ""),
            "tag": p["situacao"]} for p in parcelas])
        self.lbl_qtd.configure(text=f"{len(parcelas)} parcela(s)")

    # ---- ações
    def _sel(self) -> int | None:
        sel = self.tabela.selecionado()
        if not sel:
            ui.aviso("Selecione uma parcela na lista.", parent=self)
            return None
        return int(sel)

    def _receber(self):
        pid = self._sel()
        if pid:
            acoes.registrar_pagamento(self, pid, self.atualizar)

    def _quitar(self):
        acoes.quitar_varias(self, self.tabela.selecionados(), self.atualizar)

    def _recibo(self):
        pid = self._sel()
        if pid:
            acoes.recibo_da_parcela(self, pid)

    def _editar(self):
        pid = self._sel()
        if pid:
            acoes.editar_parcela(self, pid, self.atualizar)

    def _cancelar(self):
        pid = self._sel()
        if pid:
            acoes.cancelar_ou_reabrir_parcela(self, pid, self.atualizar)

    def _cobrar(self):
        pid = self._sel()
        if pid:
            acoes.cobrar_parcela(self, pid, self.atualizar)

    def _ficha(self):
        pid = self._sel()
        if pid:
            acoes.abrir_ficha(self, self.parcelas[str(pid)]["paciente_id"], self.atualizar)

    def _exportar(self):
        ini, fim = self._datas()
        descricao = f"Situação: {self.seg_situacao.get()} · Período: {self.periodo.get()}"
        if ini and fim:
            descricao += f" ({utils.data_br(ini)} a {utils.data_br(fim)})"
        caminho = relatorios.exportar_parcelas(list(self.parcelas.values()), descricao)
        recibos.abrir_arquivo(caminho)
        acoes.notificar(self, f"Planilha salva em {caminho.name}")

    # ================================================================ CAIXA
    def _montar_caixa(self, aba):
        aba.grid_columnconfigure(0, weight=1)
        aba.grid_rowconfigure(2, weight=1)
        filtros = ui.Cartao(aba)
        filtros.grid(row=0, column=0, sticky="ew", pady=(4, 8))
        self.cx_periodo = ui.combo(filtros, PERIODOS, 170, self._cx_periodo_mudou, valor_inicial="Mês atual")
        self.cx_periodo.grid(row=0, column=0, padx=(14, 6), pady=12)
        self.cx_ini = ui.CampoData(filtros, 120)
        self.cx_ini.grid(row=0, column=1, padx=4)
        self.cx_fim = ui.CampoData(filtros, 120)
        self.cx_fim.grid(row=0, column=2, padx=4)
        self.cx_forma = ui.combo(filtros, ["Todas"] + config.FORMAS_PAGAMENTO, 220,
                                 lambda _v: self._atualizar_caixa())
        self.cx_forma.grid(row=0, column=3, padx=4)
        ui.botao(filtros, "Filtrar", self._atualizar_caixa, "secundario", 80).grid(row=0, column=4, padx=4)
        self.cx_busca = ui.Campo(filtros, 200, placeholder_text="Nome ou nº do recibo")
        self.cx_busca.grid(row=0, column=5, padx=4)
        self.cx_busca.bind("<Return>", lambda _e: self._atualizar_caixa())

        ui.barra_botoes(aba, [
            ("Recibo (PDF)", self._cx_recibo, "primario", 140),
            ("✉ Enviar confirmação", self._cx_whats, "whatsapp", 180),
            ("↺ Estornar", self._cx_estornar, "perigo", 110),
            ("⤓ Excel", self._cx_exportar, "fantasma", 90),
        ]).grid(row=1, column=0, sticky="w", pady=(0, 8))

        corpo = ctk.CTkFrame(aba, fg_color="transparent")
        corpo.grid(row=2, column=0, sticky="nsew")
        corpo.grid_columnconfigure(0, weight=3)
        corpo.grid_columnconfigure(1, weight=1)
        corpo.grid_rowconfigure(0, weight=1)
        self.cx_tabela = ui.Tabela(corpo, [
            ("data", "Data", 90, "center"), ("rec", "Recibo", 70, "center"),
            ("pac", "Paciente", 170, "w"), ("serv", "Serviço", 170, "w"),
            ("parc", "Parcela", 90, "center"), ("forma", "Forma", 170, "w"),
            ("valor", "Valor", 100, "e"), ("usuario", "Lançado por", 110, "w")],
            altura=14, ao_duplo_clique=self._cx_recibo)
        self.cx_tabela.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.cx_resumo = ui.Cartao(corpo)
        self.cx_resumo.grid(row=0, column=1, sticky="nsew")
        self._cx_periodo_mudou("Mês atual")

    def _cx_periodo_mudou(self, nome):
        ini, fim = intervalo_periodo(nome)
        if nome != "Personalizado":
            self.cx_ini.definir(ini)
            self.cx_fim.definir(fim)
        estado = "normal" if nome == "Personalizado" else "disabled"
        self.cx_ini.configure(state=estado)
        self.cx_fim.configure(state=estado)
        self._atualizar_caixa()

    def _cx_datas(self):
        try:
            ini, fim = self.cx_ini.data(), self.cx_fim.data()
        except ValueError:
            ini, fim = None, None
        return ini or date(2000, 1, 1), fim or date(2100, 12, 31)

    def _atualizar_caixa(self):
        ini, fim = self._cx_datas()
        lista = financeiro.listar_pagamentos(ini, fim, self.cx_forma.get(), self.cx_busca.valor())
        self.pagamentos = {str(g["id"]): g for g in lista}
        self.cx_tabela.carregar([{
            "iid": g["id"],
            "valores": (utils.data_br(g["data_pagamento"]), f"{g['recibo_numero'] or 0:06d}", g["paciente"],
                        g["servico"], g["rotulo"],
                        g["forma_pagamento"] + (f" {g['parcelas_cartao']}x" if g["parcelas_cartao"] > 1 else ""),
                        utils.formatar_moeda(g["valor"]), g.get("usuario") or "")} for g in lista])
        # Resumo lateral por forma de pagamento
        for w in self.cx_resumo.winfo_children():
            w.destroy()
        ui.titulo(self.cx_resumo, "Resumo do período", 14).pack(anchor="w", padx=16, pady=(14, 2))
        total = sum(g["valor"] for g in lista)
        ctk.CTkLabel(self.cx_resumo, text=utils.formatar_moeda(total), font=fonte(24, "bold"),
                     text_color=COR["pago"]).pack(anchor="w", padx=16)
        ui.subtitulo(self.cx_resumo, f"{len(lista)} recebimento(s)").pack(anchor="w", padx=16, pady=(0, 10))
        formas: dict[str, float] = {}
        for g in lista:
            formas[g["forma_pagamento"]] = formas.get(g["forma_pagamento"], 0) + g["valor"]
        for forma, valor in sorted(formas.items(), key=lambda x: -x[1]):
            linha = ctk.CTkFrame(self.cx_resumo, fg_color="transparent")
            linha.pack(fill="x", padx=16, pady=2)
            ctk.CTkLabel(linha, text=forma, font=fonte(11), text_color=COR["texto"]).pack(side="left")
            ctk.CTkLabel(linha, text=utils.formatar_moeda(valor), font=fonte(11, "bold"),
                         text_color=COR["primaria_profunda"]).pack(side="right")

    def _cx_sel(self) -> int | None:
        sel = self.cx_tabela.selecionado()
        if not sel:
            ui.aviso("Selecione um recebimento na lista.", parent=self)
            return None
        return int(sel)

    def _cx_recibo(self):
        gid = self._cx_sel()
        if gid:
            acoes.abrir_recibo(self, gid)

    def _cx_whats(self):
        gid = self._cx_sel()
        if gid:
            acoes.enviar_recibo_whatsapp(self, gid)

    def _cx_estornar(self):
        gid = self._cx_sel()
        if gid:
            acoes.estornar_pagamento(self, gid, self._atualizar_caixa)

    def _cx_exportar(self):
        ini, fim = self._cx_datas()
        caminho = relatorios.exportar_pagamentos(ini, fim)
        recibos.abrir_arquivo(caminho)
