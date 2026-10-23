# Guia: Configurando o Banco Supabase

Este sistema usa **PostgreSQL do Supabase** como banco de dados na nuvem. Siga os passos abaixo.

## Passo 1: Criar projeto no Supabase

1. Acesse [supabase.com](https://supabase.com) e faça login (ou crie conta gratuita)
2. Clique em **"New Project"**
3. Preencha:
   - **Name**: `sistema-gestao` (ou o nome que quiser)
   - **Database Password**: defina uma senha forte (anote-a — você vai precisar)
   - **Region**: escolha a mais próxima (ex: `Southeast Brazil (São Paulo)` se disponível, ou `South America`)
4. Clique em **Create new project** e aguarde ~2 minutos até provisionar

## Passo 2: Pegar a Connection String

1. No menu lateral esquerdo, clique no ícone de **engrenagem (Project Settings)**
2. Clique em **Database**
3. Role até **Connection string** > aba **URI**
4. Copie a string. Ela tem este formato:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.abcdefghijklmnopqrst.supabase.co:5432/postgres
   ```
5. Substitua `[YOUR-PASSWORD]` pela senha que você definiu no Passo 1

## Passo 3: Configurar o .env

1. Copie o arquivo `.env.example` para `.env`:
   ```bash
   cp .env.example .env
   ```
2. Edite o `.env` e cole sua connection string completa (com senha) em `DATABASE_URL`

## Passo 4: Liberar acesso (se necessário)

Por padrão o Supabase permite conexões de qualquer IP. Se tiver erro de conexão:
- Project Settings > Database > **IP Allowlist** > adicione `0.0.0.0/0` (ou seu IP)

## Passo 5: Criar tabelas e dados iniciais

```bash
pip install -r requirements.txt
python init_db.py
```

O `init_db.py` vai:
- Conectar no Supabase
- Criar **todas as tabelas** (30+ tabelas dos 6 módulos) automaticamente via SQLAlchemy
- Carregar plano de contas, impostos, centros de custo
- Inserir dados de demonstração (produtos, fornecedores, clientes, armazém)

## Passo 6: Rodar o sistema

```bash
python app.py
```

Acesse http://localhost:5000 — todos os dados agora ficam salvos no Supabase (nuvem).

## Verificando no painel do Supabase

Para confirmar que deu certo:
1. Menu lateral > **Table Editor**
2. Você verá todas as tabelas criadas: `erp_produtos`, `crm_clientes`, `wms_armazens`, `sap_lancamentos`, etc.
3. Os dados de demonstração já estarão lá

## Observações importantes

- **Não comite o arquivo `.env`** no GitHub — ele contém sua senha. Ele já deve estar no `.gitignore`.
- O sistema tem **fallback automático**: se a `DATABASE_URL` não estiver definida, ele usa SQLite local (`instance/sistema_gestao.db`).
- O `pool_pre_ping=True` está ativado para evitar conexões quebradas (comum em bancos na nuvem).
- Se quiser recomeçar do zero: no Supabase, vá em **SQL Editor** e execute `DROP SCHEMA public CASCADE; CREATE SCHEMA public;` depois rode `python init_db.py` novamente.
