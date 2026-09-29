"""
=============================================================================
 log.py — Registro de erros
=============================================================================
 Tudo que der errado é anotado em dados/sistema.log, com data e hora.
 Se algum dia o sistema apresentar um problema, esse arquivo ajuda a
 descobrir a causa.
=============================================================================
"""
import logging
from logging.handlers import RotatingFileHandler

from app.core import config


def configurar_log() -> logging.Logger:
    config.garantir_pastas()
    logger = logging.getLogger("shay")
    if logger.handlers:            # já configurado
        return logger
    logger.setLevel(logging.INFO)
    arquivo = RotatingFileHandler(config.LOG_PATH, maxBytes=1_000_000, backupCount=3,
                                  encoding="utf-8")
    arquivo.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(arquivo)
    return logger


def logger() -> logging.Logger:
    return logging.getLogger("shay")
