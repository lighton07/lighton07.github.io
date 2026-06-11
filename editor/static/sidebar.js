// ── Sidebar: folder tree with drag-and-drop ───────────────────────────────────
// Globals shared with app.js: currentFile, setStatus, apiFetch, loadTree

const expandedFolders = new Set();
let treeCache = null;
let dragState  = null;  // { type: 'post'|'folder', path, title }

// ── Render ────────────────────────────────────────────────────────────────────

function renderTree(data) {
  treeCache = data;
  const el = document.getElementById('folder-tree');
  el.innerHTML = '';

  if (!data || !data.children || !data.children.length) {
    el.innerHTML = '<div class="tree-empty">글이 없습니다</div>';
    return;
  }

  el.appendChild(buildChildren(data.children, ''));

  // Root drop zone (move to top level)
  const rootZone = document.createElement('div');
  rootZone.className = 'drop-root-zone';
  rootZone.title = '여기에 드롭하면 최상위로 이동';
  setupDropZone(rootZone, '');
  el.appendChild(rootZone);
}

function buildChildren(children, parentPath) {
  const wrap = document.createElement('div');
  wrap.className = 'tree-children';
  for (const child of children) {
    if (child.type === 'folder') wrap.appendChild(buildFolder(child));
    else if (child.type === 'post') wrap.appendChild(buildPost(child));
  }
  return wrap;
}

function buildFolder(folder) {
  const isOpen = expandedFolders.has(folder.path);

  const group = document.createElement('div');
  group.className = 'tree-folder';
  group.dataset.path = folder.path;

  const label = document.createElement('div');
  label.className = 'tree-folder-label' + (isOpen ? ' open' : '');
  label.innerHTML =
    `<span class="drag-handle" draggable="false">⠿</span>` +
    `<span class="tree-arrow">▶</span>` +
    `<span class="tree-folder-icon">📁</span>` +
    `<span class="tree-folder-name">${folder.name}</span>` +
    `<span class="tree-badge">${countAll(folder)}</span>`;

  label.addEventListener('click', e => {
    if (e.target.classList.contains('drag-handle')) return;
    if (expandedFolders.has(folder.path)) expandedFolders.delete(folder.path);
    else expandedFolders.add(folder.path);
    renderTree(treeCache);
  });

  setupDraggable(label, { type: 'folder', path: folder.path, title: folder.name });
  setupDropZone(label, folder.path);

  group.appendChild(label);

  const childrenWrap = document.createElement('div');
  childrenWrap.className = 'tree-folder-children';
  childrenWrap.style.display = isOpen ? '' : 'none';
  if (folder.children && folder.children.length) {
    childrenWrap.appendChild(buildChildren(folder.children, folder.path));
  }
  group.appendChild(childrenWrap);
  return group;
}

function buildPost(post) {
  const item = document.createElement('div');
  item.className = 'tree-post-item' + (currentFile === post.file ? ' active' : '');
  item.dataset.file = post.file;
  item.innerHTML =
    `<span class="drag-handle" draggable="false">⠿</span>` +
    `<span class="tree-post-icon">📄</span>` +
    `<div class="tree-post-info">` +
    `  <div class="tree-post-title">${post.title}</div>` +
    `  <div class="tree-post-date">${post.date}</div>` +
    `</div>`;

  item.addEventListener('click', e => {
    if (e.target.classList.contains('drag-handle')) return;
    openPost(post.file);
  });

  setupDraggable(item, { type: 'post', path: post.file, title: post.title });
  return item;
}

function countAll(folder) {
  let n = 0;
  for (const c of (folder.children || [])) {
    if (c.type === 'post') n++;
    else if (c.type === 'folder') n += countAll(c);
  }
  return n;
}

// ── Drag & Drop ───────────────────────────────────────────────────────────────

function setupDraggable(el, item) {
  el.draggable = true;

  el.addEventListener('dragstart', e => {
    dragState = item;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', item.path);
    requestAnimationFrame(() => el.classList.add('is-dragging'));
  });

  el.addEventListener('dragend', () => {
    dragState = null;
    el.classList.remove('is-dragging');
    clearDropHighlights();
  });
}

function setupDropZone(el, targetPath) {
  el.addEventListener('dragover', e => {
    if (!dragState) return;
    if (dragState.path === targetPath) return;
    // Prevent folder dropping into its own subtree
    if (dragState.type === 'folder' && targetPath.startsWith(dragState.path + '/')) return;
    // Post: skip if already in target folder
    if (dragState.type === 'post') {
      const cur = dragState.path.includes('/')
        ? dragState.path.substring(0, dragState.path.lastIndexOf('/'))
        : '';
      if (cur === targetPath) return;
    }
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = 'move';
    clearDropHighlights();
    el.classList.add('drop-target');
  });

  el.addEventListener('dragleave', e => {
    if (!el.contains(e.relatedTarget)) el.classList.remove('drop-target');
  });

  el.addEventListener('drop', async e => {
    e.preventDefault();
    e.stopPropagation();
    el.classList.remove('drop-target');
    if (!dragState) return;
    const item = dragState;
    dragState = null;
    await doMove(item, targetPath);
  });
}

function clearDropHighlights() {
  document.querySelectorAll('.drop-target').forEach(e => e.classList.remove('drop-target'));
}

async function doMove(item, newParent) {
  setStatus('이동 중...');
  try {
    const res = await apiFetch('/api/move', { type: item.type, from: item.path, toParent: newParent });
    if (res.ok) {
      // Update currentFile if the open post was moved
      if (item.type === 'post' && currentFile === item.path) {
        const fname = item.path.split('/').pop();
        currentFile = newParent ? `${newParent}/${fname}` : fname;
        document.getElementById('editing-label').textContent = currentFile;
      }
      setStatus('✓ 이동됨', 'ok');
      await loadTree();
    } else {
      setStatus('✗ ' + res.error, 'err');
    }
  } catch (err) {
    setStatus('✗ ' + err.message, 'err');
  }
}

// ── Folder creation ───────────────────────────────────────────────────────────

async function promptNewFolder() {
  const name = prompt('새 폴더 경로\n(중첩 폴더: math/calculus 처럼 입력):');
  if (!name || !name.trim()) return;
  setStatus('폴더 생성 중...');
  const res = await apiFetch('/api/create-folder', { path: name.trim() });
  if (res.ok) {
    // Expand all parent paths
    const parts = res.path.split('/');
    for (let i = 1; i <= parts.length; i++) expandedFolders.add(parts.slice(0,i).join('/'));
    setStatus(`✓ "${name}" 생성됨`, 'ok');
    await loadTree();
  } else {
    setStatus('✗ ' + res.error, 'err');
  }
}
