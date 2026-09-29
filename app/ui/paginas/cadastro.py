"""
=============================================================================
 ui/paginas/cadastro.py — Cadastro (novo / edição) de paciente
=============================================================================
 Formulário dividido em 4 abas:
   1. Paciente        → identificação, contato, escola/trabalho, convênio
   2. Responsável     → responsável financeiro/legal + endereço
   3. Clínico         → diagnósticos (TEA, TDAH…), CID, medicações, queixa
   4. Emergência      → contato de emergência, autorização de imagem, LGPD
 Campos com * são obrigatórios.
=============================================================================
"""
from __future__ import annotations

import json
import threading
import urllib.request

import customtkinter as ctk

from app.core import config, utils
from app.repositorios import pacientes
from app.ui import acoes
from app.ui import componentes as ui
from app.ui.paginas.base import Pagina
from app.ui.tema import fonte

COR = config.CORES


class PaginaCadastro(Pagina):
    TITULO = "Cadastro de paciente"
    SUBTITULO = "Preencha os dados do paciente e do responsável. Campos com * são obrigatórios."

    def __init__(self, master, app):
        super().__init__(master, app)
        self.paciente_id: int | None = None
        self.responsavel_id: int | None = None
        self.cp: dict = {}   # campos do paciente   {coluna_do_banco: widget}
        self.cr: dict = {}   # campos do responsável

        c = self.conteudo
        c.grid_columnconfigure(0, weight=1)
        c.grid_rowconfigure(0, weight=1)
        self.abas = ctk.CTkTabview(c, fg_color=COR["superficie"], corner_radius=14, border_width=1,
                                   border_color=COR["borda"],
                                   segmented_button_fg_color=COR["primaria_clara"],
                                   segmented_button_selected_color=COR["primaria"],
                                   segmented_button_selected_hover_color=COR["primaria_escura"],
                                   segmented_button_unselected_color=COR["primaria_clara"],
                                   segmented_button_unselected_hover_color="#C8DFE0",
                                   text_color=COR["primaria_profunda"])
        self.abas.grid(row=0, column=0, sticky="nsew")
        for nome in ("1. Paciente", "2. Responsável e endereço", "3. Informações clínicas",
                     "4. Emergência e autorizações"):
            self.abas.add(nome)
        self._aba_paciente(self._rolavel("1. Paciente"))
        self._aba_responsavel(self._rolavel("2. Responsável e endereço"))
        self._aba_clinica(self._rolavel("3. Informações clínicas"))
        self._aba_emergencia(self._rolavel("4. Emergência e autorizações"))

        rodape = ctk.CTkFrame(c, fg_color="transparent")
        rodape.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        rodape.grid_columnconfigure(0, weight=1)
        self.lbl_status = ui.subtitulo(rodape, "")
        self.lbl_status.grid(row=0, column=0, sticky="w")
        ui.botao(rodape, "Voltar à lista", lambda: self.app.mostrar("pacientes"), "fantasma", 120).grid(row=0, column=1, padx=4)
        ui.botao(rodape, "Limpar / Novo", lambda: self.atualizar(), "secundario", 130).grid(row=0, column=2, padx=4)
        ui.botao(rodape, "Salvar e incluir serviço", lambda: self._salvar(True), "destaque", 200).grid(row=0, column=3, padx=4)
        ui.botao(rodape, "✔  Salvar", lambda: self._salvar(False), "primario", 130).grid(row=0, column=4, padx=(4, 0))

    # ------------------------------------------------------------ utilidades
    def _rolavel(self, aba: str) -> ctk.CTkScrollableFrame:
        frame = ctk.CTkScrollableFrame(self.abas.tab(aba), fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=6, pady=6)
        for i in range(4):
            frame.grid_columnconfigure(i, weight=1, uniform="col")
        return frame

    def _secao(self, pai, texto: str, linha: int):
        ctk.CTkLabel(pai, text=texto, font=fonte(14, "bold"), text_color=COR["destaque_escuro"],
                     anchor="w").grid(row=linha, column=0, columnspan=4, sticky="w", pady=(14, 4), padx=6)

    def _campo(self, pai, destino: dict, chave: str, rotulo: str, linha: int, coluna: int,
               tipo: str = "texto", colspan: int = 1, obrigatorio: bool = False, valores=None,
               placeholder: str = ""):
        """Cria rótulo + campo e guarda o campo em destino[chave]."""
        ui.rotulo(pai, rotulo, obrigatorio).grid(row=linha, column=coluna, columnspan=colspan,
                                                 sticky="w", padx=6, pady=(6, 0))
        if tipo == "data":
            w = ui.CampoData(pai, 150)
        elif tipo == "cpf":
            w = ui.CampoCPF(pai, 150)
        elif tipo == "tel":
            w = ui.CampoTelefone(pai, 150)
        elif tipo == "combo":
            w = ui.combo(pai, valores or [], 150)
        elif tipo == "combo_edit":
            w = ui.combo(pai, valores or [], 150, editavel=True, valor_inicial="")
        elif tipo == "longo":
            w = ctk.CTkTextbox(pai, height=70, corner_radius=9, border_width=1, font=fonte(12), wrap="word")
        else:
            w = ui.Campo(pai, 150, placeholder_text=placeholder)
        w.grid(row=linha + 1, column=coluna, columnspan=colspan, sticky="ew", padx=6)
        destino[chave] = w
        return w

    # ------------------------------------------------------------ abas
    def _aba_paciente(self, f):
        self._secao(f, "Identificação", 0)
        self._campo(f, self.cp, "nome", "Nome completo", 1, 0, colspan=2, obrigatorio=True)
        self._campo(f, self.cp, "nome_social", "Nome social / como gosta de ser chamado", 1, 2, colspan=2)
        nasc = self._campo(f, self.cp, "data_nascimento", "Data de nascimento", 3, 0, "data", obrigatorio=True)
        nasc.bind("<FocusOut>", lambda _e: self._mostrar_idade(), add="+")
        self.lbl_idade = ctk.CTkLabel(f, text="", font=fonte(12, "bold"), text_color=COR["primaria_escura"])
        self.lbl_idade.grid(row=4, column=1, sticky="w", padx=6)
        self._campo(f, self.cp, "sexo", "Sexo", 3, 2, "combo", valores=config.SEXOS)
        self._campo(f, self.cp, "cpf", "CPF", 5, 0, "cpf")
        self._campo(f, self.cp, "rg", "RG / Certidão de nascimento", 5, 1)
        self._campo(f, self.cp, "cartao_sus", "Cartão SUS", 5, 2)

        self._secao(f, "Contato do paciente (adolescentes e adultos)", 7)
        self._campo(f, self.cp, "whatsapp", "WhatsApp", 8, 0, "tel")
        self._campo(f, self.cp, "telefone", "Telefone", 8, 1, "tel")
        self._campo(f, self.cp, "email", "E-mail", 8, 2, colspan=2)

        self._secao(f, "Escola / trabalho", 10)
        self._campo(f, self.cp, "escola", "Escola", 11, 0, colspan=2)
        self._campo(f, self.cp, "serie", "Série / ano", 11, 2)
        self._campo(f, self.cp, "turno", "Turno", 11, 3, "combo", valores=config.TURNOS)
        self._campo(f, self.cp, "ocupacao", "Ocupação / profissão (adultos)", 13, 0, colspan=2)

        self._secao(f, "Convênio", 15)
        self._campo(f, self.cp, "convenio", "Convênio / plano de saúde", 16, 0, colspan=2,
                    placeholder="Particular")
        self._campo(f, self.cp, "num_carteirinha", "Nº da carteirinha", 16, 2)

    def _aba_responsavel(self, f):
        self.var_proprio = ctk.BooleanVar(value=False)
        topo = ctk.CTkFrame(f, fg_color="transparent")
        topo.grid(row=0, column=0, columnspan=4, sticky="ew", padx=6, pady=(6, 0))
        ctk.CTkSwitch(topo, text="O paciente é o próprio responsável (adulto que paga o tratamento)",
                      variable=self.var_proprio, command=self._proprio_mudou, font=fonte(12)).pack(side="left")
        ui.botao(topo, "Usar responsável já cadastrado (irmãos)", self._escolher_responsavel,
                 "secundario", 290).pack(side="right")

        self._secao(f, "Responsável financeiro / legal", 1)
        self._campo(f, self.cr, "nome", "Nome completo", 2, 0, colspan=2, obrigatorio=True)
        self._campo(f, self.cr, "parentesco", "Parentesco", 2, 2, "combo_edit", valores=config.PARENTESCOS)
        self._campo(f, self.cr, "data_nascimento", "Data de nascimento", 2, 3, "data")
        self._campo(f, self.cr, "cpf", "CPF", 4, 0, "cpf")
        self._campo(f, self.cr, "rg", "RG", 4, 1)
        self._campo(f, self.cr, "profissao", "Profissão", 4, 2, colspan=2)

        self._secao(f, "Contato (usado nas cobranças por WhatsApp)", 6)
        self._campo(f, self.cr, "whatsapp", "WhatsApp", 7, 0, "tel", obrigatorio=True)
        self._campo(f, self.cr, "telefone", "Telefone", 7, 1, "tel")
        self._campo(f, self.cr, "telefone_alt", "Outro telefone", 7, 2, "tel")
        self._campo(f, self.cr, "email", "E-mail", 7, 3)

        self._secao(f, "Endereço", 9)
        cep = self._campo(f, self.cr, "cep", "CEP (Enter busca o endereço)", 10, 0)
        cep.bind("<Return>", lambda _e: self._buscar_cep())
        self._campo(f, self.cr, "logradouro", "Rua / avenida", 10, 1, colspan=2)
        self._campo(f, self.cr, "numero", "Número", 10, 3)
        self._campo(f, self.cr, "complemento", "Complemento", 12, 0)
        self._campo(f, self.cr, "bairro", "Bairro", 12, 1)
        self._campo(f, self.cr, "cidade", "Cidade", 12, 2)
        self._campo(f, self.cr, "uf", "UF", 12, 3, "combo", valores=config.UFS)
        self._campo(f, self.cr, "observacoes", "Observações sobre o responsável", 14, 0, "longo", colspan=4)

    def _aba_clinica(self, f):
        self._secao(f, "Diagnósticos / hipóteses", 0)
        grade = ctk.CTkFrame(f, fg_color="transparent")
        grade.grid(row=1, column=0, columnspan=4, sticky="ew", padx=6)
        self.vars_diag: dict[str, ctk.BooleanVar] = {}
        for i, d in enumerate(config.DIAGNOSTICOS):
            v = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(grade, text=d, variable=v, font=fonte(12)).grid(
                row=i // 4, column=i % 4, sticky="w", padx=(0, 18), pady=4)
            self.vars_diag[d] = v
        self._campo(f, self.cp, "cid", "CID(s)", 2, 0, placeholder="Ex.: F84.0, F90.0")
        self._campo(f, self.cp, "nivel_suporte", "Nível de suporte (TEA)", 2, 1, "combo",
                    valores=config.NIVEIS_SUPORTE_TEA)
        self.var_laudo = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(f, text="Possui laudo", variable=self.var_laudo, font=fonte(12)).grid(
            row=3, column=2, sticky="w", padx=6)
        self._campo(f, self.cp, "medico_responsavel", "Médico(a) que acompanha", 4, 0, colspan=2)
        self._campo(f, self.cp, "encaminhado_por", "Encaminhado por", 4, 2, colspan=2)
        self._campo(f, self.cp, "medicacoes", "Medicações em uso", 6, 0, "longo", colspan=2)
        self._campo(f, self.cp, "alergias", "Alergias / restrições", 6, 2, "longo", colspan=2)
        self._campo(f, self.cp, "queixa_principal", "Queixa principal / motivo da procura", 8, 0, "longo", colspan=4)
        self._campo(f, self.cp, "observacoes", "Observações gerais", 10, 0, "longo", colspan=4)

    def _aba_emergencia(self, f):
        self._secao(f, "Contato de emergência", 0)
        self._campo(f, self.cp, "emergencia_nome", "Nome", 1, 0, colspan=2)
        self._campo(f, self.cp, "emergencia_parentesco", "Parentesco", 1, 2, "combo_edit", valores=config.PARENTESCOS)
        self._campo(f, self.cp, "emergencia_telefone", "Telefone", 1, 3, "tel")

        self._secao(f, "Autorizações", 3)
        self.var_imagem = ctk.BooleanVar(value=False)
        self.var_lgpd = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(f, text="Autoriza o uso de imagem (fotos/vídeos) para fins terapêuticos e de divulgação",
                        variable=self.var_imagem, font=fonte(12)).grid(row=4, column=0, columnspan=4, sticky="w", padx=6, pady=6)
        ctk.CTkCheckBox(f, text="Consentimento LGPD: autoriza o armazenamento dos dados pessoais e de saúde "
                                "para o atendimento",
                        variable=self.var_lgpd, font=fonte(12)).grid(row=5, column=0, columnspan=4, sticky="w", padx=6, pady=6)
        ui.subtitulo(f, "Os dados ficam guardados somente neste computador, no banco de dados local do sistema.",
                     11).grid(row=6, column=0, columnspan=4, sticky="w", padx=6)
        ativo = ctk.CTkFrame(f, fg_color="transparent")
        ativo.grid(row=7, column=0, columnspan=4, sticky="w", padx=6, pady=(16, 0))
        self.var_ativo = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(ativo, text="Paciente ativo (em atendimento)", variable=self.var_ativo,
                      font=fonte(12)).pack(side="left")

    # ------------------------------------------------------------ comportamento
    def _mostrar_idade(self):
        try:
            nasc = self.cp["data_nascimento"].data()
        except ValueError:
            self.lbl_idade.configure(text="⚠ data inválida", text_color=COR["atraso"])
            return
        if nasc:
            self.lbl_idade.configure(text=f"{utils.texto_idade(nasc)} · {utils.faixa_etaria(nasc)}",
                                     text_color=COR["primaria_escura"])
            if utils.calcular_idade(nasc) >= 18 and not self.paciente_id and not self.cr["nome"].get():
                self.lbl_status.configure(text="Paciente adulto: se ele mesmo paga o tratamento, marque "
                                               "'o paciente é o próprio responsável' na aba 2.")
        else:
            self.lbl_idade.configure(text="")

    def _proprio_mudou(self):
        estado = "disabled" if self.var_proprio.get() else "normal"
        for chave in ("nome", "cpf", "rg", "data_nascimento", "whatsapp", "telefone", "email"):
            if estado == "disabled":
                ui.definir_texto(self.cr[chave], "")
            self.cr[chave].configure(state=estado)
        if self.var_proprio.get():
            self.lbl_status.configure(text="Os dados pessoais e o WhatsApp do responsável serão os do paciente (aba 1).")

    def _escolher_responsavel(self):
        from app.ui.dialogos.diversos import DialogoResponsavel
        r = DialogoResponsavel(self).aguardar()
        if not r:
            return
        self.var_proprio.set(False)
        self._proprio_mudou()
        self.responsavel_id = r["id"]
        self._preencher(self.cr, r)
        self.lbl_status.configure(text=f"Vinculado ao responsável já cadastrado: {r['nome']}")

    def _buscar_cep(self):
        """Busca o endereço pelo CEP (precisa de internet; se falhar, preencha à mão)."""
        cep = utils.somente_digitos(self.cr["cep"].get())
        if len(cep) != 8:
            return
        self.lbl_status.configure(text="Buscando CEP…")

        def tarefa():
            try:
                with urllib.request.urlopen(f"https://viacep.com.br/ws/{cep}/json/", timeout=6) as r:
                    dados = json.loads(r.read().decode("utf-8"))
            except Exception:  # noqa: BLE001
                dados = {"erro": True}
            self.after(0, lambda: self._aplicar_cep(dados))
        threading.Thread(target=tarefa, daemon=True).start()

    def _aplicar_cep(self, dados: dict):
        if dados.get("erro"):
            self.lbl_status.configure(text="CEP não encontrado (ou sem internet). Preencha o endereço manualmente.")
            return
        for campo, chave in (("logradouro", "logradouro"), ("bairro", "bairro"), ("cidade", "localidade")):
            ui.definir_texto(self.cr[campo], dados.get(chave, ""))
        ui.definir_combo(self.cr["uf"], dados.get("uf", ""))
        self.lbl_status.configure(text="Endereço preenchido pelo CEP ✔")

    # ------------------------------------------------------------ ler / escrever
    def _ler(self, campos: dict) -> dict:
        dados = {}
        for chave, w in campos.items():
            if isinstance(w, ctk.CTkTextbox):
                dados[chave] = w.get("1.0", "end-1c").strip()
            elif isinstance(w, ui.CampoData):
                dados[chave] = w.data()  # pode lançar ValueError (data inválida)
            else:
                dados[chave] = w.get().strip()
        return dados

    def _preencher(self, campos: dict, dados: dict):
        for chave, w in campos.items():
            valor = dados.get(chave) or ""
            if isinstance(w, ctk.CTkTextbox):
                w.delete("1.0", "end")
                w.insert("1.0", valor)
            elif isinstance(w, ctk.CTkComboBox):
                ui.definir_combo(w, valor)
            elif isinstance(w, ui.CampoData):
                w.definir(valor)
            else:
                ui.definir_texto(w, valor)

    def atualizar(self, paciente_id: int | None = None, **_kwargs):
        """Abre o formulário vazio (novo) ou com os dados do paciente (edição)."""
        self.paciente_id = paciente_id
        self.responsavel_id = None
        self.var_proprio.set(False)
        self._proprio_mudou()
        p = pacientes.obter(paciente_id) if paciente_id else {}
        r = (p or {}).get("responsavel") or {}
        self._preencher(self.cp, p or {})
        self._preencher(self.cr, r)
        diags = [d.strip() for d in ((p or {}).get("diagnosticos") or "").split(";")]
        for d, v in self.vars_diag.items():
            v.set(d in diags)
        self.var_laudo.set(bool((p or {}).get("laudo")))
        self.var_imagem.set(bool((p or {}).get("autoriza_imagem")))
        self.var_lgpd.set(bool((p or {}).get("consentimento_lgpd")))
        self.var_ativo.set(bool((p or {}).get("ativo", 1)))
        if p:
            self.responsavel_id = p.get("responsavel_id")
            if p.get("proprio_responsavel"):
                self.var_proprio.set(True)
                self._proprio_mudou()
        titulo = f"Editando: {p['nome']}" if p else "Novo paciente"
        self.lbl_subtitulo.configure(text=titulo + " · Campos com * são obrigatórios.")
        self.lbl_status.configure(text="")
        self._mostrar_idade()
        self.abas.set("1. Paciente")

    def _salvar(self, incluir_servico: bool):
        try:
            paciente = self._ler(self.cp)
            responsavel = self._ler(self.cr)
        except ValueError as e:
            ui.erro(str(e), parent=self)
            return
        paciente["diagnosticos"] = "; ".join(d for d, v in self.vars_diag.items() if v.get())
        paciente["laudo"] = self.var_laudo.get()
        paciente["autoriza_imagem"] = self.var_imagem.get()
        paciente["consentimento_lgpd"] = self.var_lgpd.get()
        paciente["proprio_responsavel"] = self.var_proprio.get()
        paciente["ativo"] = self.var_ativo.get()
        if not paciente["consentimento_lgpd"] and not ui.confirmar(
                "O consentimento LGPD (aba 4) não foi marcado. Deseja salvar mesmo assim?", parent=self):
            self.abas.set("4. Emergência e autorizações")
            return
        try:
            novo_id = pacientes.salvar(paciente, responsavel, self.paciente_id, self.responsavel_id)
        except ValueError as e:
            ui.erro(f"Confira os dados:\n\n{e}", "Dados incompletos", self)
            return
        acoes.notificar(self, "Cadastro salvo com sucesso ✔")
        nome = paciente["nome"]
        if incluir_servico:
            acoes.novo_contrato(self, novo_id, nome)
        self.app.mostrar("pacientes")
