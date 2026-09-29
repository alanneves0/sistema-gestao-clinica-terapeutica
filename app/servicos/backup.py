"""
=============================================================================
 servicos/backup.py — Cópias de segurança do banco de dados
=============================================================================
 • Backup automático: 1 vez por dia, ao abrir o sistema (pode desligar).
 • Backup manual: botão em Configurações (pode salvar num pendrive).
 • Restaurar: substitui o banco atual por um backup (o atual é guardado antes).
 O backup usa a função oficial do SQLite (seguro mesmo com o sistema aberto).
 Mantém os últimos N backups automáticos (padrão 30).

 DICA: copie de vez em quando a pasta dados/backups para um pendrive ou
 nuvem (Google Drive/OneDrive). Se o computador quebrar, os dados estão salvos.
=============================================================================
"""
from __future__ import annotations

import shutil
import sqlite3
from datetime import date, datetime
from pathlib import Path

from app.core import config
from app.repositorios import configuracoes


def fazer_backup(destino: Path | str | None = None) -> Path:
    """Cria uma cópia do banco. Devolve o caminho do arquivo gerado."""
    config.garantir_pastas()
    if destino is None:
        destino = config.BACKUP_DIR / f"backup_{datetime.now():%Y%m%d_%H%M%S}.db"
    destino = Path(destino)
    origem = sqlite3.connect(config.DB_PATH)
    copia = sqlite3.connect(destino)
    try:
        origem.backup(copia)
    finally:
        copia.close()
        origem.close()
    configuracoes.salvar("ultimo_backup", date.today().isoformat())
    return destino


def backup_automatico() -> Path | None:
    """Faz o backup do dia (se ainda não foi feito) e apaga os mais antigos."""
    if configuracoes.obter("backup_automatico", "1") != "1":
        return None
    if configuracoes.obter("ultimo_backup") == date.today().isoformat():
        return None
    caminho = fazer_backup()
    manter = int(configuracoes.obter_numero("backup_manter", 30))
    antigos = sorted(config.BACKUP_DIR.glob("backup_*.db"))
    for arquivo in antigos[:-manter] if manter > 0 else []:
        arquivo.unlink(missing_ok=True)
    return caminho


def restaurar(arquivo: Path | str) -> Path:
    """
    Restaura um backup. Antes, guarda o banco atual como 'antes_restauracao_*.db'.
    Depois de restaurar, o sistema precisa ser reiniciado.
    """
    arquivo = Path(arquivo)
    teste = sqlite3.connect(arquivo)
    try:
        tabelas = {l[0] for l in teste.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        teste.close()
    if not {"pacientes", "parcelas", "pagamentos"} <= tabelas:
        raise ValueError("O arquivo escolhido não é um backup válido deste sistema.")
    seguranca = config.BACKUP_DIR / f"antes_restauracao_{datetime.now():%Y%m%d_%H%M%S}.db"
    if config.DB_PATH.exists():
        shutil.copy2(config.DB_PATH, seguranca)
    shutil.copy2(arquivo, config.DB_PATH)
    return seguranca
