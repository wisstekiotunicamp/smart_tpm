from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin

# Instância do banco de dados (será inicializada no app.py)
db = SQLAlchemy()

class User(UserMixin, db.Model):
    """
    Tabela de Usuários.
    Gerencia login e identificação.
    Herda de UserMixin para compatibilidade com Flask-Login.
    """
    __tablename__ = 'users'

    id = db.Column(db.BigInteger, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    projects = db.relationship('Project', backref='owner', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'


class Project(db.Model):
    """
    Tabela de Projetos (Abrange Fase 1, 2 e 3 do TpM).
    Armazena os dados preenchidos nos formulários de todas as fases.
    """
    __tablename__ = 'projects'

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False)
    
    # Metadados Gerais
    name = db.Column(db.String(150), nullable=False)
    responsible = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # --- FASE 1: Considering the Business ---
    context_desc = db.Column(db.Text)     # Contextualização (NOVO)
    business_desc = db.Column(db.Text)    # Negócio
    business_rules = db.Column(db.Text)   # Regras
    specialist_desc = db.Column(db.Text)  # Especialista
    things_desc = db.Column(db.Text)      # Coisas
    
    # --- FASE 2: Gathering Requirements (Top-Down) ---
    req_l6_display = db.Column(db.Text)
    req_l5_abstraction = db.Column(db.Text)
    req_l4_storage = db.Column(db.Text)
    req_l3_border = db.Column(db.Text)
    req_l2_connectivity = db.Column(db.Text)
    req_l1_sensor = db.Column(db.Text)

    # --- FASE 3: Implementation (Bottom-Up) ---
    impl_l1_sensor = db.Column(db.Text)
    impl_l2_connectivity = db.Column(db.Text)
    impl_l3_border = db.Column(db.Text)
    impl_l4_storage = db.Column(db.Text)
    impl_l5_abstraction = db.Column(db.Text)
    impl_l6_display = db.Column(db.Text)

    # Relacionamentos
    attachments = db.relationship('Attachment', backref='project', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Project {self.name}>'


class Attachment(db.Model):
    """
    Tabela de Anexos.
    Armazena APENAS O CAMINHO e metadados dos arquivos. 
    """
    __tablename__ = 'attachments'

    id = db.Column(db.BigInteger, primary_key=True)
    project_id = db.Column(db.BigInteger, db.ForeignKey('projects.id'), nullable=False)
    
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    filetype = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer)
    
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Attachment {self.filename}>'
