@echo off
REM Script de sincronizacao automatica para Windows
REM Uso: sync.bat [mensagem]

cd /d %~dp0..
python scripts\auto_sync.py %*
pause