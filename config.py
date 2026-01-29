import os

class Config:
    """
    Classe de configuração para separar segredos do código principal.
    """
    # Chave secreta para sessões e segurança do Flask (em produção, usar variável de ambiente)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'uma_chave_secreta_bem_dificil'
    
    # String de Conexão com o MariaDB
    # Formato: mysql+pymysql://USUARIO:SENHA@HOST:PORTA/NOME_BANCO
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://tpm_user:tpm123@localhost/smart_tpm_db'
    
    # Desativa notificação de modificações para economizar recursos
    SQLALCHEMY_TRACK_MODIFICATIONS = False
