/**
 * Hospital Government of India - Live Vitals Chart Telemetry Engine
 * Plots BP, SpO2, Sugar, Weight, Blood Percentage (Hb), and Heart Rate using Chart.js
 */

const VitalsChartEngine = {
  charts: {},

  init() {
    this.fetchAndRenderAll();
  },

  fetchAndRenderAll() {
    fetch('/api/vitals/')
      .then(res => {
        if (res.redirected || !res.ok) return null;
        return res.json();
      })
      .then(data => {
        if (data && data.success && data.history) {
          this.renderCharts(data.history);
          this.updateMetricCards(data.latest);
        }
      })
      .catch(err => console.error('Error loading vitals telemetry:', err));
  },

  updateMetricCards(latest) {
    if (!latest) return;

    // 1. Blood Pressure
    const bpVal = document.getElementById('card-bp-val');
    const bpStatus = document.getElementById('card-bp-status');
    if (bpVal) bpVal.textContent = latest.bp_display;
    if (bpStatus && latest.bp_status) {
      bpStatus.textContent = latest.bp_status.label;
      bpStatus.className = `vital-status-pill ${latest.bp_status.color}`;
    }

    // 2. Oxygen Saturation (SpO2)
    const o2Val = document.getElementById('card-o2-val');
    const o2Status = document.getElementById('card-o2-status');
    if (o2Val) o2Val.textContent = `${latest.o2_saturation}%`;
    if (o2Status && latest.o2_status) {
      o2Status.textContent = latest.o2_status.label;
      o2Status.className = `vital-status-pill ${latest.o2_status.color}`;
    }

    // 3. Sugar Percentage
    const sugarVal = document.getElementById('card-sugar-val');
    const sugarStatus = document.getElementById('card-sugar-status');
    if (sugarVal) sugarVal.textContent = `${latest.sugar_level}`;
    if (sugarStatus && latest.sugar_status) {
      sugarStatus.textContent = `${latest.sugar_type}: ${latest.sugar_status.label}`;
      sugarStatus.className = `vital-status-pill ${latest.sugar_status.color}`;
    }

    // 4. Body Weight
    const weightVal = document.getElementById('card-weight-val');
    if (weightVal) weightVal.textContent = `${latest.weight} kg`;

    // 5. Blood Percentage (Hemoglobin)
    const bloodVal = document.getElementById('card-blood-val');
    const bloodStatus = document.getElementById('card-blood-status');
    if (bloodVal) bloodVal.textContent = `${latest.blood_percentage} g/dL`;
    if (bloodStatus && latest.hb_status) {
      bloodStatus.textContent = latest.hb_status.label;
      bloodStatus.className = `vital-status-pill ${latest.hb_status.color}`;
    }

    // 6. Heart Rate
    const hrVal = document.getElementById('card-hr-val');
    const hrStatus = document.getElementById('card-hr-status');
    if (hrVal) hrVal.textContent = `${latest.heart_rate} BPM`;
    if (hrStatus && latest.hr_status) {
      hrStatus.textContent = latest.hr_status.label;
      hrStatus.className = `vital-status-pill ${latest.hr_status.color}`;
    }

    const lastSyncEl = document.getElementById('last-sync-time');
    if (lastSyncEl && latest.date) {
      lastSyncEl.textContent = `Last Clinical Update: ${latest.date} (${latest.source})`;
    }
  },

  renderCharts(history) {
    if (!window.Chart) return;

    const labels = history.map(item => item.date_short);

    // Chart 1: Blood Pressure (Systolic & Diastolic)
    const bpCtx = document.getElementById('chart-bp-canvas');
    if (bpCtx) {
      if (this.charts.bp) this.charts.bp.destroy();
      this.charts.bp = new Chart(bpCtx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [
            {
              label: 'Systolic (Max)',
              data: history.map(h => h.bp_systolic),
              borderColor: '#e63946',
              backgroundColor: 'rgba(230, 57, 70, 0.1)',
              tension: 0.3,
              fill: true,
              pointRadius: 4
            },
            {
              label: 'Diastolic (Min)',
              data: history.map(h => h.bp_diastolic),
              borderColor: '#457b9d',
              backgroundColor: 'transparent',
              borderDash: [4, 4],
              tension: 0.3,
              pointRadius: 4
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: 'top' } },
          scales: { y: { min: 50, max: 180 } }
        }
      });
    }

    // Chart 2: Blood Sugar & SpO2
    const sugarCtx = document.getElementById('chart-sugar-canvas');
    if (sugarCtx) {
      if (this.charts.sugar) this.charts.sugar.destroy();
      this.charts.sugar = new Chart(sugarCtx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [
            {
              label: 'Blood Glucose (mg/dL)',
              data: history.map(h => h.sugar_level),
              borderColor: '#ff9933',
              backgroundColor: 'rgba(255, 153, 51, 0.1)',
              tension: 0.3,
              fill: true,
              pointRadius: 5
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: 'top' } },
          scales: { y: { min: 60, max: 220 } }
        }
      });
    }

    // Chart 3: Heart Rate (BPM) Pulse
    const hrCtx = document.getElementById('chart-hr-canvas');
    if (hrCtx) {
      if (this.charts.hr) this.charts.hr.destroy();
      this.charts.hr = new Chart(hrCtx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [
            {
              label: 'Resting Heart Rate (BPM)',
              data: history.map(h => h.heart_rate),
              borderColor: '#e0218a',
              backgroundColor: 'rgba(224, 33, 138, 0.12)',
              tension: 0.4,
              fill: true,
              pointRadius: 4
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: 'top' } },
          scales: { y: { min: 50, max: 130 } }
        }
      });
    }

    // Chart 4: Hemoglobin & Weight
    const hbCtx = document.getElementById('chart-hb-canvas');
    if (hbCtx) {
      if (this.charts.hb) this.charts.hb.destroy();
      this.charts.hb = new Chart(hbCtx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [
            {
              label: 'Hemoglobin (g/dL)',
              data: history.map(h => h.blood_percentage),
              backgroundColor: '#9d0208',
              borderRadius: 6
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: 'top' } },
          scales: { y: { min: 5, max: 18 } }
        }
      });
    }
  }
};

window.VitalsChartEngine = VitalsChartEngine;
document.addEventListener('DOMContentLoaded', () => {
  VitalsChartEngine.init();
});
