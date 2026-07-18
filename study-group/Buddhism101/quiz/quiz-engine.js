(function(){
"use strict";
var ROUNDS = window.WLS_QUIZ_ROUNDS || [];
var ENDPOINT = window.WLS_QUIZ_ENDPOINT || "";
var LETTERS = ["A","B","C","D","E","F"];
var state = { roundIdx: -1, qIdx: 0, score: 0, correct: 0, answers: [], locked: false };
var done = {};

function qs(s){ return document.querySelector(s); }
function qsa(s){ return Array.prototype.slice.call(document.querySelectorAll(s)); }
function esc(s){ return String(s).replace(/[&<>"']/g, function(c){ return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]; }); }

function getName(){ return qs("#quizName").value.trim(); }

function renderGrid(){
  var grid = qs("#missionGrid");
  grid.innerHTML = ROUNDS.map(function(r, i){
    var count = (r.questions || []).length;
    return '<button class="mission" data-idx="' + i + '"' + (count === 0 ? " disabled" : "") + '>' +
      '<h3>' + esc(r.title) + '</h3>' +
      '<p>' + esc(r.range) + '　' + esc(r.theme) + '</p>' +
      (count === 0 ? '<p style="margin-top:6px;color:#b98">（題目準備中）</p>' : '') +
      '</button>';
  }).join("");
  qsa(".mission").forEach(function(btn){
    btn.addEventListener("click", function(){
      if (btn.disabled) return;
      if (!getName()){
        alert("請先在上方填寫姓名，再開始作答。");
        qs("#quizName").focus();
        return;
      }
      startRound(Number(btn.dataset.idx));
    });
  });
}

function startRound(idx){
  state.roundIdx = idx;
  state.qIdx = 0;
  state.score = 0;
  state.correct = 0;
  state.answers = [];
  state.locked = false;
  renderQuestion();
}

function currentRound(){ return ROUNDS[state.roundIdx]; }

function renderQuestion(){
  var round = currentRound();
  var total = round.questions.length;
  var q = round.questions[state.qIdx];
  state.locked = false;
  var html = '<div class="stage active game-panel">';
  html += '<h2>' + esc(round.title) + '　' + esc(round.theme) + '</h2>';
  html += '<div class="qmeta"><span>第 ' + (state.qIdx + 1) + ' 題／共 ' + total + ' 題</span><span>目前得分 ' + state.score + '</span></div>';
  html += '<div class="qbox"><span class="qtag">' + (q.type === "tf" ? "是非題" : "單選題") + '</span><b>' + esc(q.q) + '</b></div>';
  html += '<div class="choices" id="qChoices">';
  if (q.type === "tf"){
    html += '<div class="tfrow">';
    html += '<button class="choice" data-val="true"><span class="opt-letter">A</span>是</button>';
    html += '<button class="choice" data-val="false"><span class="opt-letter">B</span>非</button>';
    html += '</div>';
  } else {
    q.options.forEach(function(opt, i){
      html += '<button class="choice" data-val="' + i + '"><span class="opt-letter">' + LETTERS[i] + '</span>' + esc(opt) + '</button>';
    });
  }
  html += '</div>';
  html += '<div class="feedback" id="qFeedback">請選出您認為正確的答案。</div>';
  var isLast = state.qIdx >= total - 1;
  html += '<div class="navrow"><button class="game-btn" id="nextBtn" style="display:none">' + (isLast ? "看結果 →" : "下一題 →") + '</button><button class="game-btn secondary" id="backGrid">回小考首頁</button></div>';
  html += '</div>';
  qs("#stageArea").innerHTML = html;
  qs("#backGrid").onclick = function(){ qs("#stageArea").innerHTML = ""; };
  qs("#nextBtn").onclick = function(){
    if (state.qIdx < currentRound().questions.length - 1){
      state.qIdx += 1;
      renderQuestion();
    } else {
      finishRound();
    }
  };
  qsa("#qChoices .choice").forEach(function(btn){
    btn.addEventListener("click", function(){ handleAnswer(btn, q); });
  });
}

function handleAnswer(btn, q){
  if (state.locked) return;
  state.locked = true;
  var chosenVal = btn.dataset.val === "true" ? true : (btn.dataset.val === "false" ? false : Number(btn.dataset.val));
  var isCorrect = (q.type === "tf") ? (chosenVal === q.answer) : (chosenVal === q.answer);
  btn.classList.add(isCorrect ? "good" : "bad");
  if (!isCorrect){
    qsa("#qChoices .choice").forEach(function(b){
      var v = b.dataset.val === "true" ? true : (b.dataset.val === "false" ? false : Number(b.dataset.val));
      if (v === q.answer) b.classList.add("good");
    });
  }
  qsa("#qChoices .choice").forEach(function(b){ b.disabled = true; });
  qs("#qFeedback").innerHTML = (isCorrect ? "✅ 答對了。" : "❌ 再想想。") + " " + esc(q.explain || "") + (q.source ? "（出自：" + esc(q.source) + "）" : "");
  if (isCorrect){ state.score += 1; state.correct += 1; }
  state.answers.push({ q: state.qIdx + 1, correct: isCorrect });
  var nextBtn = qs("#nextBtn");
  if (nextBtn){
    nextBtn.style.display = "inline-block";
    nextBtn.focus();
  }
}

function finishRound(){
  var round = currentRound();
  var total = round.questions.length;
  done[state.roundIdx] = true;
  qsa(".mission")[state.roundIdx] && qsa(".mission")[state.roundIdx].classList.add("done");
  var html = '<div class="stage active game-panel"><div class="finish">';
  html += '<div class="finish-card"><h3>' + esc(round.title) + ' 完成</h3><div class="finish-score">' + state.correct + ' / ' + total + '</div><p class="stage-lead" style="margin-top:8px">答對 ' + state.correct + ' 題，共 ' + total + ' 題。</p><p class="submit-state" id="submitState">正在送出成績…</p></div>';
  html += '<div class="finish-card"><h3>接下來</h3><ul style="margin:0;padding-left:20px;color:var(--sub);line-height:1.9"><li>可以回小考首頁挑戰其他單元</li><li>也可以重新作答本單元，加深印象</li><li>全部二十個單元都通過後，可申請「佛法概論」結業證書</li></ul><div class="navrow"><button class="game-btn" id="retakeBtn">重新作答本單元</button><button class="game-btn secondary" id="backGrid2">回小考首頁</button></div></div>';
  html += '</div></div>';
  qs("#stageArea").innerHTML = html;
  qs("#retakeBtn").onclick = function(){ startRound(state.roundIdx); };
  qs("#backGrid2").onclick = function(){ qs("#stageArea").innerHTML = ""; };
  submitResult(round, total);
}

function submitResult(round, total){
  var stateEl = qs("#submitState");
  if (!ENDPOINT || ENDPOINT.indexOf("REPLACE_WITH") === 0){
    if (stateEl) stateEl.textContent = "（尚未設定後台網址，成績僅顯示於畫面，未送出紀錄）";
    return;
  }
  var payload = {
    name: getName(),
    course: window.WLS_QUIZ_COURSE || "",
    round: round.id,
    roundTitle: round.title,
    score: state.score,
    total: total,
    correct: state.correct,
    answers: state.answers
  };
  fetch(ENDPOINT, {
    method: "POST",
    mode: "no-cors",
    headers: { "Content-Type": "text/plain;charset=utf-8" },
    body: JSON.stringify(payload)
  }).then(function(){
    if (stateEl) stateEl.textContent = "✅ 成績已送出紀錄。";
  }).catch(function(){
    if (stateEl) stateEl.textContent = "⚠️ 成績送出失敗，請確認網路連線後重新作答一次本單元。";
  });
}

renderGrid();
})();
