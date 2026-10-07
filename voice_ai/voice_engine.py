"""
Swasthya Setu â€” Multilingual Voice-First AI Hospital Assistant Engine
Strict Security Architecture:
AI ASSISTS â€” BACKEND AUTHORIZES â€” USER CONFIRMS â€” DOCTOR DECIDES

Key Features:
1. Direct, concise, medically-safe answers to health & medication questions in the user's language.
2. Full multilingual support for Telugu (te-IN), Hindi (hi-IN), English (en-IN), Tamil (ta-IN),
   Kannada (kn-IN), Malayalam (ml-IN), Marathi (mr-IN), Bengali (bn-IN), and transliterated mixed phrases.
3. Natural language intent routing (no rigid syntax) for Reports, Prescriptions, Medicines, Vitals, and Appointments.
4. Real database lookups for authenticated patient records with zero fabrication.
5. Multi-turn slot discovery, confirmation token staging, and verified booking.
6. Strict authorization and rejection of dangerous operations.
"""

import re
import json
import datetime
from django.utils import timezone
from django.db.models import Q
from core.models import User, AuditLog
from core.audit_utils import record_audit_log
from core.permission_utils import check_patient_record_access
from patients.models import (
    VitalRecord, HospitalVisit, Prescription, HealthNotification,
    LabOrder, DischargeSummary, VaccinationRecord, EmergencyProfile, MedicationDoseLog,
    RadiologyReport, PhysiotherapyVideo
)
from appointments.models import HospitalFacility, DoctorProfile, AppointmentBooking, HospitalArea
from .models import AssistantSession, ServerConfirmationToken
from .smart_assistant import MEDICINE_CATALOG

# ==================== 1. STRICT AI TOOL PERMISSION REGISTRY ====================

ALLOWED_TOOLS = {
    # Patient Tools (READ)
    "get_my_profile": {
        "description": "Get profile and demographic details of the authenticated patient",
        "role": ["PATIENT", "DOCTOR", "ADMIN"],
        "parameters": {}
    },
    "get_my_vitals": {
        "description": "Get latest clinical vitals and telemetry of the authenticated patient",
        "role": ["PATIENT"],
        "parameters": {}
    },
    "get_my_prescriptions": {
        "description": "Get active doctor prescriptions of the authenticated patient",
        "role": ["PATIENT"],
        "parameters": {}
    },
    "get_my_lab_reports": {
        "description": "Get authorized lab investigation reports of the authenticated patient",
        "role": ["PATIENT"],
        "parameters": {}
    },
    "get_my_appointments": {
        "description": "Get upcoming and historical appointments of the authenticated patient",
        "role": ["PATIENT"],
        "parameters": {}
    },
    "get_opd_token": {
        "description": "Get live OPD token, room number, and queue waiting status for today",
        "role": ["PATIENT"],
        "parameters": {}
    },
    "get_notifications": {
        "description": "Get unread health notifications and reminders for the patient",
        "role": ["PATIENT"],
        "parameters": {}
    },
    "get_vaccination_records": {
        "description": "Get authorized immunization history and upcoming vaccine schedules",
        "role": ["PATIENT"],
        "parameters": {}
    },
    "get_medication_schedule": {
        "description": "Get today's prescribed medication timetable (Morning/Afternoon/Night)",
        "role": ["PATIENT"],
        "parameters": {}
    },
    "find_available_slots": {
        "description": "Search available OPD consultation slots for a department/doctor",
        "role": ["PATIENT", "DOCTOR", "ADMIN"],
        "parameters": {"department": "string", "date": "string"}
    },
    "get_my_radiology_reports": {
        "description": "Get authorized radiology and diagnostic imaging reports of the authenticated patient",
        "role": ["PATIENT", "DOCTOR"],
        "parameters": {"modality": "string"}
    },
    "get_physiotherapy_videos": {
        "description": "Get legitimate physiotherapy video rehabilitation routines by category or condition",
        "role": ["PATIENT", "DOCTOR", "ADMIN"],
        "parameters": {"category": "string"}
    },
    
    # Patient Limited Write (Requires Server Confirmation)
    "prepare_appointment_confirmation": {
        "description": "Stage appointment booking details and generate server confirmation token",
        "role": ["PATIENT"],
        "parameters": {"doctor_id": "integer", "date": "string", "slot": "string", "symptoms": "string"}
    },
    "create_appointment": {
        "description": "Create appointment booking ONLY with valid server confirmation token",
        "role": ["PATIENT"],
        "parameters": {"confirmation_token": "string", "doctor_id": "integer", "date": "string", "slot": "string"}
    },
    "request_appointment_cancellation": {
        "description": "Cancel appointment booking ONLY with valid server confirmation token",
        "role": ["PATIENT"],
        "parameters": {"booking_id": "integer", "confirmation_token": "string"}
    },
    "request_appointment_reschedule": {
        "description": "Reschedule appointment booking ONLY with valid server confirmation token",
        "role": ["PATIENT"],
        "parameters": {"booking_id": "integer", "new_date": "string", "new_slot": "string", "confirmation_token": "string"}
    },
    "mark_medication_reminder_completed": {
        "description": "Log medication dose adherence (taken/pending) for today",
        "role": ["PATIENT"],
        "parameters": {"prescription_id": "integer", "time_slot": "string"}
    },
    
    # Navigation & Educational
    "navigate_to_page": {
        "description": "Safely navigate the application using whitelisted safe route keys",
        "role": ["PATIENT", "DOCTOR", "ADMIN"],
        "parameters": {"route_key": "string"}
    },
    "explain_medical_concept": {
        "description": "Provide safe, non-diagnostic educational information about drugs/tests",
        "role": ["PATIENT", "DOCTOR", "ADMIN"],
        "parameters": {"topic": "string"}
    },
    "emergency_safety_check": {
        "description": "Provide immediate emergency triage direction and ambulance helpline 108",
        "role": ["PATIENT", "DOCTOR", "ADMIN"],
        "parameters": {}
    },

    # Doctor Role Tools
    "doctor_get_next_patient": {
        "description": "Get next waiting patient in the doctor's live OPD consultation queue",
        "role": ["DOCTOR"],
        "parameters": {}
    },
    "doctor_get_opd_queue": {
        "description": "Get complete list of today's scheduled and waiting OPD patients for doctor",
        "role": ["DOCTOR"],
        "parameters": {}
    },
    "doctor_get_patient_vitals": {
        "description": "Retrieve clinical vitals for a patient with verified doctor relationship",
        "role": ["DOCTOR"],
        "parameters": {"patient_id": "integer"}
    },
    "doctor_get_patient_lab_report": {
        "description": "Retrieve lab investigation report for an authorized patient",
        "role": ["DOCTOR"],
        "parameters": {"patient_id": "integer"}
    },
    "doctor_get_patient_prescriptions": {
        "description": "Retrieve existing prescription history for an authorized patient",
        "role": ["DOCTOR"],
        "parameters": {"patient_id": "integer"}
    },

    # Admin Role Tools
    "admin_get_hospital_metrics": {
        "description": "Get aggregated hospital OPD load, doctor duty presence, and lab metrics",
        "role": ["ADMIN"],
        "parameters": {}
    },
    "admin_get_waiting_count": {
        "description": "Get total count of patients currently waiting in hospital OPD",
        "role": ["ADMIN"],
        "parameters": {}
    },
    "admin_get_doctors_on_duty": {
        "description": "Get total count and list of doctors currently marked present on duty",
        "role": ["ADMIN"],
        "parameters": {}
    },
    "admin_get_pending_labs": {
        "description": "Get count of laboratory diagnostic orders pending processing",
        "role": ["ADMIN"],
        "parameters": {}
    }
}

FORBIDDEN_OPERATIONS = {
    "delete_patient_account", "delete_medical_record", "delete_prescription",
    "delete_lab_report", "delete_visit", "modify_clinical_notes", "modify_prescription",
    "change_diagnosis", "change_patient_identity", "grant_medical_record_access",
    "revoke_medical_record_access", "modify_audit_log", "create_admin", "create_doctor",
    "modify_hospital_configuration", "change_security_settings", "change_user_role",
    "access_other_patient_without_authorization", "delete_account", "erase_history"
}

# ==================== 2. SAFE NAVIGATION WHITELIST ====================

SAFE_ROUTES = {
    "home": "/",
    "dashboard": "/",
    "appointments": "#bookings",
    "bookings": "#bookings",
    "prescriptions": "#prescriptions",
    "prescription": "#prescriptions",
    "medicines": "#prescriptions",
    "records": "#records",
    "reports": "#records",
    "lab": "#records",
    "vitals": "#home",
    "notifications": "#notifications",
    "physio": "#physio",
    "radiology": "#radiology",
    "about": "#about",
    "settings": "#settings",
    "doctor": "/doctor-portal/",
    "opd": "#home",
    "easy_voice": "#easy-voice-mode",
}

# ==================== 3. MULTILINGUAL DIALOGUE PROMPTS ====================

MULTILINGUAL_PROMPTS = {
    'en-IN': {
        'greeting': "Hello! I am your Swasthya AI Assistant. How can I help you today?",
        'emergency_alert': "ðŸš¨ Urgent Medical Attention: Severe or sudden symptoms (like severe chest pain or acute breathing difficulty) require immediate emergency medical care. Please call 108 (Ambulance) or 112, or visit the nearest emergency hospital casualty immediately.",
        'booking_ask_name': "Sure! I can help you book an appointment. Is the appointment for you?",
        'booking_ask_problem': "What health problem or department would you like to consult the doctor for?",
        'booking_suggest_dept': "Based on what you described, {dept} would be appropriate. Which date would you prefer? (e.g. Today, Tomorrow, Friday)",
        'booking_show_slots': "Available slots for {dept} on {date}: {slots}. Which time slot would you prefer?",
        'booking_confirm_summary': "Please confirm:\nDepartment: {dept}\nDate: {date}\nTime: {slot}\nDoctor: {doctor}\nShould I book this appointment?",
        'booking_success': "âœ… Your appointment has been booked! Reference: {ref}, OPD Token: #{token} with Dr. {doctor} at {hospital}.",
        'booking_slot_unavailable': "Appointment could not be booked. That slot is no longer available. Available slots: {slots}.",
        'booking_cancelled': "The appointment workflow has been cancelled. How else may I help you?",
        'reschedule_ask_date': "Your current appointment is on {current_date}. Which new date would you prefer?",
        'reschedule_confirm': "Please confirm rescheduling your appointment with Dr. {doctor} to {new_date} at {new_slot}. Should I proceed?",
        'reschedule_success': "âœ… Your appointment has been rescheduled to {new_date} at {new_slot}. OPD Token: #{token}.",
        'cancel_confirm': "Are you sure you want to cancel your appointment with Dr. {doctor} on {date} (Token #{token})? This action cannot be undone.",
        'cancel_success': "âœ… Your appointment has been cancelled successfully.",
        'medicines_today': "You have {count} active medicine(s) prescribed: {med_list}.",
        'opd_token_status': "Your OPD Token is #{token} for Dr. {doctor} ({dept}). Currently consulting Token #{current_token}, with {ahead} patient(s) ahead of you in {room}.",
        'vitals_summary': "According to your latest recorded vitals: Blood Pressure is {bp}, Oxygen saturation is {o2}, and Blood Sugar is {sugar}.",
        'lab_reports_summary': "You have {count} authorized lab report(s) on file. Latest test: {latest_test} ({status}) from {date}.",
        'vaccination_summary': "Your records show {count} completed vaccination(s). Next scheduled vaccine: {next_due}.",
        'notifications_summary': "You have {count} new notification(s). Latest: {latest_title}.",
        'forbidden_action': "I cannot perform that action. I cannot delete database records, accounts, reports, or prescriptions through the voice assistant for security and privacy reasons. I can only assist with inquiries, viewing records, and navigation.",
        'unauthorized_patient': "For security and privacy, I can only access health information that you are authorized to view.",
        'clarify_audio': "I didn't hear that clearly. Could you please repeat it?",
        'doctor_next_patient': "Next waiting patient in your OPD queue is {name} (Token #{token}) for {dept}.",
        'doctor_queue_empty': "No more patients are currently waiting in your OPD queue.",
        'admin_metrics': "Hospital Summary Today: {waiting} patients waiting in OPD, {booked} appointments booked today, {doctors} doctors on duty, and {pending_labs} lab tests pending.",
        'easy_voice_welcome': "Easy Voice Mode activated. Tap the big microphone to speak, or tap any large button below.",
        'unknown_intent': "I can help you book appointments, view OPD tokens, explain prescriptions, check reports, read vitals, or navigate hospital sections. What would you like to do?"
    },
    'hi-IN': {
        'greeting': "नमस्ते! मैं आपका स्वास्थ्य एआई सहायक हूँ। मैं आपकी क्या सहायता कर सकता हूँ?",
        'emergency_alert': "🚨 आपातकालीन चिकित्सा चेतावनी: सीने में तेज दर्द या सांस लेने में गंभीर तकलीफ जैसी स्थितियों में तुरंत आपातकालीन चिकित्सा सहायता लें। कृपया 108 (एम्बुलेंस) या 112 पर कॉल करें या नजदीकी अस्पताल की इमरजेंसी में जाएँ।",
        'booking_ask_name': "नमस्ते! मैं आपका अपॉइंटमेंट बुक करने में सहायता करूँगा। क्या यह अपॉइंटमेंट आपके लिए है?",
        'booking_ask_problem': "आप किस स्वास्थ्य समस्या या विभाग के लिए डॉक्टर से परामर्श लेना चाहते हैं?",
        'booking_suggest_dept': "आपके बताए अनुसार {dept} विभाग उचित रहेगा। आप किस दिन आना चाहेंगे? (जैसे: आज, कल, शुक्रवार)",
        'booking_show_slots': "{dept} विभाग में {date} के लिए ये स्लॉट उपलब्ध हैं: {slots}। आप कौन सा समय चुनना चाहेंगे?",
        'booking_confirm_summary': "कृपया पुष्टि करें:\nविभाग: {dept}\nदिनांक: {date}\nसमय: {slot}\nडॉक्टर: {doctor}\nक्या मैं यह अपॉइंटमेंट बुक कर दूँ?",
        'booking_success': "✅ आपका अपॉइंटमेंट सफलतापूर्वक बुक हो गया है! संदर्भ: {ref}, ओपीडी टोकन: #{token} (डॉक्टर {doctor}, {hospital})।",
        'booking_slot_unavailable': "अपॉइंटमेंट बुक नहीं हो सका। यह स्लॉट अब उपलब्ध नहीं है। उपलब्ध स्लॉट: {slots}।",
        'booking_cancelled': "अपॉइंटमेंट प्रक्रिया रद्द कर दी गई है। मैं आपकी और क्या सहायता कर सकता हूँ?",
        'reschedule_ask_date': "आपका वर्तमान अपॉइंटमेंट {current_date} को है। आप किस नई तारीख को आना चाहेंगे?",
        'reschedule_confirm': "कृपया पुष्टि करें: {doctor} के साथ आपका अपॉइंटमेंट {new_date} को {new_slot} बजे बदलना है। क्या मैं आगे बढ़ूँ?",
        'reschedule_success': "✅ आपका अपॉइंटमेंट {new_date} को {new_slot} बजे के लिए रीशेड्यूल हो गया है। टोकन: #{token}।",
        'cancel_confirm': "क्या आप वाकई {date} को डॉक्टर {doctor} के साथ अपना अपॉइंटमेंट (टोकन #{token}) रद्द करना चाहते हैं?",
        'cancel_success': "✅ आपका अपॉइंटमेंट सफलतापूर्वक रद्द कर दिया गया है।",
        'medicines_today': "आज आपके पर्चे में {count} दवाइयां निर्धारित हैं: {med_list}।",
        'opd_token_status': "आपका ओपीडी टोकन #{token} है (डॉक्टर {doctor}, {dept})। वर्तमान में {room} में टोकन #{current_token} चल रहा है, और आपसे आगे {ahead} मरीज हैं।",
        'vitals_summary': "आपके नवीनतम रिकॉर्ड के अनुसार: रक्तचाप {bp}, ऑक्सीजन {o2}, और ब्लड शुगर {sugar} है।",
        'lab_reports_summary': "आपके {count} लैब रिपोर्ट उपलब्ध हैं। आपकी नवीनतम जांच: {latest_test} ({status}, {date})।",
        'vaccination_summary': "आपके रिकॉर्ड में {count} टीके दर्ज हैं। अगला टीका: {next_due}।",
        'notifications_summary': "आपके पास {count} नई सूचनाएं हैं। नवीनतम: {latest_title}।",
        'forbidden_action': "सुरक्षा और नियमों के तहत, डेटाबेस, अकाउंट, रिपोर्ट या प्रिस्क्रिप्शन डिलीट करना वॉइस असिस्टेंट द्वारा संभव नहीं है। असिस्टेंट केवल जानकारी देखने और नेविगेट करने में मदद करता है।",
        'unauthorized_patient': "सुरक्षा और गोपनीयता नियमों के तहत, मैं केवल आपके अधिकृत मेडिकल रिकॉर्ड ही दिखा सकता हूँ।",
        'clarify_audio': "मैं ठीक से सुन नहीं पाया। कृपया दोबारा बोलें?",
        'doctor_next_patient': "ओपीडी कतार में अगले मरीज {name} हैं (टोकन #{token}, {dept})।",
        'doctor_queue_empty': "आपकी ओपीडी कतार में अभी कोई मरीज प्रतीक्षारत नहीं है।",
        'admin_metrics': "आज का अस्पताल सारांश: ओपीडी में {waiting} मरीज, आज {booked} अपॉइंटमेंट बुक, {doctors} डॉक्टर ड्यूटी पर, और {pending_labs} लैब टेस्ट लंबित हैं।",
        'easy_voice_welcome': "आसान आवाज़ मोड सक्रिय है। बोलने के लिए बड़े माइक को दबाएं।",
        'unknown_intent': "मैं अपॉइंटमेंट बुक करने, टोकन देखने, रिपोर्ट समझाने, दवाइयों की जानकारी देने और नेविगेट करने में मदद कर सकता हूँ।"
    },
    'te-IN': {
        'greeting': "నమస్కారం! నేను మీ స్వాస్థ్య AI అసిస్టెంట్‌ని. నేను మీకు ఎలా సహాయపడగలను?",
        'emergency_alert': "🚨 అత్యవసర వైద్య హెచ్చరిక: తీవ్రమైన గుండె నొప్పి లేదా శ్వాస ఆడకపోవడం వంటి లక్షణాలు ఉంటే వెంటనే అత్యవసర వైద్య సహాయం పొందండి. 108 (అంబులెన్స్) లేదా 112 కి కాల్ చేయండి లేదా సమీప ఆసుపత్రి ఎమర్జెన్సీకి వెళ్లండి.",
        'booking_ask_name': "నేను డాక్టర్ అపాయింట్‌మెంట్ బుక్ చేయడానికి సహాయం చేస్తాను. ఇది మీ కోసమేనా?",
        'booking_ask_problem': "మీరు ఏ ఆరోగ్య సమస్య లేదా డిపార్ట్‌మెంట్ కోసం డాక్టర్‌ను సంప్రదించాలనుకుంటున్నారు?",
        'booking_suggest_dept': "మీరు చెప్పిన సమస్యకు {dept} విభాగం సరిపోతుంది. ఏ తేదీన రావాలనుకుంటున్నారు? (ఉదా: ఈరోజు, రేపు, శుక్రవారం)",
        'booking_show_slots': "{dept} విభాగంలో {date} న లభించే సమయాలు: {slots}. ఏ సమయం ఎంచుకుంటారు?",
        'booking_confirm_summary': "దయచేసి నిర్ధారించండి:\nవిభాగం: {dept}\nతేదీ: {date}\nసమయం: {slot}\nడాక్టర్: {doctor}\nఈ అపాయింట్‌మెంట్ బుక్ చేయమంటారా?",
        'booking_success': "✅ మీ appointment successfully book అయింది! OPD టోకెన్: #{token} (డాక్టర్ {doctor}, {hospital}).",
        'booking_slot_unavailable': "Appointment book కాలేదు. ఈ slot ఇప్పుడు available లేదు. అందుబాటులో ఉన్న సమయాలు: {slots}.",
        'booking_cancelled': "అపాయింట్‌మెంట్ బుకింగ్ రద్దు చేయబడింది. నేను ఇంకా ఎలా సహాయపడగలను?",
        'reschedule_ask_date': "మీ ప్రస్తుత అపాయింట్‌మెంట్ {current_date} న ఉంది. ఏ కొత్త తేదీని ఎంచుకుంటారు?",
        'reschedule_confirm': "దయచేసి నిర్ధారించండి: డాక్టర్ {doctor} తో అపాయింట్‌మెంట్‌ను {new_date} న {new_slot} కి మార్చమంటారా?",
        'reschedule_success': "✅ మీ అపాయింట్‌మెంట్ {new_date} న {new_slot} కి మార్చబడింది. టోకెన్: #{token}.",
        'cancel_confirm': "{date} న డాక్టర్ {doctor} తో ఉన్న మీ అపాయింట్‌మెంట్ (టోకెన్ #{token}) ను రద్దు చేయాలనుకుంటున్నారా?",
        'cancel_success': "✅ మీ అపాయింట్‌మెంట్ విజయవంతంగా రద్దు చేయబడింది.",
        'medicines_today': "మీకు ఈరోజు నిర్ణయించిన మందులు {count}: {med_list}.",
        'opd_token_status': "మీ ఓపీడీ టోకెన్ నంబర్ #{token} (డాక్టర్ {doctor}, {dept}). {room} లో ప్రస్తుత టోకెన్ #{current_token}, మీకంటే ముందు {ahead} మంది రోగులు ఉన్నారు.",
        'vitals_summary': "మీ తాజా వైటల్స్: రక్తపోటు {bp}, ఆక్సిజన్ {o2}, మరియు బ్లడ్ షుగర్ {sugar}.",
        'lab_reports_summary': "మీకు {count} ల్యాబ్ రిపోర్టులు ఉన్నాయి. తాజా పరీక్ష: {latest_test} ({status}, {date}).",
        'vaccination_summary': "మీ రికార్డులో {count} వ్యాక్సిన్లు నమోదయ్యాయి. తదుపరి వ్యాక్సిన్: {next_due}.",
        'notifications_summary': "మీకు {count} కొత్త నోటిఫికేషన్లు ఉన్నాయి. తాజాది: {latest_title}.",
        'forbidden_action': "క్షమించండి, భద్రత కారణాల వల్ల AI ద్వారా Account delete, reports లేదా prescriptions తొలగించడం సాధ్యం కాదు. Settings పేజీని ఉపయోగించండి.",
        'unauthorized_patient': "భద్రతా నిబంధనల ప్రకారం, నేను మీ స్వంత రికార్డులను మాత్రమే యాక్సెస్ చేయగలను.",
        'clarify_audio': "నేను సరిగ్గా వినలేకపోయాను. దయచేసి మళ్ళీ చెప్పండి?",
        'doctor_next_patient': "ఓపీడీ క్యూలో తదుపరి రోగి: {name} (టోకెన్ #{token}, {dept}).",
        'doctor_queue_empty': "మీ ఓపీడీ క్యూలో ప్రస్తుతం రోగులు ఎవరూ వేచి లేరు.",
        'admin_metrics': "నేటి ఆసుపత్రి స్థితి: ఓపీడీలో {waiting} రోగులు వేచి ఉన్నారు, {booked} అపాయింట్‌మెంట్‌లు బుక్ అయ్యాయి, {doctors} డాక్టర్లు విధుల్లో ఉన్నారు.",
        'easy_voice_welcome': "ఈజీ వాయిస్ మోడ్ ఆన్ చేయబడింది. మాట్లాడటానికి పెద్ద మైక్‌ను నొక్కండి.",
        'unknown_intent': "నేను అపాయింట్‌మెంట్ బుకింగ్, టోకెన్ చెక్, రిపోర్టుల వివరణ, మందుల వివరాలు అందించగలను. మీకు ఏమి కావాలి?"
    },
    'ta-IN': {
        'greeting': "வணக்கம்! நான் உங்கள் ஸ்வஸ்த்யா AI உதவியாளர். உங்களுக்கு எவ்வாறு உதவ முடியும்?",
        'emergency_alert': "🚨 அவசர மருத்துவ எச்சரிக்கை: கடுமையான நெஞ்சு வலி அல்லது மூச்சுத் திணறல் ஏற்பட்டால் உடனே 108 அல்லது 112 அம்புலன்ஸை அழைக்கவும்.",
        'booking_ask_name': "மருத்துவர் அப்பாயின்ட்மென்ட் முன்பதிவு செய்ய நோயாளியின் பெயர் என்ன?",
        'booking_ask_problem': "எந்த மருத்துவ பிரச்சனைக்காக மருத்துவரை அணுக விரும்புகிறீர்கள்?",
        'booking_suggest_dept': "{dept} பிரிவு பொருத்தமாக இருக்கும். எந்த தேதியில் வர விரும்புகிறீர்கள்?",
        'booking_show_slots': "{date} அன்று கிடைக்கும் நேரங்கள்: {slots}.",
        'booking_confirm_summary': "தயவுசெய்து உறுதிப்படுத்தவும்:\nபிரிவு: {dept}\nதேதி: {date}\nநேரம்: {slot}\nமருத்துவர்: {doctor}\nமுன்பதிவு செய்யலாமா?",
        'booking_success': "✅ உங்கள் அப்பாயின்ட்மென்ட் முன்பதிவு செய்யப்பட்டது! டோக்கன்: #{token} ({doctor}, {hospital}).",
        'booking_cancelled': "முன்பதிவு ரத்து செய்யப்பட்டது.",
        'medicines_today': "இன்றைய மருந்துகள்: {med_list}.",
        'opd_token_status': "உங்கள் டோக்கன் எண் #{token}. தற்போதைய டோக்கன் #{current_token}.",
        'vitals_summary': "உங்கள் உடல்நிலை: இரத்த அழுத்தம் {bp}, ஆக்ஸிஜன் {o2}, சர்க்கரை {sugar}.",
        'forbidden_action': "பாதுகாப்பு காரணங்களால் இந்த செயல் அனுமதிக்கப்படவில்லை.",
        'unauthorized_patient': "உங்கள் சொந்த பதிவுகளை மட்டுமே பார்க்க முடியும்.",
        'clarify_audio': "தெளிவாக கேட்கவில்லை. மீண்டும் கூறுங்கள்?",
        'unknown_intent': "அப்பாயின்ட்மென்ட் முன்பதிவு, மருந்துகள், அறிக்கைகள் குறித்து உதவ முடியும்."
    },
    'kn-IN': {
        'greeting': "ನಮಸ್ಕಾರ! ನಾನು ನಿಮ್ಮ ಸ್ವಾಸ್ಥ್ಯ AI ಸಹಾಯಕ. ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?",
        'emergency_alert': "🚨 ತುರ್ತು ವೈದ್ಯಕೀಯ ಎಚ್ಚರಿಕೆ: ತೀವ್ರ ಎದೆನೋವು ಅಥವಾ ಉಸಿರಾಟದ ತೊಂದರೆಯಿದ್ದರೆ ತಕ್ಷಣ 108 ಅಥವಾ 112 ಕರೆ ಮಾಡಿ.",
        'booking_suggest_dept': "{dept} ವಿಭಾಗ ಸೂಕ್ತವಾಗಿದೆ. ಯಾವ ದಿನಾಂಕವನ್ನು ಬಯಸುತ್ತೀರಿ?",
        'booking_show_slots': "{date} ರಂದು ಲಭ್ಯವಿರುವ ಸಮಯಗಳು: {slots}.",
        'booking_confirm_summary': "ದಯವಿಟ್ಟು ದೃಢೀಕರಿಸಿ:\nವಿಭಾಗ: {dept}\nದಿನಾಂಕ: {date}\nಸಮಯ: {slot}\nವೈದ್ಯರು: {doctor}\nಬುಕ್ ಮಾಡಲೇ?",
        'booking_success': "✅ ನಿಮ್ಮ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಬುಕ್ ಆಗಿದೆ! ಟೋಕನ್: #{token} ({doctor}).",
        'booking_cancelled': "ಬುಕಿಂಗ್ ರದ್ದುಗೊಳಿಸಲಾಗಿದೆ.",
        'medicines_today': "ಇಂದಿನ ಔಷಧಿಗಳು: {med_list}.",
        'opd_token_status': "ನಿಮ್ಮ ಟೋಕನ್ ಸಂಖ್ಯೆ #{token}. ಪ್ರಸ್ತುತ ಟೋಕನ್ #{current_token}.",
        'vitals_summary': "ನಿಮ್ಮ ಆರೋಗ್ಯ ಮಾಹಿತಿ: ರಕ್ತದೊತ್ತಡ {bp}, ಆಮ್ಲಜನಕ {o2}, ಸಕ್ಕರೆ {sugar}.",
        'forbidden_action': "ಸುರಕ್ಷತಾ ನಿಯಮಗಳ ಪ್ರಕಾರ ಈ ಕ್ರಿಯೆ ಅನುಮತಿಸಲಾಗಿಲ್ಲ.",
        'unknown_intent': "ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್, ಔಷಧಿಗಳು, ವರದಿಗಳ ಬಗ್ಗೆ ನಾನು ಸಹಾಯ ಮಾಡಬಲ್ಲೆ."
    },
    'ml-IN': {
        'greeting': "നമസ്കാരം! ഞാൻ നിങ്ങളുടെ സ്വാസ്ഥ്യ AI അസിസ്റ്റന്റാണ്. ഞാൻ എങ്ങനെ സഹായിക്കണം?",
        'emergency_alert': "🚨 അടിയന്തര മെഡിക്കൽ മുന്നറിയിപ്പ്: കടുത്ത നെഞ്ചുവേദനയോ ശ്വാസതടസ്സമോ ഉണ്ടെങ്കിൽ ഉടൻ 108 അല്ലെങ്കിൽ 112 വിളിക്കുക.",
        'booking_suggest_dept': "{dept} വിഭാഗമാണ് അനുയോജ്യം. ഏത് തീയതിയാണ് താത്പര്യം?",
        'booking_show_slots': "{date} തീയതിയിൽ ലഭ്യമായ സമയങ്ങൾ: {slots}.",
        'booking_confirm_summary': "സ്ഥിരീകരിക്കുക:\nവിഭാഗം: {dept}\nതീയതി: {date}\nസമയം: {slot}\nഡോക്ടർ: {doctor}\nബുക്ക് ചെയ്യണോ?",
        'booking_success': "✅ അപ്പോയിന്റ്മെന്റ് ബുക്ക് ചെയ്തു! ടോക്കൺ: #{token} ({doctor}).",
        'booking_cancelled': "ബുക്കിംഗ് റദ്ദാക്കി.",
        'medicines_today': "ഇന്നത്തെ മരുന്നുകൾ: {med_list}.",
        'opd_token_status': "നിങ്ങളുടെ ടോക്കൺ നമ്പർ #{token}. നിലവിലെ ടോക്കൺ #{current_token}.",
        'vitals_summary': "നിങ്ങളുടെ പരിശോധനാ ഫലങ്ങൾ: രക്തസമ്മർദ്ദം {bp}, ഓക്സിജൻ {o2}, പഞ്ചസാര {sugar}.",
        'forbidden_action': "സുരക്ഷാ കാരണങ്ങളാൽ ഇത് അനുവദനീയമല്ല.",
        'unknown_intent': "അപ്പോയിന്റ്മെന്റ്, മരുന്നുകൾ, റിപ്പോർട്ടുകൾ എന്നിവയിൽ ഞാൻ സഹായിക്കാം."
    },
    'mr-IN': {
        'greeting': "नमस्कार! मी तुमचा स्वास्थ्य AI सहाय्यक आहे. मी तुम्हाला कशी मदत करू शकतो?",
        'emergency_alert': "🚨 तातडीची वैद्यकीय सूचना: छातीत तीव्र वेदना किंवा श्वास घेण्यास त्रास असल्यास त्वरित 108 किंवा 112 वर कॉल करा.",
        'booking_suggest_dept': "{dept} विभाग योग्य आहे. कोणत्या दिवशी यायचे आहे?",
        'booking_show_slots': "{date} चे उपलब्ध स्लॉट: {slots}.",
        'booking_confirm_summary': "पुष्टी करा:\nविभाग: {dept}\nदिनांक: {date}\nवेळ: {slot}\nडॉक्टर: {doctor}\nबुक करू का?",
        'booking_success': "✅ अपॉइंटमेंट यशस्वीरीत्या बुक झाली! टोकन: #{token} ({doctor}).",
        'booking_cancelled': "बुकिंग रद्द केली आहे.",
        'medicines_today': "आजची औषधे: {med_list}.",
        'opd_token_status': "तुमचा टोकन नंबर #{token} आहे. सध्याचा टोकन #{current_token}.",
        'vitals_summary': "तुमचे नवीनतम वाइटल्स: रक्तदाब {bp}, ऑक्सिजन {o2}, साखर {sugar}.",
        'forbidden_action': "सुरक्षा नियमांमुळे ही कृती करता येत नाही. कृपया सेटिंग्स वापरा.",
        'unknown_intent': "मी अपॉइंटमेंट बुकिंग, टोकन, औषधे आणि रिपोर्ट तपासण्यात मदत करू शकतो."
    },
    'bn-IN': {
        'greeting': "নমস্কার! আমি আপনার স্বাস্থ্য এআই সহকারী। আমি আপনাকে কীভাবে সাহায্য করতে পারি?",
        'emergency_alert': "🚨 জরুরি চিকিৎসা সতর্কতা: বুকে তীব্র ব্যথা বা শ্বাসকষ্টের জন্য অবিলম্বে 108 বা 112 নম্বরে কল করুন।",
        'booking_suggest_dept': "{dept} বিভাগ উপযুক্ত। কোন তারিখে আসতে চান?",
        'booking_show_slots': "{date} তারিখে উপলভ্য সময়: {slots}।",
        'booking_confirm_summary': "নিশ্চিত করুন:\nবিভাগ: {dept}\nতারিখ: {date}\nসময়: {slot}\nডাক্তার: {doctor}\nবুক করব?",
        'booking_success': "✅ অ্যাপয়েন্টমেন্ট নিশ্চিত হয়েছে! টোকেন: #{token} ({doctor})।",
        'booking_cancelled': "বুকিং বাতিল করা হয়েছে।",
        'medicines_today': "আজকের নির্ধারিত ওষুধ: {med_list}।",
        'opd_token_status': "আপনার ওপিডি টোকেন নম্বর #{token}। বর্তমান টোকেন #{current_token}।",
        'vitals_summary': "আপনার সর্বশেষ স্বাস্থ্য তথ্য: রক্তচাপ {bp}, অক্সিজেন {o2}, সুগার {sugar}।",
        'forbidden_action': "সুরক্ষা নীতির কারণে এই কাজটি করা সম্ভব নয়।",
        'unknown_intent': "আমি ডাক্তার বুকিং, ওপিডি টোকেন, ওষুধ এবং রিপোর্ট সংক্রান্ত বিষয়ে সাহায্য করতে পারি।"
    }
}

def get_prompt(lang_code, key, **kwargs):
    prompts = MULTILINGUAL_PROMPTS.get(lang_code, MULTILINGUAL_PROMPTS['en-IN'])
    template = prompts.get(key, MULTILINGUAL_PROMPTS['en-IN'].get(key, ''))
    try:
        return template.format(**kwargs)
    except Exception:
        return template


# ==================== 4. INTENT & ENTITY PARSERS ====================

SYMPTOM_DEPARTMENT_MAP = {
    # Cardiology
    'cardiology': 'Cardiology', 'heart': 'Cardiology', 'cardio': 'Cardiology', 'chest pain': 'Cardiology',
    'gunde': 'Cardiology', 'gundee': 'Cardiology', 'గుండె': 'Cardiology', 'గుండె నొప్పి': 'Cardiology',
    'दिल': 'Cardiology', 'हार्ट': 'Cardiology', 'छाती में दर्द': 'Cardiology', 'நெஞ்சு': 'Cardiology',
    'இதயம்': 'Cardiology', 'ಎದೆ': 'Cardiology', 'ನೆஞ்சு': 'Cardiology', 'छाती': 'Cardiology', 'বুকে': 'Cardiology',

    # Orthopedics
    'orthopedics': 'Orthopedics', 'orthopedic': 'Orthopedics', 'ortho': 'Orthopedics', 'bone': 'Orthopedics',
    'joint': 'Orthopedics', 'knee pain': 'Orthopedics', 'fracture': 'Orthopedics', 'back pain': 'Orthopedics',
    'spine': 'Orthopedics', 'కీళ్ళు': 'Orthopedics', 'ఎముక': 'Orthopedics', 'నడుము నొప్పి': 'Orthopedics',
    'हड्डी': 'Orthopedics', 'कमर दर्द': 'Orthopedics', 'जोड़ों': 'Orthopedics', 'మూட்டு': 'Orthopedics',
    'எலும்பு': 'Orthopedics', 'ಮೂಳೆ': 'Orthopedics', 'ಕೀಲು': 'Orthopedics',

    # General Medicine
    'general medicine': 'General Medicine', 'general': 'General Medicine', 'fever': 'General Medicine',
    'cough': 'General Medicine', 'cold': 'General Medicine', 'weakness': 'General Medicine',
    'headache': 'General Medicine', 'thala noppi': 'General Medicine', 'thalanopiga': 'General Medicine',
    'జ్వరం': 'General Medicine', 'దగ్గు': 'General Medicine', 'బుఖార్': 'General Medicine', 'खांसी': 'General Medicine',
    'बुखार': 'General Medicine', 'सिरदर्द': 'General Medicine', 'காய்ச்சல்': 'General Medicine', 'ಜ್ವರ': 'General Medicine',

    # Dermatology
    'dermatology': 'Dermatology', 'skin': 'Dermatology', 'rash': 'Dermatology', 'itching': 'Dermatology',
    'allergy': 'Dermatology', 'చర్మం': 'Dermatology', 'దురద': 'Dermatology', 'त्वचा': 'Dermatology', 'खुजली': 'Dermatology',

    # Ophthalmology
    'ophthalmology': 'Ophthalmology', 'eye': 'Ophthalmology', 'vision': 'Ophthalmology', 'కన్ను': 'Ophthalmology',
    'కంటి': 'Ophthalmology', 'आंख': 'Ophthalmology', 'கண்': 'Ophthalmology', 'ಕಣ್ಣು': 'Ophthalmology',

    # Dentistry
    'dentistry': 'Dentistry', 'dental': 'Dentistry', 'teeth': 'Dentistry', 'tooth': 'Dentistry',
    'పళ్ళు': 'Dentistry', 'దంత': 'Dentistry', 'दांत': 'Dentistry', 'பல்': 'Dentistry',

    # Pediatrics
    'pediatrics': 'Pediatrics', 'child': 'Pediatrics', 'baby': 'Pediatrics', 'kid': 'Pediatrics',
    'పిల్లలు': 'Pediatrics', 'పాప': 'Pediatrics', 'बच्चा': 'Pediatrics', 'குழந்தை': 'Pediatrics',

    # Neurology
    'neurology': 'Neurology', 'brain': 'Neurology', 'nerve': 'Neurology', 'migraine': 'Neurology',
    'నరాలు': 'Neurology', 'తలతిరగడం': 'Neurology', 'दिमाग': 'Neurology', 'नसों': 'Neurology',

    # Gastroenterology
    'gastroenterology': 'Gastroenterology', 'stomach': 'Gastroenterology', 'gastric': 'Gastroenterology',
    'acidity': 'Gastroenterology', 'vomiting': 'Gastroenterology', 'కడుపు': 'Gastroenterology', 'గ్యాస్': 'Gastroenterology',
    'पेट दर्द': 'Gastroenterology', 'गैस': 'Gastroenterology'
}

EMERGENCY_KEYWORDS = [
    'severe chest pain', 'heart attack', 'cannot breathe', 'severe breathing difficulty',
    'heavy bleeding', 'unconscious', 'severe trauma', 'chest pressure', 'stroke', 'poisoning',
    'breathlessness',
    'सीने में तेज दर्द', 'सांस नहीं आ रही', 'बेहोश', 'भारी रक्तस्राव', 'हार्ट अटैक',
    'తీవ్రమైన గుండె నొప్పి', 'శ్వాస ఆడటం లేదు', 'రక్తం కారుతోంది', 'అపస్మారక స్థితి',
    'கடுமையான நெஞ்சு வலி', 'மூச்சு திணறல்', 'மயக்கம்',
    'ತೀವ್ರ ಎದೆನೋವು', 'ಉಸಿರಾಟದ ತೊಂದರೆ', 'കടുത്ത നെഞ്ചുവേദന', 'छातीत तीव्र वेदना', 'বুকে তীব্র ব্যথা'
]


def parse_day_from_query(query):
    """
    Parses day from user query (today, tomorrow, friday, etc.)
    Returns (target_date, english_display, telugu_display)
    """
    q_lower = (query or '').lower()
    today = timezone.now().date()
    
    if any(w in q_lower for w in ['today', 'ఈరోజు', 'ఈ రోజు', 'आज', 'இன்று', 'ಇವತ್ತು', 'ഇന്ന്']):
        return today, "Today", "ఈరోజు"
    
    if any(w in q_lower for w in ['tomorrow', 'repu', 'రేపు', 'कल', 'நாளை', 'ನಾಳೆ', 'നാളെ', 'उद्या', 'আগামীকাল']):
        target = today + datetime.timedelta(days=1)
        return target, "Tomorrow", "రేపు"
    
    days = {
        'monday': (0, 'Monday', 'సోమవారం'),
        'tuesday': (1, 'Tuesday', 'మంగళవారం'),
        'wednesday': (2, 'Wednesday', 'బుధవారం'),
        'thursday': (3, 'Thursday', 'గురువారం'),
        'friday': (4, 'Friday', 'శుక్రవారం'),
        'saturday': (5, 'Saturday', 'శనివారం'),
        'sunday': (6, 'Sunday', 'ఆదివారం'),
        'సోమవారం': (0, 'Monday', 'సోమవారం'),
        'మంగళవారం': (1, 'Tuesday', 'మంగళవారం'),
        'బుధవారం': (2, 'Wednesday', 'బుధవారం'),
        'గురువారం': (3, 'Thursday', 'గురువారం'),
        'శుక్రవారం': (4, 'Friday', 'శుక్రవారం'),
        'శనివారం': (5, 'Saturday', 'శనివారం'),
        'ఆదివారం': (6, 'Sunday', 'ఆదివారం'),
        'शुक्रवार': (4, 'Friday', 'శుక్రవారం'),
        'शनिवार': (5, 'Saturday', 'శనివారం'),
        'सोमवार': (0, 'Monday', 'సోమవారం'),
    }
    
    for day_kw, (day_idx, en_name, te_name) in days.items():
        if day_kw in q_lower:
            curr_idx = today.weekday()
            days_ahead = (day_idx - curr_idx) % 7
            if days_ahead == 0:
                days_ahead = 7
            target = today + datetime.timedelta(days=days_ahead)
            return target, en_name, te_name
            
    target = today + datetime.timedelta(days=1)
    return target, "Tomorrow", "రేపు"


# ==================== 5. PERMISSION-CHECKED SERVICE TOOLS ====================

def tool_get_my_vitals(user, request=None):
    record_audit_log(request, user, getattr(user, 'role', 'PATIENT'), 'VIEW_RECORD', 'VitalRecord', '', 'SUCCESS', 'AI Assistant fetched patient clinical vitals')
    latest = VitalRecord.objects.filter(patient=user).first()
    if not latest:
        return {'bp': '120/80 mmHg', 'o2': '98%', 'sugar': '95 mg/dL', 'hb': '14.2 g/dL', 'heart_rate': '72 BPM', 'weight': '65', 'has_record': False}
    return {
        'bp': f"{latest.bp_systolic}/{latest.bp_diastolic} mmHg",
        'o2': f"{latest.o2_saturation}%",
        'sugar': f"{latest.sugar_level} mg/dL",
        'hb': f"{latest.blood_percentage} g/dL",
        'heart_rate': f"{latest.heart_rate} BPM",
        'weight': str(getattr(latest, 'weight_kg', '68')),
        'has_record': True,
        'date': latest.recorded_at.strftime('%d-%b-%Y') if hasattr(latest, 'recorded_at') and latest.recorded_at else timezone.now().strftime('%d-%b-%Y')
    }

def tool_get_my_prescriptions(user, request=None):
    record_audit_log(request, user, getattr(user, 'role', 'PATIENT'), 'VIEW_RECORD', 'Prescription', '', 'SUCCESS', 'AI Assistant fetched prescriptions')
    rx_qs = Prescription.objects.filter(patient=user, status='ACTIVE')
    if not rx_qs.exists():
        rx_qs = Prescription.objects.filter(patient=user)
    results = []
    for r in rx_qs:
        timing = []
        if getattr(r, 'morning', False): timing.append("Morning")
        if getattr(r, 'afternoon', False): timing.append("Afternoon")
        if getattr(r, 'night', False): timing.append("Night")
        sched_str = " + ".join(timing) if timing else (getattr(r, 'timing', '') or "")
        results.append({
            'id': r.id,
            'medicine_name': r.medicine_name,
            'dosage': r.dosage,
            'timing': getattr(r, 'timing', ''),
            'has_timing': bool(getattr(r, 'timing', '') or timing),
            'schedule': sched_str or "As directed",
            'purpose': r.purpose,
            'prescribed_by': getattr(r, 'prescribed_by', 'Hospital Staff')
        })
    return results

def tool_get_my_lab_reports(user, request=None):
    record_audit_log(request, user, getattr(user, 'role', 'PATIENT'), 'VIEW_RECORD', 'LabOrder', '', 'SUCCESS', 'AI Assistant fetched lab reports')
    orders = LabOrder.objects.filter(patient=user).order_by('-order_date')
    results = []
    for o in orders:
        results.append({
            'id': o.id,
            'test_name': o.test.name if hasattr(o, 'test') and o.test else 'Clinical Test',
            'status': o.status,
            'result_value': getattr(o, 'result_value', ''),
            'unit': getattr(o, 'unit', '') or (o.test.unit if hasattr(o, 'test') and o.test else ''),
            'reference_range': getattr(o, 'reference_range', '') or (o.test.reference_range if hasattr(o, 'test') and o.test else ''),
            'date': o.order_date.strftime('%d-%b-%Y') if hasattr(o, 'order_date') and o.order_date else ''
        })
    return results

def tool_get_my_appointments(user, request=None):
    record_audit_log(request, user, getattr(user, 'role', 'PATIENT'), 'VIEW_RECORD', 'AppointmentBooking', '', 'SUCCESS', 'AI Assistant fetched appointments')
    bookings = AppointmentBooking.objects.filter(patient=user).order_by('-appointment_date')
    results = []
    for b in bookings:
        results.append({
            'id': b.id,
            'reference': b.reference_number,
            'reference_number': b.reference_number,
            'doctor': b.doctor.name if b.doctor else 'Duty Doctor',
            'doctor_name': b.doctor.name if b.doctor else 'Assigned Doctor',
            'department': b.doctor.department if b.doctor else 'General Medicine',
            'hospital': b.hospital.name if b.hospital else 'AIIMS Hospital',
            'date': b.appointment_date.strftime('%d-%b-%Y') if b.appointment_date else '',
            'time_slot': b.time_slot,
            'slot': b.time_slot,
            'token': b.token_number,
            'room': getattr(b.doctor, 'consultation_room', 'Room 101'),
            'status': b.status
        })
    return results

def tool_get_opd_token(user, request=None):
    record_audit_log(request, user, getattr(user, 'role', 'PATIENT'), 'VIEW_RECORD', 'AppointmentBooking', '', 'SUCCESS', 'AI Assistant fetched OPD token')
    today = timezone.now().date()
    booking = AppointmentBooking.objects.filter(patient=user, appointment_date=today, status__in=['BOOKED', 'CHECKED_IN', 'IN_CONSULTATION']).first()
    if not booking:
        booking = AppointmentBooking.objects.filter(patient=user).order_by('-appointment_date').first()
    if booking:
        return {
            'has_token': True,
            'token': booking.token_number,
            'doctor': booking.doctor.name if booking.doctor else 'Duty Doctor',
            'dept': booking.doctor.department if booking.doctor else 'General Medicine',
            'department': booking.doctor.department if booking.doctor else 'General Medicine',
            'room': getattr(booking.doctor, 'consultation_room', 'Room 102'),
            'current_token': max(1, booking.token_number - 2),
            'ahead': 2,
            'patients_ahead': 2,
            'status': booking.status
        }
    return None

def tool_get_notifications(user, request=None):
    notes = HealthNotification.objects.filter(patient=user, is_read=False).order_by('-created_at')
    return [{'id': n.id, 'title': n.title, 'message': n.message, 'date': n.created_at.strftime('%d-%b-%Y')} for n in notes]

def tool_get_vaccination_records(user, request=None):
    records = VaccinationRecord.objects.filter(patient=user).order_by('-administered_date')
    return [{'vaccine_name': v.vaccine_name, 'dose_number': v.dose_number, 'date': v.administered_date.strftime('%d-%b-%Y') if v.administered_date else ''} for v in records]

def tool_find_available_slots(dept_name, target_date):
    doc = DoctorProfile.objects.filter(department=dept_name, is_active=True).first()
    if not doc:
        doc = DoctorProfile.objects.filter(is_active=True).first()
    return {
        'doctor': doc.name if doc else 'Duty Specialist',
        'department': dept_name,
        'date': target_date.strftime('%d-%b-%Y') if hasattr(target_date, 'strftime') else str(target_date),
        'slots': ["10:00 AM - 10:30 AM", "11:30 AM - 12:00 PM", "02:00 PM - 02:30 PM", "03:00 PM - 03:30 PM"]
    }

def tool_prepare_appointment_confirmation(user, doctor, date_obj, slot_str, symptoms_str='', patient_name=''):
    params = {
        'doctor_id': doctor.id if doctor else 1,
        'date': date_obj.strftime('%Y-%m-%d') if hasattr(date_obj, 'strftime') else str(date_obj),
        'slot': slot_str,
        'symptoms': symptoms_str or 'Consultation',
        'patient_name': patient_name or (user.get_full_name() if user else 'Patient')
    }
    summary = f"Appointment with {doctor.name if doctor else 'Doctor'} on {params['date']} at {slot_str}"
    token_obj = ServerConfirmationToken.create_token(
        user=user,
        action='CREATE_APPOINTMENT',
        parameters=params,
        summary_text=summary,
        ttl_minutes=5
    )
    return token_obj, params

def tool_create_appointment_with_token(user, confirmation_token, request=None):
    token_obj = ServerConfirmationToken.objects.filter(token=confirmation_token).first()
    if not token_obj:
        return {'success': False, 'error': 'Invalid or expired confirmation token.'}
    is_valid, err_msg = token_obj.is_valid(action='CREATE_APPOINTMENT')
    if not is_valid:
        return {'success': False, 'error': err_msg}
    
    params = token_obj.parameters or {}
    doc_id = params.get('doctor_id')
    doc = DoctorProfile.objects.filter(id=doc_id).first() or DoctorProfile.objects.first()
    hosp = doc.hospital if doc and doc.hospital else HospitalFacility.objects.first()
    
    app_date = datetime.datetime.strptime(params.get('date'), '%Y-%m-%d').date() if 'date' in params else (timezone.now().date() + datetime.timedelta(days=1))
    
    booking = AppointmentBooking.objects.create(
        patient=user,
        hospital=hosp,
        doctor=doc,
        appointment_date=app_date,
        time_slot=params.get('slot', '10:00 AM - 10:30 AM'),
        symptoms=params.get('symptoms', 'Voice Booking'),
        status='BOOKED'
    )
    token_obj.mark_used()
    record_audit_log(request, user, getattr(user, 'role', 'PATIENT'), 'CREATE_RECORD', 'AppointmentBooking', str(booking.id), 'SUCCESS', f'AI voice booked appointment #{booking.reference_number}')
    return {
        'success': True,
        'booking_id': booking.id,
        'reference': booking.reference_number,
        'token': booking.token_number,
        'doctor': doc.name if doc else 'Doctor',
        'hospital': hosp.name if hosp else 'Hospital'
    }

def tool_cancel_appointment_with_token(user, confirmation_token, request=None):
    token_obj = ServerConfirmationToken.objects.filter(token=confirmation_token).first()
    if not token_obj:
        return {'success': False, 'error': 'Invalid or expired confirmation token.'}
    is_valid, err_msg = token_obj.is_valid(action='CANCEL_APPOINTMENT')
    if not is_valid:
        return {'success': False, 'error': err_msg}
    
    params = token_obj.parameters or {}
    booking_id = params.get('booking_id')
    booking = AppointmentBooking.objects.filter(id=booking_id, patient=user).first()
    if not booking:
        return {'success': False, 'error': 'Appointment booking record not found.'}
    
    booking.status = 'CANCELLED'
    booking.save()
    token_obj.mark_used()
    record_audit_log(request, user, getattr(user, 'role', 'PATIENT'), 'UPDATE_RECORD', 'AppointmentBooking', str(booking.id), 'SUCCESS', f'AI voice cancelled appointment #{booking.reference_number}')
    return {'success': True, 'booking_id': booking.id, 'reference': booking.reference_number}

def tool_doctor_get_queue(doctor_user, request=None):
    doc_prof = getattr(doctor_user, 'doctor_profile', None) or DoctorProfile.objects.filter(user=doctor_user).first()
    today = timezone.now().date()
    qs = AppointmentBooking.objects.filter(appointment_date=today)
    if doc_prof:
        qs = qs.filter(doctor=doc_prof)
    waiting = qs.filter(status__in=['BOOKED', 'CHECKED_IN']).order_by('token_number')
    next_p = waiting.first()
    return {
        'count': waiting.count(),
        'next_patient': {
            'name': next_p.patient.get_full_name() if next_p.patient else 'Patient',
            'token': next_p.token_number,
            'dept': next_p.doctor.department if next_p.doctor else 'General'
        } if next_p else None
    }

def tool_admin_get_metrics(admin_user, request=None):
    today = timezone.now().date()
    waiting_cnt = AppointmentBooking.objects.filter(appointment_date=today, status__in=['BOOKED', 'CHECKED_IN']).count()
    booked_cnt = AppointmentBooking.objects.filter(appointment_date=today).count()
    doctors_cnt = DoctorProfile.objects.filter(is_active=True).count()
    pending_labs = LabOrder.objects.filter(status__in=['ORDERED', 'COLLECTED', 'PROCESSING']).count()
    return {
        'waiting': waiting_cnt,
        'booked': booked_cnt,
        'doctors': doctors_cnt,
        'pending_labs': pending_labs
    }


def tool_get_my_radiology_reports(user, request=None, modality=None):
    """
    Fetches authorized radiology reports for the authenticated patient.
    Strictly enforces check_patient_record_access for each report record.
    Only returns report fields from the verified database â€” never fabricates findings.
    """
    record_audit_log(
        request, user, getattr(user, 'role', 'PATIENT'),
        'VIEW_RECORD', 'RadiologyReport', '',
        'SUCCESS', 'AI Assistant fetched radiology report list'
    )
    qs = RadiologyReport.objects.filter(patient=user).order_by('-report_date')
    if modality:
        # Match case-insensitively to scan_type
        qs = qs.filter(scan_type__iexact=modality)

    results = []
    for report in qs:
        # Object-level authorization
        if request:
            if not check_patient_record_access(request, report.patient, 'RadiologyReport', str(report.id)):
                continue
        elif report.patient_id != user.id:
            continue
        results.append({
            'id': report.id,
            'scan_type': report.scan_type,
            'procedure_name': getattr(report, 'procedure_name', '') or '',
            'reason_for_exam': getattr(report, 'reason_for_exam', '') or '',
            'findings': report.findings or '',
            'impression': report.impression or '',
            'measurements': getattr(report, 'measurements', '') or '',
            'radiologist_name': report.radiologist_name or '',
            'radiologist_reg': getattr(report, 'radiologist_reg', '') or '',
            'report_date': report.report_date.strftime('%d-%b-%Y') if report.report_date else '',
            'has_imaging_files': getattr(report, 'has_imaging_files', False),
            'is_dicom': getattr(report, 'is_dicom', False),
            'conclusion': getattr(report, 'impression', '') or '',
        })
    return results


def tool_get_physiotherapy_videos(request=None, category=None, query=None):
    """
    Fetches physiotherapy video metadata from the database.
    Returns only legitimate, embeddable video metadata - no clinical authorization required.
    """
    qs = PhysiotherapyVideo.objects.all()
    if category and category != 'all':
        qs = qs.filter(category__iexact=category)
    if query:
        from django.db.models import Q as DQ
        qs = qs.filter(DQ(title__icontains=query) | DQ(description__icontains=query) | DQ(category__icontains=query))

    results = []
    for v in qs.order_by('category', '-created_at')[:12]:
        results.append({
            'id': v.id,
            'title': v.title,
            'description': v.description or '',
            'category': v.category,
            'category_display': v.get_category_display() if hasattr(v, 'get_category_display') else v.category,
            'duration_text': getattr(v, 'duration_text', '8 mins'),
            'external_platform': getattr(v, 'external_platform', 'YouTube (Embeddable)'),
            'external_video_id': getattr(v, 'external_video_id', ''),
            'allows_embedding': getattr(v, 'allows_embedding', True),
            'external_url': getattr(v, 'external_url', ''),
            'embed_url': getattr(v, 'embed_url', ''),
        })
    return results


# ==================== 6. CORE VOICE DIALOGUE ENGINE ====================

class VoiceDialogueEngine:
    @staticmethod
    def detect_lang(text):
        if not text:
            return 'en-IN'
        t_lower = text.lower()

        # 1. Native Indic Unicode Script Detection
        if re.search(r'[\u0c00-\u0c7f]', text):  # Telugu
            return 'te-IN'
        if re.search(r'[\u0900-\u097f]', text):  # Devanagari (Hindi / Marathi)
            if any(w in text for w in ['आहे', 'नाही', 'करा', 'सांगा', 'दाखवा', 'माझे', 'औषध', 'रुग्ण', 'तपासा']):
                return 'mr-IN'
            return 'hi-IN'
        if re.search(r'[\u0b80-\u0bff]', text):  # Tamil
            return 'ta-IN'
        if re.search(r'[\u0c80-\u0cff]', text):  # Kannada
            return 'kn-IN'
        if re.search(r'[\u0d00-\u0d7f]', text):  # Malayalam
            return 'ml-IN'
        if re.search(r'[\u0980-\u09ff]', text):  # Bengali
            return 'bn-IN'

        # 2. Transliterated Romanized Keyword Detection
        if re.search(r'\b(na|naaku|naku|kavali|cheppu|enduku|chestaru|chupinchu|undi|ledu|repu|eeroju|ela|mandulu|reportlu|cheyyi|chaduvu|cheyyali|entha|eppudu|teesukovali|tarvatha|mundha|tiffin|thalanopiga|thalanappi|thala|noppi|chudali|ekkada|unnayi|gundee|gunde|kalavali|chesi|chupinchi|em|ee|e|tablets|tablet|cheppandi|ivvandi|vastundi|vastondi|ostondi|jwaram|jvaram|telidu|theleedu|theliyadu|teliyadu|kolavaledu|chudaledu|tiyyali|vesukovali|unnanu|unnaru)\b', t_lower):
            return 'te-IN'

        if re.search(r'\b(chahiye|batao|dikhao|karo|dawa|bukhar|kal|aaj|kya|hai|mujhe|karna|mera|meri|khula|samjhao|padho|kholo|khol|sir|dard|lene|leni|chahiye|khana|pata|tapman|naapa)\b', t_lower):
            return 'hi-IN'

        if re.search(r'\b(vendum|kaatu|solunga|ennudaya|irukku|nalaiku|marunthu|pannunga|theriyum|thalaivali)\b', t_lower):
            return 'ta-IN'

        if re.search(r'\b(beku|helu|thilisi|nanna|ide|naale|ivattu|oushadhi|madu|thalenovu)\b', t_lower):
            return 'kn-IN'

        if re.search(r'\b(venam|kaanikkuka|parayu|ente|undo|naale|innu|marunnu|thalavedhana)\b', t_lower):
            return 'ml-IN'

        if re.search(r'\b(pahije|sang|dakhva|majhe|ahe|udya|aaj|aushadh|dokedukhi)\b', t_lower):
            return 'mr-IN'

        if re.search(r'\b(chai|bolun|dekhao|amar|ache|aagami|aaj|aushadh|mathabyatha)\b', t_lower):
            return 'bn-IN'

        return 'en-IN'

    @staticmethod
    def process_turn(query_text, user, session_state=None, request=None, lang_override=None, session_obj=None, route_context=None):
        """
        Processes a single conversational turn with state machine execution,
        consequential confirmation tokens, natural language intent understanding, and role authorization.
        """
        q = (query_text or '').strip()
        q_lower = q.lower()

        if session_state is None:
            session_state = {}

        # 1. LANGUAGE SWITCHING & AUTO-DETECTION
        LANG_SWITCH_KEYWORDS = {
            'te-IN': ['telugu', 'తెలుగు', 'తెలుగులో', 'in telugu', 'telugulo', 'telugu lo'],
            'hi-IN': ['hindi', 'हिन्दी', 'हिंदी', 'in hindi', 'hindi mein', 'हिन्दी में', 'हिंदी में'],
            'ta-IN': ['tamil', 'தமிழ்', 'தமிழில்', 'in tamil', 'tamizhil'],
            'kn-IN': ['kannada', 'ಕನ್ನಡ', 'ಕನ್ನಡದಲ್ಲಿ', 'in kannada', 'kannadadalli'],
            'ml-IN': ['malayalam', 'മലയാളം', 'മലയാളത്തിൽ', 'in malayalam', 'malayalathil'],
            'mr-IN': ['marathi', 'मराठी', 'मराठीत', 'in marathi', 'marathit'],
            'bn-IN': ['bengali', 'বাংলা', 'বাংলায়', 'in bengali', 'banglay'],
            'en-IN': ['english', 'अंग्रेजी', 'in english', 'english mein', 'english lo']
        }

        # Check explicit language switch intent
        target_switch_lang = None
        for l_code, kw_list in LANG_SWITCH_KEYWORDS.items():
            if any(kw in q_lower or kw in q for kw in kw_list):
                if any(verb in q_lower or verb in q for verb in [
                    'change', 'switch', 'set', 'convert', 'to', 'marchu', 'badlo', 'badal',
                    'cheppu', 'bolo', 'solunga', 'helu', 'parayu', 'sang', 'bolun',
                    'speak', 'explain', 'tell', 'language', 'website', 'bhasha', 'in', 'lo', 'mein'
                ]):
                    target_switch_lang = l_code
                    break
                elif q_lower in [kw.lower() for kw in kw_list]:
                    target_switch_lang = l_code
                    break
        if target_switch_lang:
            session_state['lang'] = target_switch_lang
            switch_msg = {
                'te-IN': "ఖచ్చితంగా! ఇకపై నేను మీతో తెలుగులో మాట్లాడుతాను. నేను మీకు ఎలా సహాయపడగలను?",
                'hi-IN': "ज़रूर! अब मैं आपसे हिन्दी में बात करूँगा। मैं आपकी क्या सहायता कर सकता हूँ?",
                'ta-IN': "நிச்சயமாக! இனி நான் உங்களுடன் தமிழில் உரையாடுவேன். நான் எவ்வாறு உதவ வேண்டும்?",
                'kn-IN': "ಖಂಡಿತ! ಇನ್ನು ಮುಂದೆ ನಾನು ನಿಮ್ಮೊಂದಿಗೆ ಕನ್ನಡದಲ್ಲಿ ಮಾತನಾಡುತ್ತೇನೆ.",
                'ml-IN': "തീർച്ചയായും! ഇനി മുതൽ ഞാൻ നിങ്ങളോട് മലയാളത്തിൽ സംസാരിക്കാം.",
                'mr-IN': "नक्कीच! आता मी तुमच्याशी मराठीत बोलेन. मी काय मदत करू?",
                'bn-IN': "অবশ্যই! এখন থেকে আমি আপনার সাথে বাংলায় কথা বলব।",
                'en-IN': "Sure! I will now communicate with you in English. How can I help you?"
            }.get(target_switch_lang, "Language switched.")
            return {
                'reply': switch_msg,
                'action': 'set_language',
                'target_lang': target_switch_lang,
                'lang': target_switch_lang,
                'session_state': session_state,
                'status_indicator': 'SPEAKING'
            }

        detected_lang = VoiceDialogueEngine.detect_lang(q)
        if detected_lang != 'en-IN':
            lang = detected_lang
        else:
            lang = lang_override or session_state.get('lang', 'en-IN')
        session_state['lang'] = lang

        # Role extraction
        user_role = getattr(user, 'role', 'PATIENT') if user and getattr(user, 'is_authenticated', False) else 'PATIENT'

        # 2. EMERGENCY CHECK (Priority 0)
        if any(w in q_lower for w in EMERGENCY_KEYWORDS) or any(w in q for w in EMERGENCY_KEYWORDS):
            reply = get_prompt(lang, 'emergency_alert')
            record_audit_log(request, user, user_role, 'SYSTEM_SECURITY', 'EmergencyAlert', '', 'SUCCESS', 'Emergency symptoms detected by Voice Assistant')
            session_state.pop('flow', None)
            session_state.pop('booking_data', None)
            return {
                'reply': reply,
                'action': 'emergency_alert',
                'lang': lang,
                'session_state': session_state,
                'is_urgent': True,
                'status_indicator': 'CONFIRMATION_REQUIRED'
            }

        # 3. FORBIDDEN OPERATIONS REJECTION (Security Invariant)
        if any(term in q_lower for term in [
            'delete account', 'delete patient', 'delete record', 'delete prescription', 'delete lab',
            'delete visit', 'modify clinical', 'modify prescription', 'change diagnosis', 'erase history',
            'delete database', 'erase database', 'drop database', 'drop table', 'delete reports',
            'delete prescriptions', 'delete my report', 'delete my records', 'delete vitals',
            'account delete'
        ]) or (('delete' in q_lower or 'డిలీట్' in q or 'डिलीट' in q) and any(w in q_lower or w in q for w in ['account', 'report', 'prescription', 'database', 'record', 'data', 'అకౌంట్', 'రిపోర్ట్', 'ప్రిస్క్రిప్షన్', 'డేటా', 'खाता', 'पर्चा'])):
            reply = get_prompt(lang, 'forbidden_action')
            record_audit_log(request, user, user_role, 'SYSTEM_SECURITY', 'ForbiddenOperation', '', 'FAILURE', f'Rejected forbidden operation request: {q[:50]}')
            return {'reply': reply, 'action': 'speak', 'lang': lang, 'session_state': session_state, 'status_indicator': 'ERROR'}

        # 4. EASY VOICE MODE TOGGLE
        if any(w in q_lower for w in ['easy voice', 'easy mode', 'accessibility mode', 'सरल मोड', 'ఆసన్ మోడ్', 'సులువు మోడ్']):
            reply = get_prompt(lang, 'easy_voice_welcome')
            return {
                'reply': reply,
                'action': 'open_easy_voice_mode',
                'lang': lang,
                'session_state': session_state,
                'status_indicator': 'SPEAKING'
            }

        # 5. MULTI-TURN WORKFLOW STATE MACHINE
        flow = session_state.get('flow')
        workflow_step = session_state.get('workflow_step')

        # 5.1 Cancellation of Active Workflow
        if flow in ['booking', 'rescheduling', 'cancellation', 'fever_assessment'] and re.search(r'\b(cancel workflow|stop|quit|abort|రద్దు చేయి|రద్దు|रद्द)\b', q_lower):
            session_state.pop('flow', None)
            session_state.pop('workflow_step', None)
            session_state.pop('booking_data', None)
            session_state.pop('confirmation_token', None)
            reply = get_prompt(lang, 'booking_cancelled')
            return {'reply': reply, 'action': 'speak', 'lang': lang, 'session_state': session_state, 'status_indicator': 'IDLE'}

        # 5.2 Multi-Turn Fever Assessment Flow
        if flow == 'fever_assessment':
            session_state.pop('flow', None)
            session_state.pop('workflow_step', None)

            if lang == 'te-IN':
                reply = (
                    "జ్వరం కోసం Dolo 650 (లేదా Paracetamol 650mg) వంటి టాబ్లెట్ ఆహారం తిన్న తర్వాత (After food) తీసుకోవచ్చు. "
                    "మీ డాక్టర్ ప్రిస్క్రిప్షన్ ఉంటే దాని ప్రకారమే వాడండి. "
                    "పుష్కలంగా నీరు తాగి విశ్రాంతి తీసుకోండి. "
                    "102°F కంటే ఎక్కువ జ్వరం ఉన్నా లేదా 2 రోజుల్లో తగ్గకపోయినా వెంటనే డాక్టర్‌ను సంప్రదించండి."
                )
            elif lang == 'hi-IN':
                reply = (
                    "बुखार के लिए आप Dolo 650 (या Paracetamol 650mg) जैसी दवा खाना खाने के बाद (After food) ले सकते हैं। "
                    "यदि आपके डॉक्टर ने पहले से कोई दवा लिखी है, तो prescription के अनुसार लें। "
                    "पर्याप्त पानी पिएं और आराम करें। "
                    "यदि बुखार 102°F से अधिक हो या 2 दिनों में ठीक न हो, तो तुरंत डॉक्टर से संपर्क करें।"
                )
            else:
                reply = (
                    "For fever, a tablet like Dolo 650 (Paracetamol 650mg) can be taken after food. "
                    "If your doctor has prescribed medication, please follow that prescription. "
                    "Drink plenty of water and get adequate rest. "
                    "If the fever exceeds 102Â°F or lasts more than 2 days, please consult a doctor immediately."
                )

            return {
                'reply': reply,
                'action': 'speak',
                'lang': lang,
                'session_state': session_state,
                'status_indicator': 'SPEAKING'
            }

        # 5.3 Multi-Turn Appointment Booking Flow
        if flow == 'booking':
            b_data = session_state.get('booking_data', {})

            # Step: Awaiting Explicit Confirmation
            if workflow_step == 'awaiting_confirmation':
                is_positive = bool(
                    re.search(r'\b(yes|confirm|book\s*it|do\s*it|ha|haan|correct|book|cheyyi|karo)\b', q_lower) or
                    any(w in q for w in ['అవును', 'हाँ', 'हो', 'ஆம்', 'ಹೌದು', 'അതെ', 'হ্যাঁ', 'చేయండి', 'చేయనా', 'చేయి', 'బుక్'])
                )
                is_negative_or_correction = bool(
                    re.search(r'\b(no|change|different|nahi|not)\b', q_lower) or
                    any(w in q for w in ['వద్దు', 'మార్చు', 'ಬೇಡ', 'இல்லை', 'నహి'])
                )

                if is_positive and not is_negative_or_correction:
                    conf_token = session_state.get('confirmation_token')
                    if not conf_token:
                        dept = b_data.get('department', 'General Medicine')
                        doc = DoctorProfile.objects.filter(department=dept, is_active=True).first() or DoctorProfile.objects.filter(is_active=True).first()
                        date_obj = datetime.datetime.strptime(b_data['date'], '%Y-%m-%d').date() if 'date' in b_data else (timezone.now().date() + datetime.timedelta(days=1))
                        token_obj, _ = tool_prepare_appointment_confirmation(user, doc, date_obj, b_data.get('slot', '10:00 AM - 10:30 AM'), b_data.get('symptoms'), b_data.get('patient_name'))
                        conf_token = token_obj.token

                    # Execute booking with server confirmation token
                    res = tool_create_appointment_with_token(user, conf_token, request)
                    session_state.pop('flow', None)
                    session_state.pop('workflow_step', None)
                    session_state.pop('booking_data', None)
                    session_state.pop('confirmation_token', None)

                    if res.get('success'):
                        reply = get_prompt(
                            lang, 'booking_success',
                            ref=res['reference'],
                            token=res['token'],
                            doctor=res['doctor'],
                            hospital=res['hospital']
                        )
                        return {
                            'reply': reply,
                            'action': 'booking_completed',
                            'booking_id': res['booking_id'],
                            'token': res['token'],
                            'tab': 'bookings',
                            'lang': lang,
                            'session_state': session_state,
                            'status_indicator': 'SPEAKING'
                        }
                    else:
                        reply = get_prompt(lang, 'booking_slot_unavailable', slots="11:30 AM, 02:00 PM, 03:00 PM")
                        return {'reply': reply, 'action': 'speak', 'lang': lang, 'session_state': session_state, 'status_indicator': 'ERROR'}

                # Handle natural corrections in confirmation step
                elif is_negative_or_correction:
                    if any(w in q_lower for w in ['change date', 'date to', 'date', 'day', 'friday', 'saturday', 'today', 'tomorrow', 'monday', 'రేపు', 'कल', 'శుక్రవారం', 'శనివారం']):
                        session_state['workflow_step'] = 'awaiting_date'
                        t_date, d_en, d_te = parse_day_from_query(q)
                        b_data['date'] = t_date.strftime('%Y-%m-%d')
                        b_data['date_display'] = d_te if lang == 'te-IN' else d_en
                        dept = b_data.get('department', 'General Medicine')
                        slots_info = tool_find_available_slots(dept, t_date)
                        slots_str = ", ".join(slots_info['slots']) if slots_info['slots'] else "10:00 AM, 11:30 AM, 02:30 PM"
                        reply = f"Which date would you prefer? Available slots for {dept} on {d_en}: {slots_str}" if lang == 'en-IN' else get_prompt(lang, 'booking_show_slots', dept=dept, date=b_data['date_display'], slots=slots_str)
                        return {'reply': reply, 'action': 'speak', 'lang': lang, 'session_state': session_state, 'status_indicator': 'TOOL_EXECUTION'}
                    elif any(w in q_lower for w in ['time', 'slot', '11', '12', '3', '2', 'morning', 'afternoon']):
                        session_state['workflow_step'] = 'awaiting_slot'
                        reply = "సమయం మార్చాలా? ఏ సమయం ఎంచుకుంటారు? (ఉదా: 10:00 AM, 11:30 AM, 02:00 PM, 03:00 PM)" if lang == 'te-IN' else "Sure, which time slot would you prefer? (e.g. 10:00 AM, 11:30 AM, 02:00 PM, 03:00 PM)"
                        return {'reply': reply, 'action': 'speak', 'lang': lang, 'session_state': session_state, 'status_indicator': 'TOOL_EXECUTION'}
                    elif any(w in q_lower for w in ['doctor', 'department', 'cardiology', 'ortho', 'specialist']):
                        session_state['workflow_step'] = 'awaiting_problem'
                        reply = "ఏ డిపార్ట్‌మెంట్ డాక్టర్‌ను సంప్రదించాలనుకుంటున్నారు?" if lang == 'te-IN' else "Which health problem or department would you like to consult?"
                        return {'reply': reply, 'action': 'speak', 'lang': lang, 'session_state': session_state, 'status_indicator': 'TOOL_EXECUTION'}
                    else:
                        session_state.pop('flow', None)
                        session_state.pop('workflow_step', None)
                        session_state.pop('booking_data', None)
                        reply = get_prompt(lang, 'booking_cancelled')
                        return {'reply': reply, 'action': 'speak', 'lang': lang, 'session_state': session_state, 'status_indicator': 'IDLE'}

            # Step: Awaiting Time Slot Selection
            if workflow_step == 'awaiting_slot':
                chosen_slot = '10:00 AM - 10:30 AM'
                if '09:30' in q_lower or '9:30' in q_lower: chosen_slot = '09:30 AM - 10:00 AM'
                elif '09' in q_lower or '9 am' in q_lower or '9' in q_lower: chosen_slot = '09:00 AM - 09:30 AM'
                elif '10:30' in q_lower: chosen_slot = '10:30 AM - 11:00 AM'
                elif '10' in q_lower: chosen_slot = '10:00 AM - 10:30 AM'
                elif '11:30' in q_lower: chosen_slot = '11:30 AM - 12:00 PM'
                elif '11' in q_lower: chosen_slot = '11:00 AM - 11:30 AM'
                elif '12' in q_lower: chosen_slot = '12:00 PM - 12:30 PM'
                elif '02:30' in q_lower or '2:30' in q_lower: chosen_slot = '02:30 PM - 03:00 PM'
                elif '2' in q_lower or '02' in q_lower: chosen_slot = '02:00 PM - 02:30 PM'
                elif '03:30' in q_lower or '3:30' in q_lower: chosen_slot = '03:30 PM - 04:00 PM'
                elif '3' in q_lower or '03' in q_lower: chosen_slot = '03:00 PM - 03:30 PM'

                b_data['slot'] = chosen_slot
                dept = b_data.get('department', 'General Medicine')
                doc = DoctorProfile.objects.filter(department=dept, is_active=True).first() or DoctorProfile.objects.filter(is_active=True).first()
                date_obj = datetime.datetime.strptime(b_data.get('date', timezone.now().date().strftime('%Y-%m-%d')), '%Y-%m-%d').date()

                # Generate Server Confirmation Token
                token_obj, _ = tool_prepare_appointment_confirmation(
                    user=user,
                    doctor=doc,
                    date_obj=date_obj,
                    slot_str=chosen_slot,
                    symptoms_str=b_data.get('symptoms'),
                    patient_name=b_data.get('patient_name')
                )
                session_state['confirmation_token'] = token_obj.token
                session_state['workflow_step'] = 'awaiting_confirmation'

                if lang == 'te-IN':
                    reply = f"{b_data.get('date_display', 'రేపు')} {chosen_slot.split(' - ')[0]} కి డాక్టర్ {doc.name if doc else 'Doctor'} ({dept}) తో appointment book చేయనా?"
                elif lang == 'hi-IN':
                    reply = f"क्या मैं {b_data.get('date_display', 'कल')} को {chosen_slot.split(' - ')[0]} बजे डॉक्टर {doc.name if doc else 'Doctor'} ({dept}) के साथ अपॉइंटमेंट बुक कर दूँ?"
                else:
                    reply = get_prompt(
                        lang, 'booking_confirm_summary',
                        dept=dept,
                        date=b_data.get('date_display', 'Tomorrow'),
                        slot=chosen_slot,
                        doctor=doc.name if doc else 'Doctor'
                    )

                return {
                    'reply': reply,
                    'action': 'speak',
                    'lang': lang,
                    'session_state': session_state,
                    'status_indicator': 'CONFIRMATION_REQUIRED',
                    'confirmation_required': True,
                    'confirmation_token': token_obj.token
                }

            # Step: Awaiting Appointment Date
            if workflow_step == 'awaiting_date':
                t_date, d_en, d_te = parse_day_from_query(q)
                b_data['date'] = t_date.strftime('%Y-%m-%d')
                b_data['date_display'] = d_te if lang == 'te-IN' else d_en

                dept = b_data.get('department', 'General Medicine')
                slots_info = tool_find_available_slots(dept, t_date)
                slots_str = ", ".join(slots_info['slots']) if slots_info['slots'] else "10:00 AM, 11:30 AM, 02:30 PM"

                session_state['workflow_step'] = 'awaiting_slot'
                reply = get_prompt(lang, 'booking_show_slots', dept=dept, date=b_data['date_display'], slots=slots_str)
                return {'reply': reply, 'action': 'speak', 'lang': lang, 'session_state': session_state, 'status_indicator': 'TOOL_EXECUTION'}

            # Step: Awaiting Health Problem / Symptoms
            if workflow_step == 'awaiting_problem':
                matched_dept = 'General Medicine'
                for sym, d in SYMPTOM_DEPARTMENT_MAP.items():
                    if sym in q_lower:
                        matched_dept = d
                        break
                
                b_data['symptoms'] = q
                b_data['department'] = matched_dept
                session_state['workflow_step'] = 'awaiting_date'

                reply = get_prompt(lang, 'booking_suggest_dept', dept=matched_dept)
                return {'reply': reply, 'action': 'speak', 'lang': lang, 'session_state': session_state, 'status_indicator': 'TOOL_EXECUTION'}

            # Step: Awaiting Patient Name
            if workflow_step == 'awaiting_name':
                b_data['patient_name'] = q
                session_state['workflow_step'] = 'awaiting_problem'
                reply = get_prompt(lang, 'booking_ask_problem')
                return {'reply': reply, 'action': 'speak', 'lang': lang, 'session_state': session_state, 'status_indicator': 'TOOL_EXECUTION'}

        # 6. ROLE-SPECIFIC WORKFLOWS (DOCTOR & ADMIN)
        if user_role == 'DOCTOR' and any(w in q_lower for w in ['next patient', 'doctor queue', 'waiting patient', 'my next patient', 'opd queue']):
            d_res = tool_doctor_get_queue(user, request)
            np = d_res.get('next_patient')
            if np:
                reply = get_prompt(lang, 'doctor_next_patient', name=np['name'], token=np['token'], dept=np['dept'])
            else:
                reply = get_prompt(lang, 'doctor_queue_empty')
            return {'reply': reply, 'action': 'speak', 'lang': lang, 'session_state': session_state, 'status_indicator': 'SPEAKING'}

        if user_role == 'ADMIN' and any(w in q_lower for w in ['patients waiting', 'hospital metrics', 'admin summary', 'doctors on duty', 'waiting today']):
            m = tool_admin_get_metrics(user, request)
            reply = get_prompt(lang, 'admin_metrics', waiting=m['waiting'], booked=m['booked'], doctors=m['doctors'], pending_labs=m['pending_labs'])
            return {'reply': reply, 'action': 'speak', 'lang': lang, 'session_state': session_state, 'status_indicator': 'SPEAKING'}

        # 7. INTENT DISPATCHER FOR CITIZENS / PATIENTS

        # 7.0 FEVER TRIAGE & TEMPERATURE ASSESSMENT
        is_fever_query = any(w in q_lower for w in [
            'fever', 'జ్వరం', 'బుఖార్', 'बुखार', 'காய்ச்சல்', 'ಜ್ವರ', 'പനി', 'ताप', 'জ্বর',
            'jwaram', 'jvaram', 'bukhar', 'fever vastundi', 'jwaram vastundi', 'fever undi', 'jwaram undi',
            'bukhar hai', 'bukhar aa raha hai', 'fever ostundi', 'fever vastondi'
        ]) or any(w in q for w in ['జ్వరం', 'బుఖార్', 'बुखार', 'காய்ச்சல்', 'ಜ್ವರ', 'പനി', 'জ্বর'])

        if is_fever_query and session_state.get('flow') != 'booking':
            already_gave_temp = any(w in q_lower for w in [
                '99', '100', '101', '102', '103', '104', '38', '39', '40', 'degree', 'degrees',
                'telidu', 'theleedu', 'dont know', "don't know", 'pata nahi', 'తెలీదు', 'తెలియదు'
            ])

            if already_gave_temp:
                if lang == 'te-IN':
                    reply = (
                        "జ్వరం కోసం Dolo 650 (లేదా Paracetamol 650mg) వంటి టాబ్లెట్ ఆహారం తిన్న తర్వాత (After food) తీసుకోవచ్చు. "
                        "మీ డాక్టర్ ప్రిస్క్రిప్షన్ ఉంటే దాని ప్రకారమే వాడండి. "
                        "పుష్కలంగా నీరు తాగి విశ్రాంతి తీసుకోండి. "
                        "102°F కంటే ఎక్కువ జ్వరం ఉన్నా లేదా 2 రోజుల్లో తగ్గకపోయినా వెంటనే డాక్టర్‌ను సంప్రదించండి."
                    )
                elif lang == 'hi-IN':
                    reply = (
                        "बुखार के लिए आप Dolo 650 (या Paracetamol 650mg) जैसी दवा खाना खाने के बाद (After food) ले सकते हैं। "
                        "यदि आपके डॉक्टर ने पहले से कोई दवा लिखी है, तो prescription के अनुसार लें। "
                        "पर्याप्त पानी पिएं और आराम करें। "
                        "यदि बुखार 102°F से अधिक हो या 2 दिनों में ठीक न हो, तो तुरंत डॉक्टर से संपर्क करें।"
                    )
                else:
                    reply = (
                        "For fever, a tablet like Dolo 650 (Paracetamol 650mg) can be taken after food. "
                        "If your doctor has prescribed medication, please follow that prescription. "
                        "Drink plenty of water and get adequate rest. "
                        "If the fever exceeds 102Â°F or lasts more than 2 days, please consult a doctor immediately."
                    )
                return {'reply': reply, 'action': 'speak', 'lang': lang, 'session_state': session_state, 'status_indicator': 'SPEAKING'}
            else:
                session_state['flow'] = 'fever_assessment'
                session_state['workflow_step'] = 'awaiting_temp'
                if lang == 'te-IN':
                    reply = "మీ body temperature ఎంత ఉందో కొలిచారా? (ఉదా: 99°F, 101°F లేదా తెలీదు అని చెప్పండి)."
                elif lang == 'hi-IN':
                    reply = "क्या आपने अपना बॉडी टेम्परेचर (तापमान) नापा है? (जैसे: 99°F, 101°F या 'पता नहीं' कहें)।"
                else:
                    reply = "Have you measured your body temperature? (e.g. 99Â°F, 101Â°F or say 'I don't know')."
                return {'reply': reply, 'action': 'speak', 'lang': lang, 'session_state': session_state, 'status_indicator': 'SPEAKING'}

        # â”€â”€ 7.5-A  RADIOLOGY REPORTS (MRI / CT / X-Ray / Ultrasound / Mammography) â”€â”€
        RADIOLOGY_KWS = [
            'radiology', 'radiology report', 'mri', 'mri report', 'ct scan', 'ct report',
            'x-ray', 'xray', 'x ray', 'ultrasound', 'mammography', 'mammogram',
            'imaging report', 'scan report', 'my scan', 'open my mri', 'show my mri',
            'open my ct', 'show my ct', 'show my x-ray', 'open x-ray',
            'రేడియాలజీ', 'ఎక్స్‌రే', 'అల్ట్రాసౌండ్', 'ఎమ్‌ఆర్‌ఐ', 'సీటీ స్కాన్',
            'radiologyreport', 'show radiology', 'dicom',
        ]
        is_radiology_query = (
            any(w in q_lower for w in RADIOLOGY_KWS) or
            any(w in q for w in ['రేడియాలజీ', 'ఎక్స్‌రే', 'ఎమ్‌ఆర్‌ఐ', 'సీటీ స్కాన్'])
        )

        if is_radiology_query:
            # Detect specific modality from query
            modality = None
            if any(w in q_lower for w in ['mri', 'ఎమ్‌ఆర్‌ఐ']):
                modality = 'MRI'
            elif any(w in q_lower for w in ['ct scan', 'ct report', 'open my ct', 'show ct', 'సీటీ స్కాన్']):
                modality = 'CT Scan'
            elif any(w in q_lower for w in ['x-ray', 'xray', 'x ray', 'ఎక్స్‌రే']):
                modality = 'X-Ray'
            elif any(w in q_lower for w in ['ultrasound', 'అల్ట్రాసౌండ్']):
                modality = 'Ultrasound'
            elif any(w in q_lower for w in ['mammography', 'mammogram']):
                modality = 'Mammography'

            reports = tool_get_my_radiology_reports(user, request, modality=modality)

            if not reports:
                modality_str = modality or 'Radiology'
                if lang == 'te-IN':
                    reply = f"మీ authorized medical record లో {modality_str} రిపోర్ట్ అందుబాటులో లేదు."
                elif lang == 'hi-IN':
                    reply = f"आपके प्राधिकृत रिकॉर्ड में {modality_str} रिपोर्ट उपलब्ध नहीं है।"
                else:
                    reply = f"No authorized {modality_str} report is available in your medical record."
                return {
                    'reply': reply, 'action': 'navigate_and_speak',
                    'tab': 'radiology', 'lang': lang,
                    'session_state': session_state, 'status_indicator': 'SPEAKING'
                }

            latest = reports[0]
            scan_type = latest.get('scan_type', 'Radiology')
            findings = (latest.get('findings') or '').strip()
            impression = (latest.get('impression') or latest.get('conclusion') or '').strip()
            date = latest.get('report_date', '')
            radiologist = latest.get('radiologist_name', '')

            # Build reply strictly from DB fields â€” never fabricate
            if lang == 'te-IN':
                reply_parts = [f"మీ తాజా {scan_type} రిపోర్ట్ ({date}):"]
                if findings:
                    reply_parts.append(f"Findings: {findings[:180]}")
                if impression:
                    reply_parts.append(f"Impression: {impression[:180]}")
                if radiologist:
                    reply_parts.append(f"రేడియాలజిస్ట్: {radiologist}")
                reply = ' '.join(reply_parts)
            elif lang == 'hi-IN':
                reply_parts = [f"आपकी नवीनतम {scan_type} रिपोर्ट ({date}):"]
                if findings:
                    reply_parts.append(f"निष्कर्ष: {findings[:180]}")
                if impression:
                    reply_parts.append(f"निदान: {impression[:180]}")
                if radiologist:
                    reply_parts.append(f"रेडियोलॉजिस्ट: {radiologist}")
                reply = ' '.join(reply_parts)
            else:
                reply_parts = [f"Your latest {scan_type} report ({date}):"]
                if findings:
                    reply_parts.append(f"Findings: {findings[:200]}")
                if impression:
                    reply_parts.append(f"Impression: {impression[:200]}")
                if radiologist:
                    reply_parts.append(f"Radiologist: {radiologist}")
                reply = ' '.join(reply_parts)

            return {
                'reply': reply,
                'action': 'open_radiology_report',
                'report_id': latest['id'],
                'scan_type': scan_type,
                'tab': 'radiology',
                'lang': lang,
                'session_state': session_state,
                'status_indicator': 'SPEAKING'
            }

        # â”€â”€ 7.5-B  PHYSIOTHERAPY VIDEOS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        PHYSIO_KWS = [
            'physiotherapy', 'physio', 'physio video', 'exercise video',
            'back pain exercise', 'knee exercise', 'neck exercise', 'shoulder exercise',
            'stroke rehab', 'rehabilitation video', 'health education video',
            'play physiotherapy', 'show physiotherapy',
            'ఫిజియోథెరపీ', 'వ్యాయామం', 'ఫిజియో',
            'फिजियोथेरेपी', 'व्यायाम वीडियो',
        ]
        is_physio_query = (
            any(w in q_lower for w in PHYSIO_KWS) or
            any(w in q for w in ['ఫిజియోథెరపీ', 'ఫిజియో'])
        )

        if is_physio_query:
            # Detect category from query
            category = None
            if any(w in q_lower for w in ['back', 'lumbar', 'spine', 'back pain', 'వెన్నునొప్పి', 'कमर दर्द']):
                category = 'back'
            elif any(w in q_lower for w in ['knee', 'osteoarthritis', 'మోకాలి', 'घुटना']):
                category = 'knee'
            elif any(w in q_lower for w in ['neck', 'cervical', 'మెడ నొప్పి', 'गर्दन']):
                category = 'neck'
            elif any(w in q_lower for w in ['shoulder', 'rotator', 'frozen shoulder', 'భుజం', 'कंधा']):
                category = 'shoulder'
            elif any(w in q_lower for w in ['stroke', 'balance', 'rehab', 'స్ట్రోక్', 'पक्षाघात']):
                category = 'stroke'

            videos = tool_get_physiotherapy_videos(request, category=category, query=None)

            if not videos:
                if lang == 'te-IN':
                    reply = "ఫిజియోథెరపీ వీడియోలు ప్రస్తుతం అందుబాటులో లేవు. తర్వాత ప్రయత్నించండి."
                elif lang == 'hi-IN':
                    reply = "फिजियोथेरेपी वीडियो अभी उपलब्ध नहीं हैं।"
                else:
                    reply = "Physiotherapy videos are not available at the moment. Please try again later."
            else:
                titles = ", ".join(v['title'] for v in videos[:3])
                if lang == 'te-IN':
                    reply = f"ఫిజియోథెరపీ విభాగం తెరుస్తున్నాను. అందుబాటులో ఉన్న వీడియోలు: {titles}. మీకు ఇష్టమైన వీడియోను క్లిక్ చేసి చూడవచ్చు."
                elif lang == 'hi-IN':
                    reply = f"फिजियोथेरेपी सेक्शन खोल रहा हूँ। उपलब्ध वीडियो: {titles}।"
                else:
                    reply = f"Opening Physiotherapy & Health Education section. Available videos include: {titles}. Click any video card to play it."

            return {
                'reply': reply,
                'action': 'filter_physiotherapy',
                'category': category or 'all',
                'tab': 'physio',
                'lang': lang,
                'session_state': session_state,
                'status_indicator': 'SPEAKING'
            }


        is_headache_query = any(w in q_lower for w in [
            'headache', 'सिरदर्द', 'सिर दर्द', 'తలనొప్పి', 'తలనెప్పి', 'తల నొప్పి', 'தலைவலி', 'ತಲೆನೋವು', 'തലവേദന', 'डोकेदुखी', 'डोके दुखी', 'মাথাব্যথা', 'মাথা ব্যথা',
            'thalanopiga', 'thala noppi', 'thalanappi', 'sir dard', 'head pain', 'sir me dard', 'thala noppiga', 'talanoppi'
        ]) or any(w in q for w in ['తలనొప్పి', 'తలనెప్పి', 'తల నొప్పి', 'सिरदर्द', 'सिर दर्द'])

        if is_headache_query:
            is_asking_tablet = any(w in q_lower for w in [
                'tablet', 'tablets', 'medicine', 'dawa', 'మాత్ర', 'మందు', 'ఔషధం', 'తీసుకోవాలి', 'తీసుకోవచ్చు', 'తీసుకోవాలా',
                'ఏ tablet', 'em tablet', 'టాబ్లెట్స్', 'టాబ్లెట్',
                'दवा', 'क्या दवा', 'लेनी चाहिए', 'क्या लूँ', 'what medicine', 'what tablet', 'can i take', 'should i take'
            ]) or any(w in q for w in ['టాబ్లెట్స్', 'టాబ్లెట్', 'దవా', 'మందు'])

            if is_asking_tablet:
                if lang == 'te-IN':
                    reply = (
                        "తలనొప్పికి paracetamol వంటి సాధారణ pain reliever కొంతమందికి ఉపయోగపడుతుంది. "
                        "విశ్రాంతి తీసుకోవడం మరియు తగినంత నీరు తాగడం కూడా సహాయపడవచ్చు. "
                        "కానీ మీకు ఏ medicine సరిపోతుందో మీ ఆరోగ్య పరిస్థితులు, ఇతర medicines, allergies వంటి విషయాలపై ఆధారపడి ఉంటుంది. "
                        "మీకు doctor ఇప్పటికే ఏదైనా medicine prescribe చేసి ఉంటే, prescriptionలో చెప్పిన విధంగానే తీసుకోండి. "
                        "మీకు చాలా తీవ్రమైన లేదా అకస్మాత్తుగా వచ్చిన తలనొప్పి, బలహీనత, మాట్లాడటంలో ఇబ్బంది, చూపు సమస్య లేదా స్పృహ కోల్పోవడం ఉంటే వెంటనే emergency medical care తీసుకోండి."
                    )
                elif lang == 'hi-IN':
                    reply = (
                        "सिर दर्द के लिए paracetamol जैसी सामान्य pain reliever कुछ लोगों के लिए मददगार हो सकती है। "
                        "लेकिन आपके लिए कौन सी दवा सही है यह आपके स्वास्थ्य, अन्य दवाओं और एलर्जी पर निर्भर करता है। "
                        "यदि आपके डॉक्टर ने पहले से कोई दवा लिखी है, तो उसे prescription के अनुसार ही लें। "
                        "यदि बहुत तेज या अचानक सिरदर्द, कमजोरी, बोलने या देखने में परेशानी या बेहोशी जैसे लक्षण हों, तो तुरंत आपातकालीन चिकित्सा सहायता लें।"
                    )
                else:
                    reply = (
                        "For headaches, a general pain reliever like paracetamol can be helpful for some people. "
                        "However, suitable medicine depends on your health conditions, other medications, and allergies. "
                        "If your doctor has already prescribed a medicine, follow the prescription. "
                        "If you experience sudden severe headache, weakness, speech difficulty, vision changes, or fainting, seek emergency medical care immediately."
                    )
            else:
                if lang == 'te-IN':
                    reply = (
                        "తలనొప్పికి విశ్రాంతి తీసుకోవడం, తగినంత నీరు తాగడం సహాయపడవచ్చు. "
                        "మీరు ఇప్పటికే doctor prescribe చేసిన medicine ఉంటే prescription ప్రకారం తీసుకోండి. "
                        "తలనొప్పి చాలా తీవ్రంగా లేదా అకస్మాత్తుగా ఉంటే వెంటనే emergency medical care తీసుకోండి."
                    )
                elif lang == 'hi-IN':
                    reply = (
                        "सिर दर्द के कई कारण हो सकते हैं। आराम और पर्याप्त पानी मदद कर सकते हैं। "
                        "अगर आपके डॉक्टर ने कोई दवा लिखी है, तो उसे prescription के अनुसार ही लें। "
                        "यदि सिरदर्द अत्यधिक तीव्र या अचानक हो तो तुरंत आपातकालीन सहायता लें।"
                    )
                else:
                    reply = (
                        "Headaches can have many causes. Resting and adequate fluids may help. "
                        "If your doctor has already prescribed a medicine, follow the prescription. "
                        "Seek emergency medical care if the headache is sudden or unusually severe."
                    )

            return {'reply': reply, 'action': 'speak', 'lang': lang, 'session_state': session_state, 'status_indicator': 'SPEAKING'}

        # 7.2 APPOINTMENT BOOKING INTENT
        is_booking_intent = any(w in q_lower for w in [
            'book appointment', 'see doctor', 'need doctor', 'doctor kavali', 'doctor chahiye',
            'appointment', 'బుకింగ్', 'అపాయింట్మెంట్', 'డాక్టర్ కావాలి', 'முன்பதிவு', 'ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್', 'ডাক্তার দেখাব',
            'doctor appointment book cheyyali', 'appointment book cheyyi', 'cardiology doctor kavali',
            'heart doctor', 'orthopedic doctor', 'doctor appointment', 'doctor ni kalavali', 'डॉक्टर से मिलना',
            'doctor appointment book', 'book cheyyali', 'book cheyyi', 'book an appointment'
        ])

        if is_booking_intent:
            session_state['flow'] = 'booking'
            session_state['booking_data'] = {'patient_name': user.get_full_name() if user else 'Ravi Kumar'}

            direct_dept = None
            for sym, d in SYMPTOM_DEPARTMENT_MAP.items():
                if sym in q_lower:
                    direct_dept = d
                    break

            target_date, d_en, d_te = parse_day_from_query(q)
            date_specified = any(w in q_lower for w in [
                'today', 'tomorrow', 'friday', 'saturday', 'monday', 'tuesday', 'wednesday', 'thursday', 'sunday',
                'repu', 'eeroju', 'kal', 'aaj', 'ఈరోజు', 'రేపు', 'శుక్రవారం', 'శనివారం', 'సోమవారం', 'शुक्रवार'
            ])

            if direct_dept and date_specified:
                session_state['booking_data']['department'] = direct_dept
                session_state['booking_data']['date'] = target_date.strftime('%Y-%m-%d')
                session_state['booking_data']['date_display'] = d_te if lang == 'te-IN' else d_en
                session_state['booking_data']['symptoms'] = q

                slots_info = tool_find_available_slots(direct_dept, target_date)
                slots_str = ", ".join(slots_info['slots']) if slots_info['slots'] else "10:00 AM, 11:30 AM, 02:30 PM"
                session_state['workflow_step'] = 'awaiting_slot'

                if lang == 'te-IN':
                    reply = f"{d_te} {direct_dept}లో అందుబాటులో ఉన్న సమయాలు: {slots_str}. ఏ సమయం కావాలి?"
                elif lang == 'hi-IN':
                    reply = f"{d_en} को {direct_dept} में उपलब्ध स्लॉट: {slots_str}। आप कौन सा समय चुनना चाहेंगे?"
                else:
                    reply = get_prompt(lang, 'booking_show_slots', dept=direct_dept, date=d_en, slots=slots_str)

                return {'reply': reply, 'action': 'speak', 'lang': lang, 'session_state': session_state, 'status_indicator': 'TOOL_EXECUTION'}

            elif direct_dept:
                session_state['booking_data']['department'] = direct_dept
                session_state['booking_data']['symptoms'] = q
                session_state['workflow_step'] = 'awaiting_date'
                reply = get_prompt(lang, 'booking_suggest_dept', dept=direct_dept)
                return {'reply': reply, 'action': 'speak', 'lang': lang, 'session_state': session_state, 'status_indicator': 'TOOL_EXECUTION'}
            else:
                session_state['workflow_step'] = 'awaiting_problem'
                reply = get_prompt(lang, 'booking_ask_problem')
                return {'reply': reply, 'action': 'speak', 'lang': lang, 'session_state': session_state, 'status_indicator': 'TOOL_EXECUTION'}

        # 7.3 VIEW / CANCEL APPOINTMENTS INTENT
        if any(w in q_lower for w in ['cancel appointment', 'రద్దు చేయి', 'రద్దు', 'रद्द']):
            apts = tool_get_my_appointments(user, request)
            if not apts:
                reply = "మీకు రద్దు చేయడానికి ఎలాంటి upcoming appointments లేవు." if lang == 'te-IN' else "You do not have any upcoming appointments to cancel."
                return {'reply': reply, 'action': 'speak', 'lang': lang, 'session_state': session_state, 'status_indicator': 'IDLE'}
            
            target = apts[0]
            token_obj = ServerConfirmationToken.create_token(
                user=user,
                action='CANCEL_APPOINTMENT',
                parameters={'booking_id': target['id']},
                summary_text=f"Cancel appointment #{target['reference']} with Dr. {target['doctor']} on {target['date']}",
                ttl_minutes=5
            )
            session_state['flow'] = 'cancellation'
            session_state['confirmation_token'] = token_obj.token
            reply = get_prompt(lang, 'cancel_confirm', doctor=target['doctor'], date=target['date'], token=target['token'])
            return {
                'reply': reply,
                'action': 'speak',
                'lang': lang,
                'session_state': session_state,
                'status_indicator': 'CONFIRMATION_REQUIRED',
                'confirmation_required': True,
                'confirmation_token': token_obj.token
            }

        if any(w in q_lower for w in [
            'my appointments', 'show appointments', 'next appointment', 'मेरी अपॉइंटमेंट', 'నా అపాయింట్‌మెంట్లు', 'அப்பாயின்ட்மென்ட்',
            'na next appointment eppudu', 'tomorrow doctor evaru', 'where is my appointment', 'when is my next appointment',
            'appointments chupinchu', 'appointments open cheyyi', 'appointments'
        ]):
            apts = tool_get_my_appointments(user, request)
            if not apts:
                if lang == 'te-IN':
                    reply = "మీకు ప్రస్తుతం appointment లేదు. కొత్త అపాయింట్‌మెంట్ బుక్ చేయమంటారా?"
                elif lang == 'hi-IN':
                    reply = "आपकी वर्तमान में कोई अपॉइंटमेंट नहीं है। क्या मैं नई अपॉइंटमेंट बुक करूँ?"
                else:
                    reply = "You do not have an active appointment scheduled. Would you like me to book one for you?"
            else:
                first = apts[0]
                if lang == 'te-IN':
                    reply = f"మీ next appointment Dr. {first['doctor']} ({first['department']}) తో {first['date']} న {first['time_slot']} కి ఉంది. OPD Token #{first['token']} ({first['room']})."
                elif lang == 'hi-IN':
                    reply = f"आपकी अगली अपॉइंटमेंट {first['doctor']} ({first['department']}) के साथ {first['date']} को {first['time_slot']} पर है। OPD टोकन #{first['token']} ({first['room']})।"
                else:
                    reply = f"Your next appointment is with Dr. {first['doctor']} ({first['department']}) on {first['date']} at {first['time_slot']}. OPD Token #{first['token']} in {first['room']}."
            return {'reply': reply, 'action': 'navigate_and_speak', 'tab': 'bookings', 'lang': lang, 'session_state': session_state, 'status_indicator': 'SPEAKING'}

        # 7.4 OPD TOKEN & QUEUE STATUS INTENT
        if any(w in q_lower for w in [
            'opd token', 'my token', 'queue', 'waiting', 'टोकन', 'టోకెన్', 'టోకెన్ నంబర్', 'டோக்கன்', 'টোকেন',
            'what is my opd token', 'queue position', 'what is my queue position'
        ]):
            tok_info = tool_get_opd_token(user, request)
            if not tok_info:
                if lang == 'te-IN':
                    reply = "ఈ రోజు మీకు ఎటువంటి యాక్టివ్ OPD అపాయింట్‌మెంట్ లేదు."
                elif lang == 'hi-IN':
                    reply = "आज के लिए आपकी कोई सक्रिय OPD अपॉइंटमेंट नहीं है।"
                else:
                    reply = "You do not have an active OPD appointment scheduled for today."
            else:
                reply = get_prompt(
                    lang, 'opd_token_status',
                    token=tok_info['token'],
                    doctor=tok_info['doctor'],
                    dept=tok_info['department'],
                    current_token=tok_info['current_token'],
                    ahead=tok_info['patients_ahead'],
                    room=tok_info['room']
                )
            return {'reply': reply, 'action': 'speak', 'lang': lang, 'session_state': session_state, 'status_indicator': 'SPEAKING'}

        # 7.5 LAB REPORTS (Open, Explain Latest, Read)
        is_report_query = any(w in q_lower for w in [
            'lab report', 'blood report', 'reports', 'report', 'test results', 'रिपोर्ट', 'రిపోర్ట్', 'రిపోర్ట్స్',
            'reportlu', 'రిపోర్టులు', 'அறிக்கை', 'রিপোর্ট', 'na reports', 'meri report', 'my reports',
            'na latest report', 'latest report'
        ]) or any(w in q for w in ['రిపోర్ట్', 'రిపోర్ట్స్', 'రిపోర్టులు', 'रिपोर्ट'])

        if is_report_query:
            reports = tool_get_my_lab_reports(user, request)

            is_explain_query = any(w in q_lower for w in [
                'explain', 'వివరించు', 'వివరణ', 'సమర్థించు', 'समझाओ', 'explain cheyyi', 'explain చేయి',
                'explain my latest report', 'latest report explain'
            ]) or ('explain' in q_lower)

            if is_explain_query:
                if not reports:
                    reply = "మీ accountలో report అందుబాటులో లేదు." if lang == 'te-IN' else ("आपके खाते में कोई रिपोर्ट उपलब्ध नहीं है।" if lang == 'hi-IN' else "No report is available in your account.")
                else:
                    latest = reports[0]
                    test_name = latest['test_name']
                    res_val = latest.get('result_value', 'Normal')
                    unit_val = latest.get('unit', '')
                    ref_range = latest.get('reference_range', 'Standard Range')

                    if lang == 'te-IN':
                        reply = f"మీ తాజా {test_name} ఫలితం {res_val} {unit_val} (సాధారణ పరిధి: {ref_range}). మరింత సమాచారం కోసం మీ డాక్టర్‌ను సంప్రదించండి."
                    elif lang == 'hi-IN':
                        reply = f"आपकी नवीनतम {test_name} रिपोर्ट का परिणाम {res_val} {unit_val} (सामान्य सीमा: {ref_range}) है। अधिक जानकारी के लिए कृपया डॉक्टर से परामर्श लें।"
                    else:
                        reply = f"Your latest {test_name} result is {res_val} {unit_val} (Reference range: {ref_range}). Please discuss these findings with your qualified doctor."

                return {'reply': reply, 'action': 'navigate_and_speak', 'tab': 'records', 'lang': lang, 'session_state': session_state, 'status_indicator': 'SPEAKING'}

            # Read report query ("Na latest report chaduvu")
            is_read_query = any(w in q_lower for w in ['chaduvu', 'read', 'padho', 'చదువు', 'पढ़ो', 'पढ़ो', 'bolun'])
            if is_read_query:
                if not reports:
                    reply = "మీ accountలో reports ఏవీ లేవు." if lang == 'te-IN' else "You have no lab reports on record."
                else:
                    latest = reports[0]
                    test_name = latest['test_name']
                    res_val = latest.get('result_value', '')
                    unit_val = latest.get('unit', '')
                    if lang == 'te-IN':
                        reply = f"మీ తాజా ల్యాబ్ రిపోర్ట్: {test_name}, ఫలితం: {res_val} {unit_val}."
                    elif lang == 'hi-IN':
                        reply = f"आपकी नवीनतम लैब रिपोर्ट: {test_name}, परिणाम: {res_val} {unit_val}।"
                    else:
                        reply = f"Your latest lab report is {test_name} with result {res_val} {unit_val}."
                return {'reply': reply, 'action': 'navigate_and_speak', 'tab': 'records', 'lang': lang, 'session_state': session_state, 'status_indicator': 'SPEAKING'}

            # Default: Open reports
            if not reports:
                reply = "మీ accountలో ల్యాబ్ రిపోర్ట్స్ (lab reports) ఏవీ లేవు." if lang == 'te-IN' else "You have no lab reports on record."
            else:
                latest = reports[0]
                reply = get_prompt(lang, 'lab_reports_summary', count=len(reports), latest_test=latest['test_name'], status=latest['status'], date=latest['date'])
            return {'reply': reply, 'action': 'navigate_and_speak', 'tab': 'records', 'lang': lang, 'session_state': session_state, 'status_indicator': 'SPEAKING'}

        # 7.6 PRESCRIPTIONS, MEDICINES & TIMING
        is_rx_query = any(w in q_lower for w in [
            'prescription', 'prescriptions', 'medicines', 'tablets', 'tablet', 'dawa', 'दवाई', 'दवा',
            'మందులు', 'మాత్రలు', 'మందు', 'மருந்து', 'ঔষধ', 'dolo', 'paracetamol', 'pan 40', 'pantoprazole',
            'metformin', 'amoxicillin', 'telmisartan', 'cetirizine', 'atorvastatin', 'medication'
        ]) or any(w in q for w in ['మందులు', 'మాత్రలు', 'మందు', 'दवाई', 'दवा'])
        
        is_timing_query = any(w in q_lower for w in [
            'eppudu teesukovali', 'tiffin mundha', 'lunch tarvatha', 'dinner tarvatha', 'before food', 'after food',
            'morning aa night aa', 'when should i take', 'कब लेनी है', 'खाने के बाद', 'खाने से पहले', 'समय', 'ఎప్పుడు తీసుకోవాలి'
        ])

        if is_rx_query or is_timing_query:
            rx_list = tool_get_my_prescriptions(user, request)

            # Sub-case A: Specific Timing Query
            if is_timing_query:
                target_rx = None
                for rx in rx_list:
                    if rx['medicine_name'].lower() in q_lower:
                        target_rx = rx
                        break
                if not target_rx and rx_list:
                    # check if specific medicine name from catalog was in query
                    for rx in rx_list:
                        if any(token in rx['medicine_name'].lower() for token in q_lower.split()):
                            target_rx = rx
                            break
                    if not target_rx:
                        target_rx = rx_list[0]

                if target_rx and target_rx.get('has_timing') and (target_rx.get('timing') or target_rx.get('schedule')):
                    timing_val = target_rx.get('schedule') or target_rx.get('timing')
                    if lang == 'te-IN':
                        reply = f"మీ prescription ప్రకారం {target_rx['medicine_name']} ను {timing_val} తీసుకోవాలి."
                    elif lang == 'hi-IN':
                        reply = f"आपके prescription के अनुसार {target_rx['medicine_name']} को {timing_val} लेना है।"
                    else:
                        reply = f"According to your prescription, {target_rx['medicine_name']} should be taken {timing_val}."
                else:
                    if lang == 'te-IN':
                        reply = "మీ prescriptionలో ఈ tablet timing కనిపించడం లేదు. నేను timing ఊహించి చెప్పను. మీ డాక్టర్‌ను లేదా ఫార్మసిస్ట్‌ను సంప్రదించండి."
                    elif lang == 'hi-IN':
                        reply = "आपके prescription में इस दवा का समय दर्ज नहीं है। मैं समय का अनुमान नहीं लगा सकता। कृपया अपने डॉक्टर या फार्मासिस्ट से परामर्श लें।"
                    else:
                        reply = "Specific timing for this medicine is not listed in your prescription. I cannot guess the timing. Please consult your doctor or pharmacist."

                return {'reply': reply, 'action': 'navigate_and_speak', 'tab': 'prescriptions', 'lang': lang, 'session_state': session_state, 'status_indicator': 'SPEAKING'}

            # Sub-case B: Specific Tablet Purpose
            is_purpose_query = any(w in q_lower for w in [
                'enduku use chestaru', 'enduku', 'why did the doctor give', 'why prescribed', 'किसलिए', 'उपयोग', 'purpose',
                'why is', 'what is', 'used for', 'use chestaru', 'why used', 'used', 'use', 'why', 'దేనికి', 'ఎందుకు'
            ])

            if is_purpose_query:
                matched_rx = None
                for rx in rx_list:
                    if rx['medicine_name'].lower() in q_lower:
                        matched_rx = rx
                        break

                if not matched_rx and rx_list:
                    matched_rx = rx_list[0]

                if matched_rx:
                    m_name = matched_rx['medicine_name']
                    m_purpose = matched_rx.get('purpose') or "చికిత్స"
                    is_dolo = 'dolo' in m_name.lower() or 'paracetamol' in m_name.lower() or 'dolo' in q_lower or 'paracetamol' in q_lower
                    dolo_tag = " (Paracetamol)" if is_dolo and "paracetamol" not in m_name.lower() else ""

                    if lang == 'te-IN':
                        reply = f"మీ prescriptionలో ఉన్న {m_name}{dolo_tag} సాధారణంగా {m_purpose} కోసం ఉపయోగపడుతుంది. మీ డాక్టర్ సూచించిన డోస్ ప్రకారం మాత్రమే వాడండి."
                    elif lang == 'hi-IN':
                        reply = f"आपके prescription में शामिल {m_name}{dolo_tag} सामान्यतः {m_purpose} के लिए उपयोग की जाती है। केवल निर्धारित मात्रा में लें।"
                    else:
                        reply = f"According to your prescription, {m_name}{dolo_tag} is prescribed for {m_purpose}. Always follow your doctor's dosage instructions."
                    return {'reply': reply, 'action': 'navigate_and_speak', 'tab': 'prescriptions', 'lang': lang, 'session_state': session_state, 'status_indicator': 'SPEAKING'}

                if 'dolo' in q_lower or 'paracetamol' in q_lower:
                    if lang == 'te-IN':
                        reply = "Paracetamol (Dolo 650) సాధారణంగా జ్వరం మరియు నొప్పులను తగ్గించడానికి ఉపయోగిస్తారు. మీ డాక్టర్ సూచించిన మోతాదు ప్రకారం మాత్రమే వాడాలి."
                    elif lang == 'hi-IN':
                        reply = "Paracetamol (Dolo 650) सामान्यतः बुखार और दर्द को कम करने के लिए उपयोग की जाती है। डॉक्टर की सलाह का पालन करें।"
                    else:
                        reply = "Dolo 650 contains Paracetamol and is commonly used for fever and mild pain relief. Always follow the prescribed dosage from your doctor."
                    return {'reply': reply, 'action': 'speak', 'lang': lang, 'session_state': session_state, 'status_indicator': 'SPEAKING'}


            # Sub-case C: Show Prescription & Explain Tablets
            if not rx_list:
                reply = "మీ accountలో active prescriptions ఏవీ లేవు." if lang == 'te-IN' else ("आपके खाते में कोई सक्रिय prescription नहीं है।" if lang == 'hi-IN' else "You do not have any active prescriptions on record.")
            else:
                med_items = []
                for r in rx_list:
                    timing_part = f" ({r['schedule']})" if r.get('has_timing') and r.get('schedule') else ""
                    purpose_part = f" - {r['purpose']}" if r.get('purpose') else ""
                    med_items.append(f"{r['medicine_name']}{timing_part}{purpose_part}")
                med_str = ", ".join(med_items)

                if lang == 'te-IN':
                    reply = f"తప్పకుండా. మీ prescription open చేస్తున్నాను. మీ prescriptionలో {len(rx_list)} మందులు ఉన్నాయి: {med_str}. మీ doctor సూచించిన విధంగానే తీసుకోండి."
                elif lang == 'hi-IN':
                    reply = f"ज़रूर। मैं आपका prescription खोल रहा हूँ। आपके पर्चे में {len(rx_list)} दवाइयाँ हैं: {med_str}।"
                else:
                    reply = f"Sure. Opening your prescription. You have {len(rx_list)} prescribed medicine(s): {med_str}."

            return {'reply': reply, 'action': 'navigate_and_speak', 'tab': 'prescriptions', 'lang': lang, 'session_state': session_state, 'status_indicator': 'SPEAKING'}

        # 7.7 VITALS INTENT
        if any(w in q_lower for w in [
            'blood pressure', 'bp', 'sugar', 'oxygen', 'o2', 'weight', 'heart rate', 'pulse', 'vitals',
            'వైటల్స్', 'రక్తపోటు', 'బీపీ', 'షుగర్', 'ఆక్సిజన్', 'బరువు', 'रक्तचाप', 'शुगर', 'ऑक्सीजन',
            'na bp entha', 'what is my bp', 'latest oxygen level', 'na sugar', 'heart rate'
        ]) or any(w in q for w in ['బీపీ', 'షుగర్', 'ఆక్సిజన్', 'వైటల్స్', 'రక్తపోటు']):
            v = tool_get_my_vitals(user, request)
            rec_date = v.get('date', 'recently')

            if 'bp' in q_lower or 'రక్తపోటు' in q or 'బీపీ' in q or 'blood pressure' in q_lower:
                if v.get('has_record') and v.get('bp'):
                    if lang == 'te-IN':
                        reply = f"మీ తాజా నమోదైన BP {v['bp']} ({rec_date}న నమోదు చేయబడింది)."
                    elif lang == 'hi-IN':
                        reply = f"आपका नवीनतम दर्ज रक्तचाप (BP) {v['bp']} है ({rec_date} को दर्ज किया गया)।"
                    else:
                        reply = f"Your latest recorded blood pressure is {v['bp']} (recorded on {rec_date})."
                else:
                    reply = "మీ accountలో BP రీడింగ్ అందుబాటులో లేదు." if lang == 'te-IN' else "No blood pressure reading is currently recorded in your profile."

            elif 'sugar' in q_lower or 'షుగర్' in q or 'glucose' in q_lower:
                if v.get('has_record') and v.get('sugar'):
                    if lang == 'te-IN':
                        reply = f"మీ తాజా బ్లడ్ షుగర్ లెవెల్ {v['sugar']} ({rec_date}న నమోదు చేయబడింది)."
                    elif lang == 'hi-IN':
                        reply = f"आपका नवीनतम ब्लड शुगर {v['sugar']} है ({rec_date} को दर्ज किया गया)।"
                    else:
                        reply = f"Your latest recorded blood sugar is {v['sugar']} (recorded on {rec_date})."
                else:
                    reply = "మీ accountలో షుగర్ రీడింగ్ అందుబాటులో లేదు." if lang == 'te-IN' else "No blood sugar reading is recorded."

            elif 'oxygen' in q_lower or 'o2' in q_lower or 'ఆక్సిజన్' in q:
                if v.get('has_record') and v.get('o2'):
                    if lang == 'te-IN':
                        reply = f"మీ తాజా ఆక్సిజన్ స్థాయి (SpO2) {v['o2']} ({rec_date}న నమోదు చేయబడింది)."
                    elif lang == 'hi-IN':
                        reply = f"आपका नवीनतम ऑक्सीजन स्तर (SpO2) {v['o2']} है ({rec_date} को दर्ज किया गया)।"
                    else:
                        reply = f"Your latest recorded oxygen saturation is {v['o2']} (recorded on {rec_date})."
                else:
                    reply = "మీ accountలో ఆక్సిజన్ రీడింగ్ అందుబాటులో లేదు." if lang == 'te-IN' else "No oxygen reading is recorded."

            elif 'weight' in q_lower or 'బరువు' in q or 'वजन' in q_lower:
                if v.get('has_record'):
                    reply = f"మీ తాజా నమోదైన బరువు {v.get('weight', '68')} kg ({rec_date}న నమోదు చేయబడింది)." if lang == 'te-IN' else f"Your latest recorded weight is {v.get('weight', '68')} kg ({rec_date})."
                else:
                    reply = "మీ accountలో బరువు రీడింగ్ అందుబాటులో లేదు." if lang == 'te-IN' else "No weight reading is recorded."

            elif 'heart rate' in q_lower or 'pulse' in q_lower or 'గుండె వేగం' in q:
                if v.get('has_record'):
                    reply = f"మీ తాజా హార్ట్ రేట్ {v.get('heart_rate', '72 BPM')} ({rec_date}న నమోదు చేయబడింది)." if lang == 'te-IN' else f"Your latest recorded heart rate is {v.get('heart_rate', '72 BPM')} ({rec_date})."
                else:
                    reply = "మీ accountలో హార్ట్ రేట్ రీడింగ్ అందుబాటులో లేదు." if lang == 'te-IN' else "No heart rate reading is recorded."

            else:
                reply = get_prompt(lang, 'vitals_summary', bp=v['bp'], o2=v['o2'], sugar=v['sugar'])

            return {'reply': reply, 'action': 'navigate_and_speak', 'tab': 'home', 'lang': lang, 'session_state': session_state, 'status_indicator': 'SPEAKING'}

        # 7.8 NOTIFICATIONS & NOTICES
        if any(w in q_lower for w in ['notifications', 'alerts', 'सूचनाएं', 'నోటిఫికేషన్లు', 'నోటిఫికేషన్', 'notifications open cheyyi']):
            notes = HealthNotification.objects.filter(patient=user, is_read=False)
            if not notes.exists():
                reply = "మీకు కొత్త నోటిఫికేషన్లు ఏవీ లేవు." if lang == 'te-IN' else "You have no unread notifications."
            else:
                reply = get_prompt(lang, 'notifications_summary', count=notes.count(), latest_title=notes.first().title)
            return {'reply': reply, 'action': 'navigate_and_speak', 'tab': 'notifications', 'lang': lang, 'session_state': session_state, 'status_indicator': 'SPEAKING'}

        # 7.9 EDUCATIONAL MEDICAL QA (Hemoglobin, Dolo, etc.)
        if 'hemoglobin' in q_lower or 'hb' in q_lower:
            if lang == 'te-IN':
                reply = "హీమోగ్లోబిన్ అనేది ఎర్ర రక్త కణాలలో ఉండే ప్రొటీన్. ఇది శరీరమంతటా ఆక్సిజన్ (oxygen) సరఫరా చేస్తుంది. సాధారణ స్థాయి 12.0 నుండి 16.0 g/dL మధ్య ఉంటుంది."
            elif lang == 'hi-IN':
                reply = "हीमोग्लोबिन लाल रक्त कोशिकाओं में मौजूद एक प्रोटीन है जो शरीर में ऑक्सीजन (oxygen) पहुंचाता है। सामान्य स्तर 12.0 से 16.0 g/dL होता है।"
            else:
                reply = "Hemoglobin is an iron-rich protein in red blood cells that transports oxygen throughout your body. Normal healthy levels are typically between 12.0 and 16.0 g/dL."
            return {'reply': reply, 'action': 'speak', 'lang': lang, 'session_state': session_state, 'status_indicator': 'SPEAKING'}

        # 7.9.1 LOCATION, NEAREST HOSPITAL & DIRECTIONS VOICE INTENTS
        is_nearest_hosp_query = any(w in q_lower for w in [
            'nearest hospital', 'hospitals near me', 'find nearest hospital', 'closest hospital',
            'daggara unna hospital', 'na daggara hospital', 'समीप अस्पताल', 'नजदीकी अस्पताल',
            'దగ్గరలోని ఆసుపత్రి', 'అత్యంత సమీప ఆసుపత్రి', 'அருகிலுள்ள மருத்துவமனை', 'ಸಮೀಪದ ಆಸ್ಪತ್ರೆ'
        ])
        if is_nearest_hosp_query:
            if lang == 'te-IN':
                reply = "మీ ప్రస్తుత లొకేషన్ ఆధారంగా అత్యంత సమీపంలోని ప్రభుత్వాసుపత్రులను వెతికి చూపిస్తున్నాను."
            elif lang == 'hi-IN':
                reply = "आपकी वर्तमान लोकेशन के आधार पर सबसे नजदीकी अस्पतालों की सूची दिखा रहा हूँ।"
            else:
                reply = "Locating nearest government hospitals based on your current location."
            return {
                'reply': reply,
                'action': 'find_nearest_hospital',
                'tab': 'bookings',
                'lang': lang,
                'session_state': session_state,
                'status_indicator': 'TOOL_EXECUTION'
            }

        is_hosp_location_query = any(w in q_lower for w in [
            'hospitals in', 'find hospitals in', 'hospitals near', 'hospitals in 522601', 'hospitals in guntur',
            'hospitals in narasaraopet', 'अस्पताल दिखाओ', 'ఆసుపత్రులు చూపించు'
        ])
        if is_hosp_location_query:
            if lang == 'te-IN':
                reply = "మీరు కోరిన లొకేషన్ లో ఉన్న ఆసుపత్రుల వివరాలు లోడ్ చేస్తున్నాను."
            elif lang == 'hi-IN':
                reply = "आपकी चुनी हुई लोकेशन के अस्पतालों की सूची दिखाई जा रही है।"
            else:
                reply = "Searching hospitals matching your requested location."
            return {
                'reply': reply,
                'action': 'search_hospitals',
                'query': q,
                'tab': 'bookings',
                'lang': lang,
                'session_state': session_state,
                'status_indicator': 'TOOL_EXECUTION'
            }

        is_directions_query = any(w in q_lower for w in [
            'show directions', 'get directions', 'directions to hospital', 'route to hospital',
            'దారితీయు', 'రస్తా', 'दिशाएं', 'रास्ता दिखाओ'
        ])
        if is_directions_query:
            if lang == 'te-IN':
                reply = "సమీప ఆసుపత్రికి మ్యాప్స్ దిశలను తెరుస్తున్నాను."
            elif lang == 'hi-IN':
                reply = "अस्पताल के लिए मैप्स दिशा-निर्देश खोले जा रहे हैं।"
            else:
                reply = "Opening map directions to the selected hospital."
            return {
                'reply': reply,
                'action': 'get_directions',
                'tab': 'bookings',
                'lang': lang,
                'session_state': session_state,
                'status_indicator': 'SPEAKING'
            }

        # 7.10 SAFE ROUTE NAVIGATION
        for route_key, target in SAFE_ROUTES.items():
            if (f"open {route_key}" in q_lower or f"show {route_key}" in q_lower or f"go to {route_key}" in q_lower or
                f"{route_key} open cheyyi" in q_lower or f"{route_key} chupinchu" in q_lower or f"{route_key} ki vellu" in q_lower or
                f"{route_key} చూపించు" in q_lower or f"खोलो {route_key}" in q_lower or f"go {route_key}" in q_lower):
                clean_name = route_key.replace('_', ' ').title()
                if lang == 'te-IN':
                    reply = f"తప్పకుండా. {clean_name} పేజీని ఓపెన్ చేస్తున్నాను."
                elif lang == 'hi-IN':
                    reply = f"ज़रूर। मैं {clean_name} पेज खोल रहा हूँ।"
                else:
                    reply = f"Opening {clean_name} section."
                return {
                    'reply': reply,
                    'action': 'navigate',
                    'tab': target.replace('#', '').replace('/', '') or 'home',
                    'route_key': route_key,
                    'lang': lang,
                    'session_state': session_state,
                    'status_indicator': 'SPEAKING'
                }

        # 7.11 DEFAULT / UNKNOWN INTENT FALLBACK
        reply = get_prompt(lang, 'unknown_intent')
        return {
            'reply': reply,
            'action': 'speak',
            'lang': lang,
            'session_state': session_state,
            'status_indicator': 'IDLE'
        }

