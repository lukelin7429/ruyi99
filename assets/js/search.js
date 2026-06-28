/* 如意精舍 — 全站搜尋（純前端，零依賴） */
(function () {
  var btn = document.getElementById('siteSearchBtn');
  if (!btn) return;

  var INDEX_URL = window.RS_INDEX || '/search.json';
  var index = null, loading = false;
  var overlay = null, input = null, list = null, emptyEl = null;
  var rows = [], active = -1;

  var SECTIONS = {
    '': '首頁', bhikkhuni: '法師簡介', 'study-group': '讀書會', news: '法會資訊',
    videos: '影音', column: '專欄', learn: '學習園地', camps: '活動紀錄',
    'english-school': '英文學校'
  };

  function sectionOf(url) {
    var segs = (url || '').split('/').filter(Boolean);
    // 去掉可能的 BASE 前綴後，取第一段
    var seg = segs.length ? segs[0] : '';
    if (seg === 'ruyi99') seg = segs[1] || '';
    return SECTIONS.hasOwnProperty(seg) ? SECTIONS[seg] : (seg || '首頁');
  }

  function load() {
    if (index || loading) return Promise.resolve();
    loading = true;
    return fetch(INDEX_URL, { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        index = data.map(function (it) {
          var title = it.title || '', body = it.body || '';
          return {
            title: title, url: it.url, body: body, section: sectionOf(it.url),
            hay: (title + ' ' + body).toLowerCase()
          };
        });
        loading = false;
      })
      .catch(function () { loading = false; });
  }

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function highlight(text, words) {
    var out = esc(text);
    words.forEach(function (w) {
      if (!w) return;
      var re = new RegExp('(' + w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'ig');
      out = out.replace(re, '<mark>$1</mark>');
    });
    return out;
  }

  function snippet(body, words) {
    var lc = body.toLowerCase(), pos = -1;
    for (var i = 0; i < words.length; i++) {
      var p = lc.indexOf(words[i]);
      if (p !== -1 && (pos === -1 || p < pos)) pos = p;
    }
    if (pos > 40) body = '…' + body.slice(pos - 30);
    return body.length > 150 ? body.slice(0, 150) + '…' : body;
  }

  function search(q) {
    q = q.trim().toLowerCase();
    if (!q) return [];
    var words = q.split(/\s+/);
    var res = [];
    index.forEach(function (it) {
      var ok = true, score = 0;
      for (var i = 0; i < words.length; i++) {
        var w = words[i];
        if (it.hay.indexOf(w) === -1) { ok = false; break; }
        if (it.title.toLowerCase().indexOf(w) !== -1) score += 12;
        score += 1;
      }
      if (ok) res.push({ it: it, score: score });
    });
    res.sort(function (a, b) { return b.score - a.score; });
    return res.slice(0, 14).map(function (r) { return r.it; });
  }

  function render(q) {
    var results = q.trim() ? search(q) : [];
    var words = q.trim().toLowerCase().split(/\s+/);
    rows = results;
    active = results.length ? 0 : -1;
    if (!q.trim()) { list.innerHTML = ''; emptyEl.hidden = true; return; }
    if (!results.length) { list.innerHTML = ''; emptyEl.hidden = false; return; }
    emptyEl.hidden = true;
    list.innerHTML = results.map(function (it, i) {
      return '<li class="rs-item' + (i === 0 ? ' is-active' : '') + '" role="option" data-url="' + esc(it.url) + '">' +
        '<a href="' + esc(it.url) + '" tabindex="-1">' +
        '<span class="rs-sec">' + esc(it.section) + '</span>' +
        '<span class="rs-title">' + highlight(it.title, words) + '</span>' +
        (it.body ? '<span class="rs-snippet">' + highlight(snippet(it.body, words), words) + '</span>' : '') +
        '</a></li>';
    }).join('');
    Array.prototype.forEach.call(list.children, function (li, i) {
      li.addEventListener('mousemove', function () { setActive(i); });
    });
  }

  function setActive(i) {
    if (i < 0 || i >= rows.length) return;
    active = i;
    Array.prototype.forEach.call(list.children, function (li, j) {
      li.classList.toggle('is-active', j === i);
    });
    var el = list.children[i];
    if (el) el.scrollIntoView({ block: 'nearest' });
  }

  function go(i) { if (i >= 0 && i < rows.length) window.location.href = rows[i].url; }

  function onKey(e) {
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive(Math.min(active + 1, rows.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(Math.max(active - 1, 0)); }
    else if (e.key === 'Enter') { e.preventDefault(); go(active < 0 ? 0 : active); }
    else if (e.key === 'Escape') { e.preventDefault(); close(); }
  }

  function build() {
    overlay = document.createElement('div');
    overlay.className = 'rs-overlay';
    overlay.innerHTML =
      '<div class="rs-modal" role="dialog" aria-modal="true" aria-label="搜尋本站">' +
        '<div class="rs-bar">' +
          '<svg class="rs-mag" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"></circle><line x1="21" y1="21" x2="16.5" y2="16.5"></line></svg>' +
          '<input type="search" class="rs-input" placeholder="搜尋經論、專欄、課程…" autocomplete="off" autocapitalize="off" spellcheck="false" aria-label="搜尋關鍵字">' +
          '<kbd class="rs-esc">esc</kbd>' +
        '</div>' +
        '<ul class="rs-results" role="listbox"></ul>' +
        '<div class="rs-empty" hidden>找不到相關內容，換個關鍵字試試。</div>' +
        '<div class="rs-foot"><span><kbd>↑</kbd><kbd>↓</kbd> 移動</span><span><kbd>↵</kbd> 開啟</span><span><kbd>esc</kbd> 關閉</span></div>' +
      '</div>';
    document.body.appendChild(overlay);
    input = overlay.querySelector('.rs-input');
    list = overlay.querySelector('.rs-results');
    emptyEl = overlay.querySelector('.rs-empty');
    overlay.addEventListener('mousedown', function (e) { if (e.target === overlay) close(); });
    overlay.querySelector('.rs-esc').addEventListener('click', close);
    input.addEventListener('input', function () { render(input.value); });
    input.addEventListener('keydown', onKey);
    list.addEventListener('mousedown', function (e) {
      var li = e.target.closest('.rs-item');
      if (li) { e.preventDefault(); window.location.href = li.getAttribute('data-url'); }
    });
  }

  function open() {
    if (!overlay) build();
    load();
    document.documentElement.classList.add('rs-open');
    overlay.classList.add('is-open');
    input.value = '';
    render('');
    setTimeout(function () { input.focus(); }, 20);
  }

  function close() {
    if (!overlay) return;
    overlay.classList.remove('is-open');
    document.documentElement.classList.remove('rs-open');
  }

  btn.addEventListener('click', open);

  document.addEventListener('keydown', function (e) {
    var isOpen = overlay && overlay.classList.contains('is-open');
    var typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName) ||
                 document.activeElement.isContentEditable;
    if ((e.key === 'k' || e.key === 'K') && (e.metaKey || e.ctrlKey)) {
      e.preventDefault(); isOpen ? close() : open();
    } else if (e.key === '/' && !isOpen && !typing) {
      e.preventDefault(); open();
    }
  });
})();
