import os
from flask import Flask, render_template, redirect, url_for, flash
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from dotenv import load_dotenv
from models.models import db, User
from routes.auth import auth_bp
from routes.student import student_bp
from routes.professor import professor_bp
import re

# Cargar variables de entorno
load_dotenv()

def nl2br(value):
    """Filtro personalizado para convertir saltos de línea en <br> tags"""
    if value is None:
        return ''
    # Escapar HTML para seguridad
    from markupsafe import escape
    value = escape(value)
    # Convertir saltos de línea a <br>
    return value.replace('\n', '<br>\n')

def create_app():
    app = Flask(__name__)
    
    # Configuración de la aplicación
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'static/uploads')
    app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 16777216))  # 16MB
    
    # Registrar filtro personalizado
    app.jinja_env.filters['nl2br'] = nl2br
    
    # Inicializar extensiones
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # Configurar Login Manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Registrar blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(professor_bp, url_prefix='/professor')
    
    # Ruta principal
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.is_professor():
                return redirect(url_for('professor.dashboard'))
            else:
                return redirect(url_for('student.dashboard'))
        return render_template('index.html')
    
    # Crear carpetas necesarias
    @app.before_request
    def create_folders():
        folders = [
            app.config['UPLOAD_FOLDER'],
            os.path.join(app.config['UPLOAD_FOLDER'], 'materials'),
            os.path.join(app.config['UPLOAD_FOLDER'], 'assignments')
        ]
        for folder in folders:
            if not os.path.exists(folder):
                os.makedirs(folder)
    
    # Crear tablas de la base de datos
    with app.app_context():
        db.create_all()
        
        # Crear usuario profesor por defecto si no existe
        professor = User.query.filter_by(role='professor').first()
        if not professor:
            default_professor = User(
                email='profesor@medicina.edu',
                first_name='Profesor',
                last_name='Informática Médica',
                role='professor'
            )
            default_professor.set_password('admin123')
            db.session.add(default_professor)
            db.session.commit()
            print("Usuario profesor creado: profesor@medicina.edu / admin123")
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)