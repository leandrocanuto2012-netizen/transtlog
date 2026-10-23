# Guia: Deploy no Render

Este projeto está pronto para deploy no **Render** (plataforma de hospedagem na nuvem). Há duas formas — escolha uma.

---

## Opção A — Blueprint (recomendada, mais fácil)

O arquivo `render.yaml` já está configurado e cria **tudo automaticamente**: serviço web + banco PostgreSQL.

### Passo a passo

1. **Suba o código no GitHub**
   - Crie um repositório no GitHub e faça upload de todos os arquivos desta pasta
   - (O arquivo `.env` NÃO deve ser enviado — o `.gitignore` já protege)

2. **Entre no Render**
   - Acesse [dashboard.render.com](https://dashboard.render.com) e faça login com sua conta GitHub

3. **Crie via Blueprint**
   - Clique em **"New +"** (canto superior direito) > **"Blueprint"**
   - Conecte/selecione o repositório do GitHub que você criou
   - O Render vai ler o `render.yaml` e mostrar o que será criado:
     - ✅ Web Service: `sistema-gestao` (Flask + Gunicorn)
     - ✅ PostgreSQL: `sistema-gestao-db` (banco de dados)
   - Clique em **"Apply"** e aguarde ~5 minutos

4. **Pronto!**
   - O Render vai: instalar dependências → rodar `init_db.py` (cria tabelas + dados demo no PostgreSQL) → iniciar o servidor
   - Acesse a URL que o Render gerar (ex: `https://sistema-gestao.onrender.com`)
   - Verifique em `https://sua-url.onrender.com/health` — deve aparecer `"banco": "Supabase (PostgreSQL)"` (na verdade será o PostgreSQL do Render, mas o formato é o mesmo)

---

## Opção B — Deploy manual (sem blueprint)

Se preferir configurar manualmente:

1. **New +** > **"Web Service"** > conecte seu repositório GitHub
2. Configure:
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt && python init_db.py`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Free (ou o que preferir)
3. **Adicione o banco**: **New +** > **"PostgreSQL"** > crie com plano Free
4. **Vincule o banco ao serviço**: no Web Service criado, vá em **Environment** > **"Add Environment Variable"** > **"Add from Database"** > selecione o PostgreSQL criado. Isso cria a variável `DATABASE_URL` automaticamente.
5. Clique em **"Manual Deploy"** > **"Deploy latest commit"**

---

## Opção C — Usar Docker

Se preferir container (mais consistente): o `Dockerfile` já está pronto.

1. **New +** > **"Web Service"** > conecte o repositório
2. Em **Runtime**, selecione **"Docker"**
3. O Render detecta o `Dockerfile` automaticamente
4. Adicione a variável `DATABASE_URL` (do Supabase ou do PostgreSQL do Render) em Environment
5. Deploy

---

## Usando Supabase ao invés do PostgreSQL do Render

Se quiser manter o **Supabase** como banco (em vez do PostgreSQL nativo do Render):

1. No `render.yaml`, **remova** a seção `databases:` completa
2. No Web Service, vá em **Environment** > adicione manualmente:
   - `DATABASE_URL` = sua connection string do Supabase (igual ao `.env`)
3. Redeploy

---

## Primeiro acesso após deploy

- URL do sistema: `https://NOME_DO_SEU_SERVICO.onrender.com`
- Já vem com dados de demonstração: 7 produtos, 3 fornecedores, 3 clientes, armazém com endereços, plano de contas, impostos
- Health check: `/health`
- Dashboard consolidado: `/api/integracao/dashboard`

## Observações importantes

- **Plano Free do Render**: o serviço "hiberna" após 15 minutos sem uso. O primeiro acesso depois de hibernar demora ~30 segundos para acordar. É normal.
- **Banco PostgreSQL Free do Render**: expira após 90 dias (é só recriar). O Supabase é gratuito permanente.
- **Deploy automático**: toda vez que você der `git push` no GitHub, o Render redeploya automaticamente (`autoDeploy: true` no blueprint).
- **Logs**: no Render, aba **Logs** do serviço — mostra o `init_db.py` rodando e o Gunicorn iniciando.
- **Variável PORT**: o Render injeta automaticamente — o `app.py` já lê `os.environ.get('PORT', 5000)`.
