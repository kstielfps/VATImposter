# Deploy no Railway

Este guia vai te ajudar a fazer deploy do VAT Imposter no Railway.

## Pré-requisitos

- Conta no Railway (https://railway.app)
- Conta no GitHub (já temos o código lá)

## Passo a Passo

### 1. Criar projeto no Railway

1. Acesse https://railway.app e faça login
2. Clique em **"New Project"**
3. Selecione **"Deploy from GitHub repo"**
4. Escolha o repositório `kstielfps/VATImposter`
5. Railway vai detectar automaticamente que é um projeto Django

### 2. Configurar Banco de Dados PostgreSQL

1. No dashboard do Railway, clique em **"New"** → **"Database"** → **"Add PostgreSQL"**
2. Railway criará automaticamente um banco PostgreSQL
3. Anote as variáveis de ambiente que serão criadas:
   - `PGHOST`
   - `PGPORT`
   - `PGDATABASE`
   - `PGUSER`
   - `PGPASSWORD`

### 3. Configurar Variáveis de Ambiente

**IMPORTANTE**: O código agora usa automaticamente as variáveis do Railway PostgreSQL (`PGDATABASE`, `PGUSER`, etc.), então você NÃO precisa configurar variáveis de banco de dados manualmente!

No seu serviço Django, vá em **"Variables"** e adicione apenas:

**Variáveis Django** (obrigatórias):
```
SECRET_KEY=<gere uma chave secreta forte>
DEBUG=False
ALLOWED_HOSTS=*
```

**Variáveis do Banco de Dados**: NÃO são necessárias! O código detecta automaticamente as variáveis `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGHOST`, `PGPORT` que o Railway cria automaticamente quando você adiciona o serviço PostgreSQL.

**Para gerar SECRET_KEY**:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 4. Configurar Build e Deploy

Railway deve detectar automaticamente, mas verifique:

1. **Build Command**: Deve estar vazio (Railway detecta automaticamente)
2. **Start Command**: `daphne -b 0.0.0.0 -p $PORT vatimposter.asgi:application`

### 5. Executar Migrações

Após o primeiro deploy, você precisa executar as migrações:

1. No dashboard do Railway, vá no seu serviço Django
2. Clique em **"Deployments"** → **"View Logs"**
3. Clique em **"Shell"** ou **"Run Command"**
4. Execute:
```bash
python manage.py migrate
python manage.py populate_words
python manage.py createadmin --username admin --email admin@example.com --password <sua_senha>
```

### 6. Configurar Domínio (Opcional)

1. No dashboard, vá em **"Settings"** → **"Networking"**
2. Clique em **"Generate Domain"** para criar um domínio público
3. Adicione o domínio em `ALLOWED_HOSTS`:
```
ALLOWED_HOSTS=seu-app.railway.app,*.railway.app
```

## Estrutura de Arquivos para Railway

Os seguintes arquivos foram criados para Railway:

- `Procfile`: Define como iniciar o servidor
- `runtime.txt`: Especifica versão do Python
- `railway.json`: Configurações do Railway
- `railway.toml`: Configurações alternativas

## Variáveis de Ambiente no Railway

Railway permite usar referências entre serviços. Para conectar ao PostgreSQL:

```
DB_NAME=${{Postgres.PGDATABASE}}
DB_USER=${{Postgres.PGUSER}}
DB_PASSWORD=${{Postgres.PGPASSWORD}}
DB_HOST=${{Postgres.PGHOST}}
DB_PORT=${{Postgres.PGPORT}}
```

## Troubleshooting

### Erro: "No module named 'daphne'"
- Certifique-se de que `daphne` está no `requirements.txt` (já está)

### Erro: "Database connection failed"
- Verifique se as variáveis de ambiente do PostgreSQL estão configuradas
- Certifique-se de que o serviço PostgreSQL está rodando

### Erro: "Port already in use"
- Railway fornece a porta via variável `$PORT`, certifique-se de usar ela

### WebSocket não funciona
- Railway suporta WebSockets, mas certifique-se de usar HTTPS
- O domínio gerado pelo Railway já usa HTTPS

## Comandos Úteis

Para executar comandos Django no Railway:

1. Vá em **"Deployments"** → **"View Logs"**
2. Clique em **"Shell"**
3. Execute comandos como:
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py populate_words
```

## Notas Importantes

- **SECRET_KEY**: Sempre use uma chave secreta forte em produção
- **DEBUG**: Deixe como `False` em produção
- **ALLOWED_HOSTS**: Adicione seu domínio Railway
- **Banco de Dados**: Railway cria automaticamente, mas você precisa mapear as variáveis
- **Static Files**: Railway serve automaticamente, mas você pode configurar se necessário

## Próximos Passos

Após o deploy:
1. Execute as migrações
2. Popule as palavras
3. Crie um superusuário
4. Teste o jogo online!

