"""
=============================================================================
 ui/paginas/painel.py — Painel inicial (visão geral)
=============================================================================
 Mostra, para o mês escolhido:
   • quanto foi recebido, quanto falta receber e quanto está em atraso
   • gráfico Recebido x Previsto dos últimos 6 meses
   • pacientes por diagnóstico
   • lista de quem está em atraso (com botão de cobrança no WhatsApp)
   • parcelas que vencem nos próximos 7 dias
=============================================================================
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import customtkinter as ctk

from app.core import config, sessao, utils
from app.repositorios import financeiro, pacientes
from app.ui import acoes
from app.ui import componentes as ui
from app.ui.paginas.base import Pagina
from app.ui.tema import fonte

COR = config.CORES


class PaginaPainel(Pagina):
    TITULO = "Painel"
    SUBTITULO = "Visão geral do Espaço"

    def __init__(self, master, app):
        super().__init__(master, app)
        h = utils.hoje()
        self.ref = date(h.year, h.month, 1)

        # seletor de mês no cabeçalho
        nav = self.acoes_cabecalho
        ui.botao(nav, "◀", lambda: self._mudar_mes(-1), "secundario", 40).grid(row=0, column=0)
        self.lbl_mes = ctk.CTkLabel(nav, text="", font=fonte(14, "bold"), width=170,
                                    text_color=COR["primaria_profunda"])
        self.lbl_mes.grid(row=0, column=1, padx=6)
        ui.botao(nav, "▶", lambda: self._mudar_mes(1), "secundario", 40).grid(row=0, column=2)

        area = ctk.CTkScrollableFrame(self.conteudo, fg_color="transparent")
        area.pack(fill="both", expand=True)
        area.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="c")

        # --- Indicadores
        self.c_recebido = ui.CartaoIndicador(area, "Recebido no mês", COR["pago"], "✔")
        self.c_receber = ui.CartaoIndicador(area, "A receber (em dia)", COR["em_dia"], "⏳")
        self.c_atraso = ui.CartaoIndicador(area, "Em atraso (total)", COR["atraso"], "⚠")
        self.c_pacientes = ui.CartaoIndicador(area, "Pacientes ativos", COR["primaria_escura"], "♥")
        for i, card in enumerate((self.c_recebido, self.c_receber, self.c_atraso, self.c_pacientes)):
            card.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0 if i == 3 else 6), pady=(0, 12))

        # --- Gráfico
        cg = ui.Cartao(area)
        cg.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=(0, 6), pady=(0, 12))
        ui.titulo(cg, "Recebido x Previsto – últimos 6 meses", 14).pack(anchor="w", padx=16, pady=(12, 0))
        self.grafico = ui.GraficoBarras(cg, [("Recebido", COR["primaria"]), ("Previsto", COR["destaque"])])
        self.grafico.pack(fill="both", expand=True, padx=12, pady=12)

        # --- Diagnósticos
        self.card_diag = ui.Cartao(area)
        self.card_diag.grid(row=1, column=3, sticky="nsew", padx=(6, 0), pady=(0, 12))
        ui.titulo(self.card_diag, "Pacientes por diagnóstico", 14).pack(anchor="w", padx=16, pady=(12, 6))
        self.lista_diag = ctk.CTkFrame(self.card_diag, fg_color="transparent")
        self.lista_diag.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        # --- Em atraso
        ca = ui.Cartao(area)
        ca.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=(0, 6))
        topo = ctk.CTkFrame(ca, fg_color="transparent")
        topo.pack(fill="x", padx=16, pady=(12, 6))
        ui.titulo(topo, "⚠ Responsáveis em atraso", 14).pack(side="left")
        ui.botao(topo, "✉ Cobrar", self._cobrar, "whatsapp", 100, 32).pack(side="right")
        ui.botao(topo, "Ver todos", lambda: self.app.mostrar("cobrancas"), "fantasma", 90, 32).pack(side="right", padx=4)
        self.tab_atraso = ui.Tabela(ca, [("resp", "Responsável", 170, "w"), ("pac", "Paciente(s)", 170, "w"),
                                         ("dias", "Atraso", 70, "center"), ("total", "Total", 100, "e")],
                                    altura=6, ao_duplo_clique=self._cobrar,
                                    texto_vazio="Nenhum pagamento em atraso ✔")
        self.tab_atraso.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # --- A vencer
        cv = ui.Cartao(area)
        cv.grid(row=2, column=2, columnspan=2, sticky="nsew", padx=(6, 0))
        topo2 = ctk.CTkFrame(cv, fg_color="transparent")
        topo2.pack(fill="x", padx=16, pady=(12, 6))
        ui.titulo(topo2, "⏳ Vencem nos próximos 7 dias", 14).pack(side="left")
        ui.botao(topo2, "$ Receber", self._receber, "primario", 100, 32).pack(side="right")
        self.tab_vencer = ui.Tabela(cv, [("pac", "Paciente", 170, "w"), ("serv", "Serviço", 150, "w"),
                                         ("venc", "Venc.", 85, "center"), ("valor", "Valor", 90, "e")],
                                    altura=6, ao_duplo_clique=self._receber,
                                    texto_vazio="Nenhum vencimento nos próximos dias.")
        self.tab_vencer.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # ----------------------------------------------------------------------
    def _mudar_mes(self, delta: int):
        self.ref = utils.adicionar_meses(self.ref, delta, 1)
        self.atualizar()

    def atualizar(self, **_kwargs):
        usuario = sessao.usuario() or {}
        hora = datetime.now().hour
        saudacao = "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"
        self.lbl_subtitulo.configure(text=f"{saudacao}, {utils.primeiro_nome(usuario.get('nome', ''))}! "
                                          f"Hoje é {utils.data_extenso(utils.hoje())}.")
        self.lbl_mes.configure(text=f"{utils.MESES[self.ref.month - 1].capitalize()} de {self.ref.year}")

        ind = financeiro.indicadores(self.ref.year, self.ref.month)
        tot = pacientes.totais()
        self.c_recebido.definir(utils.formatar_moeda(ind["recebido"]), f"{ind['qtd_pagamentos']} pagamento(s)")
        self.c_receber.definir(utils.formatar_moeda(ind["a_receber"]),
                               f"Previsto no mês: {utils.formatar_moeda(ind['previsto'])}")
        self.c_atraso.definir(utils.formatar_moeda(ind["em_atraso"]),
                              f"{ind['qtd_parcelas_atraso']} parcela(s) · {ind['qtd_inadimplentes']} responsável(is)")
        self.c_pacientes.definir(str(tot["ativos"]), f"Pagas no mês: {ind['pagas_mes']}/{ind['parcelas_mes']} "
                                                     f"({ind['adimplencia']:.0f}%)")

        self.grafico.definir_dados([{"rotulo": m["rotulo"], "valores": [m["recebido"], m["previsto"]]}
                                    for m in financeiro.receita_mensal(6)])

        for w in self.lista_diag.winfo_children():
            w.destroy()
        contagem = pacientes.contagem_por_diagnostico()
        maior = max(contagem.values()) if contagem else 1
        if not contagem:
            ui.subtitulo(self.lista_diag, "Sem pacientes cadastrados.").pack(anchor="w")
        for nome, qtd in list(contagem.items())[:7]:
            linha = ctk.CTkFrame(self.lista_diag, fg_color="transparent")
            linha.pack(fill="x", pady=3)
            ctk.CTkLabel(linha, text=f"{nome}", font=fonte(11), anchor="w",
                         text_color=COR["texto"]).pack(anchor="w")
            barra = ctk.CTkProgressBar(linha, height=10, corner_radius=5,
                                       progress_color=COR["destaque"], fg_color=COR["destaque_claro"])
            barra.set(qtd / maior)
            barra.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(linha, text=str(qtd), font=fonte(11, "bold"), width=28,
                         text_color=COR["texto"]).pack(side="left", padx=(6, 0))

        self.grupos = {str(i): g for i, g in enumerate(financeiro.inadimplentes())}
        self.tab_atraso.carregar([{"iid": k, "valores": (g["responsavel"], ", ".join(g["pacientes"]),
                                                         f"{g['maior_atraso']} d", utils.formatar_moeda(g["total"])),
                                   "tag": config.SITUACAO_ATRASO} for k, g in self.grupos.items()])
        vencer = financeiro.listar_parcelas(situacao=config.SITUACAO_EM_DIA, data_ini=utils.hoje(),
                                            data_fim=utils.hoje() + timedelta(days=7))
        self.tab_vencer.carregar([{"iid": p["id"], "valores": (p["paciente"], p["servico"],
                                                               utils.data_br(p["vencimento"]),
                                                               utils.formatar_moeda(p["saldo"])),
                                   "tag": config.SITUACAO_EM_DIA} for p in vencer])

    def _cobrar(self):
        sel = self.tab_atraso.selecionado()
        if not sel:
            ui.aviso("Selecione um responsável na lista de atrasos.", parent=self)
            return
        g = self.grupos[sel]
        acoes.cobrar_responsavel(self, g["responsavel_id"], g["paciente_ids"][0], self.atualizar)

    def _receber(self):
        sel = self.tab_vencer.selecionado()
        if not sel:
            ui.aviso("Selecione uma parcela na lista de vencimentos.", parent=self)
            return
        acoes.registrar_pagamento(self, int(sel), self.atualizar)
