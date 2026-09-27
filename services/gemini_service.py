import os
import json
import re
import time
import sys
from flask import current_app
from google import genai
from google.genai import types

MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.1-flash-lite"
]

DEFAULT_USER_ERROR = "AI is temporarily busy. Please try again in a moment."

def is_gemini_configured():
    """Check if GEMINI_API_KEY is properly set in configuration or environment."""
    api_key = current_app.config.get('GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY', '')
    api_key = api_key.strip()
    return bool(api_key and api_key != 'your_api_key_here' and len(api_key) > 5)

def get_gemini_client():
    """Initialize and return the GenAI client if configured."""
    api_key = current_app.config.get('GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY', '')
    api_key = api_key.strip()
    if not is_gemini_configured():
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception as e:
        print(f"[Gemini API Error] Error initializing client: {e}", file=sys.stderr)
        return None

def extract_json_from_response(text):
    """Helper to safely extract JSON object/array from Gemini output."""
    if not text:
        return None
    # Remove markdown code blocks if present
    cleaned = re.sub(r'```json\s*', '', text)
    cleaned = re.sub(r'```\s*$', '', cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback regex search for { ... } or [ ... ]
        json_match = re.search(r'(\{.*\}|\[.*\])', cleaned, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
    return None

def call_gemini(prompt):
    """
    Centralized helper function for calling Gemini API with fallback models and retry logic.
    Retries HTTP 503 up to 3 times (wait 2s, 4s, 8s) before switching models.
    Switches model immediately on 429 or 404.
    Returns response text string or None.
    """
    if not is_gemini_configured():
        print("[Gemini API Warning] GEMINI_API_KEY is not configured.", file=sys.stderr)
        return None

    client = get_gemini_client()
    if not client:
        print("[Gemini API Error] Failed to obtain GenAI client.", file=sys.stderr)
        return None

    delays = [2, 4, 8]

    for model_name in MODELS:
        print(f"[Gemini API] Attempting request using model: {model_name}")
        
        # Try initial call + up to 3 retries for 503
        for attempt in range(4):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                if response and response.text:
                    print(f"[Gemini API] Successfully generated response using model: {model_name}")
                    return response.text
                else:
                    print(f"[Gemini API Warning] Model {model_name} returned empty text response.", file=sys.stderr)
            except Exception as e:
                err_str = str(e)
                is_503 = "503" in err_str or "UNAVAILABLE" in err_str or "Service Unavailable" in err_str or "overloaded" in err_str
                is_429 = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "Quota" in err_str
                is_404 = "404" in err_str or "NOT_FOUND" in err_str

                print(f"[Gemini API Exception] Model '{model_name}' (Attempt {attempt+1}) failed: {err_str}", file=sys.stderr)

                if is_503:
                    if attempt < len(delays):
                        wait_sec = delays[attempt]
                        print(f"[Gemini API] 503 Service Unavailable encountered. Retrying '{model_name}' in {wait_sec}s... (Retry {attempt+1}/3)")
                        time.sleep(wait_sec)
                        continue
                    else:
                        print(f"[Gemini API] 503 persistent after retries for '{model_name}'. Switching to next model in fallback list.", file=sys.stderr)
                        break
                elif is_429:
                    print(f"[Gemini API] 429 Rate Limit / Quota exceeded for '{model_name}'. Switching to next model immediately.", file=sys.stderr)
                    break
                elif is_404:
                    print(f"[Gemini API] 404 Model Not Found for '{model_name}'. Switching to next model immediately.", file=sys.stderr)
                    break
                else:
                    print(f"[Gemini API] Unexpected exception for '{model_name}': {err_str}. Switching to next model.", file=sys.stderr)
                    break

    print("[Gemini API Error] All models in fallback list failed.", file=sys.stderr)
    return None

def analyze_project_and_generate_questions(extracted_text):
    """
    SINGLE GEMINI CALL FOR PROJECT UPLOAD:
    Analyzes project metadata AND generates 10 viva questions in ONE single AI request.
    """
    if not is_gemini_configured():
        return {'error': 'AI service is not configured. Add GEMINI_API_KEY to your .env file.'}

    prompt = f"""
You are an expert academic reviewer and senior university examiner.
Analyze the following project report text and return a single valid JSON object containing BOTH project metadata and 10 viva questions across 10 specific categories.

Report Text:
\"\"\"
{extracted_text[:35000]}
\"\"\"

Return ONLY a single valid JSON object with the exact structure below:
{{
  "title": "Clear concise project title",
  "problem_statement": "Detailed summary of the problem addressed",
  "objective": "Main goal and key objectives",
  "technologies": "Frameworks, libraries, tools used (comma separated)",
  "programming_languages": "Programming languages identified (comma separated)",
  "dataset": "Dataset used or data collection methods (if any)",
  "methodology": "Step-by-step approach and workflow",
  "algorithms": "Specific algorithms, models, or formulas used",
  "system_architecture": "Architecture, modules, and data flow design",
  "results": "Key outcomes, accuracy metrics, or achievements",
  "conclusion": "Final takeaways and future scope",
  "questions": [
    {{
      "question_number": 1,
      "category": "Basic",
      "difficulty": "Easy",
      "question_text": "Question text here..."
    }},
    {{
      "question_number": 2,
      "category": "Project Understanding",
      "difficulty": "Easy",
      "question_text": "Question text here..."
    }},
    {{
      "question_number": 3,
      "category": "Technical",
      "difficulty": "Medium",
      "question_text": "Question text here..."
    }},
    {{
      "question_number": 4,
      "category": "Algorithm",
      "difficulty": "Medium",
      "question_text": "Question text here..."
    }},
    {{
      "question_number": 5,
      "category": "Implementation",
      "difficulty": "Medium",
      "question_text": "Question text here..."
    }},
    {{
      "question_number": 6,
      "category": "Dataset",
      "difficulty": "Medium",
      "question_text": "Question text here..."
    }},
    {{
      "question_number": 7,
      "category": "Testing",
      "difficulty": "Medium",
      "question_text": "Question text here..."
    }},
    {{
      "question_number": 8,
      "category": "Result",
      "difficulty": "Medium",
      "question_text": "Question text here..."
    }},
    {{
      "question_number": 9,
      "category": "Challenging",
      "difficulty": "Hard",
      "question_text": "Question text here..."
    }},
    {{
      "question_number": 10,
      "category": "Future Enhancement",
      "difficulty": "Advanced",
      "question_text": "Question text here..."
    }}
  ]
}}
Do not add any markdown formatting outside the JSON string.
"""

    response_text = call_gemini(prompt)
    if not response_text:
        return {'error': DEFAULT_USER_ERROR}

    parsed = extract_json_from_response(response_text)
    if not parsed or not isinstance(parsed, dict) or 'title' not in parsed:
        print("[Gemini API Error] Failed to parse structured JSON from combined upload response.", file=sys.stderr)
        return {'error': DEFAULT_USER_ERROR}

    return parsed

def analyze_project_report(extracted_text):
    """
    Fallback helper: Analyze project report text using centralized call_gemini.
    """
    if not is_gemini_configured():
        return {'error': 'AI service is not configured. Add GEMINI_API_KEY to your .env file.'}

    prompt = f"""
You are an expert academic reviewer evaluating a college project report.
Analyze the following project report text and extract structured information into a valid JSON object.

Report Text:
\"\"\"
{extracted_text[:35000]}
\"\"\"

Return ONLY a single valid JSON object with the exact keys below:
{{
  "title": "Clear concise project title",
  "problem_statement": "Detailed summary of the problem addressed",
  "objective": "Main goal and key objectives",
  "technologies": "Frameworks, libraries, tools used (comma separated)",
  "programming_languages": "Programming languages identified (comma separated)",
  "dataset": "Dataset used or data collection methods (if any)",
  "methodology": "Step-by-step approach and workflow",
  "algorithms": "Specific algorithms, models, or formulas used",
  "system_architecture": "Architecture, modules, and data flow design",
  "results": "Key outcomes, accuracy metrics, or achievements",
  "conclusion": "Final takeaways and future scope"
}}
"""

    response_text = call_gemini(prompt)
    if not response_text:
        return {'error': DEFAULT_USER_ERROR}

    parsed = extract_json_from_response(response_text)
    if not parsed or not isinstance(parsed, dict):
        return {'error': DEFAULT_USER_ERROR}

    return parsed

def generate_viva_questions(project_info):
    """
    Generate 10 structured viva questions across required categories using centralized call_gemini.
    """
    if not is_gemini_configured():
        return {'error': 'AI service is not configured. Add GEMINI_API_KEY to your .env file.'}

    prompt = f"""
You are a senior university professor and external examiner conducting a Viva Voce exam.
Based on the following project analysis, generate exactly 10 comprehensive viva questions covering each of the specified 10 categories.

Project Information:
Title: {project_info.get('title', 'N/A')}
Problem Statement: {project_info.get('problem_statement', 'N/A')}
Objective: {project_info.get('objective', 'N/A')}
Technologies: {project_info.get('technologies', 'N/A')}
Programming Languages: {project_info.get('programming_languages', 'N/A')}
Dataset: {project_info.get('dataset', 'N/A')}
Methodology: {project_info.get('methodology', 'N/A')}
Algorithms: {project_info.get('algorithms', 'N/A')}
System Architecture: {project_info.get('system_architecture', 'N/A')}
Results: {project_info.get('results', 'N/A')}
Conclusion: {project_info.get('conclusion', 'N/A')}

Required 10 Question Categories (exactly 1 question per category):
1. Basic
2. Project Understanding
3. Technical
4. Algorithm
5. Implementation
6. Dataset
7. Testing
8. Result
9. Challenging
10. Future Enhancement

Return ONLY a valid JSON array of 10 objects:
[
  {{
    "question_number": 1,
    "category": "Basic",
    "difficulty": "Easy",
    "question_text": "Question text here..."
  }},
  ...
]
"""

    response_text = call_gemini(prompt)
    if not response_text:
        return {'error': DEFAULT_USER_ERROR}

    parsed = extract_json_from_response(response_text)
    if not isinstance(parsed, list) or len(parsed) == 0:
        return {'error': DEFAULT_USER_ERROR}

    return parsed

def evaluate_answer(project_context, question_info, student_answer):
    """
    Evaluate student's viva answer using centralized call_gemini.
    """
    if not is_gemini_configured():
        return {'error': 'AI service is not configured. Add GEMINI_API_KEY to your .env file.'}

    prompt = f"""
You are an expert viva examiner evaluating a student's live answer in a Project Viva Voce examination.

Project Context:
Title: {project_context.get('title', '')}
Technologies: {project_context.get('technologies', '')}
Algorithms: {project_context.get('algorithms', '')}
Methodology: {project_context.get('methodology', '')}

Viva Question:
Category: {question_info.get('category', '')}
Difficulty: {question_info.get('difficulty', '')}
Question: {question_info.get('question_text', '')}

Student's Answer:
\"{student_answer}\"

Evaluate the student's response thoroughly and objectively.
Return ONLY a valid JSON object with the following fields:
{{
  "score": 8.5,
  "what_was_correct": "Clear breakdown of what points the student nailed correctly.",
  "what_was_missing": "Important concepts, details, or depth the student left out.",
  "how_to_improve": "Specific advice on how to articulate or strengthen this answer in front of external examiners.",
  "suggested_answer": "An exemplary, model response tailored to this exact project viva question.",
  "confidence_level": "High" | "Medium" | "Low",
  "follow_up_question": "An intelligent follow-up question an examiner might ask next based on this answer."
}}

Rule for score: Float between 0.0 and 10.0 based on technical accuracy, completeness, and clarity.
If the student answer is empty, gibberish, or completely off topic, assign an appropriately low score (0-3).
"""

    response_text = call_gemini(prompt)
    if not response_text:
        return {'error': DEFAULT_USER_ERROR}

    parsed = extract_json_from_response(response_text)
    if not parsed or 'score' not in parsed:
        return {'error': DEFAULT_USER_ERROR}

    return parsed

def analyze_code_against_report(code_content, report_text):
    """
    Compare uploaded Python source code against report claims using centralized call_gemini.
    """
    if not is_gemini_configured():
        return {'error': 'AI service is not configured. Add GEMINI_API_KEY to your .env file.'}

    prompt = f"""
You are a senior software reviewer and academic viva evaluator comparing a Python implementation against a Project Report.

Python Source Code:
\"\"\"
{code_content[:25000]}
\"\"\"

Project Report Text / Summary:
\"\"\"
{report_text[:25000]}
\"\"\"

Perform a deep comparison checking for:
1. Algorithm named in report vs actual algorithm implemented in code.
2. Dataset mentioned in report vs dataset loaded in code.
3. Libraries mentioned in report vs actual imports in code.
4. Evaluation metrics described vs implemented.
5. Model training steps or logic execution flow.
6. Data preprocessing steps.

Return ONLY a valid JSON object with the following fields:
{{
  "matched_claims": [
    "Matched claim 1 description",
    "Matched claim 2 description"
  ],
  "possible_mismatches": [
    "Mismatch 1 detail (e.g. Report mentions CNN but code implements Random Forest)",
    "Mismatch 2 detail (if any)"
  ],
  "code_explanation": "Comprehensive technical summary explaining how the Python code is structured and how it maps to the report.",
  "possible_viva_questions": [
    "Code-specific viva question 1 based on actual implementation lines/functions",
    "Code-specific viva question 2",
    "Code-specific viva question 3",
    "Code-specific viva question 4"
  ]
}}
"""

    response_text = call_gemini(prompt)
    if not response_text:
        return {'error': DEFAULT_USER_ERROR}

    parsed = extract_json_from_response(response_text)
    if not parsed or 'code_explanation' not in parsed:
        return {'error': DEFAULT_USER_ERROR}

    return parsed
