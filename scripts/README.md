# Scripts de Sincronização Automática

Este diretório contém scripts para sincronização automática com GitHub.

## Arquivos

| Arquivo | Descrição |
|---------|-----------|
| `auto_sync.py` | Script principal de auto-sync |
| `sync.bat` | Atalho para Windows |
| `sync.sh` | Atalho para Linux/Mac |

## Uso

### Sincronização Manual

```bash
# Windows
.\scripts\sync.bat

# Linux/Mac
./scripts/sync.sh

# Ou diretamente
python scripts/auto_sync.py
```

### Com mensagem personalizada

```bash
python scripts/auto_sync.py -m "Minha mensagem de commit"
```

### Modo Watch (Monitoramento Contínuo)

```bash
# Monitora mudanças a cada 30 segundos (padrão)
python scripts/auto_sync.py --watch

# Com intervalo customizado (60 segundos)
python scripts/auto_sync.py --watch --interval 60
```

### Pull antes de sincronizar

```bash
python scripts/auto_sync.py --pull
```

## Git Hook (Auto-Push)

O hook `post-commit` em `.git/hooks/` executa automaticamente:

- `git push origin main` após cada commit local

### Desativar Auto-Push

```bash
rm .git/hooks/post-commit
```

### Reativar Auto-Push

```bash
# Linux/Mac
cp scripts/../.git/hooks/post-commit .git/hooks/
chmod +x .git/hooks/post-commit

# Windows
copy scripts\..\git\hooks\post-commit .git\hooks\
```

## Variáveis de Ambiente

O script usa as credenciais configuradas no git:

```bash
git config user.name
git config user.email
```

## Exemplos

```bash
# Commit rápido com timestamp
python scripts/auto_sync.py

# Commit com mensagem específica
python scripts/auto_sync.py -m "feat: adiciona novo endpoint"

# Modo watch para desenvolvimento contínuo
python scripts/auto_sync.py --watch --interval 10
```

## Integração com CI/CD

Pode ser integrado em pipelines:

```yaml
# GitHub Actions
- name: Auto Sync
  run: python scripts/auto_sync.py -m "ci: auto sync"
```