"""
=============================================================================
 ui/dialogos/pagamento.py — Janela "Registrar pagamento"
=============================================================================
 Mostra os dados da parcela e permite lançar o pagamento com:
   • data, valor recebido e forma (PIX, dinheiro, cartão, parcelado…)
   • nº de vezes no cartão (quando a forma permite)
   • desconto, multa/juros e taxa da maquininha
   • opção de gerar o recibo em PDF e mandar confirmação no WhatsApp
 Também contém a janela "Quitar várias parcelas" (pagamento de vários meses).
=============================================================================
"""
from __future__ import annotations

from datetime import timedelta

import customtkinter as ctk

from app.core import config, utils
from app.repositorios import financeiro
from app.ui import componentes as ui
from app.ui.tema import fonte

COR = config.CORES


class DialogoPagamento(ui.DialogoBase):
    def __init__(self, master, parcela_id: int):
        super().__init__(master, "Registrar pagamento", 640, 690)
        self.parcela = financeiro.obter_parcela(parcela_id)
        self.parcela_id = parcela_id
        self._montar()
        self._recalcular()

    # ------------------------------------------------------------------ tela
    def _montar(self):
        p = self.parcela
        c = self.corpo
        c.grid_columnconfigure((0, 1), weight=1)

        # Resumo da parcela
        resumo = ui.Cartao(c)
        resumo.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        resumo.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(resumo, text=p["paciente"], font=fonte(16, "bold"),
                     text_color=COR["primaria_profunda"]).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 0))
        ui.Etiqueta(resumo, p["situacao"]).grid(row=0, column=1, sticky="e", padx=16, pady=(12, 0))
        detalhes = (f"{p['servico']} · {p['rotulo']} · Vencimento {utils.data_br(p['vencimento'])}\n"
                    f"Responsável: {p.get('responsavel') or '—'}\n"
                    f"Valor cheio {utils.formatar_moeda(p['valor'])} · Até o vencimento "
                    f"{utils.formatar_moeda(p['valor_pontualidade'])}")
        if p.get("total_pago"):
            detalhes += f" · Já pago {utils.formatar_moeda(p['total_pago'])}"
        ui.subtitulo(resumo, detalhes).grid(row=1, column=0, columnspan=2, sticky="w", padx=16, pady=(2, 12))

        # Campos
        ui.rotulo(c, "Data do pagamento", True).grid(row=1, column=0, sticky="w")
        ui.rotulo(c, "Forma de pagamento", True).grid(row=1, column=1, sticky="w", padx=(12, 0))
        self.data = ui.CampoData(c, 200)
        self.data.definir(utils.hoje())
        self.data.grid(row=2, column=0, sticky="ew")
        self.data.bind("<FocusOut>", lambda _e: self._recalcular(), add="+")
        self.forma = ui.combo(c, config.FORMAS_PAGAMENTO, 260, comando=lambda _v: self._forma_mudou())
        self.forma.grid(row=2, column=1, sticky="ew", padx=(12, 0))

        ui.rotulo(c, "Valor recebido (R$)", True).grid(row=3, column=0, sticky="w", pady=(10, 0))
        ui.rotulo(c, "Nº de vezes (cartão/cheque)").grid(row=3, column=1, sticky="w", padx=(12, 0), pady=(10, 0))
        self.valor = ui.CampoMoeda(c, 200)
        self.valor.grid(row=4, column=0, sticky="ew")
        self.vezes = ui.combo(c, [str(i) for i in range(1, 13)], 120)
        self.vezes.grid(row=4, column=1, sticky="w", padx=(12, 0))

        ui.rotulo(c, "Desconto concedido (R$)").grid(row=5, column=0, sticky="w", pady=(10, 0))
        ui.rotulo(c, "Multa / juros cobrados (R$)").grid(row=5, column=1, sticky="w", padx=(12, 0), pady=(10, 0))
        self.desconto = ui.CampoMoeda(c, 200)
        self.desconto.grid(row=6, column=0, sticky="ew")
        self.acrescimo = ui.CampoMoeda(c, 200)
        self.acrescimo.grid(row=6, column=1, sticky="ew", padx=(12, 0))

        ui.rotulo(c, "Taxa da maquininha (R$) – opcional").grid(row=7, column=0, sticky="w", pady=(10, 0))
        ui.rotulo(c, "Observações").grid(row=7, column=1, sticky="w", padx=(12, 0), pady=(10, 0))
        self.taxa = ui.CampoMoeda(c, 200)
        self.taxa.grid(row=8, column=0, sticky="ew")
        self.obs = ui.Campo(c, 200, placeholder_text="Ex.: comprovante enviado no WhatsApp")
        self.obs.grid(row=8, column=1, sticky="ew", padx=(12, 0))

        self.aviso = ctk.CTkLabel(c, text="", font=fonte(12, "bold"), text_color=COR["primaria_profunda"],
                                  fg_color=COR["primaria_suave"], corner_radius=10, height=40,
                                  justify="left", anchor="w")
        self.aviso.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(14, 6))

        opcoes = ctk.CTkFrame(c, fg_color="transparent")
        opcoes.grid(row=10, column=0, columnspan=2, sticky="w")
        self.var_quitar = ctk.StringVar(value="auto")
        ctk.CTkRadioButton(opcoes, text="Quitar automaticamente se cobrir o saldo", variable=self.var_quitar,
                           value="auto", font=fonte(12)).grid(row=0, column=0, sticky="w", pady=2)
        ctk.CTkRadioButton(opcoes, text="Considerar a parcela QUITADA (acordo)", variable=self.var_quitar,
                           value="sim", font=fonte(12)).grid(row=1, column=0, sticky="w", pady=2)
        ctk.CTkRadioButton(opcoes, text="Pagamento parcial (manter em aberto)", variable=self.var_quitar,
                           value="nao", font=fonte(12)).grid(row=2, column=0, sticky="w", pady=2)
        self.var_recibo = ctk.BooleanVar(value=True)
        self.var_whats = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(opcoes, text="Gerar recibo em PDF", variable=self.var_recibo,
                        font=fonte(12)).grid(row=0, column=1, sticky="w", padx=(28, 0))
        ctk.CTkCheckBox(opcoes, text="Enviar confirmação no WhatsApp", variable=self.var_whats,
                        font=fonte(12)).grid(row=1, column=1, sticky="w", padx=(28, 0))

        self.rodape.grid_columnconfigure(0, weight=1)
        ui.botao(self.rodape, "Cancelar", self.fechar, "secundario").grid(row=0, column=1, padx=(0, 8))
        ui.botao(self.rodape, "✔  Confirmar pagamento", self._confirmar, "primario", 200).grid(row=0, column=2)
        self._forma_mudou()

    # ---------------------------------------------------------------- lógica
    def _forma_mudou(self):
        permite = self.forma.get() in config.FORMAS_COM_PARCELAS
        self.vezes.configure(state="readonly" if permite else "disabled")
        if not permite:
            ui.definir_combo(self.vezes, "1")

    def _recalcular(self):
        """Atualiza o valor sugerido conforme a data (pontualidade x valor cheio)."""
        try:
            data = self.data.data() or utils.hoje()
        except ValueError:
            return
        p = financeiro.obter_parcela(self.parcela_id, data_ref=data)
        self.valor.definir(p["saldo"])
        self.acrescimo.definir(p["encargos"] if p["encargos"] else "")
        limite = utils.para_date(p["vencimento"]) + timedelta(days=financeiro.regras()["tolerancia"])
        if data <= limite:
            txt = f"  Pago até o vencimento: valor com desconto de pontualidade → {utils.formatar_moeda(p['saldo'])}"
        else:
            txt = (f"  Após o vencimento ({(data - utils.para_date(p['vencimento'])).days} dias): "
                   f"valor devido {utils.formatar_moeda(p['saldo'])}")
        self.aviso.configure(text=txt)

    def _confirmar(self):
        try:
            data = self.data.data()
            if not data:
                raise ValueError("Informe a data do pagamento.")
            quitar = {"auto": None, "sim": True, "nao": False}[self.var_quitar.get()]
            resultado = financeiro.registrar_pagamento(
                self.parcela_id, data, self.valor.numero(), self.forma.get(),
                int(self.vezes.get() or 1), self.desconto.numero(), self.acrescimo.numero(),
                self.taxa.numero(), self.obs.valor(), quitar)
        except ValueError as e:
            ui.erro(str(e), parent=self)
            return
        resultado["gerar_recibo"] = self.var_recibo.get()
        resultado["enviar_whatsapp"] = self.var_whats.get()
        self.fechar(resultado)


class DialogoQuitarVarias(ui.DialogoBase):
    """Quita várias parcelas de uma só vez (mesma data e forma de pagamento)."""
    def __init__(self, master, parcelas: list[dict]):
        super().__init__(master, "Quitar várias parcelas", 560, 470)
        self.parcelas = [p for p in parcelas if p["status"] == "aberta"]
        c = self.corpo
        c.grid_columnconfigure((0, 1), weight=1)
        total = sum(p["saldo"] for p in self.parcelas)
        linhas = "\n".join(f"• {p['paciente']} – {p['servico']} ({p['rotulo']}) – {utils.formatar_moeda(p['saldo'])}"
                           for p in self.parcelas[:8])
        if len(self.parcelas) > 8:
            linhas += f"\n… e mais {len(self.parcelas) - 8} parcela(s)"
        ui.subtitulo(c, linhas or "Nenhuma parcela em aberto selecionada.").grid(
            row=0, column=0, columnspan=2, sticky="w")
        ctk.CTkLabel(c, text=f"Total: {utils.formatar_moeda(total)}", font=fonte(18, "bold"),
                     text_color=COR["primaria_profunda"]).grid(row=1, column=0, columnspan=2, sticky="w", pady=10)
        ui.rotulo(c, "Data do pagamento", True).grid(row=2, column=0, sticky="w")
        ui.rotulo(c, "Forma de pagamento", True).grid(row=2, column=1, sticky="w", padx=(12, 0))
        self.data = ui.CampoData(c, 180)
        self.data.definir(utils.hoje())
        self.data.grid(row=3, column=0, sticky="ew")
        self.forma = ui.combo(c, config.FORMAS_PAGAMENTO, 240)
        self.forma.grid(row=3, column=1, sticky="ew", padx=(12, 0))
        ui.rotulo(c, "Nº de vezes (cartão)").grid(row=4, column=0, sticky="w", pady=(10, 0))
        self.vezes = ui.combo(c, [str(i) for i in range(1, 13)], 120)
        self.vezes.grid(row=5, column=0, sticky="w")
        self.var_recibo = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(c, text="Gerar recibos em PDF", variable=self.var_recibo,
                        font=fonte(12)).grid(row=5, column=1, sticky="w", padx=(12, 0))
        self.rodape.grid_columnconfigure(0, weight=1)
        ui.botao(self.rodape, "Cancelar", self.fechar, "secundario").grid(row=0, column=1, padx=(0, 8))
        ui.botao(self.rodape, "✔  Quitar todas", self._confirmar, "primario", 170).grid(row=0, column=2)

    def _confirmar(self):
        if not self.parcelas:
            self.fechar()
            return
        try:
            data = self.data.data()
            if not data:
                raise ValueError("Informe a data do pagamento.")
            resultados = financeiro.quitar_varias([p["id"] for p in self.parcelas], data,
                                                  self.forma.get(), int(self.vezes.get() or 1))
        except ValueError as e:
            ui.erro(str(e), parent=self)
            return
        self.fechar({"resultados": resultados, "gerar_recibo": self.var_recibo.get()})
