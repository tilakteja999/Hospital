import json
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Count, Q
from django.core.paginator import Paginator
from appointments.models import DoctorProfile, HospitalFacility, HospitalArea, AppointmentBooking
from core.models import User, AuditLog, HealthScheme, HealthAdvisory
from patients.models import VitalRecord, HospitalVisit, LabOrder
from core.audit_utils import record_audit_log

@login_required
def admin_portal_view(request):
    """
    Dedicated Government Health Admin Portal with full Doctor Scheduling, OPD Queues,
    Audit Logs, Public Advisories, and Health Schemes.
    """
    user = request.user
    if user.role != 'ADMIN' and not user.is_superuser:
        record_audit_log(request, user, getattr(user, 'role', 'PATIENT'), 'SYSTEM_SECURITY', 'AdminPortal', '', 'FAILURE', 'Non-admin attempted to access admin portal.')
        return redirect('dashboard')

    today = timezone.now().date()

    # Doctor statistics
    all_doctors = DoctorProfile.objects.select_related('hospital', 'hospital__area', 'user').all().order_by('department', 'name')
    total_doctors = all_doctors.count()
    active_doctors = all_doctors.filter(status='ACTIVE')
    active_doctors_count = active_doctors.count()
    present_doctors_count = all_doctors.filter(is_present_today=True).count()
    absent_doctors_count = all_doctors.filter(is_present_today=False).count()

    # Patient & Hospital statistics
    all_patients = User.objects.filter(role='PATIENT')
    total_patients_count = all_patients.count()
    all_hospitals = HospitalFacility.objects.select_related('area').all()
    total_hospitals_count = all_hospitals.count()
    all_areas = HospitalArea.objects.all()

    # Appointment & Queue statistics
    all_bookings = AppointmentBooking.objects.select_related('patient', 'doctor', 'hospital', 'doctor__hospital').all()
    total_appointments_all_time = all_bookings.count()
    pre_appointments_count = all_bookings.filter(status__in=['CONFIRMED', 'BOOKED']).count()
    completed_appointments_count = all_bookings.filter(status='COMPLETED').count()
    uncompleted_appointments_count = all_bookings.exclude(status__in=['COMPLETED', 'CANCELLED']).count()

    today_appointments = all_bookings.filter(appointment_date=today)
    today_total_count = today_appointments.count()
    today_completed_count = today_appointments.filter(status='COMPLETED').count()
    today_pending_count = today_appointments.exclude(status__in=['COMPLETED', 'CANCELLED']).count()

    # Pending Lab Orders
    pending_lab_orders_count = LabOrder.objects.exclude(status__in=['COMPLETED', 'CANCELLED']).count()

    # Audit Logs (Latest 50)
    recent_audit_logs = AuditLog.objects.select_related('user').all()[:60]

    # Health Schemes & Advisories
    all_schemes = HealthScheme.objects.all()
    all_advisories = HealthAdvisory.objects.all()

    # Department Breakdown
    dept_stats = []
    for code, label in DoctorProfile.DEPARTMENT_CHOICES:
        doc_count = DoctorProfile.objects.filter(department=code).count()
        total_apts = AppointmentBooking.objects.filter(doctor__department=code).count()
        today_apts = AppointmentBooking.objects.filter(doctor__department=code, appointment_date=today).count()
        today_completed = AppointmentBooking.objects.filter(doctor__department=code, appointment_date=today, status='COMPLETED').count()
        
        dept_stats.append({
            'department': code,
            'label': label,
            'doctor_count': doc_count,
            'total_appointments': total_apts,
            'today_appointments': today_apts,
            'today_completed': today_completed
        })

    dept_stats.sort(key=lambda x: x['total_appointments'], reverse=True)

    # Dynamic Time-series analytics
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    curr_year = today.year

    year_labels = month_names
    year_total, year_completed, year_pre = [], [], []
    for m in range(1, 13):
        m_qs = all_bookings.filter(appointment_date__year=curr_year, appointment_date__month=m)
        year_total.append(m_qs.count())
        year_completed.append(m_qs.filter(status='COMPLETED').count())
        year_pre.append(m_qs.filter(status__in=['CONFIRMED', 'BOOKED']).count())

    month_labels = [f"Day {d}" for d in range(1, 31, 2)]
    month_total, month_completed, month_pre = [], [], []
    for d in range(1, 31, 2):
        d_qs = all_bookings.filter(appointment_date__year=curr_year, appointment_date__month=today.month, appointment_date__day=d)
        month_total.append(d_qs.count())
        month_completed.append(d_qs.filter(status='COMPLETED').count())
        month_pre.append(d_qs.filter(status__in=['CONFIRMED', 'BOOKED']).count())

    days_map = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    week_labels, week_total, week_completed, week_pre = [], [], [], []
    for i in range(6, -1, -1):
        dt = today - datetime.timedelta(days=i)
        w_qs = all_bookings.filter(appointment_date=dt)
        week_labels.append(f"{days_map[dt.weekday()]} ({dt.strftime('%d-%b')})")
        week_total.append(w_qs.count())
        week_completed.append(w_qs.filter(status='COMPLETED').count())
        week_pre.append(w_qs.filter(status__in=['CONFIRMED', 'BOOKED']).count())

    day_labels = ['08:00 AM', '09:00 AM', '10:00 AM', '11:00 AM', '12:00 PM', '01:00 PM', '02:00 PM', '03:00 PM', '04:00 PM', '05:00 PM']
    day_total, day_completed, day_pre = [], [], []
    for slot_time in day_labels:
        s_qs = today_appointments.filter(time_slot__icontains=slot_time[:5])
        day_total.append(s_qs.count())
        day_completed.append(s_qs.filter(status='COMPLETED').count())
        day_pre.append(s_qs.filter(status__in=['CONFIRMED', 'BOOKED']).count())

    time_series_data = {
        'year': {'labels': year_labels, 'total': year_total, 'completed': year_completed, 'pre_appointments': year_pre},
        'month': {'labels': month_labels, 'total': month_total, 'completed': month_completed, 'pre_appointments': month_pre},
        'week': {'labels': week_labels, 'total': week_total, 'completed': week_completed, 'pre_appointments': week_pre},
        'day': {'labels': day_labels, 'total': day_total, 'completed': day_completed, 'pre_appointments': day_pre},
    }

    appointment_types = [
        {'id': 'all', 'name': 'All Types & Specializations'},
        {'id': 'General Medicine', 'name': 'General Medicine & Family OPD'},
        {'id': 'Cardiology', 'name': 'Cardiology & Heart Care'},
        {'id': 'Pulmonology', 'name': 'Pulmonology & Respiratory Care'},
        {'id': 'Endocrinology', 'name': 'Endocrinology & Diabetes'},
        {'id': 'Nephrology', 'name': 'Nephrology & Renal Care'},
        {'id': 'Pediatrics', 'name': 'Pediatrics & Child Care'},
        {'id': 'Orthopedics', 'name': 'Orthopedics & Joint Care'},
        {'id': 'Gynecology', 'name': 'Obstetrics & Gynecology'},
        {'id': 'Dermatology', 'name': 'Dermatology & Skin Care'},
        {'id': 'Neurology', 'name': 'Neurology & Brain Sciences'},
        {'id': 'Gastroenterology', 'name': 'Gastroenterology & Digestive Health'},
        {'id': 'Oncology', 'name': 'Oncology & Cancer Care'},
        {'id': 'ENT', 'name': 'ENT & Otolaryngology'},
        {'id': 'Ophthalmology', 'name': 'Ophthalmology & Eye Care'},
        {'id': 'Urology', 'name': 'Urology & Kidney Care'},
        {'id': 'Psychiatry', 'name': 'Psychiatry & Behavioral Health'},
        {'id': 'Dentistry', 'name': 'Dental Sciences & Maxillofacial Care'},
        {'id': 'Radiology', 'name': 'Radiology & Imaging Diagnostics'},
        {'id': 'Emergency Medicine', 'name': 'Trauma & Emergency Care'},
        {'id': 'Anesthesiology', 'name': 'Anesthesia & Critical Care'},
        {'id': 'Blood Test', 'name': 'Blood Test & Pathology Lab'},
        {'id': 'MRI Scan', 'name': 'MRI Diagnostics'},
        {'id': 'CT Scan', 'name': 'CT Scan & HRCT Imaging'},
        {'id': 'X-Ray', 'name': 'Digital X-Ray & Ultrasound'},
    ]

    context = {
        'user': user,
        'all_doctors': all_doctors,
        'total_doctors': total_doctors,
        'active_doctors_count': active_doctors_count,
        'present_doctors_count': present_doctors_count,
        'absent_doctors_count': absent_doctors_count,
        'total_patients_count': total_patients_count,
        'total_hospitals_count': total_hospitals_count,
        'total_appointments_all_time': total_appointments_all_time,
        'pre_appointments_count': pre_appointments_count,
        'completed_appointments_count': completed_appointments_count,
        'uncompleted_appointments_count': uncompleted_appointments_count,
        'today_total_count': today_total_count,
        'today_completed_count': today_completed_count,
        'today_pending_count': today_pending_count,
        'pending_lab_orders_count': pending_lab_orders_count,
        'dept_stats': dept_stats,
        'dept_stats_json': json.dumps(dept_stats),
        'time_series_json': json.dumps(time_series_data),
        'appointment_types': appointment_types,
        'all_hospitals': all_hospitals,
        'all_areas': all_areas,
        'all_patients': all_patients,
        'recent_bookings': all_bookings[:50],
        'recent_audit_logs': recent_audit_logs,
        'all_schemes': all_schemes,
        'all_advisories': all_advisories,
        'today': today,
    }
    return render(request, 'admin/admin_portal.html', context)


@login_required
@csrf_exempt
def api_add_doctor(request):
    """
    Admin action: Create new Doctor and associated User login account with full schedule.
    """
    if request.user.role != 'ADMIN' and not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Admin privilege required.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    name = data.get('name', '').strip()
    hospital_id = data.get('hospital_id')
    department = data.get('department', 'General Medicine').strip()
    specialization = data.get('specialization', department).strip()
    qualification = data.get('qualification', 'MBBS, MD').strip()
    designation = data.get('designation', 'Senior Medical Officer').strip()
    experience_years = int(data.get('experience_years', 10))
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip()
    consultation_room = data.get('consultation_room', 'Room 203').strip()
    opd_start_time = data.get('opd_start_time', '09:00 AM').strip()
    opd_end_time = data.get('opd_end_time', '01:00 PM').strip()
    appointment_duration = int(data.get('appointment_duration', 15))
    max_slots = int(data.get('max_daily_slots', 35))
    available_days = data.get('available_days', 'Mon, Tue, Wed, Thu, Fri, Sat').strip()
    doctor_reg_id = data.get('doctor_reg_id', '').strip()
    account_password = data.get('password', 'docpass123').strip()
    status = data.get('status', 'ACTIVE').strip()

    if not name or not hospital_id:
        return JsonResponse({'success': False, 'message': 'Doctor Full Name and Hospital are required.'})

    hospital = get_object_or_404(HospitalFacility, id=int(hospital_id))

    # Auto generate Phone if not provided
    if not phone:
        import random
        phone = f"98{random.randint(10000000, 99999999)}"

    # Auto generate Doctor ID if empty
    if not doctor_reg_id:
        import random
        hosp_code = hospital.name[:4].upper().replace(' ', '')
        doctor_reg_id = f"DOC-{hosp_code}-{random.randint(1000, 9999)}"

    if DoctorProfile.objects.filter(doctor_reg_id=doctor_reg_id).exists():
        import random
        doctor_reg_id = f"{doctor_reg_id}-{random.randint(10, 99)}"

    # Create User account for Doctor
    user_account = None
    if not User.objects.filter(phone=phone).exists():
        user_account = User.objects.create_user(
            phone=phone,
            password=account_password,
            role='DOCTOR',
            full_name=name,
            city=hospital.area.city if hospital.area else 'New Delhi',
            state=hospital.area.state if hospital.area else 'Delhi'
        )
    else:
        user_account = User.objects.filter(phone=phone).first()
        user_account.role = 'DOCTOR'
        user_account.full_name = name
        user_account.save()

    doctor = DoctorProfile.objects.create(
        hospital=hospital,
        user=user_account,
        doctor_reg_id=doctor_reg_id,
        name=name,
        phone=phone,
        email=email,
        qualification=qualification,
        specialization=specialization,
        department=department,
        designation=designation,
        experience_years=experience_years,
        consultation_room=consultation_room,
        opd_start_time=opd_start_time,
        opd_end_time=opd_end_time,
        appointment_duration=appointment_duration,
        max_daily_slots=max_slots,
        available_days=available_days,
        status=status,
        is_present_today=True,
        is_active=(status == 'ACTIVE')
    )

    record_audit_log(request, request.user, 'ADMIN', 'ADD_DOCTOR', 'DoctorProfile', str(doctor.id), 'SUCCESS', f'Admin added doctor {doctor.name} ({doctor.doctor_reg_id}) to {hospital.name}')

    return JsonResponse({
        'success': True,
        'message': f'Doctor {doctor.name} ({doctor.doctor_reg_id}) added successfully. Login Phone: {phone}',
        'doctor': {
            'id': doctor.id,
            'doctor_reg_id': doctor.doctor_reg_id,
            'name': doctor.name,
            'department': doctor.department,
            'hospital_name': doctor.hospital.name,
            'qualification': doctor.qualification,
            'designation': doctor.designation,
            'consultation_room': doctor.consultation_room,
            'opd_schedule': f"{doctor.opd_start_time} - {doctor.opd_end_time}",
            'status': doctor.status,
            'is_present_today': doctor.is_present_today,
            'phone': doctor.phone
        }
    })


@login_required
@csrf_exempt
def api_update_doctor(request, doctor_id):
    """
    Admin action: Update existing Doctor details, room, schedule, and status.
    """
    if request.user.role != 'ADMIN' and not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Admin privilege required.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    doctor = get_object_or_404(DoctorProfile, id=doctor_id)

    if 'name' in data and data['name'].strip():
        doctor.name = data['name'].strip()
    if 'qualification' in data:
        doctor.qualification = data['qualification'].strip()
    if 'specialization' in data:
        doctor.specialization = data['specialization'].strip()
    if 'department' in data and data['department'].strip():
        doctor.department = data['department'].strip()
    if 'hospital_id' in data and data['hospital_id']:
        doctor.hospital = get_object_or_404(HospitalFacility, id=int(data['hospital_id']))
    if 'consultation_room' in data:
        doctor.consultation_room = data['consultation_room'].strip()
    if 'opd_start_time' in data:
        doctor.opd_start_time = data['opd_start_time'].strip()
    if 'opd_end_time' in data:
        doctor.opd_end_time = data['opd_end_time'].strip()
    if 'appointment_duration' in data:
        doctor.appointment_duration = int(data['appointment_duration'])
    if 'available_days' in data:
        doctor.available_days = data['available_days'].strip()
    if 'status' in data:
        doctor.status = data['status'].strip()
        doctor.is_active = (doctor.status == 'ACTIVE')

    doctor.save()

    record_audit_log(request, request.user, 'ADMIN', 'UPDATE_DOCTOR', 'DoctorProfile', str(doctor.id), 'SUCCESS', f'Admin updated details for doctor {doctor.name} ({doctor.doctor_reg_id})')

    return JsonResponse({
        'success': True,
        'message': f'Doctor {doctor.name} updated successfully.',
        'doctor': {
            'id': doctor.id,
            'name': doctor.name,
            'status': doctor.status,
            'department': doctor.department,
            'hospital_name': doctor.hospital.name,
            'consultation_room': doctor.consultation_room,
            'opd_schedule': f"{doctor.opd_start_time} - {doctor.opd_end_time}"
        }
    })


@login_required
@csrf_exempt
def api_set_doctor_status(request, doctor_id):
    """
    Admin action: Update doctor status (ACTIVE, INACTIVE, ON_LEAVE, SUSPENDED).
    """
    if request.user.role != 'ADMIN' and not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Admin privilege required.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    status = data.get('status', 'INACTIVE').strip()
    doctor = get_object_or_404(DoctorProfile, id=doctor_id)
    doctor.status = status
    doctor.is_active = (status == 'ACTIVE')
    doctor.save()

    action_name = 'ENABLE_DOCTOR' if status == 'ACTIVE' else 'DISABLE_DOCTOR'
    record_audit_log(request, request.user, 'ADMIN', action_name, 'DoctorProfile', str(doctor.id), 'SUCCESS', f'Doctor status changed to {status}')

    return JsonResponse({
        'success': True,
        'status': doctor.status,
        'is_active': doctor.is_active,
        'message': f'Doctor {doctor.name} status updated to {doctor.get_status_display() if hasattr(doctor, "get_status_display") else doctor.status}.'
    })


@login_required
@csrf_exempt
def api_remove_doctor(request, doctor_id):
    """
    Admin action: Deactivate / soft remove doctor.
    """
    if request.user.role != 'ADMIN' and not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Admin privilege required.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    doctor = get_object_or_404(DoctorProfile, id=doctor_id)
    doc_name = doctor.name
    doc_id = doctor.doctor_reg_id or f"DOC-{doctor.id}"
    
    doctor.status = 'INACTIVE'
    doctor.is_active = False
    doctor.save()

    record_audit_log(request, request.user, 'ADMIN', 'DISABLE_DOCTOR', 'DoctorProfile', str(doctor.id), 'SUCCESS', f'Admin disabled doctor {doc_name} [{doc_id}]')

    return JsonResponse({
        'success': True,
        'message': f'Doctor {doc_name} [{doc_id}] has been deactivated and will no longer accept new bookings.'
    })


@login_required
@csrf_exempt
def api_toggle_doctor_presence(request, doctor_id):
    """
    Admin action: Toggle Doctor presence on duty today.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    doctor = get_object_or_404(DoctorProfile, id=doctor_id)
    doctor.is_present_today = not doctor.is_present_today
    doctor.save()

    status_str = "Present on Duty in Hospital" if doctor.is_present_today else "Marked Absent / On Leave"
    return JsonResponse({
        'success': True,
        'is_present_today': doctor.is_present_today,
        'message': f'Status of {doctor.name} updated: {status_str}.'
    })


@login_required
def api_admin_audit_logs(request):
    """
    Admin API: Search and filter immutable audit logs (Search, Role, Action, Date).
    """
    if request.user.role != 'ADMIN' and not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Admin privilege required.'}, status=403)

    q_search = request.GET.get('search', '').strip()
    q_role = request.GET.get('role', '').strip()
    q_action = request.GET.get('action', '').strip()
    q_date = request.GET.get('date', '').strip()

    logs = AuditLog.objects.all()

    if q_search:
        logs = logs.filter(
            Q(user_display__icontains=q_search) |
            Q(resource_type__icontains=q_search) |
            Q(resource_id__icontains=q_search) |
            Q(details__icontains=q_search)
        )
    if q_role:
        logs = logs.filter(role=q_role)
    if q_action:
        logs = logs.filter(action=q_action)
    if q_date:
        logs = logs.filter(timestamp__date=q_date)

    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    data = []
    for item in page_obj:
        data.append({
            'id': item.id,
            'user': item.user_display or (item.user.get_display_name() if item.user else 'System'),
            'role': item.role,
            'action': item.action_display or item.get_action_display(),
            'resource': f"{item.resource_type} #{item.resource_id}" if item.resource_id else item.resource_type,
            'status': item.status,
            'ip_address': item.ip_address,
            'timestamp': item.timestamp.strftime('%d-%b-%Y %I:%M %p'),
            'details': item.details
        })

    return JsonResponse({
        'success': True,
        'logs': data,
        'total_count': paginator.count,
        'num_pages': paginator.num_pages,
        'current_page': page_obj.number
    })


@login_required
@csrf_exempt
def api_admin_health_advisories(request):
    """
    Admin API: CRUD for Public Health Advisories.
    """
    if request.user.role != 'ADMIN' and not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'success': False, 'message': 'Admin privilege required.'}, status=403)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except Exception:
            data = request.POST

        advisory_id = data.get('id')
        title = data.get('title', '').strip()
        category = data.get('category', data.get('severity', 'Seasonal Health')).strip()
        description = data.get('description', data.get('message', '')).strip()
        precaution_points = data.get('precaution_points', data.get('action_advice', '')).strip()
        priority = data.get('priority', data.get('severity', 'NORMAL')).strip().upper()
        status = data.get('status', 'ACTIVE').strip()

        if not title or not description:
            return JsonResponse({'status': 'error', 'success': False, 'message': 'Title and Description are required.'})

        if advisory_id:
            advisory = get_object_or_404(HealthAdvisory, id=advisory_id)
            advisory.title = title
            advisory.category = category
            advisory.description = description
            advisory.precaution_points = precaution_points
            advisory.priority = priority if priority in ['NORMAL', 'HIGH', 'URGENT'] else 'NORMAL'
            advisory.status = status
            advisory.save()
            record_audit_log(request, request.user, 'ADMIN', 'CREATE_ADVISORY', 'HealthAdvisory', str(advisory.id), 'SUCCESS', f'Updated advisory {advisory.title}')
            msg = "Advisory updated successfully."
        else:
            advisory = HealthAdvisory.objects.create(
                title=title,
                category=category,
                description=description,
                precaution_points=precaution_points,
                priority=priority if priority in ['NORMAL', 'HIGH', 'URGENT'] else 'NORMAL',
                status=status,
                created_by=request.user
            )
            record_audit_log(request, request.user, 'ADMIN', 'CREATE_ADVISORY', 'HealthAdvisory', str(advisory.id), 'SUCCESS', f'Created advisory {advisory.title}')
            msg = "Advisory published successfully."

        return JsonResponse({'status': 'success', 'success': True, 'message': msg, 'advisory_id': advisory.id})

    # GET: return list
    advisories = HealthAdvisory.objects.all()
    res = []
    for a in advisories:
        res.append({
            'id': a.id,
            'title': a.title,
            'category': a.category,
            'severity': a.priority,
            'description': a.description,
            'message': a.description,
            'precaution_points': a.precaution_points,
            'action_advice': a.precaution_points,
            'priority': a.priority,
            'status': a.status,
            'is_active': (a.status == 'ACTIVE'),
            'published_date': a.published_date.strftime('%d-%b-%Y')
        })
    return JsonResponse({'status': 'success', 'success': True, 'advisories': res})


@login_required
@csrf_exempt
def api_admin_toggle_advisory(request, advisory_id):
    if request.user.role != 'ADMIN' and not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'success': False, 'message': 'Admin privilege required.'}, status=403)
    advisory = get_object_or_404(HealthAdvisory, id=advisory_id)
    advisory.status = 'ARCHIVED' if advisory.status == 'ACTIVE' else 'ACTIVE'
    advisory.save()
    return JsonResponse({'status': 'success', 'success': True, 'is_active': (advisory.status == 'ACTIVE')})


@login_required
@csrf_exempt
def api_admin_health_schemes(request):
    """
    Admin API: CRUD for Government Health Schemes.
    """
    if request.user.role != 'ADMIN' and not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'success': False, 'message': 'Admin privilege required.'}, status=403)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except Exception:
            data = request.POST

        scheme_id = data.get('id')
        name = data.get('name', '').strip()
        code = data.get('code', 'SCHEME').strip()
        description = data.get('description', '').strip()
        eligibility = data.get('eligibility', data.get('eligibility_criteria', '')).strip()
        benefits = data.get('benefits', '').strip()
        required_documents = data.get('required_documents', '').strip()
        official_portal_url = data.get('official_portal_url', data.get('portal_url', 'https://nha.gov.in')).strip()
        nodal_agency = data.get('nodal_agency', 'Ministry of Health & Family Welfare').strip()
        is_active = data.get('is_active', True)

        if not name or not description:
            return JsonResponse({'status': 'error', 'success': False, 'message': 'Scheme Name and Description are required.'})

        if scheme_id:
            scheme = get_object_or_404(HealthScheme, id=scheme_id)
            scheme.name = name
            scheme.code = code
            scheme.subtitle = nodal_agency
            scheme.description = description
            scheme.eligibility = eligibility
            scheme.benefits = benefits
            scheme.required_documents = required_documents
            scheme.official_portal_url = official_portal_url
            scheme.is_active = is_active
            scheme.save()
            record_audit_log(request, request.user, 'ADMIN', 'UPDATE_SCHEME', 'HealthScheme', str(scheme.id), 'SUCCESS', f'Updated scheme {scheme.name}')
            msg = "Scheme updated successfully."
        else:
            if not code:
                import random
                code = f"SCHEME-{random.randint(100, 999)}"
            scheme = HealthScheme.objects.create(
                name=name,
                code=code,
                subtitle=nodal_agency,
                description=description,
                eligibility=eligibility,
                benefits=benefits,
                required_documents=required_documents,
                official_portal_url=official_portal_url,
                is_active=is_active
            )
            record_audit_log(request, request.user, 'ADMIN', 'UPDATE_SCHEME', 'HealthScheme', str(scheme.id), 'SUCCESS', f'Created scheme {scheme.name}')
            msg = "Scheme created successfully."

        return JsonResponse({'status': 'success', 'success': True, 'message': msg, 'scheme_id': scheme.id})

    # GET
    schemes = HealthScheme.objects.all()
    res = []
    for s in schemes:
        res.append({
            'id': s.id,
            'name': s.name,
            'code': s.code,
            'nodal_agency': s.subtitle or 'National Health Authority',
            'description': s.description,
            'eligibility': s.eligibility,
            'eligibility_criteria': s.eligibility,
            'benefits': s.benefits,
            'required_documents': s.required_documents,
            'official_portal_url': s.official_portal_url,
            'portal_url': s.official_portal_url,
            'is_active': s.is_active
        })
    return JsonResponse({'status': 'success', 'success': True, 'schemes': res})


@login_required
@csrf_exempt
def api_admin_toggle_scheme(request, scheme_id):
    if request.user.role != 'ADMIN' and not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'success': False, 'message': 'Admin privilege required.'}, status=403)
    scheme = get_object_or_404(HealthScheme, id=scheme_id)
    scheme.is_active = not scheme.is_active
    scheme.save()
    return JsonResponse({'status': 'success', 'success': True, 'is_active': scheme.is_active})


@login_required
def api_admin_stats(request):
    """
    Returns live statistics for Admin charts & doctor attendance.
    """
    today = timezone.now().date()
    all_doctors = DoctorProfile.objects.all()

    dept_stats = []
    for code, label in DoctorProfile.DEPARTMENT_CHOICES:
        doc_count = DoctorProfile.objects.filter(department=code).count()
        total_apts = AppointmentBooking.objects.filter(doctor__department=code).count()
        today_apts = AppointmentBooking.objects.filter(doctor__department=code, appointment_date=today).count()
        today_completed = AppointmentBooking.objects.filter(doctor__department=code, appointment_date=today, status='COMPLETED').count()

        if doc_count > 0 or total_apts > 0:
            dept_stats.append({
                'department': code,
                'label': label,
                'doctor_count': doc_count,
                'total_appointments': total_apts,
                'today_appointments': today_apts,
                'today_completed': today_completed
            })

    dept_stats.sort(key=lambda x: x['total_appointments'], reverse=True)

    return JsonResponse({
        'success': True,
        'total_doctors': all_doctors.count(),
        'active_doctors': all_doctors.filter(status='ACTIVE').count(),
        'present_doctors': all_doctors.filter(is_present_today=True).count(),
        'absent_doctors': all_doctors.filter(is_present_today=False).count(),
        'total_appointments_all_time': AppointmentBooking.objects.count(),
        'today_appointments': AppointmentBooking.objects.filter(appointment_date=today).count(),
        'today_completed': AppointmentBooking.objects.filter(appointment_date=today, status='COMPLETED').count(),
        'pending_lab_orders': LabOrder.objects.exclude(status__in=['COMPLETED', 'CANCELLED']).count(),
        'departments': dept_stats
    })


@csrf_exempt
@login_required
def api_admin_add_hospital(request):
    """API to register a new Hospital Facility and assign a Hospital Admin."""
    if request.user.role != 'ADMIN' and not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Government Admin privilege required.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required.'}, status=405)

    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        facility_type = data.get('facility_type', 'Central Govt').strip()
        address = data.get('address', '').strip()
        city = data.get('city', 'New Delhi').strip()
        district = data.get('district', 'New Delhi').strip()
        state = data.get('state', 'Delhi').strip()
        pincode = data.get('pincode', '110001').strip()
        contact_phone = data.get('phone', '+91 11 26588500').strip()
        email = data.get('email', 'admin@hospital.gov.in').strip()
        license_number = data.get('license_number', 'MOHFW-2026-HOSP').strip()
        admin_phone = data.get('admin_phone', '').strip()
        admin_name = data.get('admin_name', '').strip()

        if not name or not city:
            return JsonResponse({'status': 'error', 'message': 'Hospital Name and City are required.'}, status=400)

        hospital = HospitalFacility.objects.create(
            name=name,
            facility_type=facility_type,
            address=address,
            city=city,
            district=district,
            state=state,
            pincode=pincode,
            contact_phone=contact_phone,
            email=email,
            license_number=license_number,
            status='ACTIVE'
        )

        # Create Hospital Resource default
        from appointments.models import HospitalResource, HospitalAdmin
        HospitalResource.objects.create(hospital=hospital)

        # Assign Hospital Admin User if provided
        if admin_phone:
            admin_user, _ = User.objects.get_or_create(
                phone=admin_phone,
                defaults={
                    'role': 'HOSPITAL',
                    'full_name': admin_name or f"Admin ({name})",
                    'email': email
                }
            )
            admin_user.role = 'HOSPITAL'
            admin_user.set_password('hospital123')
            admin_user.save()
            HospitalAdmin.objects.create(user=admin_user, hospital=hospital, designation='Hospital Administrator')

        AuditLog.objects.create(
            user=request.user, user_display=request.user.get_display_name(), role='ADMIN',
            action='ADD_HOSPITAL', resource_type='HospitalFacility', resource_id=str(hospital.id),
            details=f"Registered new hospital {hospital.name} ({city}, {state})."
        )

        return JsonResponse({'status': 'success', 'message': f"Hospital {hospital.name} registered successfully.", 'hospital_id': hospital.id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@login_required
def api_admin_update_hospital(request, hospital_id):
    """API to edit hospital details or status (Active, Pending Verification, Suspended, Inactive)."""
    if request.user.role != 'ADMIN' and not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Government Admin privilege required.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required.'}, status=405)

    hospital = get_object_or_404(HospitalFacility, id=hospital_id)
    try:
        data = json.loads(request.body)
        hospital.name = data.get('name', hospital.name)
        hospital.facility_type = data.get('facility_type', hospital.facility_type)
        hospital.address = data.get('address', hospital.address)
        hospital.city = data.get('city', hospital.city)
        hospital.district = data.get('district', hospital.district)
        hospital.state = data.get('state', hospital.state)
        hospital.pincode = data.get('pincode', hospital.pincode)
        hospital.contact_phone = data.get('phone', hospital.contact_phone)
        hospital.email = data.get('email', hospital.email)
        hospital.status = data.get('status', hospital.status)
        hospital.save()

        AuditLog.objects.create(
            user=request.user, user_display=request.user.get_display_name(), role='ADMIN',
            action='UPDATE_HOSPITAL', resource_type='HospitalFacility', resource_id=str(hospital.id),
            details=f"Updated hospital {hospital.name} status to {hospital.status}."
        )

        return JsonResponse({'status': 'success', 'message': f"Hospital {hospital.name} updated successfully."})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@login_required
def api_admin_verify_doctor(request):
    """API to verify or reject a doctor's credentials."""
    if request.user.role != 'ADMIN' and not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Government Admin privilege required.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required.'}, status=405)

    try:
        data = json.loads(request.body)
        doctor_id = data.get('doctor_id')
        action = data.get('action') # VERIFIED or REJECTED

        doctor = get_object_or_404(DoctorProfile, id=doctor_id)
        if action == 'VERIFIED':
            doctor.verification_status = 'VERIFIED'
            doctor.status = 'ACTIVE'
            doctor.is_active = True
            log_action = 'VERIFY_DOCTOR'
            msg = f"Verified credentials for Dr. {doctor.name} ({doctor.hospital.name})."
        else:
            doctor.verification_status = 'REJECTED'
            doctor.status = 'INACTIVE'
            doctor.is_active = False
            log_action = 'REJECT_DOCTOR'
            msg = f"Rejected credentials for Dr. {doctor.name}."

        doctor.save()

        AuditLog.objects.create(
            user=request.user, user_display=request.user.get_display_name(), role='ADMIN',
            action=log_action, resource_type='DoctorProfile', resource_id=str(doctor.id),
            details=msg
        )

        return JsonResponse({'status': 'success', 'message': msg, 'verification_status': doctor.verification_status})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def api_admin_multi_hospital_analytics(request):
    """API for Government Admin multi-hospital analytics and cross-filtering."""
    if request.user.role != 'ADMIN' and not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Government Admin privilege required.'}, status=403)

    hospital_ids = request.GET.getlist('hospital_id')
    state = request.GET.get('state', '')
    district = request.GET.get('district', '')
    specialty = request.GET.get('specialty', '')
    date_filter = request.GET.get('date_filter', 'all')
    status_filter = request.GET.get('status', 'ALL')

    apts_query = AppointmentBooking.objects.select_related('hospital', 'doctor')

    if hospital_ids and 'ALL' not in hospital_ids:
        apts_query = apts_query.filter(hospital_id__in=hospital_ids)

    if state:
        apts_query = apts_query.filter(hospital__state__icontains=state)
    if district:
        apts_query = apts_query.filter(hospital__district__icontains=district)
    if specialty:
        apts_query = apts_query.filter(doctor__department=specialty)

    today = timezone.now().date()
    if date_filter == 'today':
        apts_query = apts_query.filter(appointment_date=today)
    elif date_filter == 'this_week':
        start_w = today - datetime.timedelta(days=today.weekday())
        apts_query = apts_query.filter(appointment_date__gte=start_w)
    elif date_filter == 'this_month':
        apts_query = apts_query.filter(appointment_date__gte=today.replace(day=1))

    if status_filter != 'ALL':
        apts_query = apts_query.filter(status=status_filter)

    total_count = apts_query.count()
    completed_count = apts_query.filter(status='COMPLETED').count()
    pending_count = apts_query.filter(status__in=['BOOKED', 'CONFIRMED', 'CHECKED_IN', 'WAITING', 'IN_CONSULTATION']).count()
    cancelled_count = apts_query.filter(status='CANCELLED').count()
    noshow_count = apts_query.filter(status='NO_SHOW').count()
    emergency_count = apts_query.filter(is_emergency=True).count()

    # Hospital breakdown
    hosp_breakdown = list(apts_query.values('hospital__id', 'hospital__name')
                          .annotate(total=Count('id'),
                                    pending=Count('id', filter=Q(status__in=['BOOKED', 'CONFIRMED', 'CHECKED_IN', 'WAITING', 'IN_CONSULTATION'])),
                                    completed=Count('id', filter=Q(status='COMPLETED')))
                          .order_by('-total')[:10])

    # Specialty breakdown
    spec_breakdown = list(apts_query.values('doctor__department')
                          .annotate(total=Count('id'))
                          .order_by('-total')[:10])

    return JsonResponse({
        'status': 'success',
        'metrics': {
            'total': total_count,
            'completed': completed_count,
            'pending': pending_count,
            'cancelled': cancelled_count,
            'noshow': noshow_count,
            'emergency': emergency_count,
            'completion_rate': round((completed_count / max(1, total_count)) * 100, 1),
            'cancellation_rate': round((cancelled_count / max(1, total_count)) * 100, 1)
        },
        'hospital_breakdown': hosp_breakdown,
        'specialty_breakdown': spec_breakdown
    })


