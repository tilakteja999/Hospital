from django.test import TestCase, Client
from django.urls import reverse
from core.models import User, AadhaarOTPRecord
from patients.models import VitalRecord, HospitalVisit, Prescription, HealthNotification
from appointments.models import HospitalArea, HospitalFacility, DoctorProfile, AppointmentBooking
import json
import datetime

class HospitalPlatformTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create Patient User
        self.patient = User.objects.create_user(
            phone='9876543210',
            password='pass123',
            full_name='Ramesh Kumar Verma',
            role='PATIENT',
            aadhaar_number='541287963214',
            is_aadhaar_verified=True,
            abha_id='ABHA-1234-5678'
        )

        # Create Area, Hospital & Doctor
        self.area = HospitalArea.objects.create(city='New Delhi', area_name='Ansari Nagar', pincode='110029')
        self.hospital = HospitalFacility.objects.create(
            name='All India Institute of Medical Sciences (AIIMS)',
            area=self.area,
            facility_type='Apex Institute',
            address='Ansari Nagar, New Delhi'
        )
        self.doctor = DoctorProfile.objects.create(
            hospital=self.hospital,
            name='Dr. Rajesh Kumar Sharma',
            department='General Medicine',
            max_daily_slots=35
        )

        # Baseline Vitals
        self.vital = VitalRecord.objects.create(
            patient=self.patient,
            bp_systolic=120,
            bp_diastolic=80,
            o2_saturation=98.5,
            sugar_level=95.0,
            weight=68.0,
            blood_percentage=14.2,
            heart_rate=72
        )

    def test_role_portal_view(self):
        response = self.client.get(reverse('role_portal'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hospital Government of India')
        self.assertContains(response, 'Patient Portal')
        self.assertContains(response, 'Doctor Portal')
        self.assertContains(response, 'Admin Portal')

    def test_patient_login(self):
        response = self.client.post(reverse('patient_login'), {
            'phone': '9876543210',
            'password': 'pass123'
        })
        self.assertEqual(response.status_code, 302) # Redirect to dashboard

    def test_aadhaar_otp_generation_and_verification(self):
        # 1. Generate OTP
        gen_res = self.client.post(
            reverse('api_aadhaar_generate_otp'),
            data=json.dumps({'aadhaar_number': '123456789012', 'phone': '9876543210'}),
            content_type='application/json'
        )
        gen_data = gen_res.json()
        self.assertTrue(gen_data['success'])
        otp = gen_data['demo_otp']

        # 2. Verify OTP
        ver_res = self.client.post(
            reverse('api_aadhaar_verify_otp'),
            data=json.dumps({'aadhaar_number': '123456789012', 'otp': otp}),
            content_type='application/json'
        )
        ver_data = ver_res.json()
        self.assertTrue(ver_data['success'])

    def test_vitals_telemetry_api(self):
        self.client.login(phone='9876543210', password='pass123')
        response = self.client.get(reverse('api_get_vitals'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['latest']['bp_systolic'], 120)
        self.assertEqual(data['latest']['o2_saturation'], 98.5)

    def test_appointment_booking_and_slot_check(self):
        self.client.login(phone='9876543210', password='pass123')
        target_date = (datetime.date.today() + datetime.timedelta(days=2)).strftime('%Y-%m-%d')
        
        response = self.client.post(
            reverse('api_check_and_book'),
            data=json.dumps({
                'hospital_id': self.hospital.id,
                'doctor_id': self.doctor.id,
                'date': target_date,
                'time_slot': '09:30 AM - 10:00 AM',
                'symptoms': 'General OPD Health Check'
            }),
            content_type='application/json'
        )
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'ACCEPTED')
        self.assertTrue('001' in str(data['booking']['token_number']) or data['booking']['token_number'] == 1)

    def test_auto_locate_me_api(self):
        # 1. Default lookup
        res1 = self.client.get(reverse('api_locate_me'))
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertTrue(data1['success'])
        self.assertEqual(data1['detected_location']['city'], 'New Delhi')

        # 2. GPS Coords lookup
        res2 = self.client.get(reverse('api_locate_me') + '?lat=28.6139&lng=77.2090')
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertTrue(data2['success'])
        self.assertEqual(data2['detected_location']['city'], 'New Delhi')
        self.assertIn('AIIMS', data2['recommended_hospital']['name'])

    def test_admin_doctor_management_and_stats(self):
        # Create Admin
        admin_user = User.objects.create_superuser(phone='9999999999', password='adminpass123', full_name='Chief Medical Director')
        self.client.login(phone='9999999999', password='adminpass123')

        # 1. Add Doctor via Admin API
        add_res = self.client.post(
            reverse('api_admin_add_doctor'),
            data=json.dumps({
                'name': 'Dr. Ananya Iyer',
                'doctor_reg_id': 'DOC-CARD-8801',
                'department': 'Cardiology',
                'hospital_id': self.hospital.id,
                'qualification': 'MBBS, MD, DM (Cardiology)',
                'designation': 'Associate Professor',
                'experience_years': 14,
                'max_daily_slots': 40,
                'available_days': 'Mon, Wed, Fri'
            }),
            content_type='application/json'
        )
        self.assertEqual(add_res.status_code, 200)
        add_data = add_res.json()
        self.assertTrue(add_data['success'])
        new_doc_id = add_data['doctor']['id']

        # 2. Toggle Presence
        toggle_res = self.client.post(
            reverse('api_admin_toggle_doctor_presence', kwargs={'doctor_id': new_doc_id}),
            content_type='application/json'
        )
        self.assertEqual(toggle_res.status_code, 200)
        self.assertFalse(toggle_res.json()['is_present_today'])

        # 3. Check Specialization Stats API
        stats_res = self.client.get(reverse('api_admin_stats'))
        self.assertEqual(stats_res.status_code, 200)
        stats_data = stats_res.json()
        self.assertTrue(stats_data['success'])
        self.assertGreaterEqual(stats_data['total_doctors'], 2)

        # 4. Remove Doctor
        rem_res = self.client.post(
            reverse('api_admin_remove_doctor', kwargs={'doctor_id': new_doc_id}),
            content_type='application/json'
        )
        self.assertEqual(rem_res.status_code, 200)
        self.assertTrue(rem_res.json()['success'])

    def test_doctor_portal_consultation_completion(self):
        # Create Doctor User
        doc_user = User.objects.create_user(phone='8888888888', password='docpass123', full_name='Dr. Rajesh Kumar Sharma', role='DOCTOR')
        self.doctor.user = doc_user
        self.doctor.save()

        # Create Appointment Booking
        today = datetime.date.today()
        booking = AppointmentBooking.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            hospital=self.hospital,
            appointment_date=today,
            time_slot='10:00 AM - 10:30 AM',
            token_number=1,
            symptoms='Chest discomfort and elevated BP'
        )

        self.client.login(phone='8888888888', password='docpass123')

        # Complete consultation via Doctor API
        comp_res = self.client.post(
            reverse('api_doctor_mark_completed', kwargs={'booking_id': booking.id}),
            data=json.dumps({
                'consultation_notes': 'ECG Normal Sinus Rhythm. Prescribed Tab. Telmisartan 40mg.',
                'medicine_name': 'Tab. Telmisartan 40mg',
                'dosage': '1 Tablet Morning',
                'duration_days': 14
            }),
            content_type='application/json'
        )
        self.assertEqual(comp_res.status_code, 200)
        comp_data = comp_res.json()
        self.assertTrue(comp_data['success'])
        self.assertEqual(comp_data['status'], 'COMPLETED')

        # Verify prescription created for patient
        self.assertTrue(Prescription.objects.filter(patient=self.patient, medicine_name='Tab. Telmisartan 40mg').exists())

