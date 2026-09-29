"""
=============================================================================
 sessao.py — Usuário que está usando o sistema no momento
=============================================================================
 Guarda quem fez login, para registrar nos pagamentos e na auditoria.
=============================================================================
"""
_usuario_atual: dict | None = None


def iniciar(usuario: dict) -> None:
    """Chamado após o login bem-sucedido."""
    global _usuario_atual
    _usuario_atual = usuario


def encerrar() -> None:
    global _usuario_atual
    _usuario_atual = None


def usuario() -> dict | None:
    return _usuario_atual


def nome_usuario() -> str:
    return (_usuario_atual or {}).get("nome", "sistema")


def eh_administrador() -> bool:
    return (_usuario_atual or {}).get("perfil") == "administrador"
