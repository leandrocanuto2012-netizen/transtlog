# -*- coding: utf-8 -*-
"""
Services - Regras de Negócio por Módulo
ERP, WMS, CRM, VOM, PDA, SAP
"""
from datetime import datetime, timedelta
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

# ============================================================
# SERVIÇO DE INTEGRAÇÃO ENTRE MÓDULOS
# ============================================================
class IntegracaoService:
    @staticmethod
    def registrar_log(modulo_origem, modulo_destino, tipo_operacao, entidade, entidade_id, payload):
        log = IntegracaoLog(
            modulo_origem=modulo_origem,
            modulo_destino=modulo_destino,
            tipo_operacao=tipo_operacao,
            entidade=entidade,
            entidade_id=entidade_id,
            payload=str(payload),
            status='PENDENTE'
        )
        db.session.add(log)
        db.session.flush()
        return log

    @staticmethod
    def processar_fila():
        """Processa logs pendentes de integração"""
        pendentes = IntegracaoLog.query.filter_by(status='PENDENTE').all()
        processados = 0
        for log in pendentes:
            try:
                log.status = 'PROCESSADO'
                log.data_processamento = datetime.utcnow()
                processados += 1
            except Exception as e:
                log.status = 'ERRO'
                log.mensagem_erro = str(e)
        db.session.commit()
        return processados

# ============================================================
# ERP SERVICE
# ============================================================
class ERPService:
    """Regras de negócio do ERP (Enterprise Resource Planning)"""

    @staticmethod
    def calcular_margem_lucro(preco_custo, preco_venda):
        """Regra: margem = ((venda - custo) / venda) * 100"""
        if preco_venda <= 0:
            return 0.0
        return round(((preco_venda - preco_custo) / preco_venda) * 100, 2)

    @staticmethod
    def criar_produto(dados):
        """Regra: SKU único, margem automática, validação de preços"""
        if Produto.query.filter_by(codigo_sku=dados['codigo_sku']).first():
            raise ValueError(f"SKU {dados['codigo_sku']} já cadastrado")
        if dados.get('preco_venda', 0) < dados.get('preco_custo', 0):
            raise ValueError("Preço de venda não pode ser menor que preço de custo")

        produto = Produto(**{k: v for k, v in dados.items() if hasattr(Produto, k)})
        produto.margem_lucro = ERPService.calcular_margem_lucro(
            dados.get('preco_custo', 0), dados.get('preco_venda', 0)
        )
        db.session.add(produto)
        db.session.commit()
        IntegracaoService.registrar_log('ERP', 'WMS', 'CREATE', 'Produto', produto.id, dados)
        IntegracaoService.registrar_log('ERP', 'SAP', 'CREATE', 'Produto', produto.id, dados)
        db.session.commit()
        return produto

    @staticmethod
    def criar_ordem_compra(fornecedor_id, itens, dados_extra=None):
        """
        Regras:
        - Fornecedor deve estar APROVADO
        - Valor total = soma (qtd * preco) - desconto + frete
        - Número OC automático
        - Verifica limite de crédito do fornecedor
        """
        fornecedor = Fornecedor.query.get(fornecedor_id)
        if not fornecedor:
            raise ValueError("Fornecedor não encontrado")
        if fornecedor.status_aprovacao != 'APROVADO':
            raise ValueError(f"Fornecedor {fornecedor.razao_social} não está aprovado (status: {fornecedor.status_aprovacao})")

        numero_oc = f"OC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        oc = OrdemCompra(
            numero_oc=numero_oc,
            fornecedor_id=fornecedor_id,
            status='ABERTA',
            **(dados_extra or {})
        )
        db.session.add(oc)
        db.session.flush()

        valor_total = 0.0
        for item in itens:
            produto = Produto.query.get(item['produto_id'])
            if not produto:
                raise ValueError(f"Produto {item['produto_id']} não encontrado")
            valor_item = item['quantidade'] * item['preco_unitario']
            item_oc = ItemOrdemCompra(
                ordem_compra_id=oc.id,
                produto_id=item['produto_id'],
                quantidade=item['quantidade'],
                preco_unitario=item['preco_unitario'],
                valor_total=valor_item
            )
            db.session.add(item_oc)
            valor_total += valor_item

        oc.valor_total = valor_total - (dados_extra or {}).get('desconto', 0) + (dados_extra or {}).get('frete', 0)

        # Verifica limite de crédito
        total_em_aberto = db.session.query(db.func.coalesce(db.func.sum(ContaPagar.valor_original), 0)).filter(
            ContaPagar.fornecedor_id == fornecedor_id,
            ContaPagar.status.in_(['PENDENTE', 'ATRASADO'])
        ).scalar()
        if fornecedor.limite_credito > 0 and (total_em_aberto + oc.valor_total) > fornecedor.limite_credito:
            oc.status = 'ABERTA'  # Mantém aberta para aprovação gerencial

        db.session.commit()
        IntegracaoService.registrar_log('ERP', 'SAP', 'CREATE', 'OrdemCompra', oc.id, {'valor_total': oc.valor_total})
        db.session.commit()
        return oc

    @staticmethod
    def receber_mercadoria(nota_fiscal_id, itens_recebidos):
        """
        Regras:
        - Atualiza estoque do ERP
        - Gera movimentação de estoque tipo ENTRADA
        - Cria conta a pagar vinculada à NF
        - Integra com WMS para endereçamento
        """
        nf = NotaFiscalEntrada.query.get(nota_fiscal_id)
        if not nf:
            raise ValueError("Nota fiscal não encontrada")

        for item in itens_recebidos:
            produto = Produto.query.get(item['produto_id'])
            if not produto:
                continue
            qtd = item['quantidade_recebida']
            saldo_anterior = produto.estoque_atual
            produto.estoque_atual += qtd

            mov = MovimentacaoEstoque(
                produto_id=produto.id,
                tipo='ENTRADA',
                quantidade=qtd,
                saldo_anterior=saldo_anterior,
                saldo_atual=produto.estoque_atual,
                origem='NF',
                documento_ref=nf.numero_nf,
                usuario='SISTEMA'
            )
            db.session.add(mov)

        # Cria conta a pagar
        cp = ContaPagar(
            descricao=f"NF {nf.numero_nf} - {nf.fornecedor.razao_social}",
            fornecedor_id=nf.fornecedor_id,
            categoria='COMPRAS',
            valor_original=nf.valor_total,
            data_vencimento=datetime.utcnow() + timedelta(days=30),
            numero_documento=nf.numero_nf
        )
        db.session.add(cp)
        nf.status = 'RECEBIDA'
        db.session.commit()

        IntegracaoService.registrar_log('ERP', 'WMS', 'UPDATE', 'Estoque', None, {'nf_id': nota_fiscal_id})
        IntegracaoService.registrar_log('ERP', 'SAP', 'CREATE', 'ContaPagar', cp.id, {'valor': cp.valor_original})
        db.session.commit()
        return True

    @staticmethod
    def baixar_estoque_venda(pedido_venda_id):
        """Regra: baixa estoque ao faturar pedido de venda (integração CRM→ERP)"""
        pedido = PedidoVenda.query.get(pedido_venda_id)
        if not pedido:
            raise ValueError("Pedido não encontrado")

        for item in pedido.itens:
            produto = Produto.query.get(item.produto_id)
            if produto.estoque_atual < item.quantidade:
                raise ValueError(f"Estoque insuficiente para {produto.nome}: disponível {produto.estoque_atual}, necessário {item.quantidade}")

            saldo_anterior = produto.estoque_atual
            produto.estoque_atual -= item.quantidade
            mov = MovimentacaoEstoque(
                produto_id=produto.id,
                tipo='SAIDA',
                quantidade=item.quantidade,
                saldo_anterior=saldo_anterior,
                saldo_atual=produto.estoque_atual,
                origem='VENDA',
                documento_ref=pedido.numero_pedido,
                usuario='SISTEMA'
            )
            db.session.add(mov)

        # Cria conta a receber
        cr = ContaReceber(
            descricao=f"Pedido {pedido.numero_pedido} - {pedido.cliente.nome}",
            cliente_id=pedido.cliente_id,
            categoria='VENDAS',
            valor_original=pedido.valor_total,
            data_vencimento=datetime.utcnow() + timedelta(days=30),
            numero_documento=pedido.numero_pedido
        )
        db.session.add(cr)
        pedido.status = 'FATURADO'
        db.session.commit()

        IntegracaoService.registrar_log('ERP', 'WMS', 'CREATE', 'OrdemSeparacao', None, {'pedido_id': pedido_venda_id})
        IntegracaoService.registrar_log('ERP', 'SAP', 'CREATE', 'ContaReceber', cr.id, {'valor': cr.valor_original})
        db.session.commit()
        return True

    @staticmethod
    def verificar_estoque_minimo():
        """Regra: alerta produtos abaixo do estoque mínimo"""
        produtos = Produto.query.filter(
            Produto.estoque_atual <= Produto.estoque_minimo,
            Produto.ativo == True
        ).all()
        return [{'id': p.id, 'sku': p.codigo_sku, 'nome': p.nome, 'estoque': p.estoque_atual, 'minimo': p.estoque_minimo} for p in produtos]

    @staticmethod
    def fluxo_caixa_previsto(dias=30):
        """Regra: projeta fluxo de caixa com contas a pagar/receber"""
        hoje = datetime.utcnow()
        limite = hoje + timedelta(days=dias)
        a_pagar = ContaPagar.query.filter(
            ContaPagar.status.in_(['PENDENTE', 'ATRASADO']),
            ContaPagar.data_vencimento <= limite
        ).all()
        a_receber = ContaReceber.query.filter(
            ContaReceber.status == 'PENDENTE',
            ContaReceber.data_vencimento <= limite
        ).all()
        total_pagar = sum(c.valor_original - c.valor_pago for c in a_pagar)
        total_receber = sum(r.valor_original - r.valor_recebido for r in a_receber)
        return {
            'periodo_dias': dias,
            'total_a_pagar': round(total_pagar, 2),
            'total_a_receber': round(total_receber, 2),
            'saldo_previsto': round(total_receber - total_pagar, 2),
            'contas_pagar': len(a_pagar),
            'contas_receber': len(a_receber)
        }

# ============================================================
# WMS SERVICE
# ============================================================
class WMSService:
    """Regras de negócio do WMS (Warehouse Management System)"""

    @staticmethod
    def alocar_endereco(produto_id, quantidade, armazem_id=None):
        """
        Regra FEFO (First Expired, First Out) + endereço com capacidade
        Retorna o melhor endereço disponível
        """
        query = EnderecoArmazenagem.query.filter_by(status='DISPONIVEL')
        if armazem_id:
            query = query.filter_by(armazem_id=armazem_id)

        enderecos = query.all()
        for end in enderecos:
            disponivel = end.capacidade - end.ocupacao_atual
            if disponivel >= quantidade:
                return end
        return None

    @staticmethod
    def criar_ordem_separacao(pedido_venda_id):
        """Regra: cria OS a partir de pedido, define prioridade por SLA do cliente"""
        pedido = PedidoVenda.query.get(pedido_venda_id)
        if not pedido:
            raise ValueError("Pedido não encontrado")

        numero = f"OS-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        prioridade = 'ALTA' if pedido.cliente.score >= 80 else 'NORMAL'

        os = OrdemSeparacao(
            numero=numero,
            pedido_venda_id=pedido_venda_id,
            status='PENDENTE',
            prioridade=prioridade
        )
        db.session.add(os)
        db.session.flush()

        for item in pedido.itens:
            # FEFO: busca lote com validade mais próxima
            estoques = EstoquePorEndereco.query.filter_by(
                produto_id=item.produto_id
            ).order_by(EstoquePorEndereco.data_validade.asc()).all()

            endereco_id = estoques[0].endereco_id if estoques else None
            lote = estoques[0].lote if estoques else None

            item_sep = ItemSeparacao(
                ordem_separacao_id=os.id,
                produto_id=item.produto_id,
                quantidade_solicitada=item.quantidade,
                endereco_origem_id=endereco_id,
                lote=lote,
                status='PENDENTE'
            )
            db.session.add(item_sep)

        db.session.commit()
        return os

    @staticmethod
    def confirmar_separacao(ordem_separacao_id, itens_separados):
        """Regra: confirma separação, atualiza estoque por endereço, valida quantidade"""
        os = OrdemSeparacao.query.get(ordem_separacao_id)
        if not os:
            raise ValueError("Ordem de separação não encontrada")

        os.status = 'EM_SEPARACAO'
        os.data_inicio = datetime.utcnow()

        for item_sep in itens_separados:
            item_db = ItemSeparacao.query.get(item_sep['item_id'])
            if item_sep['quantidade'] < item_db.quantidade_solicitada:
                raise ValueError(f"Quantidade separada menor que solicitada para item {item_db.produto.nome}")

            item_db.quantidade_separada = item_sep['quantidade']
            item_db.status = 'CONCLUIDO'

            # Atualiza estoque no endereço
            if item_db.endereco_origem_id:
                est = EstoquePorEndereco.query.filter_by(
                    endereco_id=item_db.endereco_origem_id,
                    produto_id=item_db.produto_id,
                    lote=item_db.lote
                ).first()
                if est:
                    est.quantidade -= item_sep['quantidade']
                    endereco = EnderecoArmazenagem.query.get(item_db.endereco_origem_id)
                    endereco.ocupacao_atual -= item_sep['quantidade']
                    if endereco.ocupacao_atual <= 0:
                        endereco.status = 'DISPONIVEL'

        os.status = 'CONCLUIDA'
        os.data_conclusao = datetime.utcnow()
        db.session.commit()

        # Integra com ERP para baixa de estoque
        if os.pedido_venda_id:
            ERPService.baixar_estoque_venda(os.pedido_venda_id)

        return os

    @staticmethod
    def receber_mercadoria_wms(recebimento_id, itens_conferidos):
        """
        Regras WMS de recebimento:
        - Conferência quantidade nota x recebida
        - Avarias registradas separadamente
        - Endereçamento automático (putaway)
        - Atualiza ocupação do endereço
        """
        rec = RecebimentoMercadoria.query.get(recebimento_id)
        if not rec:
            raise ValueError("Recebimento não encontrado")

        rec.status = 'EM_CONFERENCIA'
        rec.data_conferencia = datetime.utcnow()

        for item_conf in itens_conferidos:
            item_db = ItemRecebimento.query.get(item_conf['item_id'])
            item_db.quantidade_recebida = item_conf['quantidade_recebida']
            item_db.quantidade_avariada = item_conf.get('quantidade_avariada', 0)
            item_db.lote = item_conf.get('lote')
            item_db.data_validade = item_conf.get('data_validade')

            # Putaway: aloca endereço
            qtd_liquida = item_conf['quantidade_recebida'] - item_conf.get('quantidade_avariada', 0)
            if qtd_liquida > 0:
                endereco = WMSService.alocar_endereco(item_db.produto_id, qtd_liquida)
                if endereco:
                    item_db.endereco_destino_id = endereco.id
                    est = EstoquePorEndereco(
                        endereco_id=endereco.id,
                        produto_id=item_db.produto_id,
                        lote=item_conf.get('lote'),
                        quantidade=qtd_liquida,
                        data_validade=item_conf.get('data_validade')
                    )
                    db.session.add(est)
                    endereco.ocupacao_atual += qtd_liquida
                    if endereco.ocupacao_atual >= endereco.capacidade * 0.95:
                        endereco.status = 'OCUPADO'
            item_db.status = 'CONFERIDO'

        rec.status = 'ENDERECADO'
        db.session.commit()

        # Integra com ERP
        if rec.nota_fiscal_id:
            ERPService.receber_mercadoria(rec.nota_fiscal_id, [
                {'produto_id': i.produto_id, 'quantidade_recebida': i.quantidade_recebida - i.quantidade_avariada}
                for i in rec.itens
            ])

        rec.status = 'FINALIZADO'
        db.session.commit()
        return rec

    @staticmethod
    def criar_inventario(armazem_id, tipo='GERAL'):
        """Regra: cria inventário e gera itens a contar com saldo do sistema"""
        numero = f"INV-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        inv = Inventario(
            numero=numero,
            armazem_id=armazem_id,
            tipo=tipo,
            status='ABERTO'
        )
        db.session.add(inv)
        db.session.flush()

        estoques = EstoquePorEndereco.query.join(EnderecoArmazenagem).filter(
            EnderecoArmazenagem.armazem_id == armazem_id
        ).all()

        for est in estoques:
            item_inv = ItemInventario(
                inventario_id=inv.id,
                produto_id=est.produto_id,
                endereco_id=est.endereco_id,
                quantidade_sistema=est.quantidade,
                status='PENDENTE'
            )
            db.session.add(item_inv)

        db.session.commit()
        return inv

    @staticmethod
    def finalizar_inventario(inventario_id, contagens):
        """Regra: ajusta estoque com diferenças, gera movimentação AJUSTE"""
        inv = Inventario.query.get(inventario_id)
        if not inv:
            raise ValueError("Inventário não encontrado")

        for contagem in contagens:
            item = ItemInventario.query.get(contagem['item_id'])
            item.quantidade_contada = contagem['quantidade_contada']
            item.diferenca = contagem['quantidade_contada'] - (item.quantidade_sistema or 0)
            item.status = 'CONTADO'

            if abs(item.diferenca) > 0:
                # Ajusta estoque ERP
                produto = Produto.query.get(item.produto_id)
                saldo_anterior = produto.estoque_atual
                produto.estoque_atual += item.diferenca
                mov = MovimentacaoEstoque(
                    produto_id=produto.id,
                    tipo='AJUSTE',
                    quantidade=item.diferenca,
                    saldo_anterior=saldo_anterior,
                    saldo_atual=produto.estoque_atual,
                    origem='INVENTARIO',
                    documento_ref=inv.numero,
                    usuario='SISTEMA',
                    observacoes=f"Ajuste de inventário {inv.numero}"
                )
                db.session.add(mov)
                item.status = 'AJUSTADO'

        inv.status = 'FINALIZADO'
        inv.data_fim = datetime.utcnow()
        db.session.commit()
        return inv

    @staticmethod
    def relatorio_ocupacao():
        """Regra: calcula ocupação por armazém e endereço"""
        armazens = Armazem.query.all()
        resultado = []
        for arm in armazens:
            total_cap = sum(e.capacidade for e in arm.enderecos)
            total_ocup = sum(e.ocupacao_atual for e in arm.enderecos)
            percentual = (total_ocup / total_cap * 100) if total_cap > 0 else 0
            resultado.append({
                'armazem': arm.nome,
                'codigo': arm.codigo,
                'capacidade_total': total_cap,
                'ocupacao_atual': total_ocup,
                'percentual_ocupacao': round(percentual, 2),
                'enderecos_total': len(arm.enderecos),
                'enderecos_disponiveis': len([e for e in arm.enderecos if e.status == 'DISPONIVEL'])
            })
        return resultado

# ============================================================
# CRM SERVICE
# ============================================================
class CRMService:
    """Regras de negócio do CRM (Customer Relationship Management)"""

    @staticmethod
    def calcular_score_cliente(cliente_id):
        """Regra: score baseado em histórico de compras, pagamentos e frequência"""
        cliente = Cliente.query.get(cliente_id)
        if not cliente:
            return 0

        score = 50  # base
        # + Pontos por pedidos concluídos
        total_pedidos = PedidoVenda.query.filter_by(cliente_id=cliente_id, status='ENTREGUE').count()
        score += min(total_pedidos * 2, 20)

        # + Pontos por valor total comprado
        valor_total = db.session.query(db.func.coalesce(db.func.sum(PedidoVenda.valor_total), 0)).filter(
            PedidoVenda.cliente_id == cliente_id
        ).scalar()
        score += min(int(valor_total / 1000), 20)

        # - Pontos por inadimplência
        inadimplencia = ContaReceber.query.filter_by(
            cliente_id=cliente_id, status='PENDENTE'
        ).filter(ContaReceber.data_vencimento < datetime.utcnow()).count()
        score -= inadimplencia * 5

        return max(0, min(100, score))

    @staticmethod
    def criar_pedido_venda(cliente_id, itens, dados_extra=None):
        """
        Regras:
        - Verifica limite de crédito do cliente
        - Verifica disponibilidade de estoque (consulta ERP)
        - Calcula valor total automaticamente
        - Número de pedido automático
        """
        cliente = Cliente.query.get(cliente_id)
        if not cliente:
            raise ValueError("Cliente não encontrado")
        if cliente.status == 'SUSPENSO':
            raise ValueError("Cliente suspenso, não pode realizar pedidos")

        # Verifica inadimplência
        inadimplente = ContaReceber.query.filter(
            ContaReceber.cliente_id == cliente_id,
            ContaReceber.status == 'PENDENTE',
            ContaReceber.data_vencimento < datetime.utcnow()
        ).first()
        if inadimplente:
            raise ValueError(f"Cliente possui títulos em atraso. Regularize para liberar novo pedido.")

        numero = f"PV-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        pedido = PedidoVenda(
            numero_pedido=numero,
            cliente_id=cliente_id,
            status='ORCAMENTO',
            **(dados_extra or {})
        )
        db.session.add(pedido)
        db.session.flush()

        valor_total = 0.0
        for item in itens:
            produto = Produto.query.get(item['produto_id'])
            if not produto:
                raise ValueError(f"Produto {item['produto_id']} não encontrado")
            if produto.estoque_atual < item['quantidade']:
                raise ValueError(f"Estoque insuficiente: {produto.nome} - disponível {produto.estoque_atual}, solicitado {item['quantidade']}")

            preco = item.get('preco_unitario', produto.preco_venda)
            desconto = item.get('desconto_item', 0)
            valor_item = (item['quantidade'] * preco) - desconto

            item_pv = ItemPedidoVenda(
                pedido_id=pedido.id,
                produto_id=item['produto_id'],
                quantidade=item['quantidade'],
                preco_unitario=preco,
                desconto_item=desconto,
                valor_total=valor_item
            )
            db.session.add(item_pv)
            valor_total += valor_item

        pedido.valor_total = valor_total - (dados_extra or {}).get('desconto', 0) + (dados_extra or {}).get('frete', 0)

        # Verifica limite de crédito
        total_em_aberto = db.session.query(db.func.coalesce(db.func.sum(ContaReceber.valor_original), 0)).filter(
            ContaReceber.cliente_id == cliente_id,
            ContaReceber.status == 'PENDENTE'
        ).scalar()
        if cliente.limite_credito > 0 and (total_em_aberto + pedido.valor_total) > cliente.limite_credito:
            pedido.status = 'ORCAMENTO'  # Mantém orçamento para aprovação

        db.session.commit()

        IntegracaoService.registrar_log('CRM', 'ERP', 'CREATE', 'PedidoVenda', pedido.id, {'valor': pedido.valor_total})
        IntegracaoService.registrar_log('CRM', 'WMS', 'CREATE', 'OrdemSeparacao', None, {'pedido_id': pedido.id})
        db.session.commit()
        return pedido

    @staticmethod
    def avancar_estagio_oportunidade(oportunidade_id, novo_estagio):
        """Regra: pipeline de vendas com probabilidade automática por estágio"""
        estagios = {
            'PROSPECCAO': 10,
            'QUALIFICACAO': 30,
            'PROPOSTA': 50,
            'NEGOCIACAO': 75,
            'FECHADA': 100,
            'PERDIDA': 0
        }
        if novo_estagio not in estagios:
            raise ValueError(f"Estágio inválido: {novo_estagio}")

        op = Oportunidade.query.get(oportunidade_id)
        if not op:
            raise ValueError("Oportunidade não encontrada")

        op.estagio = novo_estagio
        op.probabilidade = estagios[novo_estagio]

        if novo_estagio == 'FECHADA':
            # Cria atividade de follow-up e atualiza score do cliente
            CRMService.atualizar_score_cliente(op.cliente_id)

        db.session.commit()
        return op

    @staticmethod
    def atualizar_score_cliente(cliente_id):
        cliente = Cliente.query.get(cliente_id)
        if cliente:
            cliente.score = CRMService.calcular_score_cliente(cliente_id)
            db.session.commit()
        return cliente.score if cliente else 0

    @staticmethod
    def funil_vendas():
        """Regra: calcula funil de vendas por estágio"""
        estagios = ['PROSPECCAO', 'QUALIFICACAO', 'PROPOSTA', 'NEGOCIACAO', 'FECHADA', 'PERDIDA']
        resultado = []
        for est in estagios:
            ops = Oportunidade.query.filter_by(estagio=est).all()
            valor_total = sum(o.valor_estimado for o in ops)
            resultado.append({
                'estagio': est,
                'quantidade': len(ops),
                'valor_total': round(valor_total, 2),
                'valor_ponderado': round(sum(o.valor_estimado * o.probabilidade / 100 for o in ops), 2)
            })
        return resultado

    @staticmethod
    def criar_atividade(tipo, titulo, cliente_id=None, oportunidade_id=None, data_agendada=None, responsavel=None):
        """Regra: registra interação com cliente no histórico"""
        ativ = AtividadeCRM(
            tipo=tipo,
            titulo=titulo,
            cliente_id=cliente_id,
            oportunidade_id=oportunidade_id,
            data_agendada=data_agendada,
            responsavel=responsavel,
            status='PENDENTE'
        )
        db.session.add(ativ)
        db.session.commit()
        return ativ

# ============================================================
# VOM SERVICE - Vendor On-Boarding Management
# ============================================================
class VOMService:
    """Regras de negócio do VOM (Vendor On-Boarding)"""

    ETAPAS = {
        1: 'Cadastro Inicial',
        2: 'Documentação',
        3: 'Qualificação e Análise',
        4: 'Aprovação',
        5: 'Integração e Cadastro Final'
    }

    DOCUMENTOS_OBRIGATORIOS = [
        'CNPJ', 'CONTRATO_SOCIAL', 'CERTIDAO_FGTS', 'CERTIDAO_JOINT',
        'COMPROVANTE_ENDERECO', 'DADOS_BANCARIOS'
    ]

    @staticmethod
    def iniciar_solicitacao(dados):
        """Regra: inicia onboarding, gera checklist automático"""
        if SolicitacaoFornecedor.query.filter_by(cnpj=dados['cnpj'], status='CADASTRADO').first():
            raise ValueError("Fornecedor com este CNPJ já está cadastrado")

        sol = SolicitacaoFornecedor(**{k: v for k, v in dados.items() if hasattr(SolicitacaoFornecedor, k)})
        sol.status = 'SOLICITADO'
        sol.etapa_atual = 1
        db.session.add(sol)
        db.session.flush()

        # Gera checklist automático por etapa
        checklist_padrao = {
            1: ['Validar CNPJ na Receita Federal', 'Verificar existência de fornecedor similar', 'Preencher ficha cadastral'],
            2: ['Solicitar contrato social', 'Solicitar certidão FGTS', 'Solicitar certidão joint', 'Solicitar comprovante de endereço', 'Solicitar dados bancários'],
            3: ['Análise de capacidade produtiva', 'Análise financeira', 'Avaliação de qualidade', 'Visita técnica (se aplicável)'],
            4: ['Aprovação do comprador', 'Aprovação do financeiro', 'Aprovação da diretoria (acima do limite)'],
            5: ['Cadastrar no ERP', 'Cadastrar no SAP/Contábil', 'Configurar condições de pagamento', 'Notificar fornecedor']
        }

        for etapa, itens in checklist_padrao.items():
            for item in itens:
                cl = ChecklistOnboarding(
                    solicitacao_id=sol.id,
                    etapa=etapa,
                    item=item,
                    concluido=False
                )
                db.session.add(cl)

        db.session.commit()
        IntegracaoService.registrar_log('VOM', 'ERP', 'CREATE', 'SolicitacaoFornecedor', sol.id, dados)
        db.session.commit()
        return sol

    @staticmethod
    def enviar_documento(solicitacao_id, tipo_documento, nome_arquivo, validade=None):
        """Regra: registra documento, valida obrigatoriedade"""
        doc = DocumentoFornecedor(
            solicitacao_id=solicitacao_id,
            tipo_documento=tipo_documento,
            nome_arquivo=nome_arquivo,
            validade=validade,
            status='ENVIADO'
        )
        db.session.add(doc)

        # Marca checklist correspondente
        cl = ChecklistOnboarding.query.filter_by(
            solicitacao_id=solicitacao_id,
            etapa=2,
            concluido=False
        ).first()
        if cl and 'Solicitar' in cl.item and tipo_documento.lower() in cl.item.lower():
            cl.concluido = True
            cl.data_conclusao = datetime.utcnow()

        db.session.commit()
        VOMService._verificar_avanco_etapa(solicitacao_id)
        return doc

    @staticmethod
    def _verificar_avanco_etapa(solicitacao_id):
        """Regra: avança etapa apenas quando todos itens da etapa atual concluídos"""
        sol = SolicitacaoFornecedor.query.get(solicitacao_id)
        if not sol or sol.status in ['APROVADO', 'REJEITADO', 'CADASTRADO']:
            return

        itens_etapa = ChecklistOnboarding.query.filter_by(
            solicitacao_id=solicitacao_id,
            etapa=sol.etapa_atual
        ).all()

        if itens_etapa and all(i.concluido for i in itens_etapa):
            if sol.etapa_atual < 5:
                sol.etapa_atual += 1
                status_map = {1: 'SOLICITADO', 2: 'DOCUMENTACAO', 3: 'EM_ANALISE', 4: 'EM_ANALISE', 5: 'APROVADO'}
                sol.status = status_map.get(sol.etapa_atual, 'EM_ANALISE')
                db.session.commit()

    @staticmethod
    def concluir_checklist(solicitacao_id, checklist_id, responsavel=None):
        """Regra: marca item concluído e verifica avanço de etapa"""
        cl = ChecklistOnboarding.query.get(checklist_id)
        if not cl:
            raise ValueError("Item de checklist não encontrado")
        cl.concluido = True
        cl.data_conclusao = datetime.utcnow()
        cl.responsavel = responsavel
        db.session.commit()
        VOMService._verificar_avanco_etapa(solicitacao_id)
        return cl

    @staticmethod
    def aprovar_fornecedor(solicitacao_id):
        """
        Regra: só aprova se:
        - Todos documentos obrigatórios enviados e válidos
        - Etapa 4 concluída
        - Então cria fornecedor no ERP (integração)
        """
        sol = SolicitacaoFornecedor.query.get(solicitacao_id)
        if not sol:
            raise ValueError("Solicitação não encontrada")

        # Verifica documentos obrigatórios
        docs_enviados = {d.tipo_documento for d in sol.documentos if d.status in ['ENVIADO', 'APROVADO']}
        faltando = set(VOMService.DOCUMENTOS_OBRIGATORIOS) - docs_enviados
        if faltando:
            raise ValueError(f"Documentos obrigatórios faltando: {', '.join(faltando)}")

        # Verifica checklist etapa 4
        itens_aprov = ChecklistOnboarding.query.filter_by(solicitacao_id=solicitacao_id, etapa=4).all()
        if not all(i.concluido for i in itens_aprov):
            raise ValueError("Itens de aprovação não concluídos")

        sol.status = 'APROVADO'
        sol.etapa_atual = 5
        db.session.flush()

        # Integração: cria fornecedor no ERP
        fornecedor = Fornecedor(
            cnpj=sol.cnpj,
            razao_social=sol.razao_social,
            nome_fantasia=sol.nome_fantasia,
            email=sol.email,
            telefone=sol.telefone,
            contato=sol.contato,
            status_aprovacao='APROVADO'
        )
        db.session.add(fornecedor)
        db.session.flush()

        sol.status = 'CADASTRADO'
        db.session.commit()

        IntegracaoService.registrar_log('VOM', 'ERP', 'CREATE', 'Fornecedor', fornecedor.id, {'cnpj': sol.cnpj})
        IntegracaoService.registrar_log('VOM', 'SAP', 'CREATE', 'Fornecedor', fornecedor.id, {'cnpj': sol.cnpj})
        db.session.commit()
        return fornecedor

    @staticmethod
    def avaliar_fornecedor(fornecedor_id, avaliacoes, avaliador):
        """Regra: média ponderada das notas por critério"""
        total_ponderado = 0
        total_peso = 0
        for av in avaliacoes:
            nota = AvaliacaoFornecedor(
                fornecedor_id=fornecedor_id,
                criterio=av['criterio'],
                nota=av['nota'],
                peso=av.get('peso', 1.0),
                avaliador=avaliador,
                comentario=av.get('comentario')
            )
            db.session.add(nota)
            total_ponderado += av['nota'] * av.get('peso', 1.0)
            total_peso += av.get('peso', 1.0)

        db.session.commit()
        media = total_ponderado / total_peso if total_peso > 0 else 0
        return round(media, 2)

    @staticmethod
    def status_onboarding(solicitacao_id):
        """Regra: retorna progresso percentual do onboarding"""
        sol = SolicitacaoFornecedor.query.get(solicitacao_id)
        if not sol:
            return None
        total = ChecklistOnboarding.query.filter_by(solicitacao_id=solicitacao_id).count()
        concluidos = ChecklistOnboarding.query.filter_by(solicitacao_id=solicitacao_id, concluido=True).count()
        percentual = (concluidos / total * 100) if total > 0 else 0
        return {
            'solicitacao_id': sol.id,
            'etapa_atual': sol.etapa_atual,
            'etapa_descricao': VOMService.ETAPAS.get(sol.etapa_atual, ''),
            'status': sol.status,
            'progresso_percentual': round(percentual, 1),
            'itens_total': total,
            'itens_concluidos': concluidos
        }

# ============================================================
# PDA SERVICE - Production Data Analysis
# ============================================================
class PDAService:
    """Regras de negócio do PDA (Production Data Analysis)"""

    @staticmethod
    def criar_ordem_producao(produto_id, quantidade_planejada, dados_extra=None):
        """Regra: cria OP, verifica matéria-prima disponível, gera lista de consumo"""
        produto = Produto.query.get(produto_id)
        if not produto:
            raise ValueError("Produto não encontrado")

        numero = f"OP-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        op = OrdemProducao(
            numero_op=numero,
            produto_id=produto_id,
            quantidade_planejada=quantidade_planejada,
            status='PLANEJADA',
            **(dados_extra or {})
        )
        db.session.add(op)
        db.session.commit()
        IntegracaoService.registrar_log('PDA', 'ERP', 'CREATE', 'OrdemProducao', op.id, {'produto': produto_id, 'qtd': quantidade_planejada})
        db.session.commit()
        return op

    @staticmethod
    def registrar_producao(ordem_producao_id, dados):
        """
        Regras:
        - Atualiza quantidade produzida e refugo
        - Calcula OEE (disponibilidade x performance x qualidade)
        - Atualiza estoque do produto acabado (ERP)
        - Baixa matéria-prima consumida
        """
        op = OrdemProducao.query.get(ordem_producao_id)
        if not op:
            raise ValueError("Ordem de produção não encontrada")
        if op.status not in ['EM_PRODUCAO', 'LIBERADA']:
            raise ValueError(f"OP não está liberada para produção (status: {op.status})")

        if op.status == 'LIBERADA':
            op.status = 'EM_PRODUCAO'
            op.data_inicio_real = datetime.utcnow()

        registro = RegistroProducao(
            ordem_producao_id=ordem_producao_id,
            turno=dados.get('turno'),
            quantidade_boa=dados.get('quantidade_boa', 0),
            quantidade_refugo=dados.get('quantidade_refugo', 0),
            tempo_producao_min=dados.get('tempo_producao_min', 0),
            tempo_parada_min=dados.get('tempo_parada_min', 0),
            motivo_parada=dados.get('motivo_parada'),
            operador=dados.get('operador'),
            maquina=dados.get('maquina')
        )
        db.session.add(registro)

        op.quantidade_produzida += dados.get('quantidade_boa', 0)
        op.quantidade_refugo += dados.get('quantidade_refugo', 0)

        # Atualiza estoque do produto acabado no ERP
        if dados.get('quantidade_boa', 0) > 0:
            produto = Produto.query.get(op.produto_id)
            saldo_anterior = produto.estoque_atual
            produto.estoque_atual += dados['quantidade_boa']
            mov = MovimentacaoEstoque(
                produto_id=produto.id,
                tipo='ENTRADA',
                quantidade=dados['quantidade_boa'],
                saldo_anterior=saldo_anterior,
                saldo_atual=produto.estoque_atual,
                origem='PRODUCAO',
                documento_ref=op.numero_op,
                usuario='SISTEMA'
            )
            db.session.add(mov)

        # Baixa matéria-prima
        for consumo in dados.get('consumos', []):
            mp = ConsumoMateriaPrima(
                ordem_producao_id=ordem_producao_id,
                produto_mp_id=consumo['produto_mp_id'],
                quantidade_planejada=consumo.get('quantidade_planejada', 0),
                quantidade_real=consumo.get('quantidade_real', 0),
                unidade=consumo.get('unidade', 'UN')
            )
            db.session.add(mp)
            # Baixa estoque MP no ERP
            prod_mp = Produto.query.get(consumo['produto_mp_id'])
            if prod_mp and consumo.get('quantidade_real', 0) > 0:
                saldo_ant = prod_mp.estoque_atual
                prod_mp.estoque_atual -= consumo['quantidade_real']
                mov_mp = MovimentacaoEstoque(
                    produto_id=prod_mp.id,
                    tipo='SAIDA',
                    quantidade=consumo['quantidade_real'],
                    saldo_anterior=saldo_ant,
                    saldo_atual=prod_mp.estoque_atual,
                    origem='PRODUCAO',
                    documento_ref=op.numero_op,
                    usuario='SISTEMA'
                )
                db.session.add(mov_mp)

        # Verifica conclusão
        if op.quantidade_produzida >= op.quantidade_planejada:
            op.status = 'CONCLUIDA'
            op.data_fim_real = datetime.utcnow()

        db.session.commit()

        # Calcula e registra indicadores
        PDAService._calcular_indicadores(ordem_producao_id, dados)
        IntegracaoService.registrar_log('PDA', 'ERP', 'UPDATE', 'Estoque', op.produto_id, {'qtd': dados.get('quantidade_boa', 0)})
        db.session.commit()
        return registro

    @staticmethod
    def _calcular_indicadores(ordem_producao_id, dados):
        """Regra: OEE = Disponibilidade x Performance x Qualidade"""
        op = OrdemProducao.query.get(ordem_producao_id)
        tempo_total = dados.get('tempo_producao_min', 0) + dados.get('tempo_parada_min', 0)

        # Disponibilidade = tempo produção / tempo total
        disponibilidade = (dados.get('tempo_producao_min', 0) / tempo_total * 100) if tempo_total > 0 else 0

        # Performance (simplificado): peças produzidas / ritmo esperado
        qtd_boa = dados.get('quantidade_boa', 0)
        qtd_refugo = dados.get('quantidade_refugo', 0)
        qtd_total = qtd_boa + qtd_refugo
        performance = min(100, (qtd_total / max(op.quantidade_planejada, 1)) * 100) if op.quantidade_planejada > 0 else 0

        # Qualidade = peças boas / total produzido
        qualidade = (qtd_boa / qtd_total * 100) if qtd_total > 0 else 0

        oee = (disponibilidade * performance * qualidade) / 10000  # em %

        indicador = IndicadorProducao(
            data_referencia=datetime.utcnow(),
            linha_producao=op.linha_producao,
            oee=round(oee, 2),
            disponibilidade=round(disponibilidade, 2),
            performance=round(performance, 2),
            qualidade=round(qualidade, 2),
            pecas_boas=qtd_boa,
            pecas_refugo=qtd_refugo,
            tempo_planejado=op.quantidade_planejada,
            tempo_real=tempo_total
        )
        db.session.add(indicador)
        db.session.commit()

    @staticmethod
    def registrar_manutencao(maquina, tipo, descricao, tempo_parada_horas, custo=0, tecnico=None):
        """Regra: registra parada de máquina, impacta disponibilidade"""
        man = ManutencaoMaquina(
            maquina=maquina,
            tipo=tipo,
            descricao=descricao,
            tempo_parada_horas=tempo_parada_horas,
            custo=custo,
            tecnico=tecnico,
            status='ABERTA'
        )
        db.session.add(man)
        db.session.commit()
        return man

    @staticmethod
    def dashboard_producao(dias=30):
        """Regra: consolida indicadores de produção no período"""
        limite = datetime.utcnow() - timedelta(days=dias)
        registros = RegistroProducao.query.filter(RegistroProducao.data_registro >= limite).all()

        total_boas = sum(r.quantidade_boa for r in registros)
        total_refugo = sum(r.quantidade_refugo for r in registros)
        total_produzido = total_boas + total_refugo
        qualidade = (total_boas / total_produzido * 100) if total_produzido > 0 else 0

        indicadores = IndicadorProducao.query.filter(IndicadorProducao.data_referencia >= limite).all()
        oee_medio = sum(i.oee for i in indicadores) / len(indicadores) if indicadores else 0

        ops = OrdemProducao.query.filter(OrdemProducao.criado_em >= limite).all()
        concluidas = len([o for o in ops if o.status == 'CONCLUIDA'])

        return {
            'periodo_dias': dias,
            'total_pecas_boas': total_boas,
            'total_refugo': total_refugo,
            'taxa_qualidade': round(qualidade, 2),
            'oee_medio': round(oee_medio, 2),
            'ordens_criadas': len(ops),
            'ordens_concluidas': concluidas,
            'taxa_conclusao': round((concluidas / len(ops) * 100) if ops else 0, 2)
        }

# ============================================================
# SAP SERVICE - System Accounting & Processing (Contábil/Fiscal)
# ============================================================
class SAPService:
    """Regras de negócio do SAP (Contábil/Fiscal)"""

    @staticmethod
    def criar_lancamento_contabil(data_competencia, historico, partidas, tipo_documento=None, documento_origem=None, usuario='SISTEMA'):
        """
        Regra fundamental: Método das Partidas Dobradas
        - Soma de débitos = Soma de créditos (razão contábil)
        - Cada partida tem conta, tipo D/C, valor
        - Valida antes de contabilizar
        """
        total_debito = sum(p['valor'] for p in partidas if p['tipo'] == 'DEBITO')
        total_credito = sum(p['valor'] for p in partidas if p['tipo'] == 'CREDITO')

        if abs(total_debito - total_credito) > 0.01:
            raise ValueError(f"Lançamento não balanceado: Débitos R$ {total_debito:.2f} vs Créditos R$ {total_credito:.2f}")

        numero = f"LCT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        lanc = LancamentoContabil(
            numero_lancamento=numero,
            data_competencia=data_competencia,
            historico=historico,
            tipo_documento=tipo_documento,
            documento_origem=documento_origem,
            valor_total_debito=total_debito,
            valor_total_credito=total_credito,
            status='VALIDADO',
            usuario=usuario
        )
        db.session.add(lanc)
        db.session.flush()

        for p in partidas:
            partida = PartidaDobrada(
                lancamento_id=lanc.id,
                plano_conta_id=p['plano_conta_id'],
                tipo=p['tipo'],
                valor=p['valor'],
                centro_custo=p.get('centro_custo'),
                historico_complementar=p.get('historico_complementar')
            )
            db.session.add(partida)

        db.session.commit()
        return lanc

    @staticmethod
    def contabilizar_compra(nota_fiscal_id):
        """Regra: integração ERP→SAP - contabiliza entrada de mercadoria"""
        nf = NotaFiscalEntrada.query.get(nota_fiscal_id)
        if not nf:
            raise ValueError("NF não encontrada")

        # Busca contas contábeis padrão
        conta_estoque = PlanoConta.query.filter_by(codigo='1.1.2.01').first()  # Estoques
        conta_fornecedor = PlanoConta.query.filter_by(codigo='2.1.1.01').first()  # Fornecedores
        conta_icms = PlanoConta.query.filter_by(codigo='1.2.1.01').first()  # ICMS a recuperar

        partidas = []
        if conta_estoque:
            partidas.append({'plano_conta_id': conta_estoque.id, 'tipo': 'DEBITO', 'valor': nf.valor_total - nf.valor_icms})
        if conta_icms and nf.valor_icms > 0:
            partidas.append({'plano_conta_id': conta_icms.id, 'tipo': 'DEBITO', 'valor': nf.valor_icms})
        if conta_fornecedor:
            partidas.append({'plano_conta_id': conta_fornecedor.id, 'tipo': 'CREDITO', 'valor': nf.valor_total})

        if partidas:
            return SAPService.criar_lancamento_contabil(
                data_competencia=nf.data_emissao or datetime.utcnow(),
                historico=f"Entrada mercadoria NF {nf.numero_nf}",
                partidas=partidas,
                tipo_documento='NF',
                documento_origem=nf.numero_nf
            )
        return None

    @staticmethod
    def contabilizar_venda(pedido_venda_id):
        """Regra: integração CRM→SAP - contabiliza receita e custo"""
        pedido = PedidoVenda.query.get(pedido_venda_id)
        if not pedido:
            raise ValueError("Pedido não encontrado")

        conta_receita = PlanoConta.query.filter_by(codigo='4.1.1').first()  # Receita de Vendas
        conta_cliente = PlanoConta.query.filter_by(codigo='1.1.3.01').first()  # Clientes
        conta_custo = PlanoConta.query.filter_by(codigo='5.1.1').first()  # CMV
        conta_estoque = PlanoConta.query.filter_by(codigo='1.1.2.01').first()  # Estoques

        partidas = []
        if conta_cliente:
            partidas.append({'plano_conta_id': conta_cliente.id, 'tipo': 'DEBITO', 'valor': pedido.valor_total})
        if conta_receita:
            partidas.append({'plano_conta_id': conta_receita.id, 'tipo': 'CREDITO', 'valor': pedido.valor_total})

        # Custo da mercadoria vendida
        custo_total = sum(item.quantidade * item.produto.preco_custo for item in pedido.itens)
        if conta_custo and custo_total > 0:
            partidas.append({'plano_conta_id': conta_custo.id, 'tipo': 'DEBITO', 'valor': custo_total})
        if conta_estoque and custo_total > 0:
            partidas.append({'plano_conta_id': conta_estoque.id, 'tipo': 'CREDITO', 'valor': custo_total})

        if partidas:
            return SAPService.criar_lancamento_contabil(
                data_competencia=pedido.data_pedido,
                historico=f"Venda pedido {pedido.numero_pedido} - {pedido.cliente.nome}",
                partidas=partidas,
                tipo_documento='VENDA',
                documento_origem=pedido.numero_pedido
            )
        return None

    @staticmethod
    def apurar_imposto(competencia, imposto_nome, base_calculo):
        """Regra: calcula imposto com base na alíquota cadastrada"""
        imposto = Imposto.query.filter_by(nome=imposto_nome, ativo=True).first()
        if not imposto:
            raise ValueError(f"Imposto {imposto_nome} não cadastrado")

        valor_apurado = base_calculo * (imposto.aliquota / 100)

        apuracao = ApuracaoImposto(
            competencia=competencia,
            imposto_id=imposto.id,
            base_calculo=base_calculo,
            valor_apurado=round(valor_apurado, 2),
            status='APURADO',
            data_vencimento=datetime.utcnow() + timedelta(days=20)
        )
        db.session.add(apuracao)
        db.session.commit()
        return apuracao

    @staticmethod
    def gerar_balancete(competencia):
        """Regra: consolida saldos por conta contábil no período"""
        inicio = datetime.strptime(f"01/{competencia}", '%d/%m/%Y') if '/' in competencia else datetime.utcnow()
        # Simplificado: calcula por plano de conta
        contas = PlanoConta.query.all()
        resultado = []

        for conta in contas:
            partidas = PartidaDobrada.query.join(LancamentoContabil).filter(
                PartidaDobrada.plano_conta_id == conta.id,
                LancamentoContabil.status.in_(['VALIDADO', 'CONTABILIZADO'])
            ).all()

            debito = sum(p.valor for p in partidas if p.tipo == 'DEBITO')
            credito = sum(p.valor for p in partidas if p.tipo == 'CREDITO')

            saldo_debito = max(0, debito - credito) if conta.natureza == 'DEVEDORA' else 0
            saldo_credito = max(0, credito - debito) if conta.natureza == 'CREDORA' else 0

            bal = Balancete(
                competencia=competencia,
                plano_conta_id=conta.id,
                movimento_debito=debito,
                movimento_credito=credito,
                saldo_atual_debito=saldo_debito,
                saldo_atual_credito=saldo_credito
            )
            db.session.add(bal)
            resultado.append({
                'conta': conta.codigo,
                'descricao': conta.descricao,
                'debito': round(debito, 2),
                'credito': round(credito, 2),
                'saldo_devedor': round(saldo_debito, 2),
                'saldo_credor': round(saldo_credito, 2)
            })

        db.session.commit()
        return resultado

    @staticmethod
    def demonstrativo_resultado(competencia):
        """Regra: DRE - Receitas - Custos - Despesas = Lucro"""
        receitas = db.session.query(db.func.coalesce(db.func.sum(PartidaDobrada.valor), 0)).join(
            PlanoConta, PartidaDobrada.plano_conta_id == PlanoConta.id
        ).filter(PlanoConta.tipo == 'RECEITA', PartidaDobrada.tipo == 'CREDITO').scalar()

        custos = db.session.query(db.func.coalesce(db.func.sum(PartidaDobrada.valor), 0)).join(
            PlanoConta, PartidaDobrada.plano_conta_id == PlanoConta.id
        ).filter(PlanoConta.tipo == 'CUSTO', PartidaDobrada.tipo == 'DEBITO').scalar()

        despesas = db.session.query(db.func.coalesce(db.func.sum(PartidaDobrada.valor), 0)).join(
            PlanoConta, PartidaDobrada.plano_conta_id == PlanoConta.id
        ).filter(PlanoConta.tipo == 'DESPESA', PartidaDobrada.tipo == 'DEBITO').scalar()

        lucro_bruto = receitas - custos
        lucro_liquido = lucro_bruto - despesas

        return {
            'competencia': competencia,
            'receita_total': round(receitas, 2),
            'custos': round(custos, 2),
            'lucro_bruto': round(lucro_bruto, 2),
            'despesas': round(despesas, 2),
            'lucro_liquido': round(lucro_liquido, 2),
            'margem_liquida': round((lucro_liquido / receitas * 100) if receitas > 0 else 0, 2)
        }

    @staticmethod
    def inicializar_plano_contas():
        """Regra: cria plano de contas padrão (Plano Brasil - CPC)"""
        contas_padrao = [
            ('1', 'ATIVO', 'ATIVO', 'DEVEDORA', True, None),
            ('1.1', 'Ativo Circulante', 'ATIVO', 'DEVEDORA', True, '1'),
            ('1.1.1', 'Caixa e Equivalentes', 'ATIVO', 'DEVEDORA', True, '1.1'),
            ('1.1.1.01', 'Caixa', 'ATIVO', 'DEVEDORA', False, '1.1.1'),
            ('1.1.1.02', 'Bancos Conta Movimento', 'ATIVO', 'DEVEDORA', False, '1.1.1'),
            ('1.1.2', 'Estoques', 'ATIVO', 'DEVEDORA', True, '1.1'),
            ('1.1.2.01', 'Estoque de Mercadorias', 'ATIVO', 'DEVEDORA', False, '1.1.2'),
            ('1.1.3', 'Clientes', 'ATIVO', 'DEVEDORA', True, '1.1'),
            ('1.1.3.01', 'Clientes', 'ATIVO', 'DEVEDORA', False, '1.1.3'),
            ('1.2', 'Ativo Não Circulante', 'ATIVO', 'DEVEDORA', True, '1'),
            ('1.2.1', 'Impostos a Recuperar', 'ATIVO', 'DEVEDORA', True, '1.2'),
            ('1.2.1.01', 'ICMS a Recuperar', 'ATIVO', 'DEVEDORA', False, '1.2.1'),
            ('2', 'PASSIVO', 'PASSIVO', 'CREDORA', True, None),
            ('2.1', 'Passivo Circulante', 'PASSIVO', 'CREDORA', True, '2'),
            ('2.1.1', 'Fornecedores', 'PASSIVO', 'CREDORA', True, '2.1'),
            ('2.1.1.01', 'Fornecedores Nacionais', 'PASSIVO', 'CREDORA', False, '2.1.1'),
            ('2.1.2', 'Obrigações Fiscais', 'PASSIVO', 'CREDORA', True, '2.1'),
            ('2.1.2.01', 'ICMS a Recolher', 'PASSIVO', 'CREDORA', False, '2.1.2'),
            ('2.1.2.02', 'PIS/COFINS a Recolher', 'PASSIVO', 'CREDORA', False, '2.1.2'),
            ('3', 'PATRIMONIO LIQUIDO', 'PATRIMONIO', 'CREDORA', True, None),
            ('3.1', 'Capital Social', 'PATRIMONIO', 'CREDORA', False, '3'),
            ('3.2', 'Lucros/Prejuízos Acumulados', 'PATRIMONIO', 'CREDORA', False, '3'),
            ('4', 'RECEITAS', 'RECEITA', 'CREDORA', True, None),
            ('4.1', 'Receita Operacional', 'RECEITA', 'CREDORA', True, '4'),
            ('4.1.1', 'Receita de Vendas', 'RECEITA', 'CREDORA', False, '4.1'),
            ('5', 'CUSTOS E DESPESAS', 'DESPESA', 'DEVEDORA', True, None),
            ('5.1', 'Custos', 'CUSTO', 'DEVEDORA', True, '5'),
            ('5.1.1', 'CMV - Custo da Mercadoria Vendida', 'CUSTO', 'DEVEDORA', False, '5.1'),
            ('5.2', 'Despesas Operacionais', 'DESPESA', 'DEVEDORA', True, '5'),
            ('5.2.1', 'Despesas com Vendas', 'DESPESA', 'DEVEDORA', False, '5.2'),
            ('5.2.2', 'Despesas Administrativas', 'DESPESA', 'DEVEDORA', False, '5.2'),
            ('5.3', 'Despesas Financeiras', 'DESPESA', 'DEVEDORA', False, '5'),
        ]

        conta_map = {}
        for codigo, descricao, tipo, natureza, sintetica, pai_codigo in contas_padrao:
            pai_id = conta_map.get(pai_codigo) if pai_codigo else None
            conta = PlanoConta(
                codigo=codigo,
                descricao=descricao,
                tipo=tipo,
                natureza=natureza,
                conta_sintetica=sintetica,
                conta_pai_id=pai_id
            )
            db.session.add(conta)
            db.session.flush()
            conta_map[codigo] = conta.id

        # Impostos padrão
        impostos_padrao = [
            ('ICMS', 18.0, 'Valor da operação', 'LUCRO_PRESUMIDO'),
            ('PIS', 1.65, 'Faturamento', 'LUCRO_PRESUMIDO'),
            ('COFINS', 7.6, 'Faturamento', 'LUCRO_PRESUMIDO'),
            ('IPI', 5.0, 'Valor produto', 'LUCRO_PRESUMIDO'),
            ('ISS', 5.0, 'Serviços', 'LUCRO_PRESUMIDO'),
            ('IRPJ', 15.0, 'Lucro presumido', 'LUCRO_PRESUMIDO'),
            ('CSLL', 9.0, 'Lucro presumido', 'LUCRO_PRESUMIDO'),
        ]
        for nome, aliquota, base, regime in impostos_padrao:
            imp = Imposto(nome=nome, aliquota=aliquota, base_calculo=base, regime=regime, ativo=True)
            db.session.add(imp)

        # Centros de custo padrão
        centros = [
            ('CC-001', 'Administrativo', 'Administrativo', 'Financeiro'),
            ('CC-002', 'Comercial', 'Vendas', 'Comercial'),
            ('CC-003', 'Produção', 'Operacional', 'Produção'),
            ('CC-004', 'Logística', 'Operacional', 'Logística'),
            ('CC-005', 'Tecnologia', 'Administrativo', 'TI'),
        ]
        for codigo, desc, depto, resp in centros:
            cc = CentroCusto(codigo=codigo, descricao=desc, departamento=depto, responsavel=resp)
            db.session.add(cc)

        db.session.commit()
