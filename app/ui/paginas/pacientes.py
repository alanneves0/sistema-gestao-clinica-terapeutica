"""
=============================================================================
 ui/paginas/pacientes.py — Lista de pacientes
=============================================================================
 Busca por nome do paciente/responsável, CPF ou telefone, com filtros por
 situação (ativos/inativos), faixa etária e diagnóstico. A coluna
 "Financeiro" mostra se o paciente está em dia ou em atraso.
 Duplo clique abre o cadastro para edição.
=============================================================================
"""
from __future__ import annotations


from app.core import config, sessao, utils
from app.repositorios import financeiro, pacientes
from app.ui import acoes
from app.ui import componentes as ui
from app.ui.paginas.base import Pagina

COR = config.CORES


class PaginaPacientes(Pagina):
    TITULO = "Pacientes"
    SUBTITULO = "Cadastro de pacientes e responsáveis"

    def __init__(self, master, app):
        super().__init__(master, app)
        ui.botao(self.acoes_cabecalho, "+ Novo paciente", lambda: self.app.mostrar("cadastro"),
                 "primario", 160).grid(row=0, column=0)

        c = self.conteudo
        c.grid_columnconfigure(0, weight=1)
        c.grid_rowconfigure(2, weight=1)

        # Filtros
        filtros = ui.Cartao(c)
        filtros.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.busca = ui.Campo(filtros, 330, placeholder_text="Buscar paciente, responsável, CPF ou telefone")
        self.busca.grid(row=0, column=0, padx=(14, 8), pady=12)
        self.busca.bind("<KeyRelease>", lambda _e: self._agendar_busca())
        self.situacao = ui.combo(filtros, ["Ativos", "Inativos", "Todos"], 120, lambda _v: self.atualizar())
        self.situacao.grid(row=0, column=1, padx=4)
        self.faixa = ui.combo(filtros, config.FAIXAS_ETARIAS, 170, lambda _v: self.atualizar())
        self.faixa.grid(row=0, column=2, padx=4)
        self.diag = ui.combo(filtros, ["Todos"] + config.DIAGNOSTICOS, 200, lambda _v: self.atualizar())
        self.diag.grid(row=0, column=3, padx=4)
        self.lbl_total = ui.subtitulo(filtros, "")
        self.lbl_total.grid(row=0, column=4, padx=14)

        # Ações
        barra = ui.barra_botoes(c, [
            ("✎ Editar", self._editar, "secundario", 100),
            ("$ Ficha financeira", self._ficha, "primario", 160),
            ("+ Incluir serviço", self._contrato, "secundario", 150),
            ("✉ WhatsApp", self._whats, "whatsapp", 120),
            ("Inativar / Reativar", self._ativar, "secundario", 160),
            ("✕ Excluir", self._excluir, "perigo", 100),
        ])
        barra.grid(row=1, column=0, sticky="w", pady=(0, 8))

        self.tabela = ui.Tabela(c, [
            ("nome", "Paciente", 220, "w"), ("idade", "Idade", 70, "center"),
            ("diag", "Diagnósticos", 200, "w"), ("resp", "Responsável", 200, "w"),
            ("whats", "WhatsApp", 130, "center"), ("fin", "Financeiro", 140, "center")],
            altura=16, ao_duplo_clique=self._editar)
        self.tabela.grid(row=2, column=0, sticky="nsew")
        self._job = None

    def _agendar_busca(self):
        """Espera o usuário parar de digitar (300 ms) antes de buscar."""
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(300, self.atualizar)

    def atualizar(self, **_kwargs):
        ativos = {"Ativos": True, "Inativos": False, "Todos": None}[self.situacao.get()]
        lista = pacientes.listar(self.busca.valor(), ativos, self.faixa.get(), self.diag.get())
        situacoes = financeiro.situacao_por_paciente()
        self.pacientes = {str(p["id"]): p for p in lista}
        linhas = []
        for p in lista:
            sit = situacoes.get(p["id"], "")
            texto_sit = {config.SITUACAO_PAGO: "Em dia ✔", config.SITUACAO_EM_DIA: "Pendente (em dia)",
                         config.SITUACAO_ATRASO: "⚠ Em atraso"}.get(sit, "Sem cobranças")
            linhas.append({"iid": p["id"], "valores": (
                p["nome"], utils.texto_idade(p.get("data_nascimento")),
                (p.get("diagnosticos") or "").replace(";", ","),
                p.get("responsavel_nome") or "", p.get("responsavel_whatsapp") or p.get("responsavel_telefone") or "",
                texto_sit), "tag": "inativo" if not p["ativo"] else (sit or None)})
        self.tabela.carregar(linhas)
        self.lbl_total.configure(text=f"{len(lista)} paciente(s)")

    # ------------------------------------------------------------------ ações
    def _sel(self) -> dict | None:
        sel = self.tabela.selecionado()
        if not sel:
            ui.aviso("Selecione um paciente na lista.", parent=self)
            return None
        return self.pacientes[sel]

    def _editar(self):
        p = self._sel()
        if p:
            self.app.mostrar("cadastro", paciente_id=p["id"])

    def _ficha(self):
        p = self._sel()
        if p:
            acoes.abrir_ficha(self, p["id"], self.atualizar)

    def _contrato(self):
        p = self._sel()
        if p:
            acoes.novo_contrato(self, p["id"], p["nome"], self.atualizar)

    def _whats(self):
        p = self._sel()
        if p:
            acoes.conversar(self, p.get("responsavel_nome") or p["nome"],
                            p.get("responsavel_whatsapp") or p.get("responsavel_telefone") or "",
                            p.get("responsavel_id"), p["id"])

    def _ativar(self):
        p = self._sel()
        if not p:
            return
        if p["ativo"]:
            if ui.confirmar(f"Inativar {p['nome']}?\n\nOs serviços ativos serão ENCERRADOS "
                            "(parcelas em aberto continuam na lista de cobrança).", parent=self):
                pacientes.definir_ativo(p["id"], False)
        else:
            pacientes.definir_ativo(p["id"], True)
        self.atualizar()

    def _excluir(self):
        p = self._sel()
        if not p:
            return
        if not sessao.eh_administrador():
            ui.aviso("Somente administradores podem excluir pacientes. Use 'Inativar'.", parent=self)
            return
        if ui.confirmar(f"EXCLUIR DEFINITIVAMENTE {p['nome']}?\n\nTodo o histórico financeiro "
                        "(parcelas e pagamentos) será apagado. Esta ação não pode ser desfeita.\n\n"
                        "Dica: prefira 'Inativar'.", "Excluir paciente", self):
            pacientes.excluir(p["id"])
            self.atualizar()
