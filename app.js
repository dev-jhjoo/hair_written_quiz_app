const app = document.querySelector("#app");

const state = {
  data: null,
  selectedRoundId: null,
  quizQuestions: [],
  currentIndex: 0,
  selectedIndex: null,
  showResult: false,
  correctCount: 0,
  wrongQuestions: [],
};

const choiceLabels = ["①", "②", "③", "④"];

async function loadData() {
  try {
    const response = await fetch("data/questions.json");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    state.data = await response.json();
    renderHome();
  } catch (error) {
    renderShell(`
      <section class="card error">
        <h1>문제 데이터를 불러오지 못했습니다.</h1>
        <p>${error.message}</p>
      </section>
    `);
  }
}

function renderShell(content) {
  app.innerHTML = `<main class="app-shell">${content}</main>`;
}

function getRoundOptions() {
  const options = [];
  state.data.rounds.forEach((round) => {
    const count = state.data.questions.filter((question) => question.roundId === round.id).length;
    options.push(`<option value="${round.id}">${escapeHtml(round.title ?? `${round.date} 회차`)} (${count}문제)</option>`);
  });
  return options.join("");
}

function renderHome() {
  const issueCount = state.data.questions.filter((question) => question.hasTextExtractionIssue).length;
  renderShell(`
    <section class="card home-card">
      <div class="badge">✂️ 미용사 일반 필기</div>
      <h1>기출 문제풀이</h1>
      <p class="home-description">
        ${state.data.rounds.length}개 세트에서 추출한 ${state.data.totalQuestions}문제를 한 문제씩 풀어볼 수 있습니다.<br />
        답을 선택하면 바로 정답 여부와 실제 정답을 확인합니다.
      </p>
      <p class="source-credit">출처 | 무니쌤 미용교실(네이버 블로그)</p>
      <div class="home-controls">
        <div class="field">
          <label for="roundSelect">풀이 범위</label>
          <select id="roundSelect">${getRoundOptions()}</select>
        </div>
        <button class="primary-button" id="startButton">문제풀이 시작</button>
      </div>
      <div class="meta-grid">
        <div class="meta-box"><span class="meta-value">${state.data.rounds.length}</span><span class="meta-label">세트</span></div>
        <div class="meta-box"><span class="meta-value">${state.data.totalQuestions}</span><span class="meta-label">문제</span></div>
        <div class="meta-box"><span class="meta-value">${issueCount}</span><span class="meta-label">원본 확인 문제</span></div>
      </div>
    </section>
  `);

  if (!state.selectedRoundId && state.data.rounds.length > 0) {
    state.selectedRoundId = state.data.rounds[0].id;
  }
  const select = document.querySelector("#roundSelect");
  select.value = state.selectedRoundId;
  select.addEventListener("change", (event) => {
    state.selectedRoundId = event.target.value;
  });
  document.querySelector("#startButton").addEventListener("click", startQuiz);
}

function startQuiz() {
  const roundId = state.selectedRoundId || state.data.rounds[0]?.id;
  state.quizQuestions = state.data.questions.filter((question) => question.roundId === roundId);

  state.currentIndex = 0;
  state.selectedIndex = null;
  state.showResult = false;
  state.correctCount = 0;
  state.wrongQuestions = [];
  renderQuestion();
}

function renderQuestion() {
  if (state.currentIndex >= state.quizQuestions.length) {
    renderResult();
    return;
  }

  const question = state.quizQuestions[state.currentIndex];
  const progress = Math.round(((state.currentIndex + 1) / state.quizQuestions.length) * 100);
  const originalPdfButton = question.hasTextExtractionIssue
    ? `<a class="ghost-button" href="${question.sourcePdf}" target="_blank" rel="noreferrer">원본 PDF 보기</a>`
    : "";

  const choices = question.choices.map((choice, index) => {
    let className = "choice-button";
    if (state.showResult && index === question.answerIndex) {
      className += " correct";
    }
    if (state.showResult && index === state.selectedIndex && index !== question.answerIndex) {
      className += " wrong";
    }
    return `
      <button class="${className}" data-choice="${index}" ${state.showResult ? "disabled" : ""}>
        <span class="choice-number">${index + 1}</span>
        <span>${escapeHtml(choice)}</span>
      </button>
    `;
  }).join("");

  const warning = question.hasTextExtractionIssue
    ? `<div class="warning-box">이 문제의 선택지는 PDF에서 그림으로 들어가 있어 텍스트 추출이 어렵습니다. 선택 번호로 풀고, 필요하면 원본 PDF를 함께 확인하세요.</div>`
    : "";

  const feedback = state.showResult ? renderFeedback(question) : "";
  const nextLabel = state.currentIndex + 1 === state.quizQuestions.length ? "결과 보기" : "다음 문제";
  const nextButton = state.showResult ? `<button class="primary-button" id="nextButton">${nextLabel}</button>` : "";

  renderShell(`
    <section class="card">
      <div class="top-bar">
        <div>
          <div class="progress-text">${state.currentIndex + 1} / ${state.quizQuestions.length}</div>
          <div class="round-text">${escapeHtml(question.roundTitle || `${question.roundDate} 회차`)} · ${question.number}번</div>
        </div>
        ${originalPdfButton}
      </div>
      <div class="progress-track"><div class="progress-fill" style="width: ${progress}%"></div></div>
      <h2 class="question-title">Q${question.number}. ${escapeHtml(question.question)}</h2>
      ${warning}
      <div class="choice-list">${choices}</div>
      ${feedback}
      <div class="bottom-actions">
        <button class="secondary-button" id="homeButton">처음으로</button>
        ${nextButton}
      </div>
    </section>
  `);

  document.querySelectorAll("[data-choice]").forEach((button) => {
    button.addEventListener("click", () => selectAnswer(Number(button.dataset.choice)));
  });
  document.querySelector("#homeButton").addEventListener("click", renderHome);
  const next = document.querySelector("#nextButton");
  if (next) {
    next.addEventListener("click", goNext);
  }
}

function renderFeedback(question) {
  const isCorrect = state.selectedIndex === question.answerIndex;
  const correctLabel = choiceLabels[question.answerIndex] ?? `${question.answerIndex + 1}번`;
  const correctChoice = question.choices[question.answerIndex];
  const explanation = question.explanation
    ? `<p class="explanation">${escapeHtml(question.explanation)}</p>`
    : "";

  if (isCorrect) {
    return `
      <div class="feedback correct">
        <strong>정답입니다!</strong>
        <div>정답: ${correctLabel} ${escapeHtml(correctChoice)}</div>
        ${explanation}
      </div>
    `;
  }

  return `
    <div class="feedback wrong">
      <strong>틀렸습니다.</strong>
      <div>정답: ${correctLabel} ${escapeHtml(correctChoice)}</div>
      ${explanation}
    </div>
  `;
}

function selectAnswer(index) {
  if (state.showResult) return;
  const question = state.quizQuestions[state.currentIndex];
  state.selectedIndex = index;
  state.showResult = true;

  if (index === question.answerIndex) {
    state.correctCount += 1;
  } else {
    state.wrongQuestions.push(question);
  }

  renderQuestion();
}

function goNext() {
  state.currentIndex += 1;
  state.selectedIndex = null;
  state.showResult = false;
  renderQuestion();
}

function renderResult() {
  const total = state.quizQuestions.length;
  const percent = total === 0 ? 0 : Math.round((state.correctCount / total) * 100);
  const wrongList = state.wrongQuestions.slice(0, 10).map((question) => `
    <li>${escapeHtml(question.roundTitle || question.roundDate)} · ${question.number}번: ${escapeHtml(question.question)}</li>
  `).join("");

  renderShell(`
    <section class="card result-card">
      <div class="badge">풀이 완료</div>
      <h1>결과</h1>
      <div class="result-score">
        <span class="score-number">${percent}%</span>
        <p>총 ${total}문제 중 ${state.correctCount}문제를 맞혔습니다.</p>
      </div>
      ${state.wrongQuestions.length > 0 ? `
        <h2>오답 문제</h2>
        <p class="round-text">최대 10개까지만 표시합니다.</p>
        <ol>${wrongList}</ol>
      ` : `<p>틀린 문제가 없습니다. 좋습니다!</p>`}
      <div class="result-actions">
        <button class="primary-button" id="retryButton">다시 풀기</button>
        <button class="secondary-button" id="homeButton">처음으로</button>
      </div>
    </section>
  `);

  document.querySelector("#retryButton").addEventListener("click", startQuiz);
  document.querySelector("#homeButton").addEventListener("click", renderHome);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

renderShell(`
  <section class="card loading">
    <h1>문제를 불러오는 중입니다.</h1>
  </section>
`);
loadData();
