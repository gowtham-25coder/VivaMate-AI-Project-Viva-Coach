from flask import Blueprint, render_template, redirect, url_for, flash, request
from models import db, Project, Question, PracticeSession
from services.gemini_service import is_gemini_configured
from services.question_service import create_practice_session

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports', methods=['GET'])
def list_reports():
    projects = Project.query.order_by(Project.upload_date.desc()).all()
    gemini_ready = is_gemini_configured()
    return render_template('reports.html', projects=projects, gemini_ready=gemini_ready)

@reports_bp.route('/reports/<int:project_id>', methods=['GET'])
def view_report(project_id):
    project = Project.query.get_or_404(project_id)
    questions = Question.query.filter_by(project_id=project.id).order_by(Question.question_number).all()
    sessions = PracticeSession.query.filter_by(project_id=project.id).order_by(PracticeSession.start_time.desc()).all()
    gemini_ready = is_gemini_configured()
    return render_template('report_detail.html', project=project, questions=questions, sessions=sessions, gemini_ready=gemini_ready)

@reports_bp.route('/reports/<int:project_id>/practice', methods=['POST'])
def start_practice_for_report(project_id):
    project = Project.query.get_or_404(project_id)
    gemini_ready = is_gemini_configured()
    if not gemini_ready:
        flash('AI service is not configured. Add GEMINI_API_KEY to your .env file.', 'danger')
        return redirect(url_for('reports.list_reports'))

    # Check if project has questions, if not generate them
    questions = Question.query.filter_by(project_id=project.id).all()
    if not questions:
        from services.gemini_service import generate_viva_questions
        from services.question_service import save_generated_questions
        
        project_info = project.to_dict()
        q_data = generate_viva_questions(project_info)
        if isinstance(q_data, list):
            save_generated_questions(project.id, q_data)

    session = create_practice_session(project.id)
    flash(f'Started practice session for "{project.title}". Good luck!', 'success')
    return redirect(url_for('practice.viva_session', session_id=session.id))

@reports_bp.route('/reports/<int:project_id>/delete', methods=['POST'])
def delete_report(project_id):
    project = Project.query.get_or_404(project_id)
    title = project.title
    db.session.delete(project)
    db.session.commit()
    flash(f'Project report "{title}" and all related data deleted successfully.', 'success')
    return redirect(url_for('reports.list_reports'))
