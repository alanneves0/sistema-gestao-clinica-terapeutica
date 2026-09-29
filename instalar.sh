#!/usr/bin/env bash
# Instalação no Linux / macOS
cd "$(dirname "$0")"
python3 -m venv .venv && .venv/bin/python -m pip install --upgrade pip && .venv/bin/python -m pip install -r requirements.txt
echo "Pronto! Para abrir: ./executar.sh   (Linux: pode ser preciso 'sudo apt install python3-tk')"
