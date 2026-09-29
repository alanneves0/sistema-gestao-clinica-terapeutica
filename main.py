"""
=============================================================================
 main.py — PONTO DE ENTRADA do sistema
=============================================================================
 Para abrir o sistema:   python main.py
 (ou dê dois cliques em "Executar.bat" no Windows)

 O que acontece ao abrir:
   1. cria as pastas de dados (dados/, backups/, recibos/, relatorios/)
   2. liga o registro de erros (dados/sistema.log)
   3. cria/atualiza o banco de dados SQLite (dados/espaco_shay.db)
   4. aplica o tema de cores da marca
   5. abre a janela de login
=============================================================================
"""
import sys


def verificar_dependencias() -> bool:
    """Confere se as bibliotecas necessárias estão instaladas."""
    faltando = []
    for modulo, pacote in (("customtkinter", "customtkinter"), ("PIL", "pillow"),
                           ("reportlab", "reportlab"), ("openpyxl", "openpyxl")):
        try:
            __import__(modulo)
        except ImportError:
            faltando.append(pacote)
    if faltando:
        print("=" * 70)
        print(" Faltam bibliotecas para rodar o sistema:", ", ".join(faltando))
        print(" Instale com o comando:")
        print("     python -m pip install -r requirements.txt")
        print(" (ou dê dois cliques em Instalar.bat)")
        print("=" * 70)
        try:  # se aberto sem console (pythonw), mostra o aviso numa janela
            import tkinter
            from tkinter import messagebox
            raiz = tkinter.Tk()
            raiz.withdraw()
            messagebox.showerror("Espaço Terapêutico Shay Soares",
                                 "Faltam bibliotecas: " + ", ".join(faltando) +
                                 "\n\nDê dois cliques em Instalar.bat e tente novamente.")
            raiz.destroy()
        except Exception:  # noqa: BLE001
            pass
        return False
    return True


def main() -> None:
    if not verificar_dependencias():
        sys.exit(1)

    # Modo demonstração: usa um banco separado, com pacientes fictícios
    modo_demo = "--demo" in sys.argv
    if modo_demo:
        import os
        from pathlib import Path
        base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
        os.environ["SHAY_DADOS"] = str(base / "dados_demo")

    from app.core import config, database
    from app.core.log import configurar_log
    from app.ui import tema

    config.garantir_pastas()
    log = configurar_log()
    log.info("Sistema iniciado (versão %s)", config.APP_VERSAO)
    database.inicializar_banco()
    if modo_demo:
        from app.core import demo
        demo.popular()
    tema.aplicar_tema()

    from app.ui.janela_principal import App   # importado depois do tema aplicado
    app = App()
    app.mainloop()
    log.info("Sistema encerrado")


if __name__ == "__main__":
    main()
