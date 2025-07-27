// Funciones principales de la aplicación
document.addEventListener('DOMContentLoaded', function() {
    
    // Inicializar tooltips de Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-hide alerts después de 5 segundos
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            if (alert.classList.contains('alert-success') || alert.classList.contains('alert-info')) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        });
    }, 5000);

    // Confirmación para acciones destructivas
    const deleteButtons = document.querySelectorAll('[onclick*="confirm"]');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            if (!confirm('¿Estás seguro de realizar esta acción?')) {
                e.preventDefault();
                return false;
            }
        });
    });

    // Validación de archivos antes de subir
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(function(input) {
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // Verificar tamaño (16MB máximo)
                const maxSize = 16 * 1024 * 1024;
                if (file.size > maxSize) {
                    alert('El archivo es demasiado grande. El tamaño máximo es 16MB.');
                    e.target.value = '';
                    return;
                }

                // Mostrar información del archivo
                const fileName = file.name;
                const fileSize = (file.size / 1024 / 1024).toFixed(2);
                console.log(`Archivo seleccionado: ${fileName} (${fileSize} MB)`);
            }
        });
    });

    // Prevenir doble envío de formularios
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton) {
                setTimeout(function() {
                    submitButton.disabled = true;
                    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Enviando...';
                }, 100);
            }
        });
    });

    // Búsqueda en tiempo real para listas largas
    const searchInputs = document.querySelectorAll('.search-input');
    searchInputs.forEach(function(input) {
        input.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            const searchableItems = document.querySelectorAll('.searchable-item');
            
            searchableItems.forEach(function(item) {
                const text = item.textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    item.style.display = '';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    });

    // Contador de caracteres para textareas
    const textareas = document.querySelectorAll('textarea[maxlength]');
    textareas.forEach(function(textarea) {
        const maxLength = textarea.getAttribute('maxlength');
        const counter = document.createElement('small');
        counter.className = 'text-muted float-end';
        textarea.parentNode.appendChild(counter);
        
        function updateCounter() {
            const remaining = maxLength - textarea.value.length;
            counter.textContent = `${remaining} caracteres restantes`;
            
            if (remaining < 50) {
                counter.className = 'text-warning float-end';
            } else if (remaining < 20) {
                counter.className = 'text-danger float-end';
            } else {
                counter.className = 'text-muted float-end';
            }
        }
        
        textarea.addEventListener('input', updateCounter);
        updateCounter();
    });

    // Animación suave para el scroll
    const smoothScrollLinks = document.querySelectorAll('a[href^="#"]');
    smoothScrollLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Notificaciones push simuladas (para desarrollo)
    if ('Notification' in window && navigator.serviceWorker) {
        // Solicitar permiso para notificaciones
        if (Notification.permission === 'default') {
            Notification.requestPermission();
        }
    }

    // Drag & Drop para archivos (mejora UX)
    const fileDropZones = document.querySelectorAll('.file-drop-zone');
    fileDropZones.forEach(function(zone) {
        zone.addEventListener('dragover', function(e) {
            e.preventDefault();
            zone.classList.add('drag-over');
        });

        zone.addEventListener('dragleave', function(e) {
            e.preventDefault();
            zone.classList.remove('drag-over');
        });

        zone.addEventListener('drop', function(e) {
            e.preventDefault();
            zone.classList.remove('drag-over');
            
            const files = e.dataTransfer.files;
            const fileInput = zone.querySelector('input[type="file"]');
            
            if (files.length > 0 && fileInput) {
                fileInput.files = files;
                // Disparar evento change
                const event = new Event('change', { bubbles: true });
                fileInput.dispatchEvent(event);
            }
        });
    });

    // Auto-guardar contenido de formularios en localStorage
    const autoSaveInputs = document.querySelectorAll('.auto-save');
    autoSaveInputs.forEach(function(input) {
        const key = `autosave_${input.name || input.id}`;
        
        // Cargar contenido guardado
        const savedValue = localStorage.getItem(key);
        if (savedValue && !input.value) {
            input.value = savedValue;
        }
        
        // Guardar en cada cambio
        input.addEventListener('input', function() {
            localStorage.setItem(key, input.value);
        });
        
        // Limpiar al enviar formulario
        const form = input.closest('form');
        if (form) {
            form.addEventListener('submit', function() {
                localStorage.removeItem(key);
            });
        }
    });

    // Indicador de conexión
    function updateConnectionStatus() {
        const statusIndicator = document.querySelector('.connection-status');
        if (statusIndicator) {
            if (navigator.onLine) {
                statusIndicator.className = 'connection-status text-success';
                statusIndicator.innerHTML = '<i class="bi bi-wifi"></i> En línea';
            } else {
                statusIndicator.className = 'connection-status text-danger';
                statusIndicator.innerHTML = '<i class="bi bi-wifi-off"></i> Sin conexión';
            }
        }
    }

    window.addEventListener('online', updateConnectionStatus);
    window.addEventListener('offline', updateConnectionStatus);
    updateConnectionStatus();

});

// Funciones utilitarias globales
window.utils = {
    // Formatear tamaños de archivo
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    // Mostrar notificación temporal
    showNotification: function(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = 'top: 90px; right: 20px; z-index: 9999; min-width: 300px;';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        // Auto-remove después de 4 segundos
        setTimeout(function() {
            if (alertDiv.parentNode) {
                alertDiv.parentNode.removeChild(alertDiv);
            }
        }, 4000);
    },

    // Copiar texto al portapapeles
    copyToClipboard: function(text) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(function() {
                utils.showNotification('Texto copiado al portapapeles', 'success');
            });
        } else {
            // Fallback para navegadores antiguos
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            utils.showNotification('Texto copiado al portapapeles', 'success');
        }
    }
};