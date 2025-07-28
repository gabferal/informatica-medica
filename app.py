import os
from flask import Flask, render_template, redirect, url_for, flash
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from dotenv import load_dotenv
from models.models import db, User
from routes.auth import auth_bp
from routes.student import student_bp
from routes.professor import professor_bp
from datetime import datetime
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
    
    # Configuración de base de datos con soporte para Neon PostgreSQL
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Neon PostgreSQL - asegurar compatibilidad
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        # Configuración optimizada para Neon PostgreSQL
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'connect_args': {'sslmode': 'require'}
        }
        print("✅ Configurando Neon PostgreSQL")
    else:
        # Fallback a SQLite para desarrollo local
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
        print("✅ Configurando SQLite para desarrollo local")
    
    # Configuración de la aplicación
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Configuración de archivos - adaptada para Fly.io
    if os.environ.get('FLY_APP_NAME'):
        # En Fly.io - usar volumen persistente
        app.config['UPLOAD_FOLDER'] = '/app/static/uploads'
    else:
        # En desarrollo local
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

    @app.route('/health')
    def health_check():
        """Health check endpoint for Fly.io"""
        try:
            # Verificar conexión a base de datos
            result = db.session.execute('SELECT version()')
            version_info = result.fetchone()
            
            # Información adicional para debugging
            response_data = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'database': 'connected',
                'app_name': os.environ.get('FLY_APP_NAME', 'local'),
                'upload_folder': app.config['UPLOAD_FOLDER']
            }
            
            # Solo incluir versión de PostgreSQL si está disponible
            if version_info:
                response_data['postgres_version'] = version_info[0][:50]
            
            return response_data, 200
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'app_name': os.environ.get('FLY_APP_NAME', 'local')
            }, 500

    # Crear carpetas necesarias
    def create_folders():
        folders = [
            app.config['UPLOAD_FOLDER'],
            os.path.join(app.config['UPLOAD_FOLDER'], 'materials'),
            os.path.join(app.config['UPLOAD_FOLDER'], 'assignments')
        ]
        for folder in folders:
            try:
                if not os.path.exists(folder):
                    os.makedirs(folder)
                    print(f"✅ Carpeta creada: {folder}")
            except Exception as e:
                print(f"⚠️ No se pudo crear carpeta {folder}: {e}")
    
    # Inicialización de base de datos y carpetas
    with app.app_context():
        try:
            # Crear carpetas de uploads
            create_folders()
            
            # Crear tablas de la base de datos
            db.create_all()
            print("✅ Tablas de base de datos creadas exitosamente")
            
            # Crear usuario profesor por defecto si no existe
            professor = User.query.filter_by(role='professor').first()
            if not professor:
                default_professor = User(
                    email='profesor@medicina.edu',
                    first_name='Profesor',
                    last_name='Informática Médica',
                    role='professor',
                    is_active=True
                )
                default_professor.set_password('admin123')
                db.session.add(default_professor)
                db.session.commit()
                print("✅ Usuario profesor creado: profesor@medicina.edu / admin123")
            else:
                print("✅ Usuario profesor ya existe")
                
        except Exception as e:
            print(f"❌ Error en inicialización: {e}")
            # No fallar el startup por problemas de inicialización
            pass
    
    return app

app = create_app()

if __name__ == '__main__':
    # Para desarrollo local - usar puerto 8000
    # Para Fly.io - usar puerto 8080 (configurado en Dockerfile)
    port = int(os.environ.get('PORT', 8000))
    debug_mode = not os.environ.get('FLY_APP_NAME')  # No debug en producción
    app.run(debug=debug_mode, host='0.0.0.0', port=port)