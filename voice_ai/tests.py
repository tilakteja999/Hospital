import json
import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from core.models import User
from patients.models import Prescription, HealthNotification, VitalRecord, LabOrder, LabTest
from appointments.models import HospitalFacility, DoctorProfile, HospitalArea, AppointmentBooking
from voice_ai.models import AssistantSession, ServerConfirmationToken
from voice_ai.voice_engine import (
    VoiceDialogueEngine,
    tool_prepare_appointment_confirmation,
    tool_create_appointment_with_token,
    ALLOWED_TOOLS,
    FORBIDDEN_OPERATIONS
)


class VoiceAIAssistantMasterTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Patient User
        self.patient = User.objects.create_user(
            phone='9876543210',
            password='testpassword',
            full_name='Ravi Kumar',
            role='PATIENT',
            aadhaar_number='999988887777',
            is_aadhaar_verified=True
        )

        # Doctor User
        self.doctor_user = User.objects.create_user(
            phone='9876543211',
            password='docpassword',
            full_name='Dr. Rajesh Kumar',
            role='DOCTOR'
        )

        # Admin User
        self.admin_user = User.objects.create_user(
            phone='9876543212',
            password='adminpassword',
            full_name='Hospital Director',
            role='ADMIN'
        )

        # Hospital & Doctor
        self.area = HospitalArea.objects.create(
            city='New Delhi',
            area_name='Ansari Nagar',
            state='Delhi',
            pincode='110029'
        )

        self.hospital = HospitalFacility.objects.create(
            name='All India Institute of Medical Sciences (AIIMS)',
            area=self.area,
            facility_type='Central Govt',
            address='Sri Aurobindo Marg, Ansari Nagar, New Delhi',
            contact_phone='108',
            emergency_available=True,
            total_beds=2500
        )

        self.doctor = DoctorProfile.objects.create(
            name='Dr. Rajesh Kumar',
            user=self.doctor_user,
            doctor_reg_id='DOC-GM-1001',
            department='General Medicine',
            hospital=self.hospital,
            qualification='MBBS, MD',
            max_daily_slots=35,
            is_active=True,
            consultation_room='Room 102'
        )

        self.ortho_doc = DoctorProfile.objects.create(
            name='Dr. Suresh Ortho',
            doctor_reg_id='DOC-ORT-1002',
            department='Orthopedics',
            hospital=self.hospital,
            qualification='MS Orthopedics',
            max_daily_slots=30,
            is_active=True,
            consultation_room='Room 204'
        )

        # Vitals
        VitalRecord.objects.create(
            patient=self.patient,
            bp_systolic=124,
            bp_diastolic=82,
            o2_saturation=98.5,
            sugar_level=96.0
        )

        # Active Prescription
        Prescription.objects.create(
            patient=self.patient,
            medicine_name='Tab. Dolo 650mg',
            dosage='650mg',
            form='Tablet',
            morning=True,
            night=True,
            purpose='Fever and pain relief',
            prescribed_by='Dr. Rajesh Kumar',
            status='ACTIVE'
        )

    # 1. TEST MULTILINGUAL AUTO-DETECTION ACROSS 8 LANGUAGES
    def test_multilingual_language_detection(self):
        # Telugu (Unicode & Romanized)
        self.assertEqual(VoiceDialogueEngine.detect_lang("నా రిపోర్ట్స్ ఓపెన్ చేయి"), 'te-IN')
        self.assertEqual(VoiceDialogueEngine.detect_lang("Dolo 650 enduku use chestaru?"), 'te-IN')
        self.assertEqual(VoiceDialogueEngine.detect_lang("Doctor kavali"), 'te-IN')

        # Hindi
        self.assertEqual(VoiceDialogueEngine.detect_lang("मेरी रिपोर्ट दिखाओ"), 'hi-IN')
        self.assertEqual(VoiceDialogueEngine.detect_lang("Mera appointment dikhao"), 'hi-IN')

        # Tamil
        self.assertEqual(VoiceDialogueEngine.detect_lang("என்னுடைய அப்பாயின்ட்மென்ட்களை காட்டு"), 'ta-IN')
        self.assertEqual(VoiceDialogueEngine.detect_lang("Marunthu kaatu"), 'ta-IN')

        # Kannada
        self.assertEqual(VoiceDialogueEngine.detect_lang("ನನ್ನ ಅಪಾಯಿಂಟ್ಮೆಂಟ್ ತೋರಿಸಿ"), 'kn-IN')

        # Malayalam
        self.assertEqual(VoiceDialogueEngine.detect_lang("എന്റെ റിപ്പോർട്ട് കാണിക്കൂ"), 'ml-IN')

        # Marathi
        self.assertEqual(VoiceDialogueEngine.detect_lang("माझे रिपोर्ट दाखवा"), 'mr-IN')

        # Bengali
        self.assertEqual(VoiceDialogueEngine.detect_lang("আমার রিপোর্ট দেখাও"), 'bn-IN')

        # English Default
        self.assertEqual(VoiceDialogueEngine.detect_lang("Show my appointments"), 'en-IN')

    # 2. TEST EXPLICIT LANGUAGE SWITCHING
    def test_explicit_language_switch(self):
        res_te = VoiceDialogueEngine.process_turn("తెలుగులో చెప్పండి", self.patient, {})
        self.assertEqual(res_te['target_lang'], 'te-IN')
        self.assertIn("తెలుగులో", res_te['reply'])

        res_en = VoiceDialogueEngine.process_turn("English lo cheppu", self.patient, {})
        self.assertEqual(res_en['target_lang'], 'en-IN')
        self.assertIn("English", res_en['reply'])

        res_hi = VoiceDialogueEngine.process_turn("हिन्दी में बोलो", self.patient, {})
        self.assertEqual(res_hi['target_lang'], 'hi-IN')
        self.assertIn("हिन्दी", res_hi['reply'])

    # 3. TEST FULL MULTI-TURN APPOINTMENT BOOKING WORKFLOW WITH SERVER CONFIRMATION
    def test_multi_turn_booking_workflow(self):
        session_state = {}

        # Turn 1: User says "Book an appointment"
        t1 = VoiceDialogueEngine.process_turn("Book an appointment", self.patient, session_state)
        self.assertEqual(t1['session_state']['flow'], 'booking')
        self.assertEqual(t1['session_state']['workflow_step'], 'awaiting_problem')
        self.assertIn("problem", t1['reply'].lower())

        # Turn 2: User specifies "Knee pain" -> system matches Orthopedics
        t2 = VoiceDialogueEngine.process_turn("Knee pain", self.patient, t1['session_state'])
        self.assertEqual(t2['session_state']['booking_data']['department'], 'Orthopedics')
        self.assertEqual(t2['session_state']['workflow_step'], 'awaiting_date')
        self.assertIn("Orthopedics", t2['reply'])

        # Turn 3: User specifies "Tomorrow" -> system finds slots
        t3 = VoiceDialogueEngine.process_turn("Tomorrow", self.patient, t2['session_state'])
        self.assertEqual(t3['session_state']['workflow_step'], 'awaiting_slot')
        self.assertIn("slots", t3['reply'].lower())

        # Turn 4: User picks "10 AM" -> system stages booking and creates ServerConfirmationToken
        t4 = VoiceDialogueEngine.process_turn("10 AM", self.patient, t3['session_state'])
        self.assertEqual(t4['session_state']['workflow_step'], 'awaiting_confirmation')
        self.assertTrue(t4.get('confirmation_required'))
        self.assertTrue(t4.get('confirmation_token'))
        self.assertIn("Please confirm", t4['reply'])
        self.assertIn("Orthopedics", t4['reply'])

        token_str = t4['confirmation_token']
        token_obj = ServerConfirmationToken.objects.filter(token=token_str).first()
        self.assertIsNotNone(token_obj)
        self.assertFalse(token_obj.is_used)

        # Turn 5: User explicitly confirms "Yes" -> booking executed
        t5 = VoiceDialogueEngine.process_turn("Yes, book it", self.patient, t4['session_state'])
        self.assertEqual(t5['action'], 'booking_completed')
        self.assertTrue("booked" in t5['reply'].lower() or "confirmed" in t5['reply'].lower())
        self.assertTrue(AppointmentBooking.objects.filter(patient=self.patient, doctor=self.ortho_doc).exists())

        # Verify token was marked as used
        token_obj.refresh_from_db()
        self.assertTrue(token_obj.is_used)

    # 4. TEST NATURAL CORRECTIONS IN BOOKING
    def test_natural_corrections(self):
        session_state = {
            'flow': 'booking',
            'workflow_step': 'awaiting_confirmation',
            'booking_data': {
                'department': 'Cardiology',
                'date': (timezone.now().date() + datetime.timedelta(days=1)).strftime('%Y-%m-%d'),
                'date_display': 'Tomorrow',
                'slot': '10:00 AM - 10:30 AM',
                'patient_name': 'Ravi Kumar'
            }
        }
        # User corrects: "No, Friday instead"
        res = VoiceDialogueEngine.process_turn("No, change date to Friday", self.patient, session_state)
        self.assertEqual(res['session_state']['workflow_step'], 'awaiting_date')
        self.assertIn("date", res['reply'].lower())

    # 5. TEST SERVER CONFIRMATION TOKEN INTEGRITY & EXPIRATION
    def test_confirmation_token_integrity_and_expiration(self):
        token_obj, params = tool_prepare_appointment_confirmation(
            user=self.patient,
            doctor=self.doctor,
            date_obj=timezone.now().date() + datetime.timedelta(days=1),
            slot_str='10:00 AM - 10:30 AM',
            symptoms_str='Routine checkup'
        )

        # 1. Valid execution
        res = tool_create_appointment_with_token(self.patient, token_obj.token)
        self.assertTrue(res['success'])
        self.assertIn('reference', res)

        # 2. Used token replay attempt must be rejected (single-use idempotency)
        res_replay = tool_create_appointment_with_token(self.patient, token_obj.token)
        self.assertFalse(res_replay['success'])
        self.assertIn("already been used", res_replay['error'])

        # 3. Expired token must be rejected
        expired_token = ServerConfirmationToken.create_token(
            user=self.patient,
            action='CREATE_APPOINTMENT',
            parameters=params,
            ttl_minutes=-10 # Already expired
        )
        res_expired = tool_create_appointment_with_token(self.patient, expired_token.token)
        self.assertFalse(res_expired['success'])
        self.assertIn("expired", res_expired['error'])

    # 6. TEST EMERGENCY RED FLAG INTERCEPTION (Priority 0)
    def test_emergency_interception(self):
        res = VoiceDialogueEngine.process_turn("I am having severe chest pain and breathlessness", self.patient, {})
        self.assertTrue(res['is_urgent'])
        self.assertEqual(res['action'], 'emergency_alert')
        self.assertIn("108", res['reply'])
        self.assertIn("112", res['reply'])

    # 7. TEST FORBIDDEN OPERATIONS
    def test_forbidden_operations_rejection(self):
        res = VoiceDialogueEngine.process_turn("Delete my patient account and prescriptions", self.patient, {})
        self.assertEqual(res['status_indicator'], 'ERROR')
        self.assertIn("cannot perform that action", res['reply'].lower())

    # 8. TEST SAFE MEDICAL QA (Non-diagnostic)
    def test_safe_medical_qa(self):
        res_dolo = VoiceDialogueEngine.process_turn("Why is Dolo 650 used?", self.patient, {})
        self.assertIn("Paracetamol", res_dolo['reply'])
        self.assertIn("fever", res_dolo['reply'].lower())
        self.assertIn("doctor", res_dolo['reply'].lower())

        res_hb = VoiceDialogueEngine.process_turn("What does hemoglobin mean?", self.patient, {})
        self.assertIn("oxygen", res_hb['reply'].lower())

    # 9. TEST ROLE-BASED ACCESS CONTROLS
    def test_role_based_access(self):
        # Patient queries vitals -> Success
        res_vit = VoiceDialogueEngine.process_turn("What is my blood pressure?", self.patient, {})
        self.assertIn("124/82", res_vit['reply'])

        # Doctor queries next patient -> Success for Doctor
        res_doc = VoiceDialogueEngine.process_turn("Show my next patient in OPD queue", self.doctor_user, {})
        self.assertIn("patient", res_doc['reply'].lower())

        # Admin queries hospital metrics -> Success for Admin
        res_admin = VoiceDialogueEngine.process_turn("How many patients are waiting today?", self.admin_user, {})
        self.assertIn("Hospital Summary", res_admin['reply'])

    # 10. TEST ASSISTANT GATEWAY API ENDPOINTS
    def test_assistant_gateway_api(self):
        self.client.login(phone='9876543210', password='testpassword')

        # Message API
        response = self.client.post(
            reverse('api_assistant_message'),
            data=json.dumps({'query': 'Show my medicines', 'lang': 'en-IN'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('reply', data)
        self.assertEqual(data['tab'], 'prescriptions')

        # Session Reset API
        res_reset = self.client.post(reverse('api_assistant_session_reset'))
        self.assertEqual(res_reset.status_code, 200)
        self.assertTrue(res_reset.json()['success'])

    # 11. TEST MASTER PROMPT NATURAL TELUGU & HINDI QUERIES
    def test_master_prompt_natural_queries(self):
        # 1. Telugu Headache triage question
        res_headache_te = VoiceDialogueEngine.process_turn(
            "నాకు చాలా తలనొప్పిగా ఉంది. ఏం చేయాలి? ఏమైనా టాబ్లెట్స్ తీసుకోవాలా?",
            self.patient, {}
        )
        self.assertEqual(res_headache_te['lang'], 'te-IN')
        self.assertIn("తలనొప్పి", res_headache_te['reply'])
        self.assertIn("విశ్రాంతి", res_headache_te['reply'])
        self.assertIn("prescription", res_headache_te['reply'])

        # 2. Telugu Mixed "Na reports open cheyyi"
        res_rep_open = VoiceDialogueEngine.process_turn("Na reports open cheyyi.", self.patient, {})
        self.assertEqual(res_rep_open['lang'], 'te-IN')
        self.assertEqual(res_rep_open['tab'], 'records')
        self.assertTrue("reports" in res_rep_open['reply'].lower() or "రిపోర్ట్స్" in res_rep_open['reply'])

        # 3. Create a Lab Test & Order for Read/Explain tests
        test_cbc = LabTest.objects.create(name='Complete Blood Count (CBC)', code='CBC-01', category='Hematology', unit='g/dL', reference_range='12.0 - 16.0')
        LabOrder.objects.create(
            patient=self.patient,
            test=test_cbc,
            order_reference='LAB-2026-001',
            status='COMPLETED',
            result_value='10.2'
        )

        # 4. Telugu Mixed "Na latest report chaduvu" -> reads actual test name and value
        res_rep_read = VoiceDialogueEngine.process_turn("Na latest report chaduvu.", self.patient, {})
        self.assertEqual(res_rep_read['lang'], 'te-IN')
        self.assertIn("10.2", res_rep_read['reply'])

        # 5. Telugu Mixed "Na report explain cheyyi" -> explains values with doctor disclaimer
        res_rep_explain = VoiceDialogueEngine.process_turn("Na report explain cheyyi.", self.patient, {})
        self.assertEqual(res_rep_explain['lang'], 'te-IN')
        self.assertIn("10.2", res_rep_explain['reply'])
        self.assertIn("డాక్టర్", res_rep_explain['reply'])

        # 6. Telugu Mixed "Na BP entha?" -> reads real BP with recorded date
        res_bp = VoiceDialogueEngine.process_turn("Na BP entha?", self.patient, {})
        self.assertEqual(res_bp['lang'], 'te-IN')
        self.assertIn("124/82", res_bp['reply'])

        # 7. Medicine timing "Ee tablet eppudu teesukovali?" / "Ee tablet tiffin mundha teesukovala?"
        res_timing = VoiceDialogueEngine.process_turn("Ee tablet eppudu teesukovali?", self.patient, {})
        self.assertEqual(res_timing['lang'], 'te-IN')
        self.assertIn("prescription", res_timing['reply'])
        self.assertIn("Dolo 650mg", res_timing['reply'])

        # 8. English "I have a headache. What should I do?"
        res_headache_en = VoiceDialogueEngine.process_turn("I have a headache. What should I do?", self.patient, {})
        self.assertEqual(res_headache_en['lang'], 'en-IN')
        self.assertIn("headache", res_headache_en['reply'].lower())
        self.assertIn("resting", res_headache_en['reply'].lower())

    # 12. TEST SPECIFIC USER PROMPT VALIDATION SCENARIOS
    def test_user_prompt_exact_scenarios(self):
        # Test 1: "నాకు తలనొప్పిగా ఉంది." -> Telugu general headache triage
        t1 = VoiceDialogueEngine.process_turn("నాకు తలనొప్పిగా ఉంది.", self.patient, {})
        self.assertEqual(t1['lang'], 'te-IN')
        self.assertIn("తలనొప్పి", t1['reply'])
        self.assertIn("విశ్రాంతి", t1['reply'])
        self.assertIn("prescription", t1['reply'])

        # Test 2: "నాకు చాలా తలనొప్పిగా ఉంది. ఏ tablet తీసుకోవాలి?" -> Telugu medication answer
        t2 = VoiceDialogueEngine.process_turn("నాకు చాలా తలనొప్పిగా ఉంది. ఏ tablet తీసుకోవాలి?", self.patient, {})
        self.assertEqual(t2['lang'], 'te-IN')
        self.assertIn("తలనొప్పి", t2['reply'])
        self.assertIn("paracetamol", t2['reply'].lower())
        self.assertIn("prescription", t2['reply'].lower())
        self.assertIn("emergency", t2['reply'].lower())

        # Test 3: "मुझे सिर दर्द हो रहा है, क्या दवा लेनी चाहिए?" -> Hindi medication answer
        t3 = VoiceDialogueEngine.process_turn("मुझे सिर दर्द हो रहा है, क्या दवा लेनी चाहिए?", self.patient, {})
        self.assertEqual(t3['lang'], 'hi-IN')
        self.assertIn("paracetamol", t3['reply'].lower())
        self.assertIn("prescription", t3['reply'].lower())

        # Test 4: "I have a headache. What medicine can I take?" -> English medication answer
        t4 = VoiceDialogueEngine.process_turn("I have a headache. What medicine can I take?", self.patient, {})
        self.assertEqual(t4['lang'], 'en-IN')
        self.assertIn("paracetamol", t4['reply'].lower())
        self.assertIn("prescription", t4['reply'].lower())
        self.assertIn("emergency", t4['reply'].lower())

        # Test 5: "Na reports open cheyyi." -> Open reports
        t5 = VoiceDialogueEngine.process_turn("Na reports open cheyyi.", self.patient, {})
        self.assertEqual(t5['lang'], 'te-IN')
        self.assertEqual(t5['tab'], 'records')
        self.assertIn("reports", t5['reply'].lower())

        # Test 6: "నా reports open చేసి latest report explain చేయి." -> Open reports & explain
        test_cbc = LabTest.objects.create(name='Hemoglobin Lab Test', code='HB-01', category='Hematology', unit='g/dL', reference_range='12.0 - 16.0')
        LabOrder.objects.create(patient=self.patient, test=test_cbc, order_reference='LAB-2026-HB', status='COMPLETED', result_value='13.5')
        t6 = VoiceDialogueEngine.process_turn("నా reports open చేసి latest report explain చేయి.", self.patient, {})
        self.assertEqual(t6['lang'], 'te-IN')
        self.assertEqual(t6['tab'], 'records')
        self.assertIn("13.5", t6['reply'])
        self.assertIn("Hemoglobin", t6['reply'])
        self.assertIn("డాక్టర్", t6['reply'])

        # Test 7: "నా prescription చూపించి tablets గురించి చెప్పు." -> Open prescriptions & explain active tablets
        t7 = VoiceDialogueEngine.process_turn("నా prescription చూపించి tablets గురించి చెప్పు.", self.patient, {})
        self.assertEqual(t7['lang'], 'te-IN')
        self.assertEqual(t7['tab'], 'prescriptions')
        self.assertIn("Dolo 650mg", t7['reply'])
        self.assertIn("Fever and pain relief", t7['reply'])

        # Test 8: "Naaku Friday cardiology appointment book cheyyali." -> Multi-turn booking
        t8_turn1 = VoiceDialogueEngine.process_turn("Naaku Friday cardiology appointment book cheyyali.", self.patient, {})
        self.assertEqual(t8_turn1['lang'], 'te-IN')
        self.assertEqual(t8_turn1['session_state']['workflow_step'], 'awaiting_slot')
        self.assertIn("Cardiology", t8_turn1['reply'])
        self.assertIn("సమయాలు", t8_turn1['reply'])

        # Turn 2: Slot selection "10 AM"
        t8_turn2 = VoiceDialogueEngine.process_turn("10 AM", self.patient, t8_turn1['session_state'])
        self.assertEqual(t8_turn2['session_state']['workflow_step'], 'awaiting_confirmation')
        self.assertTrue(t8_turn2['confirmation_required'])
        self.assertIn("10:00 AM", t8_turn2['reply'])

        # Turn 3: User confirms "అవును" -> Booked!
        t8_turn3 = VoiceDialogueEngine.process_turn("అవును", self.patient, t8_turn2['session_state'])
        self.assertEqual(t8_turn3['action'], 'booking_completed')
        self.assertIn("successfully book", t8_turn3['reply'])
        self.assertIn("OPD టోకెన్", t8_turn3['reply'])

        # Test 9: Specific tablet purpose "ఈ tablet ఎందుకు వాడతారు?"
        t9 = VoiceDialogueEngine.process_turn("ఈ tablet ఎందుకు వాడతారు?", self.patient, {})
        self.assertEqual(t9['lang'], 'te-IN')
        self.assertIn("Dolo 650mg", t9['reply'])
        self.assertIn("Fever and pain relief", t9['reply'])

        # Test 10: Medicine timing without timing in prescription
        # Create prescription without timing
        p_no_time = Prescription.objects.create(patient=self.patient, medicine_name='Tab. Calcium 500mg', dosage='500mg', morning=False, afternoon=False, night=False, timing='', status='ACTIVE')
        t10 = VoiceDialogueEngine.process_turn("Tab. Calcium 500mg eppudu teesukovali?", self.patient, {})
        self.assertEqual(t10['lang'], 'te-IN')
        self.assertIn("timing కనిపించడం లేదు", t10['reply'])

        # Test 11: Vitals query "నా oxygen ఎంత ఉంది?"
        t11_o2 = VoiceDialogueEngine.process_turn("నా oxygen ఎంత ఉంది?", self.patient, {})
        self.assertEqual(t11_o2['lang'], 'te-IN')
        self.assertIn("98.5%", t11_o2['reply'])

        t11_sugar = VoiceDialogueEngine.process_turn("నా sugar ఎంత?", self.patient, {})
        self.assertEqual(t11_sugar['lang'], 'te-IN')
        self.assertIn("96.0 mg/dL", t11_sugar['reply'])

        # Test 12: Forbidden operation "నా account delete చేయి."
        t12 = VoiceDialogueEngine.process_turn("నా account delete చేయి.", self.patient, {})
        self.assertEqual(t12['status_indicator'], 'ERROR')
        self.assertIn("Account delete", t12['reply'])
        self.assertIn("క్షమించండి", t12['reply'])


