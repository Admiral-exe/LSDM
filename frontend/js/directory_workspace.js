/**
 * Workspace 4: Master Directories & Settings (100% Offline)
 */

const DirectoryWorkspace = {
  init() {
    this.setupListeners();
  },

  refresh() {
    this.loadManufacturers();
    this.loadInspectors();
    this.loadAuditLogs();
  },

  setupListeners() {
    document.getElementById('w4-btn-new-mfg')?.addEventListener('click', () => {
      this.promptAddManufacturer();
    });
  },

  async loadManufacturers() {
    const tbody = document.getElementById('w4-mfg-tbody');
    try {
      const res = await fetch('/api/directories/manufacturers');
      const data = await res.json();

      if (!data.data || data.data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 16px;">No saved manufacturers.</td></tr>';
        return;
      }

      tbody.innerHTML = '';
      data.data.forEach(m => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td style="font-weight: 700; color: #60a5fa;">${m.short_name_alias}</td>
          <td class="table-cell-mono">${m.licence}</td>
          <td>${m.mfgname}</td>
          <td style="font-size: 11px; color: var(--text-dim);">${m.mfgadd3 || ''} ${m.distcd ? '('+m.distcd+')' : ''}</td>
          <td style="text-align: center;">
            <button class="btn btn-sm btn-icon btn-danger" onclick="DirectoryWorkspace.deleteManufacturer(${m.id})">✕</button>
          </td>
        `;
        tbody.appendChild(tr);
      });
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--led-red);">Failed to load manufacturers: ${e}</td></tr>`;
    }
  },

  async loadInspectors() {
    const tbody = document.getElementById('w4-inspector-tbody');
    try {
      const res = await fetch('/api/directories/inspectors');
      const data = await res.json();

      if (!data.data || data.data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--text-muted); padding: 16px;">No inspectors recorded.</td></tr>';
        return;
      }

      tbody.innerHTML = '';
      data.data.forEach(i => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td style="font-weight: 600;">${i.inspector_name}</td>
          <td>${i.default_district_name || '--'}</td>
          <td class="table-cell-mono">${i.default_district_code || '--'}</td>
        `;
        tbody.appendChild(tr);
      });
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--led-red);">Failed to load inspectors: ${e}</td></tr>`;
    }
  },

  async loadAuditLogs() {
    const tbody = document.getElementById('w4-audit-tbody');
    try {
      const res = await fetch('/api/directories/audit-logs');
      const data = await res.json();

      if (!data.data || data.data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 16px;">No sync audit logs yet.</td></tr>';
        return;
      }

      tbody.innerHTML = '';
      data.data.forEach(log => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td class="table-cell-mono" style="font-size: 11px;">${log.timestamp}</td>
          <td><span class="plate-badge" style="font-size: 10px;">${log.action}</span></td>
          <td style="font-weight: 600;">${log.target_file}</td>
          <td class="table-cell-mono" style="font-size: 10px; color: var(--text-dim); max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${log.backup_path || ''}">${log.backup_path || '--'}</td>
          <td style="font-size: 11px; color: var(--text-dim);">${log.details || ''}</td>
        `;
        tbody.appendChild(tr);
      });
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--led-red);">Failed to load audit log: ${e}</td></tr>`;
    }
  },

  async promptAddManufacturer() {
    const alias = prompt('Short Name Alias (e.g., SUN PHARMA):');
    if (!alias) return;
    const licence = prompt('Licence # (@):', 'G/25/1234');
    if (!licence) return;
    const mfgname = prompt('Formal Corporate Name:', alias);
    if (!mfgname) return;
    const add1 = prompt('Address Line 1:');
    const add2 = prompt('Address Line 2:');
    const add3 = prompt('City / District:');
    const distcd = prompt('District Code:');
    const statecd = prompt('State Code:', '24');

    try {
      const res = await fetch('/api/directories/manufacturers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          short_name_alias: alias,
          licence: licence,
          mfgname: mfgname,
          mfgadd1: add1 || '',
          mfgadd2: add2 || '',
          mfgadd3: add3 || '',
          distcd: distcd || '',
          statecd: statecd || '24'
        })
      });
      if (res.ok) {
        this.loadManufacturers();
        App.loadLookups();
      }
    } catch (e) {
      alert('Failed to save manufacturer: ' + e);
    }
  },

  async deleteManufacturer(mfgId) {
    if (!confirm('Delete this manufacturer profile?')) return;
    try {
      const res = await fetch(`/api/directories/manufacturers/${mfgId}`, { method: 'DELETE' });
      if (res.ok) {
        this.loadManufacturers();
        App.loadLookups();
      }
    } catch (e) {
      alert('Delete failed: ' + e);
    }
  }
};
