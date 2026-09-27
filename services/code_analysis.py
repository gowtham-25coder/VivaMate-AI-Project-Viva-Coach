import os
import json
from models import db, CodeReview, Project
from services.gemini_service import analyze_code_against_report, is_gemini_configured

def review_code_file(filename, code_content, project_id=None):
    """
    Review python code file against an optional project report context.
    """
    report_text = ""
    if project_id:
        project = Project.query.get(project_id)
        if project:
            report_text = project.extracted_text or f"Title: {project.title}\nObjective: {project.objective}\nTechnologies: {project.technologies}\nAlgorithms: {project.algorithms}"

    if not is_gemini_configured():
        return {
            'error': 'AI service is not configured. Add GEMINI_API_KEY to your .env file.'
        }

    ai_result = analyze_code_against_report(code_content, report_text)
    if 'error' in ai_result:
        return ai_result

    # Store CodeReview record in DB
    code_review = CodeReview(
        project_id=project_id if project_id else None,
        filename=filename,
        code_content=code_content,
        matched_claims=json.dumps(ai_result.get('matched_claims', [])),
        mismatches=json.dumps(ai_result.get('possible_mismatches', [])),
        code_explanation=ai_result.get('code_explanation', ''),
        viva_questions=json.dumps(ai_result.get('possible_viva_questions', []))
    )
    db.session.add(code_review)
    db.session.commit()

    return {
        'id': code_review.id,
        'filename': filename,
        'matched_claims': ai_result.get('matched_claims', []),
        'possible_mismatches': ai_result.get('possible_mismatches', []),
        'code_explanation': ai_result.get('code_explanation', ''),
        'possible_viva_questions': ai_result.get('possible_viva_questions', [])
    }
