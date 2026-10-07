from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
import random
import uuid

class CustomUserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError('The Phone Number is required')
        phone = phone.strip()
        user = self.model(phone=phone, username=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')
        return self.create_user(phone, password, **extra_fields)

class User(AbstractUser):
    ROLE_CHOICES = (
        ('PATIENT', 'Patient'),
        ('DOCTOR', 'Doctor'),
        ('HOSPITAL', 'Hospital Admin'),
        ('ADMIN', 'Government Health Officer / National Admin'),
    )

    phone = models.CharField(max_length=15, unique=True, db_index=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='PATIENT')
    full_name = models.CharField(max_length=150, blank=True)
    aadhaar_number = models.CharField(max_length=12, blank=True, null=True, unique=True)
    is_aadhaar_verified = models.BooleanField(default=False)
    abha_id = models.CharField(max_length=20, blank=True, null=True, unique=True)
    gender = models.CharField(max_length=10, choices=(('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')), blank=True, default='Male')
    age = models.IntegerField(null=True, blank=True, default=32)
    blood_group = models.CharField(max_length=5, blank=True, default='B+')
    city = models.CharField(max_length=100, blank=True, default='New Delhi')
    state = models.CharField(max_length=100, blank=True, default='Delhi')
    address = models.TextField(blank=True, default='Sector 4, RK Puram')
    emergency_contact = models.CharField(max_length=15, blank=True, default='+91 9876543210')
    preferred_language = models.CharField(max_length=20, default='English')
    profile_photo_url = models.CharField(max_length=255, blank=True, default='/static/images/default_avatar.svg')

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['full_name']

    objects = CustomUserManager()

    def get_display_name(self):
        return self.full_name or self.phone or 'Citizen'

    def get_masked_aadhaar(self):
        if self.aadhaar_number and len(self.aadhaar_number) == 12:
            return f"XXXX-XXXX-{self.aadhaar_number[-4:]}"
        return "Not Linked"

    def __str__(self):
        return f"{self.get_display_name()} ({self.get_role_display()}) - {self.phone}"


class AadhaarOTPRecord(models.Model):
    aadhaar_number = models.CharField(max_length=12, db_index=True)
    phone = models.CharField(max_length=15)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    @classmethod
    def generate_otp(cls, aadhaar_number, phone):
        otp_val = f"{random.randint(100000, 999999)}"
        # Mark previous OTPs as used
        cls.objects.filter(aadhaar_number=aadhaar_number, is_used=False).update(is_used=True)
        record = cls.objects.create(
            aadhaar_number=aadhaar_number,
            phone=phone,
            otp=otp_val
        )
        return otp_val


class AuditLog(models.Model):
    ACTION_CHOICES = (
        ('VIEW_RECORD', 'Viewed Medical Record'),
        ('CREATE_PRESCRIPTION', 'Created Prescription'),
        ('UPDATE_PRESCRIPTION', 'Updated Prescription'),
        ('ADD_DOCTOR', 'Added Doctor Account'),
        ('UPDATE_DOCTOR', 'Updated Doctor Account'),
        ('VERIFY_DOCTOR', 'Verified Doctor Credentials'),
        ('REJECT_DOCTOR', 'Rejected Doctor Credentials'),
        ('DISABLE_DOCTOR', 'Disabled Doctor Account'),
        ('ENABLE_DOCTOR', 'Enabled Doctor Account'),
        ('ADD_HOSPITAL', 'Registered Hospital Facility'),
        ('UPDATE_HOSPITAL', 'Updated Hospital Facility'),
        ('UPDATE_BED_RESOURCE', 'Updated Bed & Resource Capacity'),
        ('BOOK_APPOINTMENT', 'Booked Appointment'),
        ('CONFIRM_APPOINTMENT', 'Confirmed Appointment'),
        ('RESCHEDULE_APPOINTMENT', 'Rescheduled Appointment'),
        ('CANCEL_APPOINTMENT', 'Cancelled Appointment'),
        ('UPDATE_QUEUE_STATUS', 'Updated OPD Queue Status'),
        ('ORDER_LAB_TEST', 'Ordered Laboratory Test'),
        ('UPDATE_LAB_RESULT', 'Updated Laboratory Result'),
        ('DOWNLOAD_REPORT', 'Downloaded Report / Document'),
        ('CREATE_DISCHARGE_SUMMARY', 'Created Discharge Summary'),
        ('UPDATE_VACCINATION', 'Updated Vaccination Record'),
        ('GRANT_CONSENT', 'Granted Record Access Consent'),
        ('REVOKE_CONSENT', 'Revoked Record Access Consent'),
        ('DENY_CONSENT', 'Denied Record Access Consent'),
        ('UPDATE_EMERGENCY_INFO', 'Updated Emergency Information'),
        ('CREATE_ADVISORY', 'Created Health Advisory'),
        ('UPDATE_SCHEME', 'Updated Health Scheme'),
        ('SYSTEM_SECURITY', 'Security & Authorization Check'),
    )

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    user_display = models.CharField(max_length=150, blank=True, help_text="Cached user name at time of action")
    role = models.CharField(max_length=20, default='SYSTEM')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    action_display = models.CharField(max_length=100, blank=True)
    resource_type = models.CharField(max_length=50, help_text="e.g. PatientRecord, Prescription, DoctorProfile, LabOrder")
    resource_id = models.CharField(max_length=50, blank=True)
    ip_address = models.CharField(max_length=45, default='127.0.0.1')
    status = models.CharField(max_length=20, default='SUCCESS', choices=(('SUCCESS', 'Success'), ('FAILURE', 'Failure / Denied')))
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp.strftime('%d-%b-%Y %H:%M')}] {self.user_display or 'System'} ({self.role}) - {self.get_action_display()} on {self.resource_type} #{self.resource_id}"


class HealthScheme(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True, default='PMJAY')
    subtitle = models.CharField(max_length=255, blank=True, default='Government Healthcare Initiative')
    description = models.TextField()
    eligibility = models.TextField()
    benefits = models.TextField()
    required_documents = models.TextField()
    official_portal_url = models.URLField(default='https://nha.gov.in')
    helpline = models.CharField(max_length=50, default='14555 / 1800-111-565')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class HealthAdvisory(models.Model):
    CATEGORY_CHOICES = (
        ('Vaccination', 'Vaccination & Immunization Drive'),
        ('Seasonal Health', 'Seasonal Health & Monsoon Care'),
        ('Heatwave', 'Heatwave & Extreme Weather'),
        ('Respiratory Health', 'Respiratory & Air Quality Advisory'),
        ('Nutrition', 'Nutrition & Lifestyle Wellness'),
        ('Maternal Health', 'Maternal & Prenatal Health'),
        ('Child Health', 'Child & Infant Care'),
        ('Disease Prevention', 'Communicable Disease Prevention'),
        ('Emergency Preparedness', 'Disaster & Emergency Preparedness'),
    )

    PRIORITY_CHOICES = (
        ('NORMAL', 'Normal Informational'),
        ('HIGH', 'High Priority Notice'),
        ('URGENT', 'Urgent Health Alert'),
    )

    STATUS_CHOICES = (
        ('ACTIVE', 'Active Advisory'),
        ('ARCHIVED', 'Archived / Expired'),
    )

    title = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Seasonal Health')
    description = models.TextField()
    precaution_points = models.TextField(blank=True, help_text="Bulleted prevention measures separated by newline")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='NORMAL')
    published_date = models.DateField(default=timezone.now)
    valid_until = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    issuing_authority = models.CharField(max_length=150, default='Ministry of Health & Family Welfare (MoHFW), Govt of India')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='advisories_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_date', '-created_at']

    def __str__(self):
        return f"[{self.category}] {self.title} ({self.status})"

