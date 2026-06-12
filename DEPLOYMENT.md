# 📦 Guia de Deployment

Instruções passo a passo para fazer deploy do GitHub Repository Validator em produção.

## 🚀 Opção 1: Deploy Local (Desenvolvimento)

### Pré-requisitos
- Python 3.11+
- Git
- GitHub Token (token de acesso)

### Passos

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/m3br-repositorios.git
cd m3br-repositorios
```

2. Crie ambiente Python:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.\.venv\Scripts\activate   # Windows
```

3. Instale dependências:
```bash
pip install -r requirements.txt
```

4. Configure o token GitHub:
```bash
cp .env.example .env
# Edite .env e adicione seu GITHUB_TOKEN
```

5. Execute o servidor:
```bash
uvicorn app.main:app --reload
```

6. Acesse no navegador:
```
http://127.0.0.1:8000
```

---

## 🐳 Opção 2: Deploy com Docker

### Dockerfile

Crie um arquivo `Dockerfile` na raiz do projeto:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Expor porta
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000')"

# Comando para iniciar
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
    volumes:
      - ./repos.db:/app/repos.db
    restart: unless-stopped
```

### Build e Run

```bash
# Build imagem
docker build -t github-repo-validator .

# Run container
docker run -e GITHUB_TOKEN=seu_token -p 8000:8000 github-repo-validator

# Ou com docker-compose
docker-compose up -d
```

---

## ☁️ Opção 3: Deploy em Heroku

### Pré-requisitos
- Conta Heroku
- Heroku CLI instalado

### Passos

1. Crie um arquivo `Procfile`:
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

2. Crie um arquivo `runtime.txt`:
```
python-3.11.0
```

3. Login no Heroku:
```bash
heroku login
heroku create seu-app-name
```

4. Configure variáveis de ambiente:
```bash
heroku config:set GITHUB_TOKEN=seu_token
```

5. Deploy:
```bash
git push heroku main
```

6. Veja os logs:
```bash
heroku logs --tail
```

---

## ☁️ Opção 4: Deploy em AWS (EC2 + RDS)

### Pré-requisitos
- Conta AWS
- EC2 instance com Ubuntu 22.04
- RDS PostgreSQL (opcional, para dados mais robustos)

### Passos (simplificado)

1. SSH na instância:
```bash
ssh -i sua-chave.pem ubuntu@seu-ip-publico
```

2. Instale dependências:
```bash
sudo apt-get update
sudo apt-get install python3.11 python3.11-venv python3-pip nginx
```

3. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/m3br-repositorios.git
cd m3br-repositorios
```

4. Configure venv:
```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

5. Configure GITHUB_TOKEN:
```bash
echo "GITHUB_TOKEN=seu_token" > .env
```

6. Configure Nginx como reverse proxy:
```nginx
server {
    listen 80;
    server_name seu-dominio.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

7. Configure Systemd service:
```ini
[Unit]
Description=GitHub Repository Validator
After=network.target

[Service]
Type=notify
User=ubuntu
WorkingDirectory=/home/ubuntu/m3br-repositorios
ExecStart=/home/ubuntu/m3br-repositorios/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

8. Inicie o serviço:
```bash
sudo systemctl start github-repo-validator
sudo systemctl enable github-repo-validator
```

---

## ☁️ Opção 5: Deploy em Railway.app

### Pré-requisitos
- Conta Railway
- GitHub repository

### Passos

1. Acesse https://railway.app
2. Clique em "New Project"
3. Selecione "Deploy from GitHub"
4. Autorize e selecione seu repositório
5. Adicione variável de ambiente:
   - `GITHUB_TOKEN`=seu_token
6. Deploy automático começará

---

## 📋 Checklist Pré-Deploy

- [ ] Todos os testes passam: `pytest app/tests/`
- [ ] Não há debug mode: `DEBUG=False`
- [ ] GITHUB_TOKEN configurado
- [ ] Database backup criado (se aplicável)
- [ ] Logging configurado
- [ ] Health check implementado
- [ ] CORS configurado (se necessário)
- [ ] Rate limiting implementado
- [ ] Monitoring ativo

---

## 🔒 Segurança em Produção

### 1. Adicione autenticação (se compartilhado)

Edite `app/main.py`:

```python
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.get("/validate")
async def validate(
    repo: str = Query(...),
    credentials: HTTPAuthCredentials = Depends(security)
) -> Any:
    # Validar token
    if credentials.credentials != getenv("API_TOKEN"):
        raise HTTPException(status_code=401, detail="Não autorizado")
    # ... resto do código
```

### 2. Configure CORS

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["seu-dominio.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. Rate limiting

```bash
pip install slowapi
```

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.get("/validate")
@limiter.limit("5/minute")
async def validate(request: Request, repo: str = Query(...)):
    # ...
```

### 4. Use HTTPS

```bash
# Com Let's Encrypt (Certbot)
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d seu-dominio.com
```

---

## 📊 Monitoramento

### 1. Setup Sentry (error tracking)

```bash
pip install sentry-sdk
```

```python
import sentry_sdk

sentry_sdk.init(
    dsn="seu_sentry_dsn",
    traces_sample_rate=1.0
)
```

### 2. Logs estruturados

```python
import json
import logging

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'message': record.getMessage(),
        }
        return json.dumps(log_data)

handler = logging.FileHandler('app.log')
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
```

### 3. Health check endpoint

```python
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    # Verifica database
    try:
        db.execute("SELECT 1")
        return {"status": "healthy", "database": "ok"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Serviço indisponível")
```

---

## 🚨 Troubleshooting

### Porta já em uso
```bash
# Linux/Mac
lsof -i :8000
kill -9 <PID>

# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Permission denied
```bash
chmod +x venv/bin/activate
sudo chown -R $USER:$USER .
```

### Database locked
```bash
rm repos.db
# Reinicia aplicação
```

### Rate limit GitHub
```bash
# Verifique limite atual
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/rate_limit
```

---

## 📈 Performance Tips

1. **Cache validações**: Redis para cache de 1 hora
2. **Async everything**: Certifique-se que todas as I/O são async
3. **Database indexes**: Adicione índices em searches frequentes
4. **Connection pooling**: Use pool de conexões
5. **CDN**: Sirva assets estáticos via CDN
6. **Compression**: Ative gzip em respostas

---

## 📞 Suporte

Para problemas ou dúvidas:
1. Verifique os logs: `tail -f app.log`
2. Rode testes: `pytest app/tests/ -v`
3. Consulte documentação FastAPI: https://fastapi.tiangolo.com
