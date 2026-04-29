import os
import uuid
import logging
from datetime import datetime
from io import BytesIO, StringIO

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, send_file, jsonify, session, current_app
)
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

from .converter import FileConverter

bp = Blueprint('main', __name__, url_prefix='/')

# Allowed file extensions
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'dbf'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_extension(filename):
    """Get file extension in lowercase."""
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

def validate_mime_type(file_stream, extension):
    """Validate file MIME type matches extension."""
    mime_map = {
        'csv': ['text/csv', 'text/plain', 'application/vnd.ms-excel'],
        'xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
        'xls': ['application/vnd.ms-excel', 'application/msexcel'],
        'dbf': ['application/x-dbf', 'application/octet-stream']
    }
    # Note: Actual MIME type checking would require python-magic
    # For now, we rely on extension and content validation
    return True

@bp.route('/')
def index():
    """Main page - Step 1: Upload."""
    session.clear()
    return render_template('index.html')

@bp.route('/upload', methods=['POST'])
def upload():
    """Handle file upload."""
    logging.info('Upload request received')
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({
            'success': False,
            'message': 'Invalid file type. Supported formats: CSV, XLSX, XLS, DBF'
        }), 400
    
    # Check file size
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Seek back to start
    
    if file_size > MAX_FILE_SIZE:
        return jsonify({
            'success': False,
            'message': f'File too large. Maximum size is 50 MB. Your file is {file_size / (1024*1024):.1f} MB.'
        }), 400
    
    if file_size == 0:
        return jsonify({'success': False, 'message': 'File is empty'}), 400
    
    try:
        extension = get_extension(file.filename)
        
        # Generate unique filename
        safe_filename = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex}_{safe_filename}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name)
        
        # Save file
        file.save(filepath)
        
        # Store in session
        session['uploaded_file'] = unique_name
        session['original_filename'] = safe_filename
        session['file_extension'] = extension
        session['file_size'] = file_size
        
        logging.info(f'File uploaded successfully: {unique_name} ({file_size} bytes)')
        
        return jsonify({
            'success': True,
            'filename': safe_filename,
            'extension': extension,
            'size': file_size,
            'message': 'File uploaded successfully'
        })
    
    except Exception as e:
        logging.error(f'Upload error: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Upload failed. Please try again.'
        }), 500

@bp.route('/configure')
def configure():
    """Step 2: Configure conversion options."""
    uploaded_file = session.get('uploaded_file')
    if not uploaded_file:
        flash('Please upload a file first', 'error')
        return redirect(url_for('main.index'))
    
    source_ext = session.get('file_extension')
    source_path = os.path.join(current_app.config['UPLOAD_FOLDER'], uploaded_file)
    
    if not os.path.exists(source_path):
        flash('Uploaded file not found', 'error')
        return redirect(url_for('main.index'))
    
    # Determine available target formats
    available_targets = get_available_targets(source_ext)
    
    # Get file info
    converter = FileConverter()
    try:
        file_info = converter.get_file_info(source_path, source_ext)
    except Exception as e:
        logging.error(f'Error reading file info: {str(e)}', exc_info=True)
        flash('Could not read uploaded file', 'error')
        return redirect(url_for('main.index'))
    
    return render_template(
        'configure.html',
        source_ext=source_ext,
        original_filename=session.get('original_filename'),
        available_targets=available_targets,
        file_info=file_info
    )

@bp.route('/convert', methods=['POST'])
def convert():
    """Perform file conversion."""
    uploaded_file = session.get('uploaded_file')
    if not uploaded_file:
        return jsonify({'success': False, 'message': 'No file uploaded'}), 400
    
    target_ext = request.form.get('target_format', '').lower()
    if target_ext not in ALLOWED_EXTENSIONS:
        return jsonify({'success': False, 'message': 'Invalid target format'}), 400
    
    source_ext = session.get('file_extension')
    source_path = os.path.join(current_app.config['UPLOAD_FOLDER'], uploaded_file)
    original_name = session.get('original_filename', 'converted_file')
    
    if not os.path.exists(source_path):
        return jsonify({'success': False, 'message': 'Source file not found'}), 400
    
    try:
        converter = FileConverter()
        output_filename = f"{os.path.splitext(original_name)[0]}.{target_ext}"
        output_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"converted_{uuid.uuid4().hex}.{target_ext}")
        
        # Perform conversion
        converter.convert(source_path, source_ext, output_path, target_ext)
        
        # Store conversion result in session
        session['converted_file'] = os.path.basename(output_path)
        session['converted_filename'] = output_filename
        session['target_extension'] = target_ext
        
        logging.info(f'Conversion successful: {uploaded_file} ({source_ext}) -> {target_ext}')
        
        return jsonify({
            'success': True,
            'message': 'Conversion complete',
            'filename': output_filename
        })
    
    except Exception as e:
        logging.error(f'Conversion error: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Conversion failed: {str(e)}'
        }), 500

@bp.route('/download')
def download():
    """Step 3: Download converted file."""
    converted_file = session.get('converted_file')
    filename = session.get('converted_filename', 'converted_file')
    
    if not converted_file:
        flash('No converted file available', 'error')
        return redirect(url_for('main.index'))
    
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], converted_file)
    
    if not os.path.exists(filepath):
        flash('Converted file not found', 'error')
        return redirect(url_for('main.index'))
    
    try:
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
    except Exception as e:
        logging.error(f'Download error: {str(e)}', exc_info=True)
        flash('Download failed', 'error')
        return redirect(url_for('main.index'))

@bp.route('/api/file-info', methods=['POST'])
def api_file_info():
    """Get file information via API."""
    uploaded_file = session.get('uploaded_file')
    if not uploaded_file:
        return jsonify({'success': False, 'message': 'No file uploaded'}), 400
    
    source_ext = session.get('file_extension')
    source_path = os.path.join(current_app.config['UPLOAD_FOLDER'], uploaded_file)
    
    if not os.path.exists(source_path):
        return jsonify({'success': False, 'message': 'File not found'}), 404
    
    try:
        converter = FileConverter()
        file_info = converter.get_file_info(source_path, source_ext)
        return jsonify({'success': True, 'data': file_info})
    except Exception as e:
        logging.error(f'Error getting file info: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/api/available-targets/<source_ext>')
def api_available_targets(source_ext):
    """Get available target formats for a source format."""
    targets = get_available_targets(source_ext)
    return jsonify({'success': True, 'targets': targets})

def get_available_targets(source_ext):
    """Get list of available target formats for a given source format."""
    all_formats = ['csv', 'xlsx', 'xls', 'dbf']
    return [f for f in all_formats if f != source_ext]