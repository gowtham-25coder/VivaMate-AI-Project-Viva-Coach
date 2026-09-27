import os
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from models import db, Project, CodeReview
from services.gemini_service import is_gemini_configured
from services.code_analysis import review_code_file

code_review_bp = Blueprint('code_review', __name__)

@code_review_bp.route('/code-review', methods=['GET'])
def code_review_index():
    projects = Project.query.order_by(Project.upload_date.desc()).all()
    recent_reviews = CodeReview.query.order_by(CodeReview.analysis_date.desc()).limit(5).all()
    gemini_ready = is_gemini_configured()
    
    return render_template(
        'code_review.html',
        projects=projects,
        recent_reviews=recent_reviews,
        gemini_ready=gemini_ready,
        analysis_result=None
    )

@code_review_bp.route('/code-review/analyze', methods=['POST'])
def analyze_code():
    gemini_ready = is_gemini_configured()
    if not gemini_ready:
        flash('AI service is not configured. Add GEMINI_API_KEY to your .env file.', 'danger')
        return redirect(url_for('code_review.code_review_index'))

    project_id = request.form.get('project_id')
    project_id = int(project_id) if project_id and project_id.isdigit() else None
    
    pasted_code = request.form.get('pasted_code', '').strip()
    code_content = ""
    filename = "submitted_code.py"

    if 'code_file' in request.files:
        file = request.files['code_file']
        if file and file.filename != '':
            if not file.filename.endswith('.py'):
                flash('Please upload a Python (.py) file.', 'warning')
                return redirect(url_for('code_review.code_review_index'))

            filename = secure_filename(file.filename)
            upload_dir = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                code_content = f.read()

    if not code_content and pasted_code:
        code_content = pasted_code
        filename = "pasted_script.py"

    if not code_content or len(code_content.strip()) < 10:
        flash('Please upload a valid .py file or paste your Python code.', 'warning')
        return redirect(url_for('code_review.code_review_index'))

    # Perform code review analysis
    result = review_code_file(filename, code_content, project_id)
    if 'error' in result:
        flash(result['error'], 'danger')
        return redirect(url_for('code_review.code_review_index'))

    projects = Project.query.order_by(Project.upload_date.desc()).all()
    recent_reviews = CodeReview.query.order_by(CodeReview.analysis_date.desc()).limit(5).all()

    return render_template(
        'code_review.html',
        projects=projects,
        recent_reviews=recent_reviews,
        gemini_ready=gemini_ready,
        analysis_result=result
    )

@code_review_bp.route('/code-review/<int:review_id>', methods=['GET'])
def view_review(review_id):
    review = CodeReview.query.get_or_404(review_id)
    gemini_ready = is_gemini_configured()
    projects = Project.query.order_by(Project.upload_date.desc()).all()
    recent_reviews = CodeReview.query.order_by(CodeReview.analysis_date.desc()).limit(5).all()

    analysis_result = {
        'id': review.id,
        'filename': review.filename,
        'matched_claims': json.loads(review.matched_claims) if review.matched_claims else [],
        'possible_mismatches': json.loads(review.mismatches) if review.mismatches else [],
        'code_explanation': review.code_explanation,
        'possible_viva_questions': json.loads(review.viva_questions) if review.viva_questions else []
    }

    return render_template(
        'code_review.html',
        projects=projects,
        recent_reviews=recent_reviews,
        gemini_ready=gemini_ready,
        analysis_result=analysis_result
    )
