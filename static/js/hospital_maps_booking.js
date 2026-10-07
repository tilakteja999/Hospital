/**
 * Swasthya Setu — Hospital Maps, Geolocation & Specialist Booking Engine
 * Government of India Health Portal
 */

(function () {
  'use strict';

  // State Management
  const state = {
    userLat: 16.2354, // Default Narasaraopet, AP
    userLng: 80.0494,
    userAddress: 'Narasaraopet, Palnadu District, Andhra Pradesh - 522601',
    userCity: 'Narasaraopet',
    userPincode: '522601',
    userState: 'Andhra Pradesh',
    userDistrict: 'Palnadu District',
    hasGpsPermission: false,
    map: null,
    markers: [],
    userMarker: null,
    hospitals: [],
    selectedHospital: null,
    selectedSpecialty: '',
    selectedDoctor: null,
    selectedDate: new Date().toISOString().split('T')[0],
    selectedSlot: '09:30 AM - 10:00 AM'
  };

  // DOM Loaded
  document.addEventListener('DOMContentLoaded', () => {
    initDefaultDate();
    initEventListeners();
    initLeafletMap();
    autoDetectLocation(false);
  });

  function initDefaultDate() {
    const dateInput = document.getElementById('booking-date-input');
    if (dateInput) {
      const todayStr = new Date().toISOString().split('T')[0];
      dateInput.value = todayStr;
      dateInput.min = todayStr;
      state.selectedDate = todayStr;
    }
  }

  function initEventListeners() {
    // Current Location button
    const btnUseLoc = document.getElementById('btn-use-current-location');
    if (btnUseLoc) {
      btnUseLoc.addEventListener('click', () => autoDetectLocation(true));
    }

    // Toggle Manual Location Panel
    const btnToggleManual = document.getElementById('btn-toggle-manual-location');
    const manualPanel = document.getElementById('manual-location-panel');
    if (btnToggleManual && manualPanel) {
      btnToggleManual.addEventListener('click', () => {
        const isHidden = manualPanel.style.display === 'none';
        manualPanel.style.display = isHidden ? 'block' : 'none';
      });
    }

    // Manual Search Apply
    const btnApplyManual = document.getElementById('btn-apply-manual-location');
    if (btnApplyManual) {
      btnApplyManual.addEventListener('click', handleManualLocationApply);
    }

    // Enter Location from Denied Banner
    const btnEnterManualDenied = document.getElementById('btn-enter-location-manual');
    if (btnEnterManualDenied && manualPanel) {
      btnEnterManualDenied.addEventListener('click', () => {
        manualPanel.style.display = 'block';
        document.getElementById('manual-location-input')?.focus();
      });
    }

    // Quick Chip Clicks
    document.querySelectorAll('.btn-chip').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const loc = e.target.getAttribute('data-loc');
        if (loc) {
          const parts = loc.split(',');
          const cityPart = parts[0].trim();
          const pinPart = parts[1] ? parts[1].trim() : '';
          document.getElementById('manual-location-input').value = cityPart;
          document.getElementById('manual-pincode-input').value = pinPart;
          handleManualLocationApply();
        }
      });
    });

    // Find Nearest Hospital Button
    const btnNearest = document.getElementById('btn-find-nearest-hospital');
    if (btnNearest) {
      btnNearest.addEventListener('click', () => {
        autoDetectLocation(true, true);
      });
    }

    // Hospital Select Change
    const hospSelect = document.getElementById('booking-hospital-select');
    if (hospSelect) {
      hospSelect.addEventListener('change', (e) => {
        const hospId = e.target.value;
        onHospitalSelectChange(hospId);
      });
    }

    // Specialty Select Change
    const specSelect = document.getElementById('booking-specialty-select');
    if (specSelect) {
      specSelect.addEventListener('change', (e) => {
        state.selectedSpecialty = e.target.value;
        loadDoctorsForSelection();
      });
    }

    // Doctor Select Change
    const docSelect = document.getElementById('booking-doctor-select');
    if (docSelect) {
      docSelect.addEventListener('change', (e) => {
        state.selectedDoctor = e.target.value;
        loadAvailableSlots();
      });
    }

    // Date Input Change
    const dateInput = document.getElementById('booking-date-input');
    if (dateInput) {
      dateInput.addEventListener('change', (e) => {
        state.selectedDate = e.target.value;
        loadAvailableSlots();
      });
    }

    // Slot Select Change
    const slotSelect = document.getElementById('booking-slot-select');
    if (slotSelect) {
      slotSelect.addEventListener('change', (e) => {
        state.selectedSlot = e.target.value;
      });
    }

    // Doctor Search Button & Input
    const btnDocSearch = document.getElementById('btn-do-doctor-search');
    const docSearchInput = document.getElementById('doctor-search-input');
    if (btnDocSearch && docSearchInput) {
      btnDocSearch.addEventListener('click', performDoctorSearch);
      docSearchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performDoctorSearch();
      });
    }

    // Check & Book Appointment Button
    const btnBook = document.getElementById('btn-check-book-appointment');
    if (btnBook) {
      btnBook.addEventListener('click', openBookingConfirmationModal);
    }

    // Final Confirm Booking Button inside Modal
    const btnFinalConfirm = document.getElementById('btn-final-confirm-booking');
    if (btnFinalConfirm) {
      btnFinalConfirm.addEventListener('click', executeBookingCreation);
    }
  }

  // Initialize Leaflet Map
  function initLeafletMap() {
    const container = document.getElementById('booking-hospital-map');
    if (!container || typeof L === 'undefined') return;

    state.map = L.map('booking-hospital-map', {
      zoomControl: true,
      attributionControl: false
    }).setView([state.userLat, state.userLng], 12);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19
    }).addTo(state.map);

    // Initial User Marker
    addUserMarker(state.userLat, state.userLng, state.userAddress);
  }

  function addUserMarker(lat, lng, label) {
    if (!state.map) return;
    if (state.userMarker) {
      state.map.removeLayer(state.userMarker);
    }

    const blueDotIcon = L.divIcon({
      className: 'custom-user-marker',
      html: `<div style="background:#0284c7; width:18px; height:18px; border-radius:50%; border:3px solid #ffffff; box-shadow:0 0 10px rgba(2,132,199,0.8);"></div>`,
      iconSize: [18, 18],
      iconAnchor: [9, 9]
    });

    state.userMarker = L.marker([lat, lng], { icon: blueDotIcon }).addTo(state.map);
    state.userMarker.bindPopup(`<b>📍 Your Location</b><br>${label}`).openPopup();
  }

  // Automatic Geolocation Detection
  function autoDetectLocation(userRequested = false, isNearestTrigger = false) {
    const deniedBanner = document.getElementById('location-denied-alert');
    if (deniedBanner) deniedBanner.style.display = 'none';

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          state.hasGpsPermission = true;
          state.userLat = position.coords.latitude;
          state.userLng = position.coords.longitude;

          // Reverse Geocode
          fetch(`/api/geocode/reverse/?lat=${state.userLat}&lng=${state.userLng}`)
            .then(res => res.json())
            .then(data => {
              if (data.success && data.location) {
                const loc = data.location;
                state.userAddress = loc.address;
                state.userCity = loc.city;
                state.userState = loc.state;
                state.userDistrict = loc.district;
                state.userPincode = loc.pincode;

                updateLocationDisplayUI(loc.address, loc.pincode, 'GPS Geolocation Active');
                addUserMarker(state.userLat, state.userLng, loc.address);
                fetchNearbyHospitals(state.userLat, state.userLng, loc.city, loc.pincode, isNearestTrigger);
              }
            })
            .catch(() => {
              fetchNearbyHospitals(state.userLat, state.userLng, state.userCity, state.userPincode, isNearestTrigger);
            });
        },
        (error) => {
          console.warn('Geolocation permission denied or unavailable:', error.message);
          state.hasGpsPermission = false;
          if (deniedBanner && userRequested) {
            deniedBanner.style.display = 'block';
          }
          // Fallback fetch with default city/pincode
          fetchNearbyHospitals(state.userLat, state.userLng, state.userCity, state.userPincode, isNearestTrigger);
        },
        { timeout: 8000, maximumAge: 60000 }
      );
    } else {
      if (deniedBanner && userRequested) deniedBanner.style.display = 'block';
      fetchNearbyHospitals(state.userLat, state.userLng, state.userCity, state.userPincode, isNearestTrigger);
    }
  }

  function handleManualLocationApply() {
    const locInput = document.getElementById('manual-location-input')?.value.trim();
    const pinInput = document.getElementById('manual-pincode-input')?.value.trim();

    if (!locInput && !pinInput) return;

    fetch(`/api/hospitals/nearby/?city=${encodeURIComponent(locInput)}&pincode=${encodeURIComponent(pinInput)}&q=${encodeURIComponent(locInput)}`)
      .then(res => res.json())
      .then(data => {
        if (data.success && data.hospitals.length > 0) {
          const first = data.hospitals[0];
          state.userCity = first.city;
          state.userPincode = first.pincode || pinInput || '522601';
          state.userDistrict = first.district;
          state.userAddress = `${first.area_name || first.city}, ${first.district || first.state} - ${state.userPincode}`;

          if (first.latitude && first.longitude) {
            state.userLat = first.latitude;
            state.userLng = first.longitude;
            addUserMarker(state.userLat, state.userLng, state.userAddress);
          }

          updateLocationDisplayUI(state.userAddress, state.userPincode, 'Manual Search Active');
          renderNearbyHospitals(data.hospitals);
          renderHospitalMapMarkers(data.hospitals);

          const panel = document.getElementById('manual-location-panel');
          if (panel) panel.style.display = 'none';
        } else {
          alert('No hospitals found for this location/pincode. Showing default regional facilities.');
          fetchNearbyHospitals(state.userLat, state.userLng, 'Narasaraopet', '522601', false);
        }
      });
  }

  function updateLocationDisplayUI(address, pincode, sourceLabel) {
    const addrEl = document.getElementById('loc-display-address');
    const pinEl = document.getElementById('loc-display-pincode');
    const subEl = document.getElementById('loc-display-subtext');
    const step1El = document.getElementById('step1-location-display');

    if (addrEl) addrEl.textContent = address;
    if (pinEl) pinEl.textContent = `PIN: ${pincode}`;
    if (subEl) subEl.innerHTML = `<span>${sourceLabel}</span> · <span>PIN: ${pincode}</span>`;
    if (step1El) step1El.textContent = address;
  }

  // Fetch Nearby Hospitals from API
  function fetchNearbyHospitals(lat, lng, city, pincode, isNearestTrigger = false) {
    let url = `/api/hospitals/nearby/?lat=${lat}&lng=${lng}`;
    if (city) url += `&city=${encodeURIComponent(city)}`;
    if (pincode) url += `&pincode=${encodeURIComponent(pincode)}`;

    fetch(url)
      .then(res => res.json())
      .then(data => {
        if (data.success && data.hospitals) {
          state.hospitals = data.hospitals;
          renderNearbyHospitals(data.hospitals);
          renderHospitalMapMarkers(data.hospitals);
          updateHospitalSelectDropdown(data.hospitals);

          if (isNearestTrigger && data.hospitals.length > 0) {
            const nearest = data.hospitals[0];
            if (state.map && nearest.latitude && nearest.longitude) {
              state.map.setView([nearest.latitude, nearest.longitude], 14);
            }
          }
        }
      })
      .catch(err => console.error('Failed to fetch nearby hospitals:', err));
  }

  // Render Hospital Map Markers
  function renderHospitalMapMarkers(hospitals) {
    if (!state.map) return;

    // Clear old hospital markers
    state.markers.forEach(m => state.map.removeLayer(m));
    state.markers = [];

    const redCrossIcon = L.divIcon({
      className: 'custom-hosp-marker',
      html: `<div style="background:#e63946; color:#ffffff; font-weight:800; font-size:11px; padding:4px 8px; border-radius:12px; border:2px solid #ffffff; box-shadow:0 3px 8px rgba(0,0,0,0.3); display:flex; align-items:center; gap:4px;">🏥 Hosp</div>`,
      iconSize: [60, 24],
      iconAnchor: [30, 12]
    });

    hospitals.forEach(h => {
      if (h.latitude && h.longitude) {
        const marker = L.marker([h.latitude, h.longitude], { icon: redCrossIcon }).addTo(state.map);
        
        const popupContent = `
          <div style="font-family:sans-serif; width:220px;">
            <strong style="color:#0369a1; font-size:0.95rem;">${h.name}</strong><br>
            <span style="font-size:0.78rem; color:#64748b;">${h.facility_type}</span><br>
            <span style="font-size:0.8rem; color:#16a34a; font-weight:700;">${h.distance_display}</span><br>
            <span style="font-size:0.75rem; color:#475569;">${h.address}</span>
            <div style="display:flex; gap:6px; margin-top:8px;">
              <button onclick="window.AppBooking.openHospitalDetail(${h.id})" style="background:#0284c7; color:#fff; border:none; padding:4px 8px; border-radius:4px; font-size:0.75rem; cursor:pointer;">View Hospital</button>
              <button onclick="window.AppBooking.selectHospitalForBooking(${h.id})" style="background:#10b981; color:#fff; border:none; padding:4px 8px; border-radius:4px; font-size:0.75rem; cursor:pointer;">Book</button>
            </div>
          </div>
        `;
        marker.bindPopup(popupContent);
        state.markers.push(marker);
      }
    });

    if (hospitals.length > 0 && state.map) {
      const group = L.featureGroup(state.markers.concat(state.userMarker ? [state.userMarker] : []));
      state.map.fitBounds(group.getBounds().pad(0.1));
    }
  }

  // Render Nearby Hospitals Cards in Right Panel
  function renderNearbyHospitals(hospitals) {
    const container = document.getElementById('nearby-hospitals-container');
    const badge = document.getElementById('nearby-hospitals-count-badge');

    if (badge) badge.textContent = `${hospitals.length} Facilities`;
    if (!container) return;

    if (hospitals.length === 0) {
      container.innerHTML = `
        <div style="text-align:center; padding:20px; color:#64748b;">
          <p>No hospitals were found in this area.</p>
          <small>Try another pincode, nearby city, or different area.</small>
        </div>
      `;
      return;
    }

    let html = '';
    hospitals.forEach(h => {
      const specsList = (h.specialties && h.specialties.length > 0) 
        ? h.specialties.slice(0, 4).join(' · ') 
        : 'General Medicine · Pediatrics · Orthopedics';

      html += `
        <div class="hospital-card-item" id="hosp-card-${h.id}" style="border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px; background: #ffffff; box-shadow: 0 2px 6px rgba(0,0,0,0.03);">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
            <div>
              <strong style="font-size: 0.98rem; color: #0f172a; display: block;">${h.name}</strong>
              <span style="font-size: 0.78rem; color: #64748b; font-weight: 600;">🏥 ${h.facility_type}</span>
            </div>
            <span class="badge-distance" style="background: #dbeafe; color: #1e40af; font-size: 0.75rem; font-weight: 700; padding: 4px 8px; border-radius: 6px; white-space: nowrap;">
              ${h.distance_display}
            </span>
          </div>

          <div style="font-size: 0.8rem; color: #475569; margin: 8px 0 6px 0;">
            📍 ${h.address}
          </div>

          <div style="font-size: 0.76rem; color: #0369a1; font-weight: 600; margin-bottom: 8px;">
            Specialties: ${specsList}
          </div>

          <div style="display: flex; gap: 8px; margin-top: 10px;">
            <button type="button" onclick="window.AppBooking.openHospitalDetail(${h.id})" class="btn btn-sm btn-outline" style="font-size: 0.76rem; padding: 5px 10px; border-radius: 6px;">
              🗺️ View Map & Details
            </button>
            <button type="button" onclick="window.AppBooking.selectHospitalForBooking(${h.id})" class="btn btn-sm btn-primary" style="font-size: 0.76rem; padding: 5px 10px; border-radius: 6px; background: #0284c7; border: none;">
              📅 Book Appointment
            </button>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  }

  // Update Hospital Select Dropdown in Form
  function updateHospitalSelectDropdown(hospitals) {
    const select = document.getElementById('booking-hospital-select');
    if (!select) return;

    let html = '<option value="">-- Select Hospital --</option>';
    hospitals.forEach(h => {
      const distTag = h.distance_km ? ` (${h.distance_km} km)` : '';
      html += `<option value="${h.id}" data-lat="${h.latitude}" data-lng="${h.longitude}">🏥 ${h.name}${distTag}</option>`;
    });
    select.innerHTML = html;
  }

  function onHospitalSelectChange(hospId) {
    if (!hospId) {
      state.selectedHospital = null;
      loadDoctorsForSelection();
      return;
    }

    const hosp = state.hospitals.find(h => h.id == hospId);
    state.selectedHospital = hosp;

    if (hosp && state.map && hosp.latitude && hosp.longitude) {
      state.map.setView([hosp.latitude, hosp.longitude], 15);
    }

    loadDoctorsForSelection();
  }

  // Load Doctors for Selection
  function loadDoctorsForSelection() {
    const docSelect = document.getElementById('booking-doctor-select');
    if (!docSelect) return;

    const hospId = state.selectedHospital ? state.selectedHospital.id : '';
    const specName = state.selectedSpecialty || '';

    let url = `/api/doctors/?status=ACTIVE`;
    if (hospId) url += `&hospital_id=${hospId}`;
    if (specName) url += `&specialty=${encodeURIComponent(specName)}`;

    docSelect.innerHTML = '<option value="">Loading available doctors...</option>';

    fetch(url)
      .then(res => res.json())
      .then(data => {
        if (data.success && data.doctors && data.doctors.length > 0) {
          let html = '<option value="">-- Choose Specialist Doctor --</option>';
          data.doctors.forEach(d => {
            html += `<option value="${d.id}">👨‍⚕️ ${d.name} (${d.specialty || d.department}) - ${d.qualification}</option>`;
          });
          docSelect.innerHTML = html;
        } else {
          docSelect.innerHTML = '<option value="">No doctors available for this selection</option>';
        }
      });
  }

  // Load Available Time Slots
  function loadAvailableSlots() {
    const docId = document.getElementById('booking-doctor-select')?.value;
    const dateVal = document.getElementById('booking-date-input')?.value;
    const slotSelect = document.getElementById('booking-slot-select');

    if (!docId || !dateVal || !slotSelect) return;

    fetch(`/api/appointments/slots/?doctor_id=${docId}&date=${dateVal}`)
      .then(res => res.json())
      .then(data => {
        if (data.success && data.slots) {
          let html = '';
          data.slots.forEach(s => {
            if (s.available) {
              html += `<option value="${s.slot}">${s.slot}</option>`;
            } else {
              html += `<option value="${s.slot}" disabled style="color:#94a3b8;">${s.slot} (Fully Booked)</option>`;
            }
          });
          slotSelect.innerHTML = html || '<option value="">No slots available</option>';
          state.selectedSlot = slotSelect.value;
        }
      });
  }

  // Perform Doctor Search
  function performDoctorSearch() {
    const q = document.getElementById('doctor-search-input')?.value.trim();
    const container = document.getElementById('doctor-search-results');
    if (!container || !q) return;

    container.innerHTML = '<div style="text-align:center; padding:12px; color:#64748b;">Searching doctors...</div>';

    fetch(`/api/doctors/search/?q=${encodeURIComponent(q)}`)
      .then(res => res.json())
      .then(data => {
        if (data.success && data.doctors.length > 0) {
          let html = '';
          data.doctors.forEach(d => {
            html += `
              <div style="border:1px solid #e2e8f0; border-radius:8px; padding:10px; background:#f8fafc;">
                <strong style="color:#0f172a; font-size:0.9rem;">👨‍⚕️ ${d.name}</strong><br>
                <span style="font-size:0.78rem; color:#0284c7; font-weight:600;">${d.specialty || d.department}</span> · <span style="font-size:0.75rem; color:#64748b;">${d.qualification}</span><br>
                <span style="font-size:0.76rem; color:#475569;">🏥 ${d.hospital_name} (${d.hospital_city})</span>
                <div style="margin-top:6px;">
                  <button type="button" onclick="window.AppBooking.quickBookDoctor(${d.hospital_id}, '${d.specialty || d.department}', ${d.id})" class="btn btn-sm btn-primary" style="font-size:0.75rem; padding:4px 10px; background:#0369a1; border:none;">Book</button>
                </div>
              </div>
            `;
          });
          container.innerHTML = html;
        } else {
          container.innerHTML = '<div style="text-align:center; padding:12px; color:#64748b;">No doctors found matching your query.</div>';
        }
      });
  }

  // Quick Book Doctor helper
  function quickBookDoctor(hospId, specName, docId) {
    const hospSelect = document.getElementById('booking-hospital-select');
    const specSelect = document.getElementById('booking-specialty-select');

    if (hospSelect) hospSelect.value = hospId;
    if (specSelect) specSelect.value = specName;

    onHospitalSelectChange(hospId);

    setTimeout(() => {
      const docSelect = document.getElementById('booking-doctor-select');
      if (docSelect) {
        docSelect.value = docId;
        loadAvailableSlots();
      }
      document.getElementById('appointment-step-form')?.scrollIntoView({ behavior: 'smooth' });
    }, 400);
  }

  // Hospital Detail Modal
  function openHospitalDetail(hospId) {
    fetch(`/api/hospitals/${hospId}/`)
      .then(res => res.json())
      .then(data => {
        if (data.success && data.hospital) {
          const h = data.hospital;
          document.getElementById('modal-hosp-name').textContent = h.name;
          document.getElementById('modal-hosp-type').textContent = `${h.facility_type} · ${h.city}`;
          document.getElementById('modal-hosp-address').textContent = `${h.address}, ${h.city}, ${h.state} - ${h.pincode}`;
          document.getElementById('modal-hosp-phone').textContent = h.contact_phone;
          document.getElementById('modal-hosp-emergency').textContent = h.emergency ? '24/7 Emergency Available' : 'Standard OPD';
          document.getElementById('modal-hosp-directions-btn').href = h.directions_url;

          const specContainer = document.getElementById('modal-hosp-specialties');
          if (specContainer) {
            let specHtml = '';
            (h.specialties || []).forEach(s => {
              specHtml += `<span style="background:#e0f2fe; color:#0369a1; font-size:0.75rem; font-weight:700; padding:3px 8px; border-radius:12px;">${s}</span>`;
            });
            specContainer.innerHTML = specHtml || '<span>General Medicine</span>';
          }

          const docContainer = document.getElementById('modal-hosp-doctors');
          if (docContainer) {
            let docHtml = '';
            (h.doctors || []).forEach(d => {
              docHtml += `
                <div style="padding:6px 0; border-bottom:1px solid #f1f5f9;">
                  <strong>👨‍⚕️ ${d.name}</strong> (${d.specialty})<br>
                  <small style="color:#64748b;">${d.qualification} · ${d.experience} · Room: ${d.room}</small>
                </div>
              `;
            });
            docContainer.innerHTML = docHtml || '<div>Contact hospital front desk for daily doctor roster.</div>';
          }

          const bookBtn = document.getElementById('modal-hosp-book-btn');
          if (bookBtn) {
            bookBtn.onclick = () => {
              document.getElementById('modal-hospital-detail').style.display = 'none';
              selectHospitalForBooking(h.id);
            };
          }

          document.getElementById('modal-hospital-detail').style.display = 'flex';
        }
      });
  }

  function selectHospitalForBooking(hospId) {
    const hospSelect = document.getElementById('booking-hospital-select');
    if (hospSelect) {
      hospSelect.value = hospId;
      onHospitalSelectChange(hospId);
      document.getElementById('appointment-step-form')?.scrollIntoView({ behavior: 'smooth' });
    }
  }

  // Open Booking Confirmation Modal
  function openBookingConfirmationModal() {
    const hospSelect = document.getElementById('booking-hospital-select');
    const specSelect = document.getElementById('booking-specialty-select');
    const docSelect = document.getElementById('booking-doctor-select');
    const dateInput = document.getElementById('booking-date-input');
    const slotSelect = document.getElementById('booking-slot-select');

    if (!hospSelect?.value || !docSelect?.value || !dateInput?.value) {
      alert('Please select a Hospital, Specialist Doctor, and Date before proceeding.');
      return;
    }

    const hospText = hospSelect.options[hospSelect.selectedIndex]?.text || '';
    const specText = specSelect.value || 'General Medicine';
    const docText = docSelect.options[docSelect.selectedIndex]?.text || '';
    const dateVal = dateInput.value;
    const slotVal = slotSelect.value;

    document.getElementById('confirm-hosp-name').textContent = hospText;
    document.getElementById('confirm-specialty').textContent = specText;
    document.getElementById('confirm-doctor').textContent = docText;
    document.getElementById('confirm-date').textContent = formatDateDisplay(dateVal);
    document.getElementById('confirm-time').textContent = slotVal;
    document.getElementById('confirm-location').textContent = state.userAddress;

    document.getElementById('modal-booking-confirmation').style.display = 'flex';
  }

  function formatDateDisplay(dateStr) {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-IN', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' });
    } catch {
      return dateStr;
    }
  }

  // Execute Booking Creation via API
  function executeBookingCreation() {
    const hospId = document.getElementById('booking-hospital-select')?.value;
    const docId = document.getElementById('booking-doctor-select')?.value;
    const dateVal = document.getElementById('booking-date-input')?.value;
    const slotVal = document.getElementById('booking-slot-select')?.value;
    const symptoms = document.getElementById('booking-symptoms-input')?.value || 'General Consultation';

    const payload = {
      hospital_id: hospId,
      doctor_id: docId,
      date: dateVal,
      time_slot: slotVal,
      symptoms: symptoms
    };

    fetch('/api/appointments/check-and-book/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: JSON.stringify(payload)
    })
      .then(res => res.json())
      .then(data => {
        document.getElementById('modal-booking-confirmation').style.display = 'none';

        if (data.success && data.booking) {
          const b = data.booking;
          alert(`✅ Appointment Booked Successfully!\n\nReference ID: ${b.reference}\nOPD Token: #${b.token_number}\nHospital: ${b.hospital_name}\nDoctor: ${b.doctor_name}\nDate: ${b.date}\nTime: ${b.time_slot}`);
          window.location.reload();
        } else {
          alert(`⚠️ ${data.title || 'Booking Failed'}: ${data.message || 'Unable to book appointment.'}`);
        }
      })
      .catch(err => {
        document.getElementById('modal-booking-confirmation').style.display = 'none';
        alert('An error occurred while creating appointment. Please try again.');
      });
  }

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  // Export global API object
  window.AppBooking = {
    autoDetectLocation,
    openHospitalDetail,
    selectHospitalForBooking,
    quickBookDoctor
  };

})();
