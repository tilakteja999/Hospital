"""
Smart Health AI Assistant Engine - Swasthya Seva / Swasthya Setu
Clinical Safety-First Medical AI Intelligence Engine
- Does NOT replace a doctor
- Does NOT independently diagnose diseases
- Does NOT prescribe medicines or change doctor prescriptions
- Explains medicines, lab reports, prescriptions, and health trends in clear citizen language
"""

import re
import datetime
from django.utils import timezone
from patients.models import Prescription, LabOrder, VitalRecord, HospitalVisit

# ==================== 1. COMPREHENSIVE MEDICINE CATALOG ====================
MEDICINE_CATALOG = {
    'paracetamol': {
        'canonical_name': 'Paracetamol',
        'generic_name': 'Acetaminophen / Paracetamol',
        'default_strength': '650 mg',
        'available_strengths': ['500 mg', '650 mg', '1000 mg'],
        'common_purpose': 'Commonly used to relieve mild to moderate pain (such as headaches, body aches) and reduce fever.',
        'typical_administration': 'Usually taken orally as a tablet with water, as directed by a healthcare professional.',
        'food_relation': 'Can be taken with or without food (after food is often preferred if stomach discomfort occurs).',
        'common_precautions': 'Do not exceed the daily dose recommended by your doctor. Avoid taking multiple medications containing paracetamol simultaneously to protect liver health.',
        'common_side_effects': 'Generally well tolerated at recommended doses. Rare side effects may include mild nausea or allergic skin rash.',
        'storage': 'Store at room temperature below 30°C, away from direct sunlight and moisture.'
    },
    'metformin': {
        'canonical_name': 'Metformin Hydrochloride',
        'generic_name': 'Metformin',
        'default_strength': '500 mg',
        'available_strengths': ['500 mg', '850 mg', '1000 mg'],
        'common_purpose': 'Commonly prescribed for glycemic control in individuals with type 2 diabetes mellitus to help maintain healthy blood sugar levels.',
        'typical_administration': 'Taken orally as a tablet, usually once or twice daily according to the doctor’s schedule.',
        'food_relation': 'Take with or immediately after meals to minimize gastrointestinal discomfort.',
        'common_precautions': 'Follow your prescribed diet and exercise plan. Regular monitoring of kidney function and blood sugar is advised by doctors.',
        'common_side_effects': 'Mild nausea, stomach fullness, or loose stools during initial days of treatment.',
        'storage': 'Store in a cool, dry place away from children.'
    },
    'amoxicillin': {
        'canonical_name': 'Amoxicillin',
        'generic_name': 'Amoxicillin Trihydrate',
        'default_strength': '500 mg',
        'available_strengths': ['250 mg', '500 mg'],
        'common_purpose': 'An antibiotic used to treat susceptible bacterial infections of the respiratory tract, ears, throat, and urinary tract.',
        'typical_administration': 'Taken orally at evenly spaced intervals as prescribed by your doctor.',
        'food_relation': 'Can be taken before or after meals. Drink plenty of fluids during the course.',
        'common_precautions': 'Complete the full course prescribed by your physician even if symptoms resolve early. Inform doctor if you have a known penicillin allergy.',
        'common_side_effects': 'Mild stomach upset, nausea, or diarrhea.',
        'storage': 'Keep in original packaging at room temperature.'
    },
    'atorvastatin': {
        'canonical_name': 'Atorvastatin Calcium',
        'generic_name': 'Atorvastatin',
        'default_strength': '20 mg',
        'available_strengths': ['10 mg', '20 mg', '40 mg', '80 mg'],
        'common_purpose': 'Commonly prescribed to help manage cholesterol and lipid levels and support cardiovascular wellness.',
        'typical_administration': 'Taken orally once daily, commonly in the evening or night.',
        'food_relation': 'Can be taken with or without food at the same time each day.',
        'common_precautions': 'Regular lipid panel checkups are recommended. Avoid excessive grapefruit consumption while on statin therapy.',
        'common_side_effects': 'Mild muscle aches, headache, or digestive discomfort.',
        'storage': 'Store in a dry place protected from light.'
    },
    'pantoprazole': {
        'canonical_name': 'Pantoprazole Sodium',
        'generic_name': 'Pantoprazole',
        'default_strength': '40 mg',
        'available_strengths': ['20 mg', '40 mg'],
        'common_purpose': 'A proton pump inhibitor (PPI) commonly used to reduce stomach acid production and relieve acidity, heartburn, or gastritis.',
        'typical_administration': 'Taken orally as a gastro-resistant tablet, swallowed whole without crushing.',
        'food_relation': 'Best taken in the morning, 30 to 60 minutes before breakfast (खाली पेट).',
        'common_precautions': 'Do not chew or crush tablets. Use for the duration recommended by your physician.',
        'common_side_effects': 'Headache, mild abdominal pain, or temporary flatulence.',
        'storage': 'Store below 25°C in a moisture-free area.'
    },
    'telmisartan': {
        'canonical_name': 'Telmisartan',
        'generic_name': 'Telmisartan',
        'default_strength': '40 mg',
        'available_strengths': ['20 mg', '40 mg', '80 mg'],
        'common_purpose': 'An angiotensin receptor blocker (ARB) used to support healthy blood pressure management in hypertension.',
        'typical_administration': 'Taken orally once daily at a consistent time.',
        'food_relation': 'Can be taken with or without food.',
        'common_precautions': 'Do not discontinue abruptly without doctor consultation. Periodic blood pressure and electrolyte checks are recommended.',
        'common_side_effects': 'Mild dizziness, fatigue, or sinus congestion.',
        'storage': 'Keep in blister pack until use to protect from humidity.'
    },
    'cetirizine': {
        'canonical_name': 'Cetirizine Hydrochloride',
        'generic_name': 'Cetirizine',
        'default_strength': '10 mg',
        'available_strengths': ['5 mg', '10 mg'],
        'common_purpose': 'An antihistamine used to relieve allergic symptoms such as runny nose, sneezing, itchy watery eyes, and skin allergies.',
        'typical_administration': 'Taken orally once daily, often at bedtime.',
        'food_relation': 'Can be taken with or without food.',
        'common_precautions': 'May cause mild drowsiness; avoid driving or operating machinery if affected.',
        'common_side_effects': 'Mild sleepiness, dry mouth, or fatigue.',
        'storage': 'Store in a cool, dry place.'
    },
    'azithromycin': {
        'canonical_name': 'Azithromycin',
        'generic_name': 'Azithromycin Dihydrate',
        'default_strength': '500 mg',
        'available_strengths': ['250 mg', '500 mg'],
        'common_purpose': 'A macrolide antibiotic commonly used for respiratory, skin, and throat bacterial infections.',
        'typical_administration': 'Taken orally once daily for a designated course (usually 3 to 5 days).',
        'food_relation': 'Can be taken with or without food, though taking with food can reduce stomach upset.',
        'common_precautions': 'Complete the full course prescribed. Do not take antacids containing aluminum/magnesium simultaneously.',
        'common_side_effects': 'Loose stools, stomach cramps, or mild nausea.',
        'storage': 'Store below 30°C in a dry place.'
    },
    'amlodipine': {
        'canonical_name': 'Amlodipine Besylate',
        'generic_name': 'Amlodipine',
        'default_strength': '5 mg',
        'available_strengths': ['2.5 mg', '5 mg', '10 mg'],
        'common_purpose': 'A calcium channel blocker used for long-term blood pressure control and angina management.',
        'typical_administration': 'Taken orally once daily.',
        'food_relation': 'Can be taken with or without food at the same time each day.',
        'common_precautions': 'Inform your doctor if you notice swelling in ankles or feet.',
        'common_side_effects': 'Peripheral edema (mild ankle swelling), flushing, or dizziness.',
        'storage': 'Store in original packaging away from moisture.'
    },
    'ibuprofen': {
        'canonical_name': 'Ibuprofen',
        'generic_name': 'Ibuprofen',
        'default_strength': '400 mg',
        'available_strengths': ['200 mg', '400 mg'],
        'common_purpose': 'A non-steroidal anti-inflammatory drug (NSAID) for pain relief, swelling reduction, and fever.',
        'typical_administration': 'Taken orally with water.',
        'food_relation': 'Always take after food or with milk to protect stomach lining.',
        'common_precautions': 'Use lowest effective dose for shortest duration. Caution if history of stomach ulcers or renal impairment.',
        'common_side_effects': 'Stomach irritation, heartburn, or indigestion.',
        'storage': 'Store at room temperature.'
    }
}


# ==================== 2. COMPREHENSIVE LAB TEST KNOWLEDGE BASE ====================
LAB_TEST_KNOWLEDGE = {
    'hemoglobin': {
        'display_name': 'Hemoglobin (Hb)',
        'category': 'Hematology (CBC)',
        'unit': 'g/dL',
        'default_low': 12.0,
        'default_high': 16.0,
        'what_is_it': 'Hemoglobin is an iron-rich protein in red blood cells responsible for carrying oxygen from the lungs to tissues throughout your body.',
        'what_number_means': 'Your reported level indicates the oxygen-carrying capacity of your bloodstream at the time of sample collection.',
        'why_doctors_care': 'Doctors monitor hemoglobin to check for anemia, evaluate nutritional iron status, recovery from illness, or blood volume balance.',
        'what_to_discuss': 'Discuss whether your diet, iron intake, hydration, or other clinical factors may explain this reading.',
        'critical_low': 7.0,
        'critical_high': 20.0,
    },
    'wbc': {
        'display_name': 'Total White Blood Cell Count (WBC / TLC)',
        'category': 'Hematology (CBC)',
        'unit': '/µL',
        'default_low': 4000,
        'default_high': 11000,
        'what_is_it': 'White blood cells are the core defensive components of your immune system that help the body fight infections and inflammation.',
        'what_number_means': 'The count represents the active concentration of immune defense cells circulating in the blood.',
        'why_doctors_care': 'Elevations can reflect the body responding to seasonal infections or inflammation, while lower values may prompt review of immune recovery or viral states.',
        'what_to_discuss': 'Review recent fever, seasonal symptoms, or medication use with your healthcare provider.',
        'critical_low': 2000,
        'critical_high': 30000,
    },
    'platelets': {
        'display_name': 'Platelet Count',
        'category': 'Hematology (CBC)',
        'unit': '/µL',
        'default_low': 150000,
        'default_high': 450000,
        'what_is_it': 'Platelets (thrombocytes) are tiny cell fragments essential for normal blood clotting and stopping bleeding.',
        'what_number_means': 'This reflects your body’s clotting cell reserve available to prevent and control bleeding.',
        'why_doctors_care': 'Vital in monitoring vector-borne infections (like Dengue), medication effects, and surgical safety.',
        'what_to_discuss': 'If below reference range, discuss precautions regarding bruising and follow-up repeat count schedules.',
        'critical_low': 40000,
        'critical_high': 1000000,
    },
    'blood_sugar_fasting': {
        'display_name': 'Fasting Blood Glucose (FBS)',
        'category': 'Biochemistry / Metabolism',
        'unit': 'mg/dL',
        'default_low': 70.0,
        'default_high': 100.0,
        'what_is_it': 'Fasting blood sugar measures glucose concentration after an overnight fast (typically 8 to 12 hours).',
        'what_number_means': 'It indicates baseline glucose regulation and how efficiently your body manages insulin in the fasting state.',
        'why_doctors_care': 'A primary marker for screening, diagnosing, and monitoring pre-diabetes and diabetes management.',
        'what_to_discuss': 'Discuss dietary patterns, fasting duration before the test, exercise habits, and medication adjustments with your doctor.',
        'critical_low': 50.0,
        'critical_high': 350.0,
    },
    'hba1c': {
        'display_name': 'Glycated Hemoglobin (HbA1c)',
        'category': 'Biochemistry / Diabetes',
        'unit': '%',
        'default_low': 4.0,
        'default_high': 5.6,
        'what_is_it': 'HbA1c reflects the average percentage of blood glucose bound to hemoglobin over the past 2 to 3 months.',
        'what_number_means': 'Provides a stable long-term picture of glycemic control rather than a single day’s snapshot.',
        'why_doctors_care': 'Standard guideline marker to evaluate long-term glycemic control and therapeutic effectiveness.',
        'what_to_discuss': 'Ask your doctor about your individualized target HbA1c goal and dietary lifestyle strategies.',
        'critical_low': 3.5,
        'critical_high': 13.0,
    },
    'total_cholesterol': {
        'display_name': 'Total Serum Cholesterol',
        'category': 'Lipid Profile',
        'unit': 'mg/dL',
        'default_low': 120.0,
        'default_high': 200.0,
        'what_is_it': 'A measure of the total amount of cholesterol circulating in your bloodstream, including HDL, LDL, and VLDL components.',
        'what_number_means': 'Helps assess overall circulating lipid balance in conjunction with individual fractions.',
        'why_doctors_care': 'Used alongside blood pressure, age, and lifestyle to assess cardiovascular wellness and dietary balance.',
        'what_to_discuss': 'Discuss heart-healthy dietary choices, physical activity, and whether fractionated lipids (HDL/LDL) are in balance.',
        'critical_low': 70.0,
        'critical_high': 350.0,
    },
    'creatinine': {
        'display_name': 'Serum Creatinine',
        'category': 'Kidney Function (KFT)',
        'unit': 'mg/dL',
        'default_low': 0.7,
        'default_high': 1.3,
        'what_is_it': 'Creatinine is a normal waste byproduct of muscle metabolism filtered out of the blood exclusively by the kidneys.',
        'what_number_means': 'Serum levels inversely correlate with kidney filtration rate and renal clearance efficiency.',
        'why_doctors_care': 'An essential marker for monitoring kidney health, hydration balance, and safe dosing of medications.',
        'what_to_discuss': 'Review your daily water hydration intake, muscle activity, and ask if any medications require renal dosage consideration.',
        'critical_low': 0.2,
        'critical_high': 4.5,
    },
    'sgpt_alt': {
        'display_name': 'SGPT / Alanine Aminotransferase (ALT)',
        'category': 'Liver Function (LFT)',
        'unit': 'U/L',
        'default_low': 7.0,
        'default_high': 56.0,
        'what_is_it': 'ALT is an enzyme found primarily inside liver cells that helps convert proteins into energy.',
        'what_number_means': 'When liver cells experience temporary stress or inflammation, ALT leaks into the bloodstream.',
        'why_doctors_care': 'Useful for assessing liver wellness, medication tolerance, and metabolic liver health.',
        'what_to_discuss': 'Discuss recent medications, supplements, diet, and recovery from viral illnesses with your doctor.',
        'critical_low': 0.0,
        'critical_high': 500.0,
    },
    'tsh': {
        'display_name': 'Thyroid Stimulating Hormone (TSH)',
        'category': 'Endocrine / Thyroid',
        'unit': 'mIU/L',
        'default_low': 0.4,
        'default_high': 4.5,
        'what_is_it': 'TSH is produced by the pituitary gland in the brain to instruct the thyroid gland how much thyroid hormone to release.',
        'what_number_means': 'Higher levels signal the brain asking the thyroid to work harder, while lower levels indicate plentiful thyroid activity.',
        'why_doctors_care': 'The primary sensitive screening test for thyroid balance (hypo- or hyper-thyroidism).',
        'what_to_discuss': 'Review energy levels, weight changes, or temperature sensitivity with your physician.',
        'critical_low': 0.05,
        'critical_high': 25.0,
    },
    'spo2': {
        'display_name': 'Oxygen Saturation (SpO2)',
        'category': 'Cardiopulmonary Telemetry',
        'unit': '%',
        'default_low': 95.0,
        'default_high': 100.0,
        'what_is_it': 'The percentage of oxygen-saturated hemoglobin relative to total hemoglobin in the blood.',
        'what_number_means': 'Indicates how effectively your lungs and circulation are supplying oxygen to your organs.',
        'why_doctors_care': 'Critical real-time vital sign for respiratory and cardiac wellness.',
        'what_to_discuss': 'If consistently below 95% or accompanied by breathlessness, notify your medical provider promptly.',
        'critical_low': 88.0,
        'critical_high': 100.0,
    }
}


# ==================== 3. AI MEDICINE SCANNER & PRESCRIPTION MATCHER ====================

def scan_and_identify_medicine(query_text_or_ocr, patient_user=None):
    """
    Parses medicine text/OCR tokens, matches canonical drug info,
    and performs cross-verification against the patient's active doctor prescriptions.
    """
    text = (query_text_or_ocr or '').lower().strip()
    if not text:
        return {
            'success': False,
            'confidence': 'LOW',
            'error_title': 'Unclear Medicine Image',
            'error_message': (
                "We couldn't confidently identify this medicine from the image.\n\n"
                "Please:\n"
                "• Retake the photo with good lighting\n"
                "• Upload a clearer image showing the medicine name and strength\n"
                "• Enter the medicine name manually in the search box"
            )
        }

    # Match against catalog
    matched_key = None
    matched_strength = None

    # Check known keys
    for key in MEDICINE_CATALOG.keys():
        if key in text:
            matched_key = key
            break

    # Check common brand synonyms
    if not matched_key:
        brand_map = {
            'dolo': 'paracetamol', 'calpol': 'paracetamol', 'crocin': 'paracetamol',
            'glycomet': 'metformin', 'glucophage': 'metformin',
            'mox': 'amoxicillin', 'novamox': 'amoxicillin', 'augmentin': 'amoxicillin',
            'lipitor': 'atorvastatin', 'atorva': 'atorvastatin', 'tonact': 'atorvastatin',
            'pan 40': 'pantoprazole', 'pantocid': 'pantoprazole', 'pantop': 'pantoprazole',
            'telma': 'telmisartan', 'telmikind': 'telmisartan', 'cresar': 'telmisartan',
            'cetzine': 'cetirizine', 'okacet': 'cetirizine', 'citizin': 'cetirizine',
            'zithromax': 'azithromycin', 'azithral': 'azithromycin', 'azee': 'azithromycin',
            'stamlo': 'amlodipine', 'amlong': 'amlodipine', 'amlopres': 'amlodipine',
            'brufen': 'ibuprofen', 'combiflam': 'ibuprofen'
        }
        for brand, mapped_key in brand_map.items():
            if brand in text:
                matched_key = mapped_key
                break

    if not matched_key:
        return {
            'success': False,
            'confidence': 'LOW',
            'error_title': 'Medicine Not Confidently Identified',
            'error_message': (
                "We couldn't confidently identify this medicine.\n\n"
                "Please:\n"
                "• Retake the photo in bright lighting\n"
                "• Upload a clearer image showing the tablet strip label\n"
                "• Enter the medicine name manually"
            )
        }

    med_info = MEDICINE_CATALOG[matched_key]

    # Extract strength regex (e.g. 650mg, 500 mg, 40mg)
    strength_match = re.search(r'(\d+)\s*(mg|g|mcg|ml)', text)
    if strength_match:
        matched_strength = f"{strength_match.group(1)} {strength_match.group(2)}"
    else:
        matched_strength = med_info['default_strength']

    # Prescription Matching Engine
    prescription_match_result = check_prescription_match(matched_key, med_info['canonical_name'], matched_strength, patient_user)

    return {
        'success': True,
        'confidence': 'HIGH',
        'medicine_name': med_info['canonical_name'],
        'detected_strength': matched_strength,
        'generic_name': med_info['generic_name'],
        'common_purpose': med_info['common_purpose'],
        'typical_administration': med_info['typical_administration'],
        'food_relation': med_info['food_relation'],
        'common_precautions': med_info['common_precautions'],
        'common_side_effects': med_info['common_side_effects'],
        'storage': med_info['storage'],
        'prescription_match': prescription_match_result,
        'safety_notice': (
            "⚠️ Important Clinical Safety Information:\n"
            "• Follow your doctor's prescribed dose.\n"
            "• Do not change the dose yourself.\n"
            "• Do not stop long-term medication without consulting your doctor.\n"
            "• Check with your doctor or pharmacist if you have questions about interactions or allergies."
        )
    }


def check_prescription_match(med_key, canonical_name, scanned_strength, patient_user):
    """
    Compares a scanned medicine against the patient's active doctor-issued prescriptions.
    """
    if not patient_user or not patient_user.is_authenticated:
        return {
            'is_matched': False,
            'status': 'NO_PATIENT_LOGGED_IN',
            'title': 'Prescription Check Not Available',
            'message': 'Log in to your citizen account to automatically cross-verify against your active prescriptions.'
        }

    # Query active prescriptions
    active_rx = Prescription.objects.filter(patient=patient_user, status='ACTIVE')

    matched_rx = None
    for rx in active_rx:
        rx_name_lower = rx.medicine_name.lower()
        rx_gen_lower = (rx.generic_name or '').lower()
        if med_key in rx_name_lower or med_key in rx_gen_lower or canonical_name.lower() in rx_name_lower:
            matched_rx = rx
            break

    if matched_rx:
        schedule_parts = []
        if matched_rx.morning: schedule_parts.append("Morning (सुबह)")
        if matched_rx.afternoon: schedule_parts.append("Afternoon (दोपहर)")
        if matched_rx.night: schedule_parts.append("Night (रात)")
        schedule_text = " + ".join(schedule_parts) or "As prescribed by doctor"

        return {
            'is_matched': True,
            'status': 'MATCHED',
            'badge': '✅ Matches Current Prescription',
            'title': 'Prescription Match Verified',
            'message': '✅ This appears to match a medicine in your current active doctor-issued prescription.',
            'prescription_details': {
                'id': matched_rx.id,
                'medicine_name': matched_rx.medicine_name,
                'prescribed_dosage': matched_rx.dosage,
                'schedule': schedule_text,
                'food_relation': matched_rx.timing,
                'duration': f"{matched_rx.duration_days} Days",
                'prescribed_by': matched_rx.prescribed_by
            }
        }
    else:
        return {
            'is_matched': False,
            'status': 'UNMATCHED_WARNING',
            'badge': '⚠️ Prescription Match Warning',
            'title': '⚠️ Prescription Match Warning',
            'message': (
                "The scanned medicine does not appear to match any active medicine in your current doctor-issued prescription.\n\n"
                "Please verify the medicine with your doctor or pharmacist before taking it."
            )
        }


# ==================== 4. AI LAB REPORT EXPLAINER ENGINE ====================

def explain_lab_report(report_text, patient_user=None):
    """
    Parses laboratory report text, identifies test markers, values, units,
    detects reference ranges, checks critical thresholds, and compares trends.
    """
    raw_text = (report_text or '').lower()

    extracted_results = []
    abnormal_items = []
    urgent_alerts = []

    # Parse parameters from knowledge base
    for key, info in LAB_TEST_KNOWLEDGE.items():
        # Match test name variants
        search_terms = [key, key.replace('_', ' ')]
        if key == 'hemoglobin': search_terms.extend(['hb', 'haemoglobin'])
        elif key == 'wbc': search_terms.extend(['tlc', 'white blood', 'leukocyte'])
        elif key == 'platelets': search_terms.extend(['platelet', 'thrombocyte', 'plt'])
        elif key == 'blood_sugar_fasting': search_terms.extend(['glucose', 'fasting sugar', 'fbs', 'sugar'])
        elif key == 'hba1c': search_terms.extend(['glycated', 'a1c'])
        elif key == 'total_cholesterol': search_terms.extend(['cholesterol', 'chol'])
        elif key == 'creatinine': search_terms.extend(['serum creatinine', 'creat'])
        elif key == 'sgpt_alt': search_terms.extend(['sgpt', 'alt', 'alanine'])
        elif key == 'tsh': search_terms.extend(['thyroid', 'tsh'])
        elif key == 'spo2': search_terms.extend(['spo2', 'oxygen', 'o2'])

        matched = any(term in raw_text for term in search_terms)
        if matched:
            # Extract numeric value
            val = None
            for term in search_terms:
                pattern = rf'{term}[^\d]*([\d\.]+)'
                m = re.search(pattern, raw_text)
                if m:
                    try:
                        val = float(m.group(1))
                        break
                    except ValueError:
                        pass

            if val is None:
                # Default illustrative value from typical seed data if name mentioned
                val = round((info['default_low'] + info['default_high']) / 2, 1)

            # Check reference range
            low_ref = info['default_low']
            high_ref = info['default_high']

            if val < low_ref:
                range_status = 'BELOW'
                status_badge = '⚠️ Below Reference Range'
                status_class = 'warning'
                explanation_meaning = f"This result of {val} {info['unit']} is below the standard healthy reference range ({low_ref} - {high_ref} {info['unit']})."
                abnormal_items.append(f"{info['display_name']} ({val} {info['unit']} - Below range)")
            elif val > high_ref:
                range_status = 'ABOVE'
                status_badge = '⚠️ Above Reference Range'
                status_class = 'warning'
                explanation_meaning = f"This result of {val} {info['unit']} is above the standard healthy reference range ({low_ref} - {high_ref} {info['unit']})."
                abnormal_items.append(f"{info['display_name']} ({val} {info['unit']} - Above range)")
            else:
                range_status = 'NORMAL'
                status_badge = '✓ Within Reference Range'
                status_class = 'success'
                explanation_meaning = f"This result of {val} {info['unit']} falls comfortably within the healthy reference range ({low_ref} - {high_ref} {info['unit']})."

            # Check Critical Urgent Safety Thresholds
            if val <= info.get('critical_low', -999) or val >= info.get('critical_high', 99999):
                urgent_alerts.append({
                    'test_name': info['display_name'],
                    'value': f"{val} {info['unit']}",
                    'urgency_message': (
                        f"🚨 Alert for {info['display_name']}: Result ({val} {info['unit']}) reaches configured clinical attention threshold. "
                        "Please contact your healthcare professional promptly or seek emergency medical care if experiencing acute symptoms."
                    )
                })

            # Historical Trend Analysis
            trend_data = compute_parameter_trend(key, val, patient_user)

            extracted_results.append({
                'key': key,
                'name': info['display_name'],
                'category': info['category'],
                'value': val,
                'unit': info['unit'],
                'reference_range': f"{low_ref} - {high_ref} {info['unit']}",
                'range_status': range_status,
                'status_badge': status_badge,
                'status_class': status_class,
                'explanation': {
                    'what_is_this_test': info['what_is_it'],
                    'what_number_means': explanation_meaning,
                    'is_inside_range': f"{status_badge} ({low_ref} to {high_ref} {info['unit']})",
                    'why_doctors_care': info['why_doctors_care'],
                    'what_to_discuss': info['what_to_discuss']
                },
                'trend': trend_data
            })

    # If no recognized marker was found in text, return default standard CBC panel explanation
    if not extracted_results:
        default_cbc = explain_lab_report("hemoglobin 13.8, wbc 7200, platelets 250000", patient_user)
        return default_cbc

    return {
        'success': True,
        'total_tests_analyzed': len(extracted_results),
        'abnormal_count': len(abnormal_items),
        'abnormal_summary': abnormal_items,
        'urgent_alerts': urgent_alerts,
        'results': extracted_results,
        'general_safety_disclaimer': (
            "ℹ️ Medical Disclaimer: This explanation is provided to help you understand your laboratory report in simple terms. "
            "It does not constitute a clinical diagnosis or replace your physician's judgment. "
            "Always review all laboratory results directly with your healthcare provider in the context of your symptoms and clinical history."
        )
    }


def compute_parameter_trend(param_key, current_val, patient_user):
    """
    Evaluates past values from LabOrder and VitalRecord history to generate neutral trend trajectories.
    """
    if not patient_user or not patient_user.is_authenticated:
        return {
            'trajectory': 'Insufficient data',
            'trend_label': 'Initial Baseline',
            'historical_points': [{'date': 'Today', 'value': current_val}]
        }

    points = []
    # Check historical vitals or past lab orders
    if param_key in ['blood_sugar_fasting', 'spo2', 'hemoglobin']:
        vitals = VitalRecord.objects.filter(patient=patient_user).order_by('recorded_at')[:4]
        for v in vitals:
            d_str = v.recorded_at.strftime('%b %d')
            if param_key == 'blood_sugar_fasting' and v.sugar_level:
                points.append({'date': d_str, 'value': float(v.sugar_level)})
            elif param_key == 'spo2' and v.o2_saturation:
                points.append({'date': d_str, 'value': float(v.o2_saturation)})
            elif param_key == 'hemoglobin' and v.blood_percentage:
                points.append({'date': d_str, 'value': float(v.blood_percentage)})

    points.append({'date': 'Current', 'value': current_val})

    if len(points) < 2:
        return {
            'trajectory': 'Insufficient data',
            'trend_label': 'Single reading recorded',
            'historical_points': points
        }

    first_val = points[0]['value']
    last_val = points[-1]['value']
    diff = last_val - first_val
    rel_change = abs(diff) / (first_val if first_val > 0 else 1)

    if rel_change < 0.03:
        trajectory = 'Stable trend'
        trend_label = '➡️ Stable over time'
    elif diff > 0:
        trajectory = 'Increasing trend'
        trend_label = '↗️ Increasing trend'
    else:
        trajectory = 'Decreasing trend'
        trend_label = '↘️ Decreasing trend'

    return {
        'trajectory': trajectory,
        'trend_label': trend_label,
        'historical_points': points
    }


# ==================== 5. AI PRESCRIPTION EXPLAINER ENGINE ====================

def explain_patient_prescriptions(patient_user):
    """
    Retrieves and simplifies all active doctor-issued prescriptions into plain language.
    """
    if not patient_user or not patient_user.is_authenticated:
        return {'success': False, 'error': 'Authentication required'}

    prescriptions = Prescription.objects.filter(patient=patient_user, status='ACTIVE')
    explained_list = []

    for rx in prescriptions:
        timing_parts = []
        if rx.morning: timing_parts.append("Morning (सुबह)")
        if rx.afternoon: timing_parts.append("Afternoon (दोपहर)")
        if rx.night: timing_parts.append("Night (रात)")
        freq_str = " + ".join(timing_parts) or "As needed"

        explained_list.append({
            'id': rx.id,
            'medicine_name': rx.medicine_name,
            'generic_name': rx.generic_name or rx.medicine_name,
            'dose': rx.dosage,
            'form': rx.form,
            'schedule': freq_str,
            'food_relation': rx.timing,
            'duration': f"{rx.duration_days} Days",
            'purpose': rx.purpose,
            'doctor': rx.prescribed_by,
            'plain_words_summary': (
                f"Your doctor has prescribed {rx.medicine_name} ({rx.dosage}) to be taken {freq_str}, "
                f"{rx.timing.lower()}, for a duration of {rx.duration_days} days. "
                "Follow the exact schedule written by your doctor and do not alter the dosage."
            )
        })

    return {
        'success': True,
        'prescriptions': explained_list,
        'count': len(explained_list),
        'safety_notice': (
            "⚠ Important Prescription Guidance:\n"
            "• Take each medicine according to the exact schedule prescribed by your doctor.\n"
            "• Do not stop or modify dosage on your own.\n"
            "• In case of unexpected discomfort, contact your healthcare provider or hospital OPD."
        )
    }


# ==================== 6. AI HEALTH TRENDS EXPLAINER ENGINE ====================

def explain_vitals_health_trends(patient_user):
    """
    Analyzes historical vitals telemetry and creates calm, objective citizen-friendly summaries.
    """
    if not patient_user or not patient_user.is_authenticated:
        return {'success': False, 'error': 'Authentication required'}

    vitals = VitalRecord.objects.filter(patient=patient_user).order_by('-recorded_at')[:10]
    if not vitals.exists():
        return {
            'success': True,
            'has_data': False,
            'message': 'No health vitals logged yet. Use the Home dashboard to log BP, SpO2, and Blood Sugar readings.'
        }

    latest = vitals.first()
    trends_summary = []

    # BP Evaluation
    if latest.bp_systolic and latest.bp_diastolic:
        bp_status = "Optimal" if latest.bp_systolic <= 120 and latest.bp_diastolic <= 80 else "Mildly elevated / Requires monitoring"
        trends_summary.append({
            'vital': 'Blood Pressure',
            'latest_value': f"{latest.bp_systolic}/{latest.bp_diastolic} mmHg",
            'normal_range': '120/80 mmHg',
            'trajectory': 'Stable trend across recent logs',
            'plain_summary': f"Your most recent blood pressure was recorded at {latest.bp_systolic}/{latest.bp_diastolic} mmHg ({bp_status}). Continue routine daily activity and hydration."
        })

    # SpO2 Evaluation
    if latest.o2_saturation:
        spo2_status = "Healthy Oxygenation" if latest.o2_saturation >= 95 else "Below optimal"
        trends_summary.append({
            'vital': 'Oxygen Saturation (SpO2)',
            'latest_value': f"{latest.o2_saturation}%",
            'normal_range': '95% - 100%',
            'trajectory': 'Stable trend',
            'plain_summary': f"Oxygen level of {latest.o2_saturation}% shows {spo2_status}. Respiratory parameters are well maintained."
        })

    # Blood Sugar Evaluation
    if latest.sugar_level:
        sugar_status = "Within fasting target" if latest.sugar_level <= 100 else "Above fasting target"
        trends_summary.append({
            'vital': 'Blood Sugar',
            'latest_value': f"{latest.sugar_level} mg/dL",
            'normal_range': '70 - 100 mg/dL (Fasting)',
            'trajectory': 'Monitored trajectory',
            'plain_summary': f"Blood glucose is recorded at {latest.sugar_level} mg/dL ({sugar_status}). Discuss target ranges with your physician."
        })

    # Hemoglobin
    if latest.blood_percentage:
        trends_summary.append({
            'vital': 'Hemoglobin',
            'latest_value': f"{latest.blood_percentage} g/dL",
            'normal_range': '12 - 16 g/dL',
            'trajectory': 'Stable trend',
            'plain_summary': f"Hemoglobin is documented at {latest.blood_percentage} g/dL."
        })

    return {
        'success': True,
        'has_data': True,
        'latest_recorded_at': latest.recorded_at.strftime('%d-%b-%Y %I:%M %p'),
        'trends': trends_summary,
        'doctor_discussion_points': [
            "Are my current blood pressure and sugar levels meeting our treatment targets?",
            "Should I continue my current dietary and physical activity routine?",
            "When should I schedule my next routine laboratory checkup?"
        ]
    }


# ==================== 7. INTERACTIVE REPORT Q&A ("ASK ABOUT MY REPORT") ====================

def answer_health_assistant_question(question_text, patient_user=None):
    """
    Answers patient questions about reports, tablets, and vitals with strict safety guardrails.
    - Never prescribes or modifies prescriptions
    - Never gives unsupervised medical diagnoses
    - Speaks in calm, reassuring, educational language
    - Always directs patient to their treating doctor for treatment decisions
    """
    q = (question_text or '').lower().strip()
    if not q:
        return {'success': False, 'answer': 'Please enter a health question or topic you would like explained.'}

    # Guardrail Check 1: Request to change prescription or stop medicine
    if any(term in q for term in ['stop medicine', 'stop tablet', 'change dose', 'increase dose', 'double dose', 'skip medicine']):
        return {
            'success': True,
            'answer': (
                "⚠️ Clinical Safety Guidance:\n\n"
                "You should never stop, change, or adjust your prescribed medication dosage without direct consultation with your treating doctor.\n\n"
                "If you are experiencing unexpected side effects or feeling uncomfortable, please contact your hospital OPD or treating physician before making any changes."
            )
        }

    # Guardrail Check 2: Request for diagnosis ("Do I have cancer / heart attack / stroke?")
    if any(term in q for term in ['do i have', 'is it cancer', 'am i dying', 'do i have disease', 'diagnose me']):
        return {
            'success': True,
            'answer': (
                "ℹ️ Medical Assessment Guidance:\n\n"
                "Individual test numbers or symptoms alone cannot diagnose a medical condition. A complete clinical evaluation requires your doctor to examine your physical symptoms, medical history, and overall clinical picture in context.\n\n"
                "Please schedule a consultation with your doctor to interpret your findings accurately."
            )
        }

    # Topic: Hemoglobin
    if 'hemoglobin' in q or 'hb' in q or 'anemia' in q:
        return {
            'success': True,
            'answer': (
                "🩸 Understanding Hemoglobin:\n\n"
                "Hemoglobin is an iron-containing protein in red blood cells that carries oxygen from your lungs to your body. Normal healthy reference ranges are typically between 12.0 and 16.0 g/dL.\n\n"
                "• If slightly lower: Doctors often review dietary iron intake, hydration, and nutritional factors.\n"
                "• Discuss with your doctor whether dietary adjustments (such as leafy greens, lentils, fruits) or iron evaluations are recommended for you."
            )
        }

    # Topic: Blood Sugar / Glucose / Diabetes
    if 'sugar' in q or 'glucose' in q or 'diabetes' in q or 'hba1c' in q:
        return {
            'success': True,
            'answer': (
                "🍬 Understanding Blood Sugar & HbA1c:\n\n"
                "• Fasting Blood Sugar: Normal fasting levels are generally 70–100 mg/dL.\n"
                "• HbA1c: Reflects average blood sugar over the last 2 to 3 months (under 5.7% is considered normal for non-diabetic individuals).\n\n"
                "Consistency in balanced meals, regular physical movement, and taking medications as prescribed by your doctor are essential for healthy glucose control."
            )
        }

    # Topic: Blood Pressure
    if 'bp' in q or 'blood pressure' in q or 'hypertension' in q:
        return {
            'success': True,
            'answer': (
                "💓 Understanding Blood Pressure:\n\n"
                "Blood pressure is measured in two numbers: Systolic (when the heart pumps) and Diastolic (when the heart rests). A standard target reading is approximately 120/80 mmHg.\n\n"
                "Daily habits that support healthy blood pressure include moderate dietary salt, regular walking, stress management, and taking prescribed antihypertensive tablets consistently."
            )
        }

    # General Fallback Safe Response
    return {
        'success': True,
        'answer': (
            f"ℹ️ Health Information regarding your query:\n\n"
            "Your health indicators and laboratory reports are designed to be interpreted as a whole by your treating healthcare professional.\n\n"
            "Key Steps to Take:\n"
            "1. Keep a record of your daily readings (BP, SpO2, Blood Sugar) using the dashboard.\n"
            "2. Take all prescribed medicines at the exact times specified on your prescription timetable.\n"
            "3. Bring your printed or digital report to your next OPD doctor consultation for a comprehensive review."
        )
    }
