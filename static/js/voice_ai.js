/**
 * Swasthya Setu — Multilingual Voice-First AI Hospital Assistant Engine
 * 
 * Key Capabilities:
 * 1. Web Speech API Speech Recognition with confidence tracking and Indic language locales.
 * 2. Multi-turn deterministic state machine with server confirmation token execution.
 * 3. Interruptible Text-To-Speech (TTS) with audio playback controls (Stop, Repeat, Mute).
 * 4. Dedicated High-Contrast Easy Voice Mode with large touch targets and auto-read aloud.
 * 5. Audio wave visualizer and real-time state indicator badges (Listening, Thinking, Speaking, Confirming).
 * 6. Dual-modality: Seamless fallback to text typing without losing conversation context.
 * 7. Safe Route Navigation Whitelist integration.
 */

const VoiceAIEngine = {
  recognition: null,
  isListening: false,
  isSpeaking: false,
  synth: window.speechSynthesis || null,
  currentUtterance: null,
  selectedLanguage: localStorage.getItem('hospital_portal_lang') || 'hi-IN',
  sessionId: localStorage.getItem('swasthya_voice_session_id') || '',
  lastSpokenText: '',
  lastSpokenLang: 'hi-IN',
  activeConfirmationToken: '',
  easyVoiceModeActive: false,

  init() {
    this.initSpeechRecognition();
    this.attachEvents();
    this.setLanguage(this.selectedLanguage);
    this.updateStateUI('IDLE');
  },

  initSpeechRecognition() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRec) {
      this.recognition = new SpeechRec();
      this.recognition.continuous = false;
      this.recognition.interimResults = true;
      this.recognition.lang = this.selectedLanguage;

      this.recognition.onstart = () => {
        this.isListening = true;
        this.stopSpeaking();
        this.updateStateUI('LISTENING');
        this.setAudioWavesActive(true);
      };

      this.recognition.onresult = (event) => {
        let interim = '';
        let finalTranscript = '';
        let confidence = 1.0;

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
            confidence = event.results[i][0].confidence || 1.0;
          } else {
            interim += event.results[i][0].transcript;
          }
        }

        if (interim && !finalTranscript) {
          const micLabel = document.getElementById('hero-mic-label');
          if (micLabel) micLabel.innerText = `"${interim.slice(-25)}..."`;
        }

        if (finalTranscript) {
          this.appendMessage('user', finalTranscript);
          this.updateStateUI('THINKING');
          this.processVoiceQuery(finalTranscript, confidence);
        }
      };

      this.recognition.onerror = (event) => {
        console.warn('Voice AI Speech Recognition Error:', event.error);
        this.isListening = false;
        this.setAudioWavesActive(false);
        if (event.error !== 'no-speech') {
          this.updateStateUI('ERROR', 'Could not hear clearly. Tap to retry.');
        } else {
          this.updateStateUI('IDLE');
        }
      };

      this.recognition.onend = () => {
        this.isListening = false;
        this.setAudioWavesActive(false);
        if (!this.isSpeaking) {
          const micBtn = document.getElementById('voice-hero-mic-btn');
          if (micBtn) micBtn.classList.remove('listening');
        }
      };
    } else {
      console.warn('Web Speech API is not supported on this browser.');
    }
  },

  attachEvents() {
    // 1. Trigger button & modal controls
    const triggerBtn = document.getElementById('voice-ai-trigger-btn');
    const modal = document.getElementById('voice-bot-modal');
    const closeBtn = document.getElementById('voice-modal-close');
    const easyToggleInModal = document.getElementById('voice-easy-mode-toggle');
    const headerEasyBtn = document.getElementById('header-easy-voice-btn');

    if (triggerBtn && modal) {
      triggerBtn.addEventListener('click', () => {
        modal.classList.toggle('open');
        if (modal.classList.contains('open')) {
          this.startListening();
        } else {
          this.stopListening();
          this.stopSpeaking();
        }
      });
    }

    if (closeBtn && modal) {
      closeBtn.addEventListener('click', () => {
        modal.classList.remove('open');
        this.stopListening();
        this.stopSpeaking();
      });
    }

    // 2. Primary Hero Mic button inside modal
    const heroMicBtn = document.getElementById('voice-hero-mic-btn');
    if (heroMicBtn) {
      heroMicBtn.addEventListener('click', () => {
        if (this.isListening) {
          this.stopListening();
        } else {
          this.startListening();
        }
      });
    }

    // 3. Inline Mic & Text Input Controls
    const micInline = document.getElementById('voice-mic-inline');
    const sendBtn = document.getElementById('voice-send-btn');
    const inputField = document.getElementById('voice-text-input');
    const langSelect = document.getElementById('voice-lang-select');
    const topLangSelect = document.getElementById('top-lang-select');

    if (micInline) {
      micInline.addEventListener('click', () => {
        if (this.isListening) {
          this.stopListening();
        } else {
          this.startListening();
        }
      });
    }

    if (sendBtn && inputField) {
      const handleSend = () => {
        const text = inputField.value.trim();
        if (text) {
          this.appendMessage('user', text);
          inputField.value = '';
          this.updateStateUI('THINKING');
          this.processVoiceQuery(text, 1.0);
        }
      };
      sendBtn.addEventListener('click', handleSend);
      inputField.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSend();
      });
    }

    if (langSelect) {
      langSelect.value = this.selectedLanguage;
      langSelect.addEventListener('change', (e) => {
        this.setLanguage(e.target.value);
      });
    }

    if (topLangSelect) {
      topLangSelect.value = this.selectedLanguage;
      topLangSelect.addEventListener('change', (e) => {
        this.setLanguage(e.target.value);
      });
    }

    // 4. Audio Control Toolbar
    const stopBtn = document.getElementById('voice-toolbar-stop');
    const repeatBtn = document.getElementById('voice-toolbar-repeat');
    const resetBtn = document.getElementById('voice-toolbar-reset');
    const doctorBtn = document.getElementById('voice-toolbar-doctor');
    const emergencyBtn = document.getElementById('voice-toolbar-emergency');

    if (stopBtn) {
      stopBtn.addEventListener('click', () => {
        this.stopSpeaking();
        this.updateStateUI('IDLE');
      });
    }

    if (repeatBtn) {
      repeatBtn.addEventListener('click', () => {
        if (this.lastSpokenText) {
          this.speak(this.lastSpokenText, this.lastSpokenLang);
        }
      });
    }

    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        this.resetSession();
      });
    }

    if (doctorBtn) {
      doctorBtn.addEventListener('click', () => {
        this.appendMessage('user', 'Book an appointment');
        this.processVoiceQuery('Book an appointment', 1.0);
      });
    }

    if (emergencyBtn) {
      emergencyBtn.addEventListener('click', () => {
        this.processVoiceQuery('Emergency medical help', 1.0);
      });
    }

    // 5. Quick Voice Chips
    document.querySelectorAll('.quick-chip-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const query = btn.getAttribute('data-query');
        if (query) {
          this.appendMessage('user', query);
          this.processVoiceQuery(query, 1.0);
        }
      });
    });

    // 6. Easy Voice Mode Overlay Controls
    if (headerEasyBtn) {
      headerEasyBtn.addEventListener('click', () => {
        this.openEasyVoiceMode();
      });
    }

    if (easyToggleInModal) {
      easyToggleInModal.addEventListener('click', () => {
        if (modal) modal.classList.remove('open');
        this.openEasyVoiceMode();
      });
    }

    const easyExitBtn = document.getElementById('easy-voice-exit-btn');
    if (easyExitBtn) {
      easyExitBtn.addEventListener('click', () => {
        this.closeEasyVoiceMode();
      });
    }

    const easyGiantMic = document.getElementById('easy-giant-mic-btn');
    if (easyGiantMic) {
      easyGiantMic.addEventListener('click', () => {
        if (this.isListening) {
          this.stopListening();
        } else {
          this.startListening();
        }
      });
    }

    // Easy Voice Mode Action Buttons
    document.querySelectorAll('.easy-grid-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const action = btn.getAttribute('data-action');
        this.handleEasyAction(action);
      });
    });

    // Easy Mode Yes / No Confirmation Buttons
    const easyYesBtn = document.getElementById('easy-confirm-yes');
    const easyNoBtn = document.getElementById('easy-confirm-no');
    if (easyYesBtn) {
      easyYesBtn.addEventListener('click', () => {
        this.appendMessage('user', 'Yes, confirm');
        this.processVoiceQuery('Yes', 1.0);
        const confirmBar = document.getElementById('easy-voice-confirm-bar');
        if (confirmBar) confirmBar.style.display = 'none';
      });
    }
    if (easyNoBtn) {
      easyNoBtn.addEventListener('click', () => {
        this.appendMessage('user', 'No, cancel');
        this.processVoiceQuery('No', 1.0);
        const confirmBar = document.getElementById('easy-voice-confirm-bar');
        if (confirmBar) confirmBar.style.display = 'none';
      });
    }

    // 7. Modal Confirmation Action Handlers
    const confirmProceedBtn = document.getElementById('ai-confirm-proceed-btn');
    const confirmCancelBtn = document.getElementById('ai-confirm-cancel-btn');
    if (confirmProceedBtn) {
      confirmProceedBtn.addEventListener('click', () => {
        const modalEl = document.getElementById('modal-ai-action-confirm');
        if (modalEl) modalEl.classList.remove('open');
        this.processVoiceQuery('Yes', 1.0);
      });
    }
    if (confirmCancelBtn) {
      confirmCancelBtn.addEventListener('click', () => {
        const modalEl = document.getElementById('modal-ai-action-confirm');
        if (modalEl) modalEl.classList.remove('open');
        this.processVoiceQuery('No', 1.0);
      });
    }
  },

  startListening() {
    this.stopSpeaking();
    if (this.recognition && !this.isListening) {
      try {
        this.recognition.lang = this.selectedLanguage;
        this.recognition.start();
      } catch (e) {
        console.warn('Speech recognition start error:', e);
      }
    }
  },

  stopListening() {
    if (this.recognition && this.isListening) {
      try {
        this.recognition.stop();
      } catch (e) {}
      this.isListening = false;
      this.setAudioWavesActive(false);
      this.updateStateUI('IDLE');
    }
  },

  updateStateUI(state, customText = '') {
    const stateText = document.getElementById('voice-state-text');
    const indicator = document.getElementById('voice-state-indicator');
    const heroMic = document.getElementById('voice-hero-mic-btn');
    const heroLabel = document.getElementById('hero-mic-label');
    const easyMicText = document.getElementById('easy-mic-status-text');
    const easyGiantBtn = document.getElementById('easy-giant-mic-btn');

    if (indicator) {
      indicator.className = `voice-state-indicator ${state.toLowerCase()}`;
    }

    let label = 'Tap to Speak';
    let statusMsg = 'Ready';

    switch (state) {
      case 'LISTENING':
        statusMsg = '🎙️ Listening... Speak now';
        label = 'Listening...';
        if (heroMic) heroMic.classList.add('listening');
        if (easyGiantBtn) easyGiantBtn.classList.add('listening');
        if (easyMicText) easyMicText.innerText = 'LISTENING...';
        break;
      case 'THINKING':
        statusMsg = '⏳ Understanding...';
        label = 'Understanding...';
        if (heroMic) heroMic.classList.remove('listening');
        if (easyGiantBtn) easyGiantBtn.classList.remove('listening');
        if (easyMicText) easyMicText.innerText = 'UNDERSTANDING...';
        break;
      case 'TOOL_EXECUTION':
        statusMsg = '📅 Finding slots / Checking records...';
        label = 'Working...';
        break;
      case 'SPEAKING':
        statusMsg = '🔊 Speaking...';
        label = 'Speaking...';
        if (easyMicText) easyMicText.innerText = 'SPEAK';
        break;
      case 'CONFIRMATION_REQUIRED':
        statusMsg = '⚠️ Confirmation Required';
        label = 'Confirming...';
        break;
      case 'ERROR':
        statusMsg = customText || '⚠️ Temporary issue. Tap to retry.';
        label = 'Tap to Retry';
        if (easyMicText) easyMicText.innerText = 'RETRY';
        break;
      default: // IDLE
        statusMsg = 'Ready to listen';
        label = 'Tap to Speak';
        if (heroMic) heroMic.classList.remove('listening');
        if (easyGiantBtn) easyGiantBtn.classList.remove('listening');
        if (easyMicText) easyMicText.innerText = 'SPEAK';
        break;
    }

    if (stateText) stateText.innerText = customText || statusMsg;
    if (heroLabel) heroLabel.innerText = label;
  },

  setAudioWavesActive(active) {
    const waveBox = document.getElementById('voice-wave-container');
    if (waveBox) {
      waveBox.classList.toggle('active', active);
    }
  },

  appendMessage(sender, text, isUrgent = false) {
    const body = document.getElementById('voice-bot-body');
    if (!body) return;

    const bubble = document.createElement('div');
    bubble.className = `voice-msg-bubble ${sender}`;
    if (isUrgent) {
      bubble.style.background = '#fef2f2';
      bubble.style.border = '2px solid #ef4444';
      bubble.style.color = '#991b1b';
      bubble.style.fontWeight = '700';
    }
    bubble.innerText = text;
    body.appendChild(bubble);
    body.scrollTop = body.scrollHeight;

    // Update Easy Voice Mode text card if active
    const easySpeechText = document.getElementById('easy-speech-text');
    if (easySpeechText && sender === 'ai') {
      easySpeechText.innerText = `"${text}"`;
    }
  },

  getSafeRouteContext() {
    let currentTab = 'home';
    const activeNav = document.querySelector('.nav-tab-btn.active');
    if (activeNav) {
      currentTab = activeNav.getAttribute('data-tab') || 'home';
    }
    return {
      current_route: window.location.pathname,
      active_tab: currentTab
    };
  },

  processVoiceQuery(text, confidence = 1.0) {
    const routeCtx = this.getSafeRouteContext();

    fetch('/api/assistant/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: text,
        confidence: confidence,
        lang: this.selectedLanguage,
        session_id: this.sessionId,
        context: routeCtx
      })
    })
    .then(res => res.json())
    .then(data => {
      if (data.session_id) {
        this.sessionId = data.session_id;
        localStorage.setItem('swasthya_voice_session_id', data.session_id);
      }

      const respLang = data.lang || this.selectedLanguage;
      if (data.reply) {
        this.lastSpokenText = data.reply;
        this.lastSpokenLang = respLang;
        this.appendMessage('ai', data.reply, data.is_urgent);
        this.speak(data.reply, respLang);
      }

      if (data.status_indicator) {
        this.updateStateUI(data.status_indicator);
      }

      // 1. Language switch update
      if (data.action === 'set_language' && data.target_lang) {
        this.setLanguage(data.target_lang);
      }

      // 2. Consequential Confirmation Token Handling
      if (data.confirmation_required && data.confirmation_token) {
        this.activeConfirmationToken = data.confirmation_token;
        this.showConfirmationModal(data.reply, data.confirmation_token);
        
        const easyConfirmBar = document.getElementById('easy-voice-confirm-bar');
        if (easyConfirmBar) easyConfirmBar.style.display = 'flex';
      } else {
        const easyConfirmBar = document.getElementById('easy-voice-confirm-bar');
        if (easyConfirmBar) easyConfirmBar.style.display = 'none';
      }

      // 3. Safe Navigation Handling
      if (data.action === 'navigate' || data.action === 'navigate_and_speak' || data.tab) {
        const targetTab = data.tab || 'home';
        if (window.App && typeof window.App.switchTab === 'function') {
          window.App.switchTab(targetTab);
        }
      }

      // 4. Booking Completion Feedback
      if (data.action === 'booking_completed') {
        if (window.App && typeof window.App.switchTab === 'function') {
          window.App.switchTab('bookings');
        }
        setTimeout(() => { window.location.reload(); }, 3500);
      }

      // 5. Easy Voice Mode Trigger
      if (data.action === 'open_easy_voice_mode') {
        this.openEasyVoiceMode();
      }
    })
    .catch(err => {
      console.error('Assistant API Error:', err);
      this.updateStateUI('ERROR');
      this.appendMessage('ai', 'Connection issue. Please verify network or try again.');
    });
  },

  showConfirmationModal(summaryText, token) {
    const modalEl = document.getElementById('modal-ai-action-confirm');
    const bodyEl = document.getElementById('ai-confirm-body');
    if (modalEl && bodyEl) {
      bodyEl.innerText = summaryText;
      modalEl.classList.add('open');
    }
  },

  speak(text, lang) {
    if (!this.synth) return;
    this.stopSpeaking();

    const cleanText = text.replace(/[*_#💡👨‍⚕️🚨✅⚠️]/g, '').trim();
    if (!cleanText) return;

    this.currentUtterance = new SpeechSynthesisUtterance(cleanText);
    const spokenLang = lang || this.selectedLanguage;
    this.currentUtterance.lang = spokenLang;
    this.currentUtterance.rate = 0.95;
    this.currentUtterance.pitch = 1.0;

    this.currentUtterance.onstart = () => {
      this.isSpeaking = true;
      this.updateStateUI('SPEAKING');
      this.setAudioWavesActive(true);
    };

    this.currentUtterance.onend = () => {
      this.isSpeaking = false;
      this.setAudioWavesActive(false);
      this.updateStateUI('IDLE');
    };

    this.currentUtterance.onerror = () => {
      this.isSpeaking = false;
      this.setAudioWavesActive(false);
      this.updateStateUI('IDLE');
    };

    // Voice match resolver
    const voices = this.synth.getVoices();
    const langPrefix = spokenLang.split('-')[0];
    const match = voices.find(v => v.lang.startsWith(langPrefix));
    if (match) this.currentUtterance.voice = match;

    this.synth.speak(this.currentUtterance);
  },

  stopSpeaking() {
    if (this.synth && this.synth.speaking) {
      this.synth.cancel();
      this.isSpeaking = false;
      this.setAudioWavesActive(false);
    }
  },

  setLanguage(langCode) {
    this.selectedLanguage = langCode;
    this.lastSpokenLang = langCode;
    localStorage.setItem('hospital_portal_lang', langCode);

    if (this.recognition) this.recognition.lang = langCode;

    const langSelect = document.getElementById('voice-lang-select');
    if (langSelect) langSelect.value = langCode;
    const topSelect = document.getElementById('top-lang-select');
    if (topSelect) topSelect.value = langCode;

    const pill = document.getElementById('voice-current-lang-pill');
    if (pill) {
      const names = {
        'en-IN': 'English', 'hi-IN': 'हिन्दी', 'te-IN': 'తెలుగు',
        'ta-IN': 'தமிழ்', 'bn-IN': 'বাংলা', 'mr-IN': 'मराठी',
        'kn-IN': 'ಕನ್ನಡ', 'ml-IN': 'മലയാളം'
      };
      pill.innerText = names[langCode] || langCode;
    }

    if (window.I18nEngine && typeof window.I18nEngine.applyLanguage === 'function') {
      window.I18nEngine.applyLanguage(langCode);
    }
  },

  resetSession() {
    fetch('/api/assistant/session-reset', { method: 'POST' })
      .then(res => res.json())
      .then(() => {
        const body = document.getElementById('voice-bot-body');
        if (body) {
          body.innerHTML = `
            <div class="voice-msg-bubble ai">
              🔄 <strong>Session reset.</strong> How can I assist you right now?
            </div>
          `;
        }
        this.updateStateUI('IDLE');
        this.speak("Session reset. How can I help you?", this.selectedLanguage);
      })
      .catch(err => console.error('Reset Session Error:', err));
  },

  openEasyVoiceMode() {
    this.easyVoiceModeActive = true;
    const overlay = document.getElementById('easy-voice-overlay');
    if (overlay) {
      overlay.classList.add('open');
    }
    const welcomeMsg = "Easy Voice Mode activated. Tap the big microphone to speak, or tap any large button.";
    this.speak(welcomeMsg, this.selectedLanguage);
  },

  closeEasyVoiceMode() {
    this.easyVoiceModeActive = false;
    const overlay = document.getElementById('easy-voice-overlay');
    if (overlay) {
      overlay.classList.remove('open');
    }
    this.stopSpeaking();
    this.stopListening();
  },

  handleEasyAction(action) {
    switch (action) {
      case 'home':
        if (window.App) window.App.switchTab('home');
        this.processVoiceQuery('Show my vitals', 1.0);
        break;
      case 'appointment':
        if (window.App) window.App.switchTab('bookings');
        this.processVoiceQuery('Book an appointment', 1.0);
        break;
      case 'medicines':
        if (window.App) window.App.switchTab('prescriptions');
        this.processVoiceQuery('Show my medicines', 1.0);
        break;
      case 'reports':
        if (window.App) window.App.switchTab('records');
        this.processVoiceQuery('Show my reports', 1.0);
        break;
      case 'doctor':
        this.processVoiceQuery('Show doctor consultation schedule', 1.0);
        break;
      case 'notifications':
        if (window.App) window.App.switchTab('notifications');
        this.processVoiceQuery('Read my notifications', 1.0);
        break;
      case 'emergency':
        this.processVoiceQuery('Emergency medical help', 1.0);
        break;
    }
  }
};

window.VoiceAIEngine = VoiceAIEngine;
document.addEventListener('DOMContentLoaded', () => {
  VoiceAIEngine.init();
});
