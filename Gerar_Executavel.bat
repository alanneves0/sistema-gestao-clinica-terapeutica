@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Gerando executavel (.exe) com PyInstaller...
if not exist ".venv\Scripts\python.exe" (
  echo Rode primeiro o Instalar.bat
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install pyinstaller
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --windowed --name EspacoShaySoares --icon assets\icone.ico --add-data "assets;assets" --collect-all customtkinter main.py
echo.
echo Executavel criado em: dist\EspacoShaySoares\EspacoShaySoares.exe
echo Copie a pasta dist\EspacoShaySoares inteira para onde quiser.
pause
