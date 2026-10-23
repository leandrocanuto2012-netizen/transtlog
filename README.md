# Sistema Integrado de Gestão

Sistema completo multi-módulo com **ERP, WMS, CRM, VOM, PDA e SAP (Contábil/Fiscal)**, totalmente integrado, com **banco de dados Supabase (PostgreSQL na nuvem)**, APIs REST e interface web.

> 📖 **Guia completo de configuração do Supabase**: veja o arquivo [`GUIA_SUPABASE.md`](GUIA_SUPABASE.md)

## Banco de Dados: Supabase (PostgreSQL)

O sistema pode usar **SQLite local** para testes ou **PostgreSQL do Supabase** para persistência na nuvem. Para configurar o Supabase:

1. Crie um projeto grátis em [supabase.com](https://supabase.com)
2. Copie `.env.example` para `.env` e cole sua **Connection String** (URI) do Supabase no campo `DATABASE_URL`
3. Rode `python init_db.py` — cria todas as tabelas automaticamente no Supabase
4. Rode `python app.py` — todos os dados ficam salvos na nuvem

*Fallback automático*: se a `DATABASE_URL` não estiver configurada, o sistema usa SQLite local (`instance/sistema_gestao.db`) — ideal para testes offline.

## Módulos e Regras de Negócio Implementadas

### 🏢 ERP - Enterprise Resource Planning
- Cadastro de produtos com SKU único e cálculo automático de margem de lucro
- Fornecedores com controle de aprovação e limite de crédito
- Ordens de compra com validação de fornecedor aprovado e limite de crédito
- Notas fiscais de entrada com impostos (ICMS, IPI)
- Contas a pagar e receber com status (PENDENTE, PAGO, ATRASADO)
- Movimentação de estoque (ENTRADA, SAIDA, AJUSTE, TRANSFERENCIA) com saldo anterior/atual
- Alerta de estoque mínimo automático
- Fluxo de caixa previsto (30 dias)

### 📦 WMS - Warehouse Management System
- Múltiplos armazéns com endereçamento (rua-módulo-nível-posição)
- Controle de capacidade e ocupação por endereço
- Ordens de separação com prioridade por score do cliente
- **FEFO** (First Expired, First Out) na separação por lote/validade
- Recebimento de mercadoria com conferência, avarias e **putaway** automático
- Inventário geral/cíclico com ajuste automático de estoque por diferença
- Relatório de ocupação por armazém

### 👥 CRM - Customer Relationship Management
- Clientes PF/PJ com score automático (histórico, inadimplência, valor)
- Contatos por cliente
- Funil de vendas com estágios e probabilidade automática
- Atividades (ligação, email, reunião, visita)
- Pedidos de venda com validação de estoque, limite de crédito e inadimplência
- Faturamento integra com ERP (baixa estoque) e SAP (contabiliza receita/CMV)
- Campanhas de marketing

### 🤝 VOM - Vendor On-Boarding Management
- Solicitação de cadastro de fornecedor com 5 etapas
- Checklist automático gerado por etapa
- Documentos obrigatórios (CNPJ, Contrato Social, FGTS, Joint, Endereço, Bancários)
- Avanço de etapa apenas com todos itens concluídos
- Aprovação só com documentos completos → **integra automática no ERP e SAP**
- Avaliação de fornecedores por critério ponderado (qualidade, prazo, preço...)

### 🏭 PDA - Production Data Analysis
- Ordens de produção com planejamento
- Registro de produção por turno/máquina/operador
- **Cálculo automático de OEE** (Disponibilidade × Performance × Qualidade)
- Baixa automática de matéria-prima e entrada de produto acabado no estoque ERP
- Controle de refugo e taxa de qualidade
- Manutenção de máquinas (preventiva/corretiva/preditiva)
- Dashboard de produção consolidado

### 💰 SAP - Sistema Contábil & Fiscal
- Plano de contas padrão brasileiro (CPC) com contas sintéticas/analíticas
- **Método das partidas dobradas** (valida Débito = Crédito antes de contabilizar)
- Centros de custo
- Impostos (ICMS, PIS, COFINS, IPI, ISS, IRPJ, CSLL) com alíquotas
- Apuração automática de imposto por competência
- Balancete e **DRE** (Receitas - Custos - Despesas = Lucro)
- Contabilização automática de compras e vendas integrada

### 🔄 Integração entre Módulos
- Toda operação gera log de integração rastreável
- CRM → ERP (baixa estoque, conta a receber)
- CRM → SAP (contabiliza venda + CMV)
- ERP → WMS (ordem de separação, recebimento)
- ERP → SAP (conta a pagar, entrada mercadoria)
- VOM → ERP/SAP (cadastro fornecedor aprovado)
- PDA → ERP (entrada produto acabado, baixa MP)

## Instalação e Execução

```bash
# 1. Instalar dependências (inclui psycopg2 para PostgreSQL/Supabase)
pip install -r requirements.txt

# 2. Banco local: não é necessário criar .env; usa SQLite automaticamente.
#    Para Supabase, copie .env.example para .env e configure DATABASE_URL com
#    a URL real do seu projeto (nunca use valores de exemplo).

# 3. Criar tabelas e dados de demonstração
python init_db.py

# 4. Iniciar a aplicação
python app.py
```

Acesse: **http://localhost:5000**
Verifique o banco em uso: **http://localhost:5000/health** (mostra "Supabase (PostgreSQL)" ou "SQLite (local)")

## Deploy no Render (hospedagem na nuvem)

O projeto já está 100% pronto para deploy no **Render** com deploy automático via GitHub.

- 📖 Guia completo: [`GUIA_DEPLOY_RENDER.md`](GUIA_DEPLOY_RENDER.md)
- Arquivos incluídos:
  - `render.yaml` — Blueprint de infraestrutura: cria Web Service + PostgreSQL automaticamente
  - `Dockerfile` — alternativa de deploy via container
  - `gunicorn` já no `requirements.txt` como servidor WSGI de produção
  - `app.py` já lê a variável `PORT` que o Render injeta

**Deploy em 3 passos**: suba no GitHub → no Render clique em *New + > Blueprint* → selecione o repositório. Pronto, tudo é criado automático (serviço + banco + tabelas + dados demo).

## Principais Endpoints da API

| Módulo | Endpoint | Método | Descrição |
|--------|----------|--------|-----------|
| Geral | `/api/integracao/dashboard` | GET | Dashboard consolidado |
| Geral | `/api/integracao/logs` | GET | Logs de integração |
| ERP | `/api/erp/produtos` | GET/POST | Produtos |
| ERP | `/api/erp/ordens-compra` | GET/POST | Ordens de compra |
| ERP | `/api/erp/fluxo-caixa` | GET | Fluxo de caixa |
| WMS | `/api/wms/ordens-separacao` | GET/POST | Ordens de separação |
| WMS | `/api/wms/relatorios/ocupacao` | GET | Ocupação armazém |
| CRM | `/api/crm/clientes` | GET/POST | Clientes |
| CRM | `/api/crm/pedidos-venda` | GET/POST | Pedidos de venda |
| CRM | `/api/crm/funil-vendas` | GET | Funil de vendas |
| VOM | `/api/vom/solicitacoes` | GET/POST | Onboarding fornecedores |
| VOM | `/api/vom/solicitacoes/{id}/aprovar` | POST | Aprovar e integrar |
| PDA | `/api/pda/ordens-producao` | GET/POST | Ordens de produção |
| PDA | `/api/pda/registros-producao` | POST | Registrar produção (calcula OEE) |
| PDA | `/api/pda/dashboard` | GET | Dashboard produção |
| SAP | `/api/sap/lancamentos` | GET/POST | Lançamentos contábeis |
| SAP | `/api/sap/apuracoes` | GET/POST | Apuração de impostos |
| SAP | `/api/sap/dre/{competencia}` | GET | Demonstrativo de resultado |

## Estrutura do Projeto

```
sistema_gestao/
├── app.py              # Aplicação Flask (lê PORT e DATABASE_URL do ambiente)
├── models.py           # 41 modelos de dados (SQLAlchemy - compatível com PostgreSQL)
├── services.py         # Regras de negócio de cada módulo
├── routes.py           # APIs REST (70+ endpoints)
├── init_db.py          # Inicialização + dados demo (roda no build do Render)
├── requirements.txt    # Dependências (psycopg2, gunicorn, flask...)
├── .env.example        # Template de configuração do Supabase (copie para .env)
├── .gitignore          # Protege o .env com senhas
├── render.yaml         # Blueprint Render: cria Web Service + PostgreSQL automático
├── Dockerfile          # Deploy via container (alternativa)
├── .dockerignore
├── GUIA_SUPABASE.md    # Guia: configurar banco Supabase
├── GUIA_DEPLOY_RENDER.md # Guia: deploy passo a passo no Render
├── README.md
├── static/
│   └── index.html      # Interface web completa (dashboard)
└── instance/           # (apenas fallback SQLite local)
```
