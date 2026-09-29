"""
Testes automáticos das regras do sistema (sem interface).
Rodar:  python -m unittest discover -s tests -v
"""
from __future__ import annotations

import unittest
from datetime import date, timedelta

from app.core import config, utils
from app.repositorios import configuracoes, financeiro, mensagens, pacientes, servicos, usuarios
from app.servicos import backup, cobranca, recibos, relatorios, whatsapp
from tests.apoio import banco_temporario, dados_exemplo

IDS: dict = {}
HOJE = utils.hoje()


def setUpModule():
    """Antes dos testes: banco temporário novo com dados de exemplo."""
    banco_temporario()
    IDS.update(dados_exemplo())


class TesteUtilitarios(unittest.TestCase):
    def test_moeda(self):
        self.assertEqual(utils.formatar_moeda(1234.5), "R$ 1.234,50")
        self.assertEqual(utils.ler_moeda("1.234,50"), 1234.5)
        self.assertEqual(utils.ler_moeda("R$ 200"), 200.0)
        self.assertEqual(utils.ler_moeda("200.5"), 200.5)
        with self.assertRaises(ValueError):
            utils.ler_moeda("abc")

    def test_extenso(self):
        self.assertEqual(utils.valor_por_extenso(220), "duzentos e vinte reais")
        self.assertEqual(utils.valor_por_extenso(1600), "mil e seiscentos reais")
        self.assertEqual(utils.valor_por_extenso(180.5), "cento e oitenta reais e cinquenta centavos")
        self.assertEqual(utils.valor_por_extenso(1), "um real")

    def test_cpf_telefone(self):
        self.assertTrue(utils.validar_cpf("529.982.247-25"))
        self.assertFalse(utils.validar_cpf("111.111.111-11"))
        self.assertEqual(utils.telefone_whatsapp("(81) 9 9767-3217"), "5581997673217")
        self.assertEqual(utils.telefone_whatsapp("997673217", "81"), "5581997673217")
        self.assertIsNone(utils.telefone_whatsapp("123"))

    def test_datas(self):
        self.assertEqual(utils.adicionar_meses(date(2026, 1, 30), 1, 30), date(2026, 2, 28))
        self.assertEqual(utils.ler_data("29092026"), date(2026, 9, 29))
        with self.assertRaises(ValueError):
            utils.ler_data("31/02/2026")


class TesteCadastro(unittest.TestCase):
    def test_validacao(self):
        erros = pacientes.validar({"nome": "", "data_nascimento": None}, {"nome": ""})
        self.assertTrue(any("nome do paciente" in e for e in erros))
        erros = pacientes.validar({"nome": "Bia", "data_nascimento": "01/01/2020", "proprio_responsavel": True,
                                   "whatsapp": "81999990000"}, {})
        self.assertTrue(any("menor de 18" in e for e in erros))

    def test_proprio_responsavel(self):
        p = pacientes.obter(IDS["adulto"])
        self.assertEqual(p["responsavel"]["nome"], "Rafael Nunes")
        self.assertEqual(p["responsavel"]["whatsapp"], "(81) 97777-6666")

    def test_busca(self):
        self.assertEqual(len(pacientes.listar("joao")), 1)          # sem acento
        self.assertEqual(len(pacientes.listar("98888-7777")), 1)         # telefone do responsável
        self.assertEqual(len(pacientes.listar(faixa="Adulto (18+)")), 1)
        self.assertEqual(len(pacientes.listar(diagnostico="TDAH")), 2)

    def test_irmao_mesmo_responsavel(self):
        resp_id = pacientes.obter(IDS["joao"])["responsavel_id"]
        irmao = pacientes.salvar({"nome": "Lucas Lima", "data_nascimento": "03/03/2020"},
                                 {"nome": "Maria Lima", "whatsapp": "81999998888"}, responsavel_id=resp_id)
        self.assertEqual(pacientes.obter(irmao)["responsavel_id"], resp_id)
        pacientes.excluir(irmao)
        self.assertTrue(pacientes.obter_responsavel(resp_id))       # responsável continua (tem o João)


class TesteFinanceiro(unittest.TestCase):
    def test_simulacao_avaliacao(self):
        v = [p["valor"] for p in financeiro.simular_parcelas("parcelado", "parcelado", 1000, 1000, 4, 100,
                                                             HOJE, 10)]
        self.assertEqual(v, [100, 300, 300, 300])
        v = [p["valor"] for p in financeiro.simular_parcelas("parcelado", "parcelado", 1000, 1000, 3, 0, HOJE, 10)]
        self.assertAlmostEqual(sum(v), 1000)                          # centavos ajustados

    def test_simulacao_a_vista_e_desconto(self):
        p = financeiro.simular_parcelas("mensal", "a_vista", 220, 200, 6, 0, HOJE, 10)
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0]["valor"], 1200)
        p = financeiro.simular_parcelas("mensal", "parcelado", 200, 180, 2, 0, HOJE, 10, 10)
        self.assertEqual(p[0]["valor_pontualidade"], 162)

    def test_situacoes(self):
        parcelas = financeiro.listar_parcelas(contrato_id=IDS["c_joao"])
        self.assertEqual(parcelas[0]["situacao"], config.SITUACAO_ATRASO)
        self.assertEqual(parcelas[0]["valor_devido"], 220)            # passou do vencimento: valor cheio
        self.assertEqual(parcelas[-1]["situacao"], config.SITUACAO_EM_DIA)
        self.assertEqual(parcelas[-1]["valor_devido"], 200)           # em dia: pontualidade
        entrada = financeiro.listar_parcelas(contrato_id=IDS["c_adulto"])[0]
        self.assertEqual(entrada["situacao"], config.SITUACAO_PAGO)

    def test_pagamento_parcial_e_estorno(self):
        p = financeiro.listar_parcelas(contrato_id=IDS["c_ana"])[1]
        r = financeiro.registrar_pagamento(p["id"], HOJE, 50, "Dinheiro")
        self.assertFalse(r["quitada"])
        self.assertAlmostEqual(r["saldo_restante"], 130)
        r2 = financeiro.registrar_pagamento(p["id"], HOJE, 130, "Cartão de crédito (parcelado)", 2)
        self.assertTrue(r2["quitada"])
        self.assertEqual(financeiro.obter_parcela(p["id"])["situacao"], config.SITUACAO_PAGO)
        financeiro.estornar_pagamento(r2["pagamento_id"])
        self.assertEqual(financeiro.obter_parcela(p["id"])["status"], "aberta")
        financeiro.estornar_pagamento(r["pagamento_id"])

    def test_multa_juros_tolerancia(self):
        configuracoes.salvar_varias({"multa_percentual": "2", "juros_mes_percentual": "1", "tolerancia_dias": "0"})
        p = {"vencimento": HOJE - timedelta(days=30), "valor": 220, "valor_pontualidade": 200}
        devido, encargos = financeiro.calcular_valor_devido(p, HOJE)
        self.assertAlmostEqual(encargos, 4.4 + 2.2, places=2)
        configuracoes.salvar("tolerancia_dias", "40")
        self.assertEqual(financeiro.calcular_valor_devido(p, HOJE)[0], 200)
        configuracoes.salvar_varias({"multa_percentual": "0", "juros_mes_percentual": "0", "tolerancia_dias": "0"})

    def test_nao_paga_duas_vezes(self):
        entrada = financeiro.listar_parcelas(contrato_id=IDS["c_adulto"])[0]
        with self.assertRaises(ValueError):
            financeiro.registrar_pagamento(entrada["id"], HOJE, 10, "PIX")

    def test_inadimplentes_e_indicadores(self):
        grupos = financeiro.inadimplentes()
        self.assertTrue(any(g["responsavel"] == "Maria Lima" for g in grupos))
        ind = financeiro.indicadores()
        self.assertGreater(ind["em_atraso"], 0)
        self.assertEqual(len(financeiro.receita_mensal(6)), 6)

    def test_renovar_e_cancelar(self):
        antes = len(financeiro.listar_parcelas(contrato_id=IDS["c_ana"]))
        financeiro.renovar_contrato(IDS["c_ana"], 2)
        self.assertEqual(len(financeiro.listar_parcelas(contrato_id=IDS["c_ana"])), antes + 2)
        financeiro.alterar_status_contrato(IDS["c_ana"], "ativo")

    def test_recibo_sequencial(self):
        a = configuracoes.proximo_numero_recibo()
        b = configuracoes.proximo_numero_recibo()
        self.assertEqual(b, a + 1)


class TesteServicos(unittest.TestCase):
    def test_precos_iniciais(self):
        s = {x["nome"]: x for x in servicos.listar()}
        self.assertEqual(s["Terapia ABA"]["valor_cheio"], 380)
        self.assertEqual(s["Terapia ABA"]["valor_pontualidade"], 350)
        self.assertEqual(s["Taxa de Adesão"]["valor_cheio"], 70)
        self.assertEqual(len(s), 10)

    def test_whatsapp_mensagem(self):
        g = financeiro.inadimplentes()[0]
        texto = whatsapp.mensagem_cobranca(g)
        self.assertIn(g["pacientes"][0], texto)
        self.assertIn("Chave", texto)
        link = whatsapp.link_whatsapp("5581999998888", texto)
        self.assertTrue(link.startswith("https://api.whatsapp.com/send?phone=5581999998888&text="))

    def test_whatsapp_envio_link_registra(self):
        import webbrowser
        original = webbrowser.open
        webbrowser.open = lambda url: True
        grupo = financeiro.inadimplentes()[0]
        try:
            ok, _ = whatsapp.enviar_cobranca(grupo, "atraso")
        finally:
            webbrowser.open = original
        self.assertTrue(ok)
        self.assertEqual(mensagens.listar(1)[0]["status"], "aberto")
        # quem acabou de ser cobrado sai da fila (não recebe mensagem repetida)
        self.assertFalse(any(g["responsavel_id"] == grupo["responsavel_id"] for g in cobranca.fila_cobrancas()))

    def test_api_sem_configuracao(self):
        ok, detalhe = whatsapp.enviar("81999998888", "teste", forcar_modo="api")
        self.assertFalse(ok)
        self.assertIn("não configurada", detalhe)

    def test_pdfs_e_planilhas(self):
        g = financeiro.listar_pagamentos()[0]
        self.assertTrue(recibos.gerar_recibo(g["id"]).exists())
        self.assertTrue(recibos.gerar_carne(IDS["c_joao"]).exists())
        self.assertTrue(relatorios.exportar_parcelas(financeiro.listar_parcelas()).exists())
        self.assertTrue(relatorios.exportar_pagamentos(HOJE - timedelta(days=60), HOJE).exists())
        self.assertTrue(relatorios.exportar_pacientes().exists())
        self.assertTrue(relatorios.exportar_inadimplentes().exists())

    def test_backup(self):
        caminho = backup.fazer_backup()
        self.assertTrue(caminho.exists())
        self.assertTrue(backup.restaurar(caminho).exists())

    def test_usuarios(self):
        uid = usuarios.criar("Recepção", "recep", "1234")
        self.assertTrue(usuarios.autenticar("recep", "1234"))
        self.assertIsNone(usuarios.autenticar("recep", "errada"))
        self.assertTrue(usuarios.autenticar("admin", "admin"))
        with self.assertRaises(ValueError):
            usuarios.definir_ativo(1, False)                            # único administrador
        usuarios.definir_ativo(uid, False)


if __name__ == "__main__":
    unittest.main()
