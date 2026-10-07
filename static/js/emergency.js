/**
 * Emergency SOS Engine — Swasthya Setu
 * Handles: SOS creation, status polling, cancellation, feedback, broadcast display
 */

const EmergencySOS = {
  activeSosId: null,
  pollTimer: null,
  userLat: null,
  userLon: null,

  // ==================== INIT ====================
  init() {
    this.detectLocation();
    this.loadFeedbackAppointments();
    this.checkActiveSOS();
  },

  // ==================== GEOLOCATION ====================
  detectLocation() {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        this.userLat = pos.coords.latitude;
        this.userLon = pos.coords.longitude;
      },
      () => {
        this.userLat = 28.6139;  // fallback: New Delhi
        this.userLon = 77.2090;
      }
    );
  },

  // ==================== SOS TRIGGER ====================
  async triggerSOS() {
    const btn = document.getElementById('btn-sos-trigger');
    const emergencyType = document.getElementById('sos-emergency-type')?.value || 'Accident / Injury';

    if (this.activeSosId) {
      alert('🚨 You already have an active SOS request. Please check the status tracker below.');
      return;
    }

    const confirmMsg = `🚨 CONFIRM EMERGENCY SOS\n\nType: ${emergencyType}\n\nThis will immediately alert the nearest government hospital and dispatch an ambulance to your location.\n\nAre you sure?`;
    if (!confirm(confirmMsg)) return;

    btn.disabled = true;
    btn.innerHTML = '<span>⏳</span><span style="font-size:0.6rem;">SENDING…</span>';

    try {
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
        || document.cookie.split('; ').find(r => r.startsWith('csrftoken='))?.split('=')[1] || '';

      const payload = {
        emergency_type: emergencyType,
        latitude: this.userLat || 28.6139,
        longitude: this.userLon || 77.2090,
        location_address: 'Detected via GPS',
        notes: `Patient triggered SOS for: ${emergencyType}`,
        contact_phone: ''
      };

      const res = await fetch('/api/patient/sos/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (data.status === 'success') {
        this.activeSosId = data.id;
        localStorage.setItem('active_sos_id', data.id);
        this.showStatusTracker(data);
        this.startPolling();
        this.playAlertSound();
      } else {
        alert('❌ SOS Failed: ' + (data.message || 'Unknown error'));
        btn.disabled = false;
        btn.innerHTML = '<span>🆘</span><span style="font-size:0.7rem;font-weight:800;color:#991b1b;">SEND SOS</span>';
      }
    } catch (err) {
      console.error('SOS Error:', err);
      alert('❌ Network error. Please call 108 directly for ambulance.');
      btn.disabled = false;
      btn.innerHTML = '<span>🆘</span><span style="font-size:0.7rem;font-weight:800;color:#991b1b;">SEND SOS</span>';
    }
  },

  // ==================== STATUS DISPLAY ====================
  showStatusTracker(data) {
    const tracker = document.getElementById('sos-status-tracker');
    if (!tracker) return;
    tracker.style.display = 'block';
    tracker.scrollIntoView({ behavior: 'smooth', block: 'center' });

    document.getElementById('sos-detail-id').textContent = `SOS-${data.id}`;
    document.getElementById('sos-detail-type').textContent = data.emergency_type || '—';
    document.getElementById('sos-detail-hospital').textContent = data.hospital || 'Nearest Gov. Hospital';
    document.getElementById('sos-detail-eta').textContent = data.eta_minutes ? `~${data.eta_minutes} min` : 'Calculating…';

    const priorityBadge = document.getElementById('sos-priority-badge');
    if (priorityBadge) {
      priorityBadge.textContent = data.priority || 'CRITICAL';
      priorityBadge.style.background = data.priority === 'CRITICAL' ? '#dc2626' : data.priority === 'HIGH' ? '#f59e0b' : '#3b82f6';
    }

    this.updateSteps(data.status || 'RECEIVED');
  },

  updateSteps(currentStatus) {
    const statusOrder = ['RECEIVED', 'DISPATCHED', 'EN_ROUTE', 'ON_SCENE', 'RESOLVED'];
    const steps = document.querySelectorAll('.sos-step');
    const currentIdx = statusOrder.indexOf(currentStatus);

    steps.forEach((step, i) => {
      step.classList.remove('active', 'done');
      if (i < currentIdx) step.classList.add('done');
      else if (i === currentIdx) step.classList.add('active');
    });
  },

  // ==================== POLLING ====================
  async pollStatus() {
    if (!this.activeSosId) return;
    try {
      const res = await fetch(`/api/patient/sos/${this.activeSosId}/status/`);
      const data = await res.json();

      if (data.status === 'success' && data.sos) {
        const sos = data.sos;
        document.getElementById('sos-detail-eta').textContent = sos.eta_minutes ? `~${sos.eta_minutes} min` : 'Calculating…';
        this.updateSteps(sos.status);

        if (sos.status === 'RESOLVED' || sos.status === 'CANCELLED') {
          this.stopPolling();
          if (sos.status === 'RESOLVED') {
            alert('✅ Your emergency has been resolved. Please remain with the medical team.');
          }
        }
      }
    } catch (err) {
      console.error('Status poll error:', err);
    }
  },

  startPolling() {
    this.stopPolling();
    this.pollTimer = setInterval(() => this.pollStatus(), 30000);  // every 30s
  },

  stopPolling() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  },

  // ==================== CANCEL SOS ====================
  async cancelSOS() {
    if (!this.activeSosId) return;
    if (!confirm('Are you sure you want to cancel this emergency request?')) return;

    try {
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
        || document.cookie.split('; ').find(r => r.startsWith('csrftoken='))?.split('=')[1] || '';

      const res = await fetch(`/api/patient/sos/${this.activeSosId}/cancel/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken }
      });
      const data = await res.json();

      if (data.status === 'success') {
        this.activeSosId = null;
        localStorage.removeItem('active_sos_id');
        this.stopPolling();
        document.getElementById('sos-status-tracker').style.display = 'none';
        const btn = document.getElementById('btn-sos-trigger');
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = '<span>🆘</span><span style="font-size:0.7rem;font-weight:800;color:#991b1b;">SEND SOS</span>';
        }
        alert('✓ Emergency request cancelled.');
      }
    } catch (err) {
      console.error('Cancel SOS error:', err);
    }
  },

  // ==================== CHECK EXISTING SOS ====================
  async checkActiveSOS() {
    const storedId = localStorage.getItem('active_sos_id');
    if (!storedId) return;
    this.activeSosId = storedId;

    try {
      const res = await fetch(`/api/patient/sos/${storedId}/status/`);
      const data = await res.json();
      if (data.status === 'success' && data.sos) {
        const sos = data.sos;
        if (sos.status !== 'RESOLVED' && sos.status !== 'CANCELLED') {
          this.showStatusTracker(sos);
          this.startPolling();
        } else {
          localStorage.removeItem('active_sos_id');
          this.activeSosId = null;
        }
      }
    } catch (err) {
      console.error('Check SOS error:', err);
    }
  },

  // ==================== SOUND ALERT ====================
  playAlertSound() {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      [440, 880, 660].forEach((freq, i) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = freq;
        osc.type = 'square';
        gain.gain.setValueAtTime(0.3, ctx.currentTime + i * 0.2);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.2 + 0.3);
        osc.start(ctx.currentTime + i * 0.2);
        osc.stop(ctx.currentTime + i * 0.2 + 0.3);
      });
    } catch (e) { /* AudioContext not available */ }
  },

  // ==================== FEEDBACK / RATING ====================
  async loadFeedbackAppointments() {
    const container = document.getElementById('feedback-appointment-list');
    if (!container) return;

    try {
      const res = await fetch('/api/patient/appointments/completed/');
      const data = await res.json();

      if (!data.appointments || data.appointments.length === 0) {
        container.innerHTML = '<div style="color:var(--text-muted);font-size:0.88rem;text-align:center;padding:20px;">No completed appointments found. Rate your experience after a visit.</div>';
        return;
      }

      container.innerHTML = data.appointments.map(appt => `
        <div id="feedback-card-${appt.id}" style="background:var(--bg);border:1px solid var(--border);border-radius:12px;padding:16px;">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap;">
            <div>
              <div style="font-weight:800;font-size:0.95rem;color:var(--text);">Dr. ${appt.doctor} — ${appt.department}</div>
              <div style="font-size:0.8rem;color:var(--text-muted);">📅 ${appt.date} · 🏥 ${appt.hospital}</div>
            </div>
            ${appt.already_rated ? '<span style="background:#dcfce7;color:#166534;border-radius:20px;padding:4px 12px;font-size:0.75rem;font-weight:700;">✓ Rated</span>' : ''}
          </div>
          ${!appt.already_rated ? `
          <div style="margin-top:14px;">
            <div style="font-size:0.82rem;font-weight:700;color:var(--text);margin-bottom:8px;">How was your experience?</div>
            <div class="star-rating" id="stars-${appt.id}">
              ${[5,4,3,2,1].map(n => `
                <input type="radio" id="star${n}-${appt.id}" name="rating-${appt.id}" value="${n}">
                <label for="star${n}-${appt.id}" title="${n} stars">★</label>
              `).join('')}
            </div>
            <textarea id="feedback-comment-${appt.id}" placeholder="Share your feedback (optional)…" style="width:100%;margin-top:10px;padding:10px;border-radius:8px;border:1px solid var(--border);background:var(--card-bg);color:var(--text);font-size:0.83rem;resize:vertical;min-height:70px;"></textarea>
            <div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap;">
              <select id="feedback-category-${appt.id}" style="padding:8px;border-radius:8px;border:1px solid var(--border);background:var(--card-bg);color:var(--text);font-size:0.82rem;flex:1;">
                <option value="GENERAL">General Feedback</option>
                <option value="STAFF">Staff Behavior</option>
                <option value="CLEANLINESS">Cleanliness</option>
                <option value="WAIT_TIME">Wait Time</option>
                <option value="TREATMENT">Treatment Quality</option>
                <option value="COMPLAINT">Complaint</option>
              </select>
              <button onclick="EmergencySOS.submitFeedback(${appt.id})" style="background:var(--primary);color:#fff;border:none;border-radius:8px;padding:8px 18px;font-weight:700;font-size:0.85rem;cursor:pointer;">Submit ⭐</button>
            </div>
          </div>` : `<div style="margin-top:10px;font-size:0.8rem;color:var(--text-muted);">⭐ Rating: ${appt.rating || 'N/A'}/5 — Thank you for your feedback!</div>`}
        </div>
      `).join('');
    } catch (err) {
      container.innerHTML = '<div style="color:var(--text-muted);font-size:0.88rem;text-align:center;padding:20px;">Unable to load appointments.</div>';
    }
  },

  async submitFeedback(apptId) {
    const ratingInput = document.querySelector(`input[name="rating-${apptId}"]:checked`);
    if (!ratingInput) { alert('Please select a star rating first.'); return; }

    const rating = parseInt(ratingInput.value);
    const comment = document.getElementById(`feedback-comment-${apptId}`)?.value || '';
    const category = document.getElementById(`feedback-category-${apptId}`)?.value || 'GENERAL';

    try {
      const csrfToken = document.cookie.split('; ').find(r => r.startsWith('csrftoken='))?.split('=')[1] || '';
      const res = await fetch('/api/patient/feedback/submit/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
        body: JSON.stringify({ appointment_id: apptId, rating, comment, category })
      });
      const data = await res.json();

      if (data.status === 'success') {
        const card = document.getElementById(`feedback-card-${apptId}`);
        if (card) {
          card.style.border = '1.5px solid #059669';
          card.querySelector('[id^="stars-"]')?.closest('div')?.remove();
          const ratedBadge = document.createElement('div');
          ratedBadge.innerHTML = `<div style="margin-top:10px;font-size:0.85rem;color:#166534;font-weight:700;">✅ Thank you! Your feedback has been submitted (${rating}/5 stars).</div>`;
          card.appendChild(ratedBadge);
        }
      } else {
        alert('Error: ' + (data.message || 'Could not submit feedback.'));
      }
    } catch (err) {
      alert('Network error. Please try again.');
    }
  }
};

// Auto-init when emergency tab loads
document.addEventListener('DOMContentLoaded', () => {
  EmergencySOS.init();

  // Also init when tab becomes active
  document.getElementById('nav-btn-emergency')?.addEventListener('click', () => {
    setTimeout(() => EmergencySOS.init(), 200);
  });
});

window.EmergencySOS = EmergencySOS;
