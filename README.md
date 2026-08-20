# printflow-ai
AI Operations Platform for intelligent print management

## Ambiente local no Windows

Pre-requisitos gratuitos:

- Git;
- Python 3.12;
- Node.js (necessario apenas para trabalhar no frontend).

Preparacao reproduzivel:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup-local.ps1
```

Validacao:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/test-local.ps1
```

O ambiente virtual `.venv`, arquivos `.env`, logs e saidas do Agent nao sao
versionados. Tokens e senhas nunca devem ser adicionados ao repositorio.
