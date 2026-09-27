from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, default="Untitled Project")
    filename = db.Column(db.String(255), nullable=True)
    extracted_text = db.Column(db.Text, nullable=True)
    upload_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_practiced = db.Column(db.DateTime, nullable=True)
    practice_count = db.Column(db.Integer, default=0)

    # Analyzed Project Metadata
    problem_statement = db.Column(db.Text, nullable=True)
    objective = db.Column(db.Text, nullable=True)
    technologies = db.Column(db.Text, nullable=True)
    programming_languages = db.Column(db.Text, nullable=True)
    dataset = db.Column(db.Text, nullable=True)
    methodology = db.Column(db.Text, nullable=True)
    algorithms = db.Column(db.Text, nullable=True)
    system_architecture = db.Column(db.Text, nullable=True)
    results = db.Column(db.Text, nullable=True)
    conclusion = db.Column(db.Text, nullable=True)

    # Relationships
    questions = db.relationship('Question', backref='project', lazy=True, cascade='all, delete-orphan')
    practice_sessions = db.relationship('PracticeSession', backref='project', lazy=True, cascade='all, delete-orphan')
    code_reviews = db.relationship('CodeReview', backref='project', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'filename': self.filename,
            'upload_date': self.upload_date.strftime('%b %d, %Y %H:%M') if self.upload_date else '',
            'last_practiced': self.last_practiced.strftime('%b %d, %Y %H:%M') if self.last_practiced else 'Never',
            'practice_count': self.practice_count,
            'problem_statement': self.problem_statement or 'N/A',
            'objective': self.objective or 'N/A',
            'technologies': self.technologies or 'N/A',
            'programming_languages': self.programming_languages or 'N/A',
            'dataset': self.dataset or 'N/A',
            'methodology': self.methodology or 'N/A',
            'algorithms': self.algorithms or 'N/A',
            'system_architecture': self.system_architecture or 'N/A',
            'results': self.results or 'N/A',
            'conclusion': self.conclusion or 'N/A'
        }


class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    question_number = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(100), nullable=False)  # e.g., Basic, Technical, Algorithm...
    difficulty = db.Column(db.String(50), nullable=False, default='Medium') # Easy, Medium, Hard, Advanced
    question_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    answers = db.relationship('Answer', backref='question', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'question_number': self.question_number,
            'category': self.category,
            'difficulty': self.difficulty,
            'question_text': self.question_text
        }


class PracticeSession(db.Model):
    __tablename__ = 'practice_sessions'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    end_time = db.Column(db.DateTime, nullable=True)
    total_questions = db.Column(db.Integer, default=10)
    answered_count = db.Column(db.Integer, default=0)
    average_score = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default='in_progress')  # in_progress, completed

    # Relationships
    answers = db.relationship('Answer', backref='session', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'project_title': self.project.title if self.project else '',
            'start_time': self.start_time.strftime('%b %d, %Y %H:%M') if self.start_time else '',
            'end_time': self.end_time.strftime('%b %d, %Y %H:%M') if self.end_time else 'In progress',
            'total_questions': self.total_questions,
            'answered_count': self.answered_count,
            'average_score': round(self.average_score, 1),
            'status': self.status
        }


class Answer(db.Model):
    __tablename__ = 'answers'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('practice_sessions.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    student_answer = db.Column(db.Text, nullable=True)
    score = db.Column(db.Float, default=0.0)  # out of 10
    what_was_correct = db.Column(db.Text, nullable=True)
    what_was_missing = db.Column(db.Text, nullable=True)
    how_to_improve = db.Column(db.Text, nullable=True)
    suggested_answer = db.Column(db.Text, nullable=True)
    confidence_level = db.Column(db.String(50), default='Medium')  # High, Medium, Low
    follow_up_question = db.Column(db.Text, nullable=True)
    is_skipped = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'question_id': self.question_id,
            'student_answer': self.student_answer,
            'score': self.score,
            'what_was_correct': self.what_was_correct or '',
            'what_was_missing': self.what_was_missing or '',
            'how_to_improve': self.how_to_improve or '',
            'suggested_answer': self.suggested_answer or '',
            'confidence_level': self.confidence_level or 'Medium',
            'follow_up_question': self.follow_up_question or '',
            'is_skipped': self.is_skipped
        }


class CodeReview(db.Model):
    __tablename__ = 'code_reviews'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    filename = db.Column(db.String(255), nullable=False)
    code_content = db.Column(db.Text, nullable=False)
    analysis_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Store JSON strings for complex outputs
    matched_claims = db.Column(db.Text, nullable=True)
    mismatches = db.Column(db.Text, nullable=True)
    code_explanation = db.Column(db.Text, nullable=True)
    viva_questions = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'filename': self.filename,
            'analysis_date': self.analysis_date.strftime('%b %d, %Y %H:%M') if self.analysis_date else '',
            'code_explanation': self.code_explanation or ''
        }
