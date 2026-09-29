"""
Apoio aos testes: cria um banco de dados temporário (em pasta descartável),
para que os testes NUNCA mexam nos dados reais do Espaço.
"""
from __future__ import annotations

import tempfile
from datetime import timedelta
from pathlib import Path

from app.core import config, database, sessao, utils


def banco_temporario() -> Path:
    pasta = Path(tempfile.mkdtemp(prefix="shay_teste_"))
    config.DADOS_DIR = pasta
    config.DB_PATH = pasta / "teste.db"
    config.BACKUP_DIR = pasta / "backups"
    config.RECIBOS_DIR = pasta / "recibos"
    config.RELATORIOS_DIR = pasta / "relatorios"
    config.LOG_PATH = pasta / "teste.log"
    database.inicializar_banco()
    sessao.iniciar({"id": 1, "nome": "Administrador", "perfil": "administrador"})
    return pasta


def dados_exemplo() -> dict:
    """Cadastra 3 pacientes com contratos em situações diferentes."""
    from app.repositorios import financeiro, pacientes, servicos
    s = {x["nome"]: x for x in servicos.listar()}
    h = utils.hoje()

    joao = pacientes.salvar({"nome": "João Pedro Lima", "data_nascimento": "10/05/2018",
                             "diagnosticos": "TEA (Autismo); TDAH"},
                            {"nome": "Maria Lima", "whatsapp": "81999998888", "cpf": "529.982.247-25",
                             "parentesco": "Mãe"})
    ana = pacientes.salvar({"nome": "Ana Clara Souza", "data_nascimento": "02/02/2012",
                            "diagnosticos": "TDAH"},
                           {"nome": "Carlos Souza", "whatsapp": "(81) 98888-7777", "parentesco": "Pai"})
    adulto = pacientes.salvar({"nome": "Rafael Nunes", "data_nascimento": "01/01/1990",
                               "whatsapp": "81977776666", "proprio_responsavel": True,
                               "diagnosticos": "TEA (Autismo)"}, {})

    fono = s["Fonoaudiologia"]
    parc = financeiro.simular_parcelas("mensal", "parcelado", fono["valor_cheio"], fono["valor_pontualidade"],
                                       6, 0, h - timedelta(days=45), (h - timedelta(days=45)).day)
    c1 = financeiro.criar_contrato(joao, fono["id"], fono["nome"], "parcelado", parc[0]["vencimento"].day, parc)
    psico = s["Psicologia"]
    parc2 = financeiro.simular_parcelas("mensal", "parcelado", psico["valor_cheio"], psico["valor_pontualidade"],
                                        3, 0, h + timedelta(days=2), (h + timedelta(days=2)).day)
    c2 = financeiro.criar_contrato(ana, psico["id"], psico["nome"], "parcelado", parc2[0]["vencimento"].day, parc2)
    aval = s["Avaliação (R$ 1.000 – entrada + 3x)"]
    parc3 = financeiro.simular_parcelas("parcelado", "parcelado", aval["valor_cheio"], aval["valor_pontualidade"],
                                        4, aval["valor_entrada"], h - timedelta(days=5), (h - timedelta(days=5)).day)
    c3 = financeiro.criar_contrato(adulto, aval["id"], aval["nome"], "parcelado", parc3[0]["vencimento"].day, parc3)
    # Rafael pagou a entrada
    p = financeiro.listar_parcelas(contrato_id=c3)[0]
    financeiro.registrar_pagamento(p["id"], h - timedelta(days=6), 100, "PIX")
    return {"joao": joao, "ana": ana, "adulto": adulto, "c_joao": c1, "c_ana": c2, "c_adulto": c3}
