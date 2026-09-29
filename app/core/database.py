"""
=============================================================================
 database.py — Banco de dados local (SQLite)
=============================================================================
 O sistema usa SQLite: um banco SQL completo que fica em UM arquivo no
 computador (dados/espaco_shay.db). Não precisa instalar servidor nenhum.

 Este módulo:
   1. abre a conexão com o banco                      -> conexao()
   2. cria as tabelas na primeira execução            -> inicializar_banco()
   3. aplica atualizações de estrutura (migrações)    -> _migrar()
   4. insere os dados iniciais (serviços e preços)    -> _dados_iniciais()
   5. oferece atalhos para consultas                  -> consultar(), executar()

 Estrutura das tabelas (resumo):
   usuarios        – quem pode entrar no sistema
   responsaveis    – responsável financeiro/legal (pai, mãe, o próprio adulto…)
   pacientes       – dados de identificação e clínicos do paciente
   servicos        – tabela de preços (Psicologia, Fono, ABA, Avaliação…)
   contratos       – um serviço contratado para um paciente
   parcelas        – mensalidades/parcelas geradas para cada contrato
   pagamentos      – cada pagamento recebido (PIX, cartão, dinheiro…)
   mensagens       – histórico de mensagens de WhatsApp enviadas
   configuracoes   – dados do Espaço, PIX, multa/juros, textos das mensagens
   auditoria       – registro de "quem fez o quê e quando"
=============================================================================
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime

from app.core import config
from app.core.seguranca import gerar_hash

# Versão atual da estrutura do banco. Ao criar uma nova migração,
# aumente este número e adicione o SQL em MIGRACOES.
VERSAO_SCHEMA = 1

# ---------------------------------------------------------------------------
# Estrutura (DDL) — versão 1
# ---------------------------------------------------------------------------
SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS usuarios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          TEXT NOT NULL,
    login         TEXT NOT NULL UNIQUE COLLATE NOCASE,
    senha_hash    TEXT NOT NULL,
    perfil        TEXT NOT NULL DEFAULT 'administrador',  -- administrador | recepcao
    ativo         INTEGER NOT NULL DEFAULT 1,
    trocar_senha  INTEGER NOT NULL DEFAULT 0,
    criado_em     TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS responsaveis (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nome            TEXT NOT NULL,
    cpf             TEXT,
    rg              TEXT,
    data_nascimento TEXT,
    parentesco      TEXT,
    profissao       TEXT,
    telefone        TEXT,
    whatsapp        TEXT,
    telefone_alt    TEXT,
    email           TEXT,
    cep             TEXT,
    logradouro      TEXT,
    numero          TEXT,
    complemento     TEXT,
    bairro          TEXT,
    cidade          TEXT,
    uf              TEXT,
    observacoes     TEXT,
    criado_em       TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    atualizado_em   TEXT
);

CREATE TABLE IF NOT EXISTS pacientes (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    responsavel_id          INTEGER REFERENCES responsaveis(id) ON DELETE SET NULL,
    proprio_responsavel     INTEGER NOT NULL DEFAULT 0,
    -- identificação
    nome                    TEXT NOT NULL,
    nome_social             TEXT,
    data_nascimento         TEXT,
    sexo                    TEXT,
    cpf                     TEXT,
    rg                      TEXT,
    cartao_sus              TEXT,
    telefone                TEXT,
    whatsapp                TEXT,
    email                   TEXT,
    -- convênio
    convenio                TEXT,
    num_carteirinha         TEXT,
    -- escola / trabalho
    escola                  TEXT,
    serie                   TEXT,
    turno                   TEXT,
    ocupacao                TEXT,
    -- informações clínicas
    diagnosticos            TEXT,    -- lista separada por ';' (TEA; TDAH; ...)
    cid                     TEXT,
    nivel_suporte           TEXT,
    laudo                   INTEGER NOT NULL DEFAULT 0,
    medicacoes              TEXT,
    alergias                TEXT,
    medico_responsavel      TEXT,
    encaminhado_por         TEXT,
    queixa_principal        TEXT,
    observacoes             TEXT,
    -- emergência / autorizações
    emergencia_nome         TEXT,
    emergencia_telefone     TEXT,
    emergencia_parentesco   TEXT,
    autoriza_imagem         INTEGER NOT NULL DEFAULT 0,
    consentimento_lgpd      INTEGER NOT NULL DEFAULT 0,
    -- controle
    ativo                   INTEGER NOT NULL DEFAULT 1,
    data_cadastro           TEXT NOT NULL DEFAULT (date('now','localtime')),
    atualizado_em           TEXT
);
CREATE INDEX IF NOT EXISTS ix_pacientes_nome ON pacientes(nome);
CREATE INDEX IF NOT EXISTS ix_pacientes_resp ON pacientes(responsavel_id);

CREATE TABLE IF NOT EXISTS servicos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    nome                TEXT NOT NULL,
    categoria           TEXT NOT NULL DEFAULT 'Terapia',
    tipo_cobranca       TEXT NOT NULL DEFAULT 'mensal',   -- mensal | parcelado | unico
    valor_cheio         REAL NOT NULL DEFAULT 0,          -- mensalidade (ou total do pacote)
    valor_pontualidade  REAL NOT NULL DEFAULT 0,          -- valor pago até o vencimento
    parcelas_padrao     INTEGER NOT NULL DEFAULT 1,
    valor_entrada       REAL NOT NULL DEFAULT 0,          -- 1ª parcela diferente (ex.: avaliação)
    descricao           TEXT,
    ativo               INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS contratos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente_id         INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    servico_id          INTEGER REFERENCES servicos(id),
    descricao           TEXT NOT NULL,
    modalidade          TEXT NOT NULL DEFAULT 'parcelado',   -- parcelado | a_vista
    data_inicio         TEXT NOT NULL,
    dia_vencimento      INTEGER NOT NULL DEFAULT 10,
    num_parcelas        INTEGER NOT NULL DEFAULT 1,
    valor_total         REAL NOT NULL DEFAULT 0,
    desconto_percentual REAL NOT NULL DEFAULT 0,
    profissional        TEXT,
    dias_atendimento    TEXT,
    horario             TEXT,
    status              TEXT NOT NULL DEFAULT 'ativo',       -- ativo | encerrado | cancelado
    observacoes         TEXT,
    criado_em           TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS ix_contratos_paciente ON contratos(paciente_id);

CREATE TABLE IF NOT EXISTS parcelas (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    contrato_id         INTEGER NOT NULL REFERENCES contratos(id) ON DELETE CASCADE,
    numero              INTEGER NOT NULL,
    vencimento          TEXT NOT NULL,
    valor               REAL NOT NULL,              -- valor cheio (após o vencimento)
    valor_pontualidade  REAL NOT NULL,              -- valor até o vencimento
    status              TEXT NOT NULL DEFAULT 'aberta',   -- aberta | paga | cancelada
    data_quitacao       TEXT,
    observacoes         TEXT
);
CREATE INDEX IF NOT EXISTS ix_parcelas_venc ON parcelas(vencimento);
CREATE INDEX IF NOT EXISTS ix_parcelas_contrato ON parcelas(contrato_id);

CREATE TABLE IF NOT EXISTS pagamentos (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    parcela_id       INTEGER NOT NULL REFERENCES parcelas(id) ON DELETE CASCADE,
    data_pagamento   TEXT NOT NULL,
    valor            REAL NOT NULL,           -- valor efetivamente recebido
    desconto         REAL NOT NULL DEFAULT 0, -- desconto concedido no ato
    acrescimo        REAL NOT NULL DEFAULT 0, -- multa/juros cobrados
    forma_pagamento  TEXT NOT NULL,
    parcelas_cartao  INTEGER NOT NULL DEFAULT 1,
    taxa_operadora   REAL NOT NULL DEFAULT 0, -- taxa da maquininha (informativo)
    recibo_numero    INTEGER,
    observacoes      TEXT,
    usuario          TEXT,
    criado_em        TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS ix_pagamentos_data ON pagamentos(data_pagamento);
CREATE INDEX IF NOT EXISTS ix_pagamentos_parcela ON pagamentos(parcela_id);

CREATE TABLE IF NOT EXISTS mensagens (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    responsavel_id  INTEGER REFERENCES responsaveis(id) ON DELETE SET NULL,
    paciente_id     INTEGER REFERENCES pacientes(id) ON DELETE SET NULL,
    telefone        TEXT,
    tipo            TEXT NOT NULL,     -- atraso | lembrete | recibo | manual
    canal           TEXT NOT NULL,     -- link | api
    texto           TEXT,
    status          TEXT NOT NULL,     -- aberto | enviado | erro
    detalhe         TEXT,
    enviado_em      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS ix_mensagens_resp ON mensagens(responsavel_id, tipo);

CREATE TABLE IF NOT EXISTS configuracoes (
    chave  TEXT PRIMARY KEY,
    valor  TEXT
);

CREATE TABLE IF NOT EXISTS auditoria (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    data_hora   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    usuario     TEXT,
    acao        TEXT NOT NULL,
    detalhes    TEXT
);
"""

# Lista de migrações: {versão: SQL}. A versão 1 é a criação inicial.
MIGRACOES: dict[int, str] = {
    1: SCHEMA_V1,
}


# ---------------------------------------------------------------------------
# Serviços e preços iniciais (tirados dos carnês do Espaço)
#   (nome, categoria, tipo, valor_cheio, valor_pontualidade, parcelas, entrada, descrição)
# ---------------------------------------------------------------------------
SERVICOS_INICIAIS = [
    ("Taxa de Adesão", "Taxa", "unico", 70.00, 70.00, 1, 0,
     "Taxa única cobrada na entrada do paciente."),
    ("Psicologia", "Terapia", "mensal", 200.00, 180.00, 6, 0,
     "Serviço terapêutico de psicologia. R$ 180,00 pago até o vencimento."),
    ("Psicopedagogia", "Terapia", "mensal", 200.00, 180.00, 6, 0,
     "Serviço terapêutico de psicopedagogia. R$ 180,00 pago até o vencimento."),
    ("Fonoaudiologia", "Terapia", "mensal", 220.00, 200.00, 6, 0,
     "Serviço terapêutico de fonoaudiologia. R$ 200,00 pago até o vencimento."),
    ("Terapia ABA", "Terapia", "mensal", 380.00, 350.00, 6, 0,
     "Serviço terapêutico ABA. R$ 350,00 pago até o vencimento."),
    ("Fono + Psicologia", "Pacote", "mensal", 400.00, 380.00, 6, 0,
     "Fonoaudiologia + Psicologia. R$ 380,00 pago até o vencimento."),
    ("Fono + Psicologia + Psicopedagogia", "Pacote", "mensal", 470.00, 450.00, 6, 0,
     "Fonoaudiologia + Psicologia + Psicopedagogia. R$ 450,00 até o vencimento."),
    ("Fono + Psicopedagogia + ABA (Clínica + Domiciliar)", "Pacote", "mensal", 690.00, 690.00, 6, 0,
     "Fonoaudiologia + Psicopedagogia + ABA clínica e domiciliar."),
    ("Avaliação (R$ 1.000 – entrada + 3x)", "Avaliação", "parcelado", 1000.00, 1000.00, 4, 100.00,
     "Serviço de avaliação: entrada de R$ 100,00 + 3 parcelas de R$ 300,00."),
    ("Avaliação (R$ 1.600 – 4x)", "Avaliação", "parcelado", 1600.00, 1600.00, 4, 0,
     "Serviço de avaliação: 4 parcelas de R$ 400,00."),
]

# ---------------------------------------------------------------------------
# Configurações iniciais (podem ser alteradas na tela "Configurações")
# ---------------------------------------------------------------------------
MSG_ATRASO_PADRAO = (
    "Olá, {responsavel}! 🌷\n\n"
    "Aqui é do *{clinica}*.\n"
    "Identificamos pagamento(s) em aberto referente(s) ao atendimento de *{paciente}*:\n\n"
    "{lista_parcelas}\n\n"
    "*Total em aberto: {total}*\n\n"
    "Para sua comodidade, o pagamento pode ser feito via PIX:\n"
    "🔑 Chave: {pix_chave}\n"
    "👤 {pix_titular} – {pix_banco}\n\n"
    "Se o pagamento já foi realizado, por favor desconsidere esta mensagem "
    "e nos envie o comprovante. 💙\n"
    "Qualquer dúvida, estamos à disposição!"
)
MSG_LEMBRETE_PADRAO = (
    "Olá, {responsavel}! 🌷\n\n"
    "Passando para lembrar que a mensalidade de *{paciente}* vence em *{vencimento}*.\n\n"
    "{lista_parcelas}\n\n"
    "Pagando até o vencimento o valor é de *{total}*. 💙\n"
    "PIX: {pix_chave} ({pix_titular} – {pix_banco})\n\n"
    "*{clinica}*"
)
MSG_RECIBO_PADRAO = (
    "Olá, {responsavel}! 🌷\n\n"
    "Confirmamos o recebimento de *{valor}* referente a *{servico}* "
    "({parcela}) do(a) paciente *{paciente}*, pago em {data} via {forma}.\n\n"
    "Muito obrigada pela confiança! 💙\n*{clinica}*"
)

CONFIG_PADRAO = {
    # Dados do Espaço
    "clinica_nome": config.APP_NOME,
    "clinica_documento": "",
    "clinica_telefone": "(81) 9 9767-3217",
    "clinica_email": "",
    "clinica_endereco": "",
    "clinica_cidade": "",
    "assinatura_nome": "Sharlene Soares de Lima",
    "assinatura_registro": "Neuropsicopedagoga – SBNPp 12081",
    # PIX / banco
    "pix_chave": "(81) 9 9767-3217",
    "pix_tipo": "Telefone",
    "pix_titular": "Sharlene Soares de Lima",
    "pix_banco": "Banco Santander",
    # Regras financeiras
    "tolerancia_dias": "0",          # dias após o vencimento antes de marcar "em atraso"
    "multa_percentual": "0",         # multa única por atraso (%)
    "juros_mes_percentual": "0",     # juros ao mês (%), proporcional aos dias
    "dias_vencimento": ",".join(config.DIAS_VENCIMENTO),
    "proximo_recibo": "1",
    # WhatsApp
    "whatsapp_modo": "link",         # link (WhatsApp Web/App) | api (WhatsApp Cloud API)
    "whatsapp_abrir_em": "web",      # web | app
    "ddd_padrao": "81",
    "api_versao": "v21.0",
    "api_token": "",
    "api_phone_id": "",
    "api_template_atraso": "",
    "api_template_idioma": "pt_BR",
    "cobranca_automatica": "0",      # 1 = envia sozinho ao abrir o sistema (só modo API)
    "cobranca_intervalo_dias": "7",  # não repetir a cobrança ao mesmo responsável antes disso
    "lembrete_dias_antes": "3",
    "msg_atraso": MSG_ATRASO_PADRAO,
    "msg_lembrete": MSG_LEMBRETE_PADRAO,
    "msg_recibo": MSG_RECIBO_PADRAO,
    # Backup
    "backup_automatico": "1",
    "backup_manter": "30",
    "ultimo_backup": "",
}


# ---------------------------------------------------------------------------
# Conexão
# ---------------------------------------------------------------------------

def conectar() -> sqlite3.Connection:
    """Abre uma conexão nova com o banco (linhas acessíveis por nome da coluna)."""
    config.garantir_pastas()
    conn = sqlite3.connect(config.DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def conexao():
    """
    Uso:  with conexao() as conn:
              conn.execute(...)
    Grava (commit) automaticamente no final; se der erro, desfaz (rollback).
    """
    conn = conectar()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def consultar(sql: str, parametros=()) -> list[dict]:
    """Executa um SELECT e devolve uma lista de dicionários."""
    with conexao() as conn:
        return [dict(linha) for linha in conn.execute(sql, parametros).fetchall()]


def consultar_um(sql: str, parametros=()) -> dict | None:
    """Executa um SELECT e devolve só a primeira linha (ou None)."""
    with conexao() as conn:
        linha = conn.execute(sql, parametros).fetchone()
        return dict(linha) if linha else None


def executar(sql: str, parametros=()) -> int:
    """Executa INSERT/UPDATE/DELETE. Devolve o id inserido (quando houver)."""
    with conexao() as conn:
        cursor = conn.execute(sql, parametros)
        return cursor.lastrowid


def registrar_auditoria(acao: str, detalhes: str = "", usuario: str | None = None) -> None:
    """Grava uma linha no histórico de ações (quem fez o quê)."""
    from app.core import sessao  # import tardio para evitar ciclo
    executar(
        "INSERT INTO auditoria (usuario, acao, detalhes) VALUES (?, ?, ?)",
        (usuario or sessao.nome_usuario(), acao, detalhes),
    )


# ---------------------------------------------------------------------------
# Criação / atualização da estrutura
# ---------------------------------------------------------------------------

def inicializar_banco() -> None:
    """Chamado ao abrir o sistema: cria/atualiza tabelas e dados iniciais."""
    with conexao() as conn:
        _migrar(conn)
        _dados_iniciais(conn)


def _migrar(conn: sqlite3.Connection) -> None:
    """Aplica, em ordem, as migrações que ainda não foram aplicadas."""
    versao_atual = conn.execute("PRAGMA user_version").fetchone()[0]
    for versao in sorted(MIGRACOES):
        if versao > versao_atual:
            conn.executescript(MIGRACOES[versao])
            conn.execute(f"PRAGMA user_version = {versao}")


def _dados_iniciais(conn: sqlite3.Connection) -> None:
    """Insere serviços, configurações e o usuário administrador (só se faltarem)."""
    # Configurações: só adiciona chaves que ainda não existem
    for chave, valor in CONFIG_PADRAO.items():
        conn.execute("INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES (?, ?)",
                     (chave, valor))

    # Serviços: só na primeira vez (tabela vazia)
    if conn.execute("SELECT COUNT(*) FROM servicos").fetchone()[0] == 0:
        conn.executemany(
            """INSERT INTO servicos (nome, categoria, tipo_cobranca, valor_cheio,
                   valor_pontualidade, parcelas_padrao, valor_entrada, descricao)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            SERVICOS_INICIAIS,
        )

    # Usuário administrador padrão (login: admin / senha: admin)
    if conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0:
        conn.execute(
            """INSERT INTO usuarios (nome, login, senha_hash, perfil, trocar_senha)
               VALUES (?, ?, ?, 'administrador', 1)""",
            ("Administrador", "admin", gerar_hash("admin")),
        )


def agora_texto() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
