# -*- coding: utf-8 -*-
"""
Sistema Integrado de Gestão
Módulos: ERP, WMS, CRM, VOM, PDA, SAP
Aplicação Principal Flask
"""
import os
from dotenv import load_dotenv
from flask import Flask, render_template, jsonify
from flask_cors import CORS
from models import db
from routes import erp_bp, wms_bp, crm_bp, vom_bp, pda_bp, sap_bp, int_bp

# Carrega variáveis de ambiente do arquivo .env (ex: DATABASE_URL do Supabase)
load_dotenv()

def get_database_uri():
    """Retorna a URI do banco. Prioriza Supabase (DATABASE_URL), senão usa SQLite local."""
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Supabase às vezes fornece 'postgres://' — SQLAlchemy com psycopg2 exige 'postgresql://'
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        return database_url
    # Fallback: SQLite local (se não configurar o Supabase)
    basedir = os.path.abspath(os.path.dirname(__file__))
    return 'sqlite:///' + os.path.join(basedir, 'instance', 'sistema_gestao.db')

def create_app():
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    CORS(app)

    # Garante que o diretório do SQLite exista também após clone/deploy via Git,
    # pois diretórios vazios não são preservados pelo Git.
    instance_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance')
    os.makedirs(instance_dir, exist_ok=True)

    # Configuração do banco de dados (PostgreSQL/Supabase ou SQLite local).
    database_uri = get_database_uri()
    app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # Opções de pool do PostgreSQL; manter configuração simples para SQLite local.
    if database_uri.startswith(('postgresql://', 'postgresql+')):
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_size': 5,
            'max_overflow': 10,
            'pool_pre_ping': True
        }
    app.config['JSON_AS_ASCII'] = False

    db.init_app(app)

    # Registra blueprints
    app.register_blueprint(erp_bp)
    app.register_blueprint(wms_bp)
    app.register_blueprint(crm_bp)
    app.register_blueprint(vom_bp)
    app.register_blueprint(pda_bp)
    app.register_blueprint(sap_bp)
    app.register_blueprint(int_bp)

    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    @app.route('/health')
    def health():
        db_type = 'Supabase (PostgreSQL)' if os.environ.get('DATABASE_URL') else 'SQLite (local)'
        return jsonify({'status': 'OK', 'sistema': 'Sistema Integrado de Gestão', 'banco': db_type, 'modulos': ['ERP', 'WMS', 'CRM', 'VOM', 'PDA', 'SAP']})

    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == '__main__':
    # Render (e outras plataformas) injetam a variável PORT — use-a, senão 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
