"""
=============================================================================
 ui/paginas/relatorios.py — Relatórios
=============================================================================
 Escolha o período e veja: total recebido, por forma de pagamento e por
 serviço. Botões exportam planilhas Excel (pasta dados/relatorios).
=============================================================================
"""
from __future__ import annotations

import customtkinter as ctk

from app.core import config, utils
from app.repositorios import financeiro
from app.servicos import recibos, relatorios
from app.ui import acoes
from app.ui import componentes as ui
from app.ui.paginas.base import Pagina
from app.ui.paginas.financeiro import PERIODOS, intervalo_periodo
from app.ui.tema import fonte

COR = config.CORES


class PaginaRelatorios(Pagina):
    TITULO = "Relatórios"
    SUBTITULO = "Resumo do período e exportação para Excel"

    def __init__(self, master, app):
        super().__init__(master, app)
        c = self.conteudo
        c.grid_columnconfigure((0, 1), weight=1)
        c.grid_rowconfigure(2, weight=1)

        filtros = ui.Cartao(c)
        filtros.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.periodo = ui.combo(filtros, [p for p in PERIODOS if p != "Todos"], 170, self._periodo,
                                valor_inicial="Mês atual")
        self.periodo.grid(row=0, column=0, padx=(14, 6), pady=12)
        self.ini = ui.CampoData(filtros, 120)
        self.ini.grid(row=0, column=1, padx=4)
        self.fim = ui.CampoData(filtros, 120)
        self.fim.grid(row=0, column=2, padx=4)
        ui.botao(filtros, "Atualizar", self.atualizar, "secundario", 100).grid(row=0, column=3, padx=4)

        cards = ctk.CTkFrame(c, fg_color="transparent")
        cards.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        cards.grid_columnconfigure((0, 1, 2), weight=1)
        self.c_rec = ui.CartaoIndicador(cards, "Recebido no período", COR["pago"], "✔")
        self.c_qtd = ui.CartaoIndicador(cards, "Recebimentos", COR["primaria_escura"], "#")
        self.c_ticket = ui.CartaoIndicador(cards, "Valor médio", COR["destaque_escuro"], "≈")
        for i, card in enumerate((self.c_rec, self.c_qtd, self.c_ticket)):
            card.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0 if i == 2 else 6))

        self.tab_formas = ui.Tabela(c, [("forma", "Forma de pagamento", 220, "w"), ("qtd", "Qtd.", 60, "center"),
                                        ("total", "Total", 120, "e")], altura=10)
        self.tab_formas.grid(row=2, column=0, sticky="nsew", padx=(0, 6))
        self.tab_serv = ui.Tabela(c, [("serv", "Serviço", 260, "w"), ("qtd", "Qtd.", 60, "center"),
                                      ("total", "Total", 120, "e")], altura=10)
        self.tab_serv.grid(row=2, column=1, sticky="nsew", padx=(6, 0))

        exp = ui.Cartao(c)
        exp.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ctk.CTkLabel(exp, text="Exportar para Excel:", font=fonte(13, "bold"),
                     text_color=COR["primaria_profunda"]).grid(row=0, column=0, padx=14, pady=12)
        for i, (txt, cmd) in enumerate((("Recebimentos do período", self._exp_pag),
                                        ("Parcelas do período", self._exp_parc),
                                        ("Inadimplentes", self._exp_inad),
                                        ("Pacientes", self._exp_pac))):
            ui.botao(exp, txt, cmd, "secundario", 190).grid(row=0, column=i + 1, padx=4)
        ui.botao(exp, "Abrir pasta", lambda: recibos.abrir_arquivo(config.RELATORIOS_DIR),
                 "fantasma", 120).grid(row=0, column=6, padx=8)
        self._periodo("Mês atual")

    def _periodo(self, nome):
        a, b = intervalo_periodo(nome)
        if nome != "Personalizado":
            self.ini.definir(a)
            self.fim.definir(b)
        self.atualizar()

    def _datas(self):
        try:
            a, b = self.ini.data(), self.fim.data()
        except ValueError as e:
            ui.erro(str(e), parent=self)
            return None, None
        return a, b

    def atualizar(self, **_kwargs):
        a, b = self._datas()
        if not a or not b:
            return
        formas = financeiro.por_forma_pagamento(a, b)
        total = sum(f["total"] for f in formas)
        qtd = sum(f["qtd"] for f in formas)
        self.c_rec.definir(utils.formatar_moeda(total), f"{utils.data_br(a)} a {utils.data_br(b)}")
        self.c_qtd.definir(str(qtd), "pagamentos registrados")
        self.c_ticket.definir(utils.formatar_moeda(total / qtd if qtd else 0), "por recebimento")
        self.tab_formas.carregar([{"iid": i, "valores": (f["forma"], f["qtd"], utils.formatar_moeda(f["total"]))}
                                  for i, f in enumerate(formas)])
        self.tab_serv.carregar([{"iid": i, "valores": (s["servico"], s["qtd"], utils.formatar_moeda(s["total"]))}
                                for i, s in enumerate(financeiro.por_servico(a, b))])

    def _abrir(self, caminho):
        recibos.abrir_arquivo(caminho)
        acoes.notificar(self, f"Planilha gerada: {caminho.name}")

    def _exp_pag(self):
        a, b = self._datas()
        if a and b:
            self._abrir(relatorios.exportar_pagamentos(a, b))

    def _exp_parc(self):
        a, b = self._datas()
        if a and b:
            self._abrir(relatorios.exportar_parcelas(financeiro.listar_parcelas(data_ini=a, data_fim=b),
                                                     f"Vencimentos de {utils.data_br(a)} a {utils.data_br(b)}"))

    def _exp_inad(self):
        self._abrir(relatorios.exportar_inadimplentes())

    def _exp_pac(self):
        self._abrir(relatorios.exportar_pacientes(None))
