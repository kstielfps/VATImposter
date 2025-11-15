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
3. **IMPORTANTE**: Conecte o serviço PostgreSQL ao serviço Django:
   - Clique no serviço Django (não no PostgreSQL)
   - Vá em **"Settings"** → **"Service Connections"**
   - Clique em **"Connect"** ao lado do serviço PostgreSQL
   - Isso disponibilizará automaticamente as variáveis de ambiente:
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
CSRF_TRUSTED_ORIGINS=https://seu-app.railway.app
```

**IMPORTANTE**: Substitua `seu-app.railway.app` pelo domínio real do seu app no Railway. Você pode encontrar o domínio em **"Settings"** → **"Networking"** → **"Public Domain"**.

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

**IMPORTANTE**: As migrações devem ser executadas automaticamente durante o deploy (configurado no `.nixpacks.toml` e `railway.json`). 

**Se as migrações não foram executadas automaticamente**, você pode executá-las manualmente:

1. No dashboard do Railway, vá no seu serviço Django
2. Clique em **"Deployments"** → clique no deployment mais recente
3. Clique em **"View Logs"** para ver os logs do deploy
4. Verifique se há mensagens de erro relacionados a migrações
5. Se necessário, clique em **"Shell"** ou **"Run Command"** e execute:
```bash
python manage.py migrate
python manage.py populate_words
python manage.py createadmin --username admin --email admin@example.com --password <sua_senha>
```

**Para verificar se as migrações foram aplicadas:**
- No serviço PostgreSQL, vá em **"Database"** → **"Data"**
- Você deve ver tabelas como `game_game`, `game_player`, `game_wordgroup`, etc.
- Se não houver tabelas, as migrações não foram executadas

**Para verificar logs de erro:**
- No serviço Django, vá em **"Deployments"** → **"View Logs"**
- Procure por mensagens de erro (em vermelho)
- Se houver erro 500 ao criar sala, os logs mostrarão o erro específico

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

