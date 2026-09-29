"""
=============================================================================
 seguranca.py — Senhas dos usuários
=============================================================================
 As senhas NUNCA são gravadas em texto puro. Guardamos apenas um "hash"
 (impressão digital) gerado com PBKDF2-SHA256 + sal aleatório, que é o
 padrão recomendado. Mesmo quem abrir o arquivo do banco não descobre a senha.
=============================================================================
"""
import hashlib
import hmac
import secrets

_ITERACOES = 200_000


def gerar_hash(senha: str) -> str:
    """Gera o texto que será gravado no banco: 'sal$hash'."""
    sal = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), bytes.fromhex(sal), _ITERACOES)
    return f"{sal}${digest.hex()}"


def conferir_senha(senha: str, hash_salvo: str) -> bool:
    """Confere se a senha digitada corresponde ao hash gravado."""
    try:
        sal, esperado = hash_salvo.split("$", 1)
    except (ValueError, AttributeError):
        return False
    digest = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), bytes.fromhex(sal), _ITERACOES)
    return hmac.compare_digest(digest.hex(), esperado)
