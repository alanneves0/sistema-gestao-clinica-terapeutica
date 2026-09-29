"""
Teste da INTERFACE com "tela falsa" (tests/stub_tk.py): monta todas as telas,
preenche formulários e aciona os botões principais, verificando o resultado
no banco de dados. Não abre nenhuma janela.
Rodar:  python -m unittest tests.test_interface -v
"""
from __future__ import annotations

import sys
import unittest
import webbrowser

from tests import stub_tk

ORIGINAIS = {k: sys.modules.get(k) for k in ("tkinter", "tkinter.ttk", "tkinter.messagebox",
                                             "tkinter.filedialog", "customtkinter")}


def setUpModule():
    stub_tk.instalar()
    # remove módulos de interface já importados para que usem a tela falsa
    for nome in [m for m in sys.modules if m.startswith("app.ui")]:
        del sys.modules[nome]
    from tests.apoio import banco_temporario, dados_exemplo
    banco_temporario()
    DADOS.update(dados_exemplo())
    webbrowser.open = lambda url: ABERTOS.append(url) or True
    from app.servicos import recibos
    recibos.abrir_arquivo = lambda caminho: ABERTOS.append(str(caminho))


def tearDownModule():
    for k, v in ORIGINAIS.items():
        if v is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = v


DADOS: dict = {}
ABERTOS: list = []


class TesteInterface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.ui import tema
        tema.aplicar_tema()
        from app.ui.janela_principal import App
        cls.app = App()
        login = cls.app.tela_login
        login.login.insert(0, "admin")
        login.senha.insert(0, "admin")
        login._entrar()

    def setUp(self):
        stub_tk.REGISTRO["mensagens"].clear()
        stub_tk.REGISTRO["responder_sim"] = True

    def _sem_erros(self):
        erros = [m for m in stub_tk.REGISTRO["mensagens"] if m[0] == "showerror"]
        self.assertEqual(erros, [], f"Mensagens de erro exibidas: {erros}")

    # ------------------------------------------------------------------
    def test_01_todas_as_paginas_abrem(self):
        from app.ui.janela_principal import MENU
        for chave, _t, _c in MENU:
            self.app.mostrar(chave)
            self.assertEqual(self.app.pagina_atual, chave)
        self._sem_erros()

    def test_02_login_errado(self):
        from app.ui.janela_principal import TelaLogin
        entrou = []
        tela = TelaLogin(self.app, entrou.append)
        tela.login.insert(0, "admin")
        tela.senha.insert(0, "xxx")
        tela._entrar()
        self.assertEqual(entrou, [])
        self.assertIn("incorretos", tela.msg.cget("text"))

    def test_03_cadastro_novo_paciente(self):
        from app.repositorios import pacientes
        self.app.mostrar("cadastro")
        pg = self.app.paginas["cadastro"]
        pg.cp["nome"].insert(0, "Helena Costa")
        pg.cp["data_nascimento"].insert(0, "15/08/2016")
        pg.cr["nome"].insert(0, "Patrícia Costa")
        pg.cr["whatsapp"].insert(0, "81 99123-4567")
        pg.cr["cpf"].insert(0, "52998224725")
        pg.vars_diag["TEA (Autismo)"].set(True)
        pg.var_lgpd.set(True)
        pg._salvar(False)
        self._sem_erros()
        p = pacientes.listar("Helena")[0]
        self.assertEqual(p["responsavel_nome"], "Patrícia Costa")
        self.assertEqual(p["diagnosticos"], "TEA (Autismo)")
        self.assertEqual(self.app.pagina_atual, "pacientes")

    def test_04_cadastro_invalido_mostra_erro(self):
        self.app.mostrar("cadastro")
        pg = self.app.paginas["cadastro"]
        pg.var_lgpd.set(True)
        pg._salvar(False)
        self.assertTrue(any(m[0] == "showerror" for m in stub_tk.REGISTRO["mensagens"]))

    def test_05_editar_paciente(self):
        from app.repositorios import pacientes
        self.app.mostrar("cadastro", paciente_id=DADOS["adulto"])
        pg = self.app.paginas["cadastro"]
        self.assertEqual(pg.cp["nome"].get(), "Rafael Nunes")
        self.assertTrue(pg.var_proprio.get())
        pg.cp["escola"].insert(0, "UFPE")
        pg._salvar(False)
        self._sem_erros()
        self.assertEqual(pacientes.obter(DADOS["adulto"])["escola"], "UFPE")

    def test_06_lista_pacientes_e_acoes(self):
        self.app.mostrar("pacientes")
        pg = self.app.paginas["pacientes"]
        self.assertGreaterEqual(len(pg.tabela.tree.get_children()), 3)
        pg.busca.insert(0, "joao")
        pg.atualizar()
        self.assertEqual(len(pg.tabela.tree.get_children()), 1)
        pg.tabela.tree.selection_set(str(DADOS["joao"]))
        pg._whats()        # abre diálogo de mensagem (não bloqueia na tela falsa)
        pg._ficha()
        pg._contrato()
        ui_busca = pg.busca
        ui_busca.delete(0, "end")
        pg.atualizar()
        self._sem_erros()

    def test_07_contrato_dialogo(self):
        from app.repositorios import financeiro
        from app.ui.dialogos.contrato import DialogoContrato
        d = DialogoContrato(self.app, DADOS["ana"], "Ana")
        d.servico.escolher("Terapia ABA")
        self.assertEqual(d.valor_cheio.numero(), 380)
        self.assertEqual(len(d.simulacao), 6)
        d.modalidade.escolher("À vista (pagamento único)")
        self.assertEqual(len(d.simulacao), 1)
        self.assertEqual(d.simulacao[0]["valor"], 350 * 6)
        d.modalidade.escolher("Mensal / Parcelado")
        d.var_adesao.set(True)
        antes = len(financeiro.listar_contratos(DADOS["ana"]))
        d._salvar()
        self._sem_erros()
        self.assertEqual(len(financeiro.listar_contratos(DADOS["ana"])), antes + 2)

    def test_08_pagamento_dialogo(self):
        from app.repositorios import financeiro
        from app.ui.dialogos.pagamento import DialogoPagamento
        p = [x for x in financeiro.listar_parcelas(contrato_id=DADOS["c_joao"]) if x["status"] == "aberta"][0]
        d = DialogoPagamento(self.app, p["id"])
        self.assertEqual(d.valor.numero(), 220)            # atrasada: valor cheio
        d.forma.escolher("Cartão de crédito (parcelado)")
        d.vezes.set("3")
        d._confirmar()
        self._sem_erros()
        self.assertTrue(d.resultado["quitada"])
        g = financeiro.listar_pagamentos(parcela_id=p["id"])[0]
        self.assertEqual(g["parcelas_cartao"], 3)

    def test_09_financeiro_pagina(self):
        from app.core import config
        self.app.mostrar("financeiro")
        pg = self.app.paginas["financeiro"]
        for periodo in ("Todos", "Mês atual", "Próximos 30 dias", "Ano atual"):
            pg.periodo.escolher(periodo)
        for sit in ("Todas", config.SITUACAO_ATRASO, config.SITUACAO_PAGO, config.SITUACAO_EM_DIA):
            pg.seg_situacao.escolher(sit)
        pg.seg_situacao.escolher(config.SITUACAO_ATRASO)
        self.assertGreater(len(pg.tabela.tree.get_children()), 0)
        primeira = pg.tabela.tree.get_children()[0]
        pg.tabela.tree.selection_set(primeira)
        pg._receber()
        pg._cobrar()
        pg._editar()
        pg._ficha()
        pg._exportar()
        pg.tabela._ordenar("venc")
        pg.abas.set("Recebimentos (caixa)")
        pg.atualizar()
        self.assertGreater(len(pg.cx_tabela.tree.get_children()), 0)
        pg.cx_tabela.tree.selection_set(pg.cx_tabela.tree.get_children()[0])
        pg._cx_recibo()
        pg._cx_whats()
        pg._cx_exportar()
        self._sem_erros()

    def test_10_quitar_varias(self):
        from app.repositorios import financeiro
        from app.ui.dialogos.pagamento import DialogoQuitarVarias
        abertas = [p for p in financeiro.listar_parcelas(contrato_id=DADOS["c_adulto"]) if p["status"] == "aberta"]
        d = DialogoQuitarVarias(self.app, abertas)
        d.forma.set("PIX")
        d._confirmar()
        self._sem_erros()
        self.assertTrue(all(p["status"] == "paga" for p in financeiro.listar_parcelas(contrato_id=DADOS["c_adulto"])))

    def test_11_ficha_financeira(self):
        from app.ui.dialogos.ficha import FichaFinanceira
        f = FichaFinanceira(self.app, DADOS["joao"])
        self.assertGreater(len(f.tab_parcelas.tree.get_children()), 0)
        f.tab_contratos.tree.selection_set(str(DADOS["c_joao"]))
        f._carregar_parcelas()
        f._carne()
        f._renovar()                 # CTkInputDialog falso responde "3"
        f.tab_parcelas.tree.selection_set(f.tab_parcelas.tree.get_children()[-1])
        f._editar()
        f._recibo()
        f._todas()
        self._sem_erros()

    def test_12_cobrancas(self):
        self.app.mostrar("cobrancas")
        pg = self.app.paginas["cobrancas"]
        pg.lista_atraso["fila"].set(False)
        pg.atualizar()
        self.assertGreater(len(pg.lista_atraso["tabela"].tree.get_children()), 0)
        pg.lista_atraso["tabela"].tree.selection_set("0")
        pg._enviar_um("atraso")
        antes = len(ABERTOS)
        pg._enviar_todos("atraso")
        self.assertGreater(len(ABERTOS), antes)          # WhatsApp aberto (modo link)
        pg.abas.set("Histórico de mensagens")
        pg.atualizar()
        self.assertGreater(len(pg.hist_tabela.tree.get_children()), 0)
        self._sem_erros()

    def test_13_mensagem_dialogo_envia(self):
        from app.ui.dialogos.diversos import DialogoMensagem
        d = DialogoMensagem(self.app, "Maria", "81999998888", "Olá 🌷", "link")
        d._enviar()
        self.assertEqual(d.resultado["texto"], "Olá 🌷")

    def test_14_servicos(self):
        from app.repositorios import servicos
        from app.ui.dialogos.diversos import DialogoServico
        self.app.mostrar("servicos")
        d = DialogoServico(self.app)
        d.nome.insert(0, "Terapia Ocupacional")
        d.valor.insert(0, "250,00")
        d.pont.insert(0, "230")
        d._salvar()
        self._sem_erros()
        self.assertTrue(any(s["nome"] == "Terapia Ocupacional" for s in servicos.listar()))

    def test_15_configuracoes(self):
        from app.repositorios import configuracoes
        self.app.mostrar("configuracoes", aba="WhatsApp")
        pg = self.app.paginas["configuracoes"]
        pg.campos["clinica_cidade"].insert(0, "Recife")
        pg.seg_modo.set("WhatsApp Web / App (manual)")
        pg._salvar()
        self._sem_erros()
        self.assertEqual(configuracoes.obter("clinica_cidade"), "Recife")
        self.assertIn("{responsavel}", configuracoes.obter("msg_atraso"))
        pg._backup_agora()

    def test_16_relatorios(self):
        self.app.mostrar("relatorios")
        pg = self.app.paginas["relatorios"]
        pg.periodo.escolher("Ano atual")
        pg._exp_pag()
        pg._exp_parc()
        pg._exp_inad()
        pg._exp_pac()
        self._sem_erros()

    def test_17_usuarios_e_sair(self):
        from app.ui.dialogos.diversos import DialogoSenha, DialogoUsuario
        d = DialogoUsuario(self.app)
        d.nome.insert(0, "Recepção")
        d.login.insert(0, "recepcao")
        d.senha.insert(0, "1234")
        d._salvar()
        s = DialogoSenha(self.app, 1)
        s.s1.insert(0, "nova123")
        s.s2.insert(0, "nova123")
        s._salvar()
        self._sem_erros()
        self.app.notificar("teste")
        self.app._tarefas_de_fundo()
        self.app.sair()
        self.assertIsNotNone(self.app.tela_login)


if __name__ == "__main__":
    unittest.main()
