import os
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, current_app
from werkzeug.utils import secure_filename
from models import db, Project, Question, PracticeSession, Answer
from services.pdf_service import process_file_content
from services.gemini_service import analyze_project_report, generate_viva_questions, evaluate_answer, is_gemini_configured, analyze_project_and_generate_questions
from services.question_service import save_generated_questions, create_practice_session, update_session_score

practice_bp = Blueprint('practice', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@practice_bp.route('/practice', methods=['GET'])
def practice():
    projects = Project.query.order_by(Project.upload_date.desc()).all()
    gemini_ready = is_gemini_configured()
    return render_template('practice.html', projects=projects, gemini_ready=gemini_ready)

@practice_bp.route('/practice/upload', methods=['POST'])
def upload_report():
    gemini_ready = is_gemini_configured()
    if not gemini_ready:
        flash('AI service is not configured. Add GEMINI_API_KEY to your .env file.', 'danger')
        return redirect(url_for('practice.practice'))

    report_text = ""
    original_filename = None

    # Check if text was pasted
    pasted_text = request.form.get('pasted_text', '').strip()
    
    if pasted_text:
        report_text = pasted_text
        original_filename = "Pasted_Report.txt"
    elif 'report_file' in request.files:
        file = request.files['report_file']
        if file and file.filename != '':
            if not allowed_file(file.filename):
                flash('Invalid file format. Please upload a PDF or TXT file.', 'danger')
                return redirect(url_for('practice.practice'))
            
            original_filename = secure_filename(file.filename)
            upload_dir = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, original_filename)
            file.save(file_path)

            try:
                report_text = process_file_content(file_path, original_filename)
            except Exception as e:
                flash(f'Error processing file: {str(e)}', 'danger')
                return redirect(url_for('practice.practice'))

    if not report_text or len(report_text.strip()) < 50:
        flash('Please upload a valid project report or paste sufficient text (minimum 50 characters).', 'warning')
        return redirect(url_for('practice.practice'))

    # Step 1 & 2: Single AI call for report analysis AND question generation
    result = analyze_project_and_generate_questions(report_text)
    if 'error' in result:
        flash(result['error'], 'danger')
        return redirect(url_for('practice.practice'))

    project_title = result.get('title') or (original_filename.rsplit('.', 1)[0] if original_filename else "My Viva Project")
    
    project = Project(
        title=project_title,
        filename=original_filename,
        extracted_text=report_text,
        problem_statement=result.get('problem_statement'),
        objective=result.get('objective'),
        technologies=result.get('technologies'),
        programming_languages=result.get('programming_languages'),
        dataset=result.get('dataset'),
        methodology=result.get('methodology'),
        algorithms=result.get('algorithms'),
        system_architecture=result.get('system_architecture'),
        results=result.get('results'),
        conclusion=result.get('conclusion')
    )
    db.session.add(project)
    db.session.commit()

    # Step 3: Save generated questions from single call
    questions_data = result.get('questions', [])
    if questions_data:
        save_generated_questions(project.id, questions_data)

    # Step 4: Create Practice Session & redirect to viva studio
    session = create_practice_session(project.id)
    flash('Project analyzed successfully! Welcome to your Practice Studio session.', 'success')
    return redirect(url_for('practice.viva_session', session_id=session.id))


@practice_bp.route('/viva/<int:session_id>', methods=['GET'])
def viva_session(session_id):
    session = PracticeSession.query.get_or_404(session_id)
    project = session.project
    questions = Question.query.filter_by(project_id=project.id).order_by(Question.question_number).all()
    gemini_ready = is_gemini_configured()
    
    return render_template(
        'viva.html',
        session=session,
        project=project,
        questions=questions,
        total_questions=len(questions),
        gemini_ready=gemini_ready
    )


@practice_bp.route('/api/viva/<int:session_id>/question/<int:q_num>', methods=['GET'])
def get_question_api(session_id, q_num):
    session = PracticeSession.query.get_or_404(session_id)
    question = Question.query.filter_by(project_id=session.project_id, question_number=q_num).first()
    
    if not question:
        return jsonify({'error': 'Question not found'}), 404

    # Check if this question was already answered in this session
    existing_answer = Answer.query.filter_by(session_id=session.id, question_id=question.id).first()

    return jsonify({
        'session_id': session.id,
        'question_id': question.id,
        'question_number': question.question_number,
        'total_questions': session.total_questions,
        'category': question.category,
        'difficulty': question.difficulty,
        'question_text': question.question_text,
        'already_answered': existing_answer is not None,
        'previous_answer': existing_answer.to_dict() if existing_answer else None
    })


@practice_bp.route('/api/viva/<int:session_id>/submit', methods=['POST'])
def submit_answer_api(session_id):
    data = request.get_json() or {}
    question_id = data.get('question_id')
    student_answer = data.get('student_answer', '').strip()

    if not question_id:
        return jsonify({'error': 'Question ID is required'}), 400

    session = PracticeSession.query.get_or_404(session_id)
    question = Question.query.get_or_404(question_id)
    project = session.project

    if not is_gemini_configured():
        return jsonify({'error': 'AI service is not configured. Add GEMINI_API_KEY to your .env file.'}), 400

    # Build context for Gemini evaluation
    project_context = {
        'title': project.title,
        'technologies': project.technologies,
        'algorithms': project.algorithms,
        'methodology': project.methodology
    }
    
    question_info = {
        'category': question.category,
        'difficulty': question.difficulty,
        'question_text': question.question_text
    }

    # Run AI evaluation
    eval_result = evaluate_answer(project_context, question_info, student_answer)
    if 'error' in eval_result:
        return jsonify({'error': eval_result['error']}), 500

    # Check if answer entry already exists, update or create
    existing_answer = Answer.query.filter_by(session_id=session.id, question_id=question.id).first()
    if existing_answer:
        answer = existing_answer
        answer.student_answer = student_answer
        answer.score = float(eval_result.get('score', 0.0))
        answer.what_was_correct = eval_result.get('what_was_correct', '')
        answer.what_was_missing = eval_result.get('what_was_missing', '')
        answer.how_to_improve = eval_result.get('how_to_improve', '')
        answer.suggested_answer = eval_result.get('suggested_answer', '')
        answer.confidence_level = eval_result.get('confidence_level', 'Medium')
        answer.follow_up_question = eval_result.get('follow_up_question', '')
        answer.is_skipped = False
    else:
        answer = Answer(
            session_id=session.id,
            question_id=question.id,
            student_answer=student_answer,
            score=float(eval_result.get('score', 0.0)),
            what_was_correct=eval_result.get('what_was_correct', ''),
            what_was_missing=eval_result.get('what_was_missing', ''),
            how_to_improve=eval_result.get('how_to_improve', ''),
            suggested_answer=eval_result.get('suggested_answer', ''),
            confidence_level=eval_result.get('confidence_level', 'Medium'),
            follow_up_question=eval_result.get('follow_up_question', ''),
            is_skipped=False
        )
        db.session.add(answer)

    db.session.commit()
    update_session_score(session.id)

    return jsonify({
        'success': True,
        'feedback': answer.to_dict(),
        'session_average': session.average_score,
        'answered_count': session.answered_count
    })


@practice_bp.route('/api/viva/<int:session_id>/skip', methods=['POST'])
def skip_question_api(session_id):
    data = request.get_json() or {}
    question_id = data.get('question_id')
    
    if not question_id:
        return jsonify({'error': 'Question ID is required'}), 400

    session = PracticeSession.query.get_or_404(session_id)
    question = Question.query.get_or_404(question_id)

    existing_answer = Answer.query.filter_by(session_id=session.id, question_id=question.id).first()
    if not existing_answer:
        answer = Answer(
            session_id=session.id,
            question_id=question.id,
            student_answer="[Skipped]",
            score=0.0,
            what_was_correct="Question skipped.",
            what_was_missing="No answer was provided.",
            how_to_improve="Attempt this question during your next rehearsal.",
            suggested_answer="",
            confidence_level="Low",
            is_skipped=True
        )
        db.session.add(answer)
        db.session.commit()

    update_session_score(session.id)

    return jsonify({
        'success': True,
        'message': 'Question skipped successfully',
        'answered_count': session.answered_count
    })


@practice_bp.route('/viva/<int:session_id>/summary', methods=['GET'])
def session_summary(session_id):
    session = PracticeSession.query.get_or_404(session_id)
    answers = Answer.query.filter_by(session_id=session.id).all()
    gemini_ready = is_gemini_configured()

    return render_template(
        'summary.html',
        session=session,
        project=session.project,
        answers=answers,
        gemini_ready=gemini_ready
    )
