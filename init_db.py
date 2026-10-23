# -*- coding: utf-8 -*-
"""
Script de Inicialização do Banco de Dados
Cria tabelas, plano de contas, impostos, centros de custo e dados de demonstração
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()  # Carrega DATABASE_URL do Supabase do arquivo .env

from datetime import datetime, timedelta
from app import create_app
from models import db, Produto, Fornecedor, Cliente, Armazem, EnderecoArmazenagem
from services import SAPService

def init_database():
    app = create_app()
    with app.app_context():
        # Cria todas as tabelas
        db.create_all()
        print("Tabelas criadas com sucesso!")

        # Inicializa plano de contas, impostos e centros de custo (SAP)
        from models import PlanoConta
        if PlanoConta.query.count() == 0:
            SAPService.inicializar_plano_contas()
            print("Plano de contas, impostos e centros de custo inicializados!")

        # Dados de demonstração
        if Produto.query.count() == 0:
            # Produtos
            produtos = [
                {'codigo_sku': 'PRD-001', 'nome': 'Cadeira de Escritório Ergonômica', 'categoria': 'Móveis', 'preco_custo': 250.00, 'preco_venda': 499.90, 'estoque_minimo': 10, 'estoque_maximo': 100, 'estoque_atual': 50, 'unidade_medida': 'UN', 'ncm': '9401.31.00'},
                {'codigo_sku': 'PRD-002', 'nome': 'Mesa de Escritório 1,5m', 'categoria': 'Móveis', 'preco_custo': 400.00, 'preco_venda': 799.90, 'estoque_minimo': 5, 'estoque_maximo': 50, 'estoque_atual': 25, 'unidade_medida': 'UN', 'ncm': '9403.30.00'},
                {'codigo_sku': 'PRD-003', 'nome': 'Notebook Dell i7 16GB', 'categoria': 'Informática', 'preco_custo': 3500.00, 'preco_venda': 5499.00, 'estoque_minimo': 3, 'estoque_maximo': 20, 'estoque_atual': 8, 'unidade_medida': 'UN', 'ncm': '8471.30.12'},
                {'codigo_sku': 'PRD-004', 'nome': 'Monitor LG 27" 4K', 'categoria': 'Informática', 'preco_custo': 1200.00, 'preco_venda': 1899.00, 'estoque_minimo': 5, 'estoque_maximo': 30, 'estoque_atual': 15, 'unidade_medida': 'UN', 'ncm': '8528.52.00'},
                {'codigo_sku': 'PRD-005', 'nome': 'Teclado Mecânico RGB', 'categoria': 'Periféricos', 'preco_custo': 150.00, 'preco_venda': 299.90, 'estoque_minimo': 20, 'estoque_maximo': 200, 'estoque_atual': 80, 'unidade_medida': 'UN', 'ncm': '8471.60.40'},
                {'codigo_sku': 'MP-001', 'nome': 'Madeira MDF 15mm', 'categoria': 'Matéria-Prima', 'preco_custo': 80.00, 'preco_venda': 120.00, 'estoque_minimo': 30, 'estoque_maximo': 200, 'estoque_atual': 100, 'unidade_medida': 'CHAPA', 'ncm': '4411.12.10'},
                {'codigo_sku': 'MP-002', 'nome': 'Parafuso 5mm (100un)', 'categoria': 'Matéria-Prima', 'preco_custo': 15.00, 'preco_venda': 25.00, 'estoque_minimo': 50, 'estoque_maximo': 500, 'estoque_atual': 200, 'unidade_medida': 'CX', 'ncm': '7318.15.00'},
            ]
            for p in produtos:
                from services import ERPService
                ERPService.criar_produto(p)
            print(f"{len(produtos)} produtos cadastrados!")

        if Fornecedor.query.count() == 0:
            fornecedores = [
                {'cnpj': '12.345.678/0001-90', 'razao_social': 'Moveis Silva Ltda', 'nome_fantasia': 'Silva Móveis', 'email': 'contato@silvamoveis.com.br', 'telefone': '(11) 3333-4444', 'contato': 'José Silva', 'cidade': 'São Paulo', 'estado': 'SP', 'status_aprovacao': 'APROVADO', 'limite_credito': 50000.00, 'condicao_pagamento': '30 dias'},
                {'cnpj': '98.765.432/0001-10', 'razao_social': 'Tech Importações SA', 'nome_fantasia': 'Tech Import', 'email': 'vendas@techimport.com.br', 'telefone': '(11) 4444-5555', 'contato': 'Maria Tech', 'cidade': 'Curitiba', 'estado': 'PR', 'status_aprovacao': 'APROVADO', 'limite_credito': 100000.00, 'condicao_pagamento': '28/56 dias'},
                {'cnpj': '11.222.333/0001-44', 'razao_social': 'Madeiraria Central Ltda', 'nome_fantasia': 'Madeira Central', 'email': 'compras@madeiracentral.com.br', 'telefone': '(41) 3222-1111', 'contato': 'Carlos Madeira', 'cidade': 'Curitiba', 'estado': 'PR', 'status_aprovacao': 'APROVADO', 'limite_credito': 30000.00, 'condicao_pagamento': '30/60 dias'},
            ]
            for f in fornecedores:
                forn = Fornecedor(**f)
                db.session.add(forn)
            db.session.commit()
            print(f"{len(fornecedores)} fornecedores cadastrados!")

        if Cliente.query.count() == 0:
            clientes = [
                {'tipo': 'PJ', 'cpf_cnpj': '55.666.777/0001-88', 'nome': 'Empresa ABC Comércio', 'razao_social': 'ABC Comércio Ltda', 'email': 'financeiro@abc.com.br', 'telefone': '(41) 3000-1000', 'cidade': 'Curitiba', 'estado': 'PR', 'segmento': 'Varejo', 'limite_credito': 20000.00, 'score': 85, 'status': 'ATIVO', 'origem': 'INDICACAO'},
                {'tipo': 'PJ', 'cpf_cnpj': '66.777.888/0001-99', 'nome': 'Escritório XYZ Advocacia', 'razao_social': 'XYZ Advocacia Associada', 'email': 'adm@xyzadv.com.br', 'telefone': '(41) 3000-2000', 'cidade': 'Curitiba', 'estado': 'PR', 'segmento': 'Serviços', 'limite_credito': 15000.00, 'score': 70, 'status': 'ATIVO', 'origem': 'SITE'},
                {'tipo': 'PF', 'cpf_cnpj': '123.456.789-00', 'nome': 'João da Silva', 'email': 'joao.silva@email.com', 'telefone': '(41) 99999-1111', 'cidade': 'Curitiba', 'estado': 'PR', 'segmento': 'Consumidor Final', 'limite_credito': 5000.00, 'score': 60, 'status': 'ATIVO', 'origem': 'TELEMARKETING'},
            ]
            for c in clientes:
                cli = Cliente(**c)
                db.session.add(cli)
            db.session.commit()
            print(f"{len(clientes)} clientes cadastrados!")

        if Armazem.query.count() == 0:
            arm = Armazem(codigo='ARM-01', nome='Armazém Central Curitiba', endereco='Av. das Indústrias, 1000 - Curitiba/PR', capacidade_total=10000, tipo='GERAL')
            db.session.add(arm)
            db.session.flush()
            # Endereços
            for rua in ['A', 'B', 'C']:
                for modulo in range(1, 4):
                    for nivel in range(1, 4):
                        for pos in range(1, 3):
                            cod = f"{rua}-{modulo:02d}-{nivel}-{pos:02d}"
                            end = EnderecoArmazenagem(
                                armazem_id=arm.id,
                                codigo=cod,
                                rua=rua,
                                modulo=str(modulo),
                                nivel=str(nivel),
                                posicao=str(pos),
                                capacidade=100,
                                status='DISPONIVEL'
                            )
                            db.session.add(end)
            db.session.commit()
            print("Armazém e endereços cadastrados!")

        print("\n=== BANCO DE DADOS INICIALIZADO COM SUCESSO ===")
        print("Acesse: http://localhost:5000")
        print("API Health: http://localhost:5000/health")
        print("Dashboard: http://localhost:5000/api/integracao/dashboard")

if __name__ == '__main__':
    init_database()
