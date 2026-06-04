from pathlib import Path
import fitz
import re
import json
import shutil
import zipfile
from datetime import datetime

BASE = Path('/mnt/data')
OUT = BASE / 'hair_written_quiz_app'
if OUT.exists():
    shutil.rmtree(OUT)
(OUT / 'data').mkdir(parents=True)
(OUT / 'pdfs').mkdir(parents=True)
(OUT / 'scripts').mkdir(parents=True)

PDFS = [
    BASE / '미용사(일반)20100711(학생용).pdf',
    BASE / '미용사(일반)20101003(학생용).pdf',
    BASE / '미용사(일반)20110417(학생용).pdf',
    BASE / '미용사(일반)20110731(학생용).pdf',
    BASE / '미용사(일반)20111009(학생용).pdf',
]
ans_map = {'①':0,'②':1,'③':2,'④':3}
circled = ['①','②','③','④']


def extract_text(path: Path) -> str:
    doc = fitz.open(str(path))
    return '\n'.join(page.get_text('text') for page in doc)


def clean_main_text(s: str) -> str:
    s = s.replace('\u00a0', ' ')
    lines = []
    for line in s.splitlines():
        t = line.strip()
        if not t:
            lines.append('')
            continue
        if t.startswith('미용사(일반)'):
            continue
        if t.startswith('◐'):
            continue
        if t.startswith('전자문제집 CBT :'):
            continue
        if t.startswith('최강 자격증'):
            continue
        if re.match(r'^[1-5]과목\s*:', t):
            continue
        if t.startswith('전자문제집 CBT 홈페이지'):
            break
        if t.startswith('기출문제 및 해설집') or t.startswith('전자문제집 CBT 앱') or t.startswith('전자문제집 CBT란?'):
            break
        lines.append(line)
    return '\n'.join(lines)


def extract_answers(fulltext: str) -> dict[int, int]:
    s = fulltext.replace('\u00a0', ' ')
    idx = s.find('전자문제집 CBT 홈페이지')
    tail = s[idx:] if idx != -1 else s[-2500:]
    tokens = re.findall(r'(?<!\d)([1-9]|[1-5][0-9]|60)(?!\d)|([①②③④])', tail)
    flat = [a or b for a, b in tokens]
    answers = {}
    i = 0
    while i < len(flat):
        if re.fullmatch(r'[0-9]+', flat[i]):
            nums = []
            j = i
            while j < len(flat) and re.fullmatch(r'[0-9]+', flat[j]):
                nums.append(int(flat[j]))
                j += 1
            ans = []
            k = j
            while k < len(flat) and flat[k] in ans_map and len(ans) < len(nums):
                ans.append(flat[k])
                k += 1
            if nums and len(nums) == len(ans):
                for n, a in zip(nums, ans):
                    if 1 <= n <= 60:
                        answers[n] = ans_map[a]
                i = k
                continue
        i += 1
    return answers


def normalize_text(x: str) -> str:
    x = x.replace('\u00a0', ' ')
    x = re.sub(r'미용사\(일반\).*?www\.combt\.com', '', x)
    x = re.sub(r'\s+', ' ', x).strip()
    # Join awkward line-wrap spaces frequently produced by the PDF extractor.
    # Keep this conservative; Korean phrase spacing in the original may already be inconsistent.
    replacements = {
        ' 것 은': ' 것은',
        ' 되 는': ' 되는',
        ' 하 는': ' 하는',
        ' 있 는': ' 있는',
        ' 없 는': ' 없는',
        ' 이 다': '이다',
        ' 한 다': '한다',
        ' 했 다': '했다',
    }
    for a, b in replacements.items():
        x = x.replace(a, b)
    return x


def round_info_from_filename(path: Path) -> dict:
    m = re.search(r'(\d{8})', path.name)
    raw = m.group(1) if m else 'unknown'
    label = f'{raw[:4]}-{raw[4:6]}-{raw[6:]}' if raw != 'unknown' else path.stem
    return {
        'id': raw,
        'date': label,
        'title': f'{label} 미용사(일반) 필기',
        'pdf': f'pdfs/{raw}.pdf',
        'originalName': path.name,
    }


def extract_questions(path: Path) -> tuple[list[dict], dict]:
    full = extract_text(path)
    answers = extract_answers(full)
    main = clean_main_text(full)
    pattern = re.compile(r'(?m)^\s*(\d{1,2})\.\s')
    matches = list(pattern.finditer(main))
    info = round_info_from_filename(path)
    questions = []
    for idx, m in enumerate(matches):
        n = int(m.group(1))
        if not (1 <= n <= 60):
            continue
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(main)
        block = main[m.end():end].strip()
        block = re.sub(r'\n\s*\n+', '\n', block)
        parts = re.split(r'([①②③④])', block)
        choices = ['', '', '', '']
        if len(parts) > 1:
            question_text = parts[0]
            for sym, text in zip(parts[1::2], parts[2::2]):
                choices[ans_map[sym]] += text
        else:
            question_text = block
        choices = [normalize_text(c) for c in choices]
        has_text_issue = any(not c for c in choices)
        if has_text_issue:
            choices = [c or f'{circled[i]}번 선택지 - 원본 PDF에서 그림으로 확인' for i, c in enumerate(choices)]
        questions.append({
            'id': f'{info["id"]}-{n:02d}',
            'roundId': info['id'],
            'roundDate': info['date'],
            'roundTitle': info['title'],
            'number': n,
            'question': normalize_text(question_text),
            'choices': choices,
            'answerIndex': answers.get(n),
            'answerLabel': circled[answers[n]] if n in answers else None,
            'sourcePdf': info['pdf'],
            'sourceFile': path.name,
            'hasTextExtractionIssue': has_text_issue,
        })
    return questions, info

all_questions = []
rounds = []
report = {
    'generatedAt': datetime.now().isoformat(timespec='seconds'),
    'sourceCount': len(PDFS),
    'rounds': [],
    'warnings': [],
}

for path in PDFS:
    qs, info = extract_questions(path)
    all_questions.extend(qs)
    rounds.append(info)
    safe_pdf = OUT / 'pdfs' / f'{info["id"]}.pdf'
    shutil.copyfile(path, safe_pdf)
    issue_numbers = [q['number'] for q in qs if q['hasTextExtractionIssue']]
    missing_answers = [q['number'] for q in qs if q['answerIndex'] is None]
    report['rounds'].append({
        **info,
        'questionCount': len(qs),
        'textExtractionIssueNumbers': issue_numbers,
        'missingAnswerNumbers': missing_answers,
    })
    if len(qs) != 60:
        report['warnings'].append(f'{path.name}: expected 60 questions, extracted {len(qs)}')
    for n in missing_answers:
        report['warnings'].append(f'{path.name}: missing answer for question {n}')
    for n in issue_numbers:
        report['warnings'].append(f'{path.name}: question {n} has image/blank choice text; original PDF link is shown in app')

bundle = {
    'examTitle': '미용사(일반) 필기 기출문제',
    'description': 'Uploaded PDF question bank converted for a static quiz web app.',
    'totalQuestions': len(all_questions),
    'rounds': rounds,
    'questions': all_questions,
}
(OUT / 'data' / 'questions.json').write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding='utf-8')
(OUT / 'data' / 'extract-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

# Write app files
(OUT / 'index.html').write_text('''<!doctype html>
<html lang="ko">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="미용사 일반 필기 기출문제 풀이 웹앱" />
    <title>미용사 일반 필기 문제풀이</title>
    <link rel="stylesheet" href="styles.css" />
  </head>
  <body>
    <div id="app"></div>
    <script src="app.js" type="module"></script>
  </body>
</html>
''', encoding='utf-8')

(OUT / 'styles.css').write_text('''@font-face {
  font-family: system-ui;
  src: local("Arial");
}

:root {
  --bg: #f8f1e8;
  --card: #fffdf9;
  --text: #2b211a;
  --muted: #7a6a5f;
  --primary: #8c5a37;
  --primary-dark: #6f4328;
  --line: #eadfD4;
  --soft: #fbf6f0;
  --correct-bg: #e9f8ef;
  --correct: #197847;
  --wrong-bg: #fdecee;
  --wrong: #c8374a;
  --focus: rgba(140, 90, 55, 0.18);
}

* { box-sizing: border-box; }

body {
  margin: 0;
  min-height: 100vh;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: radial-gradient(circle at top, #fff7ec 0%, var(--bg) 42%, #f3e2d2 100%);
  color: var(--text);
}

button, select {
  font: inherit;
}

button {
  border: 0;
}

.app-shell {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.card {
  width: min(100%, 780px);
  background: rgba(255, 253, 249, 0.94);
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 28px;
  box-shadow: 0 18px 60px rgba(64, 42, 24, 0.14);
  padding: 32px;
  backdrop-filter: blur(10px);
}

.home-card {
  text-align: center;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 18px;
  padding: 8px 14px;
  border-radius: 999px;
  background: #fff1df;
  color: var(--primary-dark);
  font-weight: 800;
  font-size: 14px;
}

h1, h2, p {
  margin-top: 0;
}

h1 {
  margin-bottom: 10px;
  font-size: clamp(30px, 6vw, 48px);
  letter-spacing: -0.04em;
}

.home-description {
  color: var(--muted);
  line-height: 1.7;
  margin-bottom: 28px;
}

.home-controls {
  display: grid;
  gap: 14px;
  margin: 0 auto 18px;
  max-width: 440px;
}

.field {
  text-align: left;
}

.field label {
  display: block;
  margin-bottom: 8px;
  color: var(--muted);
  font-size: 14px;
  font-weight: 700;
}

select {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: #fff;
  padding: 14px 16px;
  color: var(--text);
  outline: none;
}

select:focus, button:focus-visible {
  box-shadow: 0 0 0 4px var(--focus);
}

.primary-button, .secondary-button, .ghost-button {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  border-radius: 16px;
  min-height: 52px;
  padding: 14px 22px;
  cursor: pointer;
  font-weight: 800;
  transition: transform 0.12s ease, background 0.12s ease, opacity 0.12s ease;
}

.primary-button {
  width: 100%;
  background: var(--primary);
  color: #fff;
}

.primary-button:hover {
  background: var(--primary-dark);
  transform: translateY(-1px);
}

.secondary-button {
  background: #efe1d2;
  color: var(--primary-dark);
}

.ghost-button {
  background: transparent;
  color: var(--primary-dark);
  text-decoration: underline;
  min-height: auto;
  padding: 8px 10px;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 24px;
}

.meta-box {
  padding: 14px;
  background: var(--soft);
  border: 1px solid var(--line);
  border-radius: 18px;
}

.meta-value {
  display: block;
  font-size: 22px;
  font-weight: 900;
}

.meta-label {
  color: var(--muted);
  font-size: 13px;
}

.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 18px;
}

.progress-text {
  margin-bottom: 8px;
  color: var(--primary-dark);
  font-weight: 900;
}

.round-text {
  color: var(--muted);
  font-size: 14px;
}

.progress-track {
  height: 10px;
  border-radius: 999px;
  overflow: hidden;
  background: #efe1d2;
  margin: 8px 0 24px;
}

.progress-fill {
  height: 100%;
  background: var(--primary);
  width: 0%;
  transition: width 0.25s ease;
}

.question-title {
  font-size: clamp(21px, 4vw, 28px);
  line-height: 1.55;
  letter-spacing: -0.025em;
  margin-bottom: 22px;
}

.choice-list {
  display: grid;
  gap: 12px;
}

.choice-button {
  width: 100%;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  text-align: left;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: #fff;
  color: var(--text);
  padding: 16px;
  cursor: pointer;
  line-height: 1.55;
  transition: transform 0.12s ease, border-color 0.12s ease, background 0.12s ease;
}

.choice-button:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: #d1ad8f;
  background: #fffaf4;
}

.choice-button:disabled {
  cursor: default;
}

.choice-number {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #f1e2d4;
  color: var(--primary-dark);
  font-weight: 900;
}

.choice-button.correct {
  border-color: rgba(25, 120, 71, 0.55);
  background: var(--correct-bg);
}

.choice-button.correct .choice-number {
  background: var(--correct);
  color: #fff;
}

.choice-button.wrong {
  border-color: rgba(200, 55, 74, 0.55);
  background: var(--wrong-bg);
}

.choice-button.wrong .choice-number {
  background: var(--wrong);
  color: #fff;
}

.feedback {
  margin-top: 20px;
  border-radius: 18px;
  padding: 18px;
  line-height: 1.6;
}

.feedback.correct {
  background: var(--correct-bg);
  color: var(--correct);
}

.feedback.wrong {
  background: var(--wrong-bg);
  color: var(--wrong);
}

.feedback strong {
  display: block;
  margin-bottom: 8px;
  font-size: 18px;
}

.warning-box {
  margin: 18px 0;
  padding: 14px;
  border-radius: 16px;
  background: #fff6d9;
  border: 1px solid #f3d58d;
  color: #705018;
  line-height: 1.6;
}

.bottom-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 22px;
}

.result-score {
  margin: 22px 0;
  padding: 24px;
  border-radius: 22px;
  background: var(--soft);
  border: 1px solid var(--line);
  text-align: center;
}

.score-number {
  display: block;
  font-size: clamp(42px, 9vw, 72px);
  font-weight: 950;
  color: var(--primary-dark);
  letter-spacing: -0.05em;
}

.result-actions {
  display: grid;
  gap: 10px;
}

.loading, .error {
  text-align: center;
}

@media (max-width: 640px) {
  .app-shell {
    padding: 14px;
    align-items: stretch;
  }

  .card {
    padding: 24px 18px;
    border-radius: 22px;
  }

  .top-bar {
    display: block;
  }

  .meta-grid {
    grid-template-columns: 1fr;
  }

  .bottom-actions {
    grid-template-columns: 1fr;
  }
}
''', encoding='utf-8')

(OUT / 'app.js').write_text('''const app = document.querySelector("#app");

const state = {
  data: null,
  selectedRoundId: "all",
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
  const options = [`<option value="all">전체 회차 (${state.data.totalQuestions}문제)</option>`];
  state.data.rounds.forEach((round) => {
    const count = state.data.questions.filter((question) => question.roundId === round.id).length;
    options.push(`<option value="${round.id}">${round.date} 회차 (${count}문제)</option>`);
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
        5개 회차 PDF에서 추출한 ${state.data.totalQuestions}문제를 한 문제씩 풀어볼 수 있습니다.<br />
        답을 선택하면 바로 정답 여부와 실제 정답을 확인합니다.
      </p>
      <div class="home-controls">
        <div class="field">
          <label for="roundSelect">풀이 범위</label>
          <select id="roundSelect">${getRoundOptions()}</select>
        </div>
        <button class="primary-button" id="startButton">문제풀이 시작</button>
      </div>
      <div class="meta-grid">
        <div class="meta-box"><span class="meta-value">5</span><span class="meta-label">회차</span></div>
        <div class="meta-box"><span class="meta-value">${state.data.totalQuestions}</span><span class="meta-label">문제</span></div>
        <div class="meta-box"><span class="meta-value">${issueCount}</span><span class="meta-label">원본 확인 문제</span></div>
      </div>
    </section>
  `);

  const select = document.querySelector("#roundSelect");
  select.value = state.selectedRoundId;
  select.addEventListener("change", (event) => {
    state.selectedRoundId = event.target.value;
  });
  document.querySelector("#startButton").addEventListener("click", startQuiz);
}

function startQuiz() {
  state.quizQuestions = state.selectedRoundId === "all"
    ? [...state.data.questions]
    : state.data.questions.filter((question) => question.roundId === state.selectedRoundId);

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
          <div class="round-text">${question.roundDate} 회차 · ${question.number}번</div>
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

  if (isCorrect) {
    return `
      <div class="feedback correct">
        <strong>정답입니다!</strong>
        <div>정답: ${correctLabel} ${escapeHtml(correctChoice)}</div>
      </div>
    `;
  }

  return `
    <div class="feedback wrong">
      <strong>틀렸습니다.</strong>
      <div>정답: ${correctLabel} ${escapeHtml(correctChoice)}</div>
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
    <li>${question.roundDate} · ${question.number}번: ${escapeHtml(question.question)}</li>
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
''', encoding='utf-8')

(OUT / 'README.md').write_text('''# 미용사(일반) 필기 문제풀이 웹앱

첨부된 5개 회차 PDF를 `questions.json`으로 변환해서 만든 정적 웹앱입니다.
백엔드 없이 `HTML + CSS + JavaScript + JSON`만 사용합니다.

## 포함 내용

- 5개 회차
- 총 300문제
- 문제 1개씩 풀이
- 4지선다 선택
- 선택 즉시 정답/오답 표시
- 다음 문제 이동
- 마지막 점수 표시
- 회차별 풀이 또는 전체 풀이
- 원본 PDF 링크 제공

## 파일 구조

```txt
hair_written_quiz_app/
├─ index.html
├─ app.js
├─ styles.css
├─ data/
│  ├─ questions.json
│  └─ extract-report.json
├─ pdfs/
│  ├─ 20100711.pdf
│  ├─ 20101003.pdf
│  ├─ 20110417.pdf
│  ├─ 20110731.pdf
│  └─ 20111009.pdf
└─ scripts/
   └─ extract-pdf-questions.py
```

## 로컬 실행

정적 파일이므로 아래 중 하나로 실행하면 됩니다.

```bash
python -m http.server 5173
```

브라우저에서 다음 주소로 접속합니다.

```txt
http://localhost:5173
```

## Cloudflare Pages 배포

빌드 과정이 없는 정적 사이트입니다.

- Framework preset: None
- Build command: 비워두기
- Build output directory: `/` 또는 프로젝트 루트

GitHub에 이 폴더를 올린 뒤 Cloudflare Pages에서 저장소를 연결하면 됩니다.

## 추출 참고사항

`2010-10-03` 회차의 1번 문제는 선택지가 그림 형태로 들어 있어 텍스트 추출이 되지 않았습니다.
앱에서는 해당 문제에 원본 PDF 확인 안내를 표시합니다.
''', encoding='utf-8')

# Put a reproducible extraction script in the deliverable.
(OUT / 'scripts' / 'extract-pdf-questions.py').write_text(Path('/tmp/build_quiz_app.py').read_text(encoding='utf-8'), encoding='utf-8')

# Add a very small _headers file for Cloudflare cache behavior.
(OUT / '_headers').write_text('''/*
  X-Content-Type-Options: nosniff

/data/questions.json
  Cache-Control: public, max-age=300
''', encoding='utf-8')

zip_path = BASE / 'hair_written_quiz_app.zip'
if zip_path.exists():
    zip_path.unlink()
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for file in OUT.rglob('*'):
        if file.is_file():
            zf.write(file, file.relative_to(OUT.parent))

print(json.dumps({
    'outputDir': str(OUT),
    'zip': str(zip_path),
    'totalQuestions': len(all_questions),
    'warnings': report['warnings'],
}, ensure_ascii=False, indent=2))
