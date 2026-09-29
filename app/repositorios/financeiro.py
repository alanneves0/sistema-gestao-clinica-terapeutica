"""
=============================================================================
 repositorios/financeiro.py — Contratos, parcelas, pagamentos e indicadores
=============================================================================
 COMO O FINANCEIRO FUNCIONA
 --------------------------
 1. CONTRATO: ao incluir um serviço para o paciente (ex.: Fonoaudiologia),
    cria-se um contrato. Ele pode ser:
       • Mensal/Parcelado → gera uma parcela por mês (carnê)
       • À vista          → gera uma única parcela com o valor total
 2. PARCELAS: cada parcela tem vencimento, valor cheio e valor de pontualidade.
 3. PAGAMENTOS: cada recebimento (PIX, cartão, dinheiro…) é lançado contra
    uma parcela. Uma parcela pode receber mais de um pagamento (pagamento
    parcial), e cada pagamento gera um nº de recibo.

 SITUAÇÃO DE CADA PARCELA (calculada automaticamente):
   • Pago               → parcela quitada
   • Pendente (em dia)  → ainda não paga, mas dentro do prazo
   • Em atraso          → não paga e o vencimento (+ tolerância) já passou
   • Cancelado          → parcela cancelada (não é cobrada)

 VALOR DEVIDO:
   • Até o vencimento (+ tolerância) → valor de pontualidade (ex.: R$ 200)
   • Depois                          → valor cheio (ex.: R$ 220) + multa/juros
                                       (multa e juros configuráveis; padrão 0%)
=============================================================================
"""
from __future__ import annotations

from datetime import date, timedelta

from app.core import config, sessao, utils
from app.core.database import conexao, consultar, consultar_um, registrar_auditoria
from app.repositorios import configuracoes

TOLERANCIA_CENTAVOS = 0.009  # evita problemas de arredondamento


# ---------------------------------------------------------------------------
# Regras (multa, juros, tolerância) vindas das configurações
# ---------------------------------------------------------------------------

def regras() -> dict:
    return {
        "tolerancia": int(configuracoes.obter_numero("tolerancia_dias", 0)),
        "multa": configuracoes.obter_numero("multa_percentual", 0),
        "juros_mes": configuracoes.obter_numero("juros_mes_percentual", 0),
    }


# ---------------------------------------------------------------------------
# 1) Simulação e criação de contratos
# ---------------------------------------------------------------------------

def simular_parcelas(tipo_cobranca: str, modalidade: str, valor_cheio: float,
                     valor_pontualidade: float, num_parcelas: int, valor_entrada: float,
                     primeiro_vencimento: date, dia_vencimento: int,
                     desconto_percentual: float = 0.0) -> list[dict]:
    """
    Calcula as parcelas de um contrato SEM gravar nada (usado na pré-visualização).

    tipo_cobranca:
      mensal    → valor_cheio é o valor de CADA mensalidade
      parcelado → valor_cheio é o TOTAL do pacote, dividido em parcelas
      unico     → uma única cobrança
    modalidade:
      parcelado → várias parcelas
      a_vista   → uma parcela com o total (mensal à vista usa o valor de pontualidade)
    """
    num_parcelas = max(1, int(num_parcelas or 1))
    fator = 1 - float(desconto_percentual or 0) / 100
    valor_pontualidade = valor_pontualidade or valor_cheio

    def venc(i: int) -> date:
        return utils.adicionar_meses(primeiro_vencimento, i, dia_vencimento)

    # --- À vista: uma única parcela com o total -----------------------------
    if modalidade == config.MODALIDADE_A_VISTA or tipo_cobranca == config.TIPO_UNICO:
        if tipo_cobranca == config.TIPO_MENSAL:
            total = round(valor_pontualidade * num_parcelas * fator, 2)
            cheio = round(valor_cheio * num_parcelas * fator, 2)
        else:
            total = cheio = round(valor_cheio * fator, 2)
        if modalidade == config.MODALIDADE_A_VISTA:
            cheio = total  # à vista não tem diferença de pontualidade
        return [{"numero": 1, "vencimento": primeiro_vencimento, "valor": cheio,
                 "valor_pontualidade": total}]

    # --- Mensalidades: mesmo valor todo mês ---------------------------------
    if tipo_cobranca == config.TIPO_MENSAL:
        cheio = round(valor_cheio * fator, 2)
        pont = round(valor_pontualidade * fator, 2)
        return [{"numero": i + 1, "vencimento": venc(i), "valor": cheio,
                 "valor_pontualidade": pont} for i in range(num_parcelas)]

    # --- Pacote parcelado: divide o total (com entrada opcional) -------------
    total = round(valor_cheio * fator, 2)
    entrada = round(float(valor_entrada or 0) * fator, 2)
    valores: list[float] = []
    if entrada > 0 and num_parcelas > 1:
        restante = round(total - entrada, 2)
        demais = num_parcelas - 1
        base = round(restante / demais, 2)
        valores = [entrada] + [base] * demais
    else:
        base = round(total / num_parcelas, 2)
        valores = [base] * num_parcelas
    # ajusta centavos na última parcela para fechar exatamente o total
    valores[-1] = round(valores[-1] + (total - sum(valores)), 2)
    return [{"numero": i + 1, "vencimento": venc(i), "valor": v, "valor_pontualidade": v}
            for i, v in enumerate(valores)]


def criar_contrato(paciente_id: int, servico_id: int | None, descricao: str, modalidade: str,
                   dia_vencimento: int, parcelas: list[dict], desconto_percentual: float = 0,
                   data_inicio: date | None = None, profissional: str = "",
                   dias_atendimento: str = "", horario: str = "", observacoes: str = "") -> int:
    """Grava o contrato e suas parcelas. Devolve o id do contrato."""
    if not parcelas:
        raise ValueError("O contrato precisa ter pelo menos uma parcela.")
    if not descricao.strip():
        raise ValueError("Informe a descrição do serviço.")
    for p in parcelas:
        if float(p["valor"]) <= 0:
            raise ValueError("Todas as parcelas devem ter valor maior que zero.")
    total = round(sum(float(p["valor_pontualidade"]) for p in parcelas), 2)
    with conexao() as conn:
        contrato_id = conn.execute(
            """INSERT INTO contratos (paciente_id, servico_id, descricao, modalidade, data_inicio,
                   dia_vencimento, num_parcelas, valor_total, desconto_percentual, profissional,
                   dias_atendimento, horario, observacoes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (paciente_id, servico_id, descricao.strip(), modalidade,
             utils.data_iso(data_inicio or utils.hoje()), int(dia_vencimento), len(parcelas),
             total, float(desconto_percentual or 0), profissional, dias_atendimento, horario,
             observacoes),
        ).lastrowid
        conn.executemany(
            "INSERT INTO parcelas (contrato_id, numero, vencimento, valor, valor_pontualidade) "
            "VALUES (?, ?, ?, ?, ?)",
            [(contrato_id, p["numero"], utils.data_iso(p["vencimento"]), round(float(p["valor"]), 2),
              round(float(p["valor_pontualidade"]), 2)) for p in parcelas],
        )
    registrar_auditoria("Contrato criado", f"{descricao} – paciente id {paciente_id} – "
                                           f"{len(parcelas)} parcela(s)")
    return contrato_id


def renovar_contrato(contrato_id: int, quantidade: int) -> int:
    """
    Gera mais parcelas mensais para um contrato (ex.: renovar por mais 6 meses),
    continuando a partir do último vencimento e com os mesmos valores.
    """
    ultima = consultar_um("SELECT * FROM parcelas WHERE contrato_id=? ORDER BY numero DESC LIMIT 1",
                          (contrato_id,))
    contrato = consultar_um("SELECT * FROM contratos WHERE id=?", (contrato_id,))
    if not ultima or not contrato:
        raise ValueError("Contrato não encontrado.")
    base = utils.para_date(ultima["vencimento"])
    novas = [(contrato_id, ultima["numero"] + i + 1,
              utils.data_iso(utils.adicionar_meses(base, i + 1, contrato["dia_vencimento"])),
              ultima["valor"], ultima["valor_pontualidade"]) for i in range(int(quantidade))]
    with conexao() as conn:
        conn.executemany("INSERT INTO parcelas (contrato_id, numero, vencimento, valor, "
                         "valor_pontualidade) VALUES (?, ?, ?, ?, ?)", novas)
        conn.execute("""UPDATE contratos SET status='ativo',
                          num_parcelas = (SELECT COUNT(*) FROM parcelas WHERE contrato_id=?),
                          valor_total = (SELECT SUM(valor_pontualidade) FROM parcelas
                                          WHERE contrato_id=? AND status<>'cancelada')
                        WHERE id=?""", (contrato_id, contrato_id, contrato_id))
    registrar_auditoria("Contrato renovado", f"contrato {contrato_id} +{quantidade} parcela(s)")
    return len(novas)


def alterar_status_contrato(contrato_id: int, status: str, cancelar_abertas: bool = False) -> None:
    """status: ativo | encerrado | cancelado. Pode cancelar as parcelas em aberto."""
    with conexao() as conn:
        conn.execute("UPDATE contratos SET status=? WHERE id=?", (status, contrato_id))
        if cancelar_abertas:
            conn.execute("UPDATE parcelas SET status='cancelada' WHERE contrato_id=? AND status='aberta' "
                         "AND NOT EXISTS (SELECT 1 FROM pagamentos g WHERE g.parcela_id = parcelas.id)",
                         (contrato_id,))
    registrar_auditoria(f"Contrato {status}", f"contrato {contrato_id}")


def excluir_contrato(contrato_id: int) -> None:
    if consultar_um("SELECT 1 FROM pagamentos g JOIN parcelas p ON p.id=g.parcela_id "
                    "WHERE p.contrato_id=? LIMIT 1", (contrato_id,)):
        raise ValueError("Este contrato já tem pagamentos. Use 'Cancelar contrato' em vez de excluir.")
    with conexao() as conn:
        conn.execute("DELETE FROM contratos WHERE id=?", (contrato_id,))
    registrar_auditoria("Contrato excluído", f"contrato {contrato_id}")


def listar_contratos(paciente_id: int) -> list[dict]:
    return consultar("""
        SELECT c.*,
               (SELECT COUNT(*) FROM parcelas p WHERE p.contrato_id=c.id AND p.status='paga') AS pagas,
               (SELECT COUNT(*) FROM parcelas p WHERE p.contrato_id=c.id AND p.status<>'cancelada') AS total_parcelas
          FROM contratos c WHERE c.paciente_id=? ORDER BY c.status='ativo' DESC, c.data_inicio DESC""",
                     (paciente_id,))


# ---------------------------------------------------------------------------
# 2) Cálculo da situação de cada parcela
# ---------------------------------------------------------------------------

def calcular_valor_devido(parcela: dict, data_ref: date, r: dict | None = None) -> tuple[float, float]:
    """
    Quanto a parcela vale na data informada.
    Devolve (valor_devido, encargos) — encargos = multa + juros.
    """
    r = r or regras()
    venc = utils.para_date(parcela["vencimento"])
    limite = venc + timedelta(days=r["tolerancia"])
    if data_ref <= limite:
        return round(float(parcela["valor_pontualidade"]), 2), 0.0
    base = float(parcela["valor"])
    dias = (data_ref - venc).days
    encargos = base * r["multa"] / 100 + base * r["juros_mes"] / 100 / 30 * dias
    return round(base + encargos, 2), round(encargos, 2)


def calcular_situacao(parcela: dict, data_ref: date | None = None, r: dict | None = None) -> dict:
    """
    Recebe a linha da parcela (com total_pago e total_desconto) e acrescenta:
      situacao, valor_devido, encargos, saldo, dias_atraso, parcial.
    """
    data_ref = data_ref or utils.hoje()
    r = r or regras()
    p = dict(parcela)
    venc = utils.para_date(p["vencimento"])
    pago = float(p.get("total_pago") or 0)
    desconto = float(p.get("total_desconto") or 0)
    p["dias_atraso"] = 0
    p["encargos"] = 0.0

    if p["status"] == "cancelada":
        p.update(situacao=config.SITUACAO_CANCELADO, valor_devido=0.0, saldo=0.0, parcial=False)
        return p
    if p["status"] == "paga":
        p.update(situacao=config.SITUACAO_PAGO, valor_devido=round(pago + desconto, 2), saldo=0.0,
                 parcial=False)
        return p

    devido, encargos = calcular_valor_devido(p, data_ref, r)
    saldo = round(max(0.0, devido - pago - desconto), 2)
    atrasada = data_ref > venc + timedelta(days=r["tolerancia"])
    p.update(valor_devido=devido, encargos=encargos, saldo=saldo, parcial=pago > 0,
             situacao=config.SITUACAO_ATRASO if atrasada else config.SITUACAO_EM_DIA,
             dias_atraso=(data_ref - venc).days if atrasada else 0)
    return p


# SQL base: parcela + contrato + paciente + responsável + totais pagos
_SQL_PARCELAS = """
    SELECT pa.*,
           c.descricao AS servico, c.modalidade, c.paciente_id, c.status AS contrato_status,
           (SELECT COUNT(*) FROM parcelas x WHERE x.contrato_id = c.id) AS total_parcelas,
           pc.nome AS paciente, pc.ativo AS paciente_ativo,
           r.id AS responsavel_id, r.nome AS responsavel, r.whatsapp AS responsavel_whatsapp,
           r.telefone AS responsavel_telefone, r.cpf AS responsavel_cpf,
           COALESCE((SELECT SUM(g.valor) FROM pagamentos g WHERE g.parcela_id = pa.id), 0) AS total_pago,
           COALESCE((SELECT SUM(g.desconto) FROM pagamentos g WHERE g.parcela_id = pa.id), 0) AS total_desconto,
           (SELECT MAX(g.data_pagamento) FROM pagamentos g WHERE g.parcela_id = pa.id) AS ultimo_pagamento,
           (SELECT g.forma_pagamento FROM pagamentos g WHERE g.parcela_id = pa.id
             ORDER BY g.id DESC LIMIT 1) AS forma_pagamento
      FROM parcelas pa
      JOIN contratos c   ON c.id = pa.contrato_id
      JOIN pacientes pc  ON pc.id = c.paciente_id
      LEFT JOIN responsaveis r ON r.id = pc.responsavel_id
"""


def rotulo_parcela(p: dict) -> str:
    """'Parcela 02/06' (ou 'Parcela única')."""
    total = p.get("total_parcelas") or 1
    if total == 1:
        return "Parcela única"
    return f"Parcela {p['numero']:02d}/{total:02d}"


def listar_parcelas(situacao: str | None = None, busca: str = "", data_ini: date | None = None,
                    data_fim: date | None = None, paciente_id: int | None = None,
                    contrato_id: int | None = None, responsavel_id: int | None = None,
                    incluir_canceladas: bool = False, data_ref: date | None = None) -> list[dict]:
    """
    Lista parcelas já com a situação calculada.
      situacao  → filtra por uma das situações (Pago, Pendente (em dia), Em atraso…)
      data_ini/data_fim → período de VENCIMENTO
    """
    filtros, params = [], []
    if data_ini:
        filtros.append("pa.vencimento >= ?")
        params.append(utils.data_iso(data_ini))
    if data_fim:
        filtros.append("pa.vencimento <= ?")
        params.append(utils.data_iso(data_fim))
    if paciente_id:
        filtros.append("c.paciente_id = ?")
        params.append(paciente_id)
    if contrato_id:
        filtros.append("pa.contrato_id = ?")
        params.append(contrato_id)
    if responsavel_id:
        filtros.append("pc.responsavel_id = ?")
        params.append(responsavel_id)
    if not incluir_canceladas and situacao != config.SITUACAO_CANCELADO:
        filtros.append("pa.status <> 'cancelada'")
    sql = _SQL_PARCELAS + (" WHERE " + " AND ".join(filtros) if filtros else "")
    sql += " ORDER BY pa.vencimento, pc.nome"

    r = regras()
    termo = utils.sem_acentos(busca.strip())
    resultado = []
    for linha in consultar(sql, params):
        if termo and termo not in utils.sem_acentos(
                f"{linha['paciente']} {linha['responsavel'] or ''} {linha['servico']}"):
            continue
        p = calcular_situacao(linha, data_ref, r)
        if situacao and situacao != "Todas" and p["situacao"] != situacao:
            continue
        p["rotulo"] = rotulo_parcela(p)
        resultado.append(p)
    return resultado


def obter_parcela(parcela_id: int, data_ref: date | None = None) -> dict | None:
    linha = consultar_um(_SQL_PARCELAS + " WHERE pa.id = ?", (parcela_id,))
    if not linha:
        return None
    p = calcular_situacao(linha, data_ref)
    p["rotulo"] = rotulo_parcela(p)
    return p


def editar_parcela(parcela_id: int, vencimento: date, valor: float, valor_pontualidade: float,
                   observacoes: str = "") -> None:
    if valor <= 0 or valor_pontualidade <= 0:
        raise ValueError("Os valores devem ser maiores que zero.")
    if valor_pontualidade > valor:
        raise ValueError("O valor de pontualidade não pode ser maior que o valor cheio.")
    with conexao() as conn:
        conn.execute("UPDATE parcelas SET vencimento=?, valor=?, valor_pontualidade=?, observacoes=? "
                     "WHERE id=?", (utils.data_iso(vencimento), valor, valor_pontualidade,
                                    observacoes, parcela_id))
    registrar_auditoria("Parcela editada", f"parcela {parcela_id}")


def cancelar_parcela(parcela_id: int, cancelar: bool = True) -> None:
    """Cancela (não cobra mais) ou reabre uma parcela."""
    if cancelar and consultar_um("SELECT 1 FROM pagamentos WHERE parcela_id=?", (parcela_id,)):
        raise ValueError("Esta parcela tem pagamentos. Estorne os pagamentos antes de cancelar.")
    with conexao() as conn:
        conn.execute("UPDATE parcelas SET status=? WHERE id=?",
                     ("cancelada" if cancelar else "aberta", parcela_id))
    registrar_auditoria("Parcela " + ("cancelada" if cancelar else "reaberta"), f"parcela {parcela_id}")


# ---------------------------------------------------------------------------
# 3) Pagamentos
# ---------------------------------------------------------------------------

def registrar_pagamento(parcela_id: int, data_pagamento: date, valor: float, forma: str,
                        parcelas_cartao: int = 1, desconto: float = 0.0, acrescimo: float = 0.0,
                        taxa_operadora: float = 0.0, observacoes: str = "",
                        quitar: bool | None = None) -> dict:
    """
    Lança um pagamento na parcela.
      quitar=None → decide sozinho: quita se (valor + desconto) cobrir o saldo devido
      quitar=True → força a quitação (ex.: acordo com o responsável)
    Devolve {'pagamento_id', 'recibo_numero', 'quitada', 'saldo_restante'}.
    """
    p = obter_parcela(parcela_id, data_ref=data_pagamento)
    if not p:
        raise ValueError("Parcela não encontrada.")
    if p["status"] == "cancelada":
        raise ValueError("Parcela cancelada não pode receber pagamento.")
    if p["status"] == "paga":
        raise ValueError("Esta parcela já está quitada.")
    valor = round(float(valor or 0), 2)
    desconto = round(float(desconto or 0), 2)
    if valor <= 0 and desconto <= 0:
        raise ValueError("Informe o valor recebido.")
    if forma not in config.FORMAS_PAGAMENTO:
        raise ValueError("Forma de pagamento inválida.")
    if data_pagamento > utils.hoje() + timedelta(days=1):
        raise ValueError("A data do pagamento não pode estar no futuro.")

    saldo_restante = round(p["saldo"] - valor - desconto, 2)
    if quitar is None:
        quitar = saldo_restante <= TOLERANCIA_CENTAVOS

    recibo = configuracoes.proximo_numero_recibo()
    with conexao() as conn:
        pagamento_id = conn.execute(
            """INSERT INTO pagamentos (parcela_id, data_pagamento, valor, desconto, acrescimo,
                   forma_pagamento, parcelas_cartao, taxa_operadora, recibo_numero, observacoes, usuario)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (parcela_id, utils.data_iso(data_pagamento), valor, desconto, float(acrescimo or 0),
             forma, int(parcelas_cartao or 1), float(taxa_operadora or 0), recibo, observacoes,
             sessao.nome_usuario()),
        ).lastrowid
        if quitar:
            conn.execute("UPDATE parcelas SET status='paga', data_quitacao=? WHERE id=?",
                         (utils.data_iso(data_pagamento), parcela_id))
    registrar_auditoria("Pagamento registrado",
                        f"{utils.formatar_moeda(valor)} ({forma}) – {p['paciente']} – {p['rotulo']}")
    return {"pagamento_id": pagamento_id, "recibo_numero": recibo, "quitada": bool(quitar),
            "saldo_restante": max(0.0, saldo_restante)}


def quitar_varias(parcela_ids: list[int], data_pagamento: date, forma: str,
                  parcelas_cartao: int = 1, observacoes: str = "") -> list[dict]:
    """Quita várias parcelas de uma vez (ex.: responsável pagou 3 meses juntos)."""
    resultados = []
    for pid in parcela_ids:
        p = obter_parcela(pid, data_ref=data_pagamento)
        if p and p["status"] == "aberta":
            resultados.append(registrar_pagamento(pid, data_pagamento, p["saldo"], forma,
                                                  parcelas_cartao, observacoes=observacoes, quitar=True))
    return resultados


def estornar_pagamento(pagamento_id: int) -> None:
    """Desfaz um pagamento lançado por engano (a parcela volta a ficar em aberto)."""
    g = consultar_um("SELECT * FROM pagamentos WHERE id=?", (pagamento_id,))
    if not g:
        raise ValueError("Pagamento não encontrado.")
    with conexao() as conn:
        conn.execute("DELETE FROM pagamentos WHERE id=?", (pagamento_id,))
        conn.execute("UPDATE parcelas SET status='aberta', data_quitacao=NULL "
                     "WHERE id=? AND status='paga'", (g["parcela_id"],))
    registrar_auditoria("Pagamento estornado",
                        f"recibo {g['recibo_numero']} – {utils.formatar_moeda(g['valor'])}")


def listar_pagamentos(data_ini: date | None = None, data_fim: date | None = None,
                      forma: str = "", busca: str = "", parcela_id: int | None = None,
                      paciente_id: int | None = None, pagamento_id: int | None = None) -> list[dict]:
    """Lista os pagamentos recebidos (livro-caixa)."""
    sql = """
        SELECT g.*, pa.numero, pa.vencimento, pa.contrato_id,
               (SELECT COUNT(*) FROM parcelas x WHERE x.contrato_id = pa.contrato_id) AS total_parcelas,
               c.descricao AS servico, pc.id AS paciente_id, pc.nome AS paciente,
               r.nome AS responsavel, r.cpf AS responsavel_cpf, r.whatsapp AS responsavel_whatsapp,
               r.telefone AS responsavel_telefone, r.id AS responsavel_id
          FROM pagamentos g
          JOIN parcelas pa ON pa.id = g.parcela_id
          JOIN contratos c ON c.id = pa.contrato_id
          JOIN pacientes pc ON pc.id = c.paciente_id
          LEFT JOIN responsaveis r ON r.id = pc.responsavel_id
    """
    filtros, params = [], []
    if data_ini:
        filtros.append("g.data_pagamento >= ?")
        params.append(utils.data_iso(data_ini))
    if data_fim:
        filtros.append("g.data_pagamento <= ?")
        params.append(utils.data_iso(data_fim))
    if forma and forma != "Todas":
        filtros.append("g.forma_pagamento = ?")
        params.append(forma)
    if parcela_id:
        filtros.append("g.parcela_id = ?")
        params.append(parcela_id)
    if paciente_id:
        filtros.append("pc.id = ?")
        params.append(paciente_id)
    if pagamento_id:
        filtros.append("g.id = ?")
        params.append(pagamento_id)
    if filtros:
        sql += " WHERE " + " AND ".join(filtros)
    sql += " ORDER BY g.data_pagamento DESC, g.id DESC"
    termo = utils.sem_acentos(busca.strip())
    linhas = []
    for g in consultar(sql, params):
        if termo and termo not in utils.sem_acentos(f"{g['paciente']} {g['responsavel'] or ''} "
                                                    f"{g['servico']} {g['recibo_numero']}"):
            continue
        g["rotulo"] = rotulo_parcela(g)
        linhas.append(g)
    return linhas


def obter_pagamento(pagamento_id: int) -> dict | None:
    encontrados = listar_pagamentos(pagamento_id=pagamento_id)
    return encontrados[0] if encontrados else None


# ---------------------------------------------------------------------------
# 4) Inadimplência e lembretes (usados na tela de Cobranças / WhatsApp)
# ---------------------------------------------------------------------------

def _agrupar_por_responsavel(parcelas: list[dict], tipo_msg: str) -> list[dict]:
    grupos: dict = {}
    for p in parcelas:
        chave = p.get("responsavel_id") or f"pac{p['paciente_id']}"
        g = grupos.setdefault(chave, {
            "responsavel_id": p.get("responsavel_id"), "responsavel": p.get("responsavel") or p["paciente"],
            "whatsapp": p.get("responsavel_whatsapp") or p.get("responsavel_telefone") or "",
            "pacientes": [], "paciente_ids": [], "parcelas": [], "total": 0.0, "maior_atraso": 0,
            "vencimento_mais_antigo": p["vencimento"],
        })
        if p["paciente"] not in g["pacientes"]:
            g["pacientes"].append(p["paciente"])
            g["paciente_ids"].append(p["paciente_id"])
        g["parcelas"].append(p)
        g["total"] = round(g["total"] + p["saldo"], 2)
        g["maior_atraso"] = max(g["maior_atraso"], p.get("dias_atraso", 0))
        g["vencimento_mais_antigo"] = min(g["vencimento_mais_antigo"], p["vencimento"])

    # data da última mensagem desse tipo enviada ao responsável
    ultimas = {m["responsavel_id"]: m["ultima"] for m in consultar(
        "SELECT responsavel_id, MAX(enviado_em) AS ultima FROM mensagens WHERE tipo=? "
        "AND status IN ('aberto','enviado') GROUP BY responsavel_id", (tipo_msg,))}
    lista = list(grupos.values())
    for g in lista:
        g["ultima_cobranca"] = ultimas.get(g["responsavel_id"])
    return lista


def inadimplentes(data_ref: date | None = None) -> list[dict]:
    """Responsáveis com parcelas EM ATRASO, com total e maior atraso."""
    atrasadas = listar_parcelas(situacao=config.SITUACAO_ATRASO, data_ref=data_ref)
    atrasadas = [p for p in atrasadas if p["saldo"] > TOLERANCIA_CENTAVOS]
    lista = _agrupar_por_responsavel(atrasadas, "atraso")
    return sorted(lista, key=lambda g: (-g["maior_atraso"], -g["total"]))


def a_vencer(dias: int = 3, data_ref: date | None = None) -> list[dict]:
    """Responsáveis com parcelas que vencem nos próximos N dias (para lembretes)."""
    data_ref = data_ref or utils.hoje()
    parcelas = listar_parcelas(situacao=config.SITUACAO_EM_DIA, data_ini=data_ref,
                               data_fim=data_ref + timedelta(days=int(dias)), data_ref=data_ref)
    parcelas = [p for p in parcelas if p["saldo"] > TOLERANCIA_CENTAVOS]
    return sorted(_agrupar_por_responsavel(parcelas, "lembrete"),
                  key=lambda g: g["vencimento_mais_antigo"])


# ---------------------------------------------------------------------------
# 5) Indicadores (painel inicial e relatórios)
# ---------------------------------------------------------------------------

def _limites_mes(ano: int, mes: int) -> tuple[date, date]:
    inicio = date(ano, mes, 1)
    fim = utils.adicionar_meses(inicio, 1, 1) - timedelta(days=1)
    return inicio, fim


def indicadores(ano: int | None = None, mes: int | None = None) -> dict:
    """Números do mês: recebido, a receber, em atraso, inadimplentes etc."""
    h = utils.hoje()
    ano, mes = ano or h.year, mes or h.month
    inicio, fim = _limites_mes(ano, mes)

    recebido = consultar_um("SELECT COALESCE(SUM(valor),0) AS t, COUNT(*) AS n FROM pagamentos "
                            "WHERE data_pagamento BETWEEN ? AND ?",
                            (utils.data_iso(inicio), utils.data_iso(fim)))
    parcelas_mes = listar_parcelas(data_ini=inicio, data_fim=fim)
    a_receber = sum(p["saldo"] for p in parcelas_mes if p["situacao"] == config.SITUACAO_EM_DIA)
    previsto = sum(float(p["valor_pontualidade"]) for p in parcelas_mes)
    todas_atrasadas = listar_parcelas(situacao=config.SITUACAO_ATRASO)
    em_atraso = sum(p["saldo"] for p in todas_atrasadas)
    responsaveis_atraso = {p.get("responsavel_id") or p["paciente_id"] for p in todas_atrasadas}
    pagas_mes = sum(1 for p in parcelas_mes if p["situacao"] == config.SITUACAO_PAGO)

    return {
        "ano": ano, "mes": mes,
        "recebido": round(recebido["t"], 2), "qtd_pagamentos": recebido["n"],
        "a_receber": round(a_receber, 2),
        "previsto": round(previsto, 2),
        "em_atraso": round(em_atraso, 2),
        "qtd_parcelas_atraso": len(todas_atrasadas),
        "qtd_inadimplentes": len(responsaveis_atraso),
        "parcelas_mes": len(parcelas_mes),
        "pagas_mes": pagas_mes,
        "adimplencia": round(100 * pagas_mes / len(parcelas_mes), 1) if parcelas_mes else 100.0,
    }


def receita_mensal(meses: int = 6) -> list[dict]:
    """Recebido x previsto nos últimos N meses (gráfico do painel)."""
    h = utils.hoje()
    resultado = []
    for i in range(meses - 1, -1, -1):
        ref = utils.adicionar_meses(date(h.year, h.month, 1), -i, 1)
        inicio, fim = _limites_mes(ref.year, ref.month)
        rec = consultar_um("SELECT COALESCE(SUM(valor),0) t FROM pagamentos WHERE data_pagamento "
                           "BETWEEN ? AND ?", (utils.data_iso(inicio), utils.data_iso(fim)))["t"]
        prev = consultar_um("SELECT COALESCE(SUM(valor_pontualidade),0) t FROM parcelas WHERE "
                            "status<>'cancelada' AND vencimento BETWEEN ? AND ?",
                            (utils.data_iso(inicio), utils.data_iso(fim)))["t"]
        resultado.append({"rotulo": f"{utils.MESES_ABREV[ref.month - 1]}/{str(ref.year)[2:]}",
                          "recebido": round(rec, 2), "previsto": round(prev, 2)})
    return resultado


def por_forma_pagamento(data_ini: date, data_fim: date) -> list[dict]:
    return consultar("SELECT forma_pagamento AS forma, COUNT(*) AS qtd, SUM(valor) AS total "
                     "FROM pagamentos WHERE data_pagamento BETWEEN ? AND ? "
                     "GROUP BY forma_pagamento ORDER BY total DESC",
                     (utils.data_iso(data_ini), utils.data_iso(data_fim)))


def por_servico(data_ini: date, data_fim: date) -> list[dict]:
    return consultar("""SELECT c.descricao AS servico, COUNT(*) AS qtd, SUM(g.valor) AS total
                          FROM pagamentos g JOIN parcelas p ON p.id=g.parcela_id
                          JOIN contratos c ON c.id=p.contrato_id
                         WHERE g.data_pagamento BETWEEN ? AND ?
                         GROUP BY c.descricao ORDER BY total DESC""",
                     (utils.data_iso(data_ini), utils.data_iso(data_fim)))


def situacao_por_paciente() -> dict[int, str]:
    """
    Resumo por paciente para a lista de pacientes:
      'Em atraso' | 'Pendente (em dia)' | 'Pago' (tudo quitado) | '' (sem cobranças)
    """
    resumo: dict[int, str] = {}
    prioridade = {config.SITUACAO_ATRASO: 3, config.SITUACAO_EM_DIA: 2, config.SITUACAO_PAGO: 1}
    h = utils.hoje()
    for p in listar_parcelas():
        sit = p["situacao"]
        # parcelas futuras (mais de 31 dias) não contam como "pendente" no resumo
        if sit == config.SITUACAO_EM_DIA and utils.para_date(p["vencimento"]) > h + timedelta(days=31):
            sit = config.SITUACAO_PAGO
        atual = resumo.get(p["paciente_id"])
        if atual is None or prioridade.get(sit, 0) > prioridade.get(atual, 0):
            resumo[p["paciente_id"]] = sit
    return resumo


def resumo_paciente(paciente_id: int) -> dict:
    """Totais da ficha financeira de um paciente."""
    parcelas = listar_parcelas(paciente_id=paciente_id)
    return {
        "pago": round(sum(float(p.get("total_pago") or 0) for p in parcelas), 2),
        "em_aberto": round(sum(p["saldo"] for p in parcelas if p["situacao"] == config.SITUACAO_EM_DIA), 2),
        "em_atraso": round(sum(p["saldo"] for p in parcelas if p["situacao"] == config.SITUACAO_ATRASO), 2),
        "parcelas": parcelas,
    }
