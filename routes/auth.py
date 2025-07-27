from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from werkzeug.security import check_password_hash
from models.models import db, User
import re

auth_bp = Blueprint('auth', __name__)

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    if len(password) < 6:
        return False, "La contraseña debe tener al menos 6 caracteres"
    if not re.search(r'[A-Za-z]', password):
        return False, "La contraseña debe contener al menos una letra"
    if not re.search(r'\d', password):
        return False, "La contraseña debe contener al menos un número"
    return True, ""

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_professor():
            return redirect(url_for('professor.dashboard'))
        return redirect(url_for('student.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember_me = bool(request.form.get('remember_me'))
        
        # Validaciones
        if not email or not password:
            flash('Por favor completa todos los campos.', 'error')
            return render_template('auth/login.html')
        
        if not validate_email(email):
            flash('El formato del email no es válido.', 'error')
            return render_template('auth/login.html')
        
        # Buscar usuario
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Tu cuenta está desactivada. Contacta al administrador.', 'error')
                return render_template('auth/login.html')
            
            login_user(user, remember=remember_me)
            flash(f'¡Bienvenido/a, {user.get_full_name()}!', 'success')
            
            # Redireccionar según el rol
            if user.is_professor():
                return redirect(url_for('professor.dashboard'))
            else:
                return redirect(url_for('student.dashboard'))
        else:
            flash('Email o contraseña incorrectos.', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Obtener datos del formulario
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        first_name = request.form.get('first_name', '').strip().title()
        last_name = request.form.get('last_name', '').strip().title()
        student_id = request.form.get('student_id', '').strip().upper()
        
        # Validaciones
        if not all([email, password, confirm_password, first_name, last_name, student_id]):
            flash('Por favor completa todos los campos.', 'error')
            return render_template('auth/register.html')
        
        if not validate_email(email):
            flash('El formato del email no es válido.', 'error')
            return render_template('auth/register.html')
        
        is_valid, password_message = validate_password(password)
        if not is_valid:
            flash(password_message, 'error')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'error')
            return render_template('auth/register.html')
        
        if len(first_name) < 2 or len(last_name) < 2:
            flash('El nombre y apellido deben tener al menos 2 caracteres.', 'error')
            return render_template('auth/register.html')
        
        if len(student_id) < 4:
            flash('El número de estudiante debe tener al menos 4 caracteres.', 'error')
            return render_template('auth/register.html')
        
        # Verificar si el usuario ya existe
        existing_user = User.query.filter(
            (User.email == email) | (User.student_id == student_id)
        ).first()
        
        if existing_user:
            if existing_user.email == email:
                flash('Ya existe una cuenta con este email.', 'error')
            else:
                flash('Ya existe una cuenta con este número de estudiante.', 'error')
            return render_template('auth/register.html')
        
        # Crear nuevo usuario
        try:
            new_user = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                student_id=student_id,
                role='student'
            )
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            flash('¡Registro exitoso! Ya puedes iniciar sesión.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error al crear la cuenta. Inténtalo nuevamente.', 'error')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('Has cerrado sesión exitosamente.', 'info')
    return redirect(url_for('index'))