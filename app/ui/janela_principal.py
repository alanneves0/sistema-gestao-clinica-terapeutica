"""
=============================================================================
 ui/janela_principal.py — Janela principal, tela de login e menu lateral
=============================================================================
 Fluxo:
   1. Abre a tela de LOGIN.
   2. Após entrar, monta o layout: MENU LATERAL (esquerda) + PÁGINA (direita).
   3. Tarefas de fundo: backup diário e (no modo API) cobrança automática.
 As páginas são criadas na primeira vez em que são abertas e reaproveitadas.
=============================================================================
"""
from __future__ import annotations

import threading
import traceback

import customtkinter as ctk
from PIL import Image

from app.core import config, sessao
from app.core.log import logger
from app.repositorios import usuarios
from app.servicos import backup, cobranca
from app.ui import acoes
from app.ui import componentes as ui
from app.ui.tema import estilizar_tabelas, fonte

COR = config.CORES

# (chave, texto do menu, classe da página) — a classe é importada sob demanda
MENU = [
    ("painel", "⌂   Painel", "app.ui.paginas.painel:PaginaPainel"),
    ("pacientes", "☰   Pacientes", "app.ui.paginas.pacientes:PaginaPacientes"),
    ("cadastro", "+  Novo cadastro", "app.ui.paginas.cadastro:PaginaCadastro"),
    ("financeiro", "$   Financeiro", "app.ui.paginas.financeiro:PaginaFinanceiro"),
    ("cobrancas", "✉   Cobranças WhatsApp", "app.ui.paginas.cobrancas:PaginaCobrancas"),
    ("servicos", "✎   Serviços e preços", "app.ui.paginas.servicos:PaginaServicos"),
    ("relatorios", "▤   Relatórios", "app.ui.paginas.relatorios:PaginaRelatorios"),
    ("configuracoes", "⚙   Configurações", "app.ui.paginas.configuracoes:PaginaConfiguracoes"),
]


def _importar(caminho: str):
    modulo, classe = caminho.split(":")
    return getattr(__import__(modulo, fromlist=[classe]), classe)


def _imagem_logo(tamanho: int) -> ctk.CTkImage | None:
    try:
        img = Image.open(config.LOGO_PATH)
        return ctk.CTkImage(light_image=img, dark_image=img, size=(tamanho, tamanho))
    except Exception:  # noqa: BLE001
        return None


# ===========================================================================
# Tela de login
# ===========================================================================
class TelaLogin(ctk.CTkFrame):
    def __init__(self, master, ao_entrar):
        super().__init__(master, fg_color=COR["fundo"], corner_radius=0)
        self.ao_entrar = ao_entrar
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Lado esquerdo: marca
        esq = ctk.CTkFrame(self, fg_color=COR["primaria_suave"], corner_radius=0)
        esq.grid(row=0, column=0, sticky="nsew")
        caixa = ctk.CTkFrame(esq, fg_color="transparent")
        caixa.place(relx=0.5, rely=0.5, anchor="center")
        logo = _imagem_logo(300)
        if logo:
            ctk.CTkLabel(caixa, text="", image=logo).pack()
        ctk.CTkLabel(caixa, text="Cuidado, desenvolvimento e acolhimento", font=fonte(15),
                     text_color=COR["primaria_escura"]).pack(pady=(16, 0))

        # Lado direito: formulário
        dir_ = ctk.CTkFrame(self, fg_color=COR["fundo"], corner_radius=0)
        dir_.grid(row=0, column=1, sticky="nsew")
        cartao = ui.Cartao(dir_, width=400)
        cartao.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(cartao, text="Bem-vinda(o)!", font=fonte(26, "bold"),
                     text_color=COR["primaria_profunda"]).pack(anchor="w", padx=36, pady=(36, 0))
        ui.subtitulo(cartao, "Entre para acessar o sistema do Espaço").pack(anchor="w", padx=36, pady=(0, 20))
        ui.rotulo(cartao, "Usuário").pack(anchor="w", padx=36)
        self.login = ui.Campo(cartao, 320, height=42)
        self.login.pack(padx=36, pady=(2, 12))
        ui.rotulo(cartao, "Senha").pack(anchor="w", padx=36)
        self.senha = ui.Campo(cartao, 320, height=42, show="•")
        self.senha.pack(padx=36, pady=(2, 8))
        self.msg = ctk.CTkLabel(cartao, text="", text_color=COR["atraso"], font=fonte(12))
        self.msg.pack(padx=36)
        ui.botao(cartao, "Entrar", self._entrar, "primario", 320, 44).pack(padx=36, pady=(6, 12))
        ui.subtitulo(cartao, "Primeiro acesso: usuário admin · senha admin", 11).pack(padx=36, pady=(0, 30))
        ctk.CTkLabel(dir_, text=f"{config.APP_NOME} · v{config.APP_VERSAO}", font=fonte(10),
                     text_color=COR["texto_suave"]).place(relx=0.5, rely=0.97, anchor="s")

        self.login.bind("<Return>", lambda _e: self.senha.focus_set())
        self.senha.bind("<Return>", lambda _e: self._entrar())
        self.after(200, self.login.focus_set)

    def _entrar(self):
        usuario = usuarios.autenticar(self.login.get(), self.senha.get())
        if not usuario:
            self.msg.configure(text="Usuário ou senha incorretos.")
            ui.definir_texto(self.senha, "")
            return
        self.ao_entrar(usuario)


# ===========================================================================
# Janela principal
# ===========================================================================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        demo = config.DADOS_DIR.name == "dados_demo"
        self.title(config.APP_NOME + ("  —  MODO DEMONSTRAÇÃO (dados fictícios)" if demo else ""))
        self.geometry("1366x820")
        self.minsize(1180, 700)
        self.configure(fg_color=COR["fundo"])
        try:
            if config.ICONE_ICO.exists():
                self.iconbitmap(str(config.ICONE_ICO))
        except Exception:  # noqa: BLE001 — em Linux/Mac o .ico pode não ser aceito
            pass
        self.after(0, self._maximizar)
        estilizar_tabelas(self)
        acoes.registrar_janela_principal(self)
        self.report_callback_exception = self._erro_inesperado
        self.paginas: dict = {}
        self.botoes_menu: dict = {}
        self.pagina_atual: str | None = None
        self.layout = None
        self._toast = None
        self._tarefas_agendadas = False
        self._mostrar_login()

    def _maximizar(self):
        """Abre a janela maximizada (no Linux o nome do estado é diferente)."""
        try:
            self.state("zoomed")
        except Exception:  # noqa: BLE001
            try:
                self.attributes("-zoomed", True)
            except Exception:  # noqa: BLE001
                pass

    # ----------------------------------------------------------- login/logout
    def _mostrar_login(self):
        self.tela_login = TelaLogin(self, self._entrou)
        self.tela_login.pack(fill="both", expand=True)

    def _entrou(self, usuario: dict):
        sessao.iniciar(usuario)
        self.tela_login.destroy()
        self._montar_layout()
        self.mostrar("painel")
        if usuario.get("trocar_senha"):
            from app.ui.dialogos.diversos import DialogoSenha
            self.after(400, lambda: DialogoSenha(self, usuario["id"], obrigatorio=True))
        if not self._tarefas_agendadas:
            self._tarefas_agendadas = True
            self.after(1500, self._tarefas_de_fundo)

    def sair(self):
        sessao.encerrar()
        if self.layout:
            self.layout.destroy()
        self.paginas.clear()
        self.botoes_menu.clear()
        self.layout = None
        self._mostrar_login()

    # ----------------------------------------------------------- layout
    def _montar_layout(self):
        self.layout = ctk.CTkFrame(self, fg_color=COR["fundo"], corner_radius=0)
        self.layout.pack(fill="both", expand=True)
        self.layout.grid_columnconfigure(1, weight=1)
        self.layout.grid_rowconfigure(0, weight=1)

        menu = ctk.CTkFrame(self.layout, fg_color=COR["menu_fundo"], corner_radius=0, width=250,
                            border_width=0)
        menu.grid(row=0, column=0, sticky="ns")
        menu.grid_propagate(False)
        menu.grid_columnconfigure(0, weight=1)
        logo = _imagem_logo(150)
        if logo:
            ctk.CTkLabel(menu, text="", image=logo).grid(row=0, column=0, pady=(18, 8))
        else:
            ctk.CTkLabel(menu, text=config.APP_NOME_CURTO, font=fonte(20, "bold"),
                         text_color=COR["primaria_profunda"]).grid(row=0, column=0, pady=24)
        for i, (chave, texto, _cls) in enumerate(MENU, start=1):
            b = ctk.CTkButton(menu, text=texto, anchor="w", height=42, corner_radius=10, font=fonte(13, "bold"),
                              fg_color="transparent", hover_color=COR["primaria_suave"],
                              text_color=COR["texto"], command=lambda c=chave: self.mostrar(c))
            b.grid(row=i, column=0, sticky="ew", padx=14, pady=2)
            self.botoes_menu[chave] = b
        menu.grid_rowconfigure(len(MENU) + 1, weight=1)

        rodape = ctk.CTkFrame(menu, fg_color=COR["primaria_suave"], corner_radius=12)
        rodape.grid(row=len(MENU) + 2, column=0, sticky="ew", padx=14, pady=16)
        u = sessao.usuario() or {}
        ctk.CTkLabel(rodape, text=u.get("nome", ""), font=fonte(12, "bold"),
                     text_color=COR["primaria_profunda"]).pack(anchor="w", padx=12, pady=(10, 0))
        ctk.CTkLabel(rodape, text=usuarios.PERFIS.get(u.get("perfil"), ""), font=fonte(11),
                     text_color=COR["texto_suave"]).pack(anchor="w", padx=12)
        ui.botao(rodape, "Sair", self.sair, "secundario", 90, 30).pack(anchor="w", padx=12, pady=(6, 12))

        self.area = ctk.CTkFrame(self.layout, fg_color=COR["fundo"], corner_radius=0)
        self.area.grid(row=0, column=1, sticky="nsew")
        self.area.grid_columnconfigure(0, weight=1)
        self.area.grid_rowconfigure(0, weight=1)

    def mostrar(self, chave: str, **kwargs):
        """Troca a página exibida. kwargs são repassados para pagina.atualizar()."""
        if chave not in self.paginas:
            caminho = next(c for k, _t, c in MENU if k == chave)
            self.paginas[chave] = _importar(caminho)(self.area, self)
            self.paginas[chave].grid(row=0, column=0, sticky="nsew")
        pagina = self.paginas[chave]
        pagina.tkraise()
        self.pagina_atual = chave
        for k, b in self.botoes_menu.items():
            ativo = k == chave
            b.configure(fg_color=COR["menu_ativo"] if ativo else "transparent",
                        text_color=COR["primaria_profunda"] if ativo else COR["texto"])
        try:
            pagina.atualizar(**kwargs)
        except Exception:  # noqa: BLE001
            logger().exception("Erro ao atualizar a página %s", chave)
            raise

    # ----------------------------------------------------------- avisos
    def notificar(self, texto: str, tipo: str = "sucesso"):
        """Aviso flutuante no canto inferior direito que some sozinho."""
        if self._toast is not None:
            try:
                self._toast.destroy()
            except Exception:  # noqa: BLE001
                pass
        cor = {"sucesso": COR["pago"], "erro": COR["atraso"], "info": COR["primaria_escura"]}.get(tipo, COR["pago"])
        self._toast = ctk.CTkFrame(self, fg_color=cor, corner_radius=12)
        ctk.CTkLabel(self._toast, text=texto, text_color="#FFFFFF", font=fonte(13, "bold")).pack(padx=18, pady=10)
        self._toast.place(relx=0.985, rely=0.975, anchor="se")
        alvo = self._toast
        self.after(3500, lambda: alvo.destroy() if alvo.winfo_exists() else None)

    def _erro_inesperado(self, tipo, valor, tb):
        """Qualquer erro não previsto é registrado no log e mostrado de forma amigável."""
        logger().error("Erro inesperado:\n%s", "".join(traceback.format_exception(tipo, valor, tb)))
        ui.erro(f"Ocorreu um erro inesperado:\n\n{valor}\n\nOs detalhes foram salvos em\n{config.LOG_PATH}",
                parent=self)

    # ----------------------------------------------------------- tarefas de fundo
    def _tarefas_de_fundo(self):
        try:
            if backup.backup_automatico():
                logger().info("Backup automático realizado")
        except Exception:  # noqa: BLE001
            logger().exception("Falha no backup automático")

        def cobrar():
            try:
                resumo = cobranca.executar_automatico()
                if resumo["enviados"] or resumo["erros"]:
                    self.after(0, lambda: self.notificar(
                        f"Cobrança automática: {resumo['enviados']} enviada(s), {resumo['erros']} erro(s)",
                        "info" if not resumo["erros"] else "erro"))
            except Exception:  # noqa: BLE001
                logger().exception("Falha na cobrança automática")
        threading.Thread(target=cobrar, daemon=True).start()
        self.after(60 * 60 * 1000, self._tarefas_de_fundo)  # repete a cada 1 hora
