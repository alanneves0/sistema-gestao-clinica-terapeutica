"""
=============================================================================
 ui/paginas/configuracoes.py — Configurações do sistema
=============================================================================
 Abas:
   • Espaço e PIX         → dados que aparecem nos recibos e mensagens
   • Regras financeiras   → tolerância, multa, juros, numeração de recibos
   • WhatsApp             → modo de envio (link ou API oficial) e automação
   • Mensagens            → textos das mensagens (com {campos} automáticos)
   • Usuários             → quem pode entrar no sistema
   • Backup               → cópias de segurança e restauração
=============================================================================
"""
from __future__ import annotations

from datetime import date
from tkinter import filedialog

import customtkinter as ctk

from app.core import config, database, sessao, utils
from app.repositorios import configuracoes, usuarios
from app.servicos import backup, recibos, whatsapp
from app.ui import acoes
from app.ui import componentes as ui
from app.ui.paginas.base import Pagina
from app.ui.tema import fonte

COR = config.CORES

CAMPOS_MENSAGEM = ("{responsavel} {responsavel_completo} {paciente} {lista_parcelas} {total} {vencimento} "
                   "{dias_atraso} {clinica} {pix_chave} {pix_titular} {pix_banco} {telefone_clinica} · "
                   "Recibo: {valor} {servico} {parcela} {data} {forma} {recibo}")


class PaginaConfiguracoes(Pagina):
    TITULO = "Configurações"
    SUBTITULO = "Dados do Espaço, regras financeiras, WhatsApp, usuários e backup"

    def __init__(self, master, app):
        super().__init__(master, app)
        self.campos: dict = {}
        self.chaves: dict = {}
        ui.botao(self.acoes_cabecalho, "✔  Salvar configurações", self._salvar, "primario", 210).grid(row=0, column=0)
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
        for nome in ("Espaço e PIX", "Regras financeiras", "WhatsApp", "Mensagens", "Usuários", "Backup"):
            self.abas.add(nome)
        self._aba_espaco(self._rolavel("Espaço e PIX"))
        self._aba_regras(self._rolavel("Regras financeiras"))
        self._aba_whatsapp(self._rolavel("WhatsApp"))
        self._aba_mensagens(self._rolavel("Mensagens"))
        self._aba_usuarios(self.abas.tab("Usuários"))
        self._aba_backup(self._rolavel("Backup"))

    # ------------------------------------------------------------ helpers
    def _rolavel(self, aba):
        f = ctk.CTkScrollableFrame(self.abas.tab(aba), fg_color="transparent")
        f.pack(fill="both", expand=True, padx=6, pady=6)
        f.grid_columnconfigure((0, 1, 2), weight=1, uniform="c")
        return f

    def _campo(self, pai, chave, rotulo, linha, coluna, colspan=1, senha=False, placeholder=""):
        ui.rotulo(pai, rotulo).grid(row=linha, column=coluna, columnspan=colspan, sticky="w", padx=8, pady=(8, 0))
        w = ui.Campo(pai, 200, show="•" if senha else "", placeholder_text=placeholder)
        w.grid(row=linha + 1, column=coluna, columnspan=colspan, sticky="ew", padx=8)
        self.campos[chave] = w
        return w

    def _secao(self, pai, texto, linha):
        ctk.CTkLabel(pai, text=texto, font=fonte(14, "bold"), text_color=COR["destaque_escuro"]).grid(
            row=linha, column=0, columnspan=3, sticky="w", padx=8, pady=(14, 0))

    def _ajuda(self, pai, texto, linha):
        l = ui.subtitulo(pai, texto, 11)
        l.configure(wraplength=900)
        l.grid(row=linha, column=0, columnspan=3, sticky="w", padx=8, pady=(4, 0))

    # ------------------------------------------------------------ abas
    def _aba_espaco(self, f):
        self._secao(f, "Dados do Espaço (aparecem nos recibos)", 0)
        self._campo(f, "clinica_nome", "Nome do Espaço", 1, 0, 2)
        self._campo(f, "clinica_documento", "CNPJ / CPF", 1, 2)
        self._campo(f, "clinica_telefone", "Telefone", 3, 0)
        self._campo(f, "clinica_email", "E-mail", 3, 1)
        self._campo(f, "clinica_cidade", "Cidade (para 'Cidade, data' do recibo)", 3, 2)
        self._campo(f, "clinica_endereco", "Endereço", 5, 0, 3)
        self._campo(f, "assinatura_nome", "Nome na assinatura do recibo", 7, 0)
        self._campo(f, "assinatura_registro", "Registro profissional", 7, 1, 2)
        self._secao(f, "PIX / dados bancários (aparecem nas cobranças)", 9)
        self._campo(f, "pix_chave", "Chave PIX", 10, 0)
        self._campo(f, "pix_tipo", "Tipo da chave", 10, 1, placeholder="Telefone, CPF, e-mail…")
        self._campo(f, "pix_titular", "Titular", 12, 0)
        self._campo(f, "pix_banco", "Banco", 12, 1)

    def _aba_regras(self, f):
        self._secao(f, "Vencimento e atraso", 0)
        self._campo(f, "tolerancia_dias", "Dias de tolerância após o vencimento", 1, 0)
        self._campo(f, "multa_percentual", "Multa por atraso (%)", 1, 1)
        self._campo(f, "juros_mes_percentual", "Juros ao mês (%)", 1, 2)
        self._ajuda(f, "• Até o vencimento (+ tolerância) vale o valor de PONTUALIDADE (ex.: Fono R$ 200,00).\n"
                       "• Depois, vale o valor CHEIO (ex.: R$ 220,00) + multa e juros, se configurados "
                       "(deixe 0 para não cobrar).\n"
                       "• A parcela só aparece como 'Em atraso' depois de passados os dias de tolerância.", 3)
        self._secao(f, "Recibos", 4)
        self._campo(f, "proximo_recibo", "Próximo número de recibo", 5, 0)

    def _aba_whatsapp(self, f):
        self._secao(f, "Como enviar as mensagens", 0)
        self.seg_modo = ctk.CTkSegmentedButton(f, values=["WhatsApp Web / App (manual)", "API oficial (automático)"],
                                               font=fonte(12))
        self.seg_modo.grid(row=1, column=0, columnspan=2, sticky="w", padx=8, pady=6)
        self._ajuda(f, "MANUAL (recomendado para começar, gratuito): o sistema abre o WhatsApp já na conversa do "
                       "responsável com a mensagem escrita — basta apertar Enviar. Use o WhatsApp Business do Espaço "
                       "conectado no WhatsApp Web ou no aplicativo do computador.\n"
                       "AUTOMÁTICO: usa a API oficial do WhatsApp (Meta). As mensagens saem sozinhas. Exige conta "
                       "Meta Business, número dedicado, token e modelo de mensagem aprovado. Veja docs/WHATSAPP.md.", 2)
        ui.rotulo(f, "Abrir no").grid(row=3, column=0, sticky="w", padx=8, pady=(8, 0))
        self.seg_abrir = ctk.CTkSegmentedButton(f, values=["Navegador (WhatsApp Web)", "Aplicativo WhatsApp Desktop"],
                                                font=fonte(12))
        self.seg_abrir.grid(row=4, column=0, columnspan=2, sticky="w", padx=8)
        self._campo(f, "ddd_padrao", "DDD padrão (para números sem DDD)", 3, 2)

        self._secao(f, "API oficial (WhatsApp Cloud API)", 6)
        self._campo(f, "api_token", "Token de acesso", 7, 0, 2, senha=True)
        self._campo(f, "api_phone_id", "Phone Number ID", 7, 2)
        self._campo(f, "api_template_atraso", "Nome do modelo aprovado (cobrança)", 9, 0,
                    placeholder="ex.: cobranca_atraso")
        self._campo(f, "api_template_idioma", "Idioma do modelo", 9, 1)
        self._campo(f, "api_versao", "Versão da API", 9, 2)
        self._ajuda(f, "O modelo aprovado na Meta deve ter 4 variáveis no corpo: {{1}} nome do responsável, "
                       "{{2}} paciente(s), {{3}} total em aberto, {{4}} chave PIX. Sem modelo, a API só entrega "
                       "mensagens para quem conversou com o Espaço nas últimas 24 horas.", 11)
        ui.botao(f, "Testar conexão com a API", self._testar_api, "secundario", 220).grid(
            row=12, column=0, sticky="w", padx=8, pady=8)

        self._secao(f, "Automação", 13)
        self.var_auto = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(f, text="Enviar cobranças e lembretes automaticamente (somente no modo API)",
                      variable=self.var_auto, font=fonte(12)).grid(row=14, column=0, columnspan=3, sticky="w",
                                                                    padx=8, pady=6)
        self._campo(f, "cobranca_intervalo_dias", "Repetir cobrança a cada (dias)", 15, 0)
        self._campo(f, "lembrete_dias_antes", "Lembrete quantos dias antes do vencimento", 15, 1)

    def _aba_mensagens(self, f):
        self._ajuda(f, "Palavras entre chaves são trocadas automaticamente. Disponíveis: " + CAMPOS_MENSAGEM
                    + "\nNo WhatsApp: *texto* = negrito, _texto_ = itálico.", 0)
        self.textos = {}
        for i, (chave, titulo_txt) in enumerate((("msg_atraso", "Cobrança de ATRASO"),
                                                 ("msg_lembrete", "LEMBRETE de vencimento"),
                                                 ("msg_recibo", "Confirmação de PAGAMENTO"))):
            self._secao(f, titulo_txt, 1 + i * 2)
            tb = ctk.CTkTextbox(f, height=170, corner_radius=10, border_width=1, font=fonte(12), wrap="word")
            tb.grid(row=2 + i * 2, column=0, columnspan=3, sticky="ew", padx=8)
            self.textos[chave] = tb
        ui.botao(f, "Restaurar textos padrão", self._restaurar_textos, "secundario", 200).grid(
            row=8, column=0, sticky="w", padx=8, pady=12)

    def _aba_usuarios(self, aba):
        aba.grid_columnconfigure(0, weight=1)
        aba.grid_rowconfigure(1, weight=1)
        ui.barra_botoes(aba, [("+ Novo usuário", self._novo_usuario, "primario", 150),
                              ("Trocar senha", self._trocar_senha, "secundario", 140),
                              ("Ativar / Desativar", self._ativar_usuario, "secundario", 160)]).grid(
            row=0, column=0, sticky="w", padx=8, pady=8)
        self.tab_usuarios = ui.Tabela(aba, [("nome", "Nome", 220, "w"), ("login", "Login", 150, "w"),
                                            ("perfil", "Perfil", 140, "center"), ("ativo", "Situação", 100, "center"),
                                            ("criado", "Criado em", 150, "center")], altura=10)
        self.tab_usuarios.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

    def _aba_backup(self, f):
        self._secao(f, "Cópias de segurança", 0)
        self.lbl_backup = ui.subtitulo(f, "")
        self.lbl_backup.grid(row=1, column=0, columnspan=3, sticky="w", padx=8)
        self.var_backup = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(f, text="Fazer backup automático diário ao abrir o sistema", variable=self.var_backup,
                      font=fonte(12)).grid(row=2, column=0, columnspan=2, sticky="w", padx=8, pady=8)
        self._campo(f, "backup_manter", "Quantos backups automáticos manter", 3, 0)
        botoes = ui.barra_botoes(f, [("Fazer backup agora", self._backup_agora, "primario", 190),
                                     ("Salvar cópia em… (pendrive)", self._backup_em, "secundario", 230),
                                     ("♻ Restaurar backup", self._restaurar, "perigo", 180),
                                     ("Abrir pasta de dados", lambda: recibos.abrir_arquivo(config.DADOS_DIR),
                                      "fantasma", 190)])
        botoes.grid(row=5, column=0, columnspan=3, sticky="w", padx=8, pady=12)
        self._ajuda(f, f"Pasta de dados: {config.DADOS_DIR}\nBanco de dados: {config.DB_PATH.name} · "
                       f"Recibos: {config.RECIBOS_DIR.name} · Relatórios: {config.RELATORIOS_DIR.name}\n"
                       "Dica: copie a pasta 'dados' regularmente para um pendrive ou para a nuvem.", 6)
        self._ajuda(f, f"{config.APP_NOME} · versão {config.APP_VERSAO}", 7)

    # ------------------------------------------------------------ carregar / salvar
    def atualizar(self, aba: str | None = None, **_kwargs):
        cfg = configuracoes.obter_todas()
        for chave, w in self.campos.items():
            ui.definir_texto(w, cfg.get(chave, ""))
        for chave, tb in self.textos.items():
            tb.delete("1.0", "end")
            tb.insert("1.0", cfg.get(chave, ""))
        self.seg_modo.set("API oficial (automático)" if cfg.get("whatsapp_modo") == "api"
                          else "WhatsApp Web / App (manual)")
        self.seg_abrir.set("Aplicativo WhatsApp Desktop" if cfg.get("whatsapp_abrir_em") == "app"
                           else "Navegador (WhatsApp Web)")
        self.var_auto.set(cfg.get("cobranca_automatica") == "1")
        self.var_backup.set(cfg.get("backup_automatico", "1") == "1")
        ultimo = cfg.get("ultimo_backup") or "nunca"
        qtd = len(list(config.BACKUP_DIR.glob("*.db"))) if config.BACKUP_DIR.exists() else 0
        self.lbl_backup.configure(text=f"Último backup automático: {ultimo} · {qtd} arquivo(s) de backup guardados.")
        self._carregar_usuarios()
        if aba:
            self.abas.set(aba)

    def _salvar(self):
        if not sessao.eh_administrador():
            ui.aviso("Somente administradores podem alterar as configurações.", parent=self)
            return
        valores = {chave: w.get().strip() for chave, w in self.campos.items()}
        for chave in ("tolerancia_dias", "multa_percentual", "juros_mes_percentual", "proximo_recibo",
                      "cobranca_intervalo_dias", "lembrete_dias_antes", "backup_manter"):
            try:
                float(valores[chave].replace(",", ".") or 0)
            except ValueError:
                ui.erro(f"Valor numérico inválido em '{chave}'.", parent=self)
                return
            valores[chave] = valores[chave].replace(",", ".") or "0"
        for chave, tb in self.textos.items():
            valores[chave] = utils.normalizar_texto(tb.get("1.0", "end-1c"))
        valores["whatsapp_modo"] = "api" if self.seg_modo.get().startswith("API") else "link"
        valores["whatsapp_abrir_em"] = "app" if self.seg_abrir.get().startswith("Aplicativo") else "web"
        valores["cobranca_automatica"] = "1" if self.var_auto.get() else "0"
        valores["backup_automatico"] = "1" if self.var_backup.get() else "0"
        configuracoes.salvar_varias(valores)
        database.registrar_auditoria("Configurações alteradas")
        acoes.notificar(self, "Configurações salvas ✔")

    def _restaurar_textos(self):
        for chave, tb in self.textos.items():
            tb.delete("1.0", "end")
            tb.insert("1.0", database.CONFIG_PADRAO[chave])

    def _testar_api(self):
        self._salvar()
        ok, detalhe = whatsapp.testar_api()
        (ui.info if ok else ui.erro)(detalhe, "Teste da API do WhatsApp", self)

    # ------------------------------------------------------------ usuários
    def _carregar_usuarios(self):
        self.usuarios = {str(u["id"]): u for u in usuarios.listar()}
        self.tab_usuarios.carregar([{"iid": k, "valores": (u["nome"], u["login"],
                                                           usuarios.PERFIS.get(u["perfil"], u["perfil"]),
                                                           "Ativo" if u["ativo"] else "Inativo", u["criado_em"]),
                                     "tag": None if u["ativo"] else "inativo"}
                                    for k, u in self.usuarios.items()])

    def _novo_usuario(self):
        from app.ui.dialogos.diversos import DialogoUsuario
        if not sessao.eh_administrador():
            ui.aviso("Somente administradores podem criar usuários.", parent=self)
            return
        if DialogoUsuario(self).aguardar():
            self._carregar_usuarios()

    def _trocar_senha(self):
        from app.ui.dialogos.diversos import DialogoSenha
        sel = self.tab_usuarios.selecionado()
        atual = sessao.usuario() or {}
        alvo = int(sel) if sel else atual.get("id")
        if alvo != atual.get("id") and not sessao.eh_administrador():
            ui.aviso("Você só pode trocar a sua própria senha.", parent=self)
            return
        if DialogoSenha(self, alvo).aguardar():
            acoes.notificar(self, "Senha alterada ✔")

    def _ativar_usuario(self):
        sel = self.tab_usuarios.selecionado()
        if not sel or not sessao.eh_administrador():
            ui.aviso("Selecione um usuário (somente administradores).", parent=self)
            return
        try:
            usuarios.definir_ativo(int(sel), not self.usuarios[sel]["ativo"])
        except ValueError as e:
            ui.erro(str(e), parent=self)
        self._carregar_usuarios()

    # ------------------------------------------------------------ backup
    def _backup_agora(self):
        caminho = backup.fazer_backup()
        ui.info(f"Backup criado:\n{caminho}", parent=self)
        self.atualizar()

    def _backup_em(self):
        destino = filedialog.asksaveasfilename(parent=self, title="Salvar backup em…", defaultextension=".db",
                                               initialfile=f"backup_shay_{date.today():%Y%m%d}.db",
                                               filetypes=[("Banco de dados", "*.db")])
        if destino:
            backup.fazer_backup(destino)
            ui.info(f"Backup salvo em:\n{destino}", parent=self)

    def _restaurar(self):
        if not sessao.eh_administrador():
            ui.aviso("Somente administradores podem restaurar backups.", parent=self)
            return
        arquivo = filedialog.askopenfilename(parent=self, title="Escolha o arquivo de backup",
                                             initialdir=str(config.BACKUP_DIR),
                                             filetypes=[("Banco de dados", "*.db")])
        if not arquivo:
            return
        if not ui.confirmar("Restaurar este backup vai SUBSTITUIR todos os dados atuais "
                            "(uma cópia do estado atual será guardada antes).\n\nContinuar?", parent=self):
            return
        try:
            seguranca = backup.restaurar(arquivo)
        except Exception as e:  # noqa: BLE001
            ui.erro(f"Não foi possível restaurar:\n{e}", parent=self)
            return
        ui.info(f"Backup restaurado! O sistema será fechado; abra-o novamente.\n\n"
                f"Cópia do estado anterior: {seguranca.name}", parent=self)
        self.app.destroy()
