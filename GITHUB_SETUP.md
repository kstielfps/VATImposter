# Como enviar para o GitHub

## Passo 1: Criar repositório no GitHub

1. Acesse https://github.com e faça login (ou crie uma conta se não tiver)

2. Clique no botão **"+"** no canto superior direito e selecione **"New repository"**

3. Preencha os dados:
   - **Repository name**: `VATImposter` (ou outro nome de sua preferência)
   - **Description**: "Jogo multiplayer VAT Imposter desenvolvido com Django e PostgreSQL"
   - **Visibility**: Escolha **Public** (público) ou **Private** (privado)
   - **NÃO marque** "Initialize this repository with a README" (já temos um)
   - **NÃO adicione** .gitignore ou license (já temos)

4. Clique em **"Create repository"**

## Passo 2: Conectar e enviar código

Após criar o repositório, o GitHub mostrará instruções. Execute estes comandos no terminal:

```bash
# Adicionar o repositório remoto (substitua SEU_USUARIO pelo seu username do GitHub)
git remote add origin https://github.com/SEU_USUARIO/VATImposter.git

# Renomear branch para main (se necessário)
git branch -M main

# Enviar código para o GitHub
git push -u origin main
```

**Nota**: Se você escolheu um nome diferente para o repositório, substitua `VATImposter` pelo nome que você usou.

## Passo 3: Autenticação

Se for solicitado login:
- **Username**: Seu username do GitHub
- **Password**: Use um **Personal Access Token** (não sua senha normal)

### Como criar Personal Access Token:

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Clique em "Generate new token (classic)"
3. Dê um nome (ex: "VATImposter")
4. Selecione escopo: **repo** (marcar tudo em repo)
5. Clique em "Generate token"
6. **Copie o token** (você só verá uma vez!)
7. Use esse token como senha quando o Git pedir

## Comandos rápidos (copie e cole):

```bash
# Substitua SEU_USUARIO pelo seu username
git remote add origin https://github.com/SEU_USUARIO/VATImposter.git
git branch -M main
git push -u origin main
```

## Pronto! 🎉

Seu código estará no GitHub! Você pode acessar em:
`https://github.com/SEU_USUARIO/VATImposter`

## Comandos úteis para o futuro:

```bash
# Ver status das mudanças
git status

# Adicionar arquivos modificados
git add .

# Fazer commit
git commit -m "Descrição das mudanças"

# Enviar para GitHub
git push
```

