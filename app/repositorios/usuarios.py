"""
=============================================================================
 repositorios/usuarios.py — Usuários e login
=============================================================================
 Perfis:
   administrador → acesso total (configurações, usuários, excluir registros)
   recepcao      → cadastro, financeiro e cobranças
=============================================================================
"""
from __future__ import annotations

from app.core.database import consultar, consultar_um, executar, registrar_auditoria
from app.core.seguranca import conferir_senha, gerar_hash

PERFIS = {"administrador": "Administrador", "recepcao": "Recepção"}


def autenticar(login: str, senha: str) -> dict | None:
    """Confere login e senha. Devolve o usuário (sem o hash) ou None."""
    u = consultar_um("SELECT * FROM usuarios WHERE login = ? AND ativo = 1", (login.strip(),))
    if u and conferir_senha(senha, u["senha_hash"]):
        u.pop("senha_hash", None)
        return u
    return None


def listar() -> list[dict]:
    return consultar("SELECT id, nome, login, perfil, ativo, criado_em FROM usuarios ORDER BY nome")


def criar(nome: str, login: str, senha: str, perfil: str = "recepcao") -> int:
    if not nome.strip() or not login.strip():
        raise ValueError("Informe nome e login.")
    if len(senha) < 4:
        raise ValueError("A senha deve ter pelo menos 4 caracteres.")
    if consultar_um("SELECT id FROM usuarios WHERE login = ?", (login.strip(),)):
        raise ValueError("Já existe um usuário com esse login.")
    novo = executar("INSERT INTO usuarios (nome, login, senha_hash, perfil) VALUES (?, ?, ?, ?)",
                    (nome.strip(), login.strip(), gerar_hash(senha), perfil))
    registrar_auditoria("Usuário criado", login)
    return novo


def alterar_senha(usuario_id: int, nova_senha: str) -> None:
    if len(nova_senha) < 4:
        raise ValueError("A senha deve ter pelo menos 4 caracteres.")
    executar("UPDATE usuarios SET senha_hash = ?, trocar_senha = 0 WHERE id = ?",
             (gerar_hash(nova_senha), usuario_id))
    registrar_auditoria("Senha alterada", f"usuário id {usuario_id}")


def definir_ativo(usuario_id: int, ativo: bool) -> None:
    if not ativo:
        admins = consultar_um("SELECT COUNT(*) n FROM usuarios WHERE perfil='administrador' "
                              "AND ativo=1 AND id <> ?", (usuario_id,))
        alvo = consultar_um("SELECT perfil FROM usuarios WHERE id=?", (usuario_id,))
        if alvo and alvo["perfil"] == "administrador" and admins["n"] == 0:
            raise ValueError("Não é possível desativar o único administrador.")
    executar("UPDATE usuarios SET ativo = ? WHERE id = ?", (1 if ativo else 0, usuario_id))
