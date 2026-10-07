import json
import datetime
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import (
    VitalRecord, HospitalVisit, Prescription, HealthNotification, 
    RadiologyReport, LabTest, LabOrder, DischargeSummary, 
    VaccinationRecord, EmergencyProfile, ConsentRecord, MedicationDoseLog,
    PhysiotherapyVideo
)
from appointments.models import HospitalFacility, DoctorProfile, AppointmentBooking, HospitalArea, Specialty
from core.models import User, HealthScheme, HealthAdvisory
from core.audit_utils import record_audit_log
from core.permission_utils import check_patient_record_access

@login_required
def dashboard_view(request):
    user = request.user
    today = timezone.now().date()

    # Intelligent role routing
    if user.role == 'ADMIN' and not request.GET.get('preview'):
        return redirect('admin_portal')
    elif user.role == 'DOCTOR' and not request.GET.get('preview'):
        return redirect('doctor_portal')

    # Ensure patient has initial vitals if empty
    if not VitalRecord.objects.filter(patient=user).exists():
        VitalRecord.objects.create(
            patient=user,
            bp_systolic=120,
            bp_diastolic=80,
            o2_saturation=98.5,
            sugar_level=95.0,
            weight=user.age * 0.8 + 42 if user.age else 68.0,
            blood_percentage=14.2 if user.gender == 'Male' else 12.8,
            heart_rate=72,
            source='Hospital Lab',
            notes='Initial Baseline Assessment - National Health Registry'
        )

    # 1. Today's Appointment & Live OPD Token Queue Calculation
    today_appointment = AppointmentBooking.objects.filter(
        patient=user,
        appointment_date=today
    ).exclude(status='CANCELLED').first()

    queue_info = None
    if today_appointment:
        doc = today_appointment.doctor
        # Find current token being consulted
        current_consult = AppointmentBooking.objects.filter(
            doctor=doc,
            appointment_date=today,
            status__in=['IN_CONSULTATION', 'IN_PROGRESS']
        ).first()

        current_token = current_consult.opd_token_number if current_consult else (
            AppointmentBooking.objects.filter(doctor=doc, appointment_date=today, status='COMPLETED').order_by('-completed_at').first()
        )
        current_token_display = current_token.opd_token_number if hasattr(current_token, 'opd_token_number') else (current_token or 'Queue Initializing')

        # Patients ahead count
        patients_ahead = AppointmentBooking.objects.filter(
            doctor=doc,
            appointment_date=today,
            token_number__lt=today_appointment.token_number,
            status__in=['WAITING', 'BOOKED', 'CHECKED_IN', 'CONFIRMED']
        ).count()

        queue_info = {
            'booking': today_appointment,
            'token': today_appointment.opd_token_number,
            'room': today_appointment.consultation_room or doc.consultation_room or 'Room 203',
            'doctor_name': doc.name,
            'department': doc.department,
            'time_slot': today_appointment.time_slot,
            'current_token': current_token_display,
            'patients_ahead': max(0, patients_ahead),
            'status': today_appointment.status
        }

    # 2. Vitals & Medical Records
    latest_vital = VitalRecord.objects.filter(patient=user).first()
    recent_visits = HospitalVisit.objects.filter(patient=user)[:10]

    # 3. Active Prescriptions & Today's Dose Adherence Matrix
    active_prescriptions = Prescription.objects.filter(patient=user, is_active=True)
    prescriptions_with_doses = []
    for p in active_prescriptions:
        morning_log = MedicationDoseLog.objects.filter(prescription=p, patient=user, dose_date=today, time_slot='MORNING').first()
        afternoon_log = MedicationDoseLog.objects.filter(prescription=p, patient=user, dose_date=today, time_slot='AFTERNOON').first()
        night_log = MedicationDoseLog.objects.filter(prescription=p, patient=user, dose_date=today, time_slot='NIGHT').first()

        prescriptions_with_doses.append({
            'prescription': p,
            'morning_taken': morning_log.is_taken if morning_log else False,
            'afternoon_taken': afternoon_log.is_taken if afternoon_log else False,
            'night_taken': night_log.is_taken if night_log else False,
        })

    # 4. Laboratory Reports & Tests
    my_lab_orders = LabOrder.objects.filter(patient=user).select_related('test').order_by('-order_date', '-id')

    # 5. Digital Discharge Summaries
    my_discharge_summaries = DischargeSummary.objects.filter(patient=user).order_by('-discharge_date')

    # 6. Vaccinations
    completed_vaccinations = VaccinationRecord.objects.filter(patient=user, status='COMPLETED').order_by('-date_given')
    upcoming_vaccinations = VaccinationRecord.objects.filter(patient=user).exclude(status='COMPLETED').order_by('next_due_date')

    # 7. Emergency Profile
    emergency_profile, _ = EmergencyProfile.objects.get_or_create(
        patient=user,
        defaults={
            'contact_name': user.emergency_contact or 'Primary Kin',
            'relationship': 'Family Contact',
            'phone_number': user.phone,
            'blood_group': user.blood_group or 'B+'
        }
    )

    # 8. Consent Records
    active_consents = ConsentRecord.objects.filter(patient=user, status='GRANTED').order_by('-requested_at')
    pending_consents = ConsentRecord.objects.filter(patient=user, status='PENDING').order_by('-requested_at')

    # 9. Health Advisories & Schemes
    active_advisories = HealthAdvisory.objects.filter(status='ACTIVE')[:6]
    active_schemes = HealthScheme.objects.filter(is_active=True)[:6]

    # 10. Radiology & Notifications & Infrastructure
    radiology_reports = RadiologyReport.objects.filter(patient=user).order_by('-report_date')
    physio_videos = PhysiotherapyVideo.objects.all().order_by('category', 'id')
    notifications = HealthNotification.objects.filter(patient=user, is_read=False)
    my_appointments = AppointmentBooking.objects.filter(patient=user).order_by('-appointment_date')
    all_areas = HospitalArea.objects.all().order_by('city', 'area_name')
    all_hospitals = HospitalFacility.objects.all().select_related('area')
    all_specialties = Specialty.objects.all().order_by('name')

    context = {
        'user': user,
        'today': today,
        'today_appointment': today_appointment,
        'queue_info': queue_info,
        'latest_vital': latest_vital,
        'recent_visits': recent_visits,
        'prescriptions_with_doses': prescriptions_with_doses,
        'my_lab_orders': my_lab_orders,
        'my_discharge_summaries': my_discharge_summaries,
        'completed_vaccinations': completed_vaccinations,
        'upcoming_vaccinations': upcoming_vaccinations,
        'emergency_profile': emergency_profile,
        'active_consents': active_consents,
        'pending_consents': pending_consents,
        'active_advisories': active_advisories,
        'active_schemes': active_schemes,
        'radiology_reports': radiology_reports,
        'physio_videos': physio_videos,
        'notifications': notifications,
        'my_appointments': my_appointments,
        'all_areas': all_areas,
        'all_hospitals': all_hospitals,
        'all_specialties': all_specialties,
        'maps_provider': getattr(settings, 'MAPS_PROVIDER', 'leaflet'),
        'maps_api_key': getattr(settings, 'MAPS_API_KEY', ''),
    }
    return render(request, 'dashboard/index.html', context)


# ==================== MEDICATION ADHERENCE CRUD APIs ====================
@login_required
@csrf_exempt
def api_toggle_dose_taken(request, prescription_id):
    """
    Patient marks a medication dose (MORNING, AFTERNOON, NIGHT) as taken for today.
    Patients CANNOT modify prescription details, only log adherence.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    slot = data.get('slot', 'MORNING').upper()
    prescription = get_object_or_404(Prescription, id=prescription_id, patient=request.user)
    today = timezone.now().date()

    dose_log, created = MedicationDoseLog.objects.get_or_create(
        prescription=prescription,
        patient=request.user,
        dose_date=today,
        time_slot=slot
    )

    dose_log.is_taken = not dose_log.is_taken
    dose_log.taken_at = timezone.now() if dose_log.is_taken else None
    dose_log.save()

    status_msg = f"{prescription.medicine_name} ({slot}) marked as taken." if dose_log.is_taken else f"{prescription.medicine_name} ({slot}) marked as pending."
    return JsonResponse({
        'success': True,
        'is_taken': dose_log.is_taken,
        'slot': slot,
        'message': status_msg,
        'taken_at': dose_log.taken_at.strftime('%I:%M %p') if dose_log.taken_at else None
    })


# ==================== OPD LIVE QUEUE STATUS API ====================
@login_required
def api_patient_opd_status(request):
    """
    Returns live OPD queue status for the patient's appointment today.
    """
    today = timezone.now().date()
    apt = AppointmentBooking.objects.filter(
        patient=request.user,
        appointment_date=today
    ).exclude(status='CANCELLED').first()

    if not apt:
        return JsonResponse({'success': False, 'message': 'No active appointment scheduled for today.'})

    doc = apt.doctor
    current_consult = AppointmentBooking.objects.filter(
        doctor=doc,
        appointment_date=today,
        status__in=['IN_CONSULTATION', 'IN_PROGRESS']
    ).first()

    current_token = current_consult.opd_token_number if current_consult else (
        AppointmentBooking.objects.filter(doctor=doc, appointment_date=today, status='COMPLETED').order_by('-completed_at').first()
    )
    current_token_display = current_token.opd_token_number if hasattr(current_token, 'opd_token_number') else (current_token or 'Queue Initializing')

    patients_ahead = AppointmentBooking.objects.filter(
        doctor=doc,
        appointment_date=today,
        token_number__lt=apt.token_number,
        status__in=['WAITING', 'BOOKED', 'CHECKED_IN', 'CONFIRMED']
    ).count()

    return JsonResponse({
        'success': True,
        'token': apt.opd_token_number,
        'room': apt.consultation_room or doc.consultation_room or 'Room 203',
        'doctor_name': doc.name,
        'department': doc.department,
        'time_slot': apt.time_slot,
        'current_token': current_token_display,
        'patients_ahead': max(0, patients_ahead),
        'status': apt.status
    })


# ==================== LABORATORY & TEST MANAGEMENT APIs ====================
@login_required
def api_patient_lab_reports(request):
    orders = LabOrder.objects.filter(patient=request.user).select_related('test').order_by('-order_date')
    data = []
    for o in orders:
        data.append({
            'id': o.id,
            'order_reference': o.order_reference,
            'test_name': o.test.name,
            'category': o.test.category,
            'doctor_name': o.doctor_name,
            'hospital_name': o.hospital_name,
            'order_date': o.order_date.strftime('%d-%b-%Y'),
            'status': o.status,
            'result_value': o.result_value or 'Pending Analysis',
            'unit': o.unit or o.test.unit,
            'reference_range': o.reference_range or o.test.reference_range,
            'lab_technician': o.lab_technician,
            'notes': o.notes
        })
    return JsonResponse({'success': True, 'reports': data})


# ==================== DISCHARGE SUMMARY & QR VERIFICATION ====================
@login_required
def api_patient_discharge_summary(request, summary_id):
    summary = get_object_or_404(DischargeSummary, id=summary_id, patient=request.user)
    record_audit_log(request, request.user, 'PATIENT', 'DOWNLOAD_REPORT', 'DischargeSummary', str(summary.id), 'SUCCESS', f'Patient downloaded discharge summary #{summary.summary_reference}')

    return JsonResponse({
        'success': True,
        'summary': {
            'reference': summary.summary_reference,
            'verification_code': summary.verification_code,
            'patient_name': summary.patient.get_display_name(),
            'patient_id': f"ABHA-{summary.patient.id:06d}",
            'dob': summary.patient.age or 'N/A',
            'hospital_name': summary.hospital_name,
            'department': summary.department,
            'admission_date': summary.admission_date.strftime('%d-%b-%Y'),
            'discharge_date': summary.discharge_date.strftime('%d-%b-%Y'),
            'reason_for_admission': summary.reason_for_admission,
            'clinical_findings': summary.clinical_findings,
            'diagnosis': summary.diagnosis,
            'procedures_treatment': summary.procedures_treatment,
            'investigation_results': summary.investigation_results,
            'condition_at_discharge': summary.condition_at_discharge,
            'discharge_medicines': summary.discharge_medicines,
            'diet_instructions': summary.diet_instructions,
            'activity_instructions': summary.activity_instructions,
            'follow_up_instructions': summary.follow_up_instructions,
            'doctor_name': summary.doctor_name,
            'doctor_reg_no': summary.doctor_reg_no
        }
    })


def verify_discharge_summary(request, ref_code):
    """
    Public digital verification endpoint for Digital Discharge Summaries (QR code target).
    """
    summary = DischargeSummary.objects.filter(
        verification_code__iexact=ref_code
    ).first()
    if not summary:
        summary = DischargeSummary.objects.filter(
            summary_reference__iexact=ref_code
        ).first()

    return render(request, 'dashboard/verify_discharge.html', {
        'summary': summary,
        'ref_code': ref_code,
        'is_verified': bool(summary)
    })


# ==================== EMERGENCY PROFILE APIs & QUICK VIEW ====================
@login_required
@csrf_exempt
def api_update_emergency_profile(request):
    """
    Patient configures their emergency contact, allergies, and critical meds.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    profile, _ = EmergencyProfile.objects.get_or_create(patient=request.user)
    profile.contact_name = data.get('contact_name', profile.contact_name).strip()
    profile.relationship = data.get('relationship', profile.relationship).strip()
    profile.phone_number = data.get('phone_number', profile.phone_number).strip()
    profile.blood_group = data.get('blood_group', profile.blood_group).strip()
    profile.known_allergies = data.get('known_allergies', profile.known_allergies).strip()
    profile.important_current_meds = data.get('important_current_meds', profile.important_current_meds).strip()
    profile.major_medical_conditions = data.get('major_medical_conditions', profile.major_medical_conditions).strip()
    profile.preferred_hospital = data.get('preferred_hospital', profile.preferred_hospital).strip()
    profile.emergency_hotline = data.get('emergency_hotline', '108 (Ambulance) / 112 (National Emergency)').strip()
    profile.save()

    record_audit_log(request, request.user, 'PATIENT', 'UPDATE_EMERGENCY_INFO', 'EmergencyProfile', str(profile.id), 'SUCCESS', 'Patient updated emergency profile.')

    return JsonResponse({
        'success': True,
        'message': 'Emergency Information updated successfully.',
        'profile': {
            'contact_name': profile.contact_name,
            'phone_number': profile.phone_number,
            'blood_group': profile.blood_group,
            'allergies': profile.known_allergies,
            'conditions': profile.major_medical_conditions
        }
    })


def view_emergency_card(request, patient_identifier):
    """
    Quick Emergency View: Exposes ONLY the patient-configured emergency information.
    Does NOT expose complete medical history or unauthorized clinical notes.
    """
    patient = None
    if str(patient_identifier).isdigit():
        if len(str(patient_identifier)) <= 6:
            patient = User.objects.filter(id=int(patient_identifier)).first()
        if not patient:
            patient = User.objects.filter(phone=str(patient_identifier)).first()
        if not patient:
            patient = User.objects.filter(aadhaar_number=str(patient_identifier)).first()
    if not patient:
        patient = get_object_or_404(User, phone=patient_identifier)

    profile = getattr(patient, 'emergency_profile', None)

    record_audit_log(request, None, 'EMERGENCY_RESPONDER', 'SYSTEM_SECURITY', 'EmergencyProfile', str(patient.id), 'SUCCESS', f'Quick Emergency Card viewed for patient {patient.get_display_name()}')

    return render(request, 'dashboard/emergency_card.html', {
        'patient': patient,
        'profile': profile,
    })


# ==================== PATIENT CONSENT & PRIVACY APIs ====================
@login_required
@csrf_exempt
def api_patient_consent_action(request, consent_id):
    """
    Patient grants, denies, or revokes doctor access to medical records.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    action = data.get('action', 'GRANT').upper()  # GRANT, DENY, REVOKE
    consent = get_object_or_404(ConsentRecord, id=consent_id, patient=request.user)

    if action == 'GRANT':
        consent.status = 'GRANTED'
        consent.actioned_at = timezone.now()
        consent.valid_until = timezone.now() + datetime.timedelta(days=30)
        record_audit_log(request, request.user, 'PATIENT', 'GRANT_CONSENT', 'ConsentRecord', str(consent.id), 'SUCCESS', f'Granted record access to Dr. {consent.doctor_name}')
        msg = f"Access granted to Dr. {consent.doctor_name} for 30 days."

    elif action == 'DENY':
        consent.status = 'DENIED'
        consent.actioned_at = timezone.now()
        record_audit_log(request, request.user, 'PATIENT', 'DENY_CONSENT', 'ConsentRecord', str(consent.id), 'SUCCESS', f'Denied record access to Dr. {consent.doctor_name}')
        msg = f"Access request from Dr. {consent.doctor_name} denied."

    elif action == 'REVOKE':
        consent.status = 'REVOKED'
        consent.actioned_at = timezone.now()
        record_audit_log(request, request.user, 'PATIENT', 'REVOKE_CONSENT', 'ConsentRecord', str(consent.id), 'SUCCESS', f'Revoked record access from Dr. {consent.doctor_name}')
        msg = f"Access consent for Dr. {consent.doctor_name} revoked immediately."

    else:
        return JsonResponse({'success': False, 'message': f'Invalid action: {action}'})

    consent.save()
    return JsonResponse({'success': True, 'status': consent.status, 'message': msg})


# ==================== VACCINATION APIs ====================
@login_required
def api_patient_vaccinations(request):
    vaccinations = VaccinationRecord.objects.filter(patient=request.user).order_by('-date_given')
    data = []
    for v in vaccinations:
        data.append({
            'id': v.id,
            'vaccine_name': v.vaccine_name,
            'dose_number': v.dose_number,
            'date_given': v.date_given.strftime('%d-%b-%Y') if v.date_given else 'Scheduled',
            'next_due_date': v.next_due_date.strftime('%d-%b-%Y') if v.next_due_date else None,
            'hospital_center': v.hospital_center,
            'provider_name': v.provider_name,
            'batch_number': v.batch_number,
            'status': v.status,
            'notes': v.notes
        })
    return JsonResponse({'success': True, 'vaccinations': data})


# ==================== VITALS CRUD APIs ====================
@login_required
def get_vitals_api(request):
    vitals_qs = VitalRecord.objects.filter(patient=request.user).order_by('recorded_at')
    data = []
    for v in vitals_qs:
        data.append({
            'id': v.id,
            'date': v.recorded_at.strftime('%d-%b-%Y %H:%M'),
            'date_short': v.recorded_at.strftime('%d/%m'),
            'bp_systolic': v.bp_systolic,
            'bp_diastolic': v.bp_diastolic,
            'bp_display': v.bp_display,
            'bp_status': v.bp_status,
            'o2_saturation': v.o2_saturation,
            'o2_status': v.o2_status,
            'sugar_level': v.sugar_level,
            'sugar_type': v.sugar_type,
            'sugar_status': v.sugar_status,
            'weight': v.weight,
            'blood_percentage': v.blood_percentage,
            'hb_status': v.hb_status,
            'heart_rate': v.heart_rate,
            'hr_status': v.hr_status,
            'source': v.source,
            'notes': v.notes
        })

    latest = data[-1] if data else None

    return JsonResponse({
        'success': True,
        'history': data,
        'latest': latest
    })


@login_required
@csrf_exempt
def add_vital_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        payload = json.loads(request.body)
    except Exception:
        payload = request.POST

    try:
        new_vital = VitalRecord.objects.create(
            patient=request.user,
            bp_systolic=int(payload.get('bp_systolic', 120)),
            bp_diastolic=int(payload.get('bp_diastolic', 80)),
            o2_saturation=float(payload.get('o2_saturation', 98.0)),
            sugar_level=float(payload.get('sugar_level', 95.0)),
            sugar_type=payload.get('sugar_type', 'Fasting'),
            weight=float(payload.get('weight', 68.0)),
            blood_percentage=float(payload.get('blood_percentage', 13.8)),
            heart_rate=int(payload.get('heart_rate', 72)),
            source=payload.get('source', 'Patient Logged'),
            notes=payload.get('notes', 'Logged via Patient Portal')
        )
        return JsonResponse({
            'success': True,
            'message': 'Vitals logged successfully and dashboard metrics updated.',
            'vital': {
                'id': new_vital.id,
                'bp': new_vital.bp_display,
                'o2': new_vital.o2_saturation,
                'sugar': new_vital.sugar_level,
                'weight': new_vital.weight,
                'blood': new_vital.blood_percentage,
                'heart_rate': new_vital.heart_rate,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


# ==================== RECORDS / VISITS CRUD APIs ====================
@login_required
def get_records_api(request):
    visits = HospitalVisit.objects.filter(patient=request.user).order_by('-visit_date')
    data = []
    for vis in visits:
        v_data = None
        if vis.vitals_snapshot:
            v_data = {
                'bp': vis.vitals_snapshot.bp_display,
                'o2': vis.vitals_snapshot.o2_saturation,
                'sugar': vis.vitals_snapshot.sugar_level,
                'weight': vis.vitals_snapshot.weight,
                'blood': vis.vitals_snapshot.blood_percentage,
                'heart_rate': vis.vitals_snapshot.heart_rate,
            }

        data.append({
            'id': vis.id,
            'hospital_name': vis.hospital_name,
            'department': vis.department,
            'doctor_name': vis.doctor_name,
            'visit_date': vis.visit_date.strftime('%d %B %Y'),
            'visit_date_raw': vis.visit_date.strftime('%Y-%m-%d'),
            'reason': vis.reason_for_visit,
            'diagnosis': vis.diagnosis,
            'treatment': vis.treatment_summary,
            'lab_reports': vis.lab_reports_summary,
            'follow_up': vis.follow_up_date.strftime('%d-%b-%Y') if vis.follow_up_date else 'As needed',
            'vitals': v_data
        })

    return JsonResponse({'success': True, 'records': data})


@login_required
def get_record_detail_api(request, record_id):
    # Enforce object-level access check
    visit = get_object_or_404(HospitalVisit, id=record_id)
    if not check_patient_record_access(request, visit.patient, 'HospitalVisit', str(visit.id)):
        return JsonResponse({'success': False, 'message': 'Access Denied: Patient consent or authorization required.'}, status=403)

    v_data = None
    if visit.vitals_snapshot:
        v = visit.vitals_snapshot
        v_data = {
            'bp': v.bp_display,
            'bp_systolic': v.bp_systolic,
            'bp_diastolic': v.bp_diastolic,
            'bp_status': v.bp_status,
            'o2': v.o2_saturation,
            'o2_status': v.o2_status,
            'sugar': v.sugar_level,
            'sugar_type': v.sugar_type,
            'sugar_status': v.sugar_status,
            'weight': v.weight,
            'blood': v.blood_percentage,
            'hb_status': v.hb_status,
            'heart_rate': v.heart_rate,
            'hr_status': v.hr_status,
        }

    return JsonResponse({
        'success': True,
        'record': {
            'id': visit.id,
            'hospital_name': visit.hospital_name,
            'department': visit.department,
            'doctor_name': visit.doctor_name,
            'visit_date': visit.visit_date.strftime('%A, %d %B %Y'),
            'reason': visit.reason_for_visit,
            'diagnosis': visit.diagnosis,
            'treatment': visit.treatment_summary,
            'lab_reports': visit.lab_reports_summary,
            'follow_up': visit.follow_up_date.strftime('%d %B %Y') if visit.follow_up_date else 'None / On Discomfort',
            'vitals': v_data
        }
    })


@login_required
@csrf_exempt
def sync_record_vitals_api(request, record_id):
    visit = get_object_or_404(HospitalVisit, id=record_id, patient=request.user)
    if not visit.vitals_snapshot:
        return JsonResponse({'success': False, 'message': 'This record does not have a linked vitals snapshot.'})

    old_v = visit.vitals_snapshot
    new_vital = VitalRecord.objects.create(
        patient=request.user,
        bp_systolic=old_v.bp_systolic,
        bp_diastolic=old_v.bp_diastolic,
        o2_saturation=old_v.o2_saturation,
        sugar_level=old_v.sugar_level,
        sugar_type=old_v.sugar_type,
        weight=old_v.weight,
        blood_percentage=old_v.blood_percentage,
        heart_rate=old_v.heart_rate,
        source=f"Synced from {visit.hospital_name}",
        notes=f"Clinical sync from visit on {visit.visit_date.strftime('%d-%b-%Y')}"
    )

    return JsonResponse({
        'success': True,
        'message': f'Vitals from {visit.hospital_name} ({visit.visit_date.strftime("%d-%b-%Y")}) have been synced to your Home Dashboard metrics!',
        'vitals': {
            'bp': new_vital.bp_display,
            'o2': new_vital.o2_saturation,
            'sugar': new_vital.sugar_level,
            'weight': new_vital.weight,
            'blood': new_vital.blood_percentage,
            'heart_rate': new_vital.heart_rate,
            'recorded_at': new_vital.recorded_at.strftime('%d-%b-%Y %H:%M')
        }
    })


@login_required
@csrf_exempt
def add_record_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    hospital_name = data.get('hospital_name', '').strip()
    department = data.get('department', 'General Medicine').strip()
    doctor_name = data.get('doctor_name', 'Senior Medical Officer').strip()
    visit_date = data.get('visit_date') or timezone.now().date()
    reason = data.get('reason', 'Routine Health Checkup').strip()
    diagnosis = data.get('diagnosis', 'All parameters normal').strip()
    treatment = data.get('treatment', 'Maintain healthy hydration and balanced diet').strip()
    lab_reports = data.get('lab_reports', 'CBC, Blood Sugar & Lipid Profile within standard ranges').strip()

    bp_sys = int(data.get('bp_systolic', 120))
    bp_dia = int(data.get('bp_diastolic', 80))
    o2 = float(data.get('o2_saturation', 98.0))
    sugar = float(data.get('sugar_level', 95.0))
    weight = float(data.get('weight', 68.0))
    blood = float(data.get('blood_percentage', 13.8))
    hr = int(data.get('heart_rate', 72))

    vital_snap = VitalRecord.objects.create(
        patient=request.user,
        bp_systolic=bp_sys,
        bp_diastolic=bp_dia,
        o2_saturation=o2,
        sugar_level=sugar,
        weight=weight,
        blood_percentage=blood,
        heart_rate=hr,
        source=f'Hospital Visit: {hospital_name}',
        notes=f'Checkup by {doctor_name}'
    )

    visit = HospitalVisit.objects.create(
        patient=request.user,
        hospital_name=hospital_name,
        department=department,
        doctor_name=doctor_name,
        visit_date=visit_date,
        reason_for_visit=reason,
        diagnosis=diagnosis,
        treatment_summary=treatment,
        lab_reports_summary=lab_reports,
        vitals_snapshot=vital_snap
    )

    HealthNotification.objects.create(
        patient=request.user,
        title=f"New Record Added: {hospital_name}",
        message=f"A medical consultation record has been added for {department}. Vitals have been updated on your dashboard.",
        category="Record Update",
        action_tab="records"
    )

    return JsonResponse({
        'success': True,
        'message': 'Medical record and clinical vitals logged successfully.',
        'record_id': visit.id
    })


# ==================== PRESCRIPTIONS & NOTIFICATIONS ====================
@login_required
def get_prescriptions_api(request):
    prescriptions = Prescription.objects.filter(patient=request.user).order_by('-start_date')
    data = []
    for p in prescriptions:
        data.append({
            'id': p.id,
            'medicine_name': p.medicine_name,
            'generic_name': p.generic_name,
            'dosage': p.dosage,
            'form': p.form,
            'morning': p.morning,
            'afternoon': p.afternoon,
            'night': p.night,
            'timing': p.timing,
            'duration_days': p.duration_days,
            'quantity': p.quantity,
            'start_date': p.start_date.strftime('%d-%b-%Y'),
            'status': p.status,
            'is_active': p.is_active,
            'instructions': p.instructions,
            'prescribed_by': p.prescribed_by,
            'schedule': p.schedule_summary
        })
    return JsonResponse({'success': True, 'prescriptions': data})


@login_required
def get_notifications_api(request):
    notes = HealthNotification.objects.filter(patient=request.user).order_by('-created_at')
    data = []
    for n in notes:
        data.append({
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'category': n.category,
            'created_at': n.created_at.strftime('%d-%b-%Y %I:%M %p'),
            'is_read': n.is_read,
            'action_tab': n.action_tab
        })
    return JsonResponse({'success': True, 'notifications': data})


@login_required
@csrf_exempt
def mark_notification_read_api(request, note_id):
    note = get_object_or_404(HealthNotification, id=note_id, patient=request.user)
    note.is_read = True
    note.save()
    return JsonResponse({'success': True, 'message': 'Notification marked as read.'})


# ==================== PHYSIOTHERAPY VIDEOS API ====================
def api_get_physiotherapy_videos(request):
    """
    Public / Authenticated health education endpoint for physiotherapy routines.
    Supports filtering by category and search keyword.
    """
    category = request.GET.get('category', '').strip().lower()
    q = request.GET.get('q', '').strip().lower()
    qs = PhysiotherapyVideo.objects.all()
    if category and category != 'all':
        qs = qs.filter(category=category)
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(instructions__icontains=q))
    
    videos = []
    for v in qs:
        videos.append({
            'id': v.id,
            'title': v.title,
            'description': v.description,
            'category': v.category,
            'category_display': v.get_category_display(),
            'duration': v.duration_text,
            'level': v.level_text,
            'instructions': v.instructions,
            'embed_url': v.embed_url,
            'thumbnail_url': v.thumbnail_url,
            'source_name': v.source_name,
            'language': v.language,
            'external_platform': v.external_platform,
            'external_url': v.external_url,
            'allows_embedding': v.allows_embedding,
            'date_added': v.date_added.strftime('%d-%b-%Y'),
        })
    return JsonResponse({'success': True, 'videos': videos, 'count': len(videos)})


# ==================== RADIOLOGY & DIAGNOSTIC IMAGING APIs ====================
@login_required
def api_get_radiology_reports(request):
    """
    Authorized radiology reports for authenticated patient or authorized doctor.
    """
    patient_user = request.user
    patient_id = request.GET.get('patient_id')
    if patient_id and request.user.role == 'DOCTOR':
        from core.models import User
        target = get_object_or_404(User, id=patient_id)
        if not check_patient_record_access(request, target, 'RadiologyReportList', str(target.id)):
            return JsonResponse({'success': False, 'message': 'Access Denied: Patient authorization required.'}, status=403)
        patient_user = target
    
    reports = RadiologyReport.objects.filter(patient=patient_user).order_by('-report_date')
    data = []
    for r in reports:
        data.append({
            'id': r.id,
            'report_title': r.report_title,
            'modality': r.modality,
            'scan_type': r.scan_type,
            'body_part': r.body_part,
            'report_date': r.report_date.strftime('%d-%b-%Y'),
            'hospital_name': r.hospital_name,
            'radiologist_name': r.radiologist_name,
            'radiologist_reg': r.radiologist_reg,
            'reason_for_exam': r.reason_for_exam,
            'procedure_name': r.procedure_name,
            'findings': r.findings,
            'measurements': r.measurements,
            'impression': r.impression,
            'dicom_slice_count': r.dicom_slice_count,
            'has_imaging_files': r.has_imaging_files,
            'is_dicom': r.is_dicom,
            'image_svg': r.image_svg,
            'imaging_url': f"/api/radiology/{r.id}/imaging/" if r.has_imaging_files else None,
            'dicom_url': f"/api/radiology/{r.id}/dicom/" if (r.has_imaging_files and r.is_dicom) else None,
        })
    return JsonResponse({'success': True, 'reports': data, 'count': len(data)})


@login_required
def api_get_radiology_report_detail(request, report_id):
    """
    Full authorized radiology report detail.
    Strictly checks Django object-level authorization & records audit log.
    """
    report = get_object_or_404(RadiologyReport, id=report_id)
    if not check_patient_record_access(request, report.patient, 'RadiologyReport', str(report.id)):
        return JsonResponse({'success': False, 'message': 'Access Denied: You are not authorized to view this diagnostic report.'}, status=403)

    record_audit_log(
        request, request.user, request.user.role, 'VIEW_RECORD',
        'RadiologyReport', str(report.id), 'SUCCESS',
        f'Authorized user viewed full {report.modality} report #{report.id}'
    )

    return JsonResponse({
        'success': True,
        'report': {
            'id': report.id,
            'report_title': report.report_title,
            'modality': report.modality,
            'scan_type': report.scan_type,
            'body_part': report.body_part,
            'report_date': report.report_date.strftime('%d %B %Y'),
            'hospital_name': report.hospital_name,
            'radiologist_name': report.radiologist_name,
            'radiologist_reg': report.radiologist_reg or 'Verified Medical Council Registered',
            'reason_for_exam': report.reason_for_exam or 'Diagnostic clinical evaluation',
            'procedure_name': report.procedure_name or 'Standard Diagnostic Radiographic Acquisition',
            'findings': report.findings,
            'measurements': report.measurements or 'Standard anatomical parameters recorded within normal limits',
            'impression': report.impression,
            'dicom_slice_count': report.dicom_slice_count,
            'has_imaging_files': report.has_imaging_files,
            'is_dicom': report.is_dicom,
            'image_svg': report.image_svg,
            'imaging_url': f"/api/radiology/{report.id}/imaging/" if report.has_imaging_files else None,
            'dicom_url': f"/api/radiology/{report.id}/dicom/" if (report.has_imaging_files and report.is_dicom) else None,
            'patient_name': report.patient.get_display_name(),
            'patient_id': f"GOI-PAT-{report.patient.id:06d}",
        }
    })


@login_required
def api_stream_radiology_imaging(request, report_id):
    """
    Secure streaming endpoint for patient imaging study frames.
    Validates Django permissions; prevents predictable URLs or unauthorized cross-patient scan access.
    """
    import os
    from django.conf import settings
    from django.http import FileResponse

    report = get_object_or_404(RadiologyReport, id=report_id)
    if not check_patient_record_access(request, report.patient, 'RadiologyStudy', str(report.id)):
        return JsonResponse({'success': False, 'message': 'Access Denied: Imaging study viewing restricted.'}, status=403)

    record_audit_log(
        request, request.user, request.user.role, 'VIEW_RECORD',
        'RadiologyStudy', str(report.id), 'SUCCESS',
        f'Secure study streaming accessed for {report.modality} #{report.id}'
    )

    # Check if a physical DICOM/imaging file exists
    if report.dicom_file and hasattr(report.dicom_file, 'path') and os.path.exists(report.dicom_file.path):
        resp = FileResponse(open(report.dicom_file.path, 'rb'), content_type='application/dicom')
        resp['Content-Disposition'] = f'inline; filename="study_{report.id}.dcm"'
        resp['Cache-Control'] = 'private, no-cache, no-store, must-revalidate'
        return resp

    sample_path = os.path.join(settings.MEDIA_ROOT, 'radiology_studies', 'sample_chest_xray.dcm')
    if report.is_dicom and os.path.exists(sample_path):
        resp = FileResponse(open(sample_path, 'rb'), content_type='application/dicom')
        resp['Content-Disposition'] = f'inline; filename="study_{report.id}.dcm"'
        resp['Cache-Control'] = 'private, no-cache, no-store, must-revalidate'
        return resp

    return JsonResponse({
        'success': True,
        'message': 'DICOM PACS metadata synchronized. Physical disc frames securely retained in hospital radiodiagnosis vault.',
        'modality': report.modality,
        'slice_count': report.dicom_slice_count,
        'has_physical_file': bool(report.dicom_file)
    })


@login_required
def api_stream_dicom_file(request, report_id):
    """
    Streams raw DICOM Part 10 binary (.dcm) for DICOM-compatible Web Viewers (Cornerstone.js / DWV).
    Enforces authorization check and audit logging.
    """
    import os
    from django.conf import settings
    from django.http import FileResponse

    report = get_object_or_404(RadiologyReport, id=report_id)
    if not check_patient_record_access(request, report.patient, 'RadiologyDICOM', str(report.id)):
        return JsonResponse({'success': False, 'message': 'Access Denied: DICOM streaming unauthorized.'}, status=403)

    record_audit_log(
        request, request.user, request.user.role, 'VIEW_RECORD',
        'RadiologyDICOM', str(report.id), 'SUCCESS',
        f'DICOM study binary streamed for report #{report.id}'
    )

    file_path = None
    if report.dicom_file and hasattr(report.dicom_file, 'path') and os.path.exists(report.dicom_file.path):
        file_path = report.dicom_file.path
    else:
        sample = os.path.join(settings.MEDIA_ROOT, 'radiology_studies', 'sample_chest_xray.dcm')
        if os.path.exists(sample):
            file_path = sample

    if file_path and os.path.exists(file_path):
        resp = FileResponse(open(file_path, 'rb'), content_type='application/dicom')
        resp['Content-Disposition'] = f'inline; filename="study_{report.id}.dcm"'
        resp['Cache-Control'] = 'private, no-cache, no-store, must-revalidate'
        return resp
    
    return JsonResponse({'success': False, 'message': 'DICOM file not found on secure storage server.'}, status=404)


# ==================== LANGUAGE PREFERENCE API ====================
@csrf_exempt
def api_update_language_preference(request):
    """
    Persists citizen preferred language in session and User model.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST
    
    lang = data.get('lang', 'en-IN').strip()
    request.session['hospital_portal_lang'] = lang
    request.session.modified = True

    if request.user.is_authenticated:
        request.user.preferred_language = lang
        request.user.save(update_fields=['preferred_language'])
    
    response = JsonResponse({'success': True, 'lang': lang, 'message': f'Language preference set to {lang}.'})
    response.set_cookie('hospital_lang', lang, max_age=365*24*3600, samesite='Lax')
    return response

