import sys
import logging
import io
import os
import shutil
import click # Importante para inputs no terminal
from flask import Flask, request, jsonify, render_template, make_response, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from datetime import datetime

# Importa a lógica de PDF (que agora espera uma lista unificada e o tipo de relatório)
from pdf_generator import gerar_pdf_com_anexos
from config import Config
from models import db, User, Project, Attachment

# Configuração de Logs
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

app = Flask(__name__)

# ------------------------------------------------------------------
# --- CONFIGURAÇÃO DO BANCO DE DADOS E LOGIN ---
# ------------------------------------------------------------------
app.config.from_object(Config)

# Inicializa o SQLAlchemy
db.init_app(app)

# Inicializa o Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça login para acessar o sistema."

@login_manager.user_loader
def load_user(user_id):
    # Correção: db.session.get para evitar LegacyAPIWarning
    return db.session.get(User, int(user_id))

# ------------------------------------------------------------------
# --- ROTAS DE AUTENTICAÇÃO E PERFIL ---
# ------------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Usuário ou senha inválidos.')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/api/update_profile', methods=['POST'])
@login_required
def update_profile():
    """
    Rota para alterar e-mail e senha do usuário logado.
    """
    try:
        data = request.json
        new_email = data.get('email')
        new_password = data.get('new_password')

        user = current_user

        # 1. Atualiza E-mail se fornecido e diferente
        if new_email and new_email != user.email:
            # Verifica se o email já existe em outro usuário
            existing_user = User.query.filter_by(email=new_email).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({"error": "Este e-mail já está em uso."}), 400
            user.email = new_email

        # 2. Atualiza Senha se fornecida
        if new_password:
            # Gera o hash da nova senha e salva
            user.password_hash = generate_password_hash(new_password)

        db.session.commit()
        return jsonify({"message": "Perfil atualizado com sucesso!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ------------------------------------------------------------------
# --- ROTAS DE NAVEGAÇÃO (FRONTEND) ---
# ------------------------------------------------------------------

@app.route('/', methods=['GET'])
@login_required 
def home():
    # Rota principal agora carrega a Fase 1 (Negócio)
    return render_template('fase_1.html', user=current_user)

@app.route('/fase2', methods=['GET'])
@login_required
def fase_2():
    # Rota para a Fase 2 (Requisitos)
    return render_template('fase_2.html', user=current_user)

@app.route('/fase3', methods=['GET'])
@login_required
def fase_3():
    # Rota para a Fase 3 (Implementação)
    return render_template('fase_3.html', user=current_user)

# ------------------------------------------------------------------
# --- ROTAS DE API (CRUD PROJETOS) ---
# ------------------------------------------------------------------

@app.route('/api/projects', methods=['GET'])
@login_required
def list_projects():
    """
    Lista simples para a sidebar.
    Retorna apenas ID, Nome e Data para leveza.
    """
    try:
        # Busca projetos ordenados por data de atualização
        projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.updated_at.desc()).all()
        
        project_list = []
        for p in projects:
            project_list.append({
                'id': p.id,
                'name': p.name,
                'updated_at': p.updated_at.strftime('%d/%m/%Y %H:%M')
            })
        
        return jsonify(project_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<int:project_id>', methods=['GET'])
@login_required
def get_project(project_id):
    """
    Retorna TODOS os dados do projeto (Fases 1, 2 e 3) para preencher os formulários.
    """
    try:
        # Correção: db.session.get
        project = db.session.get(Project, project_id)
        
        if not project:
            return jsonify({"error": "Projeto não encontrado"}), 404

        if project.user_id != current_user.id:
            return jsonify({"error": "Acesso não autorizado"}), 403
        
        # Recupera os anexos do banco
        attachments_data = []
        for att in project.attachments:
            attachments_data.append({
                'id': att.id,
                'filename': att.filename,
                'size': att.file_size,
                'filetype': att.filetype
            })
            
        return jsonify({
            'id': project.id,
            'name': project.name,
            'responsible': project.responsible,
            
            # --- FASE 1: Negócio ---
            'context': project.context_desc,
            'business_desc': project.business_desc,
            'business_rules': project.business_rules,
            'specialist_desc': project.specialist_desc,
            'things_desc': project.things_desc,
            
            # --- FASE 2: Requisitos (Top-Down) ---
            'req_l6': project.req_l6_display,
            'req_l5': project.req_l5_abstraction,
            'req_l4': project.req_l4_storage,
            'req_l3': project.req_l3_border,
            'req_l2': project.req_l2_connectivity,
            'req_l1': project.req_l1_sensor,

            # --- FASE 3: Implementação (Bottom-Up) ---
            'impl_l1': project.impl_l1_sensor,
            'impl_l2': project.impl_l2_connectivity,
            'impl_l3': project.impl_l3_border,
            'impl_l4': project.impl_l4_storage,
            'impl_l5': project.impl_l5_abstraction,
            'impl_l6': project.impl_l6_display,

            'attachments': attachments_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/save_project', methods=['POST'])
@login_required
def save_project():
    """
    Salva ou atualiza o projeto. 
    Capaz de atualizar parcialmente (apenas os campos enviados no request).
    """
    try:
        data = request.form
        project_id = data.get('project_id')
        uploaded_files = request.files.getlist('anexos') # Geralmente enviado apenas na Fase 1

        # 1. Gerencia Projeto (Insert ou Update)
        if project_id and project_id != 'null' and project_id != '':
            # Update: Busca existente
            project = db.session.get(Project, project_id)
            if not project or project.user_id != current_user.id:
                return jsonify({"error": "Não autorizado"}), 404
            
            msg = "Projeto atualizado com sucesso!"
        else:
            # Insert: Cria novo
            project = Project(user_id=current_user.id)
            # Define nome padrão se não vier no request (embora o frontend valide)
            project.name = data.get('name') or "Novo Projeto"
            db.session.add(project)
            msg = "Projeto criado com sucesso!"

        # Atualiza Metadados (se presentes no request)
        if 'name' in data: 
            project.name = data.get('name')
        if 'responsible' in data: 
            project.responsible = data.get('responsible')
        
        project.updated_at = datetime.utcnow()

        # --- ATUALIZA FASE 1 (Se os campos vierem no request) ---
        if 'context' in data: project.context_desc = data.get('context')
        if 'business_desc' in data: project.business_desc = data.get('business_desc')
        if 'business_rules' in data: project.business_rules = data.get('business_rules')
        if 'specialist_desc' in data: project.specialist_desc = data.get('specialist_desc')
        if 'things_desc' in data: project.things_desc = data.get('things_desc')

        # --- ATUALIZA FASE 2 (Requisitos) ---
        if 'req_l6' in data: project.req_l6_display = data.get('req_l6')
        if 'req_l5' in data: project.req_l5_abstraction = data.get('req_l5')
        if 'req_l4' in data: project.req_l4_storage = data.get('req_l4')
        if 'req_l3' in data: project.req_l3_border = data.get('req_l3')
        if 'req_l2' in data: project.req_l2_connectivity = data.get('req_l2')
        if 'req_l1' in data: project.req_l1_sensor = data.get('req_l1')

        # --- ATUALIZA FASE 3 (Implementação) ---
        if 'impl_l1' in data: project.impl_l1_sensor = data.get('impl_l1')
        if 'impl_l2' in data: project.impl_l2_connectivity = data.get('impl_l2')
        if 'impl_l3' in data: project.impl_l3_border = data.get('impl_l3')
        if 'impl_l4' in data: project.impl_l4_storage = data.get('impl_l4')
        if 'impl_l5' in data: project.impl_l5_abstraction = data.get('impl_l5')
        if 'impl_l6' in data: project.impl_l6_display = data.get('impl_l6')

        db.session.flush() # Garante que o ID do projeto exista antes de salvar anexos

        # 2. Gerencia Arquivos no Disco (Se houver uploads)
        if uploaded_files:
            storage_base = os.path.join(app.root_path, 'storage')
            user_folder = str(current_user.id)
            proj_folder = str(project.id)
            full_save_path = os.path.join(storage_base, user_folder, proj_folder)
            
            if not os.path.exists(full_save_path):
                os.makedirs(full_save_path)

            saved_count = 0
            for file in uploaded_files:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(full_save_path, filename)
                    
                    # Salva no disco
                    file.save(file_path)
                    file_size = os.path.getsize(file_path)
                    
                    # Salva no banco
                    new_attachment = Attachment(
                        project_id=project.id,
                        filename=filename,
                        filepath=file_path,
                        filetype=file.content_type,
                        file_size=file_size
                    )
                    db.session.add(new_attachment)
                    saved_count += 1

        db.session.commit()
        
        return jsonify({
            "message": msg,
            "project_id": project.id,
            "name": project.name
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
@login_required
def delete_project(project_id):
    try:
        project = db.session.get(Project, project_id)
        if not project:
            return jsonify({"error": "Não encontrado"}), 404
            
        if project.user_id != current_user.id:
            return jsonify({"error": "Não autorizado"}), 403

        # Remove arquivos físicos
        storage_base = os.path.join(app.root_path, 'storage')
        project_path = os.path.join(storage_base, str(current_user.id), str(project.id))

        if os.path.exists(project_path):
            try:
                shutil.rmtree(project_path)
                print(f"--- Pasta removida: {project_path}")
            except Exception as e_file:
                print(f"!!! Erro ao remover pasta física: {e_file}")

        # Remove do banco
        db.session.delete(project)
        db.session.commit()

        return jsonify({"message": "Projeto excluído com sucesso."})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/attachments/<int:attachment_id>', methods=['DELETE'])
@login_required
def delete_attachment(attachment_id):
    try:
        attachment = db.session.get(Attachment, attachment_id)
        if not attachment:
            return jsonify({"error": "Anexo não encontrado"}), 404

        if attachment.project.user_id != current_user.id:
             return jsonify({"error": "Não autorizado"}), 403
             
        # Remove arquivo físico
        if os.path.exists(attachment.filepath):
            os.remove(attachment.filepath)
            
        # Remove do banco
        db.session.delete(attachment)
        db.session.commit()
        
        return jsonify({"message": "Anexo removido."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------------------------------------------------------
# --- ROTA DE GERAÇÃO DE RELATÓRIO (PDF) ---
# ------------------------------------------------------------------

@app.route('/api/gerar_relatorio', methods=['POST'])
@login_required 
def handle_gerar_relatorio():
    """
    Rota Controller: Identifica o tipo de relatório (fase1, fase2, fase3),
    prepara os dados e chama o gerador.
    
    REGRA DE NEGÓCIO: Anexos devem ser incluídos APENAS na Fase 1.
    """
    try:
        # Recupera dados do formulário
        data = request.form
        project_id = data.get('project_id')
        tipo_relatorio = data.get('tipo_relatorio', 'fase1') # Padrão fase1
        
        lista_anexos_unificada = []

        print(f"--- Iniciando Geração de PDF ({tipo_relatorio}). Projeto ID: {project_id} ---")

        # LÓGICA DE FILTRO: Só processa anexos se for Fase 1
        if tipo_relatorio == 'fase1':
            print("--- Processando anexos para Fase 1 ---")
            
            # 1. Processa Arquivos NOVOS (Upload na memória)
            uploaded_files = request.files.getlist('anexos')
            for f in uploaded_files:
                if f and f.filename:
                    buf = io.BytesIO()
                    f.save(buf) 
                    buf.seek(0)
                    
                    lista_anexos_unificada.append({
                        'filename': f.filename,
                        'stream': buf,
                        'origem': 'upload'
                    })

            # 2. Processa Arquivos EXISTENTES (Banco de Dados/Disco)
            if project_id and project_id != 'null' and project_id != '':
                try:
                    project = db.session.get(Project, int(project_id))
                    
                    if project and project.user_id == current_user.id:
                        storage_base = os.path.join(app.root_path, 'storage')
                        
                        for att in project.attachments:
                            safe_path = os.path.join(storage_base, str(current_user.id), str(project.id), att.filename)
                            
                            if os.path.exists(safe_path):
                                with open(safe_path, 'rb') as f_disk:
                                    file_content = f_disk.read()
                                    buf = io.BytesIO(file_content)
                                    buf.seek(0)
                                    
                                    lista_anexos_unificada.append({
                                        'filename': att.filename,
                                        'stream': buf,
                                        'origem': 'disco'
                                    })
                except Exception as e_db:
                    print(f"!!! Erro ao recuperar anexos do banco: {e_db}")
        else:
            print(f"--- Ignorando anexos para relatório da {tipo_relatorio} ---")

        # Chama a função de lógica de negócio passando o tipo
        pdf_buffer = gerar_pdf_com_anexos(data, lista_anexos_unificada, tipo_relatorio=tipo_relatorio)

        # Prepara a resposta HTTP 
        filename_pdf = f'Relatorio_{tipo_relatorio}_TpM.pdf'
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename={filename_pdf}'
        
        return response

    except Exception as e:
        print(f"!!! CRITICAL ERROR no handle_gerar_relatorio: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ------------------------------------------------------------------
# --- COMANDOS CLI (SETUP & ADMIN) ---
# ------------------------------------------------------------------

@app.cli.command("setup-db")
def setup_db():
    """Cria as tabelas no banco de dados MariaDB."""
    try:
        from models import User, Project, Attachment
        db.create_all()
        print(">>> Sucesso! Tabelas criadas.")
    except Exception as e:
        print(f">>> Erro ao criar tabelas: {e}")

@app.cli.command("create-users")
def create_users():
    """Cria usuários de teste padrão."""
    try:
        from models import User
        users_to_create = [
            ('admin', 'admin@wisstek.com', 'admin123'),
            ('operador', 'operador@wisstek.com', 'op123'),
            ('convidado', 'convidado@wisstek.com', 'guest123')
        ]
        for username, email, pwd in users_to_create:
            if User.query.filter_by(username=username).first(): continue
            hashed_pw = generate_password_hash(pwd)
            new_user = User(username=username, email=email, password_hash=hashed_pw)
            db.session.add(new_user)
        db.session.commit()
        print(">>> Usuários criados com sucesso!")
    except Exception as e:
        db.session.rollback()

@app.cli.command("add-user")
def add_user():
    """Cadastra um novo usuário de forma interativa via terminal."""
    try:
        from models import User
        
        print("--- Cadastro de Novo Usuário ---")
        username = click.prompt("Nome de Usuário")
        
        # Verifica se já existe
        if User.query.filter_by(username=username).first():
            print(f"Erro: O usuário '{username}' já existe.")
            return

        email = click.prompt("E-mail")
        # hide_input esconde a digitação, confirmation pede para digitar 2x
        password = click.prompt("Senha", hide_input=True, confirmation_prompt=True)
        
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, email=email, password_hash=hashed_pw)
        
        db.session.add(new_user)
        db.session.commit()
        
        print(f"\n>>> Sucesso! Usuário '{username}' criado.")
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao criar usuário: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
