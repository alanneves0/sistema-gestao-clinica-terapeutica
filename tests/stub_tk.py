"""
=============================================================================
 tests/stub_tk.py — "Tela falsa" para testar a interface sem abrir janelas
=============================================================================
 Substitui tkinter/customtkinter por imitações simples que guardam valores
 (texto digitado, linhas de tabela, seleção) mas não desenham nada.
 Assim os testes automáticos conseguem montar TODAS as telas, preencher
 formulários e clicar em botões, mesmo num computador sem monitor.
 Usado apenas por tests/test_interface.py.
=============================================================================
"""
from __future__ import annotations

import sys
import types

REGISTRO = {"mensagens": [], "responder_sim": True}


class Var:
    def __init__(self, master=None, value=None, name=None):
        self._v = value

    def get(self):
        return self._v

    def set(self, v):
        self._v = v


class StringVar(Var):
    def __init__(self, master=None, value="", name=None):
        super().__init__(master, value)


class BooleanVar(Var):
    def __init__(self, master=None, value=False, name=None):
        super().__init__(master, value)

    def get(self):
        return bool(self._v)


class IntVar(Var):
    def __init__(self, master=None, value=0, name=None):
        super().__init__(master, value)


class TclError(Exception):
    pass


class W:
    """Widget genérico: aceita qualquer método, guarda configuração."""
    _raiz = None

    def __init__(self, master=None, *args, **kw):
        self.master = master
        self._cfg = dict(kw)
        self._filhos = []
        self._destruido = False
        self._texto = ""
        if isinstance(master, W):
            master._filhos.append(self)
        if master is None and W._raiz is None:
            W._raiz = self

    # configuração
    def configure(self, *_a, **kw):
        self._cfg.update(kw)

    config = configure

    def cget(self, chave):
        return self._cfg.get(chave, "normal" if chave == "state" else "")

    # Métodos do Tk que simplesmente não fazem nada na tela falsa.
    # Qualquer outro nome desconhecido gera AttributeError (para pegar erros de digitação).
    _PREFIXOS_OK = ("winfo_", "grid", "pack", "place", "tag_", "create_", "column", "heading", "bind",
                    "focus", "grab_", "yview", "xview", "after_cancel", "unbind", "update")
    _NOMES_OK = {"iconbitmap", "title", "geometry", "minsize", "resizable", "transient", "protocol",
                 "lift", "tkraise", "state", "attributes", "icursor", "theme_use", "layout", "map",
                 "mainloop", "set", "select", "deselect", "see", "quit", "report_callback_exception"}

    def __getattr__(self, nome):
        if nome in W._NOMES_OK or nome.startswith(W._PREFIXOS_OK):
            return lambda *a, **k: None
        raise AttributeError(f"{type(self).__name__} não tem '{nome}'")

    # árvore
    def winfo_children(self):
        return [f for f in self._filhos if not f._destruido]

    def winfo_toplevel(self):
        w = self
        while isinstance(w.master, W) and not isinstance(w, (CTk, CTkToplevel)):
            w = w.master
        return w

    def winfo_exists(self):
        return not self._destruido

    def winfo_width(self):
        return 1000

    def winfo_height(self):
        return 700

    def winfo_rootx(self):
        return 0

    winfo_rooty = winfo_rootx

    def destroy(self):
        self._destruido = True
        for f in self._filhos:
            f.destroy()

    def after(self, ms, func=None, *args):
        if func and ms < 1000:
            func(*args)
        return "after#1"

    def wait_window(self, *a):
        return None


class CTk(W):
    pass


class Canvas(W):
    def delete(self, *_a):
        pass


class CTkToplevel(W):
    pass


class CTkEntry(W):
    def get(self):
        return self._texto

    def insert(self, _i, texto):
        self._texto = self._texto + str(texto)

    def delete(self, *_a):
        self._texto = ""


class CTkTextbox(W):
    def get(self, *_a):
        return self._texto + ("\n" if _a and _a[-1] == "end" else "")

    def insert(self, _i, texto):
        self._texto += str(texto)

    def delete(self, *_a):
        self._texto = ""


class CTkComboBox(W):
    def __init__(self, master=None, *a, **kw):
        super().__init__(master, *a, **kw)
        self._valor = ""
        self._cmd = kw.get("command")

    def set(self, v):
        self._valor = v

    def get(self):
        return self._valor

    def escolher(self, v):
        self._valor = v
        if self._cmd:
            self._cmd(v)


CTkOptionMenu = CTkComboBox


class CTkSegmentedButton(CTkComboBox):
    pass


class CTkTabview(W):
    def __init__(self, master=None, *a, **kw):
        super().__init__(master, *a, **kw)
        self._abas = {}
        self._atual = None

    def add(self, nome):
        self._abas[nome] = W(self)
        self._atual = self._atual or nome
        return self._abas[nome]

    def tab(self, nome):
        return self._abas[nome]

    def set(self, nome):
        self._atual = nome

    def get(self):
        return self._atual


class CTkInputDialog(W):
    def get_input(self):
        return "3"


class Treeview(W):
    def __init__(self, master=None, *a, **kw):
        super().__init__(master, *a, **kw)
        self._colunas = list(kw.get("columns", []))
        self._itens: dict = {}
        self._ordem: list = []
        self._sel: list = []

    def insert(self, _pai, _pos, iid=None, values=(), tags=()):
        self._itens[iid] = {"values": list(values), "tags": list(tags)}
        self._ordem.append(iid)
        return iid

    def delete(self, *iids):
        for i in iids:
            self._itens.pop(i, None)
            if i in self._ordem:
                self._ordem.remove(i)
        self._sel = [s for s in self._sel if s in self._itens]

    def get_children(self, *_a):
        return tuple(self._ordem)

    def selection(self):
        return tuple(self._sel)

    def selection_set(self, *iids):
        self._sel = [i for i in iids if i in self._itens]

    def selection_remove(self, *iids):
        self._sel = [s for s in self._sel if s not in iids]

    def set(self, iid, coluna):
        return str(self._itens[iid]["values"][self._colunas.index(coluna)])

    def move(self, iid, _pai, pos):
        self._ordem.remove(iid)
        self._ordem.insert(pos, iid)

    def item(self, iid, opcao=None, **kw):
        if "tags" in kw:
            self._itens[iid]["tags"] = list(kw["tags"])
        if opcao == "tags":
            return tuple(self._itens[iid]["tags"])
        return self._itens[iid]


def _modulo(nome, **atributos):
    m = types.ModuleType(nome)
    m.__dict__.update(atributos)
    m.__getattr__ = lambda n: W  # qualquer outro widget vira W
    return m


def _msg(tipo):
    def f(titulo, texto="", **_k):
        REGISTRO["mensagens"].append((tipo, titulo, texto))
        return REGISTRO["responder_sim"] if tipo == "askyesno" else None
    return f


def instalar():
    """Coloca os módulos falsos no lugar dos verdadeiros."""
    tk = _modulo("tkinter", Tk=CTk, Toplevel=CTkToplevel, Frame=W, Canvas=Canvas, StringVar=StringVar,
                 BooleanVar=BooleanVar, IntVar=IntVar, TclError=TclError)
    ttk = _modulo("tkinter.ttk", Treeview=Treeview, Style=W, Scrollbar=W)
    mb = _modulo("tkinter.messagebox", **{n: _msg(n) for n in
                                          ("showinfo", "showwarning", "showerror", "askyesno")})
    fd = _modulo("tkinter.filedialog", askopenfilename=lambda **k: "", asksaveasfilename=lambda **k: "")
    tk.ttk, tk.messagebox, tk.filedialog = ttk, mb, fd
    ctk = _modulo(
        "customtkinter", CTk=CTk, CTkToplevel=CTkToplevel, CTkEntry=CTkEntry, CTkTextbox=CTkTextbox,
        CTkComboBox=CTkComboBox, CTkOptionMenu=CTkOptionMenu, CTkSegmentedButton=CTkSegmentedButton,
        CTkTabview=CTkTabview, CTkInputDialog=CTkInputDialog, StringVar=StringVar,
        BooleanVar=BooleanVar, IntVar=IntVar,
        set_appearance_mode=lambda *a: None, set_default_color_theme=lambda *a: None,
        set_widget_scaling=lambda *a: None)
    for nome in ("CTkFrame", "CTkScrollableFrame", "CTkLabel", "CTkButton", "CTkCheckBox", "CTkSwitch",
                 "CTkRadioButton", "CTkProgressBar", "CTkScrollbar", "CTkImage", "CTkFont", "CTkCanvas"):
        setattr(ctk, nome, type(nome, (W,), {}))
    sys.modules.update({"tkinter": tk, "tkinter.ttk": ttk, "tkinter.messagebox": mb,
                        "tkinter.filedialog": fd, "customtkinter": ctk})
