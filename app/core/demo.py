"""
=============================================================================
 demo.py — Dados de DEMONSTRAÇÃO (para treinar sem mexer nos dados reais)
=============================================================================
 Ao abrir com  python main.py --demo  (ou Executar_Demonstracao.bat), o
 sistema usa um banco separado (pasta dados_demo/) já preenchido com
 pacientes fictícios em várias situações: em dia, pendentes e em atraso.
=============================================================================
"""
from __future__ import annotations

from datetime import timedelta

from app.core import utils
from app.repositorios import financeiro, pacientes, servicos

PACIENTES_DEMO = [
    # (paciente, nascimento, diagnósticos, responsável, parentesco, whatsapp, serviço, meses_atras, pagas)
    ("Miguel Andrade", "12/03/2019", "TEA (Autismo)", "Juliana Andrade", "Mãe", "81991110001",
     "Fono + Psicologia + Psicopedagogia", 3, 3),
    ("Laura Ferreira", "25/07/2015", "TDAH; Dislexia", "Roberto Ferreira", "Pai", "81991110002",
     "Psicopedagogia", 2, 3),
    ("Davi Santos", "03/11/2020", "TEA (Autismo); Atraso de fala / linguagem", "Camila Santos", "Mãe",
     "81991110003", "Terapia ABA", 4, 1),
    ("Beatriz Rocha", "30/01/2010", "TDAH; Ansiedade", "Fernanda Rocha", "Mãe", "81991110004",
     "Psicologia", 1, 2),
    ("Pedro Almeida", "08/09/2017", "Em investigação", "Marcos Almeida", "Pai", "81991110005",
     "Avaliação (R$ 1.600 – 4x)", 1, 1),
]


def popular() -> None:
    """Cria os pacientes de demonstração (somente se o banco estiver vazio)."""
    if pacientes.listar(somente_ativos=None):
        return
    tabela = {s["nome"]: s for s in servicos.listar()}
    h = utils.hoje()
    for nome, nasc, diag, resp, parent, whats, serv, meses, pagas in PACIENTES_DEMO:
        pid = pacientes.salvar({"nome": nome, "data_nascimento": nasc, "diagnosticos": diag,
                                "consentimento_lgpd": True},
                               {"nome": resp, "parentesco": parent, "whatsapp": whats, "cidade": "Recife",
                                "uf": "PE"})
        s = tabela[serv]
        primeiro = utils.adicionar_meses(h, -meses, 10)
        parcelas = financeiro.simular_parcelas(s["tipo_cobranca"], "parcelado", s["valor_cheio"],
                                               s["valor_pontualidade"], s["parcelas_padrao"],
                                               s["valor_entrada"], primeiro, 10)
        cid = financeiro.criar_contrato(pid, s["id"], s["nome"], "parcelado", 10, parcelas,
                                        profissional="Equipe Shay Soares", horario="14h")
        formas = ["PIX", "Cartão de crédito (à vista)", "Dinheiro", "PIX", "Cartão de débito"]
        for i, p in enumerate(financeiro.listar_parcelas(contrato_id=cid)[:pagas]):
            data = min(utils.para_date(p["vencimento"]) - timedelta(days=2), h)
            financeiro.registrar_pagamento(p["id"], data, p["valor_pontualidade"], formas[i % len(formas)])
