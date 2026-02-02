import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models.models import db, Assignment, Material, Message, MessageRecipient, User
from datetime import datetime

professor_bp = Blueprint('professor', __name__)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def professor_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_professor():
            flash('Acceso denegado. Solo profesores pueden acceder a esta área.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@professor_bp.route('/dashboard')
@login_required
@professor_required
def dashboard():
    total_students = User.query.filter_by(role='student', is_active=True).count()
    total_assignments = Assignment.query.count()
    total_materials = Material.query.filter_by(is_active=True).count()
    pending_reviews = Assignment.query.filter_by(status='submitted').count()
    
    recent_students = User.query.filter_by(
        role='student',
        is_active=True
    ).order_by(User.created_at.desc()).limit(5).all()
    
    recent_assignments = Assignment.query.order_by(
        Assignment.submitted_at.desc()
    ).limit(5).all()
    
    return render_template('professor/dashboard.html',
                         total_students=total_students,
                         total_assignments=total_assignments,
                         total_materials=total_materials,
                         pending_reviews=pending_reviews,
                         recent_students=recent_students,
                         recent_assignments=recent_assignments)

@professor_bp.route('/students')
@login_required
@professor_required
def students():
    students = User.query.filter_by(role='student', is_active=True).all()
    for student in students:
        student.assignment_count = Assignment.query.filter_by(student_id=student.id).count()
        student.latest_assignment = Assignment.query.filter_by(
            student_id=student.id
        ).order_by(Assignment.submitted_at.desc()).first()
    
    return render_template('professor/students.html', students=students)

@professor_bp.route('/student_assignments/<int:student_id>')
@login_required
@professor_required
def student_assignments(student_id):
    student = User.query.get_or_404(student_id)
    if not student.is_student():
        flash('Usuario no encontrado.', 'error')
        return redirect(url_for('professor.students'))
    
    assignments = Assignment.query.filter_by(
        student_id=student_id
    ).order_by(Assignment.submitted_at.desc()).all()
    
    return render_template('professor/student_assignments.html', 
                         student=student, 
                         assignments=assignments)

@professor_bp.route('/download_assignment/<int:assignment_id>')
@login_required
@professor_required
def download_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    try:
        return send_file(assignment.file_path, as_attachment=True, download_name=assignment.filename)
    except FileNotFoundError:
        flash('El archivo no se encuentra disponible.', 'error')
        return redirect(url_for('professor.students'))

@professor_bp.route('/grade_assignment/<int:assignment_id>', methods=['POST'])
@login_required
@professor_required
def grade_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    grade = request.form.get('grade')
    feedback = request.form.get('feedback', '').strip()
    
    try:
        if grade:
            grade = float(grade)
            if grade < 0 or grade > 10:
                flash('La calificación debe estar entre 0 y 10.', 'error')
                return redirect(request.referrer)
            assignment.grade = grade
        
        assignment.feedback = feedback
        assignment.status = 'graded' if grade else 'reviewed'
        db.session.commit()
        flash('Calificación guardada exitosamente.', 'success')
    except ValueError:
        flash('La calificación debe ser un número válido.', 'error')
    except Exception as e:
        flash('Error al guardar la calificación.', 'error')
    
    return redirect(request.referrer)

# --- SECCIÓN DE MATERIALES ACTUALIZADA ---

@professor_bp.route('/materials')
@login_required
@professor_required
def materials():
    materials = Material.query.filter_by(
        uploaded_by=current_user.id
    ).order_by(Material.uploaded_at.desc()).all()
    return render_template('professor/materials.html', materials=materials)

@professor_bp.route('/download_material/<int:material_id>')
@login_required
@professor_required
def download_material(material_id):
    """Permite al profesor descargar o visualizar los materiales subidos"""
    material = Material.query.get_or_404(material_id)
    try:
        return send_file(
            material.file_path, 
            as_attachment=True, 
            download_name=material.filename
        )
    except FileNotFoundError:
        flash('El archivo físico no se encuentra en el servidor.', 'error')
        return redirect(url_for('professor.materials'))
    except Exception as e:
        flash(f'Error al descargar el archivo: {str(e)}', 'error')
        return redirect(url_for('professor.materials'))

@professor_bp.route('/upload_material', methods=['POST'])
@login_required
@professor_required
def upload_material():
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo.', 'error')
        return redirect(url_for('professor.materials'))
    
    file = request.files['file']
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    
    if file.filename == '' or not title:
        flash('El título y el archivo son obligatorios.', 'error')
        return redirect(url_for('professor.materials'))
    
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"material_{timestamp}_{filename}"
            
            # Asegurar que el directorio existe
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'materials')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)

            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            
            material = Material(
                title=title,
                description=description,
                filename=filename,
                file_path=file_path,
                file_size=os.path.getsize(file_path),
                mime_type=file.content_type,
                uploaded_by=current_user.id
            )
            
            db.session.add(material)
            db.session.commit()
            flash('Material subido exitosamente.', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash('Error al subir el material.', 'error')
    else:
        flash('Tipo de archivo no permitido.', 'error')
    
    return redirect(url_for('professor.materials'))

@professor_bp.route('/delete_material/<int:material_id>')
@login_required
@professor_required
def delete_material(material_id):
    material = Material.query.get_or_404(material_id)
    if material.uploaded_by != current_user.id:
        flash('No tienes permisos para eliminar este material.', 'error')
        return redirect(url_for('professor.materials'))
    
    try:
        material.is_active = False
        db.session.commit()
        flash('Material eliminado exitosamente.', 'success')
    except Exception as e:
        flash('Error al eliminar el material.', 'error')
    
    return redirect(url_for('professor.materials'))

# --- SECCIÓN DE MENSAJERÍA ---

@professor_bp.route('/messages')
@login_required
@professor_required
def messages():
    sent_messages = Message.query.filter_by(
        sender_id=current_user.id
    ).order_at(Message.created_at.desc()).all()
    return render_template('professor/messages.html', messages=sent_messages)

@professor_bp.route('/send_message', methods=['GET', 'POST'])
@login_required
@professor_required
def send_message():
    if request.method == 'POST':
        subject = request.form.get('subject', '').strip()
        content = request.form.get('content', '').strip()
        recipients = request.form.getlist('recipients')
        is_announcement = bool(request.form.get('is_announcement'))
        
        if not subject or not content:
            flash('El asunto y contenido son obligatorios.', 'error')
            return redirect(url_for('professor.send_message'))
        
        try:
            message = Message(
                subject=subject,
                content=content,
                sender_id=current_user.id,
                is_announcement=is_announcement
            )
            db.session.add(message)
            db.session.flush() 
            
            if is_announcement:
                students = User.query.filter_by(role='student', is_active=True).all()
                for student in students:
                    db.session.add(MessageRecipient(message_id=message.id, recipient_id=student.id))
            else:
                for recipient_id in recipients:
                    db.session.add(MessageRecipient(message_id=message.id, recipient_id=int(recipient_id)))
            
            db.session.commit()
            flash('Mensaje enviado exitosamente.', 'success')
            return redirect(url_for('professor.messages'))
        except Exception as e:
            db.session.rollback()
            flash('Error al enviar el mensaje.', 'error')
    
    students = User.query.filter_by(role='student', is_active=True).order_by(User.first_name, User.last_name).all()
    return render_template('professor/send_message.html', students=students)