from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Avg, Count, Q, F
from core.models import User, AuditLog
from appointments.models import HospitalFacility, DoctorProfile, AppointmentBooking, HospitalResource
from patients.models import (
    EmergencyRequest, Ambulance, PatientFeedback, TargetedBroadcast, DiseaseRecord
)
import json
import datetime

# ==================== 1. EMERGENCY & SOS APIS ====================

@csrf_exempt
@login_required
def api_patient_sos_create(request):
    """Patient SOS button endpoint."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required.'}, status=405)

    try:
        data = json.loads(request.body)
        emergency_type = data.get('emergency_type', 'Accident / Injury')
        latitude = float(data.get('latitude', 28.5672))
        longitude = float(data.get('longitude', 77.2100))
        address = data.get('location_address', 'Near Patient Location, New Delhi')
        notes = data.get('notes', 'Urgent medical assistance required.')
        contact_phone = data.get('contact_phone', request.user.phone)
        hospital_id = data.get('hospital_id')

        hospital = None
        if hospital_id:
            hospital = HospitalFacility.objects.filter(id=hospital_id).first()
        if not hospital:
            hospital = HospitalFacility.objects.filter(status='ACTIVE').first()

        priority = 'CRITICAL'
        if emergency_type in ['Chest pain', 'Breathing difficulty', 'Unconsciousness', 'Stroke symptoms']:
            priority = 'CRITICAL'
        elif emergency_type in ['Severe bleeding', 'Pregnancy emergency']:
            priority = 'HIGH'
        else:
            priority = 'MEDIUM'

        sos = EmergencyRequest.objects.create(
            patient=request.user,
            emergency_type=emergency_type,
            priority=priority,
            latitude=latitude,
            longitude=longitude,
            location_address=address,
            patient_notes=notes,
            contact_phone=contact_phone,
            hospital=hospital,
            status='RECEIVED'
        )

        AuditLog.objects.create(
            user=request.user, user_display=request.user.get_display_name(), role='PATIENT',
            action='UPDATE_EMERGENCY_INFO', resource_type='EmergencyRequest', resource_id=str(sos.id),
            details=f"Triggered SOS Alert [{emergency_type}] (Priority: {priority})."
        )

        return JsonResponse({
            'status': 'success',
            'message': 'Emergency SOS dispatched to nearest hospital & helpline 108.',
            'request_id': sos.id,
            'hospital_name': hospital.name if hospital else 'Central Emergency Cell',
            'emergency_type': sos.emergency_type,
            'priority': sos.priority,
            'current_status': sos.status
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def api_patient_sos_status(request, request_id):
    """Patient live tracking endpoint for SOS request."""
    sos = get_object_or_404(EmergencyRequest, id=request_id, patient=request.user)
    return JsonResponse({
        'status': 'success',
        'sos': {
            'id': sos.id,
            'status': sos.status,
            'emergency_type': sos.emergency_type,
            'status_display': sos.get_status_display(),
            'hospital': sos.hospital.name if sos.hospital else 'General Emergency Desk',
            'ambulance_vehicle': sos.ambulance.vehicle_number if sos.ambulance else 'Assigning Ambulance...',
            'driver_name': sos.driver_name or (sos.ambulance.driver_name if sos.ambulance else 'Dispatch Desk'),
            'driver_phone': sos.driver_phone or (sos.ambulance.driver_phone if sos.ambulance else '108 / 102'),
            'eta_minutes': 12 if sos.status == 'DISPATCHED' else (8 if sos.status == 'EN_ROUTE' else None),
            'updated_at': sos.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }
    })


@csrf_exempt
@login_required
def api_hospital_emergency_action(request, request_id):
    """Hospital Admin emergency management endpoint."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required.'}, status=405)

    sos = get_object_or_404(EmergencyRequest, id=request_id)
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        ambulance_id = data.get('ambulance_id')
        driver_name = data.get('driver_name', '')
        driver_phone = data.get('driver_phone', '')

        if new_status:
            sos.status = new_status
            if new_status == 'COMPLETED':
                sos.completed_at = timezone.now()

        if ambulance_id:
            amb = Ambulance.objects.filter(id=ambulance_id).first()
            if amb:
                sos.ambulance = amb
                sos.driver_name = driver_name or amb.driver_name
                sos.driver_phone = driver_phone or amb.driver_phone
                amb.status = 'ON_DUTY'
                amb.save()

        sos.save()

        AuditLog.objects.create(
            user=request.user, user_display=request.user.get_display_name(), role='HOSPITAL',
            action='UPDATE_EMERGENCY_INFO', resource_type='EmergencyRequest', resource_id=str(sos.id),
            details=f"Updated SOS #{sos.id} status to {sos.status}."
        )

        return JsonResponse({
            'status': 'success',
            'message': f"Emergency request updated to {sos.get_status_display()}.",
            'current_status': sos.status
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@login_required
def api_hospital_ambulance_manage(request):
    """CRUD for hospital ambulances."""
    if request.method == 'GET':
        hospital_id = request.GET.get('hospital_id')
        ambulances = Ambulance.objects.all()
        if hospital_id:
            ambulances = ambulances.filter(hospital_id=hospital_id)
        data = [{
            'id': a.id,
            'vehicle_number': a.vehicle_number,
            'driver_name': a.driver_name,
            'driver_phone': a.driver_phone,
            'status': a.status,
            'hospital_name': a.hospital.name
        } for a in ambulances]
        return JsonResponse({'status': 'success', 'ambulances': data})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            vehicle_number = data.get('vehicle_number')
            driver_name = data.get('driver_name', 'Rajesh Kumar')
            driver_phone = data.get('driver_phone', '+91 9810810800')
            hospital_id = data.get('hospital_id')

            hospital = HospitalFacility.objects.filter(id=hospital_id).first() or HospitalFacility.objects.first()

            amb = Ambulance.objects.create(
                hospital=hospital,
                vehicle_number=vehicle_number,
                driver_name=driver_name,
                driver_phone=driver_phone,
                status='AVAILABLE'
            )

            return JsonResponse({'status': 'success', 'message': f"Ambulance {amb.vehicle_number} added.", 'ambulance_id': amb.id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@login_required
def api_patient_sos_cancel(request, request_id):
    """Patient cancels an active SOS request."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required.'}, status=405)
    sos = get_object_or_404(EmergencyRequest, id=request_id, patient=request.user)
    if sos.status in ('RESOLVED', 'CANCELLED', 'COMPLETED'):
        return JsonResponse({'status': 'error', 'message': 'Cannot cancel a completed/resolved SOS.'}, status=400)
    sos.status = 'CANCELLED'
    sos.save()
    return JsonResponse({'status': 'success', 'message': 'SOS request cancelled.'})


@login_required
def api_patient_completed_appointments(request):
    """Returns completed appointments for the patient to rate."""
    from appointments.models import AppointmentBooking
    apts = AppointmentBooking.objects.filter(
        patient=request.user, status='COMPLETED'
    ).select_related('hospital', 'doctor').order_by('-date')[:10]

    rated_ids = set(
        PatientFeedback.objects.filter(patient=request.user)
        .values_list('appointment_id', flat=True)
    )

    data = []
    for a in apts:
        fb = PatientFeedback.objects.filter(appointment=a, patient=request.user).first()
        data.append({
            'id': a.id,
            'doctor': a.doctor.user.get_display_name() if a.doctor else a.doctor_name,
            'department': a.department,
            'date': a.date.strftime('%d %b %Y') if a.date else '—',
            'hospital': a.hospital.name if a.hospital else '—',
            'already_rated': a.id in rated_ids,
            'rating': fb.overall_rating if fb else None
        })

    return JsonResponse({'status': 'success', 'appointments': data})


# ==================== 2. PATIENT FEEDBACK & COMPLAINTS APIS ====================

@csrf_exempt
@login_required
def api_patient_feedback_create(request):
    """Patient submits feedback/complaint after consultation."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required.'}, status=405)

    try:
        data = json.loads(request.body)
        appointment_id = data.get('appointment_id')
        hospital_id = data.get('hospital_id')
        doc_rating = int(data.get('doctor_rating', 5))
        clean_rating = int(data.get('cleanliness_rating', 5))
        wait_rating = int(data.get('waiting_time_rating', 5))
        overall_rating = int(data.get('overall_rating', 5))
        written_feedback = data.get('written_feedback', '').strip()
        complaint_cat = data.get('complaint_category', 'None')

        hospital = None
        apt = None
        doctor = None
        if appointment_id:
            apt = AppointmentBooking.objects.filter(id=appointment_id).first()
            if apt:
                hospital = apt.hospital
                doctor = apt.doctor
        if not hospital and hospital_id:
            hospital = HospitalFacility.objects.filter(id=hospital_id).first()
        if not hospital:
            hospital = HospitalFacility.objects.first()

        fb = PatientFeedback.objects.create(
            patient=request.user,
            appointment=apt,
            hospital=hospital,
            doctor=doctor,
            doctor_rating=doc_rating,
            cleanliness_rating=clean_rating,
            waiting_time_rating=wait_rating,
            overall_rating=overall_rating,
            written_feedback=written_feedback,
            complaint_category=complaint_cat,
            status='SUBMITTED'
        )

        return JsonResponse({
            'status': 'success',
            'message': 'Thank you! Your feedback & rating have been submitted.',
            'feedback_id': fb.id
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@login_required
def api_hospital_feedback_action(request, feedback_id):
    """Hospital/Govt Admin responds to or resolves a feedback/complaint."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required.'}, status=405)

    fb = get_object_or_404(PatientFeedback, id=feedback_id)
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        notes = data.get('response_notes', '').strip()

        if new_status:
            fb.status = new_status
        if notes:
            fb.response_notes = notes
        fb.save()

        AuditLog.objects.create(
            user=request.user, user_display=request.user.get_display_name(), role=request.user.role,
            action='SYSTEM_SECURITY', resource_type='PatientFeedback', resource_id=str(fb.id),
            details=f"Updated complaint #{fb.id} status to {fb.status}."
        )

        return JsonResponse({'status': 'success', 'message': f"Complaint status updated to {fb.status}."})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ==================== 3. HOSPITAL PERFORMANCE SCORECARD API ====================

@login_required
def api_hospital_scorecard(request, hospital_id):
    """Calculates performance scorecard and badges for a hospital."""
    hosp = get_object_or_404(HospitalFacility, id=hospital_id)
    apts = AppointmentBooking.objects.filter(hospital=hosp)
    feedbacks = PatientFeedback.objects.filter(hospital=hosp)
    resource = HospitalResource.objects.filter(hospital=hosp).first()

    total_apts = apts.count()
    completed = apts.filter(status='COMPLETED').count()
    cancelled = apts.filter(status='CANCELLED').count()
    noshow = apts.filter(status='NO_SHOW').count()

    completion_rate = round((completed / max(1, total_apts)) * 100, 1)
    cancellation_rate = round((cancelled / max(1, total_apts)) * 100, 1)
    noshow_rate = round((noshow / max(1, total_apts)) * 100, 1)

    avg_satisfaction = feedbacks.aggregate(Avg('overall_rating'))['overall_rating__avg'] or 4.5
    avg_satisfaction = round(avg_satisfaction, 1)

    total_complaints = feedbacks.exclude(complaint_category='None').count()
    resolved_complaints = feedbacks.exclude(complaint_category='None').filter(status='RESOLVED').count()

    icu_pct = resource.icu_occupancy_pct() if resource else 70.0
    bed_pct = resource.total_occupancy_pct() if resource else 65.0

    # Badge Logic
    if avg_satisfaction >= 4.5 and completion_rate >= 85 and icu_pct < 85:
        badge = 'EXCELLENT'
        badge_color = '#10b981'
    elif avg_satisfaction >= 3.8 and completion_rate >= 75:
        badge = 'GOOD'
        badge_color = '#0284c7'
    elif avg_satisfaction >= 3.0:
        badge = 'AVERAGE'
        badge_color = '#f59e0b'
    elif avg_satisfaction >= 2.0:
        badge = 'NEEDS_IMPROVEMENT'
        badge_color = '#f97316'
    else:
        badge = 'CRITICAL'
        badge_color = '#ef4444'

    return JsonResponse({
        'status': 'success',
        'hospital_name': hosp.name,
        'badge': badge,
        'badge_color': badge_color,
        'metrics': {
            'total_appointments': total_apts,
            'completion_rate': completion_rate,
            'cancellation_rate': cancellation_rate,
            'noshow_rate': noshow_rate,
            'avg_satisfaction': avg_satisfaction,
            'total_complaints': total_complaints,
            'resolved_complaints': resolved_complaints,
            'icu_occupancy_pct': icu_pct,
            'total_bed_occupancy_pct': bed_pct,
            'avg_waiting_time_mins': 18
        }
    })


# ==================== 4. TARGETED BROADCASTS & DISEASE ANALYTICS APIS ====================

@csrf_exempt
@login_required
def api_admin_broadcast_create(request):
    """Admin endpoint to create targeted health broadcasts."""
    if request.user.role != 'ADMIN' and not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Admin required.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required.'}, status=405)

    try:
        data = json.loads(request.body)
        title = data.get('title', '').strip()
        message = data.get('message', '').strip()
        severity = data.get('severity', 'WARNING')
        target_type = data.get('target_type', 'ALL')
        target_value = data.get('target_value', 'All India')

        broadcast = TargetedBroadcast.objects.create(
            title=title,
            message=message,
            severity=severity,
            target_type=target_type,
            target_value=target_value,
            status='ACTIVE'
        )

        AuditLog.objects.create(
            user=request.user, user_display=request.user.get_display_name(), role='ADMIN',
            action='CREATE_ADVISORY', resource_type='TargetedBroadcast', resource_id=str(broadcast.id),
            details=f"Broadcasted alert [{title}] to {target_type}: {target_value}."
        )

        return JsonResponse({
            'status': 'success',
            'message': f"Broadcast '{title}' created and dispatched successfully.",
            'broadcast_id': broadcast.id
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def api_admin_disease_analytics(request):
    """Disease & case analytics dashboard endpoint."""
    today = timezone.now().date()
    disease_counts = list(DiseaseRecord.objects.values('disease_name')
                          .annotate(count=Count('id'))
                          .order_by('-count')[:10])

    district_counts = list(DiseaseRecord.objects.values('district')
                           .annotate(count=Count('id'))
                           .order_by('-count')[:10])

    # Spike alert logic (e.g. if Dengue or Respiratory cases > 10)
    spikes = []
    for item in disease_counts:
        if item['count'] >= 5:
            spikes.append({
                'disease': item['disease_name'],
                'case_count': item['count'],
                'alert_level': 'HIGH SPIKE ALERT'
            })

    return JsonResponse({
        'status': 'success',
        'top_diseases': disease_counts,
        'district_breakdown': district_counts,
        'spike_alerts': spikes
    })
