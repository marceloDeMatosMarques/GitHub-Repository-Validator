# GitHub Repository Validator

Este projeto é um verificador online de repositórios GitHub em Python, projetado para avaliar se um repositório é confiável para uso em projetos de código gerado por IA.

## ✨ Funcionalidades

- **Avalia atividade e manutenção** do repositório
- **Verifica popularidade, documentação, licença, CI/testes e comunidade**
- **Aplica critérios de aprovação/reprovação** com base nos requisitos fornecidos
- **API REST** completa e **interface web moderna**
- 💾 **Persistência em SQLite** — salve repositórios avaliados
- 📂 **Categorização customizável** — crie suas próprias categorias (UI/UX, AI/ML, etc.)
- ⚖️ **Comparação lado a lado** — compare múltiplos repositórios da mesma categoria
- 📥 **Exportação** — exporte resultados em JSON ou CSV

## Instalação

1. Crie um ambiente Python 3.11+:

```bash
python -m venv .venv
.\.venv\Scripts\activate
```

2. Instale dependências:

```bash
pip install -r requirements.txt
```

3. Configure o token (veja próxima seção)

4. Execute a aplicação:

```bash
uvicorn app.main:app --reload
```

5. Acesse no navegador:

```text
http://127.0.0.1:8000
```

## Configuração do GitHub Token

### Por que um token?

Sem token, o GitHub aplica limite de 60 requisições por hora para IPs públicos. Com um token, sobe para 5.000 requisições/hora.

### Usando `.env`

1. Copie o arquivo `.env.example` para `.env`:

```bash
cp .env.example .env
```

2. Edite o `.env` e cole seu token:

```text
GITHUB_TOKEN=seu_token_aqui
```

### Como gerar o token

Existem dois tipos disponíveis no GitHub:

#### Opção 1: Personal Access Token (Classic) — Recomendado para simplicidade

1. Acesse: https://github.com/settings/tokens/new
2. Preencha:
   - **Token name**: `github-repo-validator`
   - **Expiration**: `30 days` ou `90 days`
   - **Scopes**: marque apenas `public_repo`
3. Clique em **"Generate token"**
4. Copie o token e cole no `.env`

#### Opção 2: Fine-grained Personal Access Token — Recomendado para segurança

1. Acesse: https://github.com/settings/personal-access-tokens/new
2. Preencha:
   - **Token name**: `github-repo-validator`
   - **Expiration**: `30 days` ou `90 days`
   - **Repository access**: `Public repositories (read-only)`
   - **Permissions**: `Contents: Read-only`
3. Clique em **"Generate token"**
4. Copie o token e cole no `.env`

Depois reinicie o servidor.

## Política de Segurança

Este repositório inclui uma política de segurança no arquivo `.github/SECURITY.md`.

Se você encontrar vulnerabilidades, siga as instruções desse arquivo para reportar de forma segura.

## Como Usar

### 1. Validar Repositório

1. Vá para a aba **🔍 Validar**
2. Digite o repositório no formato: `owner/repo`
3. Clique em **Avaliar**
4. Veja os resultados detalhados com scores

### 2. Salvar Repositório

Após validar, clique em **💾 Salvar** e escolha uma categoria.

Quando salvo, o repositório fica armazenado no banco de dados SQLite.

### 3. Gerenciar Categorias

1. Vá para a aba **📂 Categorias**
2. Clique em **+ Nova Categoria**
3. Defina nome e descrição
4. Suas categorias: `UI/UX`, `N8N`, `AI/ML`, `Architect FullStack`, `Spec-Driven`, etc.

### 4. Comparar Repositórios

1. Vá para a aba **💾 Salvos**
2. Selecione 2-5 repositórios clicando neles
3. Mude para a aba **⚖️ Comparar**
4. Clique em **Comparar Selecionados**
5. Veja lado a lado:
   - Todos os scores
   - Diferenças entre critérios
   - Qual é melhor em cada métrica

### 5. Exportar Dados

Na comparação, clique em **📥 JSON** ou **📥 CSV** para baixar os dados.

## Observações

A avaliação é baseada em heurísticas e dados públicos do GitHub. Para repositórios privados ou informações avançadas de segurança, são necessárias permissões adicionais.

Cada repositório salvo fica persistido no arquivo `repos.db` (SQLite).
