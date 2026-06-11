// ── PaperMod Preview Renderer ─────────────────────────────────────────────────

function mdToHtml(md) {
  return md
    .replace(/\$\$([\s\S]*?)\$\$/g,  (_, m) => `<span class="mb">$$${m}$$</span>`)
    .replace(/\$([^\n$]+?)\$/g,       (_, m) => `<span class="mi">$${m}$</span>`)
    .replace(/^```[\w]*\n([\s\S]*?)^```/gm, '<pre><code>$1</code></pre>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm,  '<h2>$1</h2>')
    .replace(/^# (.+)$/gm,   '<h1>$1</h1>')
    .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*(.+?)\*\*/g,     '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g,         '<em>$1</em>')
    .replace(/`([^`]+)`/g,         '<code>$1</code>')
    .replace(/^> (.+)$/gm,         '<blockquote>$1</blockquote>')
    .replace(/^---$/gm,            '<hr>')
    .replace(/^\- (.+)$/gm,        '<li>$1</li>')
    .replace(/\[(.+?)\]\((.+?)\)/g,'<a href="$2">$1</a>')
    .split(/\n\n+/)
    .map(b => {
      const t = b.trim();
      if (!t) return '';
      if (/^<(h[1-6]|pre|blockquote|hr|li|ul|ol|div)/.test(t)) return t;
      return `<p>${t}</p>`;
    }).join('\n')
    .replace(/<span class="mb">\$\$([\s\S]*?)\$\$<\/span>/g, (_, m) => `$$${m}$$`)
    .replace(/<span class="mi">\$([^$]*?)\$<\/span>/g,       (_, m) => `$${m}$`);
}

function renderPostPreview() {
  const title  = document.getElementById('post-title').value;
  const date   = document.getElementById('post-date').value;
  const tags   = document.getElementById('post-tags').value;
  const body   = (typeof getEditorValue === 'function') ? getEditorValue() : '';
  const math   = document.getElementById('post-math').checked;
  const folder = document.getElementById('post-folder').value;

  const tagHtml = tags.split(',').map(t => t.trim()).filter(Boolean)
    .map(t => `<span style="background:rgba(124,106,247,.18);padding:1px 7px;border-radius:4px">${t}</span>`)
    .join(' ');

  const el = document.getElementById('preview-content');
  el.innerHTML =
    `<div class="pm-post-title">${title || '<span style="opacity:.3">제목 없음</span>'}</div>` +
    `<div class="pm-post-meta">` +
    `  <span>📅 ${date}</span>${tagHtml}` +
    `  ${folder ? `<span style="color:#7c6af7;font-size:.72rem">📁 ${folder}</span>` : ''}` +
    `  ${math ? '<span style="color:rgba(94,234,212,.7);font-size:.72rem">∑ KaTeX</span>' : ''}` +
    `</div>` +
    `<div class="pm-post-body">${mdToHtml(body)}</div>`;

  if (math && window._katexReady) {
    renderMathInElement(el, {
      delimiters: [{ left:'$$', right:'$$', display:true }, { left:'$', right:'$', display:false }],
      throwOnError: false,
    });
  }
}

function renderHomepagePreview(allPosts, allFolders, eduEntries) {
  const name = document.getElementById('hp-name').value || 'Lighton';
  const bio  = document.getElementById('hp-bio').value  || '';
  document.getElementById('preview-site-title').textContent = name;

  const eduHtml = (eduEntries || []).map(e =>
    `<div class="pm-cv-row">` +
    `<span><span class="pm-cv-school">${e.school}</span>` +
    `<span class="pm-cv-deg">${e.degree}</span></span>` +
    `<span class="pm-cv-period">${e.period}</span></div>`
  ).join('');

  const folderHtml = (allFolders || []).map(f =>
    `<div class="pm-folder-item">` +
    `<span class="pm-folder-item-name">📁 ${f.name}</span>` +
    `<span class="pm-folder-item-count">${f.count}</span></div>`
  ).join('');

  const recentHtml = (allPosts || []).slice(0, 6).map(p =>
    `<div class="pm-post-card">` +
    `<div class="pm-card-title">${p.title}</div>` +
    `<div class="pm-card-meta">${p.date}</div>` +
    `${p.folder ? `<div class="pm-card-folder">📁 ${p.folder}</div>` : ''}` +
    `</div>`
  ).join('');

  document.getElementById('preview-content').innerHTML =
    `<div class="pm-home-info">` +
    `<h1>${name}</h1><p>${bio.replace(/\n/g,'<br>')}</p>` +
    `${eduEntries && eduEntries.length ? `<hr class="pm-cv-divider"><div class="pm-cv-label">학력</div>${eduHtml}` : ''}` +
    `</div>` +
    `<div class="pm-folder-layout">` +
    `<div><div class="pm-folder-nav-title">카테고리</div>` +
    `${folderHtml || '<div style="font-size:.78rem;color:rgba(255,255,255,.3)">폴더 없음</div>'}</div>` +
    `<div><div class="pm-recent-title">최근 글</div>` +
    `${recentHtml || '<div style="font-size:.78rem;color:rgba(255,255,255,.3)">글 없음</div>'}</div>` +
    `</div>`;
}
