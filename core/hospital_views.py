from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Q, Sum
from core.models import User, AuditLog
from appointments.models import (
    HospitalFacility, HospitalAdmin, DoctorProfile, Department,
    AppointmentBooking, HospitalResource
)
import json
import csv
import datetime

def get_user_hospital(user):
    """Helper to retrieve hospital for a logged-in Hospital Admin or Admin."""
    if hasattr(user, 'hospital_admin_profile'):
        return user.hospital_admin_profile.hospital
    if user.role == 'ADMIN':
        return HospitalFacility.objects.filter(status='ACTIVE').first()
    admin_link = HospitalAdmin.objects.filter(user=user, is_active=True).first()
    if admin_link:
        return admin_link.hospital
    # Fallback to first hospital if available
    return HospitalFacility.objects.first()

@login_required
def hospital_portal_view(request):
    if request.user.role not in ['HOSPITAL', 'ADMIN'] and not hasattr(request.user, 'hospital_admin_profile'):
        return redirect('role_portal')

    hospital = get_user_hospital(request.user)
    if not hospital:
        # Fallback dummy hospital if none in DB
        hospital, _ = HospitalFacility.objects.get_or_create(
            name="AIIMS New Delhi - Apex Healthcare Institute",
            defaults={
                'facility_type': 'Apex Institute',
                'address': 'Ansari Nagar, New Delhi',
                'city': 'New Delhi',
                'district': 'New Delhi',
                'state': 'Delhi',
                'pincode': '110029',
                'contact_phone': '+91 11 26588500',
                'email': 'admin@aiims.edu',
                'status': 'ACTIVE'
            }
        )
        if not hasattr(request.user, 'hospital_admin_profile'):
            HospitalAdmin.objects.create(user=request.user, hospital=hospital, designation="Medical Director")

    # Resource Status
    resource, _ = HospitalResource.objects.get_or_create(hospital=hospital)

    today = timezone.now().date()
    yesterday = today - datetime.timedelta(days=1)
    
    start_this_week = today - datetime.timedelta(days=today.weekday())
    start_last_week = start_this_week - datetime.timedelta(days=7)
    end_last_week = start_this_week - datetime.timedelta(days=1)

    start_this_month = today.replace(day=1)
    last_month_end = start_this_month - datetime.timedelta(days=1)
    start_last_month = last_month_end.replace(day=1)

    # Today Appointments
    today_apts = AppointmentBooking.objects.filter(hospital=hospital, appointment_date=today)
    yesterday_apts_count = AppointmentBooking.objects.filter(hospital=hospital, appointment_date=yesterday).count()
    
    today_total = today_apts.count()
    today_completed = today_apts.filter(status='COMPLETED').count()
    today_pending = today_apts.filter(status__in=['BOOKED', 'CONFIRMED', 'CHECKED_IN', 'WAITING', 'IN_CONSULTATION']).count()
    today_cancelled = today_apts.filter(status='CANCELLED').count()
    today_noshow = today_apts.filter(status='NO_SHOW').count()
    today_emergency = today_apts.filter(is_emergency=True).count()

    # Comparison metrics
    this_week_count = AppointmentBooking.objects.filter(hospital=hospital, appointment_date__gte=start_this_week).count()
    last_week_count = AppointmentBooking.objects.filter(hospital=hospital, appointment_date__range=[start_last_week, end_last_week]).count()
    
    this_month_count = AppointmentBooking.objects.filter(hospital=hospital, appointment_date__gte=start_this_month).count()
    last_month_count = AppointmentBooking.objects.filter(hospital=hospital, appointment_date__range=[start_last_month, last_month_end]).count()

    # Doctor statistics
    doctors = DoctorProfile.objects.filter(hospital=hospital)
    total_doctors = doctors.count()
    active_doctors = doctors.filter(status='ACTIVE', is_active=True).count()
    doctors_on_leave = doctors.filter(Q(status='ON_LEAVE') | Q(leave_status=True)).count()
    pending_verification_doctors = doctors.filter(verification_status='PENDING_VERIFICATION').count()

    # Departments
    departments = Department.objects.filter(hospital=hospital, is_active=True)

    # OPD Queue Today
    live_queue = today_apts.filter(status__in=['BOOKED', 'CONFIRMED', 'CHECKED_IN', 'WAITING', 'IN_CONSULTATION']).order_order = ['token_number']
    
    # Audit Logs
    logs = AuditLog.objects.filter(resource_type='HospitalFacility', resource_id=str(hospital.id))[:10]

    context = {
        'hospital': hospital,
        'resource': resource,
        'today': today,
        'today_total': today_total,
        'today_completed': today_completed,
        'today_pending': today_pending,
        'today_cancelled': today_cancelled,
        'today_noshow': today_noshow,
        'today_emergency': today_emergency,
        'yesterday_total': yesterday_apts_count,
        'this_week_count': this_week_count,
        'last_week_count': last_week_count,
        'this_month_count': this_month_count,
        'last_month_count': last_month_count,
        'total_doctors': total_doctors,
        'active_doctors': active_doctors,
        'doctors_on_leave': doctors_on_leave,
        'pending_verification_doctors': pending_verification_doctors,
        'doctors': doctors,
        'departments': departments,
        'live_queue': today_apts,
        'logs': logs,
    }

    return render(request, 'hospital/hospital_portal.html', context)


@login_required
def api_hospital_appointments_list(request):
    """API endpoint to search and filter appointments for the hospital."""
    hospital = get_user_hospital(request.user)
    if not hospital:
        return JsonResponse({'status': 'error', 'message': 'Hospital not found.'}, status=404)

    query = AppointmentBooking.objects.filter(hospital=hospital)

    # Filters
    date_filter = request.GET.get('date_filter', 'today')
    particular_date = request.GET.get('particular_date', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    status_filter = request.GET.get('status', 'ALL')
    doctor_id = request.GET.get('doctor_id', '')
    department_name = request.GET.get('department', '')
    search_query = request.GET.get('search', '').strip()

    today = timezone.now().date()

    if particular_date:
        query = query.filter(appointment_date=particular_date)
    elif date_filter == 'today':
        query = query.filter(appointment_date=today)
    elif date_filter == 'yesterday':
        query = query.filter(appointment_date=today - datetime.timedelta(days=1))
    elif date_filter == 'this_week':
        start_w = today - datetime.timedelta(days=today.weekday())
        query = query.filter(appointment_date__gte=start_w)
    elif date_filter == 'this_month':
        query = query.filter(appointment_date__gte=today.replace(day=1))
    elif date_filter == 'this_year':
        query = query.filter(appointment_date__year=today.year)
    elif date_filter == 'custom' and start_date and end_date:
        query = query.filter(appointment_date__range=[start_date, end_date])

    if status_filter and status_filter != 'ALL':
        if status_filter == 'PENDING':
            query = query.filter(status__in=['BOOKED', 'CONFIRMED', 'CHECKED_IN', 'WAITING', 'IN_CONSULTATION'])
        else:
            query = query.filter(status=status_filter)

    if doctor_id:
        query = query.filter(doctor_id=doctor_id)

    if department_name:
        query = query.filter(doctor__department=department_name)

    if search_query:
        query = query.filter(
            Q(patient__full_name__icontains=search_query) |
            Q(patient__phone__icontains=search_query) |
            Q(patient__abha_id__icontains=search_query) |
            Q(doctor__name__icontains=search_query) |
            Q(booking_reference__icontains=search_query) |
            Q(opd_token_number__icontains=search_query)
        )

    appointments_data = []
    for apt in query.select_related('patient', 'doctor')[:150]:
        appointments_data.append({
            'id': apt.id,
            'booking_reference': apt.booking_reference,
            'opd_token': apt.opd_token_number or str(apt.token_number),
            'patient_name': apt.patient.get_display_name(),
            'patient_phone': apt.patient.phone,
            'patient_abha': apt.patient.abha_id or 'N/A',
            'doctor_name': apt.doctor.name,
            'doctor_id': apt.doctor.id,
            'department': apt.doctor.department,
            'appointment_date': apt.appointment_date.strftime('%Y-%m-%d'),
            'time_slot': apt.time_slot,
            'status': apt.status,
            'is_emergency': apt.is_emergency,
            'symptoms': apt.symptoms,
            'cancellation_reason': apt.cancellation_reason,
            'consultation_room': apt.consultation_room,
        })

    return JsonResponse({
        'status': 'success',
        'count': len(appointments_data),
        'appointments': appointments_data
    })


@csrf_exempt
@login_required
def api_hospital_appointment_action(request, booking_id):
    """API endpoint to confirm, complete, cancel, reschedule, or mark no-show."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required.'}, status=405)

    hospital = get_user_hospital(request.user)
    apt = get_object_or_404(AppointmentBooking, id=booking_id, hospital=hospital)

    try:
        data = json.loads(request.body)
        action = data.get('action') # confirm, complete, cancel, reschedule, noshow
        reason = data.get('reason', '').strip()
        new_date = data.get('new_date', '').strip()
        new_slot = data.get('new_slot', '').strip()

        old_status = apt.status

        if action == 'confirm':
            apt.status = 'BOOKED'
            apt.save()
            AuditLog.objects.create(
                user=request.user, user_display=request.user.get_display_name(), role='HOSPITAL',
                action='CONFIRM_APPOINTMENT', resource_type='AppointmentBooking', resource_id=str(apt.id),
                details=f"Confirmed appointment {apt.booking_reference}"
            )
        elif action == 'complete':
            notes = data.get('notes', 'Completed by Hospital Admin')
            apt.mark_completed(notes)
            AuditLog.objects.create(
                user=request.user, user_display=request.user.get_display_name(), role='HOSPITAL',
                action='UPDATE_QUEUE_STATUS', resource_type='AppointmentBooking', resource_id=str(apt.id),
                details=f"Marked appointment {apt.booking_reference} as completed."
            )
        elif action == 'cancel':
            apt.status = 'CANCELLED'
            apt.cancellation_reason = reason or 'Cancelled by Hospital Management'
            apt.save()
            AuditLog.objects.create(
                user=request.user, user_display=request.user.get_display_name(), role='HOSPITAL',
                action='CANCEL_APPOINTMENT', resource_type='AppointmentBooking', resource_id=str(apt.id),
                details=f"Cancelled appointment {apt.booking_reference}. Reason: {apt.cancellation_reason}"
            )
        elif action == 'noshow':
            apt.status = 'NO_SHOW'
            apt.save()
            AuditLog.objects.create(
                user=request.user, user_display=request.user.get_display_name(), role='HOSPITAL',
                action='UPDATE_QUEUE_STATUS', resource_type='AppointmentBooking', resource_id=str(apt.id),
                details=f"Marked appointment {apt.booking_reference} as No Show."
            )
        elif action == 'reschedule':
            if new_date:
                apt.appointment_date = new_date
            if new_slot:
                apt.time_slot = new_slot
            apt.status = 'RESCHEDULED'
            apt.save()
            AuditLog.objects.create(
                user=request.user, user_display=request.user.get_display_name(), role='HOSPITAL',
                action='RESCHEDULE_APPOINTMENT', resource_type='AppointmentBooking', resource_id=str(apt.id),
                details=f"Rescheduled appointment {apt.booking_reference} to {new_date} ({new_slot})."
            )

        return JsonResponse({
            'status': 'success',
            'message': f"Appointment status updated to {apt.status}.",
            'new_status': apt.status
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@login_required
def api_hospital_add_doctor(request):
    """API endpoint to add a doctor to the hospital."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required.'}, status=405)

    hospital = get_user_hospital(request.user)
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip()
        email = data.get('email', '').strip()
        qualification = data.get('qualification', 'MBBS, MD').strip()
        department_name = data.get('department', 'General Medicine').strip()
        licensing_id = data.get('licensing_id', '').strip()
        experience_years = int(data.get('experience_years', 5))
        consultation_fee = float(data.get('consultation_fee', 0.00))
        working_days = data.get('working_days', 'Mon, Tue, Wed, Thu, Fri')
        opd_start_time = data.get('opd_start_time', '09:00 AM')
        opd_end_time = data.get('opd_end_time', '01:00 PM')
        slot_duration = int(data.get('slot_duration', 15))
        max_daily_slots = int(data.get('max_patients_per_day', 35))

        if not name or not phone:
            return JsonResponse({'status': 'error', 'message': 'Doctor Name and Phone are required.'}, status=400)

        # Create or link user account for doctor
        doctor_user, created = User.objects.get_or_create(
            phone=phone,
            defaults={
                'role': 'DOCTOR',
                'full_name': name,
                'email': email
            }
        )
        if created:
            doctor_user.set_password('doctor123')
            doctor_user.save()

        dept_obj, _ = Department.objects.get_or_create(hospital=hospital, name=department_name)

        # Hospital admin adding doctor requires Government verification
        ver_status = 'PENDING_VERIFICATION' if request.user.role != 'ADMIN' else 'VERIFIED'

        doc = DoctorProfile.objects.create(
            hospital=hospital,
            user=doctor_user,
            doctor_reg_id=licensing_id or None,
            name=name,
            phone=phone,
            email=email,
            qualification=qualification,
            department=department_name,
            department_obj=dept_obj,
            specialization=department_name,
            experience_years=experience_years,
            consultation_fee=consultation_fee,
            verification_status=ver_status,
            available_days=working_days,
            opd_start_time=opd_start_time,
            opd_end_time=opd_end_time,
            appointment_duration=slot_duration,
            max_daily_slots=max_daily_slots,
            status='ACTIVE'
        )

        AuditLog.objects.create(
            user=request.user, user_display=request.user.get_display_name(), role='HOSPITAL',
            action='ADD_DOCTOR', resource_type='DoctorProfile', resource_id=str(doc.id),
            details=f"Added doctor {doc.name} ({doc.department}) to {hospital.name} [Status: {ver_status}]."
        )

        return JsonResponse({
            'status': 'success',
            'message': f"Doctor {doc.name} registered successfully. State: {ver_status}.",
            'doctor_id': doc.id
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@login_required
def api_hospital_update_doctor(request, doctor_id):
    """API endpoint to edit doctor details."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required.'}, status=405)

    hospital = get_user_hospital(request.user)
    doc = get_object_or_404(DoctorProfile, id=doctor_id, hospital=hospital)

    try:
        data = json.loads(request.body)
        doc.name = data.get('name', doc.name)
        doc.qualification = data.get('qualification', doc.qualification)
        doc.department = data.get('department', doc.department)
        doc.experience_years = int(data.get('experience_years', doc.experience_years))
        doc.consultation_fee = float(data.get('consultation_fee', doc.consultation_fee))
        doc.available_days = data.get('working_days', doc.available_days)
        doc.opd_start_time = data.get('opd_start_time', doc.opd_start_time)
        doc.opd_end_time = data.get('opd_end_time', doc.opd_end_time)
        doc.appointment_duration = int(data.get('slot_duration', doc.appointment_duration))
        doc.max_daily_slots = int(data.get('max_patients_per_day', doc.max_daily_slots))
        doc.leave_status = data.get('leave_status', doc.leave_status)

        if 'status' in data:
            doc.status = data['status']
            doc.is_active = (doc.status == 'ACTIVE')

        doc.save()

        AuditLog.objects.create(
            user=request.user, user_display=request.user.get_display_name(), role='HOSPITAL',
            action='UPDATE_DOCTOR', resource_type='DoctorProfile', resource_id=str(doc.id),
            details=f"Updated doctor profile for {doc.name}."
        )

        return JsonResponse({'status': 'success', 'message': f"Doctor {doc.name} profile updated successfully."})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@login_required
def api_hospital_update_resources(request):
    """API endpoint to update hospital beds and resources."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required.'}, status=405)

    hospital = get_user_hospital(request.user)
    resource, _ = HospitalResource.objects.get_or_create(hospital=hospital)

    try:
        data = json.loads(request.body)
        resource.general_beds_total = int(data.get('general_beds_total', resource.general_beds_total))
        resource.general_beds_occupied = int(data.get('general_beds_occupied', resource.general_beds_occupied))
        resource.icu_beds_total = int(data.get('icu_beds_total', resource.icu_beds_total))
        resource.icu_beds_occupied = int(data.get('icu_beds_occupied', resource.icu_beds_occupied))
        resource.ventilator_beds_total = int(data.get('ventilator_beds_total', resource.ventilator_beds_total))
        resource.ventilator_beds_occupied = int(data.get('ventilator_beds_occupied', resource.ventilator_beds_occupied))
        resource.oxygen_beds_total = int(data.get('oxygen_beds_total', resource.oxygen_beds_total))
        resource.oxygen_beds_occupied = int(data.get('oxygen_beds_occupied', resource.oxygen_beds_occupied))
        resource.oxygen_supply_status = data.get('oxygen_supply_status', resource.oxygen_supply_status)
        resource.save()

        AuditLog.objects.create(
            user=request.user, user_display=request.user.get_display_name(), role='HOSPITAL',
            action='UPDATE_BED_RESOURCE', resource_type='HospitalResource', resource_id=str(resource.id),
            details=f"Updated bed resources for {hospital.name}. ICU Occupancy: {resource.icu_occupancy_pct()}%"
        )

        return JsonResponse({
            'status': 'success',
            'message': 'Bed and resource counts updated successfully.',
            'icu_pct': resource.icu_occupancy_pct(),
            'total_pct': resource.total_occupancy_pct()
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def api_hospital_export_reports(request):
    """API endpoint to generate exportable CSV report."""
    hospital = get_user_hospital(request.user)
    report_type = request.GET.get('type', 'opd_daily')
    format_type = request.GET.get('format', 'csv')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{hospital.name.replace(" ", "_")}_{report_type}_{timezone.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)

    if report_type == 'opd_daily':
        writer.writerow(['Booking Ref', 'OPD Token', 'Patient Name', 'Patient Phone', 'Doctor', 'Department', 'Date', 'Time Slot', 'Status'])
        apts = AppointmentBooking.objects.filter(hospital=hospital, appointment_date=timezone.now().date())
        for a in apts:
            writer.writerow([a.booking_reference, a.opd_token_number, a.patient.get_display_name(), a.patient.phone, a.doctor.name, a.doctor.department, a.appointment_date, a.time_slot, a.status])

    elif report_type == 'doctors':
        writer.writerow(['Doctor ID', 'Name', 'Department', 'Qualification', 'Fee', 'Verification Status', 'Total Appointments'])
        docs = DoctorProfile.objects.filter(hospital=hospital)
        for d in docs:
            writer.writerow([d.doctor_reg_id, d.name, d.department, d.qualification, d.consultation_fee, d.verification_status, d.total_appointments_count()])

    elif report_type == 'resources':
        r, _ = HospitalResource.objects.get_or_create(hospital=hospital)
        writer.writerow(['Category', 'Total Beds', 'Occupied Beds', 'Available Beds', 'Occupancy %'])
        writer.writerow(['General Beds', r.general_beds_total, r.general_beds_occupied, r.general_beds_available(), f"{round(r.general_beds_occupied/max(1,r.general_beds_total)*100,1)}%"])
        writer.writerow(['ICU Beds', r.icu_beds_total, r.icu_beds_occupied, r.icu_beds_available(), f"{r.icu_occupancy_pct()}%"])
        writer.writerow(['Ventilator Beds', r.ventilator_beds_total, r.ventilator_beds_occupied, r.ventilator_beds_available(), f"{round(r.ventilator_beds_occupied/max(1,r.ventilator_beds_total)*100,1)}%"])
        writer.writerow(['Oxygen Beds', r.oxygen_beds_total, r.oxygen_beds_occupied, r.oxygen_beds_available(), f"{round(r.oxygen_beds_occupied/max(1,r.oxygen_beds_total)*100,1)}%"])

    return response
