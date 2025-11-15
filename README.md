# VAT Imposter 🎮

Um jogo multiplayer online inspirado no conceito de "Among Us" com palavras, desenvolvido em Django e PostgreSQL.

## 📋 Descrição

VAT Imposter é um jogo onde os jogadores recebem palavras e precisam descobrir quem é o impostor através de dicas. O jogo suporta:
- **Cidadãos**: Recebem a palavra correta e tentam descobrir o impostor
- **Impostor(es)**: Recebem uma palavra diferente e tentam não ser descobertos
- **WhiteMan**: Não recebe palavra nenhuma e tenta sobreviver

## 🚀 Instalação

### Pré-requisitos

- Python 3.8+
- PostgreSQL

### Passos

1. Clone o repositório:
```bash
git clone <seu-repositorio>
cd VATImposter
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure o banco de dados PostgreSQL:
   - Crie um banco de dados chamado `vatimposter` (ou configure as variáveis de ambiente)
   - Configure as variáveis de ambiente (opcional):
     - `DB_NAME`: Nome do banco (padrão: vatimposter)
     - `DB_USER`: Usuário do banco (padrão: postgres)
     - `DB_PASSWORD`: Senha do banco (padrão: postgres)
     - `DB_HOST`: Host do banco (padrão: localhost)
     - `DB_PORT`: Porta do banco (padrão: 5432)

5. Execute as migrações:
```bash
python manage.py migrate
```

6. Crie um superusuário (opcional, para acessar o admin):
```bash
python manage.py createsuperuser
```

7. Execute o servidor:
```bash
python manage.py runserver
```

## 🎯 Como Jogar

### Criar uma Sala

1. Acesse a página inicial
2. Clique em "Criar Sala"
3. Digite seu nome
4. Configure o número de impostores (1-2) e whitemen (0-2)
5. Clique em "Criar Sala"
6. Compartilhe o código gerado com seus amigos

### Entrar em uma Sala

1. Acesse a página inicial
2. Clique em "Entrar com Código"
3. Digite o código da sala e seu nome
4. Clique em "Entrar na Sala"

### Iniciar o Jogo

- O criador da sala pode iniciar o jogo quando houver pelo menos 4 jogadores
- Máximo de 8 jogadores por sala

### Durante o Jogo

1. **Rodadas de Dicas** (3 rodadas iniciais):
   - Cada jogador tem 30 segundos para dar uma dica (uma palavra)
   - A ordem é aleatória a cada rodada
   - Todos veem as dicas dadas

2. **Votação**:
   - Após as 3 rodadas de dicas, todos votam simultaneamente
   - Escolha quem você acha que é o impostor
   - O jogador mais votado é eliminado

3. **Continuação**:
   - Se o jogo não terminar, continua com mais rodadas de dicas (1 palavra) + votação
   - O jogo termina quando:
     - Todos os impostores são eliminados (Cidadãos ganham)
     - Sobram apenas 2 jogadores (Impostores ganham)

## 🗄️ Configurando Palavras

Para adicionar palavras ao jogo, você precisa criar grupos de palavras similares:

1. Acesse o admin: `http://localhost:8000/admin`
2. Vá em "Grupos de Palavras" e crie um novo grupo
3. Adicione palavras ao grupo (mínimo 2 palavras por grupo)

Exemplo:
- Grupo 1: Água, Molhado, Chuva, Rio
- Grupo 2: Torre, Prédio, Alto

O jogo escolherá aleatoriamente um grupo e distribuirá:
- Uma palavra para os Cidadãos
- Uma palavra diferente (do mesmo grupo) para os Impostores

## 🛠️ Tecnologias Utilizadas

- **Django 4.2**: Framework web
- **PostgreSQL**: Banco de dados
- **Django Channels**: WebSockets para tempo real (InMemoryChannelLayer)

## 📁 Estrutura do Projeto

```
VATImposter/
├── vatimposter/          # Configurações do projeto
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── game/                 # App principal
│   ├── models.py         # Models (Game, Player, Word, etc.)
│   ├── views.py          # Views HTTP
│   ├── consumers.py      # WebSocket consumers
│   ├── urls.py
│   └── admin.py
├── templates/            # Templates HTML
│   ├── base.html
│   └── game/
│       ├── home.html
│       ├── create.html
│       ├── join.html
│       └── room.html
├── requirements.txt
└── README.md
```

## 🔧 Configuração de Produção

Para produção, você deve:

1. Usar um servidor ASGI como Daphne
2. Configurar variáveis de ambiente para segurança
3. Configurar `DEBUG = False` no settings.py
4. Configurar `ALLOWED_HOSTS` adequadamente
5. Usar um servidor web como Nginx como proxy reverso

**Nota**: Este projeto usa InMemoryChannelLayer, então funciona apenas com um servidor. Para múltiplos servidores, seria necessário configurar Redis.

## 📝 Notas

- O jogo usa WebSockets para atualizações em tempo real
- Usa InMemoryChannelLayer (servidor único)
- Jogadores eliminados podem continuar assistindo o jogo
- O jogo suporta múltiplas salas simultâneas

## 🐛 Problemas Conhecidos

- O projeto usa InMemoryChannelLayer, então funciona apenas com um servidor. Para escalar para múltiplos servidores, seria necessário configurar Redis.

## 📄 Licença

Este projeto é de código aberto e está disponível para uso livre.

