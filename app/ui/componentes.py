"""
=============================================================================
 ui/componentes.py — Peças reutilizáveis da interface
=============================================================================
 Em vez de repetir código em cada tela, criamos aqui os "blocos de montar":
   • Cartao / CartaoIndicador  → caixas brancas arredondadas (painel)
   • botao()                   → botões com estilos padronizados
   • CampoData / CampoMoeda / CampoTelefone / CampoCPF → caixas de texto com
                                  máscara e validação
   • Tabela                    → tabela com rolagem, ordenação e cores por situação
   • DialogoBase               → janela secundária (modal) padrão
   • GraficoBarras             → gráfico simples desenhado na tela
   • mensagens (info/erro/confirmar)
=============================================================================
"""
from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

import customtkinter as ctk

from app.core import config, utils
from app.ui.tema import fonte

COR = config.CORES


# ---------------------------------------------------------------------------
# Caixas de mensagem
# ---------------------------------------------------------------------------

def info(texto: str, titulo: str = "Informação", parent=None) -> None:
    messagebox.showinfo(titulo, texto, parent=parent)


def aviso(texto: str, titulo: str = "Atenção", parent=None) -> None:
    messagebox.showwarning(titulo, texto, parent=parent)


def erro(texto: str, titulo: str = "Erro", parent=None) -> None:
    messagebox.showerror(titulo, texto, parent=parent)


def confirmar(texto: str, titulo: str = "Confirmar", parent=None) -> bool:
    return messagebox.askyesno(titulo, texto, parent=parent)


# ---------------------------------------------------------------------------
# Botões
# ---------------------------------------------------------------------------
_ESTILOS_BOTAO = {
    #              fundo                   hover                     texto                 borda
    "primario":   (COR["primaria"],         COR["primaria_escura"],   "#FFFFFF",            None),
    "destaque":   (COR["destaque"],         COR["destaque_escuro"],   "#FFFFFF",            None),
    "secundario": (COR["superficie"],       COR["primaria_suave"],    COR["primaria_profunda"], COR["primaria"]),
    "perigo":     (COR["superficie"],       COR["atraso_claro"],      COR["atraso"],        COR["atraso"]),
    "whatsapp":   (COR["whatsapp"],         COR["whatsapp_escuro"],   "#FFFFFF",            None),
    "fantasma":   ("transparent",           COR["primaria_suave"],    COR["primaria_profunda"], None),
}


def botao(master, texto: str, comando=None, estilo: str = "primario", largura: int = 120,
          altura: int = 36, **kwargs) -> ctk.CTkButton:
    """Cria um botão já com as cores do estilo escolhido."""
    fundo, hover, cor_texto, borda = _ESTILOS_BOTAO.get(estilo, _ESTILOS_BOTAO["primario"])
    return ctk.CTkButton(
        master, text=texto, command=comando, width=largura, height=altura, corner_radius=10,
        fg_color=fundo, hover_color=hover, text_color=cor_texto,
        border_width=1 if borda else 0,
        # o CustomTkinter não aceita borda "transparent"; sem borda, a cor não aparece
        border_color=borda or (fundo if fundo != "transparent" else COR["superficie"]),
        font=kwargs.pop("font", fonte(12, "bold")), **kwargs)


# ---------------------------------------------------------------------------
# Cartões e textos
# ---------------------------------------------------------------------------

class Cartao(ctk.CTkFrame):
    """Caixa branca arredondada com borda suave (base de quase todas as telas)."""
    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", COR["superficie"])
        kwargs.setdefault("corner_radius", 14)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", COR["borda"])
        super().__init__(master, **kwargs)


def titulo(master, texto: str, tamanho: int = 22) -> ctk.CTkLabel:
    return ctk.CTkLabel(master, text=texto, font=fonte(tamanho, "bold"),
                        text_color=COR["primaria_profunda"], anchor="w")


def subtitulo(master, texto: str, tamanho: int = 12) -> ctk.CTkLabel:
    return ctk.CTkLabel(master, text=texto, font=fonte(tamanho), text_color=COR["texto_suave"],
                        anchor="w", justify="left")


def rotulo(master, texto: str, obrigatorio: bool = False) -> ctk.CTkLabel:
    return ctk.CTkLabel(master, text=texto + (" *" if obrigatorio else ""), font=fonte(11, "bold"),
                        text_color=COR["texto_suave"], anchor="w")


class CartaoIndicador(Cartao):
    """Cartão do painel: título pequeno, número grande e legenda."""
    def __init__(self, master, titulo_txt: str, cor: str = COR["primaria"], icone: str = "●"):
        super().__init__(master)
        self.grid_columnconfigure(1, weight=1)
        faixa = ctk.CTkFrame(self, width=6, fg_color=cor, corner_radius=3)
        faixa.grid(row=0, column=0, rowspan=3, sticky="ns", padx=(12, 10), pady=14)
        ctk.CTkLabel(self, text=f"{icone}  {titulo_txt}", font=fonte(12, "bold"),
                     text_color=COR["texto_suave"], anchor="w").grid(row=0, column=1, sticky="w",
                                                                     pady=(14, 0), padx=(0, 12))
        self.valor = ctk.CTkLabel(self, text="—", font=fonte(24, "bold"), text_color=cor, anchor="w")
        self.valor.grid(row=1, column=1, sticky="w", padx=(0, 12))
        self.legenda = ctk.CTkLabel(self, text="", font=fonte(11), text_color=COR["texto_suave"],
                                    anchor="w")
        self.legenda.grid(row=2, column=1, sticky="w", pady=(0, 14), padx=(0, 12))

    def definir(self, valor: str, legenda: str = "") -> None:
        self.valor.configure(text=valor)
        self.legenda.configure(text=legenda)


class Etiqueta(ctk.CTkLabel):
    """Etiqueta colorida (ex.: situação 'Em atraso' em vermelho claro)."""
    def __init__(self, master, texto: str = "", situacao: str | None = None, **kwargs):
        super().__init__(master, text=texto, corner_radius=8, font=fonte(11, "bold"), height=24,
                         **kwargs)
        self.definir(texto, situacao)

    def definir(self, texto: str, situacao: str | None = None) -> None:
        forte, claro = config.COR_SITUACAO.get(situacao or texto, ("primaria_profunda", "primaria_clara"))
        self.configure(text=f"  {texto}  ", fg_color=COR[claro], text_color=COR[forte])


# ---------------------------------------------------------------------------
# Campos de digitação com máscara
# ---------------------------------------------------------------------------

def definir_texto(campo, texto) -> None:
    """Escreve num CTkEntry (mesmo se estiver desabilitado)."""
    estado = campo.cget("state")
    if estado == "disabled":
        campo.configure(state="normal")
    campo.delete(0, "end")
    if texto not in (None, ""):
        campo.insert(0, str(texto))
    if estado == "disabled":
        campo.configure(state="disabled")


class Campo(ctk.CTkEntry):
    """Caixa de texto padrão."""
    def __init__(self, master, largura: int = 200, **kwargs):
        kwargs.setdefault("height", 36)
        kwargs.setdefault("corner_radius", 9)
        kwargs.setdefault("font", fonte(12))
        super().__init__(master, width=largura, **kwargs)

    def valor(self) -> str:
        return self.get().strip()

    def definir(self, texto) -> None:
        definir_texto(self, texto)


class CampoData(Campo):
    """Data no formato DD/MM/AAAA — as barras são colocadas automaticamente."""
    def __init__(self, master, largura: int = 130, **kwargs):
        kwargs.setdefault("placeholder_text", "DD/MM/AAAA")
        super().__init__(master, largura, **kwargs)
        self.bind("<KeyRelease>", self._mascara)

    def _mascara(self, evento=None):
        if evento is not None and evento.keysym in ("BackSpace", "Delete", "Left", "Right", "Tab"):
            return
        d = utils.somente_digitos(self.get())[:8]
        texto = d[:2] + ("/" + d[2:4] if len(d) > 2 else "") + ("/" + d[4:] if len(d) > 4 else "")
        if texto != self.get():
            definir_texto(self, texto)
            self.icursor("end")

    def data(self) -> date | None:
        """Devolve a data digitada (ou None). Lança ValueError se estiver inválida."""
        return utils.ler_data(self.get())

    def definir(self, valor) -> None:
        definir_texto(self, utils.data_br(valor) if valor else "")


class CampoMoeda(Campo):
    """Valor em reais. Aceita '200', '200,50', '1.200,50'."""
    def __init__(self, master, largura: int = 130, **kwargs):
        kwargs.setdefault("placeholder_text", "0,00")
        super().__init__(master, largura, **kwargs)
        self.bind("<FocusOut>", self._formatar)

    def _formatar(self, _evento=None):
        if self.get().strip():
            try:
                definir_texto(self, utils.formatar_moeda(utils.ler_moeda(self.get()), simbolo=False))
            except ValueError:
                pass

    def numero(self) -> float:
        return utils.ler_moeda(self.get())

    def definir(self, valor) -> None:
        definir_texto(self, utils.formatar_moeda(valor, simbolo=False) if valor not in (None, "") else "")


class CampoTelefone(Campo):
    """Telefone: formata para (81) 99999-9999 ao sair do campo."""
    def __init__(self, master, largura: int = 170, **kwargs):
        kwargs.setdefault("placeholder_text", "(81) 99999-9999")
        super().__init__(master, largura, **kwargs)
        self.bind("<FocusOut>", lambda _e: definir_texto(self, utils.formatar_telefone(self.get())))


class CampoCPF(Campo):
    """CPF: formata para 000.000.000-00 e avisa (borda vermelha) se for inválido."""
    def __init__(self, master, largura: int = 160, **kwargs):
        kwargs.setdefault("placeholder_text", "000.000.000-00")
        super().__init__(master, largura, **kwargs)
        self.bind("<FocusOut>", self._validar)

    def _validar(self, _evento=None):
        definir_texto(self, utils.formatar_cpf(self.get()))
        valido = utils.validar_cpf(self.get())
        self.configure(border_color=COR["borda"] if valido else COR["atraso"])


def combo(master, valores: list[str], largura: int = 200, comando=None, editavel: bool = False,
          valor_inicial: str | None = None) -> ctk.CTkComboBox:
    """Caixa de seleção (lista suspensa)."""
    cb = ctk.CTkComboBox(master, values=valores, width=largura, height=36, corner_radius=9,
                         command=comando, state="normal" if editavel else "readonly",
                         font=fonte(12), dropdown_font=fonte(12))
    cb.set(valor_inicial if valor_inicial is not None else (valores[0] if valores else ""))
    return cb


def definir_combo(cb: ctk.CTkComboBox, valor: str) -> None:
    estado = cb.cget("state")
    cb.configure(state="normal")
    cb.set(valor or "")
    cb.configure(state=estado)


# ---------------------------------------------------------------------------
# Tabela
# ---------------------------------------------------------------------------

class Tabela(ctk.CTkFrame):
    """
    Tabela com rolagem.
      colunas: lista de (id, título, largura, alinhamento) — alinhamento 'w', 'center' ou 'e'
      carregar(linhas): linhas = [{'iid': '12', 'valores': (...), 'tag': 'atraso'}, ...]
    Clique no título da coluna para ordenar.
    """
    TAGS_SITUACAO = {
        config.SITUACAO_PAGO: "pago", config.SITUACAO_EM_DIA: "em_dia",
        config.SITUACAO_ATRASO: "atraso", config.SITUACAO_CANCELADO: "cancelado",
    }

    def __init__(self, master, colunas: list[tuple], altura: int = 12, multipla: bool = False,
                 ao_duplo_clique=None, ao_selecionar=None, texto_vazio: str = "Nenhum registro encontrado."):
        super().__init__(master, fg_color=COR["superficie"], corner_radius=12, border_width=1,
                         border_color=COR["borda"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(self, columns=[c[0] for c in colunas], show="headings",
                                 style="Shay.Treeview", height=altura,
                                 selectmode="extended" if multipla else "browse")
        for cid, titulo_col, largura, alinhamento in colunas:
            self.tree.heading(cid, text=titulo_col, command=lambda c=cid: self._ordenar(c))
            self.tree.column(cid, width=largura, minwidth=50, anchor=alinhamento, stretch=True)
        barra = ctk.CTkScrollbar(self, command=self.tree.yview)
        self.tree.configure(yscrollcommand=barra.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
        barra.grid(row=0, column=1, sticky="ns", pady=8, padx=(0, 4))

        # cores das linhas
        self.tree.tag_configure("par", background="#FFFFFF")
        self.tree.tag_configure("impar", background=COR["primaria_suave"])
        self.tree.tag_configure("pago", foreground=COR["pago"])
        self.tree.tag_configure("em_dia", foreground="#B7801F")
        self.tree.tag_configure("atraso", foreground=COR["atraso"])
        self.tree.tag_configure("cancelado", foreground=COR["cancelado"])
        self.tree.tag_configure("inativo", foreground=COR["cancelado"])

        self._vazio = ctk.CTkLabel(self, text=texto_vazio, font=fonte(12), text_color=COR["texto_suave"],
                                   fg_color="#FFFFFF")
        self._ordem: dict[str, bool] = {}
        if ao_duplo_clique:
            self.tree.bind("<Double-1>", lambda _e: ao_duplo_clique())
            self.tree.bind("<Return>", lambda _e: ao_duplo_clique())
        if ao_selecionar:
            self.tree.bind("<<TreeviewSelect>>", lambda _e: ao_selecionar())

    def carregar(self, linhas: list[dict]) -> None:
        self.tree.delete(*self.tree.get_children())
        for i, linha in enumerate(linhas):
            tags = ["par" if i % 2 == 0 else "impar"]
            if linha.get("tag"):
                tags.append(self.TAGS_SITUACAO.get(linha["tag"], linha["tag"]))
            self.tree.insert("", "end", iid=str(linha["iid"]), values=linha["valores"], tags=tags)
        if linhas:
            self._vazio.place_forget()
        else:
            self._vazio.place(relx=0.5, rely=0.5, anchor="center")

    def selecionado(self) -> str | None:
        sel = self.tree.selection()
        return sel[0] if sel else None

    def selecionados(self) -> list[str]:
        return list(self.tree.selection())

    def _ordenar(self, coluna: str) -> None:
        decrescente = self._ordem.get(coluna, False)
        itens = [(self.tree.set(i, coluna), i) for i in self.tree.get_children("")]

        def chave(par):
            texto = par[0]
            d = utils.para_date(texto) if len(texto) == 10 and "/" in texto else None
            if d:
                return (0, d.isoformat())
            try:
                return (1, utils.ler_moeda(texto))
            except ValueError:
                return (2, utils.sem_acentos(texto))

        itens.sort(key=chave, reverse=decrescente)
        for posicao, (_v, iid) in enumerate(itens):
            self.tree.move(iid, "", posicao)
            tags = [t for t in self.tree.item(iid, "tags") if t not in ("par", "impar")]
            self.tree.item(iid, tags=["par" if posicao % 2 == 0 else "impar", *tags])
        self._ordem[coluna] = not decrescente


# ---------------------------------------------------------------------------
# Janela secundária (diálogo)
# ---------------------------------------------------------------------------

class DialogoBase(ctk.CTkToplevel):
    """
    Janela que abre por cima da principal e bloqueia o resto até ser fechada.
    Subclasses montam o conteúdo em self.corpo e botões em self.rodape.
    """
    def __init__(self, master, titulo_janela: str, largura: int = 640, altura: int = 520):
        super().__init__(master)
        self.title(titulo_janela)
        self.configure(fg_color=COR["fundo"])
        self.resultado = None
        self.minsize(420, 300)
        raiz = master.winfo_toplevel()
        self.transient(raiz)
        # centraliza em relação à janela principal
        raiz.update_idletasks()
        x = raiz.winfo_rootx() + max(0, (raiz.winfo_width() - largura) // 2)
        y = raiz.winfo_rooty() + max(0, (raiz.winfo_height() - altura) // 2)
        self.geometry(f"{largura}x{altura}+{x}+{max(0, y)}")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        cab = ctk.CTkFrame(self, fg_color=COR["primaria"], corner_radius=0, height=54)
        cab.grid(row=0, column=0, sticky="ew")
        cab.grid_propagate(False)
        ctk.CTkLabel(cab, text=titulo_janela, font=fonte(16, "bold"), text_color="#FFFFFF").place(
            x=20, rely=0.5, anchor="w")
        self.corpo = ctk.CTkFrame(self, fg_color="transparent")
        self.corpo.grid(row=1, column=0, sticky="nsew", padx=20, pady=(16, 6))
        self.rodape = ctk.CTkFrame(self, fg_color="transparent")
        self.rodape.grid(row=2, column=0, sticky="ew", padx=20, pady=(6, 16))

        self.bind("<Escape>", lambda _e: self.fechar())
        self.protocol("WM_DELETE_WINDOW", self.fechar)
        self.after(250, self._icone)
        self.after(120, self._tornar_modal)

    def _icone(self):
        try:
            if config.ICONE_ICO.exists():
                self.iconbitmap(str(config.ICONE_ICO))
        except Exception:  # noqa: BLE001 — em Linux/Mac .ico pode não funcionar
            pass

    def _tornar_modal(self):
        try:
            self.lift()
            self.focus_force()
            self.grab_set()
        except Exception:  # noqa: BLE001
            pass

    def fechar(self, resultado=None):
        if resultado is not None:
            self.resultado = resultado
        try:
            self.grab_release()
        except Exception:  # noqa: BLE001
            pass
        pai = self.master.winfo_toplevel() if self.master is not None else None
        self.destroy()
        # se esta janela foi aberta por outra janela modal, devolve o foco para ela
        if isinstance(pai, DialogoBase) and pai.winfo_exists():
            pai._tornar_modal()

    def aguardar(self):
        """Espera a janela ser fechada e devolve self.resultado."""
        self.wait_window()
        return self.resultado


# ---------------------------------------------------------------------------
# Gráfico de barras (desenhado num Canvas, sem bibliotecas extras)
# ---------------------------------------------------------------------------

class GraficoBarras(tk.Canvas):
    """
    Gráfico de barras agrupadas.
      dados:  [{'rotulo': 'Set/26', 'valores': [320.0, 400.0]}, ...]
      series: [('Recebido', '#86B3B5'), ('Previsto', '#F4A9A3')]
    """
    def __init__(self, master, series: list[tuple[str, str]], altura: int = 230, moeda: bool = True):
        super().__init__(master, height=altura, bg=COR["superficie"], highlightthickness=0)
        self.series = series
        self.dados: list[dict] = []
        self.moeda = moeda
        self.bind("<Configure>", lambda _e: self.desenhar())

    def definir_dados(self, dados: list[dict]) -> None:
        self.dados = dados
        self.desenhar()

    def desenhar(self) -> None:
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 50 or not self.dados:
            return
        esq, dir_, topo, base = 64, 12, 30, h - 28
        maximo = max([max(d["valores"]) for d in self.dados] + [1])
        # arredonda o topo da escala
        passo = 10 ** max(0, len(str(int(maximo))) - 1)
        maximo = ((int(maximo) // passo) + 1) * passo
        fonte_txt = (config.FONTE, 9)
        for i in range(5):  # linhas de grade
            y = base - (base - topo) * i / 4
            self.create_line(esq, y, w - dir_, y, fill=COR["borda"])
            valor = maximo * i / 4
            texto = utils.formatar_moeda(valor).replace(",00", "") if self.moeda else f"{valor:.0f}"
            self.create_text(esq - 6, y, text=texto, anchor="e", fill=COR["texto_suave"], font=fonte_txt)
        grupo = (w - esq - dir_) / len(self.dados)
        n = len(self.series)
        larg_barra = min(26, grupo * 0.7 / n)
        for gi, d in enumerate(self.dados):
            x0 = esq + gi * grupo + (grupo - larg_barra * n - 4 * (n - 1)) / 2
            for si, valor in enumerate(d["valores"]):
                altura_barra = (base - topo) * (valor / maximo if maximo else 0)
                xa = x0 + si * (larg_barra + 4)
                self.create_rectangle(xa, base - altura_barra, xa + larg_barra, base,
                                      fill=self.series[si][1], outline="")
            self.create_text(esq + gi * grupo + grupo / 2, base + 14, text=d["rotulo"],
                             fill=COR["texto_suave"], font=fonte_txt)
        # legenda
        x = esq
        for nome, cor in self.series:
            self.create_rectangle(x, 8, x + 12, 20, fill=cor, outline="")
            self.create_text(x + 18, 14, text=nome, anchor="w", fill=COR["texto"], font=fonte_txt)
            x += 30 + len(nome) * 7


# ---------------------------------------------------------------------------
# Barra de ações (fileira de botões)
# ---------------------------------------------------------------------------

def barra_botoes(master, botoes: list[tuple], coluna_inicial: int = 0) -> ctk.CTkFrame:
    """
    Cria uma fileira de botões.
      botoes: [(texto, comando, estilo, largura), ...]
    """
    barra = ctk.CTkFrame(master, fg_color="transparent")
    for i, item in enumerate(botoes):
        texto, comando, estilo = item[0], item[1], item[2] if len(item) > 2 else "secundario"
        largura = item[3] if len(item) > 3 else 120
        botao(barra, texto, comando, estilo, largura).grid(row=0, column=coluna_inicial + i, padx=(0, 8),
                                                            pady=2)
    return barra
