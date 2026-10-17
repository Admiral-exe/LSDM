/**
 * Global Application Core & State Management (100% Offline)
 */

const App = {
  activeWorkspace: 'w1',
  activeYear: 2026,
  currentTheme: 'dark',
  districts: [],
  inspectors: [],
  manufacturers: [],

  async init() {
    console.log('[App] Initializing Laboratory Sample & Supply Management System...');
    this.initTheme();
    this.setupWorkspaceNavigation();
    this.setupGlobalHotkeys();
    this.setupWebSocket();
    this.startClock();

    // Fetch initial workspace config & lookups
    await this.loadConfig();
    await this.loadLookups();

    // Initialize individual workspaces
    ArrivalWorkspace.init();
    DispatchWorkspace.init();
    TallyWorkspace.init();
    DirectoryWorkspace.init();
  },

  initTheme() {
    const saved = localStorage.getItem('lab_theme') || 'dark';
    this.applyTheme(saved);

    const toggleBtn = document.getElementById('btn-theme-toggle');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', () => {
        const nextTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        this.applyTheme(nextTheme);
      });
    }
  },

  applyTheme(theme) {
    this.currentTheme = theme;
    localStorage.setItem('lab_theme', theme);
    document.documentElement.setAttribute('data-theme', theme);

    const iconEl = document.getElementById('theme-icon-container');
    const textEl = document.getElementById('theme-text-label');

    if (theme === 'light') {
      if (iconEl) {
        iconEl.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>`;
      }
      if (textEl) textEl.textContent = 'Dark';
    } else {
      if (iconEl) {
        iconEl.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>`;
      }
      if (textEl) textEl.textContent = 'Light';
    }
  },

  async loadConfig() {
    try {
      const res = await fetch('/api/directories/config');
      const data = await res.json();
      this.activeYear = data.active_year || 2026;
      document.getElementById('active-year-badge').textContent = `YEAR ${this.activeYear}`;
      document.getElementById('workspace-folder-display').textContent = data.workspace_folder_path;
      document.getElementById('footer-workspace-name').textContent = data.workspace_folder_path;
    } catch (e) {
      console.error('[App] Failed to load config:', e);
    }

    try {
      const vRes = await fetch('/api/version');
      if (vRes.ok) {
        const vData = await vRes.json();
        const vBadge = document.getElementById('app-version-badge');
        if (vBadge && vData.version) {
          vBadge.textContent = `v${vData.version}`;
          vBadge.title = `${vData.full_name} (${vData.build_date})`;
        }
      }
    } catch (_) {}
  },

  async loadLookups() {
    try {
      const [distRes, mfgRes, inspRes] = await Promise.all([
        fetch('/api/directories/districts'),
        fetch('/api/directories/manufacturers'),
        fetch('/api/directories/inspectors')
      ]);

      const distData = await distRes.json();
      this.districts = distData.data || [];

      const mfgData = await mfgRes.json();
      this.manufacturers = mfgData.data || [];

      const inspData = await inspRes.json();
      this.inspectors = inspData.data || [];

      this.populateDatalists();
    } catch (e) {
      console.error('[App] Failed to load lookups:', e);
    }
  },

  populateDatalists() {
    // Populate district select dropdowns
    const districtSelect = document.getElementById('w1-input-district');
    if (districtSelect) {
      districtSelect.innerHTML = '<option value="">-- Select District --</option>';
      this.districts.forEach(d => {
        districtSelect.innerHTML += `<option value="${d.name}">${d.name} (${d.code})</option>`;
      });
    }

    // Populate manufacturer datalist
    const mfgDatalist = document.getElementById('mfg-datalist');
    if (mfgDatalist) {
      mfgDatalist.innerHTML = '';
      this.manufacturers.forEach(m => {
        mfgDatalist.innerHTML += `<option value="${m.short_name_alias}">${m.mfgname}</option>`;
      });
    }

    // Populate inspector datalist
    const inspDatalist = document.getElementById('inspector-datalist');
    if (inspDatalist) {
      inspDatalist.innerHTML = '';
      this.inspectors.forEach(i => {
        inspDatalist.innerHTML += `<option value="${i.inspector_name}">${i.default_district_name || ''}</option>`;
      });
    }
  },

  setupWorkspaceNavigation() {
    const navButtons = document.querySelectorAll('.nav-tab-btn');
    navButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const target = btn.dataset.workspace;
        this.switchWorkspace(target);
      });
    });
  },

  switchWorkspace(workspaceId) {
    this.activeWorkspace = workspaceId;

    // Update buttons
    document.querySelectorAll('.nav-tab-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.workspace === workspaceId);
    });

    // Update panels
    document.querySelectorAll('.workspace-panel').forEach(p => {
      p.classList.toggle('active', p.id === `workspace-${workspaceId}`);
    });

    // Trigger workspace specific refresh
    if (workspaceId === 'w1') ArrivalWorkspace.loadArrivals();
    if (workspaceId === 'w2') DispatchWorkspace.refreshState();
    if (workspaceId === 'w3') TallyWorkspace.refresh();
    if (workspaceId === 'w4') DirectoryWorkspace.refresh();
  },

  setupGlobalHotkeys() {
    window.addEventListener('keydown', (e) => {
      // Ctrl + 1/2/3/4 Workspace Switcher
      if (e.ctrlKey && ['1', '2', '3', '4'].includes(e.key)) {
        e.preventDefault();
        this.switchWorkspace(`w${e.key}`);
      }

      // Ctrl + F: Focus search in active workspace
      if (e.ctrlKey && e.key.toLowerCase() === 'f') {
        e.preventDefault();
        if (this.activeWorkspace === 'w1') {
          document.getElementById('w1-search-input').focus();
        } else if (this.activeWorkspace === 'w2') {
          document.getElementById('w2-lookup-input').focus();
        }
      }

      // Ctrl + N: Focus new arrival sample number
      if (e.ctrlKey && e.key.toLowerCase() === 'n') {
        e.preventDefault();
        this.switchWorkspace('w1');
        document.getElementById('w1-input-sample-no').focus();
      }

      // Ctrl + D: Switch to Dispatch lookup
      if (e.ctrlKey && e.key.toLowerCase() === 'd') {
        e.preventDefault();
        this.switchWorkspace('w2');
        document.getElementById('w2-lookup-input').focus();
      }

      // Ctrl + S: Force Re-scan / Sync
      if (e.ctrlKey && e.key.toLowerCase() === 's') {
        e.preventDefault();
        this.forceRescan();
      }
    });

    // Folder selector buttons
    document.getElementById('btn-change-folder')?.addEventListener('click', () => {
      document.getElementById('modal-folder-selector').classList.add('active');
    });

    document.getElementById('btn-close-folder-modal')?.addEventListener('click', () => {
      document.getElementById('modal-folder-selector').classList.remove('active');
    });

    document.getElementById('btn-cancel-folder')?.addEventListener('click', () => {
      document.getElementById('modal-folder-selector').classList.remove('active');
    });

    document.getElementById('btn-save-folder')?.addEventListener('click', async () => {
      const path = document.getElementById('input-folder-path').value.trim();
      if (!path) return;
      try {
        const res = await fetch('/api/directories/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ workspace_folder_path: path })
        });
        const data = await res.json();
        if (res.ok) {
          document.getElementById('modal-folder-selector').classList.remove('active');
          await this.loadConfig();
          this.switchWorkspace(this.activeWorkspace);
        } else {
          alert('Error: ' + data.detail);
        }
      } catch (e) {
        alert('Failed to update folder: ' + e);
      }
    });

    document.getElementById('btn-force-rescan')?.addEventListener('click', () => {
      this.forceRescan();
    });
  },

  async forceRescan() {
    this.setStatus('SYNCING', 'amber');
    try {
      const res = await fetch('/api/directories/rescan', { method: 'POST' });
      const data = await res.json();
      this.setStatus('SYNCED', 'green');
      ArrivalWorkspace.loadFiles();
      ArrivalWorkspace.loadArrivals();
      TallyWorkspace.refresh();
      DirectoryWorkspace.refresh();
    } catch (e) {
      this.setStatus('ERROR', 'red');
      alert('Rescan failed: ' + e);
    }
  },

  setStatus(text, color) {
    const led = document.getElementById('global-status-led');
    const label = document.getElementById('system-status-text');
    if (led) {
      led.className = `led led-${color}`;
    }
    if (label) {
      label.textContent = text;
    }
  },

  setupWebSocket() {
    try {
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const ws = new WebSocket(`${proto}//${window.location.host}/ws`);
      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          console.log('[WebSocket Event]', payload);
          if (payload.event === 'SYNC_REFRESH') {
            this.switchWorkspace(this.activeWorkspace);
          }
        } catch (e) {}
      };
    } catch (e) {
      console.warn('[WebSocket] Running in offline polling fallback.');
    }
  },

  startClock() {
    const timeEl = document.getElementById('footer-time-text');
    setInterval(() => {
      const now = new Date();
      timeEl.textContent = now.toLocaleTimeString();
    }, 1000);
  }
};

window.addEventListener('DOMContentLoaded', () => {
  App.init();
});
