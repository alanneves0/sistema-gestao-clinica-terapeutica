"""
=============================================================================
 repositorios/pacientes.py — Cadastro de pacientes e responsáveis
=============================================================================
 Regras:
   • Todo paciente tem um RESPONSÁVEL FINANCEIRO (quem recebe as cobranças).
   • Para adultos que pagam o próprio tratamento, marque
     "paciente é o próprio responsável": o sistema copia os dados do paciente
     para o responsável automaticamente.
   • Um mesmo responsável pode ter vários pacientes (ex.: irmãos).
=============================================================================
"""
from __future__ import annotations

from app.core import utils
from app.core.database import conexao, consultar, consultar_um, registrar_auditoria

# Colunas que podem ser gravadas em cada tabela (proteção contra campos indevidos)
CAMPOS_RESPONSAVEL = [
    "nome", "cpf", "rg", "data_nascimento", "parentesco", "profissao", "telefone",
    "whatsapp", "telefone_alt", "email", "cep", "logradouro", "numero",
    "complemento", "bairro", "cidade", "uf", "observacoes",
]
CAMPOS_PACIENTE = [
    "nome", "nome_social", "data_nascimento", "sexo", "cpf", "rg", "cartao_sus",
    "telefone", "whatsapp", "email", "convenio", "num_carteirinha", "escola", "serie",
    "turno", "ocupacao", "diagnosticos", "cid", "nivel_suporte", "laudo", "medicacoes",
    "alergias", "medico_responsavel", "encaminhado_por", "queixa_principal",
    "observacoes", "emergencia_nome", "emergencia_telefone", "emergencia_parentesco",
    "autoriza_imagem", "consentimento_lgpd", "proprio_responsavel", "ativo",
]


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------

def validar(paciente: dict, responsavel: dict) -> list[str]:
    """Confere os dados antes de salvar. Devolve a lista de problemas encontrados."""
    erros = []
    if not (paciente.get("nome") or "").strip():
        erros.append("Informe o nome do paciente.")
    if not paciente.get("data_nascimento"):
        erros.append("Informe a data de nascimento do paciente.")
    if paciente.get("cpf") and not utils.validar_cpf(paciente["cpf"]):
        erros.append("CPF do paciente inválido.")
    if not utils.validar_email(paciente.get("email", "")):
        erros.append("E-mail do paciente inválido.")

    if not paciente.get("proprio_responsavel"):
        if not (responsavel.get("nome") or "").strip():
            erros.append("Informe o nome do responsável.")
        if responsavel.get("cpf") and not utils.validar_cpf(responsavel["cpf"]):
            erros.append("CPF do responsável inválido.")
        if not utils.validar_email(responsavel.get("email", "")):
            erros.append("E-mail do responsável inválido.")
        contato = responsavel.get("whatsapp") or responsavel.get("telefone")
    else:
        contato = paciente.get("whatsapp") or paciente.get("telefone")
        idade = utils.calcular_idade(paciente.get("data_nascimento"))
        if idade is not None and idade < 18:
            erros.append("Paciente menor de 18 anos precisa de um responsável legal.")
    if not contato:
        erros.append("Informe ao menos um telefone/WhatsApp de contato do responsável.")
    elif not utils.telefone_whatsapp(contato):
        erros.append("Telefone/WhatsApp do responsável parece inválido (use DDD + número).")
    return erros


def _limpar(dados: dict, campos: list[str]) -> dict:
    """Mantém só os campos permitidos, tira espaços e padroniza formatos."""
    limpo = {}
    for campo in campos:
        if campo not in dados:
            continue
        valor = dados[campo]
        if isinstance(valor, str):
            valor = valor.strip()
        if campo in ("cpf",) and valor:
            valor = utils.formatar_cpf(valor)
        if campo in ("telefone", "whatsapp", "telefone_alt", "emergencia_telefone") and valor:
            valor = utils.formatar_telefone(valor)
        if campo == "cep" and valor:
            valor = utils.formatar_cep(valor)
        if campo == "data_nascimento":
            valor = utils.data_iso(valor)
        if isinstance(valor, bool):
            valor = 1 if valor else 0
        limpo[campo] = valor
    return limpo


# ---------------------------------------------------------------------------
# Gravação
# ---------------------------------------------------------------------------

def salvar(paciente: dict, responsavel: dict, paciente_id: int | None = None,
           responsavel_id: int | None = None) -> int:
    """
    Cria ou atualiza o paciente e seu responsável numa única transação.
    - paciente_id: None para cadastro novo.
    - responsavel_id: id de um responsável já existente (ex.: irmão já cadastrado).
    Devolve o id do paciente.
    """
    erros = validar(paciente, responsavel)
    if erros:
        raise ValueError("\n".join(erros))

    p = _limpar(paciente, CAMPOS_PACIENTE)
    r = _limpar(responsavel, CAMPOS_RESPONSAVEL)

    # Adulto responsável por si: copia os dados pessoais do paciente
    if p.get("proprio_responsavel"):
        for campo in ("nome", "cpf", "rg", "data_nascimento", "telefone", "whatsapp", "email"):
            r[campo] = p.get(campo) or r.get(campo)
        r["parentesco"] = "O(a) próprio(a) paciente"

    with conexao() as conn:
        # 1) Responsável
        if responsavel_id:
            colunas = ", ".join(f"{c} = ?" for c in r)
            conn.execute(f"UPDATE responsaveis SET {colunas}, atualizado_em = datetime('now','localtime') "
                         f"WHERE id = ?", [*r.values(), responsavel_id])
        else:
            colunas = ", ".join(r)
            marcas = ", ".join("?" for _ in r)
            responsavel_id = conn.execute(f"INSERT INTO responsaveis ({colunas}) VALUES ({marcas})",
                                          list(r.values())).lastrowid
        p["responsavel_id"] = responsavel_id

        # 2) Paciente
        if paciente_id:
            colunas = ", ".join(f"{c} = ?" for c in p)
            conn.execute(f"UPDATE pacientes SET {colunas}, atualizado_em = datetime('now','localtime') "
                         f"WHERE id = ?", [*p.values(), paciente_id])
            acao = "Paciente atualizado"
        else:
            colunas = ", ".join(p)
            marcas = ", ".join("?" for _ in p)
            paciente_id = conn.execute(f"INSERT INTO pacientes ({colunas}) VALUES ({marcas})",
                                       list(p.values())).lastrowid
            acao = "Paciente cadastrado"

    registrar_auditoria(acao, f"{p.get('nome')} (id {paciente_id})")
    return paciente_id


def definir_ativo(paciente_id: int, ativo: bool) -> None:
    with conexao() as conn:
        conn.execute("UPDATE pacientes SET ativo = ? WHERE id = ?", (1 if ativo else 0, paciente_id))
        if not ativo:  # ao inativar, encerra contratos ativos (parcelas pagas continuam no histórico)
            conn.execute("UPDATE contratos SET status='encerrado' WHERE paciente_id=? AND status='ativo'",
                         (paciente_id,))
    registrar_auditoria("Paciente " + ("reativado" if ativo else "inativado"), f"id {paciente_id}")


def excluir(paciente_id: int) -> None:
    """Exclui definitivamente o paciente e todo o seu histórico financeiro."""
    pac = obter(paciente_id)
    with conexao() as conn:
        conn.execute("DELETE FROM pacientes WHERE id = ?", (paciente_id,))
        # remove o responsável se ele não tiver mais nenhum paciente
        if pac and pac.get("responsavel_id"):
            conn.execute("DELETE FROM responsaveis WHERE id = ? AND NOT EXISTS "
                         "(SELECT 1 FROM pacientes WHERE responsavel_id = ?)",
                         (pac["responsavel_id"], pac["responsavel_id"]))
    registrar_auditoria("Paciente excluído", f"{pac.get('nome') if pac else ''} (id {paciente_id})")


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------

def obter(paciente_id: int) -> dict | None:
    """Devolve o paciente com os dados do responsável em p['responsavel']."""
    p = consultar_um("SELECT * FROM pacientes WHERE id = ?", (paciente_id,))
    if not p:
        return None
    p["responsavel"] = obter_responsavel(p["responsavel_id"]) if p.get("responsavel_id") else {}
    return p


def obter_responsavel(responsavel_id: int) -> dict:
    return consultar_um("SELECT * FROM responsaveis WHERE id = ?", (responsavel_id,)) or {}


def listar(busca: str = "", somente_ativos: bool | None = True, faixa: str = "Todas",
           diagnostico: str = "") -> list[dict]:
    """
    Lista pacientes com o nome/contato do responsável.
    busca procura em: nome do paciente, nome do responsável, CPF e telefones.
    """
    sql = """
        SELECT p.*, r.nome AS responsavel_nome, r.whatsapp AS responsavel_whatsapp,
               r.telefone AS responsavel_telefone, r.parentesco AS responsavel_parentesco,
               r.cpf AS responsavel_cpf
          FROM pacientes p
          LEFT JOIN responsaveis r ON r.id = p.responsavel_id
    """
    filtros, params = [], []
    if somente_ativos is not None:
        filtros.append("p.ativo = ?")
        params.append(1 if somente_ativos else 0)
    if filtros:
        sql += " WHERE " + " AND ".join(filtros)
    sql += " ORDER BY p.nome COLLATE NOCASE"
    linhas = consultar(sql, params)

    termo = utils.sem_acentos(busca.strip())
    digitos = utils.somente_digitos(busca)
    resultado = []
    for p in linhas:
        if termo:
            texto = utils.sem_acentos(" ".join(str(p.get(c) or "") for c in
                                               ("nome", "nome_social", "responsavel_nome")))
            numeros = utils.somente_digitos(" ".join(str(p.get(c) or "") for c in
                                                     ("cpf", "responsavel_cpf", "whatsapp", "telefone",
                                                      "responsavel_whatsapp", "responsavel_telefone")))
            if termo not in texto and not (digitos and len(digitos) >= 3 and digitos in numeros):
                continue
        if faixa and faixa != "Todas":
            if not faixa.startswith(utils.faixa_etaria(p.get("data_nascimento"))):
                continue
        if diagnostico and diagnostico != "Todos":
            if diagnostico not in (p.get("diagnosticos") or ""):
                continue
        p["idade"] = utils.calcular_idade(p.get("data_nascimento"))
        resultado.append(p)
    return resultado


def buscar_responsaveis(busca: str = "") -> list[dict]:
    """Lista responsáveis (para vincular um novo paciente a um responsável existente)."""
    linhas = consultar("""
        SELECT r.*, GROUP_CONCAT(p.nome, ', ') AS pacientes
          FROM responsaveis r LEFT JOIN pacientes p ON p.responsavel_id = r.id
         GROUP BY r.id ORDER BY r.nome COLLATE NOCASE""")
    termo = utils.sem_acentos(busca)
    return [r for r in linhas if not termo or termo in utils.sem_acentos(
        f"{r['nome']} {r.get('pacientes') or ''} {r.get('cpf') or ''}")]


def contagem_por_diagnostico() -> dict[str, int]:
    """Quantos pacientes ativos há por diagnóstico (usado no painel)."""
    contagem: dict[str, int] = {}
    for linha in consultar("SELECT diagnosticos FROM pacientes WHERE ativo = 1"):
        for d in (linha["diagnosticos"] or "").split(";"):
            d = d.strip()
            if d:
                contagem[d] = contagem.get(d, 0) + 1
    return dict(sorted(contagem.items(), key=lambda x: -x[1]))


def totais() -> dict:
    linha = consultar_um("""SELECT SUM(ativo = 1) AS ativos, SUM(ativo = 0) AS inativos,
                                   COUNT(*) AS total FROM pacientes""")
    return {k: (linha or {}).get(k) or 0 for k in ("ativos", "inativos", "total")}
