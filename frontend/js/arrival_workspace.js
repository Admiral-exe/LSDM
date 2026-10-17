/**
 * Workspace 1: Monthly Arrival Register (100% Offline)
 */

const ArrivalWorkspace = {
  currentFile: '',
  currentGroup: 'DI',
  currentSheet: 'D.I.',

  init() {
    this.setupListeners();
    this.loadFiles();
    this.setDefaultDate();
  },

  setDefaultDate() {
    const today = new Date().toISOString().split('T')[0];
    const dateInput = document.getElementById('w1-input-rec-date');
    if (dateInput) dateInput.value = today;
  },

  setupListeners() {
    // File selector change
    document.getElementById('w1-file-selector')?.addEventListener('change', (e) => {
      this.currentFile = e.target.value;
      this.loadArrivals();
      this.fetchNextSampleNo();
    });

    // Group tabs click
    const groupTabs = document.querySelectorAll('#w1-group-tabs .folder-tab');
    groupTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        groupTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        this.currentGroup = tab.dataset.group;
        this.currentSheet = tab.dataset.sheet;
        this.loadArrivals();
        this.fetchNextSampleNo();
      });
    });

    // Search input
    let searchDebounce;
    document.getElementById('w1-search-input')?.addEventListener('input', (e) => {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => {
        this.loadArrivals(e.target.value);
      }, 250);
    });

    // Rapid Entry Form Submit
    document.getElementById('w1-rapid-entry-form')?.addEventListener('submit', (e) => {
      e.preventDefault();
      this.submitArrival();
    });

    // New Month File Modal Listeners
    document.getElementById('btn-open-new-month-modal')?.addEventListener('click', () => {
      document.getElementById('modal-new-month').classList.add('active');
    });

    document.getElementById('btn-close-new-month')?.addEventListener('click', () => {
      document.getElementById('modal-new-month').classList.remove('active');
    });

    document.getElementById('btn-cancel-new-month')?.addEventListener('click', () => {
      document.getElementById('modal-new-month').classList.remove('active');
    });

    document.getElementById('btn-submit-new-month')?.addEventListener('click', () => {
      this.createNewMonthFile();
    });
  },

  async loadFiles() {
    try {
      const res = await fetch('/api/arrivals/files');
      const data = await res.json();
      const select = document.getElementById('w1-file-selector');
      select.innerHTML = '';

      // Add Global All Months option
      const allOpt = document.createElement('option');
      allOpt.value = 'ALL';
      allOpt.textContent = '📁 All Months / Files (Global Search)';
      select.appendChild(allOpt);

      if (data.files && data.files.length > 0) {
        data.files.forEach(f => {
          const opt = document.createElement('option');
          opt.value = f;
          opt.textContent = f;
          select.appendChild(opt);
        });
        this.currentFile = data.files[0];
        select.value = this.currentFile;
      } else {
        const defaultOpt = document.createElement('option');
        defaultOpt.value = 'APRIL_TEMPLATE.xlsx';
        defaultOpt.textContent = 'APRIL_TEMPLATE.xlsx';
        select.appendChild(defaultOpt);
        this.currentFile = 'APRIL_TEMPLATE.xlsx';
      }

      this.loadArrivals();
      this.fetchNextSampleNo();
    } catch (e) {
      console.error('[Arrival] Failed to load files:', e);
    }
  },

  async fetchNextSampleNo() {
    try {
      const year = App.activeYear || 2026;
      const res = await fetch(`/api/arrivals/next-sample-no?year=${year}&group_code=${this.currentGroup}`);
      const data = await res.json();
      const input = document.getElementById('w1-input-sample-no');
      if (input) input.value = data.next_sample_no || 1;
    } catch (e) {
      console.error('[Arrival] Failed to fetch next sample no:', e);
    }
  },

  async loadArrivals(searchQuery = '') {
    const tbody = document.getElementById('w1-table-body');
    tbody.innerHTML = '<tr><td colspan="11" style="text-align:center; padding: 20px; color: var(--text-muted);">Loading records...</td></tr>';

    try {
      let url = `/api/arrivals?file_name=${encodeURIComponent(this.currentFile)}&group_code=${this.currentGroup}`;
      if (searchQuery) url += `&search=${encodeURIComponent(searchQuery)}`;

      const res = await fetch(url);
      const data = await res.json();

      if (!data.data || data.data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="11" style="text-align:center; padding: 30px; color: var(--text-muted);">No arrival records found in tab '${this.currentSheet}' of '${this.currentFile}'.</td></tr>`;
        return;
      }

      tbody.innerHTML = '';
      data.data.forEach(item => {
        const isDispatched = (item.dispatch_status === 'DISPATCHED');
        const ledClass = isDispatched ? 'led-green' : 'led-amber';
        const ledTitle = isDispatched ? 'Dispatched to Master' : 'Pending Testing/Dispatch';

        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><span class="led ${ledClass}" title="${ledTitle}"></span></td>
          <td class="table-cell-mono">${item.sr_no}</td>
          <td class="table-cell-mono" style="font-weight: 700; color: #60a5fa;">${item.sample_no}</td>
          <td>${item.receive_date || ''}</td>
          <td style="font-weight: 600;">${item.sample_name}</td>
          <td class="table-cell-mono">${item.batch_no}</td>
          <td>${item.exp_date || ''}</td>
          <td>${item.name_of_mfg || ''}</td>
          <td>${item.di_name_city || ''}</td>
          <td class="table-cell-mono">${item.memorandum}</td>
          <td style="text-align: center;">
            <div style="display: flex; gap: 6px; justify-content: center;">
              <button class="btn btn-sm btn-icon" title="Dispatch this sample" onclick="ArrivalWorkspace.quickDispatch(${item.id})">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"></polyline></svg>
              </button>
              <button class="btn btn-sm btn-icon btn-danger" title="Delete Row" onclick="ArrivalWorkspace.deleteRow(${item.id}, ${item.sample_no})">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
              </button>
            </div>
          </td>
        `;
        tbody.appendChild(tr);
      });
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="11" style="text-align:center; padding: 20px; color: var(--led-red);">Failed to load arrivals: ${e}</td></tr>`;
    }
  },

  async submitArrival() {
    App.setStatus('WRITING EXCEL', 'amber');

    let targetFile = this.currentFile;
    if (targetFile === 'ALL') {
      const select = document.getElementById('w1-file-selector');
      for (let i = 0; i < select.options.length; i++) {
        if (select.options[i].value !== 'ALL') {
          targetFile = select.options[i].value;
          break;
        }
      }
      if (!targetFile || targetFile === 'ALL') targetFile = 'APRIL_TEMPLATE.xlsx';
    }

    const payload = {
      file_name: targetFile,
      month_name: targetFile.split(' ')[0] || 'APRIL',
      year: App.activeYear || 2026,
      sheet_name: this.currentSheet,
      group_code: this.currentGroup,
      sample_no: parseInt(document.getElementById('w1-input-sample-no').value),
      receive_date: document.getElementById('w1-input-rec-date').value,
      batch_no: document.getElementById('w1-input-batch-no').value.trim(),
      sample_name: document.getElementById('w1-input-sample-name').value.trim(),
      exp_date: document.getElementById('w1-input-exp-date').value.trim(),
      name_of_mfg: document.getElementById('w1-input-mfg-name').value.trim(),
      inspector_name: document.getElementById('w1-input-inspector').value.trim(),
      city_district: document.getElementById('w1-input-district').value,
      memorandum: document.getElementById('w1-input-memo').value.trim(),
    };

    try {
      const res = await fetch('/api/arrivals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (!res.ok) {
        App.setStatus('ERROR', 'red');
        alert('Arrival Error: ' + data.detail);
        return;
      }

      App.setStatus('SYNCED', 'green');
      this.loadArrivals();

      // Reset form and advance sample number for rapid keyboard entry
      document.getElementById('w1-input-batch-no').value = '';
      document.getElementById('w1-input-sample-name').value = '';
      document.getElementById('w1-input-exp-date').value = '';
      document.getElementById('w1-input-memo').value = '';
      this.fetchNextSampleNo();

      // Re-focus Batch No for rapid keyboard traversal
      document.getElementById('w1-input-batch-no').focus();
    } catch (e) {
      App.setStatus('ERROR', 'red');
      alert('Failed to save arrival: ' + e);
    }
  },

  quickDispatch(arrivalId) {
    App.switchWorkspace('w2');
    DispatchWorkspace.lookupById(arrivalId);
  },

  async deleteRow(arrivalId, sampleNo) {
    if (!confirm(`Are you sure you want to delete Sample #${sampleNo}? Subsequent rows will shift up by 1 in Excel and SQLite.`)) {
      return;
    }

    App.setStatus('DELETING ROW', 'amber');
    try {
      const res = await fetch(`/api/arrivals/${arrivalId}`, { method: 'DELETE' });
      const data = await res.json();

      if (!res.ok) {
        alert('Delete failed: ' + data.detail);
        App.setStatus('ERROR', 'red');
        return;
      }

      App.setStatus('SYNCED', 'green');
      this.loadArrivals();
      this.fetchNextSampleNo();
    } catch (e) {
      App.setStatus('ERROR', 'red');
      alert('Delete error: ' + e);
    }
  },

  async createNewMonthFile() {
    const month = document.getElementById('new-month-select').value;
    const year = parseInt(document.getElementById('new-month-year').value);

    try {
      const res = await fetch('/api/arrivals/new-month-file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ month_name: month, year: year })
      });
      const data = await res.json();

      if (!res.ok) {
        alert('Cannot create file: ' + data.detail);
        return;
      }

      document.getElementById('modal-new-month').classList.remove('active');
      alert(`Created clean 5-tab monthly file: ${data.file_name}`);
      await this.loadFiles();
      document.getElementById('w1-file-selector').value = data.file_name;
      this.currentFile = data.file_name;
      this.loadArrivals();
      this.fetchNextSampleNo();
    } catch (e) {
      alert('Failed to create monthly file: ' + e);
    }
  }
};
