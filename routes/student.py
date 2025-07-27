import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models.models import db, Assignment, Material, Message, MessageRecipient, User
from datetime import datetime

student_bp = Blueprint('student', __name__)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def student_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_student():
            flash('Acceso denegado. Solo estudiantes pueden acceder a esta área.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    # Obtener estadísticas para el dashboard
    total_assignments = Assignment.query.filter_by(student_id=current_user.id).count()
    total_materials = Material.query.filter_by(is_active=True).count()
    
    # Mensajes no leídos
    unread_messages = MessageRecipient.query.filter_by(
        recipient_id=current_user.id,
        is_read=False
    ).count()
    
    # Últimos archivos subidos
    recent_assignments = Assignment.query.filter_by(
        student_id=current_user.id
    ).order_by(Assignment.submitted_at.desc()).limit(5).all()
    
    # Últimos materiales disponibles
    recent_materials = Material.query.filter_by(
        is_active=True
    ).order_by(Material.uploaded_at.desc()).limit(5).all()
    
    return render_template('student/dashboard.html',
                         total_assignments=total_assignments,
                         total_materials=total_materials,
                         unread_messages=unread_messages,
                         recent_assignments=recent_assignments,
                         recent_materials=recent_materials)

@student_bp.route('/assignments')
@login_required
@student_required
def assignments():
    assignments = Assignment.query.filter_by(
        student_id=current_user.id
    ).order_by(Assignment.submitted_at.desc()).all()
    
    return render_template('student/assignments.html', assignments=assignments)

@student_bp.route('/upload_assignment', methods=['POST'])
@login_required
@student_required
def upload_assignment():
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo.', 'error')
        return redirect(url_for('student.assignments'))
    
    file = request.files['file']
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    
    if file.filename == '':
        flash('No se seleccionó ningún archivo.', 'error')
        return redirect(url_for('student.assignments'))
    
    if not title:
        flash('El título es obligatorio.', 'error')
        return redirect(url_for('student.assignments'))
    
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{current_user.student_id}_{timestamp}_{filename}"
            
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'assignments', filename)
            file.save(file_path)
            
            assignment = Assignment(
                title=title,
                description=description,
                filename=filename,
                file_path=file_path,
                file_size=os.path.getsize(file_path),
                mime_type=file.content_type,
                student_id=current_user.id
            )
            
            db.session.add(assignment)
            db.session.commit()
            
            flash('Archivo subido exitosamente.', 'success')
            
        except Exception as e:
            flash('Error al subir el archivo. Inténtalo nuevamente.', 'error')
    else:
        flash('Tipo de archivo no permitido.', 'error')
    
    return redirect(url_for('student.assignments'))

@student_bp.route('/materials')
@login_required
@student_required
def materials():
    materials = Material.query.filter_by(is_active=True).order_by(Material.uploaded_at.desc()).all()
    return render_template('student/materials.html', materials=materials)

@student_bp.route('/download_material/<int:material_id>')
@login_required
@student_required
def download_material(material_id):
    material = Material.query.get_or_404(material_id)
    
    if not material.is_active:
        flash('El material ya no está disponible.', 'error')
        return redirect(url_for('student.materials'))
    
    try:
        return send_file(material.file_path, as_attachment=True, download_name=material.filename)
    except FileNotFoundError:
        flash('El archivo no se encuentra disponible.', 'error')
        return redirect(url_for('student.materials'))

@student_bp.route('/messages')
@login_required
@student_required
def messages():
    # Obtener mensajes del estudiante
    message_recipients = MessageRecipient.query.filter_by(
        recipient_id=current_user.id
    ).order_by(MessageRecipient.id.desc()).all()
    
    return render_template('student/messages.html', message_recipients=message_recipients)

@student_bp.route('/read_message/<int:message_id>')
@login_required
@student_required
def read_message(message_id):
    message_recipient = MessageRecipient.query.filter_by(
        message_id=message_id,
        recipient_id=current_user.id
    ).first_or_404()
    
    # Marcar como leído
    if not message_recipient.is_read:
        message_recipient.is_read = True
        message_recipient.read_at = datetime.utcnow()
        db.session.commit()
    
    return render_template('student/read_message.html', 
                         message=message_recipient.message,
                         message_recipient=message_recipient)