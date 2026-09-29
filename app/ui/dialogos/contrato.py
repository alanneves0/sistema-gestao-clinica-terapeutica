"""
=============================================================================
 ui/dialogos/contrato.py — Janela "Incluir serviço / contrato"
=============================================================================
 Aqui se contrata um serviço para o paciente (ex.: Fonoaudiologia por 6 meses).
 Ao escolher o serviço, os valores da tabela de preços são preenchidos
 automaticamente, mas podem ser ajustados (desconto, nº de parcelas…).
 À direita aparece a SIMULAÇÃO das parcelas antes de salvar.
=============================================================================
"""
from __future__ import annotations

from datetime import date

import customtkinter as ctk

from app.core import config, utils
from app.repositorios import financeiro, servicos
from app.servicos import recibos
from app.ui import componentes as ui
from app.ui.tema import fonte

COR = config.CORES


def proximo_vencimento(dia: int, base: date | None = None) -> date:
    """Próxima data com o dia de vencimento escolhido (este mês ou o próximo)."""
    base = base or utils.hoje()
    candidato = utils.adicionar_meses(date(base.year, base.month, 1), 0, dia)
    return candidato if candidato >= base else utils.adicionar_meses(candidato, 1, dia)


class DialogoContrato(ui.DialogoBase):
    def __init__(self, master, paciente_id: int, nome_paciente: str = ""):
        super().__init__(master, f"Incluir serviço – {nome_paciente}".strip(" –"), 1060, 720)
        self.paciente_id = paciente_id
        self.lista_servicos = servicos.listar(somente_ativos=True)
        self.simulacao: list[dict] = []
        self._montar()
        if self.lista_servicos:
            self._servico_mudou(self.lista_servicos[0]["nome"])

    # ------------------------------------------------------------------ tela
    def _montar(self):
        c = self.corpo
        c.grid_columnconfigure(1, weight=1)
        c.grid_rowconfigure(0, weight=1)

        form = ctk.CTkScrollableFrame(c, fg_color="transparent", width=430)
        form.grid(row=0, column=0, sticky="nsw", padx=(0, 16))
        form.grid_columnconfigure((0, 1), weight=1)

        ui.rotulo(form, "Serviço", True).grid(row=0, column=0, columnspan=2, sticky="w")
        self.servico = ui.combo(form, [s["nome"] for s in self.lista_servicos], 400, self._servico_mudou)
        self.servico.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.info_servico = ui.subtitulo(form, "", 11)
        self.info_servico.configure(wraplength=400)
        self.info_servico.grid(row=2, column=0, columnspan=2, sticky="w", pady=(2, 8))

        ui.rotulo(form, "Forma de contratação").grid(row=3, column=0, columnspan=2, sticky="w")
        self.modalidade = ctk.CTkSegmentedButton(form, values=list(config.MODALIDADES.values()),
                                                 command=lambda _v: self._simular(), font=fonte(12))
        self.modalidade.set(config.MODALIDADES[config.MODALIDADE_PARCELADO])
        self.modalidade.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        ui.rotulo(form, "Nº de parcelas / meses", True).grid(row=5, column=0, sticky="w")
        ui.rotulo(form, "Dia do vencimento", True).grid(row=5, column=1, sticky="w", padx=(10, 0))
        self.num_parcelas = ui.combo(form, [str(i) for i in range(1, 25)], 180,
                                     lambda _v: self._simular(), editavel=True)
        self.num_parcelas.grid(row=6, column=0, sticky="ew")
        self.dia = ui.combo(form, config.DIAS_VENCIMENTO, 180, self._dia_mudou, editavel=True, valor_inicial="10")
        self.dia.grid(row=6, column=1, sticky="ew", padx=(10, 0))

        ui.rotulo(form, "1º vencimento", True).grid(row=7, column=0, sticky="w", pady=(8, 0))
        ui.rotulo(form, "Desconto especial (%)").grid(row=7, column=1, sticky="w", padx=(10, 0), pady=(8, 0))
        self.primeiro_venc = ui.CampoData(form, 180)
        self.primeiro_venc.definir(proximo_vencimento(10))
        self.primeiro_venc.grid(row=8, column=0, sticky="ew")
        self.desconto = ui.Campo(form, 180, placeholder_text="0")
        self.desconto.grid(row=8, column=1, sticky="ew", padx=(10, 0))

        self.lbl_valor = ui.rotulo(form, "Valor da mensalidade (R$)", True)
        self.lbl_valor.grid(row=9, column=0, sticky="w", pady=(8, 0))
        ui.rotulo(form, "Valor até o vencimento (R$)").grid(row=9, column=1, sticky="w", padx=(10, 0), pady=(8, 0))
        self.valor_cheio = ui.CampoMoeda(form, 180)
        self.valor_cheio.grid(row=10, column=0, sticky="ew")
        self.valor_pont = ui.CampoMoeda(form, 180)
        self.valor_pont.grid(row=10, column=1, sticky="ew", padx=(10, 0))

        ui.rotulo(form, "Entrada / 1ª parcela (R$)").grid(row=11, column=0, sticky="w", pady=(8, 0))
        self.entrada = ui.CampoMoeda(form, 180)
        self.entrada.grid(row=12, column=0, sticky="ew")

        ui.rotulo(form, "Profissional").grid(row=13, column=0, sticky="w", pady=(8, 0))
        ui.rotulo(form, "Horário").grid(row=13, column=1, sticky="w", padx=(10, 0), pady=(8, 0))
        self.profissional = ui.Campo(form, 180)
        self.profissional.grid(row=14, column=0, sticky="ew")
        self.horario = ui.Campo(form, 180, placeholder_text="Ex.: 14h às 15h")
        self.horario.grid(row=14, column=1, sticky="ew", padx=(10, 0))

        ui.rotulo(form, "Dias de atendimento").grid(row=15, column=0, columnspan=2, sticky="w", pady=(8, 0))
        dias = ctk.CTkFrame(form, fg_color="transparent")
        dias.grid(row=16, column=0, columnspan=2, sticky="w")
        self.vars_dias = {}
        for i, d in enumerate(config.DIAS_SEMANA):
            v = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(dias, text=d[:3], variable=v, width=60, font=fonte(11)).grid(
                row=0, column=i, padx=(0, 4))
            self.vars_dias[d] = v

        ui.rotulo(form, "Observações").grid(row=17, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.obs = ui.Campo(form, 380)
        self.obs.grid(row=18, column=0, columnspan=2, sticky="ew")

        self.var_adesao = ctk.BooleanVar(value=False)
        self.var_carne = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(form, text="Cobrar também a Taxa de Adesão", variable=self.var_adesao,
                        font=fonte(12)).grid(row=19, column=0, columnspan=2, sticky="w", pady=(12, 2))
        ctk.CTkCheckBox(form, text="Gerar carnê em PDF ao salvar", variable=self.var_carne,
                        font=fonte(12)).grid(row=20, column=0, columnspan=2, sticky="w", pady=2)

        for campo in (self.primeiro_venc, self.desconto, self.valor_cheio, self.valor_pont, self.entrada):
            campo.bind("<FocusOut>", lambda _e: self._simular(), add="+")
            campo.bind("<Return>", lambda _e: self._simular(), add="+")

        # ---- Simulação (lado direito)
        direita = ctk.CTkFrame(c, fg_color="transparent")
        direita.grid(row=0, column=1, sticky="nsew")
        direita.grid_columnconfigure(0, weight=1)
        direita.grid_rowconfigure(1, weight=1)
        ui.titulo(direita, "Simulação das parcelas", 15).grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.tabela = ui.Tabela(direita, [("n", "Parcela", 80, "center"), ("venc", "Vencimento", 110, "center"),
                                          ("valor", "Valor cheio", 110, "e"),
                                          ("pont", "Até o venc.", 110, "e")], altura=14)
        self.tabela.grid(row=1, column=0, sticky="nsew")
        self.lbl_total = ctk.CTkLabel(direita, text="", font=fonte(15, "bold"),
                                      text_color=COR["primaria_profunda"], anchor="w", justify="left")
        self.lbl_total.grid(row=2, column=0, sticky="w", pady=(8, 0))

        self.rodape.grid_columnconfigure(0, weight=1)
        ui.botao(self.rodape, "Cancelar", self.fechar, "secundario").grid(row=0, column=1, padx=(0, 8))
        ui.botao(self.rodape, "✔  Salvar contrato", self._salvar, "primario", 180).grid(row=0, column=2)

    # ---------------------------------------------------------------- lógica
    def _servico_atual(self) -> dict | None:
        nome = self.servico.get()
        return next((s for s in self.lista_servicos if s["nome"] == nome), None)

    def _servico_mudou(self, _nome=None):
        s = self._servico_atual()
        if not s:
            return
        self.info_servico.configure(text=f"{config.TIPOS_COBRANCA[s['tipo_cobranca']]} · "
                                         f"{s.get('descricao') or ''}")
        ui.definir_combo(self.num_parcelas, str(s["parcelas_padrao"]))
        self.valor_cheio.definir(s["valor_cheio"])
        self.valor_pont.definir(s["valor_pontualidade"])
        self.entrada.definir(s["valor_entrada"] or "")
        self.lbl_valor.configure(text="Valor da mensalidade (R$) *" if s["tipo_cobranca"] == config.TIPO_MENSAL
                                 else "Valor TOTAL (R$) *")
        estado = "normal" if s["tipo_cobranca"] == config.TIPO_PARCELADO else "disabled"
        self.entrada.configure(state=estado)
        self._simular()

    def _dia_mudou(self, valor):
        try:
            dia = int(valor)
            self.primeiro_venc.definir(proximo_vencimento(dia))
        except ValueError:
            pass
        self._simular()

    def _parametros(self) -> dict:
        s = self._servico_atual()
        if not s:
            raise ValueError("Escolha um serviço.")
        modalidade = next(k for k, v in config.MODALIDADES.items() if v == self.modalidade.get())
        dia = int(self.dia.get())
        if not 1 <= dia <= 31:
            raise ValueError("Dia de vencimento deve estar entre 1 e 31.")
        primeiro = self.primeiro_venc.data()
        if not primeiro:
            raise ValueError("Informe o 1º vencimento.")
        desconto = float((self.desconto.get() or "0").replace(",", ".").replace("%", ""))
        if not 0 <= desconto < 100:
            raise ValueError("Desconto deve estar entre 0 e 99%.")
        return dict(tipo_cobranca=s["tipo_cobranca"], modalidade=modalidade,
                    valor_cheio=self.valor_cheio.numero(),
                    valor_pontualidade=self.valor_pont.numero() or self.valor_cheio.numero(),
                    num_parcelas=int(self.num_parcelas.get()),
                    valor_entrada=self.entrada.numero() if s["tipo_cobranca"] == config.TIPO_PARCELADO else 0,
                    primeiro_vencimento=primeiro, dia_vencimento=dia, desconto_percentual=desconto)

    def _simular(self):
        try:
            self.simulacao = financeiro.simular_parcelas(**self._parametros())
        except (ValueError, ZeroDivisionError) as e:
            self.simulacao = []
            self.lbl_total.configure(text=f"⚠ {e}")
            self.tabela.carregar([])
            return
        n = len(self.simulacao)
        self.tabela.carregar([{
            "iid": p["numero"],
            "valores": (f"{p['numero']:02d}/{n:02d}", utils.data_br(p["vencimento"]),
                        utils.formatar_moeda(p["valor"]), utils.formatar_moeda(p["valor_pontualidade"]))}
            for p in self.simulacao])
        total_pont = sum(p["valor_pontualidade"] for p in self.simulacao)
        total_cheio = sum(p["valor"] for p in self.simulacao)
        texto = f"Total: {utils.formatar_moeda(total_pont)}"
        if abs(total_cheio - total_pont) > 0.009:
            texto += f"   (sem pontualidade: {utils.formatar_moeda(total_cheio)})"
        self.lbl_total.configure(text=texto)

    def _salvar(self):
        self._simular()
        if not self.simulacao:
            ui.erro("Confira os dados: não foi possível calcular as parcelas.", parent=self)
            return
        s = self._servico_atual()
        params = self._parametros()
        descricao = s["nome"]
        if params["modalidade"] == config.MODALIDADE_A_VISTA and s["tipo_cobranca"] == config.TIPO_MENSAL:
            descricao += f" – {params['num_parcelas']} meses à vista"
        dias = ", ".join(d for d, v in self.vars_dias.items() if v.get())
        try:
            contrato_id = financeiro.criar_contrato(
                self.paciente_id, s["id"], descricao, params["modalidade"], params["dia_vencimento"],
                self.simulacao, params["desconto_percentual"], utils.hoje(), self.profissional.valor(),
                dias, self.horario.valor(), self.obs.valor())
            if self.var_adesao.get():
                taxa = next((x for x in servicos.listar(True) if x["tipo_cobranca"] == config.TIPO_UNICO), None)
                if taxa:
                    financeiro.criar_contrato(
                        self.paciente_id, taxa["id"], taxa["nome"], config.MODALIDADE_A_VISTA,
                        params["dia_vencimento"],
                        [{"numero": 1, "vencimento": params["primeiro_vencimento"],
                          "valor": taxa["valor_cheio"], "valor_pontualidade": taxa["valor_pontualidade"]}])
            if self.var_carne.get():
                recibos.gerar_carne(contrato_id, abrir=True)
        except ValueError as e:
            ui.erro(str(e), parent=self)
            return
        self.fechar(contrato_id)
