/**
 * Workspace 2: Lab Testing & Master Dispatch Entry (100% Offline)
 */

const DispatchWorkspace = {
  activeArrival: null,

  init() {
    this.setupListeners();
    this.setDefaultDates();
  },

  refreshState() {
    this.setDefaultDates();
  },

  setDefaultDates() {
    const today = new Date().toISOString().split('T')[0];
    const dTest = document.getElementById('w2-date-test');
    const dSamp = document.getElementById('w2-date-samp');
    const dAr = document.getElementById('w2-ar-report-date');
    if (dTest && !dTest.value) dTest.value = today;
    if (dSamp && !dSamp.value) dSamp.value = today;
    if (dAr && !dAr.value) dAr.value = today;
  },

  setupListeners() {
    // Lookup search button & enter key
    document.getElementById('w2-btn-lookup')?.addEventListener('click', () => {
      this.performLookup();
    });

    document.getElementById('w2-lookup-input')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        this.performLookup();
      }
    });

    // Result select toggle (show NSQ defect specifics if 2 - NSQ)
    document.getElementById('w2-select-result')?.addEventListener('change', (e) => {
      const nsqBlock = document.getElementById('w2-nsq-block');
      if (e.target.value === '2') {
        nsqBlock.style.display = 'flex';
      } else {
        nsqBlock.style.display = 'none';
      }
    });

    // Clear form
    document.getElementById('w2-btn-clear')?.addEventListener('click', () => {
      this.clearForm();
    });

    // Submit Dispatch Form
    document.getElementById('w2-dispatch-form')?.addEventListener('submit', (e) => {
      e.preventDefault();
      this.submitDispatch();
    });
  },

  async performLookup() {
    const q = document.getElementById('w2-lookup-input').value.trim();
    if (!q) return;

    try {
      const res = await fetch(`/api/dispatches/lookup-arrival?query=${encodeURIComponent(q)}`);
      const data = await res.json();
      const dropdown = document.getElementById('w2-lookup-dropdown');

      if (!data.results || data.results.length === 0) {
        dropdown.innerHTML = '<div style="padding: 10px; font-size: 12px; color: var(--text-muted);">No matching arrival records found.</div>';
        dropdown.style.display = 'block';
        return;
      }

      dropdown.innerHTML = '';
      data.results.forEach(item => {
        const div = document.createElement('div');
        div.style.padding = '8px 12px';
        div.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
        div.style.cursor = 'pointer';
        div.className = 'lookup-item';

        const isDispatched = item.existing_dispatch_id ? '<span style="color:#00e676; font-size:10px;">[DISPATCHED]</span>' : '<span style="color:#ffaa00; font-size:10px;">[PENDING]</span>';
        div.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: baseline;">
            <strong style="color: #60a5fa;">#${item.sample_no} (${item.group_code})</strong>
            ${isDispatched}
          </div>
          <div style="font-size: 11px; color: var(--text-dim); margin-top: 2px;">
            ${item.sample_name} | Batch: ${item.batch_no} | Memo: ${item.memorandum}
          </div>
        `;
        div.addEventListener('click', () => {
          this.selectArrival(item);
          dropdown.style.display = 'none';
        });
        dropdown.appendChild(div);
      });
      dropdown.style.display = 'block';
    } catch (e) {
      alert('Lookup failed: ' + e);
    }
  },

  async lookupById(arrivalId) {
    try {
      const res = await fetch(`/api/dispatches/lookup-arrival?query=${arrivalId}`);
      const data = await res.json();
      if (data.results && data.results.length > 0) {
        const found = data.results.find(x => x.id === arrivalId) || data.results[0];
        this.selectArrival(found);
      }
    } catch (e) {
      console.error('[Dispatch] Failed to lookup arrival by ID:', e);
    }
  },

  selectArrival(item) {
    this.activeArrival = item;

    // Populate Left Plate (Locked Read-Only Data)
    document.getElementById('w2-val-target-sheet').textContent = item.target_master_sheet || 'DI CMSO UO';
    document.getElementById('w2-val-sampno').textContent = item.suggested_sampno || '--';
    document.getElementById('w2-val-sample-no').textContent = item.sample_no || '--';
    document.getElementById('w2-val-rec-date').textContent = item.receive_date || '--';
    document.getElementById('w2-val-sample-name').textContent = item.sample_name || '--';
    document.getElementById('w2-val-batch-no').textContent = item.batch_no || '--';
    document.getElementById('w2-val-memo').textContent = item.memorandum || '--';
    document.getElementById('w2-val-short-mfg').textContent = item.name_of_mfg || '--';
    document.getElementById('w2-val-inspector-city').textContent = item.di_name_city || '--';

    const plateLed = document.getElementById('w2-plate-led');
    if (item.existing_dispatch_id) {
      plateLed.className = 'led led-green';
      plateLed.title = 'Already Dispatched to Master';
    } else {
      plateLed.className = 'led led-amber';
      plateLed.title = 'Pending Testing & Dispatch';
    }

    // Auto-populate Right Plate Testing Form
    document.getElementById('w2-testrepo-group').value = item.group_code || 'DI';
    document.getElementById('w2-testrepo-yyyy').value = item.year || App.activeYear || 2026;

    // Smart Auto-Memory for Manufacturer 7 Fields
    if (item.manufacturer_memory) {
      const m = item.manufacturer_memory;
      document.getElementById('w2-mfg-licence').value = m.licence || '';
      document.getElementById('w2-mfg-name').value = m.mfgname || '';
      document.getElementById('w2-mfg-add1').value = m.mfgadd1 || '';
      document.getElementById('w2-mfg-add2').value = m.mfgadd2 || '';
      document.getElementById('w2-mfg-add3').value = m.mfgadd3 || '';
      document.getElementById('w2-mfg-distcd').value = m.distcd || '';
      document.getElementById('w2-mfg-statecd').value = m.statecd || '';
    } else {
      // Fallback: populate formal name from short name
      document.getElementById('w2-mfg-name').value = (item.name_of_mfg || '').toUpperCase();
      document.getElementById('w2-mfg-licence').value = '';
      document.getElementById('w2-mfg-add1').value = '';
      document.getElementById('w2-mfg-add2').value = '';
      document.getElementById('w2-mfg-add3').value = '';
      document.getElementById('w2-mfg-distcd').value = '';
      document.getElementById('w2-mfg-statecd').value = '';
    }

    // Focus Licence input for rapid entry
    document.getElementById('w2-mfg-licence').focus();
  },

  async submitDispatch() {
    if (!this.activeArrival) {
      alert('Please lookup and select an arrived sample on the left first!');
      document.getElementById('w2-lookup-input').focus();
      return;
    }

    App.setStatus('WRITING MASTER EXCEL', 'amber');

    const item = this.activeArrival;
    const yearPrefix = (item.year || App.activeYear || 2026) % 100;
    const grp = item.group_code || 'DI';
    const letter = item.suggested_sampno ? item.suggested_sampno.slice(2, -String(item.sample_no).length) : grp[0];

    // District code lookup
    let distocd = null;
    let distoname = item.city_district || '';
    if (item.city_district) {
      const matchedDist = App.districts.find(d => d.name.toUpperCase() === item.city_district.toUpperCase());
      if (matchedDist) {
        distocd = matchedDist.code;
        distoname = matchedDist.name;
      }
    }

    const payload = {
      file_name: 'MASTER_TEMPLATE.xlsx',
      sheet_name: item.target_master_sheet || 'DI CMSO UO',
      sampno: item.suggested_sampno,
      sampno_raw: item.suggested_sampno,
      year_prefix: yearPrefix,
      group_letter: letter,
      sample_no: item.sample_no,
      recdate_iso: item.receive_date,
      sampdate_iso: document.getElementById('w2-date-samp').value,
      type: item.division || '',
      namecd: '',
      sender_name: item.inspector_name || '',
      distocd: distocd,
      distoname: distoname,
      placecd: '',
      placenm: '',
      sampname: item.sample_name,
      batchno: item.batch_no,
      licence: document.getElementById('w2-mfg-licence').value.trim(),
      mfgname: document.getElementById('w2-mfg-name').value.trim(),
      mfgadd1: document.getElementById('w2-mfg-add1').value.trim(),
      mfgadd2: document.getElementById('w2-mfg-add2').value.trim(),
      mfgadd3: document.getElementById('w2-mfg-add3').value.trim(),
      distcd: document.getElementById('w2-mfg-distcd').value.trim(),
      statecd: document.getElementById('w2-mfg-statecd').value.trim(),
      testrepo_q: 'Q',
      testrepo_quarter: parseInt(document.getElementById('w2-testrepo-quarter').value),
      testrepo_no: document.getElementById('w2-testrepo-no').value.trim(),
      testrepo_yyyy: parseInt(document.getElementById('w2-testrepo-yyyy').value),
      testrepo_group: grp,
      testdate_iso: document.getElementById('w2-date-test').value,
      result: parseInt(document.getElementById('w2-select-result').value),
      nsq: document.getElementById('w2-select-result').value === '2' ? 'NSQ' : '',
      det1_nsq: document.getElementById('w2-input-nsq-detail').value.trim(),
      fees: document.getElementById('w2-input-fees').value.trim() || 'NIL',
      ar_report_no: document.getElementById('w2-ar-report-no').value.trim(),
      ar_report_date_iso: document.getElementById('w2-ar-report-date').value,
      di_memo_no: item.memorandum,
      di_memo_date_iso: document.getElementById('w2-date-memo').value,
      govt_analyst: document.getElementById('w2-govt-analyst').value.trim(),
      extra_fees: item.target_master_sheet === 'PDT' ? document.getElementById('w2-input-fees').value.trim() : '',
      monthly_sample_id: item.id
    };

    try {
      const res = await fetch('/api/dispatches', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (!res.ok) {
        App.setStatus('ERROR', 'red');
        alert('Dispatch Error: ' + data.detail);
        return;
      }

      App.setStatus('SYNCED', 'green');
      alert(`Testing results committed and Master Excel synchronized successfully for SAMPNO: ${data.sampno}`);
      this.clearForm();
      App.loadLookups(); // Refresh manufacturer memory cache
    } catch (e) {
      App.setStatus('ERROR', 'red');
      alert('Failed to commit dispatch: ' + e);
    }
  },

  clearForm() {
    this.activeArrival = null;
    document.getElementById('w2-lookup-input').value = '';
    document.getElementById('w2-val-target-sheet').textContent = '--';
    document.getElementById('w2-val-sampno').textContent = '--';
    document.getElementById('w2-val-sample-no').textContent = '--';
    document.getElementById('w2-val-rec-date').textContent = '--';
    document.getElementById('w2-val-sample-name').textContent = '--';
    document.getElementById('w2-val-batch-no').textContent = '--';
    document.getElementById('w2-val-memo').textContent = '--';
    document.getElementById('w2-val-short-mfg').textContent = '--';
    document.getElementById('w2-val-inspector-city').textContent = '--';
    document.getElementById('w2-plate-led').className = 'led led-amber';

    document.getElementById('w2-dispatch-form').reset();
    this.setDefaultDates();
  }
};
