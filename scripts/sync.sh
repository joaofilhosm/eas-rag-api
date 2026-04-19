#!/bin/bash
# Script de sincronizacao automatica para Linux/Mac
# Uso: ./sync.sh [mensagem]

cd "$(dirname "$0")/.."
python3 scripts/auto_sync.py "$@"