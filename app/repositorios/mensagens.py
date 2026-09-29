"""
=============================================================================
 repositorios/mensagens.py — Histórico de mensagens de WhatsApp
=============================================================================
 Toda cobrança/lembrete/recibo enviado fica registrado aqui. Assim o sistema
 sabe quando foi a última cobrança de cada responsável e evita repetir
 mensagens em excesso.
   status: aberto  → mensagem aberta no WhatsApp (modo link, envio manual)
           enviado → enviada pela API oficial
           erro    → falhou (ver coluna 'detalhe')
=============================================================================
"""
from __future__ import annotations

from app.core.database import consultar, consultar_um, executar


def registrar(tipo: str, canal: str, telefone: str, texto: str, status: str,
              responsavel_id: int | None = None, paciente_id: int | None = None,
              detalhe: str = "") -> int:
    return executar(
        """INSERT INTO mensagens (responsavel_id, paciente_id, telefone, tipo, canal, texto,
               status, detalhe) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (responsavel_id, paciente_id, telefone, tipo, canal, texto, status, detalhe[:500]),
    )


def listar(limite: int = 300, busca: str = "") -> list[dict]:
    sql = """SELECT m.*, r.nome AS responsavel, p.nome AS paciente
               FROM mensagens m
               LEFT JOIN responsaveis r ON r.id = m.responsavel_id
               LEFT JOIN pacientes p ON p.id = m.paciente_id"""
    params: list = []
    if busca:
        sql += " WHERE r.nome LIKE ? OR p.nome LIKE ? OR m.telefone LIKE ?"
        params = [f"%{busca}%"] * 3
    sql += " ORDER BY m.id DESC LIMIT ?"
    params.append(limite)
    return consultar(sql, params)


def ultima(responsavel_id: int, tipo: str) -> dict | None:
    return consultar_um("SELECT * FROM mensagens WHERE responsavel_id=? AND tipo=? AND status<>'erro' "
                        "ORDER BY id DESC LIMIT 1", (responsavel_id, tipo))
