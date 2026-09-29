"""
=============================================================================
 ui/tema.py — Aparência (cores e fontes) da interface
=============================================================================
 O visual usa a biblioteca CustomTkinter (botões arredondados, visual moderno).
 Aqui nós:
   1. criamos um TEMA de cores próprio a partir da paleta da logo
      (verde-água + rosa), aplicado a todos os botões, caixas, abas etc.;
   2. padronizamos as FONTES;
   3. estilizamos as TABELAS (ttk.Treeview).
=============================================================================
"""
from __future__ import annotations

import json
from pathlib import Path
from tkinter import ttk

import customtkinter as ctk

from app.core import config

COR = config.CORES
_fontes: dict = {}


def _par(cor: str) -> list[str]:
    """O CustomTkinter usa [cor_modo_claro, cor_modo_escuro]; usamos a mesma nas duas."""
    return [cor, cor]


def aplicar_tema() -> None:
    """Gera o arquivo de tema com as cores da marca e aplica no CustomTkinter."""
    ctk.set_appearance_mode("light")
    ctk.set_widget_scaling(1.0)
    try:
        base = Path(ctk.__file__).parent / "assets" / "themes" / "blue.json"
        tema = json.loads(base.read_text(encoding="utf-8"))
        p, pe, pc = COR["primaria"], COR["primaria_escura"], COR["primaria_clara"]
        ajustes = {
            "CTk": {"fg_color": _par(COR["fundo"])},
            "CTkToplevel": {"fg_color": _par(COR["fundo"])},
            "CTkFrame": {"fg_color": _par(COR["superficie"]), "top_fg_color": _par(COR["superficie"]),
                         "border_color": _par(COR["borda"])},
            "CTkButton": {"fg_color": _par(p), "hover_color": _par(pe), "border_color": _par(pe),
                          "text_color": _par("#FFFFFF"), "text_color_disabled": _par("#C9D6D7")},
            "CTkLabel": {"text_color": _par(COR["texto"])},
            "CTkEntry": {"fg_color": _par("#FFFFFF"), "border_color": _par(COR["borda"]),
                         "text_color": _par(COR["texto"]),
                         "placeholder_text_color": _par("#A3B5B6")},
            "CTkCheckBox": {"fg_color": _par(p), "hover_color": _par(pe), "border_color": _par(p),
                            "checkmark_color": _par("#FFFFFF"), "text_color": _par(COR["texto"])},
            "CTkSwitch": {"progress_color": _par(p), "button_color": _par("#FFFFFF"),
                          "button_hover_color": _par(pc), "fg_color": _par("#D5E0E1"),
                          "text_color": _par(COR["texto"])},
            "CTkRadioButton": {"fg_color": _par(p), "hover_color": _par(pe), "border_color": _par(p),
                               "text_color": _par(COR["texto"])},
            "CTkProgressBar": {"progress_color": _par(p), "fg_color": _par(pc)},
            "CTkSlider": {"button_color": _par(p), "button_hover_color": _par(pe),
                          "progress_color": _par(p)},
            "CTkOptionMenu": {"fg_color": _par(p), "button_color": _par(pe),
                              "button_hover_color": _par(COR["primaria_profunda"])},
            "CTkComboBox": {"fg_color": _par("#FFFFFF"), "border_color": _par(COR["borda"]),
                            "button_color": _par(COR["borda"]), "button_hover_color": _par(p),
                            "text_color": _par(COR["texto"])},
            "CTkScrollbar": {"button_color": _par(pc), "button_hover_color": _par(p)},
            "CTkSegmentedButton": {"fg_color": _par(pc), "selected_color": _par(p),
                                   "selected_hover_color": _par(pe), "unselected_color": _par(pc),
                                   "unselected_hover_color": _par("#C8DFE0"),
                                   "text_color": _par(COR["primaria_profunda"])},
            "CTkTextbox": {"fg_color": _par("#FFFFFF"), "border_color": _par(COR["borda"]),
                           "text_color": _par(COR["texto"])},
            "CTkScrollableFrame": {"label_fg_color": _par(pc)},
            "DropdownMenu": {"fg_color": _par("#FFFFFF"), "hover_color": _par(pc),
                             "text_color": _par(COR["texto"])},
        }
        for widget, valores in ajustes.items():
            if widget in tema:
                for chave, valor in valores.items():
                    if chave in tema[widget]:
                        tema[widget][chave] = valor
        # Fonte padrão de todos os componentes
        if "CTkFont" in tema:
            for sistema in tema["CTkFont"].values():
                if isinstance(sistema, dict):
                    sistema["family"] = config.FONTE
        config.garantir_pastas()
        destino = config.DADOS_DIR / "tema_shay.json"
        destino.write_text(json.dumps(tema, indent=1), encoding="utf-8")
        ctk.set_default_color_theme(str(destino))
    except Exception:  # noqa: BLE001 — se algo falhar, usa o tema padrão
        ctk.set_default_color_theme("blue")


def fonte(tamanho: int = 13, peso: str = "normal") -> ctk.CTkFont:
    """Devolve uma fonte padronizada (criada uma única vez e reaproveitada)."""
    chave = (tamanho, peso)
    if chave not in _fontes:
        _fontes[chave] = ctk.CTkFont(family=config.FONTE, size=tamanho, weight=peso)
    return _fontes[chave]


def estilizar_tabelas(raiz) -> None:
    """Deixa as tabelas (ttk.Treeview) com a cara do restante do sistema."""
    estilo = ttk.Style(raiz)
    try:
        estilo.theme_use("clam")
    except Exception:  # noqa: BLE001
        pass
    estilo.configure("Shay.Treeview", background="#FFFFFF", fieldbackground="#FFFFFF",
                     foreground=COR["texto"], rowheight=34, borderwidth=0, relief="flat",
                     font=(config.FONTE, 10))
    estilo.configure("Shay.Treeview.Heading", background=COR["primaria_clara"],
                     foreground=COR["primaria_profunda"], font=(config.FONTE, 10, "bold"),
                     relief="flat", borderwidth=0, padding=(6, 8))
    estilo.map("Shay.Treeview.Heading", background=[("active", COR["primaria"])],
               foreground=[("active", "#FFFFFF")])
    estilo.map("Shay.Treeview", background=[("selected", COR["primaria"])],
               foreground=[("selected", "#FFFFFF")])
    estilo.layout("Shay.Treeview", [("Shay.Treeview.treearea", {"sticky": "nswe"})])
