import os
import django
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_core.settings')
django.setup()

from appointments.models import Specialty, HospitalArea, HospitalFacility, DoctorProfile

SPECIALTIES_LIST = [
    ("General Medicine", "General Medicine & Family Health", "🩺"),
    ("Family Medicine", "Comprehensive Primary Care for Families", "👨‍👩‍👧‍👦"),
    ("Cardiology", "Cardiology & Heart Care", "❤️"),
    ("Cardiothoracic Surgery", "Heart & Chest Surgical Care", "🫀"),
    ("Neurology", "Neurology & Brain Sciences", "🧠"),
    ("Neurosurgery", "Surgical Brain & Spine Care", "🧠"),
    ("Orthopedics", "Orthopedics & Joint Care", "🦴"),
    ("General Surgery", "General & Laparoscopic Surgical Sciences", "✂️"),
    ("Pediatrics", "Pediatrics & Child Health", "👶"),
    ("Neonatology", "Newborn & Infant Intensive Care", "🍼"),
    ("Obstetrics and Gynecology", "Women's Health & Maternal Care", "🤰"),
    ("Gynecology", "Gynecological & Women Health Care", "👩"),
    ("Oncology", "Oncology & Cancer Treatment", "🎗️"),
    ("Radiation Oncology", "Radiation Cancer Therapy", "☢️"),
    ("Gastroenterology", "Gastroenterology & Digestive Health", "🫁"),
    ("Hepatology", "Liver Diseases & Hepatobiliary Care", "🩺"),
    ("Nephrology", "Nephrology & Renal Kidney Care", "🩺"),
    ("Urology", "Urology & Genitourinary Surgery", "🩺"),
    ("Pulmonology", "Pulmonology & Respiratory Medicine", "🫁"),
    ("Endocrinology", "Endocrinology & Hormone Care", "🩸"),
    ("Dermatology", "Dermatology & Skin Sciences", "✨"),
    ("Psychiatry", "Psychiatry & Mental Health Sciences", "🧠"),
    ("Psychology", "Clinical Psychology & Behavioral Health", "💭"),
    ("Ophthalmology", "Ophthalmology & Eye Care", "👁️"),
    ("ENT", "ENT & Otolaryngology Care", "👂"),
    ("Dentistry", "Dental Sciences & Maxillofacial Care", "🦷"),
    ("Oral and Maxillofacial Surgery", "Maxillofacial Surgical Specialties", "🦷"),
    ("Rheumatology", "Arthritis & Autoimmune Care", "🦴"),
    ("Hematology", "Blood Disorders & Hematology", "🩸"),
    ("Infectious Disease", "Infectious & Communicable Disease Care", "🦠"),
    ("Emergency Medicine", "Trauma & Emergency Casualty Care", "🚨"),
    ("Anesthesiology", "Anesthesia & Perioperative Care", "💉"),
    ("Radiology", "Radiology & Diagnostic Imaging", "🩻"),
    ("Pathology", "Laboratory Pathology & Tissue Diagnostics", "🔬"),
    ("Physical Medicine and Rehabilitation", "Physiotherapy & Rehabilitation", "♿"),
    ("Geriatrics", "Elderly & Geriatric Healthcare", "👴"),
    ("Pain Medicine", "Interventional Pain Management", "💊"),
    ("Critical Care", "ICU & Critical Care Medicine", "🏥"),
    ("Diabetology", "Diabetes & Metabolic Care", "🩸"),
    ("Pulmonary Medicine", "Pulmonary & Lung Health", "🫁"),
]

def seed_specialties():
    print("Seeding Specialties...")
    created_count = 0
    for name, desc, icon in SPECIALTIES_LIST:
        spec, created = Specialty.objects.get_or_create(
            name=name,
            defaults={'description': desc, 'icon': icon}
        )
        if created:
            created_count += 1
    print(f"Total Specialties in DB: {Specialty.objects.count()} (Created {created_count})")

def seed_hospitals_and_locations():
    print("Seeding Hospitals and Locations...")
    sample_data = [
        # Palnadu / Narasaraopet / Guntur (Andhra Pradesh)
        {
            "city": "Narasaraopet",
            "area_name": "Palnadu Road",
            "state": "Andhra Pradesh",
            "pincode": "522601",
            "district": "Palnadu District",
            "hospital_name": "Government General Hospital Narasaraopet",
            "facility_type": "District Hospital",
            "address": "Opposite RTC Bus Stand, Palnadu Road, Narasaraopet",
            "contact_phone": "+91 8647 222100",
            "emergency": True,
            "beds": 350,
            "lat": 16.2354,
            "lng": 80.0494
        },
        {
            "city": "Narasaraopet",
            "area_name": "Brodipet Area",
            "state": "Andhra Pradesh",
            "pincode": "522601",
            "district": "Palnadu District",
            "hospital_name": "Palnadu Area Multispecialty Govt Hospital",
            "facility_type": "District Hospital",
            "address": "Brodipet Extension, Near Clock Tower, Narasaraopet",
            "contact_phone": "+91 8647 224500",
            "emergency": True,
            "beds": 200,
            "lat": 16.2410,
            "lng": 80.0560
        },
        {
            "city": "Guntur",
            "area_name": "Collectorate Road",
            "state": "Andhra Pradesh",
            "pincode": "522002",
            "district": "Guntur District",
            "hospital_name": "Guntur Government Medical College & Hospital",
            "facility_type": "Apex Institute",
            "address": "Collectorate Road, Kothapeta, Guntur",
            "contact_phone": "+91 863 2220100",
            "emergency": True,
            "beds": 1200,
            "lat": 16.3067,
            "lng": 80.4365
        },
        {
            "city": "Guntur",
            "area_name": "Brodipet Guntur",
            "state": "Andhra Pradesh",
            "pincode": "522002",
            "district": "Guntur District",
            "hospital_name": "ABC Care Super Specialty Hospital",
            "facility_type": "Central Govt",
            "address": "4th Line Brodipet, Guntur",
            "contact_phone": "+91 863 2345678",
            "emergency": True,
            "beds": 300,
            "lat": 16.3008,
            "lng": 80.4420
        },

        # New Delhi
        {
            "city": "New Delhi",
            "area_name": "Ansari Nagar",
            "state": "Delhi",
            "pincode": "110029",
            "district": "South Delhi",
            "hospital_name": "All India Institute of Medical Sciences (AIIMS)",
            "facility_type": "Apex Institute",
            "address": "Sri Aurobindo Marg, Ansari Nagar, New Delhi",
            "contact_phone": "+91 11 26588500",
            "emergency": True,
            "beds": 2500,
            "lat": 28.5672,
            "lng": 77.2100
        },
        {
            "city": "New Delhi",
            "area_name": "Safdarjung Enclave",
            "state": "Delhi",
            "pincode": "110029",
            "district": "South Delhi",
            "hospital_name": "Vardhman Mahavir Medical College & Safdarjung Hospital",
            "facility_type": "Central Govt",
            "address": "Ring Road, Opposite AIIMS, New Delhi",
            "contact_phone": "+91 11 26165060",
            "emergency": True,
            "beds": 1800,
            "lat": 28.5695,
            "lng": 77.2065
        },
        {
            "city": "New Delhi",
            "area_name": "Connaught Place",
            "state": "Delhi",
            "pincode": "110001",
            "district": "Central Delhi",
            "hospital_name": "Dr. Ram Manohar Lohia (RML) Hospital",
            "facility_type": "Central Govt",
            "address": "Baba Kharak Singh Marg, Connaught Place, New Delhi",
            "contact_phone": "+91 11 23365525",
            "emergency": True,
            "beds": 1400,
            "lat": 28.6258,
            "lng": 77.2023
        },

        # Bengaluru
        {
            "city": "Bengaluru",
            "area_name": "Victoria Hospital Campus",
            "state": "Karnataka",
            "pincode": "560002",
            "district": "Bengaluru Urban",
            "hospital_name": "Bangalore Medical College & Victoria Hospital",
            "facility_type": "Central Govt",
            "address": "Fort, Near KR Market, Bengaluru",
            "contact_phone": "+91 80 26701150",
            "emergency": True,
            "beds": 1200,
            "lat": 12.9632,
            "lng": 77.5740
        },

        # Hyderabad
        {
            "city": "Hyderabad",
            "area_name": "Punjagutta",
            "state": "Telangana",
            "pincode": "500082",
            "district": "Hyderabad",
            "hospital_name": "Nizam's Institute of Medical Sciences (NIMS)",
            "facility_type": "Apex Institute",
            "address": "Punjagutta, Hyderabad, Telangana",
            "contact_phone": "+91 40 23489000",
            "emergency": True,
            "beds": 1500,
            "lat": 17.4243,
            "lng": 78.4520
        },

        # Mumbai
        {
            "city": "Mumbai",
            "area_name": "Parel",
            "state": "Maharashtra",
            "pincode": "400012",
            "district": "Mumbai City",
            "hospital_name": "King Edward Memorial (KEM) Hospital",
            "facility_type": "Central Govt",
            "address": "Acharya Donde Marg, Parel, Mumbai",
            "contact_phone": "+91 22 24107000",
            "emergency": True,
            "beds": 1800,
            "lat": 19.0022,
            "lng": 72.8423
        }
    ]

    for item in sample_data:
        area, _ = HospitalArea.objects.get_or_create(
            city=item['city'],
            area_name=item['area_name'],
            defaults={'state': item['state'], 'pincode': item['pincode']}
        )
        facility, created = HospitalFacility.objects.get_or_create(
            name=item['hospital_name'],
            defaults={
                'area': area,
                'facility_type': item['facility_type'],
                'address': item['address'],
                'contact_phone': item['contact_phone'],
                'emergency_available': item['emergency'],
                'total_beds': item['beds'],
                'latitude': item['lat'],
                'longitude': item['lng'],
                'city': item['city'],
                'district': item['district'],
                'state': item['state'],
                'pincode': item['pincode']
            }
        )
        if not created:
            facility.latitude = item['lat']
            facility.longitude = item['lng']
            facility.city = item['city']
            facility.district = item['district']
            facility.state = item['state']
            facility.pincode = item['pincode']
            facility.save()

    print(f"Total Hospitals in DB: {HospitalFacility.objects.count()}")

def link_doctors_to_specialties_and_hospitals():
    print("Linking Doctors to Specialties and Hospitals...")
    specs = list(Specialty.objects.all())
    doctors = DoctorProfile.objects.all()

    for doc in doctors:
        # Match specialty_ref by department or specialization
        matched_spec = None
        for s in specs:
            if s.name.lower() in doc.department.lower() or doc.department.lower() in s.name.lower():
                matched_spec = s
                break
        if not matched_spec and specs:
            matched_spec = specs[0]

        doc.specialty_ref = matched_spec
        doc.save()

    # Ensure doctors exist for key hospitals (Narasaraopet, Guntur, AIIMS, etc.)
    all_hospitals = HospitalFacility.objects.all()
    dept_choices = [
        ("General Medicine", "Dr. A. Sharma", "MBBS, MD (Medicine)"),
        ("Cardiology", "Dr. K. V. Rao", "MBBS, DM (Cardiology)"),
        ("Neurology", "Dr. S. Mukherjee", "MBBS, DM (Neurology)"),
        ("Orthopedics", "Dr. R. P. Patel", "MBBS, MS (Orthopedics)"),
        ("Pediatrics", "Dr. M. K. Anitha", "MBBS, MD (Pediatrics)"),
        ("Dermatology", "Dr. Priya Sundaram", "MBBS, MD (Dermatology)"),
        ("Gastroenterology", "Dr. T. N. Reddy", "MBBS, DM (Gastroenterology)"),
        ("Obstetrics and Gynecology", "Dr. L. Lakshmi", "MBBS, MS (OBG)"),
        ("ENT", "Dr. V. K. Gupta", "MBBS, MS (ENT)"),
        ("Ophthalmology", "Dr. S. K. Verma", "MBBS, MS (Ophthalmology)"),
    ]

    for hosp in all_hospitals:
        if hosp.doctors.count() < 3:
            for dept, d_name, d_qual in dept_choices[:5]:
                spec_obj = Specialty.objects.filter(name=dept).first()
                reg_id = f"DOC-{hosp.name[:3].upper()}-{random.randint(1000,9999)}"
                DoctorProfile.objects.create(
                    hospital=hosp,
                    doctor_reg_id=reg_id,
                    name=f"{d_name} ({hosp.get_city()[:3]})",
                    qualification=d_qual,
                    specialization=dept,
                    department=dept,
                    specialty_ref=spec_obj,
                    designation="Consultant Specialist",
                    experience_years=random.randint(8, 20),
                    available_days="Mon, Tue, Wed, Thu, Fri, Sat",
                    consultation_room=f"Room {random.randint(101, 305)}",
                    opd_start_time="09:00 AM",
                    opd_end_time="01:00 PM",
                    status="ACTIVE",
                    is_active=True,
                    is_present_today=True
                )

    print("Doctors successfully updated and linked!")

if __name__ == '__main__':
    seed_specialties()
    seed_hospitals_and_locations()
    link_doctors_to_specialties_and_hospitals()
    print("ALL SEEDING COMPLETED SUCCESSFULLY!")
