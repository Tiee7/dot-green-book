(() => {
  'use strict';
  const progressKey = 'dot-green-book-progress-v1';
  let progress = { chapters: [], checks: {} };
  try { const saved = JSON.parse(localStorage.getItem(progressKey)); if (saved && Array.isArray(saved.chapters) && typeof saved.checks === 'object' && saved.checks !== null) progress = saved; } catch {}
  const toast = document.querySelector('.toast');
  let timer;
  function say(message) { if (!toast) return; toast.textContent = message; toast.classList.add('visible'); clearTimeout(timer); timer = setTimeout(() => toast.classList.remove('visible'), 3500); }
  function updateProgress() {
    document.querySelectorAll('[data-progress]').forEach(el => el.textContent = progress.chapters.length ? `已手动完成 ${progress.chapters.length} / 8 章 · 仅保存在本机` : '阅读进度保存在当前浏览器。');
    document.querySelectorAll('[data-complete-id]').forEach(el => el.textContent = progress.chapters.includes(el.dataset.completeId) ? '已完成' : '');
    document.querySelectorAll('[data-mark-complete]').forEach(el => { const done = progress.chapters.includes(el.dataset.markComplete); el.textContent = done ? '已完成 · 点击取消标记' : '标记本章已完成'; el.setAttribute('aria-pressed', String(done)); });
    document.querySelectorAll('[data-check]').forEach(el => el.checked = !!progress.checks[el.dataset.check]);
  }
  function save() { try { localStorage.setItem(progressKey, JSON.stringify(progress)); } catch { say('浏览器无法保存，进度仅在当前页面保留。'); } updateProgress(); }
  updateProgress();
  document.querySelectorAll('[data-mark-complete]').forEach(button => button.addEventListener('click', () => { const id = button.dataset.markComplete; progress.chapters = progress.chapters.includes(id) ? progress.chapters.filter(x => x !== id) : [...progress.chapters, id]; save(); }));
  document.querySelectorAll('[data-check]').forEach(input => input.addEventListener('change', () => { progress.checks[input.dataset.check] = input.checked; save(); }));
  document.querySelector('[data-reset-progress]')?.addEventListener('click', () => { progress = {chapters: [], checks: {}}; save(); say('本机阅读进度已清除。'); });
  document.querySelectorAll('[data-copy]').forEach(button => button.addEventListener('click', async () => {
    const target = document.getElementById(button.dataset.copy);
    if (!target) return;
    try { await navigator.clipboard.writeText(target.textContent); say('指令已复制，粘贴到你的 Dot 对话里试试。'); } catch { const range = document.createRange(); range.selectNodeContents(target); const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range); say('无法自动复制，已选中指令，请手动复制。'); }
  }));
  document.querySelectorAll('[data-filter-group]').forEach(group => {
    const input = group.querySelector('[data-search-input]');
    const items = [...group.querySelectorAll('[data-search]')];
    const buttons = [...group.querySelectorAll('[data-filter]')];
    let category = 'all';
    function filter() {
      const query = input.value.trim().toLowerCase(); let count = 0;
      items.forEach(el => { const visible = (category === 'all' || el.dataset.category === category) && el.dataset.search.includes(query); el.hidden = !visible; if(visible) count++; });
      group.querySelector('[data-result-count]').textContent = `找到 ${count} 个${group.querySelector('.faq-list') ? '问题' : '案例'}`;
      group.querySelector('[data-empty]').hidden = count !== 0;
      buttons.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.filter === category)));
    }
    input.addEventListener('input', filter);
    buttons.forEach(button => button.addEventListener('click', () => { category = button.dataset.filter; filter(); }));
    group.querySelector('[data-clear-filter]')?.addEventListener('click', () => { input.value = ''; category = 'all'; filter(); input.focus(); });
    function revealHash() { let id; try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; } const detail = document.getElementById(id); if (detail && items.includes(detail)) { category = 'all'; input.value = ''; filter(); detail.open = true; detail.scrollIntoView({block:'start'}); } }
    revealHash(); window.addEventListener('hashchange', revealHash);
    document.addEventListener('keydown', event => { if(event.key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName) && !document.activeElement?.isContentEditable) { event.preventDefault(); input.focus(); } });
  });
})();
