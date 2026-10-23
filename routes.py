# -*- coding: utf-8 -*-
"""
Routes - APIs REST por módulo
ERP, WMS, CRM, VOM, PDA, SAP + Integração
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from models import (
    db, Produto, Fornecedor, OrdemCompra, ItemOrdemCompra, NotaFiscalEntrada,
    ContaPagar, ContaReceber, MovimentacaoEstoque,
    Armazem, EnderecoArmazenagem, EstoquePorEndereco, OrdemSeparacao, ItemSeparacao,
    RecebimentoMercadoria, ItemRecebimento, Inventario, ItemInventario,
    Cliente, Contato, Oportunidade, AtividadeCRM, PedidoVenda, ItemPedidoVenda, Campanha,
    SolicitacaoFornecedor, DocumentoFornecedor, ChecklistOnboarding, AvaliacaoFornecedor,
    OrdemProducao, RegistroProducao, IndicadorProducao, ManutencaoMaquina, ConsumoMateriaPrima,
    PlanoConta, LancamentoContabil, PartidaDobrada, CentroCusto, Imposto, ApuracaoImposto, Balancete,
    IntegracaoLog
)
from services import ERPService, WMSService, CRMService, VOMService, PDAService, SAPService, IntegracaoService

api = Blueprint('api', __name__, url_prefix='/api')

def serialize(obj, exclude=None):
    """Serializa objeto SQLAlchemy para dict"""
    if obj is None:
        return None
    exclude = exclude or []
    data = {}
    for col in obj.__table__.columns:
        if col.name in exclude:
            continue
        val = getattr(obj, col.name)
        if isinstance(val, datetime):
            val = val.isoformat()
        data[col.name] = val
    return data

def listar(Model, query_filter=None):
    """Helper genérico para listagem"""
    q = Model.query.filter_by(ativo=True) if hasattr(Model, 'ativo') else Model.query
    if query_filter:
        q = q.filter_by(**query_filter)
    itens = q.all()
    return jsonify([serialize(i) for i in itens])

# ============================================================
# ERP ROUTES
# ============================================================
erp_bp = Blueprint('erp', __name__, url_prefix='/api/erp')

@erp_bp.route('/produtos', methods=['GET'])
def listar_produtos():
    return listar(Produto)

@erp_bp.route('/produtos', methods=['POST'])
def criar_produto():
    try:
        dados = request.get_json()
        produto = ERPService.criar_produto(dados)
        return jsonify(serialize(produto)), 201
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400

@erp_bp.route('/produtos/<int:id>', methods=['GET'])
def obter_produto(id):
    p = Produto.query.get_or_404(id)
    return jsonify(serialize(p))

@erp_bp.route('/produtos/<int:id>', methods=['PUT'])
def atualizar_produto(id):
    p = Produto.query.get_or_404(id)
    dados = request.get_json()
    for k, v in dados.items():
        if hasattr(p, k) and k not in ['id', 'criado_em']:
            setattr(p, k, v)
    if 'preco_custo' in dados or 'preco_venda' in dados:
        p.margem_lucro = ERPService.calcular_margem_lucro(p.preco_custo, p.preco_venda)
    db.session.commit()
    return jsonify(serialize(p))

@erp_bp.route('/produtos/estoque-baixo', methods=['GET'])
def estoque_baixo():
    return jsonify(ERPService.verificar_estoque_minimo())

@erp_bp.route('/fornecedores', methods=['GET'])
def listar_fornecedores():
    return listar(Fornecedor)

@erp_bp.route('/fornecedores', methods=['POST'])
def criar_fornecedor():
    dados = request.get_json()
    if Fornecedor.query.filter_by(cnpj=dados.get('cnpj')).first():
        return jsonify({'erro': 'CNPJ já cadastrado'}), 400
    f = Fornecedor(**{k: v for k, v in dados.items() if hasattr(Fornecedor, k)})
    db.session.add(f)
    db.session.commit()
    return jsonify(serialize(f)), 201

@erp_bp.route('/ordens-compra', methods=['GET'])
def listar_oc():
    return listar(OrdemCompra)

@erp_bp.route('/ordens-compra', methods=['POST'])
def criar_oc():
    try:
        dados = request.get_json()
        oc = ERPService.criar_ordem_compra(
            dados['fornecedor_id'],
            dados['itens'],
            {k: v for k, v in dados.items() if k not in ['fornecedor_id', 'itens']}
        )
        return jsonify(serialize(oc)), 201
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400

@erp_bp.route('/contas-pagar', methods=['GET'])
def listar_cp():
    return listar(ContaPagar)

@erp_bp.route('/contas-pagar/<int:id>/pagar', methods=['POST'])
def pagar_conta(id):
    cp = ContaPagar.query.get_or_404(id)
    dados = request.get_json() or {}
    cp.valor_pago = dados.get('valor_pago', cp.valor_original)
    cp.data_pagamento = datetime.utcnow()
    cp.status = 'PAGO'
    cp.metodo_pagamento = dados.get('metodo_pagamento', 'PIX')
    db.session.commit()
    return jsonify(serialize(cp))

@erp_bp.route('/contas-receber', methods=['GET'])
def listar_cr():
    return listar(ContaReceber)

@erp_bp.route('/contas-receber/<int:id>/receber', methods=['POST'])
def receber_conta(id):
    cr = ContaReceber.query.get_or_404(id)
    dados = request.get_json() or {}
    cr.valor_recebido = dados.get('valor_recebido', cr.valor_original)
    cr.data_recebimento = datetime.utcnow()
    cr.status = 'PAGO'
    db.session.commit()
    return jsonify(serialize(cr))

@erp_bp.route('/fluxo-caixa', methods=['GET'])
def fluxo_caixa():
    dias = int(request.args.get('dias', 30))
    return jsonify(ERPService.fluxo_caixa_previsto(dias))

@erp_bp.route('/movimentacoes-estoque', methods=['GET'])
def listar_mov():
    return listar(MovimentacaoEstoque)

@erp_bp.route('/notas-fiscais-entrada', methods=['POST'])
def criar_nf_entrada():
    dados = request.get_json()
    nf = NotaFiscalEntrada(**{k: v for k, v in dados.items() if hasattr(NotaFiscalEntrada, k)})
    db.session.add(nf)
    db.session.commit()
    return jsonify(serialize(nf)), 201

# ============================================================
# WMS ROUTES
# ============================================================
wms_bp = Blueprint('wms', __name__, url_prefix='/api/wms')

@wms_bp.route('/armazens', methods=['GET'])
def listar_armazens():
    return listar(Armazem)

@wms_bp.route('/armazens', methods=['POST'])
def criar_armazem():
    dados = request.get_json()
    a = Armazem(**{k: v for k, v in dados.items() if hasattr(Armazem, k)})
    db.session.add(a)
    db.session.commit()
    return jsonify(serialize(a)), 201

@wms_bp.route('/enderecos', methods=['GET'])
def listar_enderecos():
    return listar(EnderecoArmazenagem)

@wms_bp.route('/enderecos', methods=['POST'])
def criar_endereco():
    dados = request.get_json()
    e = EnderecoArmazenagem(**{k: v for k, v in dados.items() if hasattr(EnderecoArmazenagem, k)})
    db.session.add(e)
    db.session.commit()
    return jsonify(serialize(e)), 201

@wms_bp.route('/estoque-endereco', methods=['GET'])
def estoque_endereco():
    return listar(EstoquePorEndereco)

@wms_bp.route('/ordens-separacao', methods=['GET'])
def listar_os():
    return listar(OrdemSeparacao)

@wms_bp.route('/ordens-separacao', methods=['POST'])
def criar_os():
    try:
        dados = request.get_json()
        os = WMSService.criar_ordem_separacao(dados['pedido_venda_id'])
        return jsonify(serialize(os)), 201
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400

@wms_bp.route('/ordens-separacao/<int:id>/confirmar', methods=['POST'])
def confirmar_os(id):
    try:
        dados = request.get_json()
        os = WMSService.confirmar_separacao(id, dados['itens'])
        return jsonify(serialize(os))
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400

@wms_bp.route('/recebimentos', methods=['GET'])
def listar_recebimentos():
    return listar(RecebimentoMercadoria)

@wms_bp.route('/recebimentos', methods=['POST'])
def criar_recebimento():
    dados = request.get_json()
    r = RecebimentoMercadoria(**{k: v for k, v in dados.items() if hasattr(RecebimentoMercadoria, k)})
    db.session.add(r)
    db.session.commit()
    return jsonify(serialize(r)), 201

@wms_bp.route('/recebimentos/<int:id>/conferir', methods=['POST'])
def conferir_recebimento(id):
    try:
        dados = request.get_json()
        r = WMSService.receber_mercadoria_wms(id, dados['itens'])
        return jsonify(serialize(r))
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400

@wms_bp.route('/inventarios', methods=['GET'])
def listar_inventarios():
    return listar(Inventario)

@wms_bp.route('/inventarios', methods=['POST'])
def criar_inventario():
    dados = request.get_json()
    inv = WMSService.criar_inventario(dados['armazem_id'], dados.get('tipo', 'GERAL'))
    return jsonify(serialize(inv)), 201

@wms_bp.route('/inventarios/<int:id>/finalizar', methods=['POST'])
def finalizar_inventario(id):
    try:
        dados = request.get_json()
        inv = WMSService.finalizar_inventario(id, dados['contagens'])
        return jsonify(serialize(inv))
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400

@wms_bp.route('/relatorios/ocupacao', methods=['GET'])
def relatorio_ocupacao():
    return jsonify(WMSService.relatorio_ocupacao())

# ============================================================
# CRM ROUTES
# ============================================================
crm_bp = Blueprint('crm', __name__, url_prefix='/api/crm')

@crm_bp.route('/clientes', methods=['GET'])
def listar_clientes():
    return listar(Cliente)

@crm_bp.route('/clientes', methods=['POST'])
def criar_cliente():
    dados = request.get_json()
    if Cliente.query.filter_by(cpf_cnpj=dados.get('cpf_cnpj')).first():
        return jsonify({'erro': 'CPF/CNPJ já cadastrado'}), 400
    c = Cliente(**{k: v for k, v in dados.items() if hasattr(Cliente, k)})
    db.session.add(c)
    db.session.commit()
    return jsonify(serialize(c)), 201

@crm_bp.route('/clientes/<int:id>/score', methods=['GET'])
def score_cliente(id):
    score = CRMService.calcular_score_cliente(id)
    return jsonify({'cliente_id': id, 'score': score})

@crm_bp.route('/contatos', methods=['GET'])
def listar_contatos():
    return listar(Contato)

@crm_bp.route('/oportunidades', methods=['GET'])
def listar_oportunidades():
    return listar(Oportunidade)

@crm_bp.route('/oportunidades', methods=['POST'])
def criar_oportunidade():
    dados = request.get_json()
    o = Oportunidade(**{k: v for k, v in dados.items() if hasattr(Oportunidade, k)})
    db.session.add(o)
    db.session.commit()
    return jsonify(serialize(o)), 201

@crm_bp.route('/oportunidades/<int:id>/avancar', methods=['POST'])
def avancar_oportunidade(id):
    try:
        dados = request.get_json()
        o = CRMService.avancar_estagio_oportunidade(id, dados['novo_estagio'])
        return jsonify(serialize(o))
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400

@crm_bp.route('/funil-vendas', methods=['GET'])
def funil_vendas():
    return jsonify(CRMService.funil_vendas())

@crm_bp.route('/atividades', methods=['GET'])
def listar_atividades():
    return listar(AtividadeCRM)

@crm_bp.route('/atividades', methods=['POST'])
def criar_atividade():
    dados = request.get_json()
    a = CRMService.criar_atividade(
        dados['tipo'], dados['titulo'],
        dados.get('cliente_id'), dados.get('oportunidade_id'),
        dados.get('data_agendada'), dados.get('responsavel')
    )
    return jsonify(serialize(a)), 201

@crm_bp.route('/pedidos-venda', methods=['GET'])
def listar_pedidos():
    return listar(PedidoVenda)

@crm_bp.route('/pedidos-venda', methods=['POST'])
def criar_pedido():
    try:
        dados = request.get_json()
        pedido = CRMService.criar_pedido_venda(
            dados['cliente_id'],
            dados['itens'],
            {k: v for k, v in dados.items() if k not in ['cliente_id', 'itens']}
        )
        return jsonify(serialize(pedido)), 201
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400

@crm_bp.route('/pedidos-venda/<int:id>/faturar', methods=['POST'])
def faturar_pedido(id):
    try:
        pedido = PedidoVenda.query.get_or_404(id)
        ERPService.baixar_estoque_venda(id)
        SAPService.contabilizar_venda(id)
        return jsonify({'mensagem': f'Pedido {pedido.numero_pedido} faturado com sucesso', 'status': pedido.status})
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400

@crm_bp.route('/campanhas', methods=['GET'])
def listar_campanhas():
    return listar(Campanha)

# ============================================================
# VOM ROUTES - Vendor On-Boarding
# ============================================================
vom_bp = Blueprint('vom', __name__, url_prefix='/api/vom')

@vom_bp.route('/solicitacoes', methods=['GET'])
def listar_solicitacoes():
    return listar(SolicitacaoFornecedor)

@vom_bp.route('/solicitacoes', methods=['POST'])
def iniciar_solicitacao():
    try:
        dados = request.get_json()
        sol = VOMService.iniciar_solicitacao(dados)
        return jsonify(serialize(sol)), 201
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400

@vom_bp.route('/solicitacoes/<int:id>/status', methods=['GET'])
def status_solicitacao(id):
    status = VOMService.status_onboarding(id)
    if not status:
        return jsonify({'erro': 'Não encontrada'}), 404
    return jsonify(status)

@vom_bp.route('/documentos', methods=['POST'])
def enviar_documento():
    dados = request.get_json()
    doc = VOMService.enviar_documento(
        dados['solicitacao_id'],
        dados['tipo_documento'],
        dados['nome_arquivo'],
        dados.get('validade')
    )
    return jsonify(serialize(doc)), 201

@vom_bp.route('/checklist/<int:id>/concluir', methods=['POST'])
def concluir_checklist(id):
    dados = request.get_json() or {}
    cl = VOMService.concluir_checklist(dados.get('solicitacao_id'), id, dados.get('responsavel'))
    return jsonify(serialize(cl))

@vom_bp.route('/solicitacoes/<int:id>/aprovar', methods=['POST'])
def aprovar_fornecedor(id):
    try:
        fornecedor = VOMService.aprovar_fornecedor(id)
        return jsonify({'mensagem': 'Fornecedor aprovado e cadastrado no ERP', 'fornecedor': serialize(fornecedor)})
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400

@vom_bp.route('/avaliacoes', methods=['POST'])
def avaliar_fornecedor():
    dados = request.get_json()
    media = VOMService.avaliar_fornecedor(
        dados['fornecedor_id'],
        dados['avaliacoes'],
        dados.get('avaliador', 'SISTEMA')
    )
    return jsonify({'media_ponderada': media})

# ============================================================
# PDA ROUTES - Production Data Analysis
# ============================================================
pda_bp = Blueprint('pda', __name__, url_prefix='/api/pda')

@pda_bp.route('/ordens-producao', methods=['GET'])
def listar_ops():
    return listar(OrdemProducao)

@pda_bp.route('/ordens-producao', methods=['POST'])
def criar_op():
    dados = request.get_json()
    op = PDAService.criar_ordem_producao(
        dados['produto_id'],
        dados['quantidade_planejada'],
        {k: v for k, v in dados.items() if k not in ['produto_id', 'quantidade_planejada']}
    )
    return jsonify(serialize(op)), 201

@pda_bp.route('/ordens-producao/<int:id>/liberar', methods=['POST'])
def liberar_op(id):
    op = OrdemProducao.query.get_or_404(id)
    op.status = 'LIBERADA'
    db.session.commit()
    return jsonify(serialize(op))

@pda_bp.route('/registros-producao', methods=['POST'])
def registrar_producao():
    try:
        dados = request.get_json()
        reg = PDAService.registrar_producao(dados['ordem_producao_id'], dados)
        return jsonify(serialize(reg)), 201
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400

@pda_bp.route('/indicadores', methods=['GET'])
def listar_indicadores():
    return listar(IndicadorProducao)

@pda_bp.route('/manutencoes', methods=['GET'])
def listar_manutencoes():
    return listar(ManutencaoMaquina)

@pda_bp.route('/manutencoes', methods=['POST'])
def criar_manutencao():
    dados = request.get_json()
    m = PDAService.registrar_manutencao(
        dados['maquina'], dados['tipo'], dados['descricao'],
        dados.get('tempo_parada_horas', 0), dados.get('custo', 0), dados.get('tecnico')
    )
    return jsonify(serialize(m)), 201

@pda_bp.route('/dashboard', methods=['GET'])
def dashboard_pda():
    dias = int(request.args.get('dias', 30))
    return jsonify(PDAService.dashboard_producao(dias))

# ============================================================
# SAP ROUTES - Accounting & Tax
# ============================================================
sap_bp = Blueprint('sap', __name__, url_prefix='/api/sap')

@sap_bp.route('/plano-contas', methods=['GET'])
def listar_plano_contas():
    return listar(PlanoConta)

@sap_bp.route('/lancamentos', methods=['GET'])
def listar_lancamentos():
    return listar(LancamentoContabil)

@sap_bp.route('/lancamentos', methods=['POST'])
def criar_lancamento():
    try:
        dados = request.get_json()
        lanc = SAPService.criar_lancamento_contabil(
            datetime.fromisoformat(dados['data_competencia']) if isinstance(dados['data_competencia'], str) else dados['data_competencia'],
            dados['historico'],
            dados['partidas'],
            dados.get('tipo_documento'),
            dados.get('documento_origem'),
            dados.get('usuario', 'SISTEMA')
        )
        return jsonify(serialize(lanc)), 201
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400

@sap_bp.route('/centros-custo', methods=['GET'])
def listar_cc():
    return listar(CentroCusto)

@sap_bp.route('/impostos', methods=['GET'])
def listar_impostos():
    return listar(Imposto)

@sap_bp.route('/apuracoes', methods=['GET'])
def listar_apuracoes():
    return listar(ApuracaoImposto)

@sap_bp.route('/apuracoes', methods=['POST'])
def apurar_imposto():
    dados = request.get_json()
    ap = SAPService.apuracao_imposto(dados['competencia'], dados['imposto_nome'], dados['base_calculo'])
    return jsonify(serialize(ap)), 201

@sap_bp.route('/balancete/<path:competencia>', methods=['GET'])
def balancete(competencia):
    return jsonify(SAPService.gerar_balancete(competencia))

@sap_bp.route('/dre/<path:competencia>', methods=['GET'])
def dre(competencia):
    return jsonify(SAPService.demonstrativo_resultado(competencia))

# ============================================================
# INTEGRAÇÃO ROUTES
# ============================================================
int_bp = Blueprint('integracao', __name__, url_prefix='/api/integracao')

@int_bp.route('/logs', methods=['GET'])
def listar_logs():
    logs = IntegracaoLog.query.order_by(IntegracaoLog.id.desc()).limit(100).all()
    return jsonify([serialize(l) for l in logs])

@int_bp.route('/processar-fila', methods=['POST'])
def processar_fila():
    qtd = IntegracaoService.processar_fila()
    return jsonify({'processados': qtd})

@int_bp.route('/dashboard', methods=['GET'])
def dashboard_geral():
    """Dashboard consolidado de todos os módulos"""
    return jsonify({
        'erp': {
            'produtos_cadastrados': Produto.query.count(),
            'fornecedores': Fornecedor.query.count(),
            'contas_pagar_abertas': ContaPagar.query.filter(ContaPagar.status.in_(['PENDENTE', 'ATRASADO'])).count(),
            'contas_receber_abertas': ContaReceber.query.filter_by(status='PENDENTE').count(),
            'fluxo_caixa_30d': ERPService.fluxo_caixa_previsto(30)
        },
        'wms': {
            'armazens': Armazem.query.count(),
            'enderecos': EnderecoArmazenagem.query.count(),
            'ordens_separacao_pendentes': OrdemSeparacao.query.filter_by(status='PENDENTE').count(),
            'ocupacao': WMSService.relatorio_ocupacao()
        },
        'crm': {
            'clientes': Cliente.query.count(),
            'oportunidades_abertas': Oportunidade.query.filter(Oportunidade.estagio.notin_(['FECHADA', 'PERDIDA'])).count(),
            'pedidos_pendentes': PedidoVenda.query.filter(PedidoVenda.status.notin_(['ENTREGUE', 'CANCELADO'])).count(),
            'funil_vendas': CRMService.funil_vendas()
        },
        'vom': {
            'solicitacoes_em_andamento': SolicitacaoFornecedor.query.filter(SolicitacaoFornecedor.status.notin_(['CADASTRADO', 'REJEITADO'])).count(),
            'fornecedores_aprovados': Fornecedor.query.filter_by(status_aprovacao='APROVADO').count()
        },
        'pda': PDAService.dashboard_producao(30),
        'sap': {
            'lancamentos_contabeis': LancamentoContabil.query.count(),
            'impostos_apurados': ApuracaoImposto.query.filter_by(status='APURADO').count()
        }
    })
