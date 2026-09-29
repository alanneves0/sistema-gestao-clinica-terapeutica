"""
=============================================================================
 ui/dialogos/ficha.py — Ficha financeira do paciente
=============================================================================
 Tudo sobre o financeiro de UM paciente num só lugar:
   • resumo (total pago, em aberto, em atraso)
   • serviços contratados (contratos) — carnê, renovar, encerrar, cancelar
   • parcelas — receber, recibo, editar, cancelar, cobrar no WhatsApp
=============================================================================
"""
from __future__ import annotations

import customtkinter as ctk

from app.core import config, utils
from app.repositorios import financeiro, pacientes
from app.servicos import recibos
from app.ui import acoes
from app.ui import componentes as ui

COR = config.CORES


class FichaFinanceira(ui.DialogoBase):
    def __init__(self, master, paciente_id: int):
        self.paciente = pacientes.obter(paciente_id)
        super().__init__(master, f"Ficha financeira – {self.paciente['nome']}", 1180, 780)
        self.paciente_id = paciente_id
        self._montar()
        self.atualizar()

    def _montar(self):
        c = self.corpo
        c.grid_columnconfigure(0, weight=1)
        c.grid_rowconfigure(4, weight=1)
        p, r = self.paciente, self.paciente.get("responsavel") or {}

        # Cabeçalho
        cab = ctk.CTkFrame(c, fg_color="transparent")
        cab.grid(row=0, column=0, sticky="ew")
        cab.grid_columnconfigure(0, weight=1)
        ui.titulo(cab, p["nome"], 20).grid(row=0, column=0, sticky="w")
        diag = (p.get("diagnosticos") or "sem diagnóstico informado").replace(";", ",")
        ui.subtitulo(cab, f"{utils.texto_idade(p.get('data_nascimento'))} · {diag}\n"
                          f"Responsável: {r.get('nome', '—')} ({r.get('parentesco') or '—'}) · "
                          f"WhatsApp {r.get('whatsapp') or r.get('telefone') or '—'}").grid(row=1, column=0, sticky="w")
        botoes = ctk.CTkFrame(cab, fg_color="transparent")
        botoes.grid(row=0, column=1, rowspan=2, sticky="e")
        ui.botao(botoes, "✉ Cobrar / Lembrar", lambda: acoes.cobrar_responsavel(
            self, p.get("responsavel_id"), self.paciente_id, self.atualizar), "whatsapp", 170).grid(row=0, column=0, padx=4)
        ui.botao(botoes, "+ Incluir serviço", lambda: acoes.novo_contrato(
            self, self.paciente_id, p["nome"], self.atualizar), "primario", 160).grid(row=0, column=1, padx=4)

        # Indicadores
        cards = ctk.CTkFrame(c, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="ew", pady=12)
        cards.grid_columnconfigure((0, 1, 2), weight=1)
        self.card_pago = ui.CartaoIndicador(cards, "Total pago", COR["pago"], "✔")
        self.card_aberto = ui.CartaoIndicador(cards, "A vencer (em dia)", COR["em_dia"], "⏳")
        self.card_atraso = ui.CartaoIndicador(cards, "Em atraso", COR["atraso"], "⚠")
        for i, card in enumerate((self.card_pago, self.card_aberto, self.card_atraso)):
            card.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0 if i == 2 else 6))

        # Contratos
        linha = ctk.CTkFrame(c, fg_color="transparent")
        linha.grid(row=2, column=0, sticky="ew")
        linha.grid_columnconfigure(0, weight=1)
        ui.titulo(linha, "Serviços contratados", 15).grid(row=0, column=0, sticky="w")
        ui.barra_botoes(linha, [
            ("Carnê PDF", self._carne, "secundario", 120),
            ("↻ Renovar", self._renovar, "secundario", 100),
            ("Encerrar", lambda: self._status_contrato("encerrado"), "secundario", 100),
            ("Cancelar", lambda: self._status_contrato("cancelado"), "perigo", 100),
            ("Excluir", self._excluir_contrato, "perigo", 90),
        ]).grid(row=0, column=1, sticky="e")
        self.tab_contratos = ui.Tabela(c, [
            ("serv", "Serviço", 260, "w"), ("mod", "Contratação", 120, "center"),
            ("ini", "Início", 90, "center"), ("parc", "Pagas", 80, "center"),
            ("total", "Valor total", 110, "e"), ("agenda", "Profissional / horário", 220, "w"),
            ("status", "Status", 90, "center")], altura=4, ao_selecionar=self._carregar_parcelas)
        self.tab_contratos.grid(row=3, column=0, sticky="ew", pady=(6, 12))

        # Parcelas
        baixo = ctk.CTkFrame(c, fg_color="transparent")
        baixo.grid(row=4, column=0, sticky="nsew")
        baixo.grid_columnconfigure(0, weight=1)
        baixo.grid_rowconfigure(1, weight=1)
        topo = ctk.CTkFrame(baixo, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew")
        topo.grid_columnconfigure(0, weight=1)
        self.lbl_parcelas = ui.titulo(topo, "Parcelas", 15)
        self.lbl_parcelas.grid(row=0, column=0, sticky="w")
        ui.barra_botoes(topo, [
            ("$ Receber", self._receber, "primario", 110),
            ("Quitar selecionadas", self._quitar, "secundario", 160),
            ("Recibo", self._recibo, "secundario", 90),
            ("Editar", self._editar, "secundario", 90),
            ("Cancelar/Reabrir", self._cancelar, "perigo", 140),
            ("Ver todas", self._todas, "fantasma", 100),
        ]).grid(row=0, column=1, sticky="e")
        self.tab_parcelas = ui.Tabela(baixo, [
            ("serv", "Serviço", 230, "w"), ("parc", "Parcela", 100, "center"),
            ("venc", "Vencimento", 100, "center"), ("valor", "Valor", 120, "e"),
            ("pago", "Pago", 100, "e"), ("saldo", "Saldo", 100, "e"),
            ("sit", "Situação", 140, "center"), ("forma", "Forma", 150, "w")],
            altura=8, multipla=True, ao_duplo_clique=self._receber)
        self.tab_parcelas.grid(row=1, column=0, sticky="nsew", pady=(6, 0))

        self.rodape.grid_columnconfigure(0, weight=1)
        ui.botao(self.rodape, "Fechar", self.fechar, "secundario").grid(row=0, column=1)

    # ------------------------------------------------------------ dados
    def atualizar(self):
        resumo = financeiro.resumo_paciente(self.paciente_id)
        self.card_pago.definir(utils.formatar_moeda(resumo["pago"]))
        self.card_aberto.definir(utils.formatar_moeda(resumo["em_aberto"]))
        self.card_atraso.definir(utils.formatar_moeda(resumo["em_atraso"]))
        self.contratos = {str(k["id"]): k for k in financeiro.listar_contratos(self.paciente_id)}
        self.tab_contratos.carregar([{
            "iid": cid,
            "valores": (k["descricao"], config.MODALIDADES.get(k["modalidade"], k["modalidade"]),
                        utils.data_br(k["data_inicio"]), f"{k['pagas']}/{k['total_parcelas']}",
                        utils.formatar_moeda(k["valor_total"]),
                        " · ".join(x for x in (k.get("profissional"), k.get("dias_atendimento"),
                                               k.get("horario")) if x),
                        k["status"].capitalize()),
            "tag": None if k["status"] == "ativo" else "inativo"} for cid, k in self.contratos.items()])
        self._contrato_filtro = None
        self._carregar_parcelas(todas=True)

    def _carregar_parcelas(self, todas: bool = False):
        cid = None if todas else self.tab_contratos.selecionado()
        self._contrato_filtro = cid
        parcelas = financeiro.listar_parcelas(paciente_id=self.paciente_id, incluir_canceladas=True,
                                              contrato_id=int(cid) if cid else None)
        self.lbl_parcelas.configure(text="Parcelas" + (f" – {self.contratos[cid]['descricao']}" if cid else
                                                        " – todos os serviços"))
        self.tab_parcelas.carregar([{
            "iid": p["id"],
            "valores": (p["servico"], p["rotulo"], utils.data_br(p["vencimento"]),
                        utils.formatar_moeda(p["valor_devido"] or p["valor_pontualidade"]),
                        utils.formatar_moeda(p.get("total_pago") or 0), utils.formatar_moeda(p["saldo"]),
                        p["situacao"] + (" (parcial)" if p.get("parcial") else ""),
                        p.get("forma_pagamento") or ""),
            "tag": p["situacao"]} for p in parcelas])

    def _recarregar(self):
        filtro = self._contrato_filtro
        self.atualizar()
        if filtro and filtro in self.contratos:
            self.tab_contratos.tree.selection_set(filtro)

    # ------------------------------------------------------------ contratos
    def _contrato_sel(self) -> dict | None:
        cid = self.tab_contratos.selecionado()
        if not cid:
            ui.aviso("Selecione um serviço na lista de serviços contratados.", parent=self)
            return None
        return self.contratos[cid]

    def _carne(self):
        k = self._contrato_sel()
        if k:
            try:
                recibos.gerar_carne(k["id"], abrir=True)
            except ValueError as e:
                ui.erro(str(e), parent=self)

    def _renovar(self):
        k = self._contrato_sel()
        if not k:
            return
        from app.ui.dialogos.diversos import pedir_numero
        qtd = pedir_numero(self, "Renovar contrato", f"Quantas parcelas/meses adicionar a\n'{k['descricao']}'?", 6)
        if qtd:
            financeiro.renovar_contrato(k["id"], qtd)
            self._recarregar()
            acoes.notificar(self, f"{qtd} parcela(s) adicionada(s).")

    def _status_contrato(self, status: str):
        k = self._contrato_sel()
        if not k:
            return
        texto = {"encerrado": "Encerrar este serviço? As parcelas em aberto CONTINUAM sendo cobradas.",
                 "cancelado": "Cancelar este serviço? As parcelas em aberto SEM pagamento serão canceladas."}[status]
        if ui.confirmar(texto, parent=self):
            financeiro.alterar_status_contrato(k["id"], status, cancelar_abertas=status == "cancelado")
            self._recarregar()

    def _excluir_contrato(self):
        k = self._contrato_sel()
        if k and ui.confirmar(f"Excluir definitivamente '{k['descricao']}' e todas as suas parcelas?",
                              parent=self):
            try:
                financeiro.excluir_contrato(k["id"])
            except ValueError as e:
                ui.erro(str(e), parent=self)
            self.atualizar()

    # ------------------------------------------------------------ parcelas
    def _parcela_sel(self) -> int | None:
        sel = self.tab_parcelas.selecionado()
        if not sel:
            ui.aviso("Selecione uma parcela.", parent=self)
            return None
        return int(sel)

    def _receber(self):
        pid = self._parcela_sel()
        if pid:
            acoes.registrar_pagamento(self, pid, self._recarregar)

    def _quitar(self):
        acoes.quitar_varias(self, self.tab_parcelas.selecionados(), self._recarregar)

    def _recibo(self):
        pid = self._parcela_sel()
        if pid:
            acoes.recibo_da_parcela(self, pid)

    def _editar(self):
        pid = self._parcela_sel()
        if pid:
            acoes.editar_parcela(self, pid, self._recarregar)

    def _cancelar(self):
        pid = self._parcela_sel()
        if pid:
            acoes.cancelar_ou_reabrir_parcela(self, pid, self._recarregar)

    def _todas(self):
        self.tab_contratos.tree.selection_remove(*self.tab_contratos.tree.selection())
        self._carregar_parcelas(todas=True)
