/**
 * Webapp File Server - Frontend Client Controller
 */

// Application State
const state = {
  currentPath: '',
  items: [],
  filteredItems: [],
  viewMode: localStorage.getItem('file_view_mode') || 'table',
  filterQuery: '',
  currentUser: null,
  editor: {
    instance: null,
    path: '',
    filename: '',
    isDirty: false,
    originalContent: ''
  }
};

// DOM Elements
const elements = {
  userBadge: document.getElementById('userBadge'),
  logoutBtn: document.getElementById('logoutBtn'),
  breadcrumbNav: document.getElementById('breadcrumbNav'),
  itemCountLabel: document.getElementById('itemCountLabel'),
  storagePathLabel: document.getElementById('storagePathLabel'),
  fileTableView: document.getElementById('fileTableView'),
  fileGridView: document.getElementById('fileGridView'),
  fileTableBody: document.getElementById('fileTableBody'),
  emptyPlaceholder: document.getElementById('emptyPlaceholder'),
  loadingOverlay: document.getElementById('loadingOverlay'),
  searchInput: document.getElementById('searchInput'),
  listViewBtn: document.getElementById('listViewBtn'),
  gridViewBtn: document.getElementById('gridViewBtn'),
  fileUploadInput: document.getElementById('fileUploadInput'),
  uploadBtn: document.getElementById('uploadBtn'),
  newFolderBtn: document.getElementById('newFolderBtn'),
  newFileBtn: document.getElementById('newFileBtn'),
  downloadZipBtn: document.getElementById('downloadZipBtn'),
  dropZoneOverlay: document.getElementById('dropZoneOverlay'),
  dropTargetLabel: document.getElementById('dropTargetLabel'),
  // Editor
  editorModal: document.getElementById('editorModal'),
  editorContainer: document.getElementById('editorContainer'),
  editorFilename: document.getElementById('editorFilename'),
  editorDirtyBadge: document.getElementById('editorDirtyBadge'),
  editorModeSelect: document.getElementById('editorModeSelect'),
  editorSaveBtn: document.getElementById('editorSaveBtn'),
  editorCloseBtn: document.getElementById('editorCloseBtn'),
  editorStatusText: document.getElementById('editorStatusText'),
  editorCursorPosition: document.getElementById('editorCursorPosition'),
  // Action Modal
  actionModal: document.getElementById('actionModal'),
  modalTitle: document.getElementById('modalTitle'),
  modalDescription: document.getElementById('modalDescription'),
  modalInputContainer: document.getElementById('modalInputContainer'),
  modalInput: document.getElementById('modalInput'),
  modalCancelBtn: document.getElementById('modalCancelBtn'),
  modalConfirmBtn: document.getElementById('modalConfirmBtn'),
  // Upload Toast
  uploadToast: document.getElementById('uploadToast'),
  uploadToastTitle: document.getElementById('uploadToastTitle'),
  uploadToastDetail: document.getElementById('uploadToastDetail'),
  uploadToastPercent: document.getElementById('uploadToastPercent'),
  uploadProgressBar: document.getElementById('uploadProgressBar')
};

// ==========================================
// Initialization & Authentication Check
// ==========================================

async function init() {
  try {
    const res = await fetch('/api/auth/status');
    const status = await res.json();

    if (!status.configured) {
      window.location.href = '/setup';
      return;
    }
    if (!status.authenticated) {
      window.location.href = '/login';
      return;
    }

    state.currentUser = status.username;
    if (elements.userBadge) {
      elements.userBadge.textContent = status.username;
    }

    setupEventListeners();
    applyViewMode(state.viewMode);
    
    // Parse path from URL hash if present
    const hashPath = decodeURIComponent(window.location.hash.replace(/^#/, ''));
    await loadDirectory(hashPath || '');
  } catch (err) {
    console.error('Failed to initialize application', err);
    showNotice('Failed to connect to file server.', true);
  }
}

// ==========================================
// Directory Navigation & Rendering
// ==========================================

async function loadDirectory(path = '') {
  showLoading(true);
  try {
    const res = await fetch(`/api/files/list?path=${encodeURIComponent(path)}`);
    if (!res.ok) {
      if (res.status === 401) {
        window.location.href = '/login';
        return;
      }
      const err = await res.json();
      showNotice(err.detail || 'Could not access folder', true);
      showLoading(false);
      return;
    }

    const data = await res.json();
    state.currentPath = data.current_path;
    state.items = data.items;
    window.location.hash = encodeURIComponent(state.currentPath);

    renderBreadcrumbs(data.breadcrumbs);
    filterAndRenderItems();

    elements.storagePathLabel.textContent = '/' + (state.currentPath ? state.currentPath : '');
  } catch (err) {
    console.error(err);
    showNotice('Error loading directory contents', true);
  } finally {
    showLoading(false);
  }
}

function navigateTo(path) {
  loadDirectory(path);
}

function renderBreadcrumbs(crumbs) {
  elements.breadcrumbNav.innerHTML = '';
  crumbs.forEach((crumb, idx) => {
    const isLast = idx === crumbs.length - 1;
    
    const btn = document.createElement('button');
    btn.className = `flex items-center gap-1.5 transition ${
      isLast ? 'text-white font-semibold' : 'text-indigo-400 hover:text-indigo-300 font-medium'
    }`;
    
    if (idx === 0) {
      btn.innerHTML = '<i class="fa-solid fa-house text-xs"></i><span>Home</span>';
    } else {
      btn.textContent = crumb.name;
    }

    btn.onclick = () => navigateTo(crumb.path);
    elements.breadcrumbNav.appendChild(btn);

    if (!isLast) {
      const sep = document.createElement('span');
      sep.className = 'text-slate-600';
      sep.innerHTML = '<i class="fa-solid fa-chevron-right text-[10px]"></i>';
      elements.breadcrumbNav.appendChild(sep);
    }
  });
}

function filterAndRenderItems() {
  const query = state.filterQuery.toLowerCase().trim();
  state.filteredItems = query
    ? state.items.filter(item => item.name.toLowerCase().includes(query))
    : state.items;

  elements.itemCountLabel.textContent = `${state.filteredItems.length} item(s)`;

  if (state.filteredItems.length === 0) {
    elements.fileTableBody.innerHTML = '';
    elements.fileGridView.innerHTML = '';
    elements.emptyPlaceholder.classList.remove('hidden');
    elements.emptyPlaceholder.classList.add('flex');
    return;
  }

  elements.emptyPlaceholder.classList.add('hidden');
  elements.emptyPlaceholder.classList.remove('flex');

  if (state.viewMode === 'table') {
    renderTableView(state.filteredItems);
  } else {
    renderGridView(state.filteredItems);
  }
}

function getFileIcon(item) {
  if (item.is_dir) {
    return { icon: 'fa-solid fa-folder text-amber-400', label: 'Folder' };
  }
  const ext = item.extension;
  if (item.is_text) {
    return { icon: 'fa-regular fa-file-code text-sky-400', label: 'Code/Text' };
  }
  if (['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp'].includes(ext)) {
    return { icon: 'fa-regular fa-file-image text-emerald-400', label: 'Image' };
  }
  if (['.zip', '.tar', '.gz', '.bz2', '.7z', '.rar'].includes(ext)) {
    return { icon: 'fa-regular fa-file-zipper text-purple-400', label: 'Archive' };
  }
  if (['.mp3', '.wav', '.ogg', '.m4a', '.flac'].includes(ext)) {
    return { icon: 'fa-regular fa-file-audio text-pink-400', label: 'Audio' };
  }
  if (['.mp4', '.mkv', '.webm', '.mov', '.avi'].includes(ext)) {
    return { icon: 'fa-regular fa-file-video text-rose-400', label: 'Video' };
  }
  if (ext === '.pdf') {
    return { icon: 'fa-regular fa-file-pdf text-red-500', label: 'PDF' };
  }
  return { icon: 'fa-regular fa-file text-slate-400', label: 'File' };
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatDate(epoch) {
  const d = new Date(epoch * 1000);
  return d.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

function renderTableView(items) {
  elements.fileTableBody.innerHTML = '';
  items.forEach(item => {
    const row = document.createElement('tr');
    row.className = 'hover:bg-slate-800/40 transition group cursor-pointer';

    const iconData = getFileIcon(item);

    row.innerHTML = `
      <td class="py-3 px-4 flex items-center gap-3">
        <i class="${iconData.icon} text-lg w-5 text-center flex-shrink-0"></i>
        <span class="font-medium text-slate-200 group-hover:text-white truncate max-w-[200px] sm:max-w-md">${escapeHtml(item.name)}</span>
      </td>
      <td class="py-3 px-4 text-slate-400 text-xs hidden sm:table-cell font-mono">
        ${item.is_dir ? '—' : formatBytes(item.size)}
      </td>
      <td class="py-3 px-4 text-slate-400 text-xs hidden md:table-cell">
        ${formatDate(item.modified)}
      </td>
      <td class="py-3 px-4 text-right">
        <div class="inline-flex items-center gap-1 opacity-90 sm:opacity-70 group-hover:opacity-100 transition" onclick="event.stopPropagation()">
          ${item.is_text ? `
            <button onclick="openEditor('${escapeJs(item.path)}')" title="Edit Online"
              class="p-1.5 text-slate-400 hover:text-sky-400 hover:bg-slate-800 rounded-lg transition">
              <i class="fa-solid fa-pen-to-square"></i>
            </button>
          ` : ''}
          ${!item.is_dir ? `
            <button onclick="downloadFile('${escapeJs(item.path)}')" title="Download"
              class="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-slate-800 rounded-lg transition">
              <i class="fa-solid fa-download"></i>
            </button>
          ` : `
            <button onclick="downloadDirectoryZip('${escapeJs(item.path)}')" title="Download Zip"
              class="p-1.5 text-slate-400 hover:text-purple-400 hover:bg-slate-800 rounded-lg transition">
              <i class="fa-solid fa-file-zipper"></i>
            </button>
          `}
          <button onclick="promptRename('${escapeJs(item.path)}', '${escapeJs(item.name)}')" title="Rename"
            class="p-1.5 text-slate-400 hover:text-amber-400 hover:bg-slate-800 rounded-lg transition">
            <i class="fa-solid fa-i-cursor"></i>
          </button>
          <button onclick="promptDelete('${escapeJs(item.path)}', '${escapeJs(item.name)}', ${item.is_dir})" title="Delete"
            class="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition">
            <i class="fa-solid fa-trash-can"></i>
          </button>
        </div>
      </td>
    `;

    // Row click handler
    row.addEventListener('click', () => {
      if (item.is_dir) {
        navigateTo(item.path);
      } else if (item.is_text) {
        openEditor(item.path);
      } else {
        downloadFile(item.path);
      }
    });

    elements.fileTableBody.appendChild(row);
  });
}

function renderGridView(items) {
  elements.fileGridView.innerHTML = '';
  items.forEach(item => {
    const card = document.createElement('div');
    card.className = 'bg-slate-800/40 hover:bg-slate-800/90 border border-slate-700/50 hover:border-slate-600 rounded-xl p-3 flex flex-col items-center text-center cursor-pointer group transition relative';

    const iconData = getFileIcon(item);

    card.innerHTML = `
      <div class="w-12 h-12 flex items-center justify-center text-2xl mb-2">
        <i class="${iconData.icon}"></i>
      </div>
      <span class="text-xs font-medium text-slate-200 group-hover:text-white truncate w-full mb-1" title="${escapeHtml(item.name)}">
        ${escapeHtml(item.name)}
      </span>
      <span class="text-[10px] text-slate-400 font-mono">
        ${item.is_dir ? 'Folder' : formatBytes(item.size)}
      </span>
    `;

    card.addEventListener('click', () => {
      if (item.is_dir) {
        navigateTo(item.path);
      } else if (item.is_text) {
        openEditor(item.path);
      } else {
        downloadFile(item.path);
      }
    });

    elements.fileGridView.appendChild(card);
  });
}

function applyViewMode(mode) {
  state.viewMode = mode;
  localStorage.setItem('file_view_mode', mode);

  if (mode === 'table') {
    elements.fileTableView.classList.remove('hidden');
    elements.fileGridView.classList.add('hidden');
    elements.listViewBtn.className = 'p-1.5 text-xs text-white bg-slate-700 rounded transition';
    elements.gridViewBtn.className = 'p-1.5 text-xs text-slate-400 hover:text-white rounded transition';
  } else {
    elements.fileTableView.classList.add('hidden');
    elements.fileGridView.classList.remove('hidden');
    elements.listViewBtn.className = 'p-1.5 text-xs text-slate-400 hover:text-white rounded transition';
    elements.gridViewBtn.className = 'p-1.5 text-xs text-white bg-slate-700 rounded transition';
  }
  filterAndRenderItems();
}

// ==========================================
// CodeMirror In-Browser Text Editor
// ==========================================

function initCodeMirror() {
  if (state.editor.instance) return;

  state.editor.instance = CodeMirror(elements.editorContainer, {
    lineNumbers: true,
    theme: 'material-darker',
    mode: 'plain',
    indentUnit: 4,
    tabSize: 4,
    lineWrapping: true,
    autofocus: true
  });

  state.editor.instance.on('change', () => {
    const currentVal = state.editor.instance.getValue();
    const dirty = currentVal !== state.editor.originalContent;
    state.editor.isDirty = dirty;
    elements.editorDirtyBadge.classList.toggle('hidden', !dirty);
  });

  state.editor.instance.on('cursorActivity', () => {
    const pos = state.editor.instance.getCursor();
    elements.editorCursorPosition.textContent = `Line ${pos.line + 1}, Col ${pos.ch + 1}`;
  });

  // Hotkey Save (Ctrl+S / Cmd+S)
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
      if (!elements.editorModal.classList.contains('hidden')) {
        e.preventDefault();
        saveEditorFile();
      }
    }
  });
}

async function openEditor(path, isNewFile = false, newFileName = '') {
  initCodeMirror();

  elements.editorStatusText.textContent = 'Loading...';
  elements.editorDirtyBadge.classList.add('hidden');
  elements.editorModal.classList.remove('hidden');

  if (isNewFile) {
    state.editor.path = path;
    state.editor.filename = newFileName;
    state.editor.isDirty = false;
    state.editor.originalContent = '';
    state.editor.isNew = true;

    elements.editorFilename.textContent = newFileName;
    state.editor.instance.setValue('');
    setEditorMode(newFileName);
    elements.editorStatusText.textContent = 'New file created';
    setTimeout(() => state.editor.instance.refresh(), 50);
    return;
  }

  try {
    const res = await fetch(`/api/editor/read?path=${encodeURIComponent(path)}`);
    if (!res.ok) {
      const err = await res.json();
      showNotice(err.detail || 'Failed reading file', true);
      closeEditorModal();
      return;
    }

    const data = await res.json();
    state.editor.path = data.path;
    state.editor.filename = data.filename;
    state.editor.originalContent = data.content;
    state.editor.isDirty = false;
    state.editor.isNew = false;

    elements.editorFilename.textContent = data.filename;
    state.editor.instance.setValue(data.content);
    setEditorMode(data.filename);
    elements.editorStatusText.textContent = `Loaded (${formatBytes(data.size)})`;

    setTimeout(() => state.editor.instance.refresh(), 50);
  } catch (err) {
    console.error(err);
    showNotice('Failed reading file for online edit', true);
    closeEditorModal();
  }
}

function setEditorMode(filename) {
  const ext = filename.split('.').pop().toLowerCase();
  const modeMap = {
    'js': 'javascript', 'mjs': 'javascript', 'cjs': 'javascript', 'json': 'javascript',
    'py': 'python',
    'md': 'markdown', 'markdown': 'markdown',
    'html': 'htmlmixed', 'htm': 'htmlmixed',
    'xml': 'xml', 'svg': 'xml',
    'css': 'css',
    'yaml': 'yaml', 'yml': 'yaml',
    'sh': 'shell', 'bash': 'shell',
    'sql': 'sql',
    'c': 'clike', 'cpp': 'clike', 'h': 'clike', 'java': 'clike'
  };

  const mode = modeMap[ext] || 'plain';
  state.editor.instance.setOption('mode', mode === 'plain' ? null : mode);
  elements.editorModeSelect.value = mode;
}

async function saveEditorFile() {
  if (!state.editor.path) return;

  elements.editorSaveBtn.disabled = true;
  elements.editorSaveBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i><span>Saving...</span>';
  elements.editorStatusText.textContent = 'Saving file...';

  const content = state.editor.instance.getValue();

  try {
    const res = await fetch('/api/editor/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        path: state.editor.path,
        content: content,
        create_if_missing: state.editor.isNew || false
      })
    });

    const data = await res.json();
    if (!res.ok) {
      showNotice(data.detail || 'Save failed', true);
      elements.editorStatusText.textContent = 'Save failed';
      return;
    }

    state.editor.originalContent = content;
    state.editor.isDirty = false;
    state.editor.isNew = false;
    elements.editorDirtyBadge.classList.add('hidden');
    elements.editorStatusText.textContent = 'All changes saved to server';
    showNotice('File saved successfully!');
    
    // Refresh directory background state
    loadDirectory(state.currentPath);
  } catch (err) {
    showNotice('Network error saving file', true);
    elements.editorStatusText.textContent = 'Network error';
  } finally {
    elements.editorSaveBtn.disabled = false;
    elements.editorSaveBtn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i><span>Save</span><span class="hidden md:inline text-[10px] opacity-70">(Ctrl+S)</span>';
  }
}

function closeEditorModal() {
  if (state.editor.isDirty) {
    if (!confirm('You have unsaved modifications. Are you sure you want to close without saving?')) {
      return;
    }
  }
  elements.editorModal.classList.add('hidden');
  state.editor.path = '';
  state.editor.isDirty = false;
}

// ==========================================
// File Transfers (Upload / Download / Zip)
// ==========================================

function downloadFile(path) {
  window.location.href = `/api/transfer/download?path=${encodeURIComponent(path)}`;
}

function downloadDirectoryZip(path = '') {
  window.location.href = `/api/transfer/zip?path=${encodeURIComponent(path || state.currentPath)}`;
}

async function uploadFiles(fileList) {
  if (!fileList || fileList.length === 0) return;

  const formData = new FormData();
  formData.append('target_folder', state.currentPath);
  for (let i = 0; i < fileList.length; i++) {
    formData.append('files', fileList[i]);
  }

  showUploadToast(fileList.length);

  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/api/transfer/upload');

  xhr.upload.onprogress = (e) => {
    if (e.lengthComputable) {
      const percent = Math.round((e.loaded / e.total) * 100);
      elements.uploadProgressBar.style.width = `${percent}%`;
      elements.uploadToastPercent.textContent = `${percent}%`;
      elements.uploadToastDetail.textContent = `${formatBytes(e.loaded)} / ${formatBytes(e.total)}`;
    }
  };

  xhr.onload = () => {
    if (xhr.status === 200) {
      elements.uploadProgressBar.style.width = '100%';
      elements.uploadToastPercent.textContent = '100%';
      elements.uploadToastTitle.textContent = 'Upload Complete';
      elements.uploadToastDetail.textContent = `Uploaded ${fileList.length} item(s)`;
      showNotice(`Successfully uploaded ${fileList.length} file(s)!`);
      loadDirectory(state.currentPath);
      setTimeout(() => elements.uploadToast.classList.add('hidden'), 3000);
    } else {
      let errDetail = 'Upload error';
      try {
        const err = JSON.parse(xhr.responseText);
        errDetail = err.detail || errDetail;
      } catch (e) {}
      showNotice(errDetail, true);
      elements.uploadToast.classList.add('hidden');
    }
  };

  xhr.onerror = () => {
    showNotice('Network error uploading files', true);
    elements.uploadToast.classList.add('hidden');
  };

  xhr.send(formData);
}

function showUploadToast(count) {
  elements.uploadToast.classList.remove('hidden');
  elements.uploadToastTitle.textContent = `Uploading ${count} file(s)...`;
  elements.uploadToastDetail.textContent = 'Starting transmission';
  elements.uploadToastPercent.textContent = '0%';
  elements.uploadProgressBar.style.width = '0%';
}

// ==========================================
// Dialogs & Modals (New Folder, Rename, Delete)
// ==========================================

function openActionModal({ title, description, inputVal, showInput, confirmText, isDanger, onConfirm }) {
  elements.modalTitle.textContent = title;
  elements.modalDescription.textContent = description;
  elements.modalConfirmBtn.textContent = confirmText || 'Confirm';

  if (isDanger) {
    elements.modalConfirmBtn.className = 'px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white text-sm font-medium rounded-xl transition shadow-lg shadow-rose-600/30';
  } else {
    elements.modalConfirmBtn.className = 'px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-xl transition shadow-lg shadow-indigo-600/30';
  }

  if (showInput) {
    elements.modalInputContainer.classList.remove('hidden');
    elements.modalInput.value = inputVal || '';
    setTimeout(() => elements.modalInput.focus(), 50);
  } else {
    elements.modalInputContainer.classList.add('hidden');
  }

  elements.actionModal.classList.remove('hidden');

  const cleanup = () => {
    elements.actionModal.classList.add('hidden');
    elements.modalConfirmBtn.onclick = null;
    elements.modalCancelBtn.onclick = null;
  };

  elements.modalCancelBtn.onclick = cleanup;
  elements.modalConfirmBtn.onclick = async () => {
    const val = elements.modalInput.value.trim();
    cleanup();
    await onConfirm(val);
  };
}

function promptNewFolder() {
  openActionModal({
    title: 'Create New Folder',
    description: `Create a new subfolder in /${state.currentPath}`,
    showInput: true,
    inputVal: '',
    confirmText: 'Create',
    isDanger: false,
    onConfirm: async (folderName) => {
      if (!folderName) return;
      try {
        const res = await fetch('/api/files/mkdir', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ parent_path: state.currentPath, folder_name: folderName })
        });
        const data = await res.json();
        if (!res.ok) {
          showNotice(data.detail || 'Could not create folder', true);
          return;
        }
        showNotice('Folder created successfully!');
        loadDirectory(state.currentPath);
      } catch (err) {
        showNotice('Failed to create folder', true);
      }
    }
  });
}

function promptNewFile() {
  openActionModal({
    title: 'Create New Text File',
    description: `Enter filename (e.g. notes.txt, script.py, config.json)`,
    showInput: true,
    inputVal: '',
    confirmText: 'Create & Edit',
    isDanger: false,
    onConfirm: (fileName) => {
      if (!fileName) return;
      const targetPath = state.currentPath ? `${state.currentPath}/${fileName}` : fileName;
      openEditor(targetPath, true, fileName);
    }
  });
}

function promptRename(path, oldName) {
  openActionModal({
    title: 'Rename Item',
    description: `Enter a new name for "${oldName}"`,
    showInput: true,
    inputVal: oldName,
    confirmText: 'Rename',
    isDanger: false,
    onConfirm: async (newName) => {
      if (!newName || newName === oldName) return;
      try {
        const res = await fetch('/api/files/rename', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path, new_name: newName })
        });
        const data = await res.json();
        if (!res.ok) {
          showNotice(data.detail || 'Could not rename item', true);
          return;
        }
        showNotice('Renamed successfully!');
        loadDirectory(state.currentPath);
      } catch (err) {
        showNotice('Failed to rename item', true);
      }
    }
  });
}

function promptDelete(path, name, isDir) {
  openActionModal({
    title: `Delete ${isDir ? 'Folder' : 'File'}?`,
    description: `Are you sure you want to permanently delete "${name}"? This cannot be undone.`,
    showInput: false,
    confirmText: 'Delete Permanently',
    isDanger: true,
    onConfirm: async () => {
      try {
        const res = await fetch(`/api/files/delete?path=${encodeURIComponent(path)}`, {
          method: 'DELETE'
        });
        const data = await res.json();
        if (!res.ok) {
          showNotice(data.detail || 'Could not delete item', true);
          return;
        }
        showNotice(`Deleted "${name}" successfully.`);
        loadDirectory(state.currentPath);
      } catch (err) {
        showNotice('Failed to delete item', true);
      }
    }
  });
}

// ==========================================
// Event Listeners & Drag-Drop Handling
// ==========================================

function setupEventListeners() {
  // Search filter
  elements.searchInput.addEventListener('input', (e) => {
    state.filterQuery = e.target.value;
    filterAndRenderItems();
  });

  // View modes
  elements.listViewBtn.addEventListener('click', () => applyViewMode('table'));
  elements.gridViewBtn.addEventListener('click', () => applyViewMode('grid'));

  // Upload buttons
  elements.uploadBtn.addEventListener('click', () => elements.fileUploadInput.click());
  elements.fileUploadInput.addEventListener('change', (e) => {
    uploadFiles(e.target.files);
    e.target.value = '';
  });

  // Toolbar actions
  elements.newFolderBtn.addEventListener('click', promptNewFolder);
  elements.newFileBtn.addEventListener('click', promptNewFile);
  elements.downloadZipBtn.addEventListener('click', () => downloadDirectoryZip());

  // Editor modal controls
  elements.editorCloseBtn.addEventListener('click', closeEditorModal);
  elements.editorSaveBtn.addEventListener('click', saveEditorFile);
  elements.editorModeSelect.addEventListener('change', (e) => {
    const mode = e.target.value;
    state.editor.instance.setOption('mode', mode === 'plain' ? null : mode);
  });

  // Logout
  elements.logoutBtn.addEventListener('click', async () => {
    await fetch('/api/auth/logout', { method: 'POST' });
    window.location.href = '/login';
  });

  // Fullscreen Drag & Drop Handling
  let dragCounter = 0;

  window.addEventListener('dragenter', (e) => {
    e.preventDefault();
    dragCounter++;
    if (dragCounter === 1) {
      elements.dropTargetLabel.textContent = `Uploading to /${state.currentPath || 'Home'}`;
      elements.dropZoneOverlay.classList.remove('opacity-0', 'pointer-events-none');
    }
  });

  window.addEventListener('dragleave', (e) => {
    e.preventDefault();
    dragCounter--;
    if (dragCounter <= 0) {
      dragCounter = 0;
      elements.dropZoneOverlay.classList.add('opacity-0', 'pointer-events-none');
    }
  });

  window.addEventListener('dragover', (e) => {
    e.preventDefault();
  });

  window.addEventListener('drop', (e) => {
    e.preventDefault();
    dragCounter = 0;
    elements.dropZoneOverlay.classList.add('opacity-0', 'pointer-events-none');
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      uploadFiles(e.dataTransfer.files);
    }
  });
}

// Helper utilities
function showLoading(show) {
  elements.loadingOverlay.classList.toggle('hidden', !show);
}

function showNotice(msg, isError = false) {
  // Quick toast notification
  const toast = document.createElement('div');
  toast.className = `fixed top-5 right-5 z-50 px-4 py-3 rounded-xl shadow-2xl text-sm font-medium border transition-all duration-300 transform translate-y-2 opacity-0 flex items-center gap-2 ${
    isError 
      ? 'bg-rose-900/90 text-rose-200 border-rose-700/80 shadow-rose-900/40' 
      : 'bg-emerald-900/90 text-emerald-200 border-emerald-700/80 shadow-emerald-900/40'
  }`;
  toast.innerHTML = `<i class="fa-solid ${isError ? 'fa-triangle-exclamation text-rose-400' : 'fa-circle-check text-emerald-400'}"></i><span>${escapeHtml(msg)}</span>`;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.classList.remove('translate-y-2', 'opacity-0');
  }, 10);

  setTimeout(() => {
    toast.classList.add('translate-y-2', 'opacity-0');
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function escapeHtml(str) {
  return String(str).replace(/[&<>'"]/g, 
    tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag));
}

function escapeJs(str) {
  return String(str).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

// Start app
document.addEventListener('DOMContentLoaded', init);
