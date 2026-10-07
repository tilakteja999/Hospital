from core.models import AuditLog

def get_client_ip(request):
    if not request:
        return '127.0.0.1'
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
    return ip or '127.0.0.1'

def record_audit_log(request=None, user=None, role=None, action='SYSTEM_SECURITY', resource_type='', resource_id='', status='SUCCESS', details=''):
    """
    Immutable audit logging helper across all views and APIs.
    """
    try:
        if request and not user and hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user
        
        if not role:
            if user and hasattr(user, 'role'):
                role = user.role
            elif user and user.is_superuser:
                role = 'ADMIN'
            else:
                role = 'SYSTEM'
        
        user_display = user.get_display_name() if (user and hasattr(user, 'get_display_name')) else (user.username if user else 'System Automated Task')
        ip_addr = get_client_ip(request)

        AuditLog.objects.create(
            user=user if (user and getattr(user, 'is_authenticated', False)) else None,
            user_display=user_display,
            role=role,
            action=action,
            action_display=dict(AuditLog.ACTION_CHOICES).get(action, action),
            resource_type=resource_type,
            resource_id=str(resource_id),
            ip_address=ip_addr,
            status=status,
            details=details
        )
    except Exception as e:
        # Failsafe so audit logging failure does not crash clinical operations
        print(f"[AUDIT_LOG_ERROR] {e}")
