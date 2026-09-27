from flask import Blueprint, render_template, current_app
from models import Project, PracticeSession, Answer
from services.gemini_service import is_gemini_configured
from sqlalchemy import func

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    gemini_ready = is_gemini_configured()
    
    # Calculate stats for home dashboard
    total_projects = Project.query.count()
    total_sessions = PracticeSession.query.count()
    total_questions_attempted = Answer.query.count()
    
    avg_score_query = db.session.query(func.avg(Answer.score)).filter(Answer.is_skipped == False).scalar() if 'db' in globals() else None
    
    # Simple direct query using SQLAlchemy model session
    from models import db
    avg_score_val = db.session.query(func.avg(Answer.score)).filter(Answer.is_skipped == False).scalar()
    avg_score = round(float(avg_score_val), 1) if avg_score_val else 0.0

    recent_projects = Project.query.order_by(Project.upload_date.desc()).limit(5).all()

    return render_template(
        'index.html',
        gemini_ready=gemini_ready,
        total_projects=total_projects,
        total_sessions=total_sessions,
        total_questions_attempted=total_questions_attempted,
        avg_score=avg_score,
        recent_projects=recent_projects
    )
