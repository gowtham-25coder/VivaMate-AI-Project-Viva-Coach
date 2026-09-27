/**
 * VivaMate - AI Project Viva Coach Client JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
  initDropzones();
  initTabs();
  initVivaStudio();
});

/* Tab Switching Logic */
function initTabs() {
  const tabBtns = document.querySelectorAll('.tab-btn');
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-tab');
      const parent = btn.closest('.upload-card-wrapper') || document;
      
      parent.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      parent.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
      
      btn.classList.add('active');
      const targetContent = parent.querySelector(`#${targetId}`);
      if (targetContent) {
        targetContent.style.display = 'block';
      }
    });
  });
}

/* Drag and Drop File Upload */
function initDropzones() {
  const dropzones = document.querySelectorAll('.upload-dropzone');
  dropzones.forEach(zone => {
    const input = zone.querySelector('input[type="file"]');
    if (!input) return;

    zone.addEventListener('click', () => input.click());

    zone.addEventListener('dragover', (e) => {
      e.preventDefault();
      zone.classList.add('dragover');
    });

    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));

    zone.addEventListener('drop', (e) => {
      e.preventDefault();
      zone.classList.remove('dragover');
      if (e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        updateDropzoneLabel(zone, input.files[0].name);
      }
    });

    input.addEventListener('change', () => {
      if (input.files.length) {
        updateDropzoneLabel(zone, input.files[0].name);
      }
    });
  });
}

function updateDropzoneLabel(zone, filename) {
  const titleEl = zone.querySelector('.upload-title');
  if (titleEl) {
    titleEl.textContent = `Selected: ${filename}`;
  }
}

/* Interactive Viva Studio Logic */
let currentSessionId = null;
let currentQuestionIndex = 1;
let totalQuestionsCount = 10;
let currentQuestionId = null;

function initVivaStudio() {
  const vivaCard = document.getElementById('viva-question-card');
  if (!vivaCard) return;

  currentSessionId = vivaCard.getAttribute('data-session-id');
  totalQuestionsCount = parseInt(vivaCard.getAttribute('data-total-questions') || 10);
  
  loadVivaQuestion(1);

  // Event Listeners
  const submitBtn = document.getElementById('btn-submit-answer');
  const skipBtn = document.getElementById('btn-skip-question');
  const nextBtn = document.getElementById('btn-next-question');

  if (submitBtn) {
    submitBtn.addEventListener('click', submitVivaAnswer);
  }

  if (skipBtn) {
    skipBtn.addEventListener('click', skipVivaQuestion);
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      if (currentQuestionIndex < totalQuestionsCount) {
        loadVivaQuestion(currentQuestionIndex + 1);
      } else {
        window.location.href = `/viva/${currentSessionId}/summary`;
      }
    });
  }
}

async function loadVivaQuestion(index) {
  currentQuestionIndex = index;
  const feedbackCard = document.getElementById('feedback-card');
  if (feedbackCard) feedbackCard.style.display = 'none';

  const answerInput = document.getElementById('student-answer-input');
  if (answerInput) {
    answerInput.value = '';
    answerInput.disabled = false;
  }

  const submitBtn = document.getElementById('btn-submit-answer');
  const skipBtn = document.getElementById('btn-skip-question');
  const nextBtn = document.getElementById('btn-next-question');

  if (submitBtn) submitBtn.style.display = 'inline-flex';
  if (skipBtn) skipBtn.style.display = 'inline-flex';
  if (nextBtn) nextBtn.style.display = 'none';

  try {
    const res = await fetch(`/api/viva/${currentSessionId}/question/${index}`);
    const data = await res.json();

    if (data.error) {
      alert(data.error);
      return;
    }

    currentQuestionId = data.question_id;

    // Update UI elements
    document.getElementById('q-number-badge').textContent = `Question ${data.question_number} of ${data.total_questions}`;
    document.getElementById('q-category-badge').textContent = data.category;
    document.getElementById('q-difficulty-badge').textContent = data.difficulty;
    document.getElementById('q-text-heading').textContent = data.question_text;
    
    // Update progress bar
    const progressPercent = (index / data.total_questions) * 100;
    const progressFill = document.getElementById('viva-progress-fill');
    if (progressFill) progressFill.style.width = `${progressPercent}%`;

    // If already answered
    if (data.already_answered && data.previous_answer) {
      if (answerInput) {
        answerInput.value = data.previous_answer.student_answer || '';
        answerInput.disabled = true;
      }
      renderFeedback(data.previous_answer);
      if (submitBtn) submitBtn.style.display = 'none';
      if (skipBtn) skipBtn.style.display = 'none';
      if (nextBtn) {
        nextBtn.style.display = 'inline-flex';
        nextBtn.textContent = (index === totalQuestionsCount) ? 'Finish Viva Exam' : 'Next Question';
      }
    }
  } catch (err) {
    console.error('Error fetching question:', err);
  }
}

async function submitVivaAnswer() {
  const answerInput = document.getElementById('student-answer-input');
  const studentAnswer = answerInput ? answerInput.value.trim() : '';

  if (!studentAnswer) {
    alert('Please type an answer before submitting.');
    return;
  }

  const submitBtn = document.getElementById('btn-submit-answer');
  const skipBtn = document.getElementById('btn-skip-question');
  const nextBtn = document.getElementById('btn-next-question');

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = 'Evaluating with AI...';
  }
  if (skipBtn) skipBtn.disabled = true;

  try {
    const response = await fetch(`/api/viva/${currentSessionId}/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question_id: currentQuestionId,
        student_answer: studentAnswer
      })
    });

    const result = await response.json();

    if (result.error) {
      alert(result.error);
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit Answer';
      }
      if (skipBtn) skipBtn.disabled = false;
      return;
    }

    if (answerInput) answerInput.disabled = true;
    if (submitBtn) submitBtn.style.display = 'none';
    if (skipBtn) skipBtn.style.display = 'none';

    renderFeedback(result.feedback);

    if (nextBtn) {
      nextBtn.style.display = 'inline-flex';
      nextBtn.textContent = (currentQuestionIndex === totalQuestionsCount) ? 'Finish Viva Exam' : 'Next Question';
    }

    // Update top header average score if present
    const avgScoreSpan = document.getElementById('session-avg-score');
    if (avgScoreSpan && result.session_average !== undefined) {
      avgScoreSpan.textContent = result.session_average;
    }

  } catch (err) {
    console.error('Error submitting answer:', err);
    alert('An unexpected error occurred while evaluating your answer.');
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Submit Answer';
    }
    if (skipBtn) skipBtn.disabled = false;
  }
}

async function skipVivaQuestion() {
  if (!confirm('Are you sure you want to skip this question?')) return;

  const submitBtn = document.getElementById('btn-submit-answer');
  const skipBtn = document.getElementById('btn-skip-question');
  const nextBtn = document.getElementById('btn-next-question');

  try {
    const res = await fetch(`/api/viva/${currentSessionId}/skip`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question_id: currentQuestionId })
    });

    const result = await res.json();
    if (result.error) {
      alert(result.error);
      return;
    }

    if (currentQuestionIndex < totalQuestionsCount) {
      loadVivaQuestion(currentQuestionIndex + 1);
    } else {
      window.location.href = `/viva/${currentSessionId}/summary`;
    }
  } catch (err) {
    console.error('Error skipping question:', err);
  }
}

function renderFeedback(feedback) {
  const feedbackCard = document.getElementById('feedback-card');
  if (!feedbackCard) return;

  document.getElementById('fb-score').textContent = `${feedback.score}/10`;
  document.getElementById('fb-correct').textContent = feedback.what_was_correct || 'N/A';
  document.getElementById('fb-missing').textContent = feedback.what_was_missing || 'N/A';
  document.getElementById('fb-improve').textContent = feedback.how_to_improve || 'N/A';
  document.getElementById('fb-suggested').textContent = feedback.suggested_answer || 'N/A';
  
  const followupEl = document.getElementById('fb-followup');
  const followupBox = document.getElementById('fb-followup-box');
  if (feedback.follow_up_question) {
    followupEl.textContent = feedback.follow_up_question;
    if (followupBox) followupBox.style.display = 'block';
  } else if (followupBox) {
    followupBox.style.display = 'none';
  }

  feedbackCard.style.display = 'block';
  feedbackCard.scrollIntoView({ behavior: 'smooth' });
}
