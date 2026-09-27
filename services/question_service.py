from datetime import datetime, timezone
from models import db, Project, Question, PracticeSession, Answer

def save_generated_questions(project_id, questions_data):
    """
    Delete any old questions for this project and save 10 new questions.
    """
    # Delete existing questions for fresh generation if re-analyzing
    Question.query.filter_by(project_id=project_id).delete()
    db.session.commit()

    saved_questions = []
    for q in questions_data:
        question = Question(
            project_id=project_id,
            question_number=q.get('question_number', len(saved_questions) + 1),
            category=q.get('category', 'General'),
            difficulty=q.get('difficulty', 'Medium'),
            question_text=q.get('question_text', '')
        )
        db.session.add(question)
        saved_questions.append(question)
    
    db.session.commit()
    return saved_questions

def create_practice_session(project_id):
    """Create a new practice session for a project."""
    questions = Question.query.filter_by(project_id=project_id).order_by(Question.question_number).all()
    
    session = PracticeSession(
        project_id=project_id,
        total_questions=len(questions),
        answered_count=0,
        average_score=0.0,
        status='in_progress'
    )
    db.session.add(session)
    
    # Update project last_practiced and practice_count
    project = Project.query.get(project_id)
    if project:
        project.last_practiced = datetime.now(timezone.utc)
        project.practice_count = (project.practice_count or 0) + 1
        
    db.session.commit()
    return session

def update_session_score(session_id):
    """Recalculate average score and answered count for a practice session."""
    session = PracticeSession.query.get(session_id)
    if not session:
        return
    
    answers = Answer.query.filter_by(session_id=session_id).all()
    non_skipped_answers = [a for a in answers if not a.is_skipped]
    
    session.answered_count = len(answers)
    if non_skipped_answers:
        total_score = sum(a.score for a in non_skipped_answers)
        session.average_score = round(total_score / len(non_skipped_answers), 2)
    else:
        session.average_score = 0.0

    if session.answered_count >= session.total_questions:
        session.status = 'completed'
        session.end_time = datetime.now(timezone.utc)

    db.session.commit()
