/**
 * Hospital Government of India - Admin Portal Engine
 * Multi-Tab Controller: Home, Doctors, Appointments, Bookings, Notifications, Settings
 * Dynamic Charts (Year, Month, Week, Day) + Specialty & Type Filtering
 */

document.addEventListener('DOMContentLoaded', () => {
  initAdminTabs();
  initHomeTelemetryChart();
  initAppointmentsChart();
  initAppointmentsTableFilters();
  initDoctorTableSearch();
  initAddDoctorForm();
  initDoctorActions();
});

// 1. Admin Tab Switching Controller
function initAdminTabs() {
  const tabBtns = document.querySelectorAll('.btn-admin-tab');

  function switchAdminTab(target) {
    if (!target) return;

    tabBtns.forEach(b => {
      if (b.getAttribute('data-tab') === target) {
        b.classList.add('active');
        b.style.background = 'var(--primary-navy)';
        b.style.color = '#ffffff';
      } else {
        b.classList.remove('active');
        b.style.background = '#ffffff';
        b.style.color = '#334155';
      }
    });

    document.querySelectorAll('.admin-tab-pane').forEach(pane => {
      pane.style.display = 'none';
      pane.classList.remove('active');
    });

    const activePane = document.getElementById(`pane-admin-${target}`);
    if (activePane) {
      activePane.style.display = 'block';
      activePane.classList.add('active');
      window.location.hash = target;
    }

    // Re-render chart dynamically when tab opens to ensure correct canvas sizing
    setTimeout(() => {
      if (target === 'home' && typeof window.renderHomeTelemetryChart === 'function') {
        window.renderHomeTelemetryChart();
      } else if (target === 'appointments' && typeof window.renderAppointmentsChart === 'function') {
        window.renderAppointmentsChart();
      }
    }, 50);
  }

  tabBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const target = btn.getAttribute('data-tab');
      switchAdminTab(target);
    });
  });

  // Handle URL hash on load (e.g. #doctors, #appointments)
  const hash = window.location.hash.replace('#', '');
  if (hash && document.getElementById(`pane-admin-${hash}`)) {
    switchAdminTab(hash);
  }
}

// 2. Home Tab Single Dynamic Telemetry Chart (Year / Month / Week / Day)
let homeChart = null;
function initHomeTelemetryChart() {
  const canvas = document.getElementById('admin-home-telemetry-chart');
  if (!canvas || !window.Chart) return;

  const rawData = window.ADMIN_TIME_SERIES_DATA || {};
  let currentPeriod = 'month';

  function renderChart(period) {
    currentPeriod = period || currentPeriod;
    const periodData = rawData[currentPeriod] || rawData['month'];
    if (!periodData) return;

    if (homeChart) {
      homeChart.destroy();
    }

    homeChart = new Chart(canvas.getContext('2d'), {
      type: 'line',
      data: {
        labels: periodData.labels,
        datasets: [
          {
            label: 'Total Appointments Registered',
            data: periodData.total,
            borderColor: '#0b2545',
            backgroundColor: 'rgba(11, 37, 69, 0.08)',
            borderWidth: 3,
            fill: true,
            tension: 0.35,
            pointBackgroundColor: '#0b2545',
            pointRadius: 4
          },
          {
            label: 'Completed Consultations',
            data: periodData.completed,
            borderColor: '#00a86b',
            backgroundColor: 'rgba(0, 168, 107, 0.08)',
            borderWidth: 3,
            fill: true,
            tension: 0.35,
            pointBackgroundColor: '#00a86b',
            pointRadius: 4
          },
          {
            label: 'Pre-Appointments / In-Queue',
            data: periodData.pre_appointments,
            borderColor: '#ff9933',
            backgroundColor: 'transparent',
            borderWidth: 2,
            borderDash: [5, 5],
            tension: 0.35,
            pointBackgroundColor: '#ff9933',
            pointRadius: 3
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            position: 'top',
            labels: { font: { family: 'Inter', size: 12, weight: '600' } }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: { color: '#f1f5f9' },
            ticks: { font: { family: 'Inter', size: 11 } }
          },
          x: {
            grid: { display: false },
            ticks: { font: { family: 'Inter', size: 11 } }
          }
        }
      }
    });

    window.homeChart = homeChart;
  }

  window.renderHomeTelemetryChart = () => renderChart(currentPeriod);
  renderChart(currentPeriod);

  // Timeframe Buttons Click Listener
  const timeframeBtns = document.querySelectorAll('#home-chart-timeframe-btns .btn-timeframe');
  timeframeBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      timeframeBtns.forEach(b => {
        b.classList.remove('active');
        b.style.background = '#ffffff';
        b.style.color = 'var(--primary-navy)';
      });

      btn.classList.add('active');
      btn.style.background = 'var(--primary-navy)';
      btn.style.color = '#ffffff';

      const period = btn.getAttribute('data-period');
      renderChart(period);
    });
  });
}

// 3. Appointments Tab Dedicated Dynamic Chart (Year / Month / Week / Day)
let aptsChart = null;
function initAppointmentsChart() {
  const canvas = document.getElementById('admin-appointments-chart');
  if (!canvas || !window.Chart) return;

  const rawData = window.ADMIN_TIME_SERIES_DATA || {};
  let currentPeriod = 'month';

  function renderChart(period) {
    currentPeriod = period || currentPeriod;
    const periodData = rawData[currentPeriod] || rawData['month'];
    if (!periodData) return;

    if (aptsChart) {
      aptsChart.destroy();
    }

    aptsChart = new Chart(canvas.getContext('2d'), {
      type: 'bar',
      data: {
        labels: periodData.labels,
        datasets: [
          {
            label: 'Completed Consultations',
            data: periodData.completed,
            backgroundColor: '#00a86b',
            borderRadius: 6
          },
          {
            label: 'Pre-Appointments (Confirmed / In-Queue)',
            data: periodData.pre_appointments,
            backgroundColor: '#f59e0b',
            borderRadius: 6
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            labels: { font: { family: 'Inter', size: 12 } }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: { color: '#f1f5f9' }
          },
          x: {
            grid: { display: false }
          }
        }
      }
    });

    window.aptsChart = aptsChart;
  }

  window.renderAppointmentsChart = () => renderChart(currentPeriod);
  renderChart(currentPeriod);

  const timeframeBtns = document.querySelectorAll('#apts-chart-timeframe-btns .btn-apt-timeframe');
  timeframeBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      timeframeBtns.forEach(b => {
        b.classList.remove('active');
        b.style.background = '#ffffff';
        b.style.color = 'var(--primary-navy)';
      });

      btn.classList.add('active');
      btn.style.background = 'var(--primary-navy)';
      btn.style.color = '#ffffff';

      const period = btn.getAttribute('data-period');
      renderChart(period);
    });
  });
}

// 4. Appointments Table Multi-Filter (Search Query, Medical Type / Test, Status)
function initAppointmentsTableFilters() {
  const searchInput = document.getElementById('admin-apt-search');
  const typeFilter = document.getElementById('admin-apt-type-filter');
  const statusFilter = document.getElementById('admin-apt-status-filter');
  const tbody = document.getElementById('admin-master-apts-tbody');

  if (!tbody) return;

  function filterAppointments() {
    const query = searchInput ? searchInput.value.toLowerCase().trim() : '';
    const selectedType = typeFilter ? typeFilter.value : 'all';
    const selectedStatus = statusFilter ? statusFilter.value : '';

    const rows = tbody.querySelectorAll('tr');

    rows.forEach(row => {
      const rowType = row.getAttribute('data-type') || '';
      const rowStatus = row.getAttribute('data-status') || '';
      const rowText = row.getAttribute('data-text') || '';

      const matchQuery = !query || rowText.includes(query);
      const matchType = selectedType === 'all' || rowType.toLowerCase().includes(selectedType.toLowerCase()) || rowText.includes(selectedType.toLowerCase());
      const matchStatus = !selectedStatus || rowStatus === selectedStatus;

      if (matchQuery && matchType && matchStatus) {
        row.style.display = '';
      } else {
        row.style.display = 'none';
      }
    });
  }

  if (searchInput) searchInput.addEventListener('input', filterAppointments);
  if (typeFilter) typeFilter.addEventListener('change', filterAppointments);
  if (statusFilter) statusFilter.addEventListener('change', filterAppointments);
}

// 5. Search & Filter in Doctor Management Table
function initDoctorTableSearch() {
  const searchInput = document.getElementById('admin-doc-search');
  const deptFilter = document.getElementById('admin-doc-dept-filter');
  const tbody = document.getElementById('admin-doctors-tbody');
  const countDisplay = document.getElementById('admin-doc-count-display');

  if (!tbody) return;

  function filterTable() {
    const query = searchInput ? searchInput.value.toLowerCase().trim() : '';
    const dept = deptFilter ? deptFilter.value : '';
    const rows = tbody.querySelectorAll('tr');
    let visibleCount = 0;

    rows.forEach(row => {
      const rowName = row.getAttribute('data-name') || '';
      const rowId = row.getAttribute('data-id') || '';
      const rowDept = row.getAttribute('data-dept') || '';

      const matchQuery = !query || rowName.includes(query) || rowId.includes(query) || rowDept.toLowerCase().includes(query);
      const matchDept = !dept || rowDept === dept;

      if (matchQuery && matchDept) {
        row.style.display = '';
        visibleCount++;
      } else {
        row.style.display = 'none';
      }
    });

    if (countDisplay) countDisplay.textContent = visibleCount;
  }

  if (searchInput) searchInput.addEventListener('input', filterTable);
  if (deptFilter) deptFilter.addEventListener('change', filterTable);
}

// 6. Add New Doctor via AJAX
function initAddDoctorForm() {
  const form = document.getElementById('form-add-doctor');
  const modal = document.getElementById('modal-add-doctor');
  const submitBtn = document.getElementById('btn-submit-add-doctor');

  if (!form) return;

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const name = document.getElementById('add-doc-name').value.trim();
    const docReg = document.getElementById('add-doc-reg').value.trim();
    const phone = document.getElementById('add-doc-phone').value.trim();
    const email = document.getElementById('add-doc-email').value.trim();
    const password = document.getElementById('add-doc-password').value.trim();
    const status = document.getElementById('add-doc-status').value;
    const dept = document.getElementById('add-doc-dept').value;
    const hospitalId = document.getElementById('add-doc-hospital').value;
    const room = document.getElementById('add-doc-room').value.trim();
    const duration = document.getElementById('add-doc-duration').value;
    const startTime = document.getElementById('add-doc-start-time').value;
    const endTime = document.getElementById('add-doc-end-time').value;
    const qual = document.getElementById('add-doc-qual').value;
    const desig = document.getElementById('add-doc-desig').value;
    const exp = document.getElementById('add-doc-exp').value;
    const slots = document.getElementById('add-doc-slots').value;
    const days = document.getElementById('add-doc-days').value;

    if (!name || !hospitalId || !phone) {
      alert('Please fill Doctor Name, Phone, and Hospital.');
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = 'Saving Doctor...';

    fetch('/api/admin/doctors/add/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: name,
        doctor_reg_id: docReg,
        phone: phone,
        email: email,
        password: password,
        status: status,
        department: dept,
        hospital_id: hospitalId,
        consultation_room: room,
        slot_duration_mins: duration,
        opd_start_time: startTime,
        opd_end_time: endTime,
        qualification: qual,
        designation: desig,
        experience_years: exp,
        max_daily_slots: slots,
        available_days: days
      })
    })
    .then(res => res.json())
    .then(data => {
      submitBtn.disabled = false;
      submitBtn.textContent = '✓ Save & Add Doctor to Hospital Roster';
      if (data.success) {
        alert(data.message);
        if (modal) modal.classList.remove('open');
        window.location.reload();
      } else {
        alert('Error: ' + data.message);
      }
    })
    .catch(err => {
      submitBtn.disabled = false;
      submitBtn.textContent = '✓ Save & Add Doctor to Hospital Roster';
      alert('Network error adding doctor.');
    });
  });
}

// 7. Toggle Duty Presence & Remove Doctor Actions
function initDoctorActions() {
  // Toggle Presence
  document.querySelectorAll('.btn-toggle-presence').forEach(btn => {
    btn.addEventListener('click', () => {
      const docId = btn.getAttribute('data-id');
      btn.disabled = true;
      btn.textContent = 'Updating...';

      fetch(`/api/admin/doctors/${docId}/toggle-presence/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      .then(res => res.json())
      .then(data => {
        btn.disabled = false;
        if (data.success) {
          if (data.is_present_today) {
            btn.innerHTML = '🟢 Present in Hospital';
            btn.style.background = '#dcfce7';
            btn.style.color = '#15803d';
            btn.style.borderColor = '#86efac';
          } else {
            btn.innerHTML = '🔴 Off Duty / Absent';
            btn.style.background = '#fee2e2';
            btn.style.color = '#b91c1c';
            btn.style.borderColor = '#fca5a5';
          }
        }
      })
      .catch(err => {
        btn.disabled = false;
        alert('Error updating status.');
      });
    });
  });

  // Remove Doctor
  document.querySelectorAll('.btn-remove-doctor').forEach(btn => {
    btn.addEventListener('click', () => {
      const docId = btn.getAttribute('data-id');
      const docName = btn.getAttribute('data-name');

      if (confirm(`Are you sure you want to remove ${docName} from the active hospital roster?`)) {
        btn.disabled = true;
        btn.textContent = 'Removing...';

        fetch(`/api/admin/doctors/${docId}/remove/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            alert(data.message);
            const tr = btn.closest('tr');
            if (tr) tr.remove();
          } else {
            alert('Error: ' + data.message);
            btn.disabled = false;
            btn.textContent = '🗑️ Remove';
          }
        })
        .catch(err => {
          alert('Error removing doctor.');
          btn.disabled = false;
          btn.textContent = '🗑️ Remove';
        });
      }
    });
  });
}

// ==================== 8. AUDIT LOG VIEWER & SEARCH ====================
async function loadAuditLogs() {
  const tbody = document.getElementById('audit-table-tbody');
  if (!tbody) return;
  const q = document.getElementById('audit-search')?.value || '';
  const role = document.getElementById('audit-role-filter')?.value || '';
  const action = document.getElementById('audit-action-filter')?.value || '';

  try {
    const url = `/api/admin/audit-logs/?q=${encodeURIComponent(q)}&role=${encodeURIComponent(role)}&action=${encodeURIComponent(action)}`;
    const res = await fetch(url);
    const data = await res.json();
    if (data.status === 'success') {
      if (!data.logs || data.logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:24px; color:var(--text-muted);">No audit log records match filter criteria.</td></tr>';
        return;
      }
      tbody.innerHTML = data.logs.map(log => `
        <tr style="border-bottom:1px solid #f1f5f9;">
          <td style="padding:10px 12px; font-family:monospace; font-size:0.8rem; color:#64748b;">${log.timestamp}</td>
          <td style="padding:10px 12px; font-weight:700; color:var(--primary-navy);">${log.user}</td>
          <td style="padding:10px 12px;"><span style="font-size:0.75rem; padding:2px 8px; border-radius:12px; font-weight:700; background:#e0f2fe; color:#0369a1;">${log.role}</span></td>
          <td style="padding:10px 12px; font-weight:600; color:#1e293b;">${log.action}</td>
          <td style="padding:10px 12px; font-size:0.82rem; color:#475569;">${log.resource_type ? `<strong>[${log.resource_type}]</strong> ` : ''}${log.details || ''}</td>
          <td style="padding:10px 12px;"><span style="font-size:0.75rem; padding:2px 8px; border-radius:12px; font-weight:700; ${log.status === 'SUCCESS' ? 'background:#dcfce7; color:#15803d;' : 'background:#fee2e2; color:#b91c1c;'}">${log.status}</span></td>
          <td style="padding:10px 12px; font-family:monospace; font-size:0.78rem; color:#64748b;">${log.ip_address}</td>
        </tr>
      `).join('');
    }
  } catch (err) {
    console.error('Failed to load audit logs:', err);
  }
}

// ==================== 9. HEALTH SCHEMES & ADVISORIES CRUD ====================
async function loadSchemesAndAdvisories() {
  const schemesTbody = document.getElementById('schemes-table-tbody');
  const advisoriesTbody = document.getElementById('advisories-table-tbody');

  if (schemesTbody) {
    try {
      const res = await fetch('/api/admin/health-schemes/');
      const data = await res.json();
      if (data.status === 'success') {
        schemesTbody.innerHTML = data.schemes.map(s => `
          <tr style="border-bottom:1px solid #f1f5f9;">
            <td style="padding:10px 12px; font-weight:700; color:var(--primary-navy);">${s.name}</td>
            <td style="padding:10px 12px;">${s.nodal_agency}</td>
            <td style="padding:10px 12px; font-size:0.82rem; color:#475569;">${s.eligibility_criteria}</td>
            <td style="padding:10px 12px;"><span style="font-size:0.75rem; padding:2px 8px; border-radius:12px; font-weight:700; ${s.is_active ? 'background:#dcfce7; color:#15803d;' : 'background:#fee2e2; color:#b91c1c;'}">${s.is_active ? 'ACTIVE' : 'INACTIVE'}</span></td>
            <td style="padding:10px 12px; text-align:right;">
              <button class="btn btn-sm btn-outline" onclick="toggleSchemeActive(${s.id})" style="font-size:0.75rem; padding:3px 8px;">Toggle Status</button>
            </td>
          </tr>
        `).join('');
      }
    } catch (e) { console.error(e); }
  }

  if (advisoriesTbody) {
    try {
      const res = await fetch('/api/admin/health-advisories/');
      const data = await res.json();
      if (data.status === 'success') {
        advisoriesTbody.innerHTML = data.advisories.map(a => `
          <tr style="border-bottom:1px solid #f1f5f9;">
            <td style="padding:10px 12px; font-weight:700; color:var(--primary-navy);">${a.title}</td>
            <td style="padding:10px 12px;"><span style="font-size:0.75rem; padding:2px 8px; border-radius:12px; font-weight:700; background:#fef3c7; color:#b45309;">${a.severity}</span></td>
            <td style="padding:10px 12px; font-size:0.82rem; color:#475569;">${a.message}</td>
            <td style="padding:10px 12px; font-size:0.82rem; color:#15803d;">${a.action_advice || '-'}</td>
            <td style="padding:10px 12px;"><span style="font-size:0.75rem; padding:2px 8px; border-radius:12px; font-weight:700; ${a.is_active ? 'background:#dcfce7; color:#15803d;' : 'background:#fee2e2; color:#b91c1c;'}">${a.is_active ? 'ACTIVE' : 'INACTIVE'}</span></td>
            <td style="padding:10px 12px; text-align:right;">
              <button class="btn btn-sm btn-outline" onclick="toggleAdvisoryActive(${a.id})" style="font-size:0.75rem; padding:3px 8px;">Toggle Status</button>
            </td>
          </tr>
        `).join('');
      }
    } catch (e) { console.error(e); }
  }
}

async function toggleSchemeActive(id) {
  await fetch(`/api/admin/health-schemes/${id}/toggle/`, { method: 'POST' });
  loadSchemesAndAdvisories();
}

async function toggleAdvisoryActive(id) {
  await fetch(`/api/admin/health-advisories/${id}/toggle/`, { method: 'POST' });
  loadSchemesAndAdvisories();
}

async function submitAdminAddScheme() {
  const payload = {
    name: document.getElementById('scheme-name')?.value,
    code: document.getElementById('scheme-code')?.value,
    nodal_agency: document.getElementById('scheme-agency')?.value,
    description: document.getElementById('scheme-desc')?.value,
    eligibility_criteria: document.getElementById('scheme-eligibility')?.value,
    benefits: document.getElementById('scheme-benefits')?.value,
    portal_url: document.getElementById('scheme-url')?.value
  };

  const res = await fetch('/api/admin/health-schemes/add/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  if (data.status === 'success') {
    alert('✓ Health scheme published successfully.');
    document.getElementById('modal-add-scheme')?.classList.remove('open');
    document.getElementById('form-add-scheme')?.reset();
    loadSchemesAndAdvisories();
  } else {
    alert(data.message || 'Error adding scheme');
  }
}

async function submitAdminAddAdvisory() {
  const payload = {
    title: document.getElementById('adv-title')?.value,
    severity: document.getElementById('adv-severity')?.value,
    target_state: document.getElementById('adv-state')?.value,
    message: document.getElementById('adv-message')?.value,
    action_advice: document.getElementById('adv-advice')?.value
  };

  const res = await fetch('/api/admin/health-advisories/add/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  if (data.status === 'success') {
    alert('✓ Public health advisory broadcasted successfully.');
    document.getElementById('modal-add-advisory')?.classList.remove('open');
    document.getElementById('form-add-advisory')?.reset();
    loadSchemesAndAdvisories();
  } else {
    alert(data.message || 'Error broadcasting advisory');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const auditSearch = document.getElementById('audit-search');
  const auditRole = document.getElementById('audit-role-filter');
  const auditAction = document.getElementById('audit-action-filter');
  if (auditSearch) auditSearch.addEventListener('input', loadAuditLogs);
  if (auditRole) auditRole.addEventListener('change', loadAuditLogs);
  if (auditAction) auditAction.addEventListener('change', loadAuditLogs);

  loadAuditLogs();
  loadSchemesAndAdvisories();
});
