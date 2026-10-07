import json
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from appointments.models import DoctorProfile, AppointmentBooking, HospitalFacility
from patients.models import HospitalVisit, Prescription, VitalRecord, HealthNotification, LabTest, LabOrder, DischargeSummary, VaccinationRecord, ConsentRecord
from core.models import User
from core.audit_utils import record_audit_log

@login_required
def doctor_portal_view(request):
    """
    Dedicated Doctor Clinical Portal.
    Includes:
    1. Today's OPD Queue (Live Token Tracker: WAITING, IN_CONSULTATION, COMPLETED, NO_SHOW)
    2. Patient Consultations & Clinical EHR
    3. Laboratory Test Ordering & Result Verification
    4. Digital Discharge Summary Creator
    5. Digital Prescriptions
    6. Patient Consent Requests
    7. Vaccination Administration
    8. Doctor Performance Telemetry & CME Library
    """
    user = request.user
    today = timezone.now().date()

    # Determine doctor profile
    doctor = None
    doctor_id = request.GET.get('doctor_id')
    if doctor_id:
        doctor = DoctorProfile.objects.filter(id=doctor_id).first()
    if not doctor and hasattr(user, 'doctor_profile') and user.doctor_profile:
        doctor = user.doctor_profile
    if not doctor:
        doctor = DoctorProfile.objects.filter(name__icontains=user.full_name).first()
    if not doctor:
        doctor = DoctorProfile.objects.first()

    all_doctors = DoctorProfile.objects.select_related('hospital').all().order_by('department', 'name')

    # Doctor Appointments
    all_doctor_appointments = AppointmentBooking.objects.filter(doctor=doctor).select_related('patient', 'hospital', 'doctor').order_by('-appointment_date', 'token_number')

    # Today's Queue Breakdown
    today_all = all_doctor_appointments.filter(appointment_date=today)
    today_waiting = today_all.filter(status__in=['WAITING', 'CHECKED_IN', 'BOOKED', 'CONFIRMED']).order_by('token_number')
    today_in_consultation = today_all.filter(status__in=['IN_CONSULTATION', 'IN_PROGRESS']).first()
    today_completed = today_all.filter(status='COMPLETED').order_by('-completed_at', 'token_number')
    today_no_show = today_all.filter(status='NO_SHOW').order_by('token_number')

    # Previous Appointments
    previous_appointments = all_doctor_appointments.filter(appointment_date__lt=today).order_by('-appointment_date', 'token_number')

    # Laboratory Test Catalog & Doctor's Orders
    all_lab_tests = LabTest.objects.all()
    doctor_lab_orders_qs = LabOrder.objects.filter(doctor_name__icontains=doctor.name if doctor else '').select_related('patient', 'test')
    if not doctor_lab_orders_qs.exists():
        doctor_lab_orders_qs = LabOrder.objects.select_related('patient', 'test').all()

    # Prescriptions Issued by this doctor
    doctor_prescriptions = Prescription.objects.filter(prescribed_by__icontains=doctor.name if doctor else '').select_related('patient')[:40]

    # Discharge Summaries
    doctor_discharge_summaries = DischargeSummary.objects.filter(doctor_name__icontains=doctor.name if doctor else '').select_related('patient')[:30]

    # Consent Records for this doctor
    doctor_consents = ConsentRecord.objects.filter(doctor_name__icontains=doctor.name if doctor else '').select_related('patient')[:30]

    # Patients list for modals
    all_patients = User.objects.filter(role='PATIENT').order_by('full_name')

    # Time-Series Analytics
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    curr_year = today.year

    year_labels = month_names
    year_total, year_completed, year_pre = [], [], []
    for m in range(1, 13):
        m_qs = all_doctor_appointments.filter(appointment_date__year=curr_year, appointment_date__month=m)
        year_total.append(m_qs.count())
        year_completed.append(m_qs.filter(status='COMPLETED').count())
        year_pre.append(m_qs.filter(status__in=['CONFIRMED', 'BOOKED', 'WAITING']).count())

    month_labels = [f"Day {d}" for d in range(1, 31, 2)]
    month_total, month_completed, month_pre = [], [], []
    for d in range(1, 31, 2):
        d_qs = all_doctor_appointments.filter(appointment_date__year=curr_year, appointment_date__month=today.month, appointment_date__day=d)
        month_total.append(d_qs.count())
        month_completed.append(d_qs.filter(status='COMPLETED').count())
        month_pre.append(d_qs.filter(status__in=['CONFIRMED', 'BOOKED', 'WAITING']).count())

    days_map = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    week_labels, week_total, week_completed, week_pre = [], [], [], []
    for i in range(6, -1, -1):
        dt = today - datetime.timedelta(days=i)
        w_qs = all_doctor_appointments.filter(appointment_date=dt)
        week_labels.append(f"{days_map[dt.weekday()]} ({dt.strftime('%d-%b')})")
        week_total.append(w_qs.count())
        week_completed.append(w_qs.filter(status='COMPLETED').count())
        week_pre.append(w_qs.filter(status__in=['CONFIRMED', 'BOOKED', 'WAITING']).count())

    day_labels = ['08:00 AM', '09:00 AM', '10:00 AM', '11:00 AM', '12:00 PM', '01:00 PM', '02:00 PM', '03:00 PM', '04:00 PM', '05:00 PM']
    day_total, day_completed, day_pre = [], [], []
    for slot_time in day_labels:
        s_qs = today_all.filter(time_slot__icontains=slot_time[:5])
        day_total.append(s_qs.count())
        day_completed.append(s_qs.filter(status='COMPLETED').count())
        day_pre.append(s_qs.filter(status__in=['CONFIRMED', 'BOOKED', 'WAITING']).count())

    doc_time_series_data = {
        'year': {'labels': year_labels, 'total': year_total, 'completed': year_completed, 'pre_appointments': year_pre},
        'month': {'labels': month_labels, 'total': month_total, 'completed': month_completed, 'pre_appointments': month_pre},
        'week': {'labels': week_labels, 'total': week_total, 'completed': week_completed, 'pre_appointments': week_pre},
        'day': {'labels': day_labels, 'total': day_total, 'completed': day_completed, 'pre_appointments': day_pre},
    }

    stats = {
        'today_total': today_all.count(),
        'today_waiting': today_waiting.count(),
        'today_completed': today_completed.count(),
        'today_in_consultation': 1 if today_in_consultation else 0,
        'today_no_show': today_no_show.count(),
        'previous_total': previous_appointments.count(),
        'all_time_total': all_doctor_appointments.count(),
        'pending_lab_results': doctor_lab_orders_qs.filter(status__in=['ORDERED', 'SAMPLE_COLLECTED', 'PROCESSING']).count(),
        'consultation_room': doctor.consultation_room if doctor else 'Room 203',
        'opd_schedule': f"{doctor.opd_start_time} - {doctor.opd_end_time}" if doctor else '09:00 AM - 01:00 PM',
        'is_present': doctor.is_present_today if doctor else True
    }

    context = {
        'user': user,
        'doctor': doctor,
        'all_doctors': all_doctors,
        'today': today,
        'today_waiting': today_waiting,
        'today_in_consultation': today_in_consultation,
        'today_completed': today_completed,
        'today_no_show': today_no_show,
        'previous_appointments': previous_appointments,
        'all_appointments': all_doctor_appointments,
        'all_lab_tests': all_lab_tests,
        'doctor_lab_orders': doctor_lab_orders_qs[:50],
        'doctor_prescriptions': doctor_prescriptions,
        'doctor_discharge_summaries': doctor_discharge_summaries,
        'doctor_consents': doctor_consents,
        'all_patients': all_patients,
        'stats': stats,
        'doc_time_series_json': json.dumps(doc_time_series_data),
    }
    return render(request, 'doctor/doctor_portal.html', context)


@login_required
@csrf_exempt
def api_doctor_opd_action(request, booking_id):
    """
    Handles live OPD queue actions:
    - 'call_next': Sets called_at, status='WAITING'
    - 'start_consultation': Sets consultation_started_at, status='IN_CONSULTATION'
    - 'complete_consultation': Sets completed_at, status='COMPLETED', creates prescription & visit
    - 'mark_no_show': Sets status='NO_SHOW'
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    action = data.get('action', 'complete_consultation')
    booking = get_object_or_404(AppointmentBooking, id=booking_id)

    if action == 'call_next':
        booking.status = 'WAITING'
        booking.called_at = timezone.now()
        booking.save()
        record_audit_log(request, request.user, 'DOCTOR', 'UPDATE_QUEUE_STATUS', 'AppointmentBooking', str(booking.id), 'SUCCESS', f'Called Token {booking.opd_token_number} for {booking.patient.get_display_name()}')
        msg = f"Token {booking.opd_token_number} called to {booking.consultation_room or 'Room 203'}."

    elif action == 'start_consultation':
        booking.status = 'IN_CONSULTATION'
        booking.consultation_started_at = timezone.now()
        booking.save()
        record_audit_log(request, request.user, 'DOCTOR', 'UPDATE_QUEUE_STATUS', 'AppointmentBooking', str(booking.id), 'SUCCESS', f'Started consultation for {booking.patient.get_display_name()} (Token {booking.opd_token_number})')
        msg = f"Consultation started for Token {booking.opd_token_number} ({booking.patient.get_display_name()})."

    elif action == 'mark_no_show':
        booking.status = 'NO_SHOW'
        booking.save()
        record_audit_log(request, request.user, 'DOCTOR', 'UPDATE_QUEUE_STATUS', 'AppointmentBooking', str(booking.id), 'SUCCESS', f'Marked Token {booking.opd_token_number} as No-Show')
        msg = f"Token {booking.opd_token_number} marked as No-Show."

    elif action == 'complete_consultation':
        notes = data.get('consultation_notes', '').strip() or "Routine OPD consultation completed. Clinical parameters reviewed and verified."
        medicine_name = data.get('medicine_name', '').strip()
        generic_name = data.get('generic_name', '').strip()
        dosage = data.get('dosage', '1 Tablet').strip()
        form = data.get('form', 'Tablet').strip()
        morning = data.get('morning', True)
        afternoon = data.get('afternoon', False)
        night = data.get('night', True)
        timing = data.get('timing', 'After Food').strip()
        duration_days = int(data.get('duration_days', 7))
        quantity = int(data.get('quantity', 14))
        instructions = data.get('instructions', 'Take with warm water as directed.').strip()

        booking.mark_completed(notes=notes)

        # Create Prescription if medication provided
        if medicine_name:
            rx = Prescription.objects.create(
                patient=booking.patient,
                medicine_name=medicine_name,
                generic_name=generic_name or medicine_name,
                dosage=dosage,
                form=form,
                morning=morning,
                afternoon=afternoon,
                night=night,
                timing=timing,
                duration_days=duration_days,
                quantity=quantity,
                instructions=instructions,
                prescribed_by=f"{booking.doctor.name} ({booking.doctor.department})",
                status='ACTIVE'
            )
            record_audit_log(request, request.user, 'DOCTOR', 'CREATE_PRESCRIPTION', 'Prescription', str(rx.id), 'SUCCESS', f'Prescribed {medicine_name} to {booking.patient.get_display_name()}')

        # Record Hospital Visit
        HospitalVisit.objects.create(
            patient=booking.patient,
            hospital_name=booking.hospital.name,
            department=booking.doctor.department,
            doctor_name=booking.doctor.name,
            visit_date=booking.appointment_date,
            reason_for_visit=booking.symptoms or 'OPD Follow-up',
            diagnosis=notes,
            treatment_summary=f"OPD Consultation with {booking.doctor.name}. {notes}"
        )

        # Notify Patient
        HealthNotification.objects.create(
            patient=booking.patient,
            title=f"Consultation Completed: {booking.doctor.name}",
            message=f"Your OPD consultation on {booking.appointment_date.strftime('%d-%b-%Y')} is marked complete. Notes: {notes}",
            category="Record Update",
            action_tab="records"
        )
        record_audit_log(request, request.user, 'DOCTOR', 'UPDATE_QUEUE_STATUS', 'AppointmentBooking', str(booking.id), 'SUCCESS', f'Completed consultation for Token {booking.opd_token_number}')
        msg = f"Consultation completed for Token {booking.opd_token_number} ({booking.patient.get_display_name()})."

    else:
        return JsonResponse({'success': False, 'message': f'Unknown action: {action}'})

    return JsonResponse({
        'success': True,
        'action': action,
        'status': booking.status,
        'message': msg,
        'booking_id': booking.id,
        'token_number': booking.opd_token_number
    })


@login_required
@csrf_exempt
def api_doctor_order_lab_test(request):
    """
    Doctor orders one or more laboratory tests for a patient.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    patient_id = data.get('patient_id')
    test_ids = data.get('test_ids', [])
    if isinstance(test_ids, str):
        test_ids = [t.strip() for t in test_ids.split(',') if t.strip()]

    doctor_name = data.get('doctor_name', request.user.full_name or 'Senior Medical Officer').strip()
    hospital_name = data.get('hospital_name', 'AIIMS New Delhi').strip()
    notes = data.get('notes', 'Routine diagnostic workup').strip()

    if not patient_id or not test_ids:
        return JsonResponse({'success': False, 'message': 'Patient and at least one Test are required.'})

    patient = get_object_or_404(User, id=int(patient_id))
    created_orders = []

    for t_id in test_ids:
        test = LabTest.objects.filter(id=int(t_id)).first()
        if not test:
            continue
        order = LabOrder.objects.create(
            patient=patient,
            doctor_name=doctor_name,
            hospital_name=hospital_name,
            test=test,
            status='ORDERED',
            notes=notes
        )
        created_orders.append(order.order_reference)
        record_audit_log(request, request.user, 'DOCTOR', 'ORDER_LAB_TEST', 'LabOrder', str(order.id), 'SUCCESS', f'Ordered {test.name} for {patient.get_display_name()}')

    # Notify patient
    HealthNotification.objects.create(
        patient=patient,
        title="Laboratory Test Ordered",
        message=f"Dr. {doctor_name} has ordered {len(created_orders)} diagnostic test(s). Please visit the hospital lab for sample collection.",
        category="Record Update",
        action_tab="records"
    )

    return JsonResponse({
        'success': True,
        'message': f'{len(created_orders)} test order(s) placed successfully for {patient.get_display_name()}.',
        'order_references': created_orders
    })


@login_required
@csrf_exempt
def api_doctor_update_lab_result(request, order_id):
    """
    Doctor / Lab Technician updates lab test result values and reference ranges.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    order = get_object_or_404(LabOrder, id=order_id)
    order.result_value = data.get('result_value', order.result_value).strip()
    order.unit = data.get('unit', order.unit).strip()
    order.reference_range = data.get('reference_range', order.reference_range).strip()
    order.status = data.get('status', 'COMPLETED').strip()
    order.lab_technician = data.get('lab_technician', request.user.full_name or 'Certified Lab Technologist').strip()
    order.notes = data.get('notes', order.notes).strip()
    order.result_date = timezone.now()
    order.save()

    record_audit_log(request, request.user, getattr(request.user, 'role', 'DOCTOR'), 'UPDATE_LAB_RESULT', 'LabOrder', str(order.id), 'SUCCESS', f'Updated result for {order.test.name} ({order.order_reference}): {order.result_value} {order.unit}')

    if order.status == 'COMPLETED':
        HealthNotification.objects.create(
            patient=order.patient,
            title=f"Lab Report Ready: {order.test.name}",
            message=f"Your laboratory test result for {order.test.name} is now available for viewing and download.",
            category="Record Update",
            action_tab="records"
        )

    return JsonResponse({
        'success': True,
        'message': f'Lab Order #{order.order_reference} updated to {order.status}.',
        'order_id': order.id,
        'status': order.status
    })


@login_required
@csrf_exempt
def api_doctor_create_discharge_summary(request):
    """
    Doctor generates a Digital Discharge Summary.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    patient_id = data.get('patient_id')
    if not patient_id:
        return JsonResponse({'success': False, 'message': 'Patient is required.'})

    patient = get_object_or_404(User, id=int(patient_id))
    doctor_name = data.get('doctor_name', request.user.full_name or 'Dr. Ravi Kumar').strip()
    doctor_reg_no = data.get('doctor_reg_no', 'MCI-88492').strip()
    hospital_name = data.get('hospital_name', 'AIIMS New Delhi').strip()
    department = data.get('department', 'General Medicine').strip()
    reason_for_admission = data.get('reason_for_admission', 'Acute clinical observation and stabilization').strip()
    clinical_findings = data.get('clinical_findings', 'Patient presented with stable vital parameters after initial treatment.').strip()
    diagnosis = data.get('diagnosis', 'Essential Hypertension with Mild Hyperglycemia').strip()
    procedures_treatment = data.get('procedures_treatment', 'IV Fluids, Antihypertensive therapy, Glycemic regulation.').strip()
    investigation_results = data.get('investigation_results', 'CBC normal, HbA1c 6.8%, Chest X-Ray clear.').strip()
    condition_at_discharge = data.get('condition_at_discharge', 'Stable, Afebrile, and Ambulatory').strip()
    discharge_medicines = data.get('discharge_medicines', 'Tab Telmisartan 40mg (1-0-0), Tab Metformin 500mg (0-0-1)').strip()
    diet_instructions = data.get('diet_instructions', 'Low sodium diabetic diet. Avoid oily and processed foods.').strip()
    activity_instructions = data.get('activity_instructions', 'Light walking permitted. Avoid strenuous exercise for 1 week.').strip()
    follow_up_instructions = data.get('follow_up_instructions', 'Review in OPD Room 203 after 10 days.').strip()
    
    summary = DischargeSummary.objects.create(
        patient=patient,
        doctor_name=doctor_name,
        doctor_reg_no=doctor_reg_no,
        hospital_name=hospital_name,
        department=department,
        reason_for_admission=reason_for_admission,
        clinical_findings=clinical_findings,
        diagnosis=diagnosis,
        procedures_treatment=procedures_treatment,
        investigation_results=investigation_results,
        condition_at_discharge=condition_at_discharge,
        discharge_medicines=discharge_medicines,
        diet_instructions=diet_instructions,
        activity_instructions=activity_instructions,
        follow_up_instructions=follow_up_instructions
    )

    record_audit_log(request, request.user, 'DOCTOR', 'CREATE_DISCHARGE_SUMMARY', 'DischargeSummary', str(summary.id), 'SUCCESS', f'Created discharge summary #{summary.summary_reference} for {patient.get_display_name()}')

    HealthNotification.objects.create(
        patient=patient,
        title="Discharge Summary Issued",
        message=f"Your Digital Discharge Summary from {hospital_name} (#{summary.summary_reference}) is available to view and print.",
        category="Record Update",
        action_tab="records"
    )

    return JsonResponse({
        'success': True,
        'message': f'Discharge Summary #{summary.summary_reference} generated successfully.',
        'summary_reference': summary.summary_reference,
        'verification_code': summary.verification_code
    })


@login_required
@csrf_exempt
def api_doctor_request_consent(request):
    """
    Doctor requests consent from patient to access their medical history.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    patient_id = data.get('patient_id')
    if not patient_id:
        return JsonResponse({'success': False, 'message': 'Patient ID is required.'})

    patient = get_object_or_404(User, id=int(patient_id))
    doctor_name = data.get('doctor_name', request.user.full_name or 'Dr. Ravi Kumar').strip()
    doctor_reg_id = data.get('doctor_reg_id', 'DOC-AIIM-1001').strip()
    hospital_name = data.get('hospital_name', 'Government Hospital').strip()
    purpose = data.get('purpose', 'Clinical Consultation & Diagnostic Review').strip()

    consent = ConsentRecord.objects.create(
        patient=patient,
        doctor_name=doctor_name,
        doctor_reg_id=doctor_reg_id,
        hospital_name=hospital_name,
        purpose=purpose,
        scope_medical_history=True,
        scope_lab_reports=True,
        scope_prescriptions=True,
        status='PENDING'
    )

    HealthNotification.objects.create(
        patient=patient,
        title=f"Record Access Request from {doctor_name}",
        message=f"{doctor_name} ({hospital_name}) has requested access to your medical history for: {purpose}. Please review and approve in Settings/Consent tab.",
        category="Consent Alert",
        action_tab="settings"
    )

    return JsonResponse({
        'success': True,
        'message': f'Consent request sent to {patient.get_display_name()}.',
        'consent_id': consent.id
    })


@login_required
@csrf_exempt
def api_doctor_add_vaccination(request):
    """
    Clinician records an administered vaccination dose.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    patient_id = data.get('patient_id')
    vaccine_name = data.get('vaccine_name', '').strip()
    dose_number = int(data.get('dose_number', 1))
    batch_number = data.get('batch_number', 'VAC-2026-B10').strip()
    hospital_center = data.get('hospital_center', 'AIIMS Primary Health Centre').strip()
    provider_name = data.get('provider_name', request.user.full_name or 'Vaccination Officer').strip()
    notes = data.get('notes', 'Administered without adverse effects.').strip()

    if not patient_id or not vaccine_name:
        return JsonResponse({'success': False, 'message': 'Patient and Vaccine Name are required.'})

    patient = get_object_or_404(User, id=int(patient_id))

    record = VaccinationRecord.objects.create(
        patient=patient,
        vaccine_name=vaccine_name,
        dose_number=dose_number,
        date_given=timezone.now().date(),
        hospital_center=hospital_center,
        provider_name=provider_name,
        batch_number=batch_number,
        status='COMPLETED',
        notes=notes
    )

    record_audit_log(request, request.user, 'DOCTOR', 'UPDATE_VACCINATION', 'VaccinationRecord', str(record.id), 'SUCCESS', f'Administered {vaccine_name} Dose #{dose_number} to {patient.get_display_name()}')

    HealthNotification.objects.create(
        patient=patient,
        title=f"Vaccination Recorded: {vaccine_name}",
        message=f"Dose #{dose_number} of {vaccine_name} has been officially recorded in your national immunization registry.",
        category="Immunization",
        action_tab="records"
    )

    return JsonResponse({
        'success': True,
        'message': f'Vaccination record added for {patient.get_display_name()}.',
        'record_id': record.id
    })


@login_required
@csrf_exempt
def api_mark_appointment_completed(request, booking_id):
    """
    Backward-compatibility wrapper pointing to api_doctor_opd_action.
    """
    return api_doctor_opd_action(request, booking_id)


@login_required
@csrf_exempt
def api_doctor_toggle_duty(request, doctor_id):
    """
    Doctor or Admin toggles doctor duty presence.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    doctor = get_object_or_404(DoctorProfile, id=doctor_id)
    doctor.is_present_today = not doctor.is_present_today
    doctor.save()

    status_msg = "You are marked PRESENT in hospital OPD today." if doctor.is_present_today else "You are marked OFF-DUTY / ON LEAVE today."
    return JsonResponse({
        'success': True,
        'is_present_today': doctor.is_present_today,
        'message': status_msg
    })

