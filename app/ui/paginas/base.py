"""
=============================================================================
 ui/paginas/base.py — Modelo comum a todas as telas (páginas)
=============================================================================
 Cada página tem um cabeçalho (título + subtítulo + botões à direita) e um
 método atualizar(), chamado sempre que a página é exibida.
=============================================================================
"""
from __future__ import annotations

import customtkinter as ctk

from app.core import config
from app.ui import componentes as ui


class Pagina(ctk.CTkFrame):
    TITULO = ""
    SUBTITULO = ""

    def __init__(self, master, app):
        super().__init__(master, fg_color=config.CORES["fundo"], corner_radius=0)
        self.app = app  # janela principal (para navegar entre páginas)
        self.grid_columnconfigure(0, weight=1)
        self.cabecalho = ctk.CTkFrame(self, fg_color="transparent")
        self.cabecalho.grid(row=0, column=0, sticky="ew", padx=28, pady=(22, 8))
        self.cabecalho.grid_columnconfigure(0, weight=1)
        ui.titulo(self.cabecalho, self.TITULO).grid(row=0, column=0, sticky="w")
        self.lbl_subtitulo = ui.subtitulo(self.cabecalho, self.SUBTITULO)
        self.lbl_subtitulo.grid(row=1, column=0, sticky="w")
        self.acoes_cabecalho = ctk.CTkFrame(self.cabecalho, fg_color="transparent")
        self.acoes_cabecalho.grid(row=0, column=1, rowspan=2, sticky="e")
        # área de conteúdo de cada página
        self.conteudo = ctk.CTkFrame(self, fg_color="transparent")
        self.conteudo.grid(row=1, column=0, sticky="nsew", padx=28, pady=(4, 20))
        self.grid_rowconfigure(1, weight=1)

    def atualizar(self, **_kwargs):
        """Recarrega os dados da página (implementado em cada página)."""
