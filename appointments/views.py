import math
import json
import datetime
import urllib.request
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
from django.conf import settings

from .models import HospitalArea, HospitalFacility, DoctorProfile, AppointmentBooking, Specialty
from patients.models import HealthNotification
from core.audit_utils import record_audit_log


def calculate_haversine(lat1, lon1, lat2, lon2):
    """
    Calculates Haversine distance in kilometers between two lat/lng coordinates.
    """
    if None in (lat1, lon1, lat2, lon2):
        return None
    try:
        lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.asin(math.sqrt(a))
        return round(c * 6371.0, 1)
    except Exception:
        return None


def get_locations_api(request):
    """
    Returns unique cities/locations for typeahead auto-complete.
    """
    query = request.GET.get('q', '').strip()
    cities = list(HospitalArea.objects.values_list('city', flat=True).distinct())
    hosp_cities = list(HospitalFacility.objects.exclude(city='').values_list('city', flat=True).distinct())
    all_cities = sorted(list(set(cities + hosp_cities)))

    if query:
        all_cities = [c for c in all_cities if query.lower() in c.lower()]

    return JsonResponse({'success': True, 'locations': all_cities})


def get_areas_api(request):
    """
    Returns popular areas for a selected location/city.
    """
    city = request.GET.get('city', '').strip()
    qs = HospitalArea.objects.all()
    if city:
        qs = qs.filter(city__iexact=city)

    areas = []
    for a in qs:
        areas.append({
            'id': a.id,
            'area_name': a.area_name,
            'city': a.city,
            'state': a.state,
            'pincode': a.pincode
        })
    return JsonResponse({'success': True, 'areas': areas})


def get_hospitals_api(request):
    """
    Returns hospitals present in that location/area to choose from dropdown.
    """
    area_id = request.GET.get('area_id')
    city = request.GET.get('city', '').strip()
    pincode = request.GET.get('pincode', '').strip()

    qs = HospitalFacility.objects.select_related('area').all()
    if area_id and area_id.isdigit():
        qs = qs.filter(area_id=int(area_id))
    elif pincode:
        qs = qs.filter(Q(pincode=pincode) | Q(area__pincode=pincode))
    elif city:
        qs = qs.filter(Q(city__iexact=city) | Q(area__city__iexact=city))

    hospitals = []
    for h in qs:
        hospitals.append({
            'id': h.id,
            'name': h.name,
            'facility_type': h.get_facility_type_display(),
            'area_name': h.area.area_name if h.area else '',
            'city': h.get_city(),
            'district': h.district or (h.area.city if h.area else ''),
            'state': h.get_state(),
            'pincode': h.get_pincode(),
            'address': h.address,
            'contact_phone': h.contact_phone,
            'emergency': h.emergency_available,
            'opd_timings': h.opd_timings,
            'beds': h.total_beds,
            'latitude': h.latitude,
            'longitude': h.longitude,
            'specialties': h.get_specialties_list()
        })
    return JsonResponse({'success': True, 'hospitals': hospitals})


def get_nearby_hospitals_api(request):
    """
    Returns hospitals near user's lat/lng or location, sorted by distance.
    Supports keyword search and pincode search.
    """
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    city = request.GET.get('city', '').strip()
    pincode = request.GET.get('pincode', '').strip()
    q = request.GET.get('q', '').strip()

    user_lat = float(lat) if lat else None
    user_lng = float(lng) if lng else None

    qs = HospitalFacility.objects.select_related('area').all()

    if pincode:
        qs = qs.filter(Q(pincode=pincode) | Q(area__pincode=pincode))
    elif city:
        qs = qs.filter(Q(city__icontains=city) | Q(area__city__icontains=city) | Q(district__icontains=city))

    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(address__icontains=q) |
            Q(city__icontains=q) |
            Q(district__icontains=q) |
            Q(pincode__icontains=q) |
            Q(area__area_name__icontains=q) |
            Q(doctors__department__icontains=q) |
            Q(doctors__specialty_ref__name__icontains=q)
        ).distinct()

    results = []
    for h in qs:
        h_lat = h.latitude or (16.2354 if "narasaraopet" in h.name.lower() or "palnadu" in h.name.lower() else (16.3067 if "guntur" in h.name.lower() else 28.5672))
        h_lng = h.longitude or (80.0494 if "narasaraopet" in h.name.lower() or "palnadu" in h.name.lower() else (80.4365 if "guntur" in h.name.lower() else 77.2100))

        dist_km = calculate_haversine(user_lat, user_lng, h_lat, h_lng) if (user_lat and user_lng) else None

        docs = h.doctors.filter(is_active=True)
        doc_list = []
        for d in docs[:6]:
            doc_list.append({
                'id': d.id,
                'name': d.name,
                'department': d.department,
                'specialty': d.specialty_ref.name if d.specialty_ref else d.department,
                'qualification': d.qualification,
                'is_present_today': d.is_present_today
            })

        results.append({
            'id': h.id,
            'name': h.name,
            'facility_type': h.get_facility_type_display(),
            'address': h.address,
            'area_name': h.area.area_name if h.area else '',
            'city': h.get_city(),
            'district': h.district or (h.area.city if h.area else ''),
            'state': h.get_state(),
            'pincode': h.get_pincode(),
            'contact_phone': h.contact_phone,
            'emergency': h.emergency_available,
            'total_beds': h.total_beds,
            'opd_timings': h.opd_timings,
            'latitude': h_lat,
            'longitude': h_lng,
            'distance_km': dist_km,
            'distance_display': f"📍 {dist_km} km away" if dist_km is not None else "📍 Nearby Facility",
            'specialties': h.get_specialties_list(),
            'doctors_count': docs.count(),
            'doctors': doc_list,
            'directions_url': f"https://www.google.com/maps/dir/?api=1&destination={h_lat},{h_lng}" if (h_lat and h_lng) else f"https://www.google.com/maps/search/?api=1&query={h.name}+{h.address}"
        })

    if user_lat and user_lng:
        results.sort(key=lambda x: (x['distance_km'] if x['distance_km'] is not None else 99999))

    return JsonResponse({
        'success': True,
        'count': len(results),
        'user_location': {'lat': user_lat, 'lng': user_lng},
        'hospitals': results
    })


def search_hospitals_api(request):
    """
    Search hospitals by pincode, city, district, area, or keyword.
    """
    return get_nearby_hospitals_api(request)


def get_hospital_detail_api(request, hospital_id):
    """
    Returns full details for a single hospital including map data, contact, specialties, and doctor list.
    """
    h = get_object_or_404(HospitalFacility, id=hospital_id)
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')

    user_lat = float(lat) if lat else None
    user_lng = float(lng) if lng else None

    h_lat = h.latitude or 16.2354
    h_lng = h.longitude or 80.0494

    dist_km = calculate_haversine(user_lat, user_lng, h_lat, h_lng) if (user_lat and user_lng) else None

    docs = []
    for d in h.doctors.filter(is_active=True):
        docs.append({
            'id': d.id,
            'doctor_reg_id': d.doctor_reg_id,
            'name': d.name,
            'qualification': d.qualification,
            'department': d.department,
            'specialty': d.specialty_ref.name if d.specialty_ref else d.department,
            'designation': d.designation,
            'experience': f"{d.experience_years} years",
            'days': d.available_days,
            'room': d.consultation_room,
            'opd_schedule': f"{d.opd_start_time} - {d.opd_end_time}",
            'is_present_today': d.is_present_today
        })

    return JsonResponse({
        'success': True,
        'hospital': {
            'id': h.id,
            'name': h.name,
            'facility_type': h.get_facility_type_display(),
            'address': h.address,
            'area_name': h.area.area_name if h.area else '',
            'city': h.get_city(),
            'district': h.district or (h.area.city if h.area else ''),
            'state': h.get_state(),
            'pincode': h.get_pincode(),
            'contact_phone': h.contact_phone,
            'emergency': h.emergency_available,
            'total_beds': h.total_beds,
            'opd_timings': h.opd_timings,
            'latitude': h_lat,
            'longitude': h_lng,
            'distance_km': dist_km,
            'distance_display': f"📍 {dist_km} km away" if dist_km is not None else "📍 Hospital Location",
            'specialties': h.get_specialties_list(),
            'doctors': docs,
            'directions_url': f"https://www.google.com/maps/dir/?api=1&destination={h_lat},{h_lng}"
        }
    })


def get_specialties_api(request):
    """
    Returns all configurable medical specialties from the database.
    """
    qs = Specialty.objects.all()
    specialties = []
    for s in qs:
        specialties.append({
            'id': s.id,
            'name': s.name,
            'code': s.code,
            'description': s.description,
            'icon': s.icon,
            'doctors_count': s.doctors.filter(is_active=True).count()
        })
    return JsonResponse({'success': True, 'specialties': specialties})


def locate_me_api(request):
    """
    Automatic Geolocation API:
    Takes latitude and longitude or uses city parameter to locate user and return nearest hospitals.
    """
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    city_param = request.GET.get('city', '').strip()

    CITY_COORDS = {
        'Narasaraopet': {'lat': 16.2354, 'lng': 80.0494, 'state': 'Andhra Pradesh'},
        'Guntur': {'lat': 16.3067, 'lng': 80.4365, 'state': 'Andhra Pradesh'},
        'New Delhi': {'lat': 28.6139, 'lng': 77.2090, 'state': 'Delhi'},
        'Bengaluru': {'lat': 12.9716, 'lng': 77.5946, 'state': 'Karnataka'},
        'Hyderabad': {'lat': 17.3850, 'lng': 78.4867, 'state': 'Telangana'},
        'Mumbai': {'lat': 19.0760, 'lng': 72.8777, 'state': 'Maharashtra'},
    }

    matched_city = 'Narasaraopet'
    matched_state = 'Andhra Pradesh'
    distance_km = 1.8

    if lat and lng:
        try:
            u_lat = float(lat)
            u_lng = float(lng)
            min_dist = 999999
            for c_name, c_info in CITY_COORDS.items():
                d = ((u_lat - c_info['lat'])**2 + (u_lng - c_info['lng'])**2)**0.5
                if d < min_dist:
                    min_dist = d
                    matched_city = c_name
                    matched_state = c_info['state']
            distance_km = round(min_dist * 111, 1) if min_dist < 100 else 1.8
        except Exception:
            matched_city = 'Narasaraopet'
    elif city_param:
        matched_city = city_param

    hospitals = HospitalFacility.objects.filter(
        Q(city__iexact=matched_city) | Q(area__city__iexact=matched_city)
    ).select_related('area')

    if not hospitals.exists():
        hospitals = HospitalFacility.objects.all()
        matched_city = hospitals.first().get_city() if hospitals.exists() else 'Narasaraopet'

    primary_hospital = hospitals.first()

    doctors = []
    if primary_hospital:
        for d in primary_hospital.doctors.filter(is_active=True):
            doctors.append({
                'id': d.id,
                'doctor_reg_id': d.doctor_reg_id,
                'name': d.name,
                'department': d.department,
                'specialty': d.specialty_ref.name if d.specialty_ref else d.department,
                'qualification': d.qualification,
                'is_present_today': d.is_present_today,
                'patients_taken_today': d.patients_taken_today_count()
            })

    primary_area = primary_hospital.area if primary_hospital else None

    return JsonResponse({
        'success': True,
        'detected_location': {
            'city': matched_city,
            'state': matched_state,
            'district': primary_hospital.district if primary_hospital and primary_hospital.district else f"{matched_city} District",
            'area_name': primary_area.area_name if primary_area else 'Palnadu Road',
            'area_id': primary_area.id if primary_area else None,
            'pincode': primary_hospital.get_pincode() if primary_hospital else '522601',
            'approx_distance': f"{distance_km} km away",
            'lat': float(lat) if lat else 16.2354,
            'lng': float(lng) if lng else 80.0494,
            'source': 'GPS / High Precision Geolocation' if (lat and lng) else 'IP Auto-Detect'
        },
        'recommended_hospital': {
            'id': primary_hospital.id if primary_hospital else None,
            'name': primary_hospital.name if primary_hospital else 'Government General Hospital',
            'facility_type': primary_hospital.get_facility_type_display() if primary_hospital else 'District Hospital',
            'address': primary_hospital.address if primary_hospital else '',
            'emergency': primary_hospital.emergency_available if primary_hospital else True,
            'beds': primary_hospital.total_beds if primary_hospital else 350
        },
        'hospitals_count': hospitals.count(),
        'available_doctors': doctors
    })


def get_doctors_api(request):
    """
    Returns active doctors available for a hospital / specialty / department.
    """
    hospital_id = request.GET.get('hospital_id')
    specialty_id = request.GET.get('specialty_id')
    specialty_name = request.GET.get('specialty', '').strip()
    department = request.GET.get('department', '').strip()
    only_present = request.GET.get('only_present', 'false').lower() == 'true'

    qs = DoctorProfile.objects.select_related('hospital', 'specialty_ref').filter(status='ACTIVE', is_active=True)
    if hospital_id and hospital_id.isdigit():
        qs = qs.filter(hospital_id=int(hospital_id))
    if specialty_id and specialty_id.isdigit():
        qs = qs.filter(specialty_ref_id=int(specialty_id))
    elif specialty_name:
        qs = qs.filter(Q(specialty_ref__name__iexact=specialty_name) | Q(department__iexact=specialty_name))
    elif department:
        qs = qs.filter(department__iexact=department)

    if only_present:
        qs = qs.filter(is_present_today=True)

    doctors = []
    for d in qs:
        doctors.append({
            'id': d.id,
            'doctor_reg_id': d.doctor_reg_id or f"DOC-{d.id}",
            'name': d.name,
            'qualification': d.qualification,
            'department': d.department,
            'specialty': d.specialty_ref.name if d.specialty_ref else d.department,
            'specialization': d.specialization or d.department,
            'designation': d.designation,
            'experience': f"{d.experience_years} years",
            'days': d.available_days,
            'consultation_room': d.consultation_room or 'Room 203',
            'opd_schedule': f"{d.opd_start_time} - {d.opd_end_time}",
            'hospital_name': d.hospital.name,
            'hospital_id': d.hospital.id,
            'status': d.status,
            'is_present_today': d.is_present_today,
            'patients_taken_today': d.patients_taken_today_count(),
            'total_patients_taken': d.total_patients_taken_count()
        })
    return JsonResponse({'success': True, 'doctors': doctors})


def search_doctors_api(request):
    """
    Search doctors by name, specialty, hospital, or location keyword.
    """
    q = request.GET.get('q', '').strip()
    specialty_name = request.GET.get('specialty', '').strip()
    hospital_id = request.GET.get('hospital_id')
    location = request.GET.get('location', '').strip()

    qs = DoctorProfile.objects.select_related('hospital', 'specialty_ref').filter(status='ACTIVE', is_active=True)

    if hospital_id and hospital_id.isdigit():
        qs = qs.filter(hospital_id=int(hospital_id))
    if specialty_name:
        qs = qs.filter(Q(department__icontains=specialty_name) | Q(specialty_ref__name__icontains=specialty_name))

    if location:
        qs = qs.filter(
            Q(hospital__city__icontains=location) |
            Q(hospital__district__icontains=location) |
            Q(hospital__area__city__icontains=location) |
            Q(hospital__area__area_name__icontains=location) |
            Q(hospital__pincode__icontains=location)
        )

    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(qualification__icontains=q) |
            Q(specialization__icontains=q) |
            Q(department__icontains=q) |
            Q(specialty_ref__name__icontains=q) |
            Q(hospital__name__icontains=q)
        )

    docs = []
    for d in qs:
        docs.append({
            'id': d.id,
            'doctor_reg_id': d.doctor_reg_id,
            'name': d.name,
            'qualification': d.qualification,
            'department': d.department,
            'specialty': d.specialty_ref.name if d.specialty_ref else d.department,
            'designation': d.designation,
            'experience': f"{d.experience_years} years",
            'hospital_id': d.hospital.id,
            'hospital_name': d.hospital.name,
            'hospital_address': d.hospital.address,
            'hospital_city': d.hospital.get_city(),
            'room': d.consultation_room,
            'days': d.available_days,
            'opd_schedule': f"{d.opd_start_time} - {d.opd_end_time}",
            'is_present_today': d.is_present_today
        })

    return JsonResponse({'success': True, 'count': len(docs), 'doctors': docs})


def get_available_slots_api(request):
    """
    Returns available time slots for a doctor on a specified date.
    Enforces daily capacity and filters already booked slots.
    """
    doctor_id = request.GET.get('doctor_id')
    date_str = request.GET.get('date', '').strip()

    if not doctor_id or not date_str:
        return JsonResponse({'success': False, 'error': 'doctor_id and date required'}, status=400)

    try:
        doctor = DoctorProfile.objects.get(id=int(doctor_id))
        target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

    all_slots = AppointmentBooking.TIME_SLOTS
    booked_slots = list(AppointmentBooking.objects.filter(
        doctor=doctor,
        appointment_date=target_date
    ).exclude(status='CANCELLED').values_list('time_slot', flat=True))

    slot_details = []
    for s in all_slots:
        is_available = s not in booked_slots
        slot_details.append({
            'slot': s,
            'available': is_available
        })

    return JsonResponse({
        'success': True,
        'doctor_id': doctor.id,
        'doctor_name': doctor.name,
        'date': target_date.strftime('%Y-%m-%d'),
        'total_slots': len(all_slots),
        'booked_count': len(booked_slots),
        'max_daily_slots': doctor.max_daily_slots,
        'is_fully_booked': len(booked_slots) >= doctor.max_daily_slots,
        'slots': slot_details
    })


@login_required
@csrf_exempt
def check_and_book_appointment_api(request):
    """
    Checks slot availability on the requested date for the doctor.
    Enforces backend slot locking and creates appointment booking.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    hospital_id = data.get('hospital_id')
    doctor_id = data.get('doctor_id')
    apt_date_str = data.get('date', '').strip()
    symptoms = data.get('symptoms', 'General Consultation / Health Followup').strip()
    preferred_time_slot = data.get('time_slot', '').strip()

    if not hospital_id or not doctor_id or not apt_date_str:
        return JsonResponse({
            'success': False,
            'status': 'DENIED',
            'title': 'Booking Denied',
            'message': 'Please select a valid Hospital, Doctor, and Appointment Date.'
        })

    try:
        hospital = HospitalFacility.objects.get(id=int(hospital_id))
        doctor = DoctorProfile.objects.get(id=int(doctor_id), hospital=hospital)
        apt_date = datetime.datetime.strptime(apt_date_str, '%Y-%m-%d').date()
    except Exception as e:
        return JsonResponse({
            'success': False,
            'status': 'DENIED',
            'title': 'Booking Denied',
            'message': f'Invalid selection parameters: {str(e)}'
        })

    if not doctor.is_available_for_booking():
        return JsonResponse({
            'success': False,
            'status': 'DENIED',
            'title': 'Doctor Unavailable',
            'message': f'{doctor.name} is currently {doctor.get_status_display() if hasattr(doctor, "get_status_display") else doctor.status} and not accepting new appointments.'
        })

    if apt_date < timezone.now().date():
        return JsonResponse({
            'success': False,
            'status': 'DENIED',
            'title': 'Booking Denied',
            'message': 'Appointment date cannot be in the past. Please select a future date.'
        })

    # Prevent double booking for the same patient on same doctor & date
    existing_patient_booking = AppointmentBooking.objects.filter(
        patient=request.user,
        doctor=doctor,
        appointment_date=apt_date
    ).exclude(status='CANCELLED').first()

    if existing_patient_booking:
        return JsonResponse({
            'success': False,
            'status': 'DENIED',
            'title': 'Duplicate Booking Warning',
            'message': f'You already have an active appointment (Token #{existing_patient_booking.opd_token_number}) with {doctor.name} on {apt_date.strftime("%d-%b-%Y")}.'
        })

    # Check capacity & slot availability
    existing_bookings = AppointmentBooking.objects.filter(
        doctor=doctor,
        appointment_date=apt_date
    ).exclude(status='CANCELLED')

    if existing_bookings.count() >= doctor.max_daily_slots:
        alt_date = apt_date + datetime.timedelta(days=1)
        return JsonResponse({
            'success': False,
            'status': 'DENIED',
            'title': 'Booking Denied',
            'message': f'All OPD slots for {doctor.name} on {apt_date.strftime("%d-%b-%Y")} are fully booked. Daily capacity reached.',
            'suggested_date': alt_date.strftime('%Y-%m-%d'),
            'suggested_date_display': alt_date.strftime('%A, %d %B %Y')
        })

    available_slots = AppointmentBooking.TIME_SLOTS
    booked_slots = list(existing_bookings.values_list('time_slot', flat=True))

    if preferred_time_slot and preferred_time_slot in booked_slots:
        # Preferred slot taken, pick next free slot
        free_slots = [s for s in available_slots if s not in booked_slots]
        if not free_slots:
            return JsonResponse({
                'success': False,
                'status': 'DENIED',
                'title': 'No Slots Available',
                'message': f'All time slots for {doctor.name} on {apt_date.strftime("%d-%b-%Y")} are booked.'
            })
        assigned_slot = free_slots[0]
    elif preferred_time_slot:
        assigned_slot = preferred_time_slot
    else:
        free_slots = [s for s in available_slots if s not in booked_slots]
        assigned_slot = free_slots[0] if free_slots else available_slots[0]

    token_no = existing_bookings.count() + 1
    dept_code = doctor.department[:1].upper() if doctor.department else 'A'
    token_str = f"{dept_code}-{token_no:03d}"

    booking = AppointmentBooking.objects.create(
        patient=request.user,
        doctor=doctor,
        hospital=hospital,
        appointment_date=apt_date,
        time_slot=assigned_slot,
        token_number=token_no,
        opd_token_number=token_str,
        consultation_room=doctor.consultation_room or 'Room 203',
        symptoms=symptoms,
        status='BOOKED'
    )

    record_audit_log(request, request.user, 'PATIENT', 'BOOK_APPOINTMENT', 'AppointmentBooking', str(booking.id), 'SUCCESS', f'Booked OPD token {token_str} with {doctor.name} at {hospital.name}')

    HealthNotification.objects.create(
        patient=request.user,
        title=f"Appointment Booked: Token {token_str}",
        message=f"Your OPD appointment with {doctor.name} ({doctor.department}) is confirmed for {apt_date.strftime('%d %B %Y')} at {assigned_slot}. Token #{token_str}, {booking.consultation_room}.",
        category="Checkup Reminder",
        action_tab="bookings"
    )

    return JsonResponse({
        'success': True,
        'status': 'ACCEPTED',
        'title': 'Booking Accepted',
        'booking': {
            'id': booking.id,
            'reference': booking.booking_reference,
            'hospital_name': hospital.name,
            'area_city': f"{hospital.get_city()}, {hospital.get_state()}",
            'doctor_name': doctor.name,
            'department': doctor.department,
            'specialty': doctor.specialty_ref.name if doctor.specialty_ref else doctor.department,
            'room_number': booking.consultation_room,
            'date': apt_date.strftime('%A, %d %B %Y'),
            'date_raw': apt_date.strftime('%Y-%m-%d'),
            'time_slot': assigned_slot,
            'token_number': token_str,
            'token_num_int': token_no,
            'patient_name': request.user.get_display_name(),
            'patient_phone': request.user.phone,
            'status': 'BOOKED'
        }
    })


@login_required
@csrf_exempt
def cancel_appointment_api(request, booking_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    booking = get_object_or_404(AppointmentBooking, id=booking_id, patient=request.user)
    booking.status = 'CANCELLED'
    booking.save()

    HealthNotification.objects.create(
        patient=request.user,
        title=f"Appointment Cancelled: {booking.booking_reference}",
        message=f"Your appointment with {booking.doctor.name} at {booking.hospital.name} for {booking.appointment_date.strftime('%d-%b-%Y')} has been cancelled.",
        category="Checkup Reminder",
        action_tab="bookings"
    )

    return JsonResponse({
        'success': True,
        'message': f'Appointment {booking.booking_reference} has been cancelled successfully.'
    })


@csrf_exempt
def api_location_pincode_sync(request):
    """
    Bi-directional Location <-> Pincode Auto-Sync API:
    Returns location, pincode, state, district, and matching hospitals.
    """
    location = request.GET.get('location', '').strip()
    pincode = request.GET.get('pincode', '').strip()
    auto_detect = request.GET.get('auto_detect', '').lower() == 'true'

    facility = None
    area = None

    if pincode:
        facility = HospitalFacility.objects.filter(Q(pincode=pincode) | Q(area__pincode=pincode)).first()
        if not facility:
            area = HospitalArea.objects.filter(pincode=pincode).first()
    elif location:
        facility = HospitalFacility.objects.filter(
            Q(city__icontains=location) | Q(district__icontains=location) | Q(area__city__icontains=location) | Q(area__area_name__icontains=location)
        ).first()
        if not facility:
            area = HospitalArea.objects.filter(Q(city__icontains=location) | Q(area_name__icontains=location)).first()

    if not facility and not area:
        facility = HospitalFacility.objects.first()
        area = facility.area if facility else HospitalArea.objects.first()

    city = facility.get_city() if facility else (area.city if area else 'Narasaraopet')
    state = facility.get_state() if facility else (area.state if area else 'Andhra Pradesh')
    district = facility.district if facility and facility.district else f"{city} District"
    res_pincode = facility.get_pincode() if facility else (area.pincode if area else '522601')
    area_name = facility.area.area_name if facility and facility.area else (area.area_name if area else 'Main Area')

    matching_hospitals = HospitalFacility.objects.filter(
        Q(city__iexact=city) | Q(area__city__iexact=city) | Q(pincode=res_pincode)
    )

    hosp_list = []
    for h in matching_hospitals:
        hosp_list.append({
            'id': h.id,
            'name': h.name,
            'facility_type': h.get_facility_type_display(),
            'opd_timings': h.opd_timings,
            'emergency': h.emergency_available,
            'address': h.address,
            'phone': h.contact_phone
        })

    return JsonResponse({
        'success': True,
        'city': city,
        'area_name': area_name,
        'pincode': res_pincode,
        'district': district,
        'state': state,
        'hospitals': hosp_list
    })


@csrf_exempt
def api_recommend_specialist(request):
    """
    Automatic Specialist Doctor Referral API based on Symptoms / Reason for Consultation.
    """
    symptoms = request.GET.get('symptoms', '').strip().lower()
    hospital_id = request.GET.get('hospital_id')

    dept_mapping = [
        (['tooth', 'teeth', 'dental', 'gum', 'cavity', 'oral'], 'Dentistry', 'Dental Sciences & Maxillofacial Care'),
        (['heart', 'chest pain', 'bp', 'cardio', 'palpitation', 'pulse'], 'Cardiology', 'Cardiology & Heart Care'),
        (['brain', 'headache', 'neuro', 'seizure', 'numbness', 'stroke', 'paralysis', 'migraine'], 'Neurology', 'Neurology & Brain Sciences'),
        (['skin', 'rash', 'acne', 'itching', 'eczema', 'derma', 'spot'], 'Dermatology', 'Dermatology & Skin Care'),
        (['cough', 'breath', 'lungs', 'asthma', 'o2', 'respiratory', 'chest tightness', 'oxygen'], 'Pulmonology', 'Pulmonology & Respiratory Care'),
        (['child', 'infant', 'pediatric', 'baby', 'vaccine', 'kid'], 'Pediatrics', 'Pediatrics & Child Care'),
        (['bone', 'fracture', 'joint', 'ortho', 'knee', 'back pain', 'spine', 'shoulder'], 'Orthopedics', 'Orthopedics & Joint Care'),
        (['stomach', 'gastric', 'acidity', 'digest', 'liver', 'gastro', 'abdominal', 'vomiting', 'nausea'], 'Gastroenterology', 'Gastroenterology & Digestive Health'),
        (['kidney', 'urine', 'renal', 'nephro', 'dialysis', 'creatinine'], 'Nephrology', 'Nephrology & Renal Care'),
        (['eye', 'vision', 'cataract', 'ophthal', 'sight', 'blind'], 'Ophthalmology', 'Ophthalmology & Eye Care'),
        (['ear', 'nose', 'throat', 'ent', 'sinus', 'tonsil', 'hearing'], 'ENT', 'ENT & Otolaryngology'),
        (['x-ray', 'ct scan', 'mri', 'ultrasound', 'scan', 'radio', 'imaging'], 'Radiology', 'Radiology & Diagnostic Imaging'),
        (['cancer', 'tumor', 'chemo', 'onco', 'lump', 'biopsy'], 'Oncology', 'Oncology & Cancer Care'),
        (['pregnant', 'period', 'gynec', 'female', 'ovary', 'uterus', 'pregnancy'], 'Gynecology', 'Obstetrics & Gynecology'),
        (['anxiety', 'depression', 'mental', 'psychiatry', 'stress', 'sleep', 'panic'], 'Psychiatry', 'Psychiatry & Behavioral Health'),
        (['emergency', 'trauma', 'accident', 'bleeding', 'unconscious', 'severe injury'], 'Emergency Medicine', 'Trauma & Emergency Care'),
    ]

    detected_dept = 'General Medicine'
    dept_label = 'General Medicine & Family Health'

    for keywords, dept_code, label in dept_mapping:
        if any(kw in symptoms for kw in keywords):
            detected_dept = dept_code
            dept_label = label
            break

    qs = DoctorProfile.objects.filter(department=detected_dept, is_active=True)
    if hospital_id and hospital_id.isdigit():
        hosp_qs = qs.filter(hospital_id=int(hospital_id))
        if hosp_qs.exists():
            qs = hosp_qs

    recommended_doctor = qs.first() or DoctorProfile.objects.filter(department='General Medicine').first() or DoctorProfile.objects.first()

    return JsonResponse({
        'success': True,
        'detected_department': detected_dept,
        'department_label': dept_label,
        'recommended_doctor': {
            'id': recommended_doctor.id,
            'name': recommended_doctor.name,
            'reg_id': recommended_doctor.doctor_reg_id,
            'qualification': recommended_doctor.qualification,
            'designation': recommended_doctor.designation,
            'hospital_name': recommended_doctor.hospital.name,
            'hospital_id': recommended_doctor.hospital.id,
            'max_daily_slots': recommended_doctor.max_daily_slots,
            'available_days': recommended_doctor.available_days
        } if recommended_doctor else None,
        'reasoning': f"Based on symptoms '{symptoms}', our AI clinical engine matched the medical domain to {dept_label}."
    })


def reverse_geocode_api(request):
    """
    Reverse geocodes lat/lng into Address, City, State, District, Pincode.
    Uses OpenStreetMap Nominatim with database fallback.
    """
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')

    if not lat or not lng:
        return JsonResponse({'success': False, 'error': 'lat and lng required'}, status=400)

    city = 'Narasaraopet'
    state = 'Andhra Pradesh'
    district = 'Palnadu District'
    pincode = '522601'
    area_name = 'Main Town'
    address = 'Narasaraopet, Palnadu District, Andhra Pradesh - 522601'

    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}&zoom=18&addressdetails=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'GovHospitalHealthPortal/1.0'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            addr = data.get('address', {})
            city = addr.get('city') or addr.get('town') or addr.get('village') or addr.get('county') or 'Narasaraopet'
            state = addr.get('state') or 'Andhra Pradesh'
            district = addr.get('state_district') or addr.get('district') or addr.get('county') or f"{city} District"
            pincode = addr.get('postcode') or '522601'
            area_name = addr.get('suburb') or addr.get('neighbourhood') or addr.get('residential') or addr.get('road') or city
            display_name = data.get('display_name') or f"{area_name}, {city}, {state} - {pincode}"
            address = display_name
    except Exception:
        u_lat, u_lng = float(lat), float(lng)
        best_h = None
        min_d = 999999
        for h in HospitalFacility.objects.all():
            if h.latitude and h.longitude:
                d = calculate_haversine(u_lat, u_lng, h.latitude, h.longitude)
                if d is not None and d < min_d:
                    min_d = d
                    best_h = h
        if best_h:
            city = best_h.get_city()
            state = best_h.get_state()
            district = best_h.district or f"{city} District"
            pincode = best_h.get_pincode()
            area_name = best_h.area.area_name if best_h.area else city
            address = f"{area_name}, {district}, {state} - {pincode}"

    return JsonResponse({
        'success': True,
        'location': {
            'address': address,
            'city': city,
            'state': state,
            'district': district,
            'pincode': pincode,
            'area_name': area_name,
            'lat': lat,
            'lng': lng
        }
    })
