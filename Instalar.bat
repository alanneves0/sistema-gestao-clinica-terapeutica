@echo off
chcp 65001 >nul
title Instalacao - Espaco Terapeutico Shay Soares
cd /d "%~dp0"
echo ==========================================================
echo   Instalando o sistema do Espaco Terapeutico Shay Soares
echo ==========================================================
echo.
set PY=
where py >nul 2>nul && set PY=py -3
if "%PY%"=="" where python >nul 2>nul && set PY=python
if "%PY%"=="" (
  echo [ERRO] Python nao encontrado.
  echo Baixe em https://www.python.org/downloads/ e, na instalacao,
  echo marque a opcao "Add Python to PATH". Depois rode este arquivo de novo.
  pause
  exit /b 1
)
echo [1/3] Criando ambiente isolado (.venv)...
if not exist ".venv\Scripts\python.exe" %PY% -m venv .venv
echo [2/3] Instalando bibliotecas (precisa de internet)...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERRO] Falha ao instalar as bibliotecas. Verifique a internet e tente de novo.
  pause
  exit /b 1
)
echo [3/3] Criando atalho na Area de Trabalho...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Espaco Shay Soares.lnk'); $s.TargetPath='%~dp0Executar.bat'; $s.WorkingDirectory='%~dp0'; $s.IconLocation='%~dp0assets\icone.ico'; $s.WindowStyle=7; $s.Save()"
echo.
echo Pronto! Use o atalho "Espaco Shay Soares" na Area de Trabalho
echo ou de dois cliques em Executar.bat.
echo Primeiro acesso: usuario admin / senha admin
pause
