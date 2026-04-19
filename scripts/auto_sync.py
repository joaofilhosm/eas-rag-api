#!/usr/bin/env python3
"""
Script de Auto-Sync para GitHub
Sincroniza mudanças automaticamente com commit e push

Uso:
    python scripts/auto_sync.py              # Commit e push
    python scripts/auto_sync.py --watch      # Monitora mudanças continuamente
    python scripts/auto_sync.py --interval 60 # Sync a cada 60 segundos
"""

import subprocess
import os
import sys
from datetime import datetime
from pathlib import Path
import time
import hashlib


def run_command(cmd, cwd=None):
    """Executa comando shell e retorna output."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd or os.getcwd(),
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), 1


def get_changed_files():
    """Retorna lista de arquivos modificados."""
    output, code = run_command("git status --porcelain")
    if code != 0:
        return []
    return [line.strip() for line in output.split('\n') if line.strip()]


def get_file_hash(filepath):
    """Calcula hash MD5 de um arquivo."""
    try:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None


def auto_commit(message=None):
    """Faz commit automático de todas as mudanças."""
    changed = get_changed_files()

    if not changed:
        print("✓ Nenhuma mudança detectada")
        return False

    # Adiciona todos os arquivos
    run_command("git add -A")

    # Gera mensagem de commit
    if not message:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        num_files = len(changed)
        message = f"Auto-sync: {num_files} arquivo(s) alterados - {timestamp}"

    # Faz o commit
    output, code = run_command(f'git commit -m "{message}"')

    if code == 0:
        print(f"✓ Commit criado: {message}")
        return True
    else:
        print(f"✗ Erro ao criar commit: {output}")
        return False


def auto_push():
    """Faz push para o remote."""
    output, code = run_command("git push origin main")

    if code == 0:
        print("✓ Push realizado com sucesso")
        return True
    else:
        print(f"✗ Erro no push: {output}")
        return False


def sync(message=None):
    """Sincroniza: commit + push."""
    print(f"\n{'='*50}")
    print(f"🔄 Sincronizando... {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*50}")

    # Commit
    if auto_commit(message):
        # Push
        auto_push()
    else:
        print("⏭️ Pulando push (sem mudanças)")


def watch_mode(interval=30):
    """Monitora mudanças e sincroniza automaticamente."""
    print(f"👀 Modo Watch ativado (intervalo: {interval}s)")
    print("Pressione Ctrl+C para parar\n")

    last_hashes = {}

    while True:
        try:
            # Pega arquivos modificados
            changed = get_changed_files()

            # Calcula hashes dos arquivos
            current_hashes = {}
            for file_line in changed:
                # Extrai nome do arquivo (remove prefixo de status)
                filepath = file_line[3:].strip()
                if os.path.exists(filepath):
                    current_hashes[filepath] = get_file_hash(filepath)

            # Compara com hashes anteriores
            if current_hashes != last_hashes:
                if last_hashes:  # Só sync se não for a primeira execução
                    sync()
                last_hashes = current_hashes.copy()

            time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n👋 Sincronização encerrada")
            break


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Auto-sync para GitHub')
    parser.add_argument('--watch', '-w', action='store_true', help='Modo watch (monitora mudanças)')
    parser.add_argument('--interval', '-i', type=int, default=30, help='Intervalo em segundos (default: 30)')
    parser.add_argument('--message', '-m', type=str, help='Mensagem de commit personalizada')
    parser.add_argument('--pull', '-p', action='store_true', help='Faz pull antes de sync')

    args = parser.parse_args()

    # Vai para o diretório do projeto
    project_dir = Path(__file__).parent.parent
    os.chdir(project_dir)

    if args.pull:
        print("⬇️ Fazendo pull...")
        run_command("git pull origin main")

    if args.watch:
        watch_mode(args.interval)
    else:
        sync(args.message)


if __name__ == "__main__":
    main()