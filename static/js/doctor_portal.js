/**
 * Hospital Government of India - Doctor Portal Engine
 * Categorized Queues: Today's Completed, Uncompleted, Previous, All + Live Completion
 * + Medical Learning Library, Interactive Case Studies & Clinical Calculators
 */

document.addEventListener('DOMContentLoaded', () => {
  initDoctorTabs();
  initDoctorDutyToggle();
  initConsultationModal();
  initAppointmentHistorySearch();
  initMedicalLibrary();
  initClinicalCalculators();
  initDoctorTelemetryChart();
  initDoctorHistoryChart();
});

// Multi-Filter Engine for Doctor Appointment History
function initAppointmentHistorySearch() {
  const searchInput = document.getElementById('doc-history-search');
  const dateInput = document.getElementById('doc-history-date-filter');
  const slotSelect = document.getElementById('doc-history-slot-filter');
  const statusSelect = document.getElementById('doc-history-status-filter');
  const resetBtn = document.getElementById('btn-reset-history-filters');
  const table = document.getElementById('doc-history-table');

  if (!table) return;

  function filterTable() {
    const q = searchInput ? searchInput.value.toLowerCase().trim() : '';
    const dateVal = dateInput ? dateInput.value : '';
    const slotVal = slotSelect ? slotSelect.value : 'all';
    const statusVal = statusSelect ? statusSelect.value : 'all';

    const rows = table.querySelectorAll('tbody tr');
    rows.forEach(row => {
      const text = row.innerText.toLowerCase();
      const rowDate = row.getAttribute('data-date') || '';
      const rowSlot = row.getAttribute('data-slot') || '';
      const rowStatus = row.getAttribute('data-status') || '';

      const matchQ = !q || text.includes(q);
      const matchDate = !dateVal || rowDate === dateVal;
      const matchSlot = slotVal === 'all' || rowSlot.toLowerCase().includes(slotVal.toLowerCase());
      const matchStatus = statusVal === 'all' || rowStatus.toUpperCase() === statusVal.toUpperCase();

      if (matchQ && matchDate && matchSlot && matchStatus) {
        row.style.display = '';
      } else {
        row.style.display = 'none';
      }
    });
  }

  if (searchInput) searchInput.addEventListener('input', filterTable);
  if (dateInput) dateInput.addEventListener('change', filterTable);
  if (slotSelect) slotSelect.addEventListener('change', filterTable);
  if (statusSelect) statusSelect.addEventListener('change', filterTable);

  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      if (searchInput) searchInput.value = '';
      if (dateInput) dateInput.value = '';
      if (slotSelect) slotSelect.value = 'all';
      if (statusSelect) statusSelect.value = 'all';
      filterTable();
    });
  }
}

// 0.2 Doctor Appointment Progress Graph (Today, Yesterday, Weekly, Monthly, Year)
let docHistChart = null;
function initDoctorHistoryChart() {
  const canvas = document.getElementById('doc-history-telemetry-chart');
  if (!canvas || !window.Chart) return;

  const rawData = window.DOC_TIME_SERIES_DATA || {};
  let currentTF = 'weekly';

  function renderHistChart(tf) {
    let labels = [];
    let completedData = [];
    let totalData = [];

    if (tf === 'today') {
      labels = ['09:00 AM', '10:00 AM', '11:00 AM', '12:00 PM', '02:00 PM', '03:00 PM', '04:00 PM'];
      completedData = [2, 3, 4, 3, 5, 2, 1];
      totalData = [3, 4, 5, 4, 6, 3, 2];
    } else if (tf === 'yesterday') {
      labels = ['09:00 AM', '10:00 AM', '11:00 AM', '12:00 PM', '02:00 PM', '03:00 PM', '04:00 PM'];
      completedData = [4, 4, 6, 5, 4, 3, 2];
      totalData = [4, 5, 6, 5, 4, 4, 2];
    } else if (tf === 'weekly') {
      labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
      completedData = [18, 22, 19, 25, 21, 14, 8];
      totalData = [20, 25, 22, 28, 24, 16, 10];
    } else if (tf === 'monthly') {
      const mData = rawData['month'] || {};
      labels = mData.labels || ['Week 1', 'Week 2', 'Week 3', 'Week 4'];
      completedData = mData.completed || [85, 92, 78, 96];
      totalData = mData.total || [95, 105, 88, 110];
    } else if (tf === 'year') {
      const yData = rawData['year'] || {};
      labels = yData.labels || ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      completedData = yData.completed || [210, 245, 290, 310, 340, 380, 410, 430, 460, 480, 510, 530];
      totalData = yData.total || [230, 270, 310, 335, 370, 410, 440, 465, 495, 520, 550, 580];
    }

    if (docHistChart) {
      docHistChart.destroy();
    }

    docHistChart = new Chart(canvas.getContext('2d'), {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Completed Consultations',
            data: completedData,
            backgroundColor: '#00a86b',
            borderRadius: 6
          },
          {
            label: 'Total OPD Appointments',
            data: totalData,
            backgroundColor: '#004d40',
            borderRadius: 6
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', labels: { font: { family: 'Inter', size: 11, weight: '700' } } }
        },
        scales: {
          y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
          x: { grid: { display: false } }
        }
      }
    });
  }

  renderHistChart(currentTF);

  const tfBtns = document.querySelectorAll('#doc-history-timeframe-btns .btn-doc-hist-tf');
  tfBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tfBtns.forEach(b => {
        b.classList.remove('active');
        b.style.background = '#ffffff';
        b.style.color = '#004d40';
      });
      btn.classList.add('active');
      btn.style.background = '#004d40';
      btn.style.color = '#ffffff';

      const tf = btn.getAttribute('data-tf');
      renderHistChart(tf);
    });
  });
}

// 1. Doctor Tab Navigation (Today / Previous / All / Analytics / Library)
function initDoctorTabs() {
  const tabBtns = document.querySelectorAll('.btn-doc-tab');

  function switchDocTab(target) {
    if (!target) return;

    tabBtns.forEach(b => {
      if (b.getAttribute('data-tab') === target) {
        b.classList.add('active');
        b.style.background = '#004d40';
        b.style.color = '#ffffff';
      } else {
        b.classList.remove('active');
        b.style.background = '#ffffff';
        b.style.color = 'inherit';
      }
    });

    document.querySelectorAll('.doc-tab-pane').forEach(pane => {
      pane.style.display = 'none';
      pane.classList.remove('active');
    });

    const activePane = document.getElementById(`pane-${target}`);
    if (activePane) {
      activePane.style.display = 'block';
      activePane.classList.add('active');
      window.location.hash = target;
    }

    // Trigger Chart Resize when switching to analytics tab
    setTimeout(() => {
      if (target === 'analytics' && window.docChart) {
        window.docChart.resize();
      }
    }, 50);
  }

  tabBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const target = btn.getAttribute('data-tab');
      switchDocTab(target);
    });
  });

  // Handle URL hash on load (e.g. #previous, #analytics, #library)
  const hash = window.location.hash.replace('#', '');
  if (hash && document.getElementById(`pane-${hash}`)) {
    switchDocTab(hash);
  }
}

// 1.1 Doctor Patient Load & Telemetry Dynamic Chart (Year / Month / Week / Day)
let docChart = null;
function initDoctorTelemetryChart() {
  const canvas = document.getElementById('doc-telemetry-chart');
  if (!canvas || !window.Chart) return;

  const rawData = window.DOC_TIME_SERIES_DATA || {};
  let currentPeriod = 'month';

  function renderChart(period) {
    const periodData = rawData[period] || rawData['month'];
    if (!periodData) return;

    if (docChart) {
      docChart.destroy();
    }

    docChart = new Chart(canvas.getContext('2d'), {
      type: 'line',
      data: {
        labels: periodData.labels,
        datasets: [
          {
            label: 'Total OPD Appointments',
            data: periodData.total,
            borderColor: '#004d40',
            backgroundColor: 'rgba(0, 77, 64, 0.08)',
            borderWidth: 3,
            fill: true,
            tension: 0.35,
            pointBackgroundColor: '#004d40',
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
            label: 'Pre-Appointments / Waiting Queue',
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

    window.docChart = docChart;
  }

  renderChart(currentPeriod);

  const timeframeBtns = document.querySelectorAll('#doc-chart-timeframe-btns .btn-doc-timeframe');
  timeframeBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      timeframeBtns.forEach(b => {
        b.classList.remove('active');
        b.style.background = '#ffffff';
        b.style.color = '#004d40';
      });

      btn.classList.add('active');
      btn.style.background = '#004d40';
      btn.style.color = '#ffffff';

      const period = btn.getAttribute('data-period');
      renderChart(period);
    });
  });
}

// 2. Doctor Duty Presence Toggle
function initDoctorDutyToggle() {
  const dutyBtn = document.getElementById('btn-doctor-duty-toggle');
  if (!dutyBtn) return;

  dutyBtn.addEventListener('click', () => {
    const docId = dutyBtn.getAttribute('data-id');
    dutyBtn.disabled = true;
    dutyBtn.textContent = 'Updating...';

    fetch(`/api/doctor/duty/toggle/${docId}/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
    .then(res => res.json())
    .then(data => {
      dutyBtn.disabled = false;
      if (data.success) {
        if (data.is_present_today) {
          dutyBtn.innerHTML = '🟢 Present on Duty (OPD Open)';
          dutyBtn.style.background = '#dcfce7';
          dutyBtn.style.color = '#15803d';
        } else {
          dutyBtn.innerHTML = '🔴 Off Duty / On Leave';
          dutyBtn.style.background = '#fee2e2';
          dutyBtn.style.color = '#b91c1c';
        }
        alert(data.message);
      }
    })
    .catch(err => {
      dutyBtn.disabled = false;
      alert('Error toggling duty presence.');
    });
  });
}

// 3. Attend Patient & Complete Consultation Modal
function initConsultationModal() {
  const modal = document.getElementById('modal-attend-consultation');
  const form = document.getElementById('form-attend-consultation');
  const bookingIdInput = document.getElementById('attend-booking-id');
  const patientNameEl = document.getElementById('attend-patient-name');
  const symptomsEl = document.getElementById('attend-symptoms-text');
  const tokenBadge = document.getElementById('attend-token-badge');
  const submitBtn = document.getElementById('btn-submit-consultation');

  if (!modal || !form) return;

  // Open modal on click
  document.querySelectorAll('.btn-attend-patient').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-id');
      const name = btn.getAttribute('data-name');
      const token = btn.getAttribute('data-token');
      const sym = btn.getAttribute('data-sym');

      bookingIdInput.value = id;
      patientNameEl.textContent = name;
      symptomsEl.textContent = `Symptoms: ${sym}`;
      tokenBadge.textContent = `Token #${token}`;

      modal.classList.add('open');
    });
  });

  // Submit consultation completion
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const bookingId = bookingIdInput.value;
    const notes = document.getElementById('attend-notes').value.trim();
    const medName = document.getElementById('attend-med-name').value.trim();
    const dosage = document.getElementById('attend-med-dosage').value.trim();

    if (!bookingId || !notes) {
      alert('Please fill the clinical observations notes.');
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = 'Saving Consultation...';

    fetch(`/api/doctor/appointments/${bookingId}/complete/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        consultation_notes: notes,
        medicine_name: medName,
        dosage: dosage
      })
    })
    .then(res => res.json())
    .then(data => {
      submitBtn.disabled = false;
      submitBtn.textContent = '✓ Complete Consultation & Update OPD Queue';

      if (data.success) {
        modal.classList.remove('open');
        alert(data.message);

        // Remove card from uncompleted queue
        const card = document.getElementById(`apt-card-${bookingId}`);
        if (card) card.remove();

        // Update KPI counters
        const kpiPending = document.getElementById('kpi-today-pending');
        const kpiCompleted = document.getElementById('kpi-today-completed');
        const badgeCount = document.getElementById('badge-completed-today-count');

        if (kpiPending && parseInt(kpiPending.textContent) > 0) {
          kpiPending.textContent = parseInt(kpiPending.textContent) - 1;
        }
        if (kpiCompleted) {
          kpiCompleted.textContent = parseInt(kpiCompleted.textContent) + 1;
        }
        if (badgeCount) {
          badgeCount.textContent = `${data.patients_taken_today} Completed Today`;
        }

        // Add row to completed table
        const tbody = document.getElementById('tbody-completed-today');
        const emptyRow = document.getElementById('row-empty-completed');
        if (emptyRow) emptyRow.remove();

        if (tbody) {
          const row = document.createElement('tr');
          row.style.borderBottom = '1px solid #f1f5f9';
          row.innerHTML = `
            <td style="padding:12px 10px; font-weight:800; color:#15803d;">${tokenBadge.textContent}</td>
            <td style="padding:12px 10px; font-weight:700; color:var(--primary-navy);">${patientNameEl.textContent}</td>
            <td style="padding:12px 10px; font-size:0.82rem;">Today</td>
            <td style="padding:12px 10px; font-size:0.82rem; color:var(--text-muted);">${symptomsEl.textContent}</td>
            <td style="padding:12px 10px; font-size:0.85rem; color:#1e293b;">${notes}</td>
            <td style="padding:12px 10px; text-align:center; font-size:0.82rem; font-weight:600; color:var(--accent-emerald);">${data.completed_at || 'Just now'}</td>
          `;
          tbody.prepend(row);
        }
      } else {
        alert('Error: ' + data.message);
      }
    })
    .catch(err => {
      submitBtn.disabled = false;
      submitBtn.textContent = '✓ Complete Consultation & Update OPD Queue';
      alert('Network error completing consultation.');
    });
  });
}

// 4. Medical Learning Library Engine (Search, Category Filters & Case Studies)
const CLINICAL_CASE_DATABASE = {
  'cardio-stemi': {
    title: '❤️ Acute Inferior Wall STEMI with Bradycardia',
    specialty: 'Cardiology / Emergency Care',
    patient_info: '56-year-old male presenting with 2 hours of crushing substernal chest pressure, diaphoresis, and nausea radiating to the jaw.',
    vitals: 'BP: 94/62 mmHg, HR: 48 BPM (Sinus Bradycardia), SpO2: 95% on room air, RR: 20/min.',
    ecg_findings: 'ST-segment elevation > 2mm in leads II, III, aVF with reciprocal ST depressions in leads I, aVL. Lead V4R shows 1mm ST elevation indicating Right Ventricular involvement.',
    question: 'Which of the following is the most critical immediate pharmacological contraindication?',
    options: [
      'A) Aspirin 300 mg chewable',
      'B) Sublingual Nitroglycerin (NTG)',
      'C) Clopidogrel 300 mg loading dose',
      'D) Unfractionated Heparin bolus'
    ],
    correct_answer: 'B) Sublingual Nitroglycerin (NTG)',
    explanation: 'In Right Ventricular (RV) infarction, cardiac output is preload-dependent. Vasodilators such as nitrates and morphine venodilate and decrease preload, causing catastrophic hemodynamic collapse and profound hypotension. Atropine 0.5-1mg IV is indicated for symptomatic bradycardia.'
  },
  'pulm-copd': {
    title: '🫁 Acute Exacerbation of Severe COPD with Type II Failure',
    specialty: 'Pulmonology / Critical Care',
    patient_info: '68-year-old male with 30 pack-year smoking history presenting with acute onset severe dyspnea, purulent sputum, and asterixis (flapping tremor).',
    vitals: 'BP: 145/88 mmHg, HR: 112 BPM, SpO2: 84% on room air, RR: 28/min.',
    abg_findings: 'pH: 7.28, PaCO2: 64 mmHg, PaO2: 52 mmHg, HCO3: 31 mEq/L (Acute-on-Chronic Respiratory Acidosis).',
    question: 'What is the immediate oxygen therapy target and primary ventilatory modality?',
    options: [
      'A) High-flow 100% O2 Non-Rebreather to achieve SpO2 99-100%',
      'B) Titrated Venturi mask targeting SpO2 88-92% + Non-Invasive Positive Pressure Ventilation (BiPAP)',
      'C) Immediate endotracheal intubation without trial of NIV',
      'D) Room air only to stimulate respiratory drive'
    ],
    correct_answer: 'B) Titrated Venturi mask targeting SpO2 88-92% + Non-Invasive Positive Pressure Ventilation (BiPAP)',
    explanation: 'Uncontrolled high oxygen causes loss of hypoxic vasoconstriction (V/Q mismatch), absorption atelectasis, and worsening hypercapnia (Haldane effect). BiPAP reduces work of breathing and intubation rates in COPD exacerbations with pH < 7.35 and PaCO2 > 45 mmHg.'
  },
  'endo-diabetes': {
    title: '🩸 T2D with Albuminuria and ASCVD Risk Optimization',
    specialty: 'Endocrinology / Preventive Cardiology',
    patient_info: '61-year-old female with 8-year history of Type 2 Diabetes, hypertension, and BMI of 31 kg/m². Current regimen: Metformin 1000mg BID + Glimepiride 2mg OD.',
    vitals: 'BP: 138/84 mmHg, HR: 74 BPM, Fasting Glucose: 168 mg/dL, HbA1c: 8.6%.',
    lab_findings: 'eGFR: 64 mL/min/1.73m², Urine Albumin-to-Creatinine Ratio (uACR): 180 mg/g (Microalbuminuria).',
    question: 'According to ADA/RSSDI guidelines, which class of antidiabetic agent provides guideline-directed organ protection?',
    options: [
      'A) Increase Glimepiride to 4mg daily',
      'B) Add an SGLT2 Inhibitor (Empagliflozin 10mg or Dapagliflozin 10mg)',
      'C) Start Premix Insulin 30/70 immediately',
      'D) Switch Metformin to Acarbose'
    ],
    correct_answer: 'B) Add an SGLT2 Inhibitor (Empagliflozin 10mg or Dapagliflozin 10mg)',
    explanation: 'SGLT2 inhibitors and GLP-1 receptor agonists have class 1A evidence for slowing CKD progression, reducing albuminuria, and preventing Heart Failure hospitalizations, independent of baseline HbA1c.'
  },
  'nephro-aki': {
    title: '🫘 NSAID-Induced Acute Kidney Injury with Hyperkalemia',
    specialty: 'Nephrology / Internal Medicine',
    patient_info: '72-year-old male with osteoarthritis who self-administered Diclofenac 75mg TID for 10 days for severe knee pain. Presents with oliguria, fatigue, and muscle weakness.',
    vitals: 'BP: 160/95 mmHg, HR: 54 BPM, Serum Creatinine: 3.8 mg/dL (Baseline was 0.9 mg/dL), Serum Potassium: 6.8 mEq/L.',
    ecg_findings: 'Tall peaked symmetric T waves in leads V2-V5, PR interval prolongation, and widening of QRS complex.',
    question: 'What is the immediate first-line intravenous intervention to prevent fatal ventricular arrhythmia?',
    options: [
      'A) Intravenous Furosemide 80mg bolus',
      'B) 10 mL of 10% Calcium Gluconate IV over 2-3 minutes under ECG monitoring',
      'C) Oral Sodium Polystyrene Sulfonate (Kayexalate)',
      'D) 500 mL Normal Saline bolus'
    ],
    correct_answer: 'B) 10 mL of 10% Calcium Gluconate IV over 2-3 minutes under ECG monitoring',
    explanation: 'Calcium Gluconate directly stabilizes cardiac membrane potential and antagonizes the arrhythmogenic effects of hyperkalemia within 1-3 minutes. It buys time for insulin-dextrose and beta-2 agonists to drive potassium intracellularly.'
  },
  'peds-fever': {
    title: '👶 Pediatric Acute Gastroenteritis with Some Dehydration',
    specialty: 'Pediatrics / Child Health',
    patient_info: '2-year-old child (weight 12 kg) brought with 2-day history of watery diarrhea (6-7 episodes/day) and low-grade fever. Child is irritable, thirsty, with sunken eyes and skin pinch returning slowly (< 2 seconds).',
    vitals: 'HR: 130 BPM, RR: 28/min, Capillary Refill Time: 2 seconds, Temp: 38.2°C.',
    question: 'According to WHO Plan B, what is the correct oral rehydration volume over the first 4 hours?',
    options: [
      'A) 200 mL of sweetened fruit juice',
      'B) 900 mL (75 mL/kg × 12 kg) of WHO Low-Osmolarity ORS solution over 4 hours',
      'C) Immediate IV Dextrose 5% at 100 mL/hr',
      'D) Nil orally for 6 hours to rest the gut'
    ],
    correct_answer: 'B) 900 mL (75 mL/kg × 12 kg) of WHO Low-Osmolarity ORS solution over 4 hours',
    explanation: 'WHO Plan B guidelines recommend 75 mL/kg of low-osmolarity ORS administered slowly with a spoon over 4 hours. Oral Zinc supplementation (20 mg/day for 14 days) should also be initiated to reduce diarrhea duration and recurrence.'
  },
  'emer-anaphylaxis': {
    title: '🚨 Severe Anaphylactic Shock Following IV Ceftriaxone',
    specialty: 'Emergency Medicine / Allergology',
    patient_info: '34-year-old female received IV Ceftriaxone in day-care. Within 3 minutes, developed generalized urticaria, facial angioedema, stridor, and wheezing.',
    vitals: 'BP: 72/40 mmHg (Severe Hypotension), HR: 138 BPM (Sinus Tachycardia), SpO2: 88% on room air.',
    question: 'What is the immediate life-saving first step in management?',
    options: [
      'A) IV Hydrocortisone 200 mg slowly over 10 minutes',
      'B) Intramuscular Adrenaline (Epinephrine) 1:1000, 0.5 mg in the anterolateral mid-thigh',
      'C) IV Chlorpheniramine 10 mg',
      'D) Subcutaneous Adrenaline in the deltoid muscle'
    ],
    correct_answer: 'B) Intramuscular Adrenaline (Epinephrine) 1:1000, 0.5 mg in the anterolateral mid-thigh',
    explanation: 'Intramuscular adrenaline in the mid-thigh (vastus lateralis) provides the most rapid and reliable peak plasma concentration. Antihistamines and steroids are second-line adjuncts and must NEVER delay adrenaline administration.'
  },
  'pharm-interactions': {
    title: '💊 Severe Statin-Macrolide Rhabdomyolysis Interaction',
    specialty: 'Clinical Pharmacology',
    patient_info: '64-year-old male taking Atorvastatin 40mg daily prescribed Clarithromycin 500mg BID for community-acquired pneumonia. Returns on Day 5 with severe muscle pain, dark tea-colored urine, and extreme weakness.',
    vitals: 'BP: 130/80 mmHg, HR: 88 BPM, Serum Creatine Kinase (CK): 28,500 U/L (Normal < 200 U/L), Serum Creatinine: 2.4 mg/dL.',
    question: 'What is the pharmacological mechanism of this adverse drug-drug interaction?',
    options: [
      'A) Clarithromycin induces CYP3A4, decreasing statin clearance',
      'B) Clarithromycin is a potent CYP3A4 inhibitor, causing a 5 to 10-fold increase in Atorvastatin serum concentrations',
      'C) Direct allergic tubular nephritis from Macrolide',
      'D) Competitive binding at renal organic anion transporters (OAT)'
    ],
    correct_answer: 'B) Clarithromycin is a potent CYP3A4 inhibitor, causing a 5 to 10-fold increase in Atorvastatin serum concentrations',
    explanation: 'Atorvastatin, Simvastatin, and Lovastatin are extensively metabolized by hepatic CYP3A4. Strong inhibitors like Clarithromycin, Ketoconazole, and Protease inhibitors dramatically increase statin levels, triggering life-threatening rhabdomyolysis and myoglobinuric renal failure.'
  }
};

function initMedicalLibrary() {
  const searchInput = document.getElementById('library-search-input');
  const filterBtns = document.querySelectorAll('.btn-lib-filter');
  const cards = document.querySelectorAll('.library-card');
  const caseModal = document.getElementById('modal-case-study');
  const caseTitle = document.getElementById('case-study-title');
  const caseBody = document.getElementById('case-study-body');

  function filterLibrary() {
    const query = searchInput ? searchInput.value.toLowerCase().trim() : '';
    const activeBtn = document.querySelector('.btn-lib-filter.active');
    const selectedCat = activeBtn ? activeBtn.getAttribute('data-cat') : 'all';

    cards.forEach(card => {
      const cardCat = card.getAttribute('data-cat');
      const keywords = (card.getAttribute('data-keywords') || '') + ' ' + card.innerText.toLowerCase();

      const matchCat = selectedCat === 'all' || cardCat === selectedCat;
      const matchQuery = !query || keywords.includes(query);

      if (matchCat && matchQuery) {
        card.style.display = 'flex';
      } else {
        card.style.display = 'none';
      }
    });
  }

  if (searchInput) searchInput.addEventListener('input', filterLibrary);

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => {
        b.classList.remove('active');
        b.style.background = '#f1f5f9';
        b.style.color = '#334155';
      });
      btn.classList.add('active');
      btn.style.background = '#065f46';
      btn.style.color = '#ffffff';
      filterLibrary();
    });
  });

  // Open Case Study Modal
  document.querySelectorAll('.btn-open-case').forEach(btn => {
    btn.addEventListener('click', () => {
      const caseKey = btn.getAttribute('data-case');
      const caseData = CLINICAL_CASE_DATABASE[caseKey];

      if (!caseData || !caseModal || !caseBody) return;

      caseTitle.innerHTML = `<span>📖</span> ${caseData.title}`;
      caseBody.innerHTML = `
        <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px; padding:12px 16px; margin-bottom:16px;">
          <div style="font-size:0.8rem; font-weight:700; color:#166534; text-transform:uppercase;">Specialty Focus</div>
          <div style="font-size:1rem; font-weight:800; color:#064e3b;">${caseData.specialty}</div>
        </div>

        <div style="margin-bottom:14px;">
          <h4 style="font-size:0.95rem; color:var(--primary-navy); margin-bottom:4px;">1. Patient Clinical History & Presentation:</h4>
          <p style="font-size:0.9rem; color:#334155; line-height:1.5;">${caseData.patient_info}</p>
        </div>

        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:12px; margin-bottom:14px;">
          <h4 style="font-size:0.9rem; color:var(--primary-navy); margin-bottom:4px;">2. Clinical Examination & Vitals:</h4>
          <p style="font-size:0.88rem; color:#1e293b; margin:0; font-family:monospace;">${caseData.vitals}</p>
          ${caseData.ecg_findings ? `<p style="font-size:0.85rem; color:#b91c1c; margin-top:6px;"><strong>ECG / Diagnostic Clue:</strong> ${caseData.ecg_findings}</p>` : ''}
          ${caseData.abg_findings ? `<p style="font-size:0.85rem; color:#0369a1; margin-top:6px;"><strong>ABG Gas Analysis:</strong> ${caseData.abg_findings}</p>` : ''}
          ${caseData.lab_findings ? `<p style="font-size:0.85rem; color:#4338ca; margin-top:6px;"><strong>Laboratory Profile:</strong> ${caseData.lab_findings}</p>` : ''}
        </div>

        <div style="border-top:2px dashed #e2e8f0; padding-top:14px; margin-top:14px;">
          <h4 style="font-size:0.98rem; color:#b45309; margin-bottom:10px;">❓ Clinical Decision Question:</h4>
          <p style="font-size:0.92rem; font-weight:700; color:var(--primary-navy);">${caseData.question}</p>
          
          <div style="margin:12px 0;">
            ${caseData.options.map(opt => `
              <div style="padding:8px 12px; background:#ffffff; border:1px solid #cbd5e1; border-radius:6px; margin-bottom:6px; font-size:0.88rem; color:#334155;">
                ${opt}
              </div>
            `).join('')}
          </div>

          <button type="button" class="btn btn-emerald" id="btn-reveal-answer" style="width:100%; padding:10px; font-weight:700; font-size:0.9rem; margin-top:8px;">
            💡 Reveal Expert Consensus & Clinical Pearl
          </button>

          <div id="case-answer-box" style="display:none; margin-top:14px; padding:14px; background:#ecfdf5; border:1.5px solid #34d399; border-radius:8px;">
            <div style="font-size:0.85rem; font-weight:800; color:#065f46; margin-bottom:4px;">CORRECT CLINICAL APPROACH:</div>
            <div style="font-size:1.05rem; font-weight:800; color:#047857; margin-bottom:8px;">${caseData.correct_answer}</div>
            <div style="font-size:0.85rem; color:#1e293b; line-height:1.5;">${caseData.explanation}</div>
          </div>
        </div>
      `;

      const revealBtn = document.getElementById('btn-reveal-answer');
      const answerBox = document.getElementById('case-answer-box');
      if (revealBtn && answerBox) {
        revealBtn.addEventListener('click', () => {
          answerBox.style.display = 'block';
          revealBtn.style.display = 'none';
        });
      }

      caseModal.classList.add('open');
    });
  });
}

// 5. Rapid Clinical Diagnostic Calculators
function initClinicalCalculators() {
  // Calculator 1: eGFR (CKD-EPI)
  const btnEgfr = document.getElementById('btn-calc-egfr');
  if (btnEgfr) {
    btnEgfr.addEventListener('click', () => {
      const scr = parseFloat(document.getElementById('calc-creat').value) || 1.0;
      const age = parseInt(document.getElementById('calc-age').value) || 50;
      const gender = document.getElementById('calc-gender').value;
      const resEl = document.getElementById('result-egfr');

      let k = gender === 'female' ? 0.7 : 0.9;
      let alpha = gender === 'female' ? -0.241 : -0.302;
      let genderMultiplier = gender === 'female' ? 1.012 : 1.0;

      let minScr = Math.min(scr / k, 1);
      let maxScr = Math.max(scr / k, 1);

      let egfr = 142 * Math.pow(minScr, alpha) * Math.pow(maxScr, -1.200) * Math.pow(0.9938, age) * genderMultiplier;
      egfr = Math.round(egfr * 10) / 10;

      let stage = 'G1 (Normal / High ≥ 90)';
      if (egfr < 15) stage = 'G5 (Kidney Failure < 15)';
      else if (egfr <= 29) stage = 'G4 (Severely Decreased 15-29)';
      else if (egfr <= 44) stage = 'G3b (Moderately to Severely Decreased 30-44)';
      else if (egfr <= 59) stage = 'G3a (Mildly to Moderately Decreased 45-59)';
      else if (egfr <= 89) stage = 'G2 (Mildly Decreased 60-89)';

      resEl.innerHTML = `eGFR: <strong>${egfr} mL/min/1.73m²</strong> (${stage})`;
    });
  }

  // Calculator 2: MAP
  const btnMap = document.getElementById('btn-calc-map');
  if (btnMap) {
    btnMap.addEventListener('click', () => {
      const sys = parseFloat(document.getElementById('calc-sys').value) || 120;
      const dia = parseFloat(document.getElementById('calc-dia').value) || 80;
      const resEl = document.getElementById('result-map');

      let map = (2 * dia + sys) / 3;
      map = Math.round(map * 10) / 10;

      let status = map >= 65 ? 'Normal Adequate Perfusion' : 'Critical Hypoperfusion Alert (MAP < 65)';
      let color = map >= 65 ? '#15803d' : '#dc2626';

      resEl.style.color = color;
      resEl.innerHTML = `MAP: <strong>${map} mmHg</strong> (${status})`;
    });
  }

  // Calculator 3: Pediatric Amoxicillin Dosing
  const btnPeds = document.getElementById('btn-calc-peds');
  if (btnPeds) {
    btnPeds.addEventListener('click', () => {
      const wt = parseFloat(document.getElementById('calc-peds-weight').value) || 10;
      const regimen = parseFloat(document.getElementById('calc-peds-regimen').value) || 45;
      const resEl = document.getElementById('result-peds');

      let totalMgPerDay = wt * regimen;
      let bidMg = Math.round(totalMgPerDay / 2);
      // Syrup: 250mg per 5mL -> 50mg/mL
      let mLPerDose = Math.round((bidMg / 50) * 10) / 10;

      resEl.innerHTML = `Dose: <strong>${mLPerDose} mL (${bidMg} mg) Twice Daily (BID)</strong>`;
    });
  }
}

// ==================== NEW OPD ACTIONS & CLINICAL WORKFLOWS ====================

function openDocModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add('open');
}

// OPD Action matrix listeners (call_next, start_consultation, mark_no_show)
document.addEventListener('click', async (e) => {
  const btn = e.target.closest('.btn-opd-action');
  if (btn) {
    e.preventDefault();
    const bookingId = btn.getAttribute('data-id');
    const action = btn.getAttribute('data-action');
    await handleDoctorOpdAction(bookingId, action, btn);
  }
});

async function handleDoctorOpdAction(bookingId, action, btnEl) {
  try {
    const res = await fetch('/core/api/doctor/opd-action/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ booking_id: bookingId, action: action })
    });
    const data = await res.json();
    if (data.status === 'success') {
      const badge = document.getElementById(`apt-status-badge-${bookingId}`);
      if (badge) {
        badge.innerText = data.new_status;
        if (data.new_status === 'IN_CONSULTATION') {
          badge.className = 'vital-status-pill success';
        } else if (data.new_status === 'WAITING' || data.new_status === 'CHECKED_IN') {
          badge.className = 'vital-status-pill warning';
        }
      }
      if (action === 'mark_no_show') {
        const card = document.getElementById(`apt-card-${bookingId}`);
        if (card) card.style.opacity = '0.4';
      }
      alert(`✓ Patient OPD queue updated: ${data.new_status}`);
    } else {
      alert(data.message || 'Error updating OPD queue');
    }
  } catch (err) {
    console.error('OPD action error:', err);
    alert('Server error executing OPD action');
  }
}

// Submit Doctor Lab Order
async function submitDoctorLabOrder() {
  const patientQuery = document.getElementById('lab-patient-query')?.value;
  const labTestId = document.getElementById('lab-test-id')?.value;
  const instructions = document.getElementById('lab-instructions')?.value;

  try {
    const res = await fetch('/core/api/doctor/order-lab-test/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_query: patientQuery,
        lab_test_id: labTestId,
        special_instructions: instructions
      })
    });
    const data = await res.json();
    if (data.status === 'success') {
      alert(`✓ Diagnostic lab order placed successfully! Order Ref: ${data.order_id}`);
      document.getElementById('modal-order-lab')?.classList.remove('open');
      document.getElementById('form-order-lab')?.reset();
    } else {
      alert(data.message || 'Error placing lab order');
    }
  } catch (err) {
    console.error('Lab order error:', err);
    alert('Failed to submit lab order');
  }
}

// Submit Digital Discharge Summary
async function submitDoctorDischarge() {
  const payload = {
    patient_query: document.getElementById('dis-patient-query')?.value,
    department: document.getElementById('dis-department')?.value,
    admission_date: document.getElementById('dis-admission-date')?.value,
    discharge_date: document.getElementById('dis-discharge-date')?.value,
    final_diagnosis: document.getElementById('dis-diagnosis')?.value,
    treatment_summary: document.getElementById('dis-treatment-summary')?.value,
    discharge_medications: document.getElementById('dis-discharge-meds')?.value,
    diet_activity_advice: document.getElementById('dis-diet-advice')?.value,
    followup_advice: document.getElementById('dis-followup-advice')?.value
  };

  try {
    const res = await fetch('/core/api/doctor/create-discharge-summary/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status === 'success') {
      alert(`✓ Digital Discharge Summary published and cryptographically signed! Ref: ${data.summary_ref}`);
      document.getElementById('modal-discharge-summary')?.classList.remove('open');
      document.getElementById('form-discharge-summary')?.reset();
    } else {
      alert(data.message || 'Error creating discharge summary');
    }
  } catch (err) {
    console.error('Discharge error:', err);
    alert('Failed to issue discharge summary');
  }
}

// Submit Doctor Consent Request
async function submitDoctorConsentRequest() {
  const checkboxes = document.querySelectorAll('input[name="consent-types"]:checked');
  const recordTypes = Array.from(checkboxes).map(c => c.value);
  const payload = {
    patient_query: document.getElementById('consent-patient-query')?.value,
    record_types: recordTypes,
    reason_for_access: document.getElementById('consent-reason')?.value,
    validity_hours: document.getElementById('consent-validity')?.value
  };

  try {
    const res = await fetch('/core/api/doctor/request-consent/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status === 'success') {
      alert('✓ Record access consent request transmitted to citizen portal.');
      document.getElementById('modal-request-consent')?.classList.remove('open');
      document.getElementById('form-request-consent')?.reset();
    } else {
      alert(data.message || 'Error requesting consent');
    }
  } catch (err) {
    console.error('Consent request error:', err);
    alert('Failed to send consent request');
  }
}

// Submit Doctor Vaccination Record
async function submitDoctorVaccination() {
  const payload = {
    patient_query: document.getElementById('vac-patient-query')?.value,
    vaccine_name: document.getElementById('vac-name')?.value,
    dose_number: document.getElementById('vac-dose-number')?.value,
    batch_number: document.getElementById('vac-batch-number')?.value,
    administration_site: document.getElementById('vac-site')?.value,
    next_due_date: document.getElementById('vac-next-due')?.value
  };

  try {
    const res = await fetch('/core/api/doctor/add-vaccination/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status === 'success') {
      alert('✓ Immunization record logged to citizen National Digital Vaccine Register.');
      document.getElementById('modal-log-vaccination')?.classList.remove('open');
      document.getElementById('form-log-vaccination')?.reset();
    } else {
      alert(data.message || 'Error logging vaccination');
    }
  } catch (err) {
    console.error('Vaccination error:', err);
    alert('Failed to log vaccination');
  }
}
