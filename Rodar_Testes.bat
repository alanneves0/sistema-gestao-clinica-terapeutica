@echo off
cd /d "%~dp0"
set PYEXE=python
if exist ".venv\Scripts\python.exe" set PYEXE=.venv\Scripts\python.exe
"%PYEXE%" -m unittest discover -s tests -t . -v
pause
