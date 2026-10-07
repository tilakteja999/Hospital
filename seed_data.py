"""
Seed data script for Indian Government Hospital Management Web Application.
Populates premier hospitals, doctors with registration IDs, linked users,
vitals telemetry history, hospital visits, prescriptions, and health notifications,
with rich appointment data for Admin analytics and Doctor portal queues.
"""

import os
import django
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_core.settings')
django.setup()

from core.models import User, AadhaarOTPRecord
from appointments.models import HospitalArea, HospitalFacility, DoctorProfile, AppointmentBooking
from patients.models import VitalRecord, HospitalVisit, Prescription, HealthNotification
from django.utils import timezone

def run_seed():
    print("Seeding Indian Government Hospital Data...")

    # 1. Create Default Users (Patient, Doctor, Admin + Extra Patients)
    patient, _ = User.objects.get_or_create(
        phone='9876543210',
        defaults={
            'username': '9876543210',
            'full_name': 'Ramesh Kumar Verma',
            'role': 'PATIENT',
            'aadhaar_number': '541287963214',
            'is_aadhaar_verified': True,
            'abha_id': 'ABHA-7845-9612',
            'gender': 'Male',
            'age': 34,
            'blood_group': 'B+',
            'city': 'New Delhi',
            'state': 'Delhi',
            'address': 'Flat 402, Block B, Pragati Vihar, New Delhi',
            'emergency_contact': '+91 9811223344',
            'preferred_language': 'Hindi'
        }
    )
    patient.set_password('pass123')
    patient.save()

    extra_patients = [
        {'phone': '9876543211', 'name': 'Sunita Devi', 'gender': 'Female', 'age': 48, 'blood': 'O+'},
        {'phone': '9876543212', 'name': 'Ankit Gupta', 'gender': 'Male', 'age': 29, 'blood': 'A+'},
        {'phone': '9876543213', 'name': 'Priya Sharma', 'gender': 'Female', 'age': 38, 'blood': 'B-'},
        {'phone': '9876543214', 'name': 'Mohammed Ali Khan', 'gender': 'Male', 'age': 55, 'blood': 'AB+'},
        {'phone': '9876543215', 'name': 'Rekha Patel', 'gender': 'Female', 'age': 42, 'blood': 'O-'},
        {'phone': '9876543216', 'name': 'Vikramaditya Rao', 'gender': 'Male', 'age': 63, 'blood': 'B+'},
    ]

    patient_objs = [patient]
    for ep in extra_patients:
        u, _ = User.objects.get_or_create(
            phone=ep['phone'],
            defaults={
                'username': ep['phone'],
                'full_name': ep['name'],
                'role': 'PATIENT',
                'gender': ep['gender'],
                'age': ep['age'],
                'blood_group': ep['blood'],
                'city': 'New Delhi',
                'state': 'Delhi'
            }
        )
        u.set_password('pass123')
        u.save()
        patient_objs.append(u)

    # Doctor User
    doctor_user, _ = User.objects.get_or_create(
        phone='9123456780',
        defaults={
            'username': '9123456780',
            'full_name': 'Dr. Rajesh Kumar Sharma',
            'role': 'DOCTOR',
            'gender': 'Male',
            'age': 46,
            'blood_group': 'O+',
            'city': 'New Delhi',
            'state': 'Delhi'
        }
    )
    doctor_user.set_password('doc123')
    doctor_user.save()

    # Admin User
    admin_user, _ = User.objects.get_or_create(
        phone='9998887770',
        defaults={
            'username': '9998887770',
            'full_name': 'Suresh Chandra IAS (Chief Health Administrator)',
            'role': 'ADMIN',
            'is_staff': True,
            'is_superuser': True,
            'gender': 'Male',
            'age': 52,
            'blood_group': 'A+'
        }
    )
    admin_user.set_password('admin123')
    admin_user.save()

    # 2. Populate Hospital Areas
    areas_data = [
        {'city': 'New Delhi', 'area_name': 'Ansari Nagar', 'state': 'Delhi', 'pincode': '110029'},
        {'city': 'New Delhi', 'area_name': 'Safdarjung Enclave', 'state': 'Delhi', 'pincode': '110029'},
        {'city': 'New Delhi', 'area_name': 'Connaught Place', 'state': 'Delhi', 'pincode': '110001'},
        {'city': 'New Delhi', 'area_name': 'Dwarka Sector 9', 'state': 'Delhi', 'pincode': '110077'},
        {'city': 'Bengaluru', 'area_name': 'Indiranagar', 'state': 'Karnataka', 'pincode': '560038'},
        {'city': 'Hyderabad', 'area_name': 'Secunderabad', 'state': 'Telangana', 'pincode': '500003'},
        {'city': 'Mumbai', 'area_name': 'Parel', 'state': 'Maharashtra', 'pincode': '400012'},
        {'city': 'Chandigarh', 'area_name': 'Sector 12', 'state': 'Chandigarh', 'pincode': '160012'},
    ]

    area_objs = {}
    for a in areas_data:
        obj, _ = HospitalArea.objects.get_or_create(city=a['city'], area_name=a['area_name'], defaults=a)
        area_objs[f"{a['city']}_{a['area_name']}"] = obj

    # 3. Populate Premier Government Hospitals
    hospitals_data = [
        {
            'name': 'All India Institute of Medical Sciences (AIIMS)',
            'area': area_objs['New Delhi_Ansari Nagar'],
            'facility_type': 'Apex Institute',
            'address': 'Sri Aurobindo Marg, Ansari Nagar, New Delhi',
            'contact_phone': '+91 11 26588500',
            'total_beds': 2478,
            'opd_timings': '08:00 AM - 01:00 PM (Mon-Sat)'
        },
        {
            'name': 'Safdarjung Hospital & VMMC',
            'area': area_objs['New Delhi_Safdarjung Enclave'],
            'facility_type': 'Central Govt',
            'address': 'Ring Road, Opposite AIIMS, New Delhi',
            'contact_phone': '+91 11 26165060',
            'total_beds': 1600,
            'opd_timings': '08:30 AM - 01:30 PM (Mon-Sat)'
        },
        {
            'name': 'Dr. Ram Manohar Lohia (RML) Hospital',
            'area': area_objs['New Delhi_Connaught Place'],
            'facility_type': 'Central Govt',
            'address': 'Baba Kharak Singh Marg, Connaught Place, New Delhi',
            'contact_phone': '+91 11 23365525',
            'total_beds': 1420,
            'opd_timings': '08:00 AM - 01:00 PM (Mon-Sat)'
        },
        {
            'name': 'Indira Gandhi Super Specialty Hospital',
            'area': area_objs['New Delhi_Dwarka Sector 9'],
            'facility_type': 'District Hospital',
            'address': 'Sector 9, Dwarka, New Delhi',
            'contact_phone': '+91 11 28050011',
            'total_beds': 1241,
            'opd_timings': '09:00 AM - 02:00 PM'
        },
        {
            'name': 'Victoria Hospital (BMCRI)',
            'area': area_objs['Bengaluru_Indiranagar'],
            'facility_type': 'Central Govt',
            'address': 'Fort Road, Near City Market, Bengaluru',
            'contact_phone': '+91 80 26701150',
            'total_beds': 1000,
            'opd_timings': '08:30 AM - 01:00 PM'
        },
        {
            'name': 'Gandhi Hospital & Medical College',
            'area': area_objs['Hyderabad_Secunderabad'],
            'facility_type': 'Central Govt',
            'address': 'Musheerabad, Secunderabad, Hyderabad',
            'contact_phone': '+91 40 27505566',
            'total_beds': 1800,
            'opd_timings': '08:00 AM - 02:00 PM'
        }
    ]

    hosp_objs = []
    for h in hospitals_data:
        obj, _ = HospitalFacility.objects.get_or_create(name=h['name'], defaults=h)
        hosp_objs.append(obj)

    # 3b. Populate Hospital Resources & Hospital Admin Accounts
    from appointments.models import HospitalResource, HospitalAdmin
    admin_phones = ['9811111111', '9822222222', '9833333333']
    for idx, hosp in enumerate(hosp_objs[:3]):
        # Hospital Resource
        HospitalResource.objects.get_or_create(
            hospital=hosp,
            defaults={
                'general_beds_total': 500 + idx*100,
                'general_beds_occupied': 320 + idx*60,
                'icu_beds_total': 80 + idx*20,
                'icu_beds_occupied': 65 + idx*15,
                'ventilator_beds_total': 40 + idx*10,
                'ventilator_beds_occupied': 25 + idx*5,
                'oxygen_beds_total': 200 + idx*50,
                'oxygen_beds_occupied': 140 + idx*30,
                'oxygen_supply_status': 'Normal (Pressure: 98%)'
            }
        )
        # Hospital Admin user
        p = admin_phones[idx]
        h_user, _ = User.objects.get_or_create(
            phone=p,
            defaults={
                'username': p,
                'full_name': f"Admin ({hosp.name[:25]})",
                'role': 'HOSPITAL',
                'email': f"admin@{hosp.name[:4].lower()}.gov.in"
            }
        )
        h_user.role = 'HOSPITAL'
        h_user.set_password('hospital123')
        h_user.save()
        HospitalAdmin.objects.get_or_create(user=h_user, hospital=hosp, defaults={'designation': 'Hospital Superintendent'})

    # 4. Populate Doctors
    aiims_hosp = hosp_objs[0]
    safdarjung_hosp = hosp_objs[1]
    rml_hosp = hosp_objs[2]

    doctors_data = [
        {
            'hospital': aiims_hosp,
            'doctor_reg_id': 'DOC-AIIMS-1049',
            'user': doctor_user,
            'name': 'Dr. Rajesh Kumar Sharma',
            'qualification': 'MBBS, MD (General Medicine), AIIMS',
            'department': 'General Medicine',
            'designation': 'Professor & Senior Consultant',
            'experience_years': 18,
            'available_days': 'Mon, Tue, Wed, Thu, Fri, Sat',
            'max_daily_slots': 35,
            'is_present_today': True,
            'is_active': True
        },
        {
            'hospital': aiims_hosp,
            'doctor_reg_id': 'DOC-AIIMS-2081',
            'name': 'Dr. Sunita Deshmukh',
            'qualification': 'MBBS, DM (Cardiology), AIIMS',
            'department': 'Cardiology',
            'designation': 'Senior Heart Specialist',
            'experience_years': 15,
            'available_days': 'Mon, Wed, Fri',
            'max_daily_slots': 25,
            'is_present_today': True,
            'is_active': True
        },
        {
            'hospital': aiims_hosp,
            'doctor_reg_id': 'DOC-AIIMS-3012',
            'name': 'Dr. Arvind Meena',
            'qualification': 'MBBS, MD (Pulmonology)',
            'department': 'Pulmonology',
            'designation': 'Respiratory & SpO2 Specialist',
            'experience_years': 12,
            'available_days': 'Tue, Thu, Sat',
            'max_daily_slots': 30,
            'is_present_today': True,
            'is_active': True
        },
        {
            'hospital': safdarjung_hosp,
            'doctor_reg_id': 'DOC-SFD-4055',
            'name': 'Dr. Priya Ananth',
            'qualification': 'MBBS, MD (Endocrinology & Diabetes)',
            'department': 'Endocrinology',
            'designation': 'Senior Medical Officer',
            'experience_years': 14,
            'available_days': 'Mon to Sat',
            'max_daily_slots': 40,
            'is_present_today': True,
            'is_active': True
        },
        {
            'hospital': safdarjung_hosp,
            'doctor_reg_id': 'DOC-SFD-5102',
            'name': 'Dr. Amitav Roy',
            'qualification': 'MBBS, MS (Orthopedics)',
            'department': 'Orthopedics',
            'designation': 'Joint Replacement & Trauma Specialist',
            'experience_years': 16,
            'available_days': 'Mon, Wed, Fri',
            'max_daily_slots': 30,
            'is_present_today': True,
            'is_active': True
        },
        {
            'hospital': rml_hosp,
            'doctor_reg_id': 'DOC-RML-6204',
            'name': 'Dr. Vikram Malhotra',
            'qualification': 'MBBS, MD (Pediatrics)',
            'department': 'Pediatrics',
            'designation': 'Head of Child Care',
            'experience_years': 11,
            'available_days': 'Mon to Sat',
            'max_daily_slots': 35,
            'is_present_today': False, # Off duty demo
            'is_active': True
        },
        {
            'hospital': aiims_hosp,
            'doctor_reg_id': 'DOC-AIIMS-7301',
            'name': 'Dr. Ananya Sengupta',
            'qualification': 'MBBS, MS (Obstetrics & Gynecology)',
            'department': 'Gynecology',
            'designation': 'Chief Gynecologist',
            'experience_years': 17,
            'available_days': 'Mon to Fri',
            'max_daily_slots': 30,
            'is_present_today': True,
            'is_active': True
        },
        {
            'hospital': aiims_hosp,
            'doctor_reg_id': 'DOC-AIIMS-8011',
            'name': 'Dr. Alok Verma',
            'qualification': 'MBBS, DM (Neurology)',
            'department': 'Neurology',
            'designation': 'Senior Neurologist & Brain Specialist',
            'experience_years': 19,
            'available_days': 'Mon, Tue, Thu, Fri',
            'max_daily_slots': 20,
            'is_present_today': True,
            'is_active': True
        },
        {
            'hospital': safdarjung_hosp,
            'doctor_reg_id': 'DOC-SFD-8022',
            'name': 'Dr. Meera Iyer',
            'qualification': 'MBBS, MD (Dermatology)',
            'department': 'Dermatology',
            'designation': 'Senior Dermatologist',
            'experience_years': 13,
            'available_days': 'Mon to Sat',
            'max_daily_slots': 35,
            'is_present_today': True,
            'is_active': True
        },
        {
            'hospital': rml_hosp,
            'doctor_reg_id': 'DOC-RML-8033',
            'name': 'Dr. Ramesh Chandra',
            'qualification': 'MBBS, DM (Nephrology)',
            'department': 'Nephrology',
            'designation': 'Kidney & Dialysis Specialist',
            'experience_years': 16,
            'available_days': 'Mon, Wed, Sat',
            'max_daily_slots': 25,
            'is_present_today': True,
            'is_active': True
        },
        {
            'hospital': aiims_hosp,
            'doctor_reg_id': 'DOC-AIIMS-8044',
            'name': 'Dr. Sanjeev Kapoor',
            'qualification': 'MBBS, DM (Gastroenterology)',
            'department': 'Gastroenterology',
            'designation': 'Gastrointestinal & Liver Specialist',
            'experience_years': 14,
            'available_days': 'Mon, Tue, Thu',
            'max_daily_slots': 25,
            'is_present_today': True,
            'is_active': True
        },
        {
            'hospital': safdarjung_hosp,
            'doctor_reg_id': 'DOC-SFD-8055',
            'name': 'Dr. Siddhartha Mukherjee',
            'qualification': 'MBBS, DM (Medical Oncology)',
            'department': 'Oncology',
            'designation': 'Senior Oncologist',
            'experience_years': 20,
            'available_days': 'Mon to Fri',
            'max_daily_slots': 20,
            'is_present_today': True,
            'is_active': True
        },
        {
            'hospital': rml_hosp,
            'doctor_reg_id': 'DOC-RML-8066',
            'name': 'Dr. Kavita Joshi',
            'qualification': 'MBBS, MS (ENT)',
            'department': 'ENT',
            'designation': 'ENT & Head Neck Surgeon',
            'experience_years': 10,
            'available_days': 'Mon to Sat',
            'max_daily_slots': 35,
            'is_present_today': True,
            'is_active': True
        },
        {
            'hospital': aiims_hosp,
            'doctor_reg_id': 'DOC-AIIMS-8077',
            'name': 'Dr. Harish Nambiar',
            'qualification': 'MBBS, MS (Ophthalmology)',
            'department': 'Ophthalmology',
            'designation': 'Chief Eye Surgeon',
            'experience_years': 15,
            'available_days': 'Mon to Fri',
            'max_daily_slots': 40,
            'is_present_today': True,
            'is_active': True
        },
        {
            'hospital': safdarjung_hosp,
            'doctor_reg_id': 'DOC-SFD-8088',
            'name': 'Dr. Devendra Reddy',
            'qualification': 'MBBS, MCh (Urology)',
            'department': 'Urology',
            'designation': 'Urologist & Renal Surgeon',
            'experience_years': 16,
            'available_days': 'Tue, Thu, Sat',
            'max_daily_slots': 25,
            'is_present_today': True,
            'is_active': True
        },
        {
            'hospital': rml_hosp,
            'doctor_reg_id': 'DOC-RML-8099',
            'name': 'Dr. Shalini Saxena',
            'qualification': 'MBBS, MD (Psychiatry)',
            'department': 'Psychiatry',
            'designation': 'Senior Psychiatrist',
            'experience_years': 12,
            'available_days': 'Mon to Fri',
            'max_daily_slots': 25,
            'is_present_today': True,
            'is_active': True
        },
        {
            'hospital': aiims_hosp,
            'doctor_reg_id': 'DOC-AIIMS-8100',
            'name': 'Dr. Manish Bhatia',
            'qualification': 'BDS, MDS (Maxillofacial Surgery)',
            'department': 'Dentistry',
            'designation': 'Senior Dental Surgeon',
            'experience_years': 14,
            'available_days': 'Mon to Sat',
            'max_daily_slots': 30,
            'is_present_today': True,
            'is_active': True
        },
        {
            'hospital': aiims_hosp,
            'doctor_reg_id': 'DOC-AIIMS-8111',
            'name': 'Dr. Subhash Chandra',
            'qualification': 'MBBS, MD (Radiology)',
            'department': 'Radiology',
            'designation': 'Head of Radiodiagnosis & CT/MRI',
            'experience_years': 18,
            'available_days': 'Mon to Sat',
            'max_daily_slots': 50,
            'is_present_today': True,
            'is_active': True
        },
        {
            'hospital': safdarjung_hosp,
            'doctor_reg_id': 'DOC-SFD-8122',
            'name': 'Dr. Rakesh Jhunjhunwala',
            'qualification': 'MBBS, MD (Emergency Medicine)',
            'department': 'Emergency Medicine',
            'designation': 'Chief Trauma Officer',
            'experience_years': 15,
            'available_days': '24x7 Duty Roster',
            'max_daily_slots': 60,
            'is_present_today': True,
            'is_active': True
        },
        {
            'hospital': rml_hosp,
            'doctor_reg_id': 'DOC-RML-8133',
            'name': 'Dr. Smita Kulkarni',
            'qualification': 'MBBS, MD (Anesthesiology)',
            'department': 'Anesthesiology',
            'designation': 'Chief Anesthesiologist & ICU Specialist',
            'experience_years': 17,
            'available_days': 'Mon to Sat',
            'max_daily_slots': 30,
            'is_present_today': True,
            'is_active': True
        }
    ]

    doc_objs = {}
    for d in doctors_data:
        obj, created = DoctorProfile.objects.update_or_create(
            name=d['name'],
            defaults=d
        )
        doc_objs[d['name']] = obj

    # 5. Populate Vitals History for Patient
    base_time = timezone.now()
    vitals_history = [
        {'days_ago': 28, 'bp_sys': 126, 'bp_dia': 84, 'o2': 97.5, 'sugar': 104.0, 'weight': 69.2, 'hb': 13.9, 'hr': 76, 'src': 'Hospital Lab', 'notes': 'Monthly Checkup - AIIMS OPD'},
        {'days_ago': 21, 'bp_sys': 124, 'bp_dia': 82, 'o2': 98.0, 'sugar': 99.0, 'weight': 68.8, 'hb': 14.0, 'hr': 74, 'src': 'Doctor Checkup', 'notes': 'Routine follow up'},
        {'days_ago': 14, 'bp_sys': 122, 'bp_dia': 80, 'o2': 98.5, 'sugar': 96.5, 'weight': 68.4, 'hb': 14.1, 'hr': 72, 'src': 'Hospital Lab', 'notes': 'Safdarjung OPD Telemetry'},
        {'days_ago': 7, 'bp_sys': 120, 'bp_dia': 80, 'o2': 99.0, 'sugar': 94.0, 'weight': 68.2, 'hb': 14.2, 'hr': 70, 'src': 'Doctor Checkup', 'notes': 'Stable parameters'},
        {'days_ago': 1, 'bp_sys': 118, 'bp_dia': 78, 'o2': 98.8, 'sugar': 92.0, 'weight': 68.0, 'hb': 14.2, 'hr': 72, 'src': 'Hospital Lab', 'notes': 'Latest Baseline OPD Assessment'}
    ]

    for v in vitals_history:
        rec_time = base_time - datetime.timedelta(days=v['days_ago'])
        VitalRecord.objects.get_or_create(
            patient=patient,
            recorded_at=rec_time,
            defaults={
                'bp_systolic': v['bp_sys'],
                'bp_diastolic': v['bp_dia'],
                'o2_saturation': v['o2'],
                'sugar_level': v['sugar'],
                'weight': v['weight'],
                'blood_percentage': v['hb'],
                'heart_rate': v['hr'],
                'source': v['src'],
                'notes': v['notes']
            }
        )

    # 6. Populate Hospital Visits & Medical Reports
    latest_vital_obj = VitalRecord.objects.filter(patient=patient).first()
    visits_data = [
        {
            'patient': patient,
            'hospital_name': 'All India Institute of Medical Sciences (AIIMS) New Delhi',
            'department': 'General Medicine & Family Health',
            'doctor_name': 'Dr. Rajesh Kumar Sharma',
            'visit_date': datetime.date.today() - datetime.timedelta(days=14),
            'reason_for_visit': 'Quarterly Routine Health & Vitals Assessment',
            'diagnosis': 'Clinical parameters healthy and stable. Optimal cardiovascular and pulmonary function.',
            'treatment_summary': 'Maintain balanced diet, 30 mins brisk walking daily, and seasonal hydration.',
            'lab_reports_summary': 'CBC normal (Hb 14.2 g/dL), Fasting Blood Glucose 95 mg/dL, Lipid Profile within healthy limits.',
            'follow_up_date': datetime.date.today() + datetime.timedelta(days=75),
            'vitals_snapshot': latest_vital_obj
        },
        {
            'patient': patient,
            'hospital_name': 'Safdarjung Hospital & VMMC New Delhi',
            'department': 'Pulmonology (Respiratory Care)',
            'doctor_name': 'Dr. Arvind Meena',
            'visit_date': datetime.date.today() - datetime.timedelta(days=45),
            'reason_for_visit': 'Seasonal respiratory checkup and cough evaluation',
            'diagnosis': 'Mild upper respiratory allergic irritation. Lungs clear, SpO2 98%.',
            'treatment_summary': 'Steam inhalation, warm saline gargles, and 5-day course of anti-allergic tablet.',
            'lab_reports_summary': 'Chest X-Ray normal, SpO2 resting 98%, Pulse regular.',
            'follow_up_date': None,
            'vitals_snapshot': latest_vital_obj
        }
    ]

    for vis in visits_data:
        HospitalVisit.objects.get_or_create(patient=vis['patient'], visit_date=vis['visit_date'], defaults=vis)

    from patients.models import RadiologyReport

    # 7. Populate Prescriptions with Tablet Purpose
    rx_data = [
        {
            'patient': patient,
            'medicine_name': 'Tab. Paracetamol 650mg (Dolo)',
            'purpose': 'Fever Reduction & Body Pain Relief (बुखार एवं दर्द निवारक)',
            'dosage': '1 Tablet As Needed',
            'form': 'Tablet',
            'morning': True,
            'afternoon': True,
            'night': True,
            'timing': 'After Food',
            'duration_days': 5,
            'instructions': 'Take after food when fever exceeds 99.5°F or body pain occurs.',
            'prescribed_by': 'Dr. Rajesh Kumar Sharma (AIIMS)'
        },
        {
            'patient': patient,
            'medicine_name': 'Tab. Multivitamin & Zinc Forte',
            'purpose': 'Immunity Booster & Cellular Nutrition (रोग प्रतिरोधक क्षमता वृद्धि)',
            'dosage': '1 Tablet Daily',
            'form': 'Tablet',
            'morning': True,
            'afternoon': False,
            'night': False,
            'timing': 'After Food',
            'duration_days': 30,
            'instructions': 'Take after breakfast with water for general immunity.',
            'prescribed_by': 'Dr. Rajesh Kumar Sharma (AIIMS)'
        },
        {
            'patient': patient,
            'medicine_name': 'Tab. Calcium & Vitamin D3 500mg',
            'purpose': 'Bone Strength & Calcium Supplement (हड्डियों की मजबूती)',
            'dosage': '1 Tablet Daily',
            'form': 'Tablet',
            'morning': False,
            'afternoon': False,
            'night': True,
            'timing': 'After Food',
            'duration_days': 30,
            'instructions': 'Take with warm milk/water before bedtime.',
            'prescribed_by': 'Dr. Amitav Roy (Safdarjung Hospital)'
        },
        {
            'patient': patient,
            'medicine_name': 'Tab. Pantoprazole 40mg (Pan-40)',
            'purpose': 'Acid Reflux & Gastric Protection (पेट की गैस एवं एसिडिटी कम करना)',
            'dosage': '1 Tablet Daily',
            'form': 'Tablet',
            'morning': True,
            'afternoon': False,
            'night': False,
            'timing': 'Before Food',
            'duration_days': 14,
            'instructions': 'Take on empty stomach 30 mins before morning breakfast.',
            'prescribed_by': 'Dr. Sanjeev Kapoor (AIIMS)'
        }
    ]

    for rx in rx_data:
        Prescription.objects.get_or_create(patient=rx['patient'], medicine_name=rx['medicine_name'], defaults=rx)

    # 7.1 Populate Radiology Reports (X-Ray, CT Scan, MRI, Ultrasound)
    radiology_data = [
        {
            'patient': patient,
            'report_title': 'Digital Chest X-Ray PA View',
            'modality': 'X-Ray',
            'body_part': 'Thorax & Lungs',
            'report_date': datetime.date.today() - datetime.timedelta(days=12),
            'hospital_name': 'All India Institute of Medical Sciences (AIIMS) Radiology Dept',
            'radiologist_name': 'Dr. Subhash Chandra (MD Radiodiagnosis)',
            'findings': 'Both lung fields are clear and well expanded. Bronchovascular markings are normal. Cardiac silhouette is of normal size and contour. Costophrenic and cardiophrenic angles are sharp and clear. Bony thorax shows no osteolytic lesions or fracture.',
            'impression': 'NORMAL CHEST RADIOGRAPH. No active parenchymal pulmonary lesion or pleural effusion.',
            'image_svg': 'chest_xray'
        },
        {
            'patient': patient,
            'report_title': 'High-Resolution HRCT Chest (Non-Contrast)',
            'modality': 'CT Scan',
            'body_part': 'Chest & Parenchyma',
            'report_date': datetime.date.today() - datetime.timedelta(days=40),
            'hospital_name': 'Safdarjung Hospital Imaging Center',
            'radiologist_name': 'Dr. Subhash Chandra (MD Radiology)',
            'findings': 'HRCT sections of chest reveal normal lung attenuation bilaterally. No ground glass opacities, consolidation or honeycombing seen. Tracheobronchial tree is normal in caliber and outline. Mediastinal lymph nodes are within normal size range (<10mm).',
            'impression': 'NORMAL HRCT CHEST STUDY. Absence of pulmonary fibrosis, interstitial lung disease, or nodules.',
            'image_svg': 'ct_chest'
        },
        {
            'patient': patient,
            'report_title': 'Brain MRI 1.5T Non-Contrast Study',
            'modality': 'MRI',
            'body_part': 'Brain & Cranium',
            'report_date': datetime.date.today() - datetime.timedelta(days=85),
            'hospital_name': 'AIIMS Neuroimaging Center',
            'radiologist_name': 'Dr. Subhash Chandra (MD Radiology)',
            'findings': 'T1, T2, and FLAIR MRI sequences demonstrate normal cerebral hemisphere architecture. Ventricles and sulci are normal for age. No restricted diffusion or microvascular ischemia. Brainstem and cerebellum appear normal.',
            'impression': 'UNREMARKABLE BRAIN MRI. Normal neuro-parenchymal parenchyma.',
            'image_svg': 'mri_brain'
        },
        {
            'patient': patient,
            'report_title': 'Whole Abdomen Ultrasound & Sonography',
            'modality': 'Ultrasound',
            'body_part': 'Abdomen & Pelvis',
            'report_date': datetime.date.today() - datetime.timedelta(days=120),
            'hospital_name': 'Dr. RML Hospital Ultrasound Wing',
            'radiologist_name': 'Dr. Subhash Chandra (MD Radiology)',
            'findings': 'Liver is normal in size (13.5cm) with smooth margins and normal echotexture. Gallbladder is well distended, lumen is clear, no calculi or wall thickening. Kidneys are normal in size (Right 10.2cm, Left 10.5cm) with maintained corticomedullary differentiation.',
            'impression': 'NORMAL ABDOMINAL USG. No gallstones, renal calculi, or ascites.',
            'image_svg': 'usg_abdomen'
        }
    ]

    for rad in radiology_data:
        RadiologyReport.objects.get_or_create(patient=rad['patient'], report_title=rad['report_title'], defaults=rad)

    # 8. Populate Appointments (Today Completed, Today Uncompleted, Previous)
    today = datetime.date.today()
    doc_rajesh = doc_objs['Dr. Rajesh Kumar Sharma']
    doc_sunita = doc_objs['Dr. Sunita Deshmukh']
    doc_arvind = doc_objs['Dr. Arvind Meena']
    doc_priya = doc_objs['Dr. Priya Ananth']
    doc_amitav = doc_objs['Dr. Amitav Roy']
    doc_ananya = doc_objs['Dr. Ananya Sengupta']

    # Clear previous appointments for clean seed state
    AppointmentBooking.objects.all().delete()

    # A) Dr. Rajesh Sharma - Today COMPLETED appointments (4 patients taken today until present time)
    completed_today_data = [
        {'pat': patient_objs[1], 'slot': '08:30 AM - 09:00 AM', 'tok': 1, 'sym': 'Mild fever and body pain', 'notes': 'Prescribed Paracetamol 650mg, vitals normal. Advised rest.'},
        {'pat': patient_objs[2], 'slot': '09:00 AM - 09:30 AM', 'tok': 2, 'sym': 'Routine BP monitoring', 'notes': 'BP 124/82 mmHg. Continue current antihypertensive medication.'},
        {'pat': patient_objs[3], 'slot': '09:30 AM - 10:00 AM', 'tok': 3, 'sym': 'Gastric discomfort & acidity', 'notes': 'Advised Tab Pantoprazole 40mg before breakfast, dietary changes.'},
        {'pat': patient_objs[4], 'slot': '10:00 AM - 10:30 AM', 'tok': 4, 'sym': 'Seasonal allergy and sneezing', 'notes': 'Prescribed Cetirizine 10mg at bedtime, steam inhalation.'},
    ]

    for c in completed_today_data:
        AppointmentBooking.objects.create(
            patient=c['pat'],
            doctor=doc_rajesh,
            hospital=aiims_hosp,
            appointment_date=today,
            time_slot=c['slot'],
            token_number=c['tok'],
            symptoms=c['sym'],
            consultation_notes=c['notes'],
            status='COMPLETED',
            completed_at=timezone.now() - datetime.timedelta(hours=4 - c['tok']),
            booking_reference=f"GOI-APT-{today.year}-{80000 + c['tok']}"
        )

    # B) Dr. Rajesh Sharma - Today UNCOMPLETED / PENDING / IN-QUEUE appointments
    pending_today_data = [
        {'pat': patient_objs[0], 'slot': '11:00 AM - 11:30 AM', 'tok': 5, 'sym': 'General Health Assessment & Blood Test Review'},
        {'pat': patient_objs[5], 'slot': '11:30 AM - 12:00 PM', 'tok': 6, 'sym': 'Persistent joint stiffness and fatigue'},
        {'pat': patient_objs[6], 'slot': '12:00 PM - 12:30 PM', 'tok': 7, 'sym': 'Follow-up for diabetes management & HbA1c'},
    ]

    for p in pending_today_data:
        AppointmentBooking.objects.create(
            patient=p['pat'],
            doctor=doc_rajesh,
            hospital=aiims_hosp,
            appointment_date=today,
            time_slot=p['slot'],
            token_number=p['tok'],
            symptoms=p['sym'],
            status='CONFIRMED',
            booking_reference=f"GOI-APT-{today.year}-{80010 + p['tok']}"
        )

    # D) Seed Lab Tests Catalog & Orders
    from patients.models import (
        LabTest, LabOrder, DischargeSummary, VaccinationRecord,
        EmergencyProfile, ConsentRecord, MedicationDoseLog
    )
    from core.models import HealthScheme, HealthAdvisory, AuditLog

    print("Seeding Lab Tests Catalog...")
    lab_tests_data = [
        {'name': 'Complete Blood Count (CBC)', 'code': 'LAB-CBC-01', 'category': 'Hematology', 'unit': 'g/dL', 'reference_range': 'Hb: 12-16 g/dL, WBC: 4000-11000/mcL', 'sample_type': 'Venous Whole Blood', 'turnaround_hours': 4, 'description': 'Complete hematology profile'},
        {'name': 'Lipid Profile Panel', 'code': 'LAB-LIP-02', 'category': 'Biochemistry', 'unit': 'mg/dL', 'reference_range': 'Total Chol: <200, HDL: >40, LDL: <100', 'sample_type': 'Fasting Serum', 'turnaround_hours': 8, 'description': 'Cholesterol & triglyceride panel'},
        {'name': 'Liver Function Test (LFT)', 'code': 'LAB-LFT-03', 'category': 'Biochemistry', 'unit': 'U/L', 'reference_range': 'SGOT: 5-40 U/L, SGPT: 7-56 U/L', 'sample_type': 'Venous Serum', 'turnaround_hours': 6, 'description': 'Hepatic enzyme profile'},
        {'name': 'Kidney Function Test (KFT)', 'code': 'LAB-KFT-04', 'category': 'Biochemistry', 'unit': 'mg/dL', 'reference_range': 'Creatinine: 0.7-1.3 mg/dL, Urea: 15-40', 'sample_type': 'Venous Serum', 'turnaround_hours': 6, 'description': 'Renal panel'},
        {'name': 'Glycated Hemoglobin (HbA1c)', 'code': 'LAB-HBA1C-05', 'category': 'Biochemistry', 'unit': '%', 'reference_range': 'Normal: <5.7%, Pre-diabetic: 5.7-6.4%', 'sample_type': 'Whole Blood (EDTA)', 'turnaround_hours': 4, 'description': 'Long term glycemic index'},
        {'name': 'Thyroid Stimulating Hormone (TSH)', 'code': 'LAB-TSH-06', 'category': 'Biochemistry', 'unit': 'mIU/L', 'reference_range': 'TSH: 0.4-4.0 mIU/L', 'sample_type': 'Venous Serum', 'turnaround_hours': 12, 'description': 'Thyroid function test'},
        {'name': 'Chest X-Ray Digital PA View', 'code': 'RAD-CXR-07', 'category': 'Imaging', 'unit': 'Radiograph', 'reference_range': 'Clear lung fields, normal CTR', 'sample_type': 'Digital Radiography', 'turnaround_hours': 2, 'description': 'Thoracic radiographic imaging'},
    ]

    lab_objs = []
    for lt in lab_tests_data:
        obj, _ = LabTest.objects.get_or_create(name=lt['name'], defaults=lt)
        lab_objs.append(obj)

    # Seed Lab Orders for main patient
    LabOrder.objects.get_or_create(
        patient=patient,
        test=lab_objs[0], # CBC
        defaults={
            'doctor_name': 'Dr. Rajesh Kumar Sharma',
            'hospital_name': 'All India Institute of Medical Sciences (AIIMS)',
            'status': 'COMPLETED',
            'result_value': '13.8 (Normal Hb)',
            'unit': 'g/dL',
            'reference_range': '12.0 - 16.0 g/dL',
            'notes': 'All cell counts within standard healthy reference limits.',
            'result_date': timezone.now() - datetime.timedelta(days=12)
        }
    )

    LabOrder.objects.get_or_create(
        patient=patient,
        test=lab_objs[1], # Lipid Profile
        defaults={
            'doctor_name': 'Dr. Rajesh Kumar Sharma',
            'hospital_name': 'All India Institute of Medical Sciences (AIIMS)',
            'status': 'COMPLETED',
            'result_value': '182 (Desirable)',
            'unit': 'mg/dL',
            'reference_range': 'Total Chol < 200 mg/dL',
            'notes': 'HDL 46 mg/dL, LDL 104 mg/dL. 12 Hours overnight fasting verified.',
            'result_date': timezone.now() - datetime.timedelta(days=28)
        }
    )

    LabOrder.objects.get_or_create(
        patient=patient,
        test=lab_objs[4], # HbA1c
        defaults={
            'doctor_name': 'Dr. Rajesh Kumar Sharma',
            'hospital_name': 'All India Institute of Medical Sciences (AIIMS)',
            'status': 'PROCESSING',
            'notes': 'Rule out glycemic variability'
        }
    )

    # E) Seed Digital Discharge Summary for main patient
    print("Seeding Digital Discharge Summary...")
    DischargeSummary.objects.get_or_create(
        patient=patient,
        admission_date=datetime.date(2026, 7, 10),
        defaults={
            'doctor_name': 'Dr. Rajesh Kumar Sharma',
            'doctor_reg_no': 'DOC-AIIMS-1001',
            'hospital_name': 'All India Institute of Medical Sciences (AIIMS)',
            'discharge_date': datetime.date(2026, 7, 14),
            'department': 'General Medicine & Critical Care',
            'reason_for_admission': 'Severe emesis, dehydration, and acute gastrointestinal discomfort',
            'clinical_findings': 'Afebrile, BP 110/72, HR 88 bpm. Mild epigastric tenderness on palpation.',
            'diagnosis': 'Acute Viral Gastroenteritis with Moderate Dehydration',
            'procedures_treatment': 'IV Ringer Lactate fluid resuscitation, Ondansetron IV, and Oral Rehydration Therapy.',
            'investigation_results': 'CBC: Hb 14.1 g/dL, WBC 8,400. S. Electrolytes: Na 137, K 3.9 mEq/L (Normal).',
            'condition_at_discharge': 'Stable and Ambulatory (स्थिर एवं स्वस्थ)',
            'discharge_medicines': '1. Tab Pantoprazole 40mg (1-0-0) x 5 days\n2. ORS Hydration Sachet SOS\n3. Cap Pre & Probiotic (0-0-1) x 7 days',
            'diet_instructions': 'Light semi-solid khichdi and clear soups for 48 hours. Avoid oily, spicy food.',
            'activity_instructions': 'Light walking permitted. Avoid heavy lifting and strenuous workouts for 7 days.',
            'follow_up_instructions': 'Review in OPD Room 102 after 10 days or SOS if fever recurs.',
            'follow_up_date': datetime.date(2026, 7, 24)
        }
    )

    # F) Seed Immunization / Vaccination Records for main patient
    print("Seeding Vaccination Registry...")
    vac_data = [
        {'name': 'COVID-19 (Covishield / ChAdOx1)', 'dose': 1, 'batch': 'COV-4491-A', 'date': datetime.date(2021, 4, 15)},
        {'name': 'COVID-19 (Covishield / ChAdOx1)', 'dose': 2, 'batch': 'COV-8821-B', 'date': datetime.date(2021, 7, 10)},
        {'name': 'COVID-19 Precautionary Dose (Booster)', 'dose': 3, 'batch': 'COV-9902-C', 'date': datetime.date(2022, 6, 20)},
        {'name': 'Tetanus Toxoid (TT)', 'dose': 1, 'batch': 'TT-3301-DEL', 'date': datetime.date(2025, 11, 5)},
        {'name': 'Hepatitis B Recombinant', 'dose': 1, 'batch': 'HEP-5520-X', 'date': datetime.date(2026, 1, 10), 'next_due': datetime.date(2026, 10, 10)},
    ]
    for vd in vac_data:
        VaccinationRecord.objects.get_or_create(
            patient=patient,
            vaccine_name=vd['name'],
            dose_number=vd['dose'],
            defaults={
                'batch_number': vd['batch'],
                'provider_name': 'Dr. Rajesh Kumar Sharma',
                'hospital_center': 'All India Institute of Medical Sciences (AIIMS)',
                'date_given': vd['date'],
                'next_due_date': vd.get('next_due'),
                'status': 'COMPLETED'
            }
        )

    # G) Seed Emergency Profile for main patient
    print("Seeding Emergency Profile...")
    EmergencyProfile.objects.get_or_create(
        patient=patient,
        defaults={
            'contact_name': 'Kavita Verma (Spouse)',
            'relationship': 'Spouse / Primary Contact',
            'phone_number': '+91 9811223344',
            'blood_group': 'B+',
            'known_allergies': 'Penicillin, Sulfa Drugs (Causes Urticaria)',
            'important_current_meds': 'Tab. Telmisartan 40mg OD, Levocetirizine 5mg PRN',
            'major_medical_conditions': 'Mild Essential Hypertension, Seasonal Asthma',
            'preferred_hospital': 'AIIMS Apex Trauma Center, New Delhi',
            'emergency_hotline': '108 (Ambulance) / 112 (National Emergency)'
        }
    )

    # H) Seed Consent Records
    print("Seeding Consent Ledger...")
    ConsentRecord.objects.get_or_create(
        patient=patient,
        doctor_name='Dr. Rajesh Kumar Sharma',
        defaults={
            'doctor_reg_id': 'DOC-AIIMS-1001',
            'hospital_name': 'All India Institute of Medical Sciences (AIIMS)',
            'status': 'GRANTED',
            'scope_medical_history': True,
            'scope_lab_reports': True,
            'scope_prescriptions': True,
            'scope_other_records': True,
            'purpose': 'Comprehensive annual health assessment & OPD consultation review',
            'valid_until': timezone.now() + datetime.timedelta(days=7),
            'actioned_at': timezone.now() - datetime.timedelta(hours=2)
        }
    )

    # I) Seed Government Health Schemes & Advisories
    print("Seeding Health Schemes & Advisories...")
    schemes = [
        {
            'name': 'Ayushman Bharat Pradhan Mantri Jan Arogya Yojana (AB-PMJAY)',
            'code': 'PMJAY',
            'subtitle': 'National Health Protection Scheme',
            'description': 'World’s largest government-sponsored health assurance scheme offering cashless health cover to bottom 40% vulnerable population.',
            'eligibility': 'Identified poor & vulnerable families based on SECC 2011 rural and urban occupational criteria.',
            'benefits': 'Cashless coverage of up to ₹5,00,000 per family per year for secondary and tertiary care hospitalization.',
            'required_documents': 'Aadhaar Card, Ration Card, PM-JAY Family Letter',
            'official_portal_url': 'https://pmjay.gov.in',
            'helpline': '14555 / 1800-111-565',
            'is_active': True
        },
        {
            'name': 'Ayushman Bharat Digital Mission (ABDM / ABHA)',
            'code': 'ABDM',
            'subtitle': 'National Digital Health Infrastructure',
            'description': 'Creates a seamless online platform to connect digital health solutions across healthcare stakeholders in India.',
            'eligibility': 'All Indian citizens with a valid Aadhaar number and registered mobile phone.',
            'benefits': '14-digit unique ABHA ID, consolidated digital health records, and seamless interoperability across hospitals.',
            'required_documents': 'Aadhaar Number and Mobile Number for OTP Verification',
            'official_portal_url': 'https://abdm.gov.in',
            'helpline': '1800-11-4477',
            'is_active': True
        },
        {
            'name': 'Pradhan Mantri Surakshit Matritva Abhiyan (PMSMA)',
            'code': 'PMSMA',
            'subtitle': 'Universal Antenatal Care Guarantee',
            'description': 'Ensures comprehensive and quality antenatal care free of cost to all pregnant women on the 9th of every month.',
            'eligibility': 'All pregnant women in their 2nd and 3rd trimesters visiting public health facilities.',
            'benefits': 'Free sonography, hemoglobin check, tetanus immunization, and high-risk pregnancy specialist care.',
            'required_documents': 'Mother and Child Protection (MCP) Card, Aadhaar Card',
            'official_portal_url': 'https://pmsma.mohfw.gov.in',
            'helpline': '104 / 1075',
            'is_active': True
        },
        {
            'name': 'National Health Mission (NHM) Free Drugs & Diagnostics',
            'code': 'NHM-FREE',
            'subtitle': 'Universal Essential Medicines Access',
            'description': 'Initiative to eliminate out-of-pocket expenditure on essential medicines and diagnostic laboratory tests.',
            'eligibility': 'All OPD and IPD patients visiting public health facilities across India.',
            'benefits': '100% free essential medicines (EDL) and standard pathology/radiology investigations in government hospitals.',
            'required_documents': 'Government Hospital OPD Registration Slip',
            'official_portal_url': 'https://nhm.gov.in',
            'helpline': '1075',
            'is_active': True
        }
    ]
    for s in schemes:
        HealthScheme.objects.get_or_create(code=s['code'], defaults=s)

    advisories = [
        {
            'title': 'Seasonal Dengue & Chikungunya Vector-Borne Advisory',
            'category': 'Seasonal Health',
            'priority': 'HIGH',
            'description': 'Monsoon and post-monsoon conditions have elevated mosquito breeding rates. Check domestic water storage and coolers weekly.',
            'precaution_points': 'Prevent water stagnation in indoor plants/coolers.\nUse mosquito repellents and mosquito nets.\nReport unremitting high fever to government OPD.',
            'status': 'ACTIVE'
        },
        {
            'title': 'National Deworming & Anemia Mukt Bharat Mission Alert',
            'category': 'Nutrition',
            'priority': 'NORMAL',
            'description': 'Free biannual Albendazole deworming tablets and Iron-Folic Acid syrups available at all Anganwadis and Primary Health Centers.',
            'precaution_points': 'Ensure children aged 1-19 receive supervised deworming dose.\nConsume iron-rich leafy vegetables and vitamin C.',
            'status': 'ACTIVE'
        },
        {
            'title': 'Air Quality Index (AQI) & Respiratory Health Advisory',
            'category': 'Respiratory Health',
            'priority': 'URGENT',
            'description': 'Elevated PM2.5 levels observed. Asthmatic patients and elderly citizens advised to limit strenuous outdoor morning activities.',
            'precaution_points': 'Keep prescribed bronchodilator inhalers accessible.\nWear N95 masks during heavy smog hours.\nConsult government pulmonology OPD if breathlessness worsens.',
            'status': 'ACTIVE'
        }
    ]
    for adv in advisories:
        HealthAdvisory.objects.get_or_create(title=adv['title'], defaults=adv)

    # J) Seed Immutable Audit Logs
    print("Seeding Audit Trail...")
    audit_samples = [
        {'user': admin_user, 'role': 'ADMIN', 'action': 'SYSTEM_SECURITY', 'resource': 'System', 'ip': '127.0.0.1', 'details': 'Admin authenticated via secure portal credentials'},
        {'user': doctor_user, 'role': 'DOCTOR', 'action': 'VIEW_RECORD', 'resource': 'PatientRecord', 'ip': '192.168.1.104', 'details': f'Dr. Rajesh viewed vitals and labs for patient {patient.phone}'},
        {'user': doctor_user, 'role': 'DOCTOR', 'action': 'UPDATE_QUEUE_STATUS', 'resource': 'AppointmentBooking', 'ip': '192.168.1.104', 'details': 'Doctor called token A-005 in Room 102'},
        {'user': patient, 'role': 'PATIENT', 'action': 'GRANT_CONSENT', 'resource': 'ConsentRecord', 'ip': '49.36.128.4', 'details': 'Citizen approved 7-day EHR access for Dr. Rajesh Sharma'},
        {'user': doctor_user, 'role': 'DOCTOR', 'action': 'CREATE_DISCHARGE_SUMMARY', 'resource': 'DischargeSummary', 'ip': '192.168.1.104', 'details': 'Issued signed discharge summary GOI-DS-2026-AIIMS-994821'},
    ]
    for a in audit_samples:
        AuditLog.objects.get_or_create(
            user=a['user'],
            action=a['action'],
            details=a['details'],
            defaults={
                'user_display': a['user'].get_display_name() if a['user'] else 'System',
                'role': a['role'],
                'resource_type': a['resource'],
                'ip_address': a['ip'],
                'status': 'SUCCESS'
            }
        )

    print("[OK] All 10 healthcare features fully seeded successfully!")

if __name__ == '__main__':
    run_seed()


