"""
=============================================================================
 ui/dialogos/diversos.py — Janelas menores
=============================================================================
   • DialogoParcela       → editar vencimento/valores de uma parcela
   • DialogoMensagem      → pré-visualizar e editar a mensagem de WhatsApp
   • DialogoResponsavel   → escolher um responsável já cadastrado (irmãos)
   • DialogoServico       → cadastrar/editar serviço e preço
   • DialogoUsuario       → cadastrar usuário do sistema
   • DialogoSenha         → trocar senha
   • pedir_numero()       → pergunta simples de um número
=============================================================================
"""
from __future__ import annotations

import customtkinter as ctk

from app.core import config, utils
from app.repositorios import financeiro, pacientes, servicos, usuarios
from app.ui import componentes as ui
from app.ui.tema import fonte

COR = config.CORES


class DialogoParcela(ui.DialogoBase):
    def __init__(self, master, parcela_id: int):
        super().__init__(master, "Editar parcela", 520, 440)
        self.p = financeiro.obter_parcela(parcela_id)
        c = self.corpo
        c.grid_columnconfigure((0, 1), weight=1)
        ui.subtitulo(c, f"{self.p['paciente']} · {self.p['servico']} · {self.p['rotulo']}").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        ui.rotulo(c, "Vencimento", True).grid(row=1, column=0, sticky="w")
        self.venc = ui.CampoData(c, 180)
        self.venc.definir(self.p["vencimento"])
        self.venc.grid(row=2, column=0, sticky="ew")
        ui.rotulo(c, "Valor cheio (R$)", True).grid(row=3, column=0, sticky="w", pady=(10, 0))
        ui.rotulo(c, "Valor até o vencimento (R$)", True).grid(row=3, column=1, sticky="w", padx=(10, 0), pady=(10, 0))
        self.valor = ui.CampoMoeda(c, 180)
        self.valor.definir(self.p["valor"])
        self.valor.grid(row=4, column=0, sticky="ew")
        self.pont = ui.CampoMoeda(c, 180)
        self.pont.definir(self.p["valor_pontualidade"])
        self.pont.grid(row=4, column=1, sticky="ew", padx=(10, 0))
        ui.rotulo(c, "Observações").grid(row=5, column=0, sticky="w", pady=(10, 0))
        self.obs = ui.Campo(c, 400)
        self.obs.definir(self.p.get("observacoes") or "")
        self.obs.grid(row=6, column=0, columnspan=2, sticky="ew")
        self.rodape.grid_columnconfigure(0, weight=1)
        ui.botao(self.rodape, "Cancelar", self.fechar, "secundario").grid(row=0, column=1, padx=(0, 8))
        ui.botao(self.rodape, "Salvar", self._salvar).grid(row=0, column=2)

    def _salvar(self):
        try:
            if not self.venc.data():
                raise ValueError("Informe o vencimento.")
            financeiro.editar_parcela(self.p["id"], self.venc.data(), self.valor.numero(),
                                      self.pont.numero(), self.obs.valor())
        except (ValueError, TypeError) as e:
            ui.erro(str(e) or "Confira os dados.", parent=self)
            return
        self.fechar(True)


class DialogoMensagem(ui.DialogoBase):
    """Mostra a mensagem que será enviada; permite editar antes de enviar."""
    def __init__(self, master, destinatario: str, telefone: str, texto: str, modo: str):
        super().__init__(master, "Mensagem de WhatsApp", 620, 600)
        c = self.corpo
        c.grid_columnconfigure(0, weight=1)
        c.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(c, text=f"Para: {destinatario}", font=fonte(14, "bold"),
                     text_color=COR["primaria_profunda"], anchor="w").grid(row=0, column=0, sticky="w")
        self.telefone = ui.CampoTelefone(c, 220)
        self.telefone.definir(utils.formatar_telefone(telefone))
        self.telefone.grid(row=1, column=0, sticky="w", pady=(4, 8))
        self.texto = ctk.CTkTextbox(c, font=fonte(13), corner_radius=12, border_width=1, wrap="word")
        self.texto.insert("1.0", texto)
        self.texto.grid(row=2, column=0, sticky="nsew")
        explica = ("O WhatsApp será aberto com a mensagem pronta — confira e clique em ENVIAR."
                   if modo != "api" else "A mensagem será enviada automaticamente pela API oficial.")
        ui.subtitulo(c, explica, 11).grid(row=3, column=0, sticky="w", pady=(6, 0))
        self.rodape.grid_columnconfigure(0, weight=1)
        ui.botao(self.rodape, "Cancelar", self.fechar, "secundario").grid(row=0, column=1, padx=(0, 8))
        ui.botao(self.rodape, "Enviar pelo WhatsApp", self._enviar, "whatsapp", 200).grid(row=0, column=2)

    def _enviar(self):
        texto = utils.normalizar_texto(self.texto.get("1.0", "end").strip())
        if not texto:
            ui.aviso("A mensagem está vazia.", parent=self)
            return
        self.fechar({"telefone": self.telefone.get(), "texto": texto})


class DialogoResponsavel(ui.DialogoBase):
    """Lista de responsáveis já cadastrados para vincular a um novo paciente."""
    def __init__(self, master):
        super().__init__(master, "Escolher responsável já cadastrado", 760, 520)
        c = self.corpo
        c.grid_columnconfigure(0, weight=1)
        c.grid_rowconfigure(1, weight=1)
        self.busca = ui.Campo(c, 320, placeholder_text="Buscar por nome, CPF ou paciente")
        self.busca.grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.busca.bind("<KeyRelease>", lambda _e: self._carregar())
        self.tabela = ui.Tabela(c, [("nome", "Responsável", 200, "w"), ("cpf", "CPF", 120, "center"),
                                    ("whats", "WhatsApp", 130, "center"), ("pac", "Paciente(s)", 220, "w")],
                                ao_duplo_clique=self._escolher)
        self.tabela.grid(row=1, column=0, sticky="nsew")
        self.rodape.grid_columnconfigure(0, weight=1)
        ui.botao(self.rodape, "Cancelar", self.fechar, "secundario").grid(row=0, column=1, padx=(0, 8))
        ui.botao(self.rodape, "Usar este responsável", self._escolher, largura=190).grid(row=0, column=2)
        self._carregar()

    def _carregar(self):
        self.dados = {str(r["id"]): r for r in pacientes.buscar_responsaveis(self.busca.valor())}
        self.tabela.carregar([{"iid": k, "valores": (r["nome"], r.get("cpf") or "", r.get("whatsapp") or
                                                     r.get("telefone") or "", r.get("pacientes") or "")}
                              for k, r in self.dados.items()])

    def _escolher(self):
        sel = self.tabela.selecionado()
        if sel:
            self.fechar(self.dados[sel])


class DialogoServico(ui.DialogoBase):
    def __init__(self, master, servico_id: int | None = None):
        super().__init__(master, "Serviço e preço", 560, 600)
        self.servico_id = servico_id
        s = servicos.obter(servico_id) if servico_id else {}
        c = self.corpo
        c.grid_columnconfigure((0, 1), weight=1)
        ui.rotulo(c, "Nome do serviço", True).grid(row=0, column=0, columnspan=2, sticky="w")
        self.nome = ui.Campo(c, 480)
        self.nome.definir(s.get("nome", ""))
        self.nome.grid(row=1, column=0, columnspan=2, sticky="ew")
        ui.rotulo(c, "Categoria").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ui.rotulo(c, "Tipo de cobrança").grid(row=2, column=1, sticky="w", padx=(10, 0), pady=(10, 0))
        self.categoria = ui.combo(c, servicos.CATEGORIAS, 200, valor_inicial=s.get("categoria", "Terapia"))
        self.categoria.grid(row=3, column=0, sticky="ew")
        self.tipo = ui.combo(c, list(config.TIPOS_COBRANCA.values()), 200,
                             valor_inicial=config.TIPOS_COBRANCA[s.get("tipo_cobranca", "mensal")])
        self.tipo.grid(row=3, column=1, sticky="ew", padx=(10, 0))
        ui.rotulo(c, "Valor cheio / total (R$)", True).grid(row=4, column=0, sticky="w", pady=(10, 0))
        ui.rotulo(c, "Valor até o vencimento (R$)").grid(row=4, column=1, sticky="w", padx=(10, 0), pady=(10, 0))
        self.valor = ui.CampoMoeda(c, 200)
        self.valor.definir(s.get("valor_cheio", ""))
        self.valor.grid(row=5, column=0, sticky="ew")
        self.pont = ui.CampoMoeda(c, 200)
        self.pont.definir(s.get("valor_pontualidade", ""))
        self.pont.grid(row=5, column=1, sticky="ew", padx=(10, 0))
        ui.rotulo(c, "Parcelas (padrão)").grid(row=6, column=0, sticky="w", pady=(10, 0))
        ui.rotulo(c, "Entrada / 1ª parcela (R$)").grid(row=6, column=1, sticky="w", padx=(10, 0), pady=(10, 0))
        self.parcelas = ui.combo(c, [str(i) for i in range(1, 25)], 200, editavel=True,
                                 valor_inicial=str(s.get("parcelas_padrao", 6)))
        self.parcelas.grid(row=7, column=0, sticky="ew")
        self.entrada = ui.CampoMoeda(c, 200)
        self.entrada.definir(s.get("valor_entrada") or "")
        self.entrada.grid(row=7, column=1, sticky="ew", padx=(10, 0))
        ui.rotulo(c, "Descrição").grid(row=8, column=0, sticky="w", pady=(10, 0))
        self.descricao = ui.Campo(c, 480)
        self.descricao.definir(s.get("descricao") or "")
        self.descricao.grid(row=9, column=0, columnspan=2, sticky="ew")
        ui.subtitulo(c, "Mensalidade: o valor é cobrado todo mês.\n"
                        "Pacote parcelado: o valor TOTAL é dividido nas parcelas (ex.: avaliação).\n"
                        "Cobrança única: cobrada uma só vez (ex.: taxa de adesão).", 11).grid(
            row=10, column=0, columnspan=2, sticky="w", pady=(12, 0))
        self.rodape.grid_columnconfigure(0, weight=1)
        ui.botao(self.rodape, "Cancelar", self.fechar, "secundario").grid(row=0, column=1, padx=(0, 8))
        ui.botao(self.rodape, "Salvar", self._salvar).grid(row=0, column=2)

    def _salvar(self):
        try:
            tipo = next(k for k, v in config.TIPOS_COBRANCA.items() if v == self.tipo.get())
            dados = {"nome": self.nome.valor(), "categoria": self.categoria.get(), "tipo_cobranca": tipo,
                     "valor_cheio": self.valor.numero(), "valor_pontualidade": self.pont.numero(),
                     "parcelas_padrao": int(self.parcelas.get() or 1), "valor_entrada": self.entrada.numero(),
                     "descricao": self.descricao.valor()}
            servicos.salvar(dados, self.servico_id)
        except ValueError as e:
            ui.erro(str(e), parent=self)
            return
        self.fechar(True)


class DialogoUsuario(ui.DialogoBase):
    def __init__(self, master):
        super().__init__(master, "Novo usuário", 480, 440)
        c = self.corpo
        c.grid_columnconfigure(0, weight=1)
        campos = [("Nome", "nome"), ("Login", "login")]
        for i, (txt, attr) in enumerate(campos):
            ui.rotulo(c, txt, True).grid(row=i * 2, column=0, sticky="w", pady=(8 if i else 0, 0))
            campo = ui.Campo(c, 400)
            campo.grid(row=i * 2 + 1, column=0, sticky="ew")
            setattr(self, attr, campo)
        ui.rotulo(c, "Senha", True).grid(row=4, column=0, sticky="w", pady=(8, 0))
        self.senha = ui.Campo(c, 400, show="•")
        self.senha.grid(row=5, column=0, sticky="ew")
        ui.rotulo(c, "Perfil").grid(row=6, column=0, sticky="w", pady=(8, 0))
        self.perfil = ui.combo(c, list(usuarios.PERFIS.values()), 400, valor_inicial="Recepção")
        self.perfil.grid(row=7, column=0, sticky="ew")
        self.rodape.grid_columnconfigure(0, weight=1)
        ui.botao(self.rodape, "Cancelar", self.fechar, "secundario").grid(row=0, column=1, padx=(0, 8))
        ui.botao(self.rodape, "Criar usuário", self._salvar, largura=150).grid(row=0, column=2)

    def _salvar(self):
        perfil = next(k for k, v in usuarios.PERFIS.items() if v == self.perfil.get())
        try:
            usuarios.criar(self.nome.valor(), self.login.valor(), self.senha.get(), perfil)
        except ValueError as e:
            ui.erro(str(e), parent=self)
            return
        self.fechar(True)


class DialogoSenha(ui.DialogoBase):
    def __init__(self, master, usuario_id: int, obrigatorio: bool = False):
        super().__init__(master, "Definir nova senha", 440, 330)
        self.usuario_id = usuario_id
        c = self.corpo
        c.grid_columnconfigure(0, weight=1)
        if obrigatorio:
            ui.subtitulo(c, "Por segurança, troque a senha padrão antes de continuar.").grid(
                row=0, column=0, sticky="w", pady=(0, 8))
        ui.rotulo(c, "Nova senha", True).grid(row=1, column=0, sticky="w")
        self.s1 = ui.Campo(c, 360, show="•")
        self.s1.grid(row=2, column=0, sticky="ew")
        ui.rotulo(c, "Repita a nova senha", True).grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.s2 = ui.Campo(c, 360, show="•")
        self.s2.grid(row=4, column=0, sticky="ew")
        self.rodape.grid_columnconfigure(0, weight=1)
        ui.botao(self.rodape, "Cancelar", self.fechar, "secundario").grid(row=0, column=1, padx=(0, 8))
        ui.botao(self.rodape, "Salvar senha", self._salvar, largura=140).grid(row=0, column=2)

    def _salvar(self):
        if self.s1.get() != self.s2.get():
            ui.erro("As senhas não conferem.", parent=self)
            return
        try:
            usuarios.alterar_senha(self.usuario_id, self.s1.get())
        except ValueError as e:
            ui.erro(str(e), parent=self)
            return
        self.fechar(True)


def pedir_numero(master, titulo_txt: str, pergunta: str, padrao: int = 6) -> int | None:
    """Pergunta um número inteiro (ex.: quantos meses renovar)."""
    dialogo = ctk.CTkInputDialog(text=f"{pergunta}\n(padrão: {padrao})", title=titulo_txt)
    resposta = dialogo.get_input()
    if resposta is None:
        return None
    resposta = resposta.strip() or str(padrao)
    if not resposta.isdigit() or int(resposta) < 1:
        ui.erro("Informe um número inteiro maior que zero.", parent=master)
        return None
    return int(resposta)
