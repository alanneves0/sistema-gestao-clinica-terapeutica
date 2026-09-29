"""
=============================================================================
 ui/paginas/servicos.py — Tabela de serviços e preços
=============================================================================
 Lista as terapias/pacotes com seus valores. Alterar um preço aqui vale para
 os NOVOS contratos; contratos já criados mantêm os valores combinados
 (para mudar parcelas existentes use "Editar parcela" no Financeiro).
=============================================================================
"""
from __future__ import annotations

from app.core import config, sessao, utils
from app.repositorios import servicos
from app.ui import componentes as ui
from app.ui.paginas.base import Pagina


class PaginaServicos(Pagina):
    TITULO = "Serviços e preços"
    SUBTITULO = "Valores usados ao incluir um serviço para o paciente"

    def __init__(self, master, app):
        super().__init__(master, app)
        ui.botao(self.acoes_cabecalho, "+ Novo serviço", self._novo, "primario", 150).grid(row=0, column=0)
        c = self.conteudo
        c.grid_columnconfigure(0, weight=1)
        c.grid_rowconfigure(1, weight=1)
        ui.barra_botoes(c, [("✎ Editar", self._editar, "secundario", 100),
                            ("Ativar / Desativar", self._ativar, "secundario", 160)]).grid(
            row=0, column=0, sticky="w", pady=(0, 8))
        self.tabela = ui.Tabela(c, [
            ("nome", "Serviço", 300, "w"), ("cat", "Categoria", 100, "center"),
            ("tipo", "Cobrança", 130, "center"), ("cheio", "Valor cheio / total", 140, "e"),
            ("pont", "Até o vencimento", 130, "e"), ("parc", "Parcelas", 80, "center"),
            ("ent", "Entrada", 100, "e"), ("ativo", "Situação", 90, "center")],
            altura=16, ao_duplo_clique=self._editar)
        self.tabela.grid(row=1, column=0, sticky="nsew")
        ui.subtitulo(c, "Valores iniciais cadastrados a partir dos carnês do Espaço. "
                        "“Até o vencimento” é o valor com desconto de pontualidade.", 11).grid(
            row=2, column=0, sticky="w", pady=(8, 0))

    def atualizar(self, **_kwargs):
        self.lista = {str(s["id"]): s for s in servicos.listar()}
        self.tabela.carregar([{
            "iid": k,
            "valores": (s["nome"], s["categoria"], config.TIPOS_COBRANCA.get(s["tipo_cobranca"], ""),
                        utils.formatar_moeda(s["valor_cheio"]), utils.formatar_moeda(s["valor_pontualidade"]),
                        s["parcelas_padrao"], utils.formatar_moeda(s["valor_entrada"]) if s["valor_entrada"] else "—",
                        "Ativo" if s["ativo"] else "Inativo"),
            "tag": None if s["ativo"] else "inativo"} for k, s in self.lista.items()])

    def _pode_editar(self) -> bool:
        if not sessao.eh_administrador():
            ui.aviso("Somente administradores podem alterar preços.", parent=self)
            return False
        return True

    def _novo(self):
        from app.ui.dialogos.diversos import DialogoServico
        if self._pode_editar() and DialogoServico(self).aguardar():
            self.atualizar()

    def _editar(self):
        from app.ui.dialogos.diversos import DialogoServico
        sel = self.tabela.selecionado()
        if not sel:
            ui.aviso("Selecione um serviço.", parent=self)
            return
        if self._pode_editar() and DialogoServico(self, int(sel)).aguardar():
            self.atualizar()

    def _ativar(self):
        sel = self.tabela.selecionado()
        if sel and self._pode_editar():
            servicos.definir_ativo(int(sel), not self.lista[sel]["ativo"])
            self.atualizar()
