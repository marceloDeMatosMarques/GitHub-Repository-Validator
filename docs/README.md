# Documentação do Projeto

Este diretório contém documentação adicional que complementa o README.

## Visão geral

O GitHub Repository Validator avalia repositórios públicos do GitHub em diferentes critérios de qualidade e segurança.

## Estrutura do projeto

- `app/` — código fonte do backend e frontend
- `app/static/` — interface web
- `app/tests/` — testes automatizados
- `CHANGELOG.md` — histórico de versões
- `.github/SECURITY.md` — política de segurança
- `README.md` — documentação principal

## Como usar

1. Instale dependências:
```bash
pip install -r requirements.txt
```
2. Crie `.env` a partir de `.env.example`
3. Execute:
```bash
uvicorn app.main:app --reload
```
4. Acesse `http://127.0.0.1:8000`

## Health check

A aplicação pode ser verificada enviando um GET para `/health` após implementação.
