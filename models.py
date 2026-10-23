# -*- coding: utf-8 -*-
"""
Models de Dados - Sistema Integrado de Gestão
Módulos: ERP, WMS, CRM, VOM, PDA, SAP
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# ============================================================
# MODELO BASE
# ============================================================
class BaseModel(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

# ============================================================
# ERP - Enterprise Resource Planning
# ============================================================
class Produto(BaseModel):
    __tablename__ = 'erp_produtos'
    codigo_sku = db.Column(db.String(50), unique=True, nullable=False, index=True)
    nome = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text)
    categoria = db.Column(db.String(100))
    unidade_medida = db.Column(db.String(20), default='UN')
    preco_custo = db.Column(db.Float, default=0.0)
    preco_venda = db.Column(db.Float, default=0.0)
    margem_lucro = db.Column(db.Float, default=0.0)
    estoque_minimo = db.Column(db.Integer, default=0)
    estoque_maximo = db.Column(db.Integer, default=0)
    estoque_atual = db.Column(db.Integer, default=0)
    localizacao = db.Column(db.String(50))
    ncm = db.Column(db.String(20))  # Nomenclatura Comum do Mercosul
    peso_bruto = db.Column(db.Float, default=0.0)
    peso_liquido = db.Column(db.Float, default=0.0)

class Fornecedor(BaseModel):
    __tablename__ = 'erp_fornecedores'
    cnpj = db.Column(db.String(20), unique=True, nullable=False, index=True)
    razao_social = db.Column(db.String(200), nullable=False)
    nome_fantasia = db.Column(db.String(200))
    email = db.Column(db.String(150))
    telefone = db.Column(db.String(30))
    contato = db.Column(db.String(100))
    endereco = db.Column(db.String(300))
    cidade = db.Column(db.String(100))
    estado = db.Column(db.String(2))
    cep = db.Column(db.String(10))
    condicao_pagamento = db.Column(db.String(50), default='30 dias')
    limite_credito = db.Column(db.Float, default=0.0)
    status_aprovacao = db.Column(db.String(20), default='PENDENTE')  # PENDENTE, APROVADO, REJEITADO

class OrdemCompra(BaseModel):
    __tablename__ = 'erp_ordens_compra'
    numero_oc = db.Column(db.String(30), unique=True, nullable=False, index=True)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('erp_fornecedores.id'), nullable=False)
    data_emissao = db.Column(db.DateTime, default=datetime.utcnow)
    data_entrega_prevista = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='ABERTA')  # ABERTA, APROVADA, RECEBIDA, CANCELADA
    valor_total = db.Column(db.Float, default=0.0)
    desconto = db.Column(db.Float, default=0.0)
    frete = db.Column(db.Float, default=0.0)
    observacoes = db.Column(db.Text)
    fornecedor = db.relationship('Fornecedor', backref='ordens_compra')

class ItemOrdemCompra(BaseModel):
    __tablename__ = 'erp_itens_oc'
    ordem_compra_id = db.Column(db.Integer, db.ForeignKey('erp_ordens_compra.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('erp_produtos.id'), nullable=False)
    quantidade = db.Column(db.Float, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=False)
    valor_total = db.Column(db.Float, default=0.0)
    produto = db.relationship('Produto')
    ordem_compra = db.relationship('OrdemCompra', backref='itens')

class NotaFiscalEntrada(BaseModel):
    __tablename__ = 'erp_nf_entrada'
    numero_nf = db.Column(db.String(30), unique=True, nullable=False, index=True)
    serie = db.Column(db.String(10))
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('erp_fornecedores.id'), nullable=False)
    ordem_compra_id = db.Column(db.Integer, db.ForeignKey('erp_ordens_compra.id'))
    data_emissao = db.Column(db.DateTime)
    data_recebimento = db.Column(db.DateTime, default=datetime.utcnow)
    valor_total = db.Column(db.Float, default=0.0)
    valor_icms = db.Column(db.Float, default=0.0)
    valor_ipi = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='RECEBIDA')

class ContaPagar(BaseModel):
    __tablename__ = 'erp_contas_pagar'
    descricao = db.Column(db.String(200), nullable=False)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('erp_fornecedores.id'))
    categoria = db.Column(db.String(100))
    valor_original = db.Column(db.Float, nullable=False)
    data_vencimento = db.Column(db.DateTime, nullable=False)
    data_pagamento = db.Column(db.DateTime)
    valor_pago = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='PENDENTE')  # PENDENTE, PAGO, ATRASADO, CANCELADO
    metodo_pagamento = db.Column(db.String(50))
    numero_documento = db.Column(db.String(50))

class ContaReceber(BaseModel):
    __tablename__ = 'erp_contas_receber'
    descricao = db.Column(db.String(200), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('crm_clientes.id'))
    categoria = db.Column(db.String(100))
    valor_original = db.Column(db.Float, nullable=False)
    data_vencimento = db.Column(db.DateTime, nullable=False)
    data_recebimento = db.Column(db.DateTime)
    valor_recebido = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='PENDENTE')
    metodo_recebimento = db.Column(db.String(50))
    numero_documento = db.Column(db.String(50))

class MovimentacaoEstoque(BaseModel):
    __tablename__ = 'erp_movimentacoes_estoque'
    produto_id = db.Column(db.Integer, db.ForeignKey('erp_produtos.id'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # ENTRADA, SAIDA, AJUSTE, TRANSFERENCIA
    quantidade = db.Column(db.Float, nullable=False)
    saldo_anterior = db.Column(db.Float)
    saldo_atual = db.Column(db.Float)
    origem = db.Column(db.String(100))  # OC, NF, VENDA, AJUSTE
    documento_ref = db.Column(db.String(50))
    usuario = db.Column(db.String(100))
    observacoes = db.Column(db.Text)
    produto = db.relationship('Produto', backref='movimentacoes')

# ============================================================
# WMS - Warehouse Management System
# ============================================================
class Armazem(BaseModel):
    __tablename__ = 'wms_armazens'
    codigo = db.Column(db.String(20), unique=True, nullable=False, index=True)
    nome = db.Column(db.String(150), nullable=False)
    endereco = db.Column(db.String(300))
    capacidade_total = db.Column(db.Float, default=0.0)
    capacidade_utilizada = db.Column(db.Float, default=0.0)
    tipo = db.Column(db.String(50), default='GERAL')  # GERAL, FRIO, QUIMICO, PERIGOSO

class EnderecoArmazenagem(BaseModel):
    __tablename__ = 'wms_enderecos'
    armazem_id = db.Column(db.Integer, db.ForeignKey('wms_armazens.id'), nullable=False)
    codigo = db.Column(db.String(30), unique=True, nullable=False, index=True)  # Ex: A-01-03-02
    rua = db.Column(db.String(10))
    modulo = db.Column(db.String(10))
    nivel = db.Column(db.String(10))
    posicao = db.Column(db.String(10))
    capacidade = db.Column(db.Float, default=0.0)
    ocupacao_atual = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='DISPONIVEL')  # DISPONIVEL, OCUPADO, BLOQUEADO, MANUTENCAO
    tipo_produto_permitido = db.Column(db.String(50))
    armazem = db.relationship('Armazem', backref='enderecos')

class EstoquePorEndereco(BaseModel):
    __tablename__ = 'wms_estoque_endereco'
    endereco_id = db.Column(db.Integer, db.ForeignKey('wms_enderecos.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('erp_produtos.id'), nullable=False)
    lote = db.Column(db.String(50))
    quantidade = db.Column(db.Float, default=0.0)
    data_validade = db.Column(db.DateTime)
    endereco = db.relationship('EnderecoArmazenagem', backref='estoques')
    produto = db.relationship('Produto')

class OrdemSeparacao(BaseModel):
    __tablename__ = 'wms_ordens_separacao'
    numero = db.Column(db.String(30), unique=True, nullable=False, index=True)
    pedido_venda_id = db.Column(db.Integer, db.ForeignKey('crm_pedidos_venda.id'))
    status = db.Column(db.String(20), default='PENDENTE')  # PENDENTE, EM_SEPARACAO, CONCLUIDA, CANCELADA
    usuario_separador = db.Column(db.String(100))
    data_inicio = db.Column(db.DateTime)
    data_conclusao = db.Column(db.DateTime)
    prioridade = db.Column(db.String(20), default='NORMAL')  # BAIXA, NORMAL, ALTA, URGENTE

class ItemSeparacao(BaseModel):
    __tablename__ = 'wms_itens_separacao'
    ordem_separacao_id = db.Column(db.Integer, db.ForeignKey('wms_ordens_separacao.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('erp_produtos.id'), nullable=False)
    quantidade_solicitada = db.Column(db.Float, nullable=False)
    quantidade_separada = db.Column(db.Float, default=0.0)
    endereco_origem_id = db.Column(db.Integer, db.ForeignKey('wms_enderecos.id'))
    lote = db.Column(db.String(50))
    status = db.Column(db.String(20), default='PENDENTE')
    ordem_separacao = db.relationship('OrdemSeparacao', backref='itens')
    produto = db.relationship('Produto')
    endereco_origem = db.relationship('EnderecoArmazenagem')

class RecebimentoMercadoria(BaseModel):
    __tablename__ = 'wms_recebimentos'
    numero = db.Column(db.String(30), unique=True, nullable=False, index=True)
    nota_fiscal_id = db.Column(db.Integer, db.ForeignKey('erp_nf_entrada.id'))
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('erp_fornecedores.id'))
    status = db.Column(db.String(20), default='AGUARDANDO')  # AGUARDANDO, EM_CONFERENCIA, CONFERIDO, ENDERECADO, FINALIZADO
    data_chegada = db.Column(db.DateTime)
    data_conferencia = db.Column(db.DateTime)
    usuario_recebedor = db.Column(db.String(100))
    observacoes = db.Column(db.Text)

class ItemRecebimento(BaseModel):
    __tablename__ = 'wms_itens_recebimento'
    recebimento_id = db.Column(db.Integer, db.ForeignKey('wms_recebimentos.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('erp_produtos.id'), nullable=False)
    quantidade_nota = db.Column(db.Float, nullable=False)
    quantidade_recebida = db.Column(db.Float, default=0.0)
    quantidade_avariada = db.Column(db.Float, default=0.0)
    lote = db.Column(db.String(50))
    data_validade = db.Column(db.DateTime)
    endereco_destino_id = db.Column(db.Integer, db.ForeignKey('wms_enderecos.id'))
    status = db.Column(db.String(20), default='PENDENTE')
    recebimento = db.relationship('RecebimentoMercadoria', backref='itens')
    produto = db.relationship('Produto')

class Inventario(BaseModel):
    __tablename__ = 'wms_inventarios'
    numero = db.Column(db.String(30), unique=True, nullable=False, index=True)
    armazem_id = db.Column(db.Integer, db.ForeignKey('wms_armazens.id'), nullable=False)
    tipo = db.Column(db.String(20), default='GERAL')  # GERAL, CICLICO, ROTATIVO
    status = db.Column(db.String(20), default='ABERTO')  # ABERTO, EM_CONTAGEM, FINALIZADO
    data_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    data_fim = db.Column(db.DateTime)
    usuario_contador = db.Column(db.String(100))
    armazem = db.relationship('Armazem', backref='inventarios')

class ItemInventario(BaseModel):
    __tablename__ = 'wms_itens_inventario'
    inventario_id = db.Column(db.Integer, db.ForeignKey('wms_inventarios.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('erp_produtos.id'), nullable=False)
    endereco_id = db.Column(db.Integer, db.ForeignKey('wms_enderecos.id'))
    quantidade_sistema = db.Column(db.Float)
    quantidade_contada = db.Column(db.Float)
    diferenca = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='PENDENTE')  # PENDENTE, CONTADO, AJUSTADO
    inventario = db.relationship('Inventario', backref='itens')
    produto = db.relationship('Produto')

# ============================================================
# CRM - Customer Relationship Management
# ============================================================
class Cliente(BaseModel):
    __tablename__ = 'crm_clientes'
    tipo = db.Column(db.String(10), default='PF')  # PF, PJ
    cpf_cnpj = db.Column(db.String(20), unique=True, nullable=False, index=True)
    nome = db.Column(db.String(200), nullable=False)
    razao_social = db.Column(db.String(200))
    email = db.Column(db.String(150))
    telefone = db.Column(db.String(30))
    celular = db.Column(db.String(30))
    endereco = db.Column(db.String(300))
    cidade = db.Column(db.String(100))
    estado = db.Column(db.String(2))
    cep = db.Column(db.String(10))
    segmento = db.Column(db.String(100))
    limite_credito = db.Column(db.Float, default=0.0)
    score = db.Column(db.Integer, default=50)  # 0-100
    status = db.Column(db.String(20), default='ATIVO')  # ATIVO, INATIVO, SUSPENSO
    origem = db.Column(db.String(50))  # SITE, INDICACAO, EVENTO, TELEMARKETING

class Contato(BaseModel):
    __tablename__ = 'crm_contatos'
    cliente_id = db.Column(db.Integer, db.ForeignKey('crm_clientes.id'), nullable=False)
    nome = db.Column(db.String(150), nullable=False)
    cargo = db.Column(db.String(100))
    email = db.Column(db.String(150))
    telefone = db.Column(db.String(30))
    celular = db.Column(db.String(30))
    departamento = db.Column(db.String(100))
    cliente = db.relationship('Cliente', backref='contatos')

class Oportunidade(BaseModel):
    __tablename__ = 'crm_oportunidades'
    cliente_id = db.Column(db.Integer, db.ForeignKey('crm_clientes.id'), nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text)
    valor_estimado = db.Column(db.Float, default=0.0)
    probabilidade = db.Column(db.Integer, default=50)  # %
    estagio = db.Column(db.String(30), default='PROSPECCAO')  # PROSPECCAO, QUALIFICACAO, PROPOSTA, NEGOCIACAO, FECHADA, PERDIDA
    data_prevista_fechamento = db.Column(db.DateTime)
    responsavel = db.Column(db.String(100))
    origem = db.Column(db.String(50))
    cliente = db.relationship('Cliente', backref='oportunidades')

class AtividadeCRM(BaseModel):
    __tablename__ = 'crm_atividades'
    cliente_id = db.Column(db.Integer, db.ForeignKey('crm_clientes.id'))
    oportunidade_id = db.Column(db.Integer, db.ForeignKey('crm_oportunidades.id'))
    tipo = db.Column(db.String(30), nullable=False)  # LIGACAO, EMAIL, REUNIAO, VISITA, TAREFA
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text)
    data_agendada = db.Column(db.DateTime)
    data_realizacao = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='PENDENTE')  # PENDENTE, CONCLUIDA, CANCELADA, ADIADA
    responsavel = db.Column(db.String(100))
    resultado = db.Column(db.Text)
    cliente = db.relationship('Cliente', backref='atividades')

class PedidoVenda(BaseModel):
    __tablename__ = 'crm_pedidos_venda'
    numero_pedido = db.Column(db.String(30), unique=True, nullable=False, index=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('crm_clientes.id'), nullable=False)
    data_pedido = db.Column(db.DateTime, default=datetime.utcnow)
    data_entrega_prevista = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='ORCAMENTO')  # ORCAMENTO, APROVADO, SEPARACAO, FATURADO, ENVIADO, ENTREGUE, CANCELADO
    valor_total = db.Column(db.Float, default=0.0)
    desconto = db.Column(db.Float, default=0.0)
    frete = db.Column(db.Float, default=0.0)
    condicao_pagamento = db.Column(db.String(50))
    vendedor = db.Column(db.String(100))
    observacoes = db.Column(db.Text)
    cliente = db.relationship('Cliente', backref='pedidos')

class ItemPedidoVenda(BaseModel):
    __tablename__ = 'crm_itens_pedido'
    pedido_id = db.Column(db.Integer, db.ForeignKey('crm_pedidos_venda.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('erp_produtos.id'), nullable=False)
    quantidade = db.Column(db.Float, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=False)
    desconto_item = db.Column(db.Float, default=0.0)
    valor_total = db.Column(db.Float, default=0.0)
    pedido = db.relationship('PedidoVenda', backref='itens')
    produto = db.relationship('Produto')

class Campanha(BaseModel):
    __tablename__ = 'crm_campanhas'
    nome = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(50))  # EMAIL_MARKETING, SMS, TELEMARKETING, EVENTO
    data_inicio = db.Column(db.DateTime)
    data_fim = db.Column(db.DateTime)
    orcamento = db.Column(db.Float, default=0.0)
    publico_alvo = db.Column(db.String(200))
    status = db.Column(db.String(20), default='PLANEJADA')  # PLANEJADA, ATIVA, PAUSADA, CONCLUIDA
    resultado = db.Column(db.Text)

# ============================================================
# VOM - Vendor On-Boarding Management
# ============================================================
class SolicitacaoFornecedor(BaseModel):
    __tablename__ = 'vom_solicitacoes'
    cnpj = db.Column(db.String(20), nullable=False, index=True)
    razao_social = db.Column(db.String(200), nullable=False)
    nome_fantasia = db.Column(db.String(200))
    email = db.Column(db.String(150))
    telefone = db.Column(db.String(30))
    contato = db.Column(db.String(100))
    categoria_produto = db.Column(db.String(100))
    status = db.Column(db.String(20), default='SOLICITADO')  # SOLICITADO, EM_ANALISE, DOCUMENTACAO, APROVADO, REJEITADO, CADASTRADO
    etapa_atual = db.Column(db.Integer, default=1)  # 1-5
    data_solicitacao = db.Column(db.DateTime, default=datetime.utcnow)
    responsavel = db.Column(db.String(100))
    observacoes = db.Column(db.Text)

class DocumentoFornecedor(BaseModel):
    __tablename__ = 'vom_documentos'
    solicitacao_id = db.Column(db.Integer, db.ForeignKey('vom_solicitacoes.id'), nullable=False)
    tipo_documento = db.Column(db.String(50), nullable=False)  # CNPJ, CONTRATO_SOCIAL, CERTIDAO_FGTS, CERTIDAO_JOINT, COMPROVANTE_ENDERECO, BANCARIO
    nome_arquivo = db.Column(db.String(255))
    caminho_arquivo = db.Column(db.String(500))
    data_upload = db.Column(db.DateTime, default=datetime.utcnow)
    validade = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='PENDENTE')  # PENDENTE, ENVIADO, APROVADO, REJEITADO, VENCIDO
    observacao = db.Column(db.Text)
    solicitacao = db.relationship('SolicitacaoFornecedor', backref='documentos')

class ChecklistOnboarding(BaseModel):
    __tablename__ = 'vom_checklist'
    solicitacao_id = db.Column(db.Integer, db.ForeignKey('vom_solicitacoes.id'), nullable=False)
    etapa = db.Column(db.Integer, nullable=False)  # 1-Cadastro, 2-Documentos, 3-Qualificacao, 4-Aprovacao, 5-Integracao
    item = db.Column(db.String(200), nullable=False)
    concluido = db.Column(db.Boolean, default=False)
    data_conclusao = db.Column(db.DateTime)
    responsavel = db.Column(db.String(100))
    observacao = db.Column(db.Text)
    solicitacao = db.relationship('SolicitacaoFornecedor', backref='checklist')

class AvaliacaoFornecedor(BaseModel):
    __tablename__ = 'vom_avaliacoes'
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('erp_fornecedores.id'), nullable=False)
    criterio = db.Column(db.String(100), nullable=False)  # QUALIDADE, PRAZO_ENTREGA, PRECO, ATENDIMENTO, FLEXIBILIDADE
    nota = db.Column(db.Float, nullable=False)  # 0-10
    peso = db.Column(db.Float, default=1.0)
    data_avaliacao = db.Column(db.DateTime, default=datetime.utcnow)
    avaliador = db.Column(db.String(100))
    comentario = db.Column(db.Text)
    fornecedor = db.relationship('Fornecedor', backref='avaliacoes')

# ============================================================
# PDA - Production Data Analysis
# ============================================================
class OrdemProducao(BaseModel):
    __tablename__ = 'pda_ordens_producao'
    numero_op = db.Column(db.String(30), unique=True, nullable=False, index=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('erp_produtos.id'), nullable=False)
    quantidade_planejada = db.Column(db.Float, nullable=False)
    quantidade_produzida = db.Column(db.Float, default=0.0)
    quantidade_refugo = db.Column(db.Float, default=0.0)
    data_inicio_planejada = db.Column(db.DateTime)
    data_fim_planejada = db.Column(db.DateTime)
    data_inicio_real = db.Column(db.DateTime)
    data_fim_real = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='PLANEJADA')  # PLANEJADA, LIBERADA, EM_PRODUCAO, PAUSADA, CONCLUIDA, CANCELADA
    linha_producao = db.Column(db.String(50))
    responsavel = db.Column(db.String(100))
    produto = db.relationship('Produto', backref='ordens_producao')

class RegistroProducao(BaseModel):
    __tablename__ = 'pda_registros_producao'
    ordem_producao_id = db.Column(db.Integer, db.ForeignKey('pda_ordens_producao.id'), nullable=False)
    data_registro = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    turno = db.Column(db.String(20))  # MATUTINO, VESPERTINO, NOTURNO
    quantidade_boa = db.Column(db.Float, default=0.0)
    quantidade_refugo = db.Column(db.Float, default=0.0)
    tempo_producao_min = db.Column(db.Float, default=0.0)
    tempo_parada_min = db.Column(db.Float, default=0.0)
    motivo_parada = db.Column(db.String(200))
    operador = db.Column(db.String(100))
    maquina = db.Column(db.String(50))
    ordem_producao = db.relationship('OrdemProducao', backref='registros')

class IndicadorProducao(BaseModel):
    __tablename__ = 'pda_indicadores'
    data_referencia = db.Column(db.DateTime, nullable=False)
    linha_producao = db.Column(db.String(50))
    oee = db.Column(db.Float, default=0.0)  # Overall Equipment Effectiveness
    disponibilidade = db.Column(db.Float, default=0.0)
    performance = db.Column(db.Float, default=0.0)
    qualidade = db.Column(db.Float, default=0.0)
    tempo_ciclo = db.Column(db.Float, default=0.0)
    pecas_boas = db.Column(db.Float, default=0.0)
    pecas_refugo = db.Column(db.Float, default=0.0)
    tempo_planejado = db.Column(db.Float, default=0.0)
    tempo_real = db.Column(db.Float, default=0.0)

class ManutencaoMaquina(BaseModel):
    __tablename__ = 'pda_manutencoes'
    maquina = db.Column(db.String(50), nullable=False)
    tipo = db.Column(db.String(30), default='CORRETIVA')  # PREVENTIVA, CORRETIVA, PREDITIVA
    descricao = db.Column(db.Text)
    data_inicio = db.Column(db.DateTime)
    data_fim = db.Column(db.DateTime)
    tempo_parada_horas = db.Column(db.Float, default=0.0)
    custo = db.Column(db.Float, default=0.0)
    tecnico = db.Column(db.String(100))
    status = db.Column(db.String(20), default='ABERTA')  # ABERTA, EM_ANDAMENTO, CONCLUIDA

class ConsumoMateriaPrima(BaseModel):
    __tablename__ = 'pda_consumo_mp'
    ordem_producao_id = db.Column(db.Integer, db.ForeignKey('pda_ordens_producao.id'), nullable=False)
    produto_mp_id = db.Column(db.Integer, db.ForeignKey('erp_produtos.id'), nullable=False)
    quantidade_planejada = db.Column(db.Float, nullable=False)
    quantidade_real = db.Column(db.Float, default=0.0)
    unidade = db.Column(db.String(20))
    ordem_producao = db.relationship('OrdemProducao', backref='consumos')
    materia_prima = db.relationship('Produto')

# ============================================================
# SAP - System Integration & Accounting (contábil/fiscal)
# ============================================================
class PlanoConta(BaseModel):
    __tablename__ = 'sap_plano_contas'
    codigo = db.Column(db.String(20), unique=True, nullable=False, index=True)
    descricao = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # ATIVO, PASSIVO, PATRIMONIO, RECEITA, DESPESA, CUSTO
    natureza = db.Column(db.String(10), default='CREDORA')  # DEVEDORA, CREDORA
    conta_sintetica = db.Column(db.Boolean, default=False)
    conta_pai_id = db.Column(db.Integer, db.ForeignKey('sap_plano_contas.id'))

class LancamentoContabil(BaseModel):
    __tablename__ = 'sap_lancamentos'
    numero_lancamento = db.Column(db.String(30), unique=True, nullable=False, index=True)
    data_lancamento = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    data_competencia = db.Column(db.DateTime, nullable=False)
    historico = db.Column(db.String(300), nullable=False)
    tipo_documento = db.Column(db.String(20))  # NF, RECIBO, COMPROVANTE, AJUSTE
    documento_origem = db.Column(db.String(50))
    valor_total_debito = db.Column(db.Float, default=0.0)
    valor_total_credito = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='RASCUNHO')  # RASCUNHO, VALIDADO, CONTABILIZADO, ESTORNADO
    usuario = db.Column(db.String(100))

class PartidaDobrada(BaseModel):
    __tablename__ = 'sap_partidas'
    lancamento_id = db.Column(db.Integer, db.ForeignKey('sap_lancamentos.id'), nullable=False)
    plano_conta_id = db.Column(db.Integer, db.ForeignKey('sap_plano_contas.id'), nullable=False)
    tipo = db.Column(db.String(10), nullable=False)  # DEBITO, CREDITO
    valor = db.Column(db.Float, nullable=False)
    centro_custo = db.Column(db.String(50))
    historico_complementar = db.Column(db.String(200))
    lancamento = db.relationship('LancamentoContabil', backref='partidas')
    plano_conta = db.relationship('PlanoConta')

class CentroCusto(BaseModel):
    __tablename__ = 'sap_centros_custo'
    codigo = db.Column(db.String(20), unique=True, nullable=False, index=True)
    descricao = db.Column(db.String(200), nullable=False)
    departamento = db.Column(db.String(100))
    responsavel = db.Column(db.String(100))
    orcamento_mensal = db.Column(db.Float, default=0.0)
    tipo = db.Column(db.String(20), default='OPERACIONAL')  # OPERACIONAL, ADMINISTRATIVO, FINANCEIRO

class Imposto(BaseModel):
    __tablename__ = 'sap_impostos'
    nome = db.Column(db.String(50), nullable=False)  # ICMS, PIS, COFINS, IPI, ISS, IRPJ, CSLL
    aliquota = db.Column(db.Float, nullable=False)
    base_calculo = db.Column(db.String(100))
    regime = db.Column(db.String(30), default='LUCRO_PRESUMIDO')  # SIMPLES_NACIONAL, LUCRO_PRESUMIDO, LUCRO_REAL
    ativo = db.Column(db.Boolean, default=True)

class ApuracaoImposto(BaseModel):
    __tablename__ = 'sap_apuracoes'
    competencia = db.Column(db.String(7), nullable=False)  # MM/AAAA
    imposto_id = db.Column(db.Integer, db.ForeignKey('sap_impostos.id'), nullable=False)
    base_calculo = db.Column(db.Float, default=0.0)
    valor_apurado = db.Column(db.Float, default=0.0)
    valor_pago = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='APURADO')  # APURADO, PAGO, EM_ABERTO, PARCELADO
    data_vencimento = db.Column(db.DateTime)
    data_pagamento = db.Column(db.DateTime)
    imposto = db.relationship('Imposto')

class Balancete(BaseModel):
    __tablename__ = 'sap_balancetes'
    competencia = db.Column(db.String(7), nullable=False)
    plano_conta_id = db.Column(db.Integer, db.ForeignKey('sap_plano_contas.id'), nullable=False)
    saldo_anterior_debito = db.Column(db.Float, default=0.0)
    saldo_anterior_credito = db.Column(db.Float, default=0.0)
    movimento_debito = db.Column(db.Float, default=0.0)
    movimento_credito = db.Column(db.Float, default=0.0)
    saldo_atual_debito = db.Column(db.Float, default=0.0)
    saldo_atual_credito = db.Column(db.Float, default=0.0)
    plano_conta = db.relationship('PlanoConta')

# ============================================================
# INTEGRAÇÃO ENTRE MÓDULOS
# ============================================================
class IntegracaoLog(BaseModel):
    __tablename__ = 'integracao_logs'
    modulo_origem = db.Column(db.String(20), nullable=False)  # ERP, WMS, CRM, VOM, PDA, SAP
    modulo_destino = db.Column(db.String(20), nullable=False)
    tipo_operacao = db.Column(db.String(50), nullable=False)  # CREATE, UPDATE, DELETE, SYNC
    entidade = db.Column(db.String(100), nullable=False)
    entidade_id = db.Column(db.Integer)
    payload = db.Column(db.Text)
    status = db.Column(db.String(20), default='PENDENTE')  # PENDENTE, PROCESSADO, ERRO
    mensagem_erro = db.Column(db.Text)
    data_tentativa = db.Column(db.DateTime, default=datetime.utcnow)
    data_processamento = db.Column(db.DateTime)
