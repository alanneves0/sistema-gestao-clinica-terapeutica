"""
=============================================================================
 ui/paginas/cobrancas.py — Cobranças e lembretes por WhatsApp
=============================================================================
 • Aba "Em atraso": responsáveis com parcelas vencidas (agrupadas por
   responsável — irmãos aparecem numa única mensagem).
 • Aba "Lembretes": parcelas que vencem nos próximos dias.
 • Aba "Histórico": tudo que já foi enviado.

 Modo LINK: o sistema abre o WhatsApp com a mensagem pronta, um responsável
            por vez; você só aperta ENVIAR.
 Modo API : envio automático pela API oficial do WhatsApp (ver Configurações).
=============================================================================
"""
from __future__ import annotations

import customtkinter as ctk

from app.core import config, utils
from app.repositorios import configuracoes, financeiro, mensagens
from app.servicos import cobranca, recibos, relatorios, whatsapp
from app.ui import acoes
from app.ui import componentes as ui
from app.ui.paginas.base import Pagina
from app.ui.tema import fonte

COR = config.CORES


class PaginaCobrancas(Pagina):
    TITULO = "Cobranças por WhatsApp"
    SUBTITULO = "Envie cobranças de atraso e lembretes de vencimento aos responsáveis"

    def __init__(self, master, app):
        super().__init__(master, app)
        self.lbl_modo = ui.Etiqueta(self.acoes_cabecalho, "")
        self.lbl_modo.grid(row=0, column=0, padx=(0, 8))
        ui.botao(self.acoes_cabecalho, "⚙ Configurar WhatsApp", lambda: self.app.mostrar("configuracoes", aba="WhatsApp"),
                 "secundario", 190).grid(row=0, column=1)

        c = self.conteudo
        c.grid_columnconfigure(0, weight=1)
        c.grid_rowconfigure(0, weight=1)
        self.abas = ctk.CTkTabview(c, fg_color=COR["fundo"], corner_radius=14,
                                   segmented_button_fg_color=COR["primaria_clara"],
                                   segmented_button_selected_color=COR["primaria"],
                                   segmented_button_selected_hover_color=COR["primaria_escura"],
                                   segmented_button_unselected_color=COR["primaria_clara"],
                                   segmented_button_unselected_hover_color="#C8DFE0",
                                   text_color=COR["primaria_profunda"], command=self.atualizar)
        self.abas.grid(row=0, column=0, sticky="nsew")
        for aba in ("Em atraso", "Lembretes de vencimento", "Histórico de mensagens"):
            self.abas.add(aba)
        self.lista_atraso = self._montar_lista(self.abas.tab("Em atraso"), "atraso")
        self.lista_lembrete = self._montar_lista(self.abas.tab("Lembretes de vencimento"), "lembrete")
        self._montar_historico(self.abas.tab("Histórico de mensagens"))

    # ----------------------------------------------------------------------
    def _montar_lista(self, aba, tipo: str) -> dict:
        aba.grid_columnconfigure(0, weight=1)
        aba.grid_rowconfigure(2, weight=1)
        topo = ui.Cartao(aba)
        topo.grid(row=0, column=0, sticky="ew", pady=(4, 8))
        var_fila = ctk.BooleanVar(value=True)
        texto_fila = ("Mostrar só quem não foi cobrado recentemente" if tipo == "atraso"
                      else "Mostrar só quem ainda não recebeu lembrete")
        ctk.CTkSwitch(topo, text=texto_fila, variable=var_fila, font=fonte(12),
                      command=self.atualizar).grid(row=0, column=0, padx=14, pady=12, sticky="w")
        resumo = ui.subtitulo(topo, "")
        resumo.grid(row=0, column=1, padx=14, sticky="e")
        topo.grid_columnconfigure(1, weight=1)

        botoes = [("Ver mensagem e enviar", lambda: self._enviar_um(tipo), "whatsapp", 210),
                  ("» Enviar para todos da lista", lambda: self._enviar_todos(tipo), "destaque", 230),
                  ("Ficha do paciente", lambda: self._ficha(tipo), "secundario", 150)]
        if tipo == "atraso":
            botoes.append(("⤓ Excel", self._exportar, "fantasma", 90))
        ui.barra_botoes(aba, botoes).grid(row=1, column=0, sticky="w", pady=(0, 8))
        tabela = ui.Tabela(aba, [
            ("resp", "Responsável", 190, "w"), ("whats", "WhatsApp", 130, "center"),
            ("pac", "Paciente(s)", 200, "w"), ("parc", "Parcelas", 80, "center"),
            ("dias", "Maior atraso" if tipo == "atraso" else "Vencimento", 110, "center"),
            ("total", "Total", 110, "e"), ("ultima", "Última mensagem", 150, "center")],
            altura=14, ao_duplo_clique=lambda: self._enviar_um(tipo),
            texto_vazio="Ninguém nesta lista no momento ✔")
        tabela.grid(row=2, column=0, sticky="nsew")
        return {"tabela": tabela, "fila": var_fila, "resumo": resumo, "grupos": {}}

    def _montar_historico(self, aba):
        aba.grid_columnconfigure(0, weight=1)
        aba.grid_rowconfigure(1, weight=1)
        self.hist_busca = ui.Campo(aba, 280, placeholder_text="Buscar por nome ou telefone")
        self.hist_busca.grid(row=0, column=0, sticky="w", pady=(4, 8))
        self.hist_busca.bind("<Return>", lambda _e: self._atualizar_historico())
        self.hist_tabela = ui.Tabela(aba, [
            ("data", "Data / hora", 140, "center"), ("tipo", "Tipo", 90, "center"),
            ("resp", "Responsável", 180, "w"), ("pac", "Paciente", 170, "w"),
            ("tel", "Telefone", 130, "center"), ("canal", "Canal", 70, "center"),
            ("status", "Status", 90, "center"), ("det", "Detalhe", 260, "w")], altura=16)
        self.hist_tabela.grid(row=1, column=0, sticky="nsew")

    # ----------------------------------------------------------------------
    def atualizar(self, **_kwargs):
        modo = configuracoes.obter("whatsapp_modo", "link")
        self.lbl_modo.definir("Modo: API oficial (automático)" if modo == "api"
                              else "Modo: WhatsApp Web/App (envio manual)", None)
        aba = self.abas.get()
        if aba == "Histórico de mensagens":
            self._atualizar_historico()
            return
        for tipo, lista in (("atraso", self.lista_atraso), ("lembrete", self.lista_lembrete)):
            if lista["fila"].get():
                grupos = cobranca.fila_cobrancas() if tipo == "atraso" else cobranca.fila_lembretes()
            else:
                grupos = (financeiro.inadimplentes() if tipo == "atraso" else
                          financeiro.a_vencer(int(configuracoes.obter_numero("lembrete_dias_antes", 3))))
            lista["grupos"] = {str(i): g for i, g in enumerate(grupos)}
            lista["tabela"].carregar([{
                "iid": k,
                "valores": (g["responsavel"], utils.formatar_telefone(g["whatsapp"]) or "⚠ sem telefone",
                            ", ".join(g["pacientes"]), len(g["parcelas"]),
                            f"{g['maior_atraso']} dias" if tipo == "atraso" else utils.data_br(g["vencimento_mais_antigo"]),
                            utils.formatar_moeda(g["total"]),
                            utils.data_br(g["ultima_cobranca"]) + g["ultima_cobranca"][10:16] if g.get("ultima_cobranca") else "nunca"),
                "tag": config.SITUACAO_ATRASO if tipo == "atraso" else config.SITUACAO_EM_DIA}
                for k, g in lista["grupos"].items()])
            total = sum(g["total"] for g in grupos)
            lista["resumo"].configure(text=f"{len(grupos)} responsável(is) · {utils.formatar_moeda(total)}")

    def _atualizar_historico(self):
        self.hist_tabela.carregar([{
            "iid": m["id"],
            "valores": (utils.data_br(m["enviado_em"]) + m["enviado_em"][10:16], m["tipo"].capitalize(),
                        m.get("responsavel") or "", m.get("paciente") or "", utils.formatar_telefone(m["telefone"]),
                        m["canal"].upper(), m["status"].capitalize(), m.get("detalhe") or ""),
            "tag": "atraso" if m["status"] == "erro" else None}
            for m in mensagens.listar(busca=self.hist_busca.valor())])

    def _lista(self, tipo: str) -> dict:
        return self.lista_atraso if tipo == "atraso" else self.lista_lembrete

    def _grupo_sel(self, tipo: str) -> dict | None:
        lista = self._lista(tipo)
        sel = lista["tabela"].selecionado()
        if not sel:
            ui.aviso("Selecione um responsável na lista.", parent=self)
            return None
        return lista["grupos"][sel]

    def _enviar_um(self, tipo: str):
        g = self._grupo_sel(tipo)
        if not g:
            return
        if not g["whatsapp"]:
            ui.aviso("Este responsável não tem WhatsApp cadastrado. Atualize o cadastro.", parent=self)
            return
        texto = whatsapp.mensagem_cobranca(g, tipo)
        if acoes.enviar_com_previa(self, g["responsavel"], g["whatsapp"], texto, tipo,
                                   g["responsavel_id"], g["paciente_ids"][0], g):
            self.atualizar()

    def _enviar_todos(self, tipo: str):
        grupos = [g for g in self._lista(tipo)["grupos"].values() if g["whatsapp"]]
        if not grupos:
            ui.info("Não há responsáveis com WhatsApp nesta lista.", parent=self)
            return
        modo = configuracoes.obter("whatsapp_modo", "link")
        if modo == "api":
            if not ui.confirmar(f"Enviar automaticamente {len(grupos)} mensagem(ns) pela API?", parent=self):
                return
            ok = erros = 0
            for g in grupos:
                sucesso, _det = whatsapp.enviar_cobranca(g, tipo)
                ok += sucesso
                erros += not sucesso
            ui.info(f"Enviadas: {ok}\nCom erro: {erros}\n\nVeja detalhes na aba Histórico.", parent=self)
        else:
            if not ui.confirmar(
                    f"O WhatsApp será aberto {len(grupos)} vez(es), uma para cada responsável.\n"
                    "Em cada conversa, confira e clique em ENVIAR; depois volte aqui para o próximo.\n\n"
                    "Deseja começar?", parent=self):
                return
            for i, g in enumerate(grupos, start=1):
                whatsapp.enviar_cobranca(g, tipo)
                if i < len(grupos) and not ui.confirmar(
                        f"({i}/{len(grupos)}) Conversa com {g['responsavel']} aberta.\n\n"
                        f"Próximo: {grupos[i]['responsavel']}. Continuar?", "Envio em sequência", self):
                    break
        self.atualizar()

    def _ficha(self, tipo: str):
        g = self._grupo_sel(tipo)
        if g:
            acoes.abrir_ficha(self, g["paciente_ids"][0], self.atualizar)

    def _exportar(self):
        recibos.abrir_arquivo(relatorios.exportar_inadimplentes())
