/**
 * Workspace 3: Multi-File Tally & Reconciliation Engine (100% Offline)
 */

const TallyWorkspace = {
  currentFilter: 'ALL',

  init() {
    this.setupListeners();
  },

  refresh() {
    this.loadSummary();
    this.loadDetails();
  },

  setupListeners() {
    // Filter buttons
    const filterBtns = document.querySelectorAll('.w3-filter-toolbar .btn[data-filter]');
    filterBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        filterBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.currentFilter = btn.dataset.filter;
        this.loadDetails();
      });
    });

    // Refresh button
    document.getElementById('w3-btn-refresh-tally')?.addEventListener('click', () => {
      this.refresh();
    });
  },

  async loadSummary() {
    try {
      const res = await fetch('/api/tally/summary');
      const data = await res.json();

      document.getElementById('m-total-arrived').textContent = data.total_arrived || 0;
      document.getElementById('m-total-dispatched').textContent = data.total_dispatched || 0;
      document.getElementById('m-tallied').textContent = data.tallied || 0;
      document.getElementById('m-pending').textContent = data.pending_dispatches || 0;
      document.getElementById('m-orphan').textContent = data.orphan_masters || 0;
      document.getElementById('m-discrepancies').textContent = data.discrepancies || 0;
    } catch (e) {
      console.error('[Tally] Failed to load summary:', e);
    }
  },

  async loadDetails() {
    const tbody = document.getElementById('w3-tally-body');
    tbody.innerHTML = '<tr><td colspan="11" style="text-align: center; color: var(--text-muted); padding: 20px;">Re-evaluating cross-file reconciliation...</td></tr>';

    try {
      const res = await fetch(`/api/tally/details?filter_type=${this.currentFilter}`);
      const data = await res.json();

      if (!data.data || data.data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="11" style="text-align: center; color: var(--text-muted); padding: 30px;">No records matching filter '${this.currentFilter}'.</td></tr>`;
        return;
      }

      tbody.innerHTML = '';
      data.data.forEach(item => {
        const tr = document.createElement('tr');
        const ledClass = `led-${item.led.toLowerCase()}`;
        const hasBatchDiff = item.monthly_batch && item.master_batch && item.monthly_batch.trim().toUpperCase() !== item.master_batch.trim().toUpperCase();
        const hasMemoDiff = item.monthly_memo && item.master_memo && item.monthly_memo.trim().toUpperCase() !== item.master_memo.trim().toUpperCase();

        const batchStyle = hasBatchDiff ? 'color: #ff3366; font-weight: 700; background: rgba(255, 51, 102, 0.1);' : '';
        const memoStyle = hasMemoDiff ? 'color: #ff3366; font-weight: 700; background: rgba(255, 51, 102, 0.1);' : '';

        let actionBtn = '--';
        if (hasBatchDiff) {
          actionBtn = `<button class="btn btn-sm btn-accent" onclick="TallyWorkspace.syncField(${item.monthly_id}, ${item.master_id}, 'batch_no')">Sync Batch</button>`;
        } else if (hasMemoDiff) {
          actionBtn = `<button class="btn btn-sm btn-accent" onclick="TallyWorkspace.syncField(${item.monthly_id}, ${item.master_id}, 'memorandum')">Sync Memo</button>`;
        } else if (item.status === 'PENDING') {
          actionBtn = `<button class="btn btn-sm" onclick="ArrivalWorkspace.quickDispatch(${item.monthly_id})">Dispatch</button>`;
        }

        tr.innerHTML = `
          <td><span class="led ${ledClass}"></span></td>
          <td style="font-size: 11px; color: var(--text-dim);">${item.monthly_file || '--'} (${item.monthly_sheet || '--'})</td>
          <td class="table-cell-mono" style="font-weight: 700; color: #60a5fa;">#${item.sample_no || '--'}</td>
          <td>${item.sample_name || '--'}</td>
          <td class="table-cell-mono" style="${batchStyle}">${item.monthly_batch || '--'}</td>
          <td class="table-cell-mono" style="${batchStyle}">${item.master_batch || '--'}</td>
          <td class="table-cell-mono" style="${memoStyle}">${item.monthly_memo || '--'}</td>
          <td class="table-cell-mono" style="${memoStyle}">${item.master_memo || '--'}</td>
          <td class="table-cell-mono" style="font-weight: 700; color: #00e676;">${item.sampno || '--'}</td>
          <td style="font-size: 11px; color: ${item.led === 'RED' ? '#ff3366' : 'var(--text-dim)'};">
            ${item.mismatches.join('; ')}
          </td>
          <td style="text-align: center;">${actionBtn}</td>
        `;
        tbody.appendChild(tr);
      });
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="11" style="text-align: center; color: var(--led-red); padding: 20px;">Failed to load tally details: ${e}</td></tr>`;
    }
  },

  async syncField(monthlyId, masterId, fieldName) {
    if (!confirm(`Synchronize ${fieldName} from Monthly arrival to Master dispatch?`)) return;

    try {
      const res = await fetch('/api/tally/repair-sync-field', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          monthly_id: monthlyId,
          master_id: masterId,
          field_name: fieldName,
          source: 'monthly'
        })
      });
      const data = await res.json();
      if (res.ok) {
        alert(data.message);
        this.refresh();
      } else {
        alert('Sync error: ' + data.detail);
      }
    } catch (e) {
      alert('Sync failed: ' + e);
    }
  }
};
