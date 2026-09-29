"""
=============================================================================
 repositorios/configuracoes.py — Leitura e gravação das configurações
=============================================================================
 As configurações ficam na tabela "configuracoes" no formato chave → valor.
 Exemplo:  pix_chave → "(81) 9 9767-3217"
=============================================================================
"""
from __future__ import annotations

from app.core.database import conexao, consultar, consultar_um, executar


def obter(chave: str, padrao: str = "") -> str:
    """Lê uma configuração. Se não existir, devolve o valor padrão."""
    linha = consultar_um("SELECT valor FROM configuracoes WHERE chave = ?", (chave,))
    return linha["valor"] if linha and linha["valor"] is not None else padrao


def obter_numero(chave: str, padrao: float = 0.0) -> float:
    """Lê uma configuração numérica (aceita vírgula como decimal)."""
    try:
        return float(str(obter(chave, str(padrao))).replace(",", "."))
    except ValueError:
        return padrao


def obter_todas() -> dict[str, str]:
    """Devolve todas as configurações num dicionário."""
    return {l["chave"]: l["valor"] or "" for l in consultar("SELECT chave, valor FROM configuracoes")}


def salvar(chave: str, valor) -> None:
    executar("INSERT INTO configuracoes (chave, valor) VALUES (?, ?) "
             "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor", (chave, str(valor)))


def salvar_varias(valores: dict) -> None:
    with conexao() as conn:
        conn.executemany(
            "INSERT INTO configuracoes (chave, valor) VALUES (?, ?) "
            "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
            [(k, str(v)) for k, v in valores.items()],
        )


def proximo_numero_recibo() -> int:
    """Reserva e devolve o próximo número de recibo (sequencial, sem repetir)."""
    with conexao() as conn:
        linha = conn.execute("SELECT valor FROM configuracoes WHERE chave='proximo_recibo'").fetchone()
        numero = int(linha["valor"]) if linha and str(linha["valor"]).isdigit() else 1
        conn.execute("INSERT INTO configuracoes (chave, valor) VALUES ('proximo_recibo', ?) "
                     "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor", (str(numero + 1),))
        return numero
