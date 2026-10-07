from django.core.exceptions import PermissionDenied
from django.utils import timezone
from core.audit_utils import record_audit_log
from patients.models import ConsentRecord
from appointments.models import AppointmentBooking

def check_patient_record_access(request, patient_user, resource_type='PatientRecord', resource_id=''):
    """
    Validates whether the requesting user has legitimate clinical or personal authorization
    to access the specified patient's data.
    """
    user = request.user
    if not user.is_authenticated:
        record_audit_log(request, None, 'ANONYMOUS', 'SYSTEM_SECURITY', resource_type, resource_id, 'FAILURE', 'Unauthenticated access attempt blocked.')
        return False

    # 1. Patient accessing own record
    if user.id == patient_user.id:
        return True

    # 2. Doctor accessing patient record
    if user.role == 'DOCTOR':
        # Check active consent record
        active_consent = ConsentRecord.objects.filter(
            patient=patient_user,
            status='GRANTED'
        ).filter(
            models_q_match(user)
        ).first()

        if active_consent and active_consent.is_active():
            record_audit_log(request, user, 'DOCTOR', 'VIEW_RECORD', resource_type, resource_id, 'SUCCESS', f'Doctor accessed record under active consent #{active_consent.id}')
            return True

        # Check assigned appointment
        if hasattr(user, 'doctor_profile') and user.doctor_profile:
            has_appointment = AppointmentBooking.objects.filter(
                patient=patient_user,
                doctor=user.doctor_profile
            ).exclude(status='CANCELLED').exists()

            if has_appointment:
                record_audit_log(request, user, 'DOCTOR', 'VIEW_RECORD', resource_type, resource_id, 'SUCCESS', f'Doctor accessed record for assigned patient appointment')
                return True

        # Denied access
        record_audit_log(request, user, 'DOCTOR', 'SYSTEM_SECURITY', resource_type, resource_id, 'FAILURE', f'Doctor {user.get_display_name()} unauthorized access attempt to patient {patient_user.get_display_name()} without consent.')
        return False

    # 3. Admin does not have automatic clinical record access
    if user.role == 'ADMIN' or user.is_superuser:
        # Check if consent specifically given or emergency override
        record_audit_log(request, user, 'ADMIN', 'SYSTEM_SECURITY', resource_type, resource_id, 'FAILURE', f'Admin {user.get_display_name()} blocked from direct clinical record view without patient consent.')
        return False

    record_audit_log(request, user, user.role, 'SYSTEM_SECURITY', resource_type, resource_id, 'FAILURE', 'Unauthorized role access attempt blocked.')
    return False

def models_q_match(user):
    from django.db.models import Q
    doc_profile = getattr(user, 'doctor_profile', None)
    doc_name = user.full_name or user.get_display_name()
    q = Q(doctor_name__icontains=doc_name)
    if doc_profile and doc_profile.doctor_reg_id:
        q |= Q(doctor_reg_id=doc_profile.doctor_reg_id)
    return q
