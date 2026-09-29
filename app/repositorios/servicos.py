"""
=============================================================================
 repositorios/servicos.py — Tabela de serviços e preços
=============================================================================
 Cada serviço tem:
   • valor_cheio         → valor da mensalidade (ou total do pacote)
   • valor_pontualidade  → valor com desconto se pago ATÉ o vencimento
                           (ex.: Fono R$ 220,00 / R$ 200,00 no carnê)
   • tipo_cobranca       → mensal | parcelado | unico
   • parcelas_padrao     → sugestão de nº de parcelas ao contratar
   • valor_entrada       → 1ª parcela diferente (ex.: Avaliação R$ 100 + 3x R$ 300)
=============================================================================
"""
from __future__ import annotations

from app.core import config
from app.core.database import consultar, consultar_um, executar, registrar_auditoria

CAMPOS = ["nome", "categoria", "tipo_cobranca", "valor_cheio", "valor_pontualidade",
          "parcelas_padrao", "valor_entrada", "descricao", "ativo"]
CATEGORIAS = ["Terapia", "Pacote", "Avaliação", "Taxa", "Outro"]


def listar(somente_ativos: bool = False) -> list[dict]:
    sql = "SELECT * FROM servicos"
    if somente_ativos:
        sql += " WHERE ativo = 1"
    sql += " ORDER BY CASE categoria WHEN 'Terapia' THEN 1 WHEN 'Pacote' THEN 2 " \
           "WHEN 'Avaliação' THEN 3 WHEN 'Taxa' THEN 4 ELSE 5 END, nome"
    return consultar(sql)


def obter(servico_id: int) -> dict | None:
    return consultar_um("SELECT * FROM servicos WHERE id = ?", (servico_id,))


def validar(dados: dict) -> list[str]:
    erros = []
    if not (dados.get("nome") or "").strip():
        erros.append("Informe o nome do serviço.")
    if dados.get("tipo_cobranca") not in config.TIPOS_COBRANCA:
        erros.append("Tipo de cobrança inválido.")
    if float(dados.get("valor_cheio") or 0) <= 0:
        erros.append("O valor deve ser maior que zero.")
    if float(dados.get("valor_pontualidade") or 0) > float(dados.get("valor_cheio") or 0):
        erros.append("O valor com desconto de pontualidade não pode ser maior que o valor cheio.")
    if int(dados.get("parcelas_padrao") or 0) < 1:
        erros.append("O número de parcelas deve ser pelo menos 1.")
    if float(dados.get("valor_entrada") or 0) >= float(dados.get("valor_cheio") or 0) > 0 \
            and dados.get("tipo_cobranca") == config.TIPO_PARCELADO:
        erros.append("A entrada deve ser menor que o valor total do pacote.")
    return erros


def salvar(dados: dict, servico_id: int | None = None) -> int:
    dados = {k: dados[k] for k in CAMPOS if k in dados}
    if not dados.get("valor_pontualidade"):
        dados["valor_pontualidade"] = dados.get("valor_cheio", 0)
    erros = validar(dados)
    if erros:
        raise ValueError("\n".join(erros))
    if servico_id:
        executar(f"UPDATE servicos SET {', '.join(f'{c}=?' for c in dados)} WHERE id=?",
                 [*dados.values(), servico_id])
        registrar_auditoria("Serviço alterado", dados["nome"])
        return servico_id
    novo = executar(f"INSERT INTO servicos ({', '.join(dados)}) VALUES ({', '.join('?' for _ in dados)})",
                    list(dados.values()))
    registrar_auditoria("Serviço criado", dados["nome"])
    return novo


def definir_ativo(servico_id: int, ativo: bool) -> None:
    executar("UPDATE servicos SET ativo = ? WHERE id = ?", (1 if ativo else 0, servico_id))
