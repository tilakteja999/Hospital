/**
 * Hospital Government of India - Aadhaar OTP Authentication & Verification Engine
 */

const AadhaarAuthEngine = {
  init() {
    this.attachInputs();
  },

  attachInputs() {
    const aadhaarInput = document.getElementById('aadhaar-number-input');
    const sendOtpBtn = document.getElementById('btn-send-aadhaar-otp');
    const verifyOtpBtn = document.getElementById('btn-verify-aadhaar-otp');
    const otpContainer = document.getElementById('aadhaar-otp-container');
    const otpInput = document.getElementById('aadhaar-otp-input');
    const statusMsg = document.getElementById('aadhaar-status-msg');

    if (aadhaarInput) {
      aadhaarInput.addEventListener('input', (e) => {
        let val = e.target.value.replace(/\D/g, '').substring(0, 12);
        // Format with hyphens XXXX-XXXX-XXXX
        let formatted = val.match(/.{1,4}/g)?.join('-') || val;
        e.target.value = formatted;
      });
    }

    if (sendOtpBtn) {
      sendOtpBtn.addEventListener('click', () => {
        const rawAadhaar = aadhaarInput ? aadhaarInput.value.replace(/-/g, '').trim() : '';
        const phone = document.getElementById('phone-input') ? document.getElementById('phone-input').value.trim() : '';

        if (rawAadhaar.length !== 12) {
          this.showMessage(statusMsg, 'Please enter a valid 12-digit Aadhaar number.', 'danger');
          return;
        }

        sendOtpBtn.disabled = true;
        sendOtpBtn.textContent = 'Sending OTP...';

        fetch('/api/aadhaar/generate-otp/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ aadhaar_number: rawAadhaar, phone: phone })
        })
        .then(res => res.json())
        .then(data => {
          sendOtpBtn.disabled = false;
          sendOtpBtn.textContent = 'Resend OTP';

          if (data.success) {
            this.showMessage(statusMsg, `${data.message} (Demo OTP: ${data.demo_otp})`, 'success');
            if (otpContainer) otpContainer.style.display = 'block';
            if (otpInput) otpInput.value = data.demo_otp; // Auto pre-fill for seamless user experience
          } else {
            this.showMessage(statusMsg, data.message, 'danger');
          }
        })
        .catch(err => {
          sendOtpBtn.disabled = false;
          sendOtpBtn.textContent = 'Send OTP';
          this.showMessage(statusMsg, 'Error generating OTP. Try again.', 'danger');
        });
      });
    }

    if (verifyOtpBtn) {
      verifyOtpBtn.addEventListener('click', () => {
        const rawAadhaar = aadhaarInput ? aadhaarInput.value.replace(/-/g, '').trim() : '';
        const otpVal = otpInput ? otpInput.value.trim() : '';

        if (!otpVal) {
          this.showMessage(statusMsg, 'Please enter the 6-digit OTP.', 'danger');
          return;
        }

        verifyOtpBtn.disabled = true;
        verifyOtpBtn.textContent = 'Verifying...';

        fetch('/api/aadhaar/verify-otp/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ aadhaar_number: rawAadhaar, otp: otpVal })
        })
        .then(res => res.json())
        .then(data => {
          verifyOtpBtn.disabled = false;
          verifyOtpBtn.textContent = 'Verify OTP';

          if (data.success) {
            this.showMessage(statusMsg, '✓ Aadhaar Successfully Verified with UIDAI.', 'success');
            const hiddenVerifyField = document.getElementById('is-aadhaar-verified-field');
            if (hiddenVerifyField) hiddenVerifyField.value = 'true';
            if (aadhaarInput) aadhaarInput.readOnly = true;
            if (sendOtpBtn) sendOtpBtn.style.display = 'none';
            if (otpContainer) otpContainer.style.display = 'none';
            const badge = document.getElementById('aadhaar-badge-verified');
            if (badge) badge.style.display = 'inline-flex';
          } else {
            this.showMessage(statusMsg, data.message, 'danger');
          }
        })
        .catch(err => {
          verifyOtpBtn.disabled = false;
          verifyOtpBtn.textContent = 'Verify OTP';
          this.showMessage(statusMsg, 'Verification request failed.', 'danger');
        });
      });
    }
  },

  showMessage(el, text, type) {
    if (!el) return;
    el.textContent = text;
    el.className = `alert alert-${type}`;
    el.style.display = 'block';
  }
};

window.AadhaarAuthEngine = AadhaarAuthEngine;
document.addEventListener('DOMContentLoaded', () => {
  AadhaarAuthEngine.init();
});
