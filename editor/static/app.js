// ── App: state, init, post CRUD, save/push ────────────────────────────────────
// Depends on: sidebar.js, preview.js (loaded before this file)

let mode        = 'post';
let currentFile = null;
let allPosts    = [];
let allFolders  = [];
let eduEntries  = [];

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('post-date').value = new Date().toISOString().slice(0, 10);

  document.getElementById('btn-save').onclick       = saveCurrentFile;
  document.getElementById('btn-push').onclick       = pushCurrent;
  document.getElementById('btn-sync').onclick       = syncAll;
  document.getElementById('btn-new').onclick        = newPost;
  document.getElementById('btn-new-folder').onclick = promptNewFolder;
  document.getElementById('btn-homepage').onclick   = openHomepage;
  document.getElementById('btn-add-edu').onclick    = addEduEntry;

  const liveInputs = ['post-title','post-date','post-tags','post-body','post-folder'];
  liveInputs.forEach(id => document.getElementById(id).addEventListener('input', renderPreview));
  document.getElementById('post-math').addEventListener('change', renderPreview);
  document.getElementById('hp-name').addEventListener('input', renderPreview);
  document.getElementById('hp-bio').addEventListener('input',  renderPreview);

  // KaTeX might load after DOMContentLoaded
  window._onKatexReady = renderPreview;

  loadTree();
});

// ── Data ──────────────────────────────────────────────────────────────────────

async function loadTree() {
  const [tree, flat] = await Promise.all([
    fetch('/api/tree').then(r => r.json()),
    fetch('/api/folders').then(r => r.json()),
  ]);
  allFolders = flat;
  allPosts   = flattenPosts(tree);
  renderTree(tree);          // sidebar.js
  updateFolderSelect();
}

function flattenPosts(node) {
  const out = [];
  for (const c of (node.children || [])) {
    if (c.type === 'post')   out.push(c);
    if (c.type === 'folder') out.push(...flattenPosts(c));
  }
  return out;
}

// ── Mode ──────────────────────────────────────────────────────────────────────

function showPostPane() {
  document.getElementById('pane-post').style.display     = '';
  document.getElementById('pane-homepage').style.display = 'none';
  document.getElementById('btn-homepage').classList.remove('active');
  mode = 'post';
}
function showHomepagePane() {
  document.getElementById('pane-post').style.display     = 'none';
  document.getElementById('pane-homepage').style.display = '';
  document.getElementById('btn-homepage').classList.add('active');
  mode = 'homepage';
}
function renderPreview() {
  if (mode === 'post') renderPostPreview();
  else renderHomepagePreview(allPosts, allFolders, eduEntries);
}

// ── Post CRUD ─────────────────────────────────────────────────────────────────

function newPost() {
  currentFile = null;
  showPostPane();
  document.getElementById('post-title').value = '';
  document.getElementById('post-body').value  = '';
  document.getElementById('post-tags').value  = '';
  document.getElementById('post-date').value  = new Date().toISOString().slice(0, 10);
  document.getElementById('post-math').checked = true;
  document.getElementById('editing-label').textContent = '새 글';
  renderTree(treeCache);
  renderPreview();
  setStatus('새 글 작성 중', '');
}

async function openPost(file) {
  currentFile = file;
  showPostPane();
  const data = await fetch('/api/post?file=' + encodeURIComponent(file)).then(r => r.json());
  if (!data) { setStatus('✗ 읽기 실패', 'err'); return; }
  document.getElementById('post-title').value  = data.title || '';
  document.getElementById('post-date').value   = data.date  || '';
  document.getElementById('post-tags').value   = data.tags  || '';
  document.getElementById('post-body').value   = data.body  || '';
  document.getElementById('post-math').checked = data.math === 'true' || data.math === true;
  document.getElementById('editing-label').textContent = file;

  const folder = file.includes('/') ? file.substring(0, file.lastIndexOf('/')) : '';
  updateFolderSelect(folder);
  renderTree(treeCache);
  renderPreview();
  setStatus(`"${data.title}" 편집 중`, '');
}

// ── Folder select ─────────────────────────────────────────────────────────────

function updateFolderSelect(selected) {
  const sel = document.getElementById('post-folder');
  const cur = selected !== undefined ? selected : sel.value;
  sel.innerHTML = '<option value="">(미분류)</option>';

  // Collect all folder paths from tree (supports nesting)
  for (const path of collectFolderPaths(treeCache)) {
    const depth = (path.match(/\//g) || []).length;
    const opt = document.createElement('option');
    opt.value = path;
    opt.textContent = '  '.repeat(depth) + '📁 ' + path.split('/').pop();
    sel.appendChild(opt);
  }
  sel.value = cur;
}

function collectFolderPaths(node) {
  const out = [];
  for (const c of (node ? node.children || [] : [])) {
    if (c.type === 'folder') {
      out.push(c.path);
      out.push(...collectFolderPaths(c));
    }
  }
  return out;
}

// ── Education ─────────────────────────────────────────────────────────────────

function renderEduList() {
  document.getElementById('edu-list').innerHTML = eduEntries.map((e, i) =>
    `<div class="edu-entry">` +
    `<div class="field"><label>학교</label>` +
    `<input type="text" value="${e.school}" oninput="eduEntries[${i}].school=this.value;renderPreview()"></div>` +
    `<div class="field" style="flex:1.4"><label>학위/전공</label>` +
    `<input type="text" value="${e.degree}" oninput="eduEntries[${i}].degree=this.value;renderPreview()"></div>` +
    `<div class="field"><label>기간</label>` +
    `<input type="text" value="${e.period}" oninput="eduEntries[${i}].period=this.value;renderPreview()"></div>` +
    `<button class="edu-del" onclick="delEdu(${i})">✕</button>` +
    `</div>`
  ).join('');
}

function addEduEntry() { eduEntries.push({school:'',degree:'',period:''}); renderEduList(); renderPreview(); }
function delEdu(i)      { eduEntries.splice(i,1); renderEduList(); renderPreview(); }

async function openHomepage() {
  showHomepagePane();
  const data = await fetch('/api/homepage').then(r => r.json());
  document.getElementById('hp-name').value = data.name || '';
  document.getElementById('hp-bio').value  = data.bio  || '';
  eduEntries = data.education || [];
  renderEduList();
  document.getElementById('preview-site-title').textContent = data.name || 'Lighton';
  renderPreview();
  setStatus('메인 페이지 편집 중', '');
}

// ── Status & utils ────────────────────────────────────────────────────────────

function setStatus(msg, type = '') {
  const el = document.getElementById('status');
  el.textContent = msg; el.className = type;
}

async function apiFetch(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return r.json();
}

function setBtnsDisabled(v) {
  document.querySelectorAll('.btn').forEach(b => b.disabled = v);
}

function slugify(t) {
  return t.toLowerCase().replace(/[^\w가-힣\s-]/g,'').replace(/\s+/g,'-').replace(/-+/g,'-').trim() || 'post';
}

function buildPostPayload() {
  const title  = document.getElementById('post-title').value || 'Untitled';
  const date   = document.getElementById('post-date').value;
  const folder = document.getElementById('post-folder').value;
  const tags   = document.getElementById('post-tags').value.split(',').map(t=>t.trim()).filter(Boolean);
  const math   = document.getElementById('post-math').checked;
  const body   = document.getElementById('post-body').value;

  let fm = `---\ntitle: "${title}"\ndate: ${date}\n`;
  if (tags.length) fm += `tags: [${tags.map(t=>`"${t}"`).join(', ')}]\n`;
  if (math)        fm += `math: true\n`;
  fm += `---\n\n`;

  const slug    = currentFile ? currentFile.split('/').pop().replace('.md','') : slugify(title);
  const newPath = folder ? `${folder}/${slug}` : slug;
  const oldPath = currentFile ? currentFile.replace('.md','') : null;
  return { content: fm + body, title, newPath, oldPath };
}

// ── Save / Push ───────────────────────────────────────────────────────────────

async function saveCurrentFile() {
  if (mode === 'post') {
    const { content, title, newPath, oldPath } = buildPostPayload();
    setStatus('저장 중...');
    const res = await apiFetch('/api/save', { path: newPath, content,
      oldPath: oldPath !== newPath ? oldPath : null });
    if (res.ok) {
      currentFile = newPath + '.md';
      document.getElementById('editing-label').textContent = currentFile;
      setStatus('✓ 저장됨', 'ok');
      await loadTree();
    } else setStatus('✗ ' + res.error, 'err');
  } else {
    await saveHomepage();
  }
}

async function saveHomepage() {
  const name = document.getElementById('hp-name').value;
  const bio  = document.getElementById('hp-bio').value;
  setStatus('저장 중...');
  const res = await apiFetch('/api/save-homepage', { name, bio, education: eduEntries });
  if (res.ok) setStatus('✓ 홈페이지 저장됨', 'ok');
  else        setStatus('✗ ' + res.error, 'err');
}

async function pushCurrent() {
  if (mode === 'post') {
    const { content, title, newPath, oldPath } = buildPostPayload();
    setStatus('Push 중...');
    setBtnsDisabled(true);
    const res = await apiFetch('/api/push', { path: newPath, content, title,
      oldPath: oldPath !== newPath ? oldPath : null });
    setBtnsDisabled(false);
    if (res.ok) {
      currentFile = newPath + '.md';
      document.getElementById('editing-label').textContent = currentFile;
      setStatus(`✓ 배포됨 → lighton07.github.io/posts/${newPath}/`, 'ok');
      await loadTree();
    } else setStatus('✗ ' + res.error, 'err');
  } else {
    await saveHomepage();
    await _doSync('chore: update homepage');
  }
}

async function syncAll() {
  const msg = prompt('커밋 메시지:', 'chore: update blog');
  if (!msg) return;
  await _doSync(msg);
}

async function _doSync(msg) {
  setStatus('전체 동기화 중...');
  setBtnsDisabled(true);
  const res = await apiFetch('/api/sync', { message: msg });
  setBtnsDisabled(false);
  if (res.ok) setStatus('✓ push됨', 'ok');
  else        setStatus('✗ ' + res.error, 'err');
}
