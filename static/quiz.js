let QUESTIONS = [];
let step = 0;
const answers = []; // {question_id, option_id}

const elStep = document.getElementById("step");
const elOpts = document.getElementById("options");
const elPrev = document.getElementById("prev");
const elNext = document.getElementById("next");
const elProg = document.getElementById("progress");
const elResult = document.getElementById("result");
const elQuiz = document.getElementById("quiz");
const elProfile = document.getElementById("profile");
const elMatches = document.getElementById("matches");
const elRestart = document.getElementById("restart");

async function loadQuiz() {
  const res = await fetch("/api/quiz");
  const data = await res.json();
  QUESTIONS = data.questions;
  renderStep();
}

function renderStep() {
  const q = QUESTIONS[step];
  elStep.innerHTML = `<h3>${step+1}/${QUESTIONS.length} — ${q.title}</h3>`;
  elOpts.innerHTML = q.options.map(o =>
    `<label class="card"><input type="radio" name="ans" value="${o.id}"><span>${o.label}</span></label>`
  ).join("");

  const current = answers.find(a => a.question_id === q.id);
  if (current) {
    const radio = elOpts.querySelector(`input[value="${current.option_id}"]`);
    if (radio) radio.checked = true;
  }

  elNext.disabled = !current;
  elPrev.disabled = (step === 0);
  elProg.style.width = `${((step)/QUESTIONS.length)*100}%`;

  elOpts.querySelectorAll('input[name="ans"]').forEach(r => {
    r.addEventListener("change", () => {
      setAnswer(q.id, r.value);
      elNext.disabled = false;
    });
  });
}

function setAnswer(qid, oid) {
  const idx = answers.findIndex(a => a.question_id === qid);
  if (idx >= 0) answers[idx].option_id = oid;
  else answers.push({question_id: qid, option_id: oid});
}

elPrev.addEventListener("click", () => {
  if (step > 0) { step--; renderStep(); }
});

elNext.addEventListener("click", async () => {
  if (step < QUESTIONS.length - 1) {
    step++; renderStep();
  } else {
    // klaar → match opvragen
    await submitQuiz();
  }
});

elRestart.addEventListener("click", () => {
  step = 0; answers.length = 0;
  elResult.classList.add("hidden");
  elQuiz.classList.remove("hidden");
  renderStep();
});

async function submitQuiz() {
  const res = await fetch("/api/match", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({quiz_answers: answers})
  });
  if (!res.ok) {
    alert("Er ging iets mis met matchen. Seed eerst de database.");
    return;
  }
  const data = await res.json();
  showResult(data);
}

function showResult(data) {
  elQuiz.classList.add("hidden");
  elResult.classList.remove("hidden");

  // profiel (simpele balkjes)
  elProfile.innerHTML = `
    <div class="bars">
      ${Object.entries(data.user_profile).map(([k,v]) =>
        `<div class="bar"><span>${k}</span><div><i style="width:${v}%"></i></div></div>`
      ).join("")}
    </div>`;

  elMatches.innerHTML = data.matches.map(m => `
    <div class="card match">
      <h3>${m.wine.name}</h3>
      <p>${m.wine.region} — €${(m.wine.price_eur ?? 0).toFixed(2)}</p>
      <p><b>Waarom bij jou:</b> ${m.why}</p>
      <small>Similarity: ${(m.similarity*100).toFixed(1)}%</small>
      <div class="axis">
        ${Object.entries(m.wine.profile).map(([k,v]) => `<span>${k}:${Math.round(v)}</span>`).join(" ")}
      </div>
      <button class="primary">In winkelmand</button>
    </div>
  `).join("");
}

loadQuiz();