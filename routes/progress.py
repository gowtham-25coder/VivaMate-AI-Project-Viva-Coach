from flask import Blueprint, render_template
from models import db, Project, PracticeSession, Answer, Question
from services.gemini_service import is_gemini_configured
from sqlalchemy import func

progress_bp = Blueprint('progress', __name__)

@progress_bp.route('/progress', methods=['GET'])
def progress():
    gemini_ready = is_gemini_configured()
    
    # Statistics calculations
    total_questions_attempted = Answer.query.filter(Answer.is_skipped == False).count()
    projects_practiced = db.session.query(func.count(func.distinct(PracticeSession.project_id))).scalar() or 0
    
    avg_score_val = db.session.query(func.avg(Answer.score)).filter(Answer.is_skipped == False).scalar()
    avg_score = round(float(avg_score_val), 1) if avg_score_val else 0.0

    # Calculate average scores per category
    category_scores = db.session.query(
        Question.category,
        func.avg(Answer.score).label('avg_score'),
        func.count(Answer.id).label('attempt_count')
    ).join(Answer, Answer.question_id == Question.id)\
     .filter(Answer.is_skipped == False)\
     .group_by(Question.category).all()

    strong_topics = []
    weak_topics = []

    for cat, score, count in category_scores:
        score_val = round(float(score), 1)
        topic_info = {'category': cat, 'score': score_val, 'count': count}
        if score_val >= 7.0:
            strong_topics.append(topic_info)
        else:
            weak_topics.append(topic_info)

    # Sort topics
    strong_topics.sort(key=lambda x: x['score'], reverse=True)
    weak_topics.sort(key=lambda x: x['score'])

    # Recent practice sessions
    recent_sessions = PracticeSession.query.order_by(PracticeSession.start_time.desc()).limit(10).all()

    return render_template(
        'progress.html',
        gemini_ready=gemini_ready,
        total_questions_attempted=total_questions_attempted,
        projects_practiced=projects_practiced,
        avg_score=avg_score,
        strong_topics=strong_topics,
        weak_topics=weak_topics,
        recent_sessions=recent_sessions
    )
