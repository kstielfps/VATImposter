# Configuração do PostgreSQL

Este guia vai te ajudar a configurar o PostgreSQL para o projeto VAT Imposter.

## 📋 Pré-requisitos

- PostgreSQL instalado no seu sistema
- Acesso ao PostgreSQL (usuário e senha)

## 🔧 Passo a Passo

### 1. Instalar PostgreSQL (se ainda não tiver)

#### Windows:
- Baixe o instalador em: https://www.postgresql.org/download/windows/
- Durante a instalação, anote a senha do usuário `postgres` que você configurar

#### Linux (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

#### macOS:
```bash
brew install postgresql
brew services start postgresql
```

### 2. Verificar se o PostgreSQL está rodando

#### Windows:
- Abra o "Services" (Serviços) e procure por "postgresql"
- Ou abra o "pgAdmin" que vem com a instalação

#### Linux/macOS:
```bash
sudo systemctl status postgresql
# ou
pg_isready
```

### 3. Criar o banco de dados

#### Opção A: Via linha de comando (psql)

1. Abra o terminal/prompt de comando
2. Conecte ao PostgreSQL:

**Windows:**
```bash
psql -U postgres
```

**Linux/macOS:**
```bash
sudo -u postgres psql
```

3. Digite a senha quando solicitado
4. Crie o banco de dados:
```sql
CREATE DATABASE vatimposter;
```

5. (Opcional) Crie um usuário específico para o projeto:
```sql
CREATE USER vatimposter_user WITH PASSWORD 'sua_senha_aqui';
GRANT ALL PRIVILEGES ON DATABASE vatimposter TO vatimposter_user;
ALTER USER vatimposter_user CREATEDB;
```

6. Saia do psql:
```sql
\q
```

#### Opção B: Via pgAdmin (Windows)

1. Abra o pgAdmin
2. Conecte ao servidor PostgreSQL
3. Clique com botão direito em "Databases" → "Create" → "Database"
4. Nome: `vatimposter`
5. Clique em "Save"

### 4. Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto (mesmo diretório do `manage.py`):

**Windows (PowerShell):**
```powershell
# Criar arquivo .env
New-Item -Path .env -ItemType File

# Adicionar conteúdo (ajuste os valores conforme necessário)
@"
DB_NAME=vatimposter
DB_USER=postgres
DB_PASSWORD=sua_senha_postgres
DB_HOST=localhost
DB_PORT=5432
"@ | Out-File -FilePath .env -Encoding utf8
```

**Linux/macOS:**
```bash
cat > .env << EOF
DB_NAME=vatimposter
DB_USER=postgres
DB_PASSWORD=sua_senha_postgres
DB_HOST=localhost
DB_PORT=5432
EOF
```

**Ou edite manualmente** criando um arquivo `.env` com:
```
DB_NAME=vatimposter
DB_USER=postgres
DB_PASSWORD=sua_senha_postgres
DB_HOST=localhost
DB_PORT=5432
```

### 5. Instalar python-dotenv (para ler o arquivo .env)

```bash
pip install python-dotenv
```

### 6. Atualizar settings.py para ler o arquivo .env

O settings.py já está configurado para ler variáveis de ambiente. Vamos apenas garantir que ele também leia o arquivo .env.

### 7. Testar a conexão

Execute as migrações para testar se a conexão está funcionando:

```bash
python manage.py migrate
```

Se tudo estiver correto, você verá mensagens de migração sendo aplicadas.

## 🔍 Troubleshooting

### Erro: "FATAL: password authentication failed"

**Solução:**
- Verifique se a senha no arquivo `.env` está correta
- Se esqueceu a senha do PostgreSQL, você pode redefini-la:
  - Windows: Use o pgAdmin para alterar a senha
  - Linux: `sudo -u postgres psql` → `ALTER USER postgres PASSWORD 'nova_senha';`

### Erro: "could not connect to server"

**Solução:**
- Verifique se o PostgreSQL está rodando
- Verifique se o `DB_HOST` está correto (deve ser `localhost` ou `127.0.0.1`)
- Verifique se a porta está correta (padrão é `5432`)

### Erro: "database does not exist"

**Solução:**
- Certifique-se de que criou o banco de dados `vatimposter`
- Verifique se o nome do banco no `.env` está correto

### Erro: "permission denied"

**Solução:**
- Certifique-se de que o usuário tem permissões no banco de dados
- Execute: `GRANT ALL PRIVILEGES ON DATABASE vatimposter TO seu_usuario;`

## 📝 Notas Importantes

- **Nunca commite o arquivo `.env`** no Git (já está no .gitignore)
- Mantenha suas credenciais seguras
- Em produção, use variáveis de ambiente do sistema ou um gerenciador de secrets

## ✅ Verificação Final

Para verificar se tudo está funcionando:

```bash
# Testar conexão
python manage.py dbshell

# Se conectar, você verá o prompt do PostgreSQL
# Digite \q para sair

# Executar migrações
python manage.py migrate

# Criar superusuário (opcional)
python manage.py createsuperuser
```

Se todos os comandos funcionarem sem erros, o PostgreSQL está configurado corretamente! 🎉



