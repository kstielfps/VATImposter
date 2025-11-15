# Guia Rápido de Setup

## Instalação Rápida

1. **Instalar dependências:**
```bash
pip install -r requirements.txt
```

2. **Configurar banco de dados PostgreSQL:**
   - Crie um banco chamado `vatimposter`
   - Ou configure as variáveis de ambiente:
     ```bash
     export DB_NAME=vatimposter
     export DB_USER=postgres
     export DB_PASSWORD=sua_senha
     export DB_HOST=localhost
     export DB_PORT=5432
     ```

3. **Executar migrações:**
```bash
python manage.py migrate
```

4. **Popular palavras de exemplo (opcional):**
```bash
python manage.py populate_words
```

5. **Criar superusuário (opcional, para admin):**
```bash
python manage.py createsuperuser
```

6. **Rodar servidor:**
```bash
python manage.py runserver
```

7. **Acessar:**
   - Jogo: http://localhost:8000
   - Admin: http://localhost:8000/admin

## Adicionar Palavras

### Via Admin (Recomendado)

1. Acesse http://localhost:8000/admin
2. Faça login com o superusuário
3. Vá em "Grupos de Palavras"
4. Clique em "Adicionar Grupo de Palavras"
5. Digite um nome (opcional) e salve
6. Adicione palavras ao grupo (mínimo 2 palavras por grupo)

### Via Script

Edite o arquivo `game/management/commands/populate_words.py` e adicione seus grupos de palavras.

## Estrutura de Grupos de Palavras

Cada grupo deve ter pelo menos 2 palavras. O jogo escolherá:
- Uma palavra para os Cidadãos
- Uma palavra diferente (do mesmo grupo) para os Impostores

Exemplo:
- Grupo: "Frutas"
  - Abacaxi
  - Manga
  - Banana
  - Laranja

Neste caso, se o grupo for escolhido:
- Cidadãos podem receber "Abacaxi"
- Impostores podem receber "Manga"

## Notas Importantes

- **Servidor Único**: O projeto usa InMemoryChannelLayer e funciona apenas com um servidor
- **WebSockets**: O jogo usa WebSockets para atualizações em tempo real
- **Múltiplas Salas**: O jogo suporta múltiplas salas simultâneas
- **Jogadores Eliminados**: Podem continuar assistindo o jogo até o final

## Troubleshooting

### Erro de conexão com PostgreSQL
- Verifique se o PostgreSQL está rodando
- Verifique as credenciais no settings.py ou variáveis de ambiente

### WebSocket não conecta
- Certifique-se de usar `python manage.py runserver` (não WSGI)
- Verifique se o servidor está rodando corretamente

### Erro ao iniciar jogo
- Certifique-se de ter pelo menos um grupo de palavras com 2+ palavras no banco
- Execute `python manage.py populate_words` para criar exemplos

