from django.db import models
from django.conf import settings
from django.utils import timezone
import random

class Specialty(models.Model):
    name = models.CharField(max_length=120, unique=True, db_index=True)
    code = models.CharField(max_length=60, unique=True, blank=True)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=30, default='🩺')

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Specialties'

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.name.lower().replace(' ', '_').replace('&', 'and')
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class HospitalArea(models.Model):
    city = models.CharField(max_length=100, db_index=True)
    area_name = models.CharField(max_length=150, db_index=True)
    state = models.CharField(max_length=100, default='Delhi')
    pincode = models.CharField(max_length=10, blank=True)

    class Meta:
        ordering = ['city', 'area_name']
        unique_together = ('city', 'area_name')

    def __str__(self):
        return f"{self.area_name}, {self.city}"


class HospitalFacility(models.Model):
    FACILITY_TYPES = (
        ('Apex Institute', 'Apex Research & Super-Specialty Institute'),
        ('Central Govt', 'Central Government Hospital'),
        ('District Hospital', 'District General Hospital'),
        ('ESI Hospital', 'ESI Corporation Hospital'),
        ('CHC', 'Community Health Centre'),
        ('Private Hospital', 'Private Hospital / Multispecialty'),
        ('Trust Hospital', 'Charitable Trust Hospital'),
        ('PHC', 'Primary Health Centre'),
    )

    STATUS_CHOICES = (
        ('ACTIVE', 'Active & Verified (सक्रिय)'),
        ('PENDING_VERIFICATION', 'Pending Verification (सत्यापन लंबित)'),
        ('SUSPENDED', 'Suspended (निलंबित)'),
        ('INACTIVE', 'Inactive (निष्क्रिय)'),
    )

    name = models.CharField(max_length=200, db_index=True)
    area = models.ForeignKey(HospitalArea, on_delete=models.CASCADE, related_name='hospitals', null=True, blank=True)
    facility_type = models.CharField(max_length=50, choices=FACILITY_TYPES, default='Central Govt')
    address = models.CharField(max_length=255)
    contact_phone = models.CharField(max_length=30, default='+91 11 26588500')
    email = models.EmailField(blank=True, default='info@hospital.gov.in')
    license_number = models.CharField(max_length=50, blank=True, default='MOHFW-HOSP-2026-001')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='ACTIVE')
    emergency_available = models.BooleanField(default=True)
    total_beds = models.IntegerField(default=1500)
    opd_timings = models.CharField(max_length=100, default='08:00 AM - 02:00 PM (Mon-Sat)')
    latitude = models.FloatField(null=True, blank=True, db_index=True)
    longitude = models.FloatField(null=True, blank=True, db_index=True)
    city = models.CharField(max_length=100, blank=True, default='', db_index=True)
    district = models.CharField(max_length=100, blank=True, default='', db_index=True)
    state = models.CharField(max_length=100, blank=True, default='')
    pincode = models.CharField(max_length=10, blank=True, default='', db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    @property
    def phone(self):
        return self.contact_phone

    @property
    def hospital_type(self):
        return self.facility_type

    def get_pincode(self):
        return self.pincode or (self.area.pincode if self.area else '')

    def get_city(self):
        return self.city or (self.area.city if self.area else '')

    def get_state(self):
        return self.state or (self.area.state if self.area else '')

    def get_specialties_list(self):
        dept_names = list(self.doctors.filter(is_active=True).values_list('department', flat=True).distinct())
        spec_names = list(self.doctors.filter(is_active=True, specialty_ref__isnull=False).values_list('specialty_ref__name', flat=True).distinct())
        all_specs = list(set(dept_names + spec_names))
        return sorted([s for s in all_specs if s])

    def __str__(self):
        return f"{self.name} - {self.get_city()}"


# Model Alias
Hospital = HospitalFacility


class HospitalAdmin(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hospital_admin_profile')
    hospital = models.ForeignKey(HospitalFacility, on_delete=models.CASCADE, related_name='admins')
    designation = models.CharField(max_length=100, default='Hospital Superintendent / Medical Director')
    phone = models.CharField(max_length=20, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_display_name()} ({self.hospital.name})"


class Department(models.Model):
    hospital = models.ForeignKey(HospitalFacility, on_delete=models.CASCADE, related_name='departments_list')
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ('hospital', 'name')

    def __str__(self):
        return f"{self.name} ({self.hospital.name})"


class DoctorProfile(models.Model):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active (सक्रिय)'),
        ('INACTIVE', 'Inactive (निष्क्रिय)'),
        ('ON_LEAVE', 'On Leave (अवकाश पर)'),
        ('SUSPENDED', 'Suspended (निलंबित)'),
    )

    VERIFICATION_CHOICES = (
        ('VERIFIED', 'Verified (सत्यापित)'),
        ('PENDING_VERIFICATION', 'Pending Verification (सत्यापन लंबित)'),
        ('REJECTED', 'Rejected (अस्वीकृत)'),
    )

    DEPARTMENT_CHOICES = (
        ('General Medicine', 'General Medicine & Family Health'),
        ('Cardiology', 'Cardiology & Heart Care'),
        ('Pulmonology', 'Pulmonology & Respiratory Care'),
        ('Endocrinology', 'Endocrinology & Diabetes'),
        ('Nephrology', 'Nephrology & Renal Care'),
        ('Pediatrics', 'Pediatrics & Child Care'),
        ('Orthopedics', 'Orthopedics & Joint Care'),
        ('Gynecology', 'Obstetrics & Gynecology'),
        ('Dermatology', 'Dermatology & Skin Care'),
        ('Neurology', 'Neurology & Brain Sciences'),
        ('Gastroenterology', 'Gastroenterology & Digestive Health'),
        ('Oncology', 'Oncology & Cancer Care'),
        ('ENT', 'ENT & Otolaryngology'),
        ('Ophthalmology', 'Ophthalmology & Eye Care'),
        ('Urology', 'Urology & Kidney Care'),
        ('Psychiatry', 'Psychiatry & Behavioral Health'),
        ('Dentistry', 'Dental Sciences & Maxillofacial Care'),
        ('Radiology', 'Radiology & Imaging Diagnostics'),
        ('Emergency Medicine', 'Trauma & Emergency Care'),
        ('Anesthesiology', 'Anesthesia & Critical Care'),
    )

    hospital = models.ForeignKey(HospitalFacility, on_delete=models.CASCADE, related_name='doctors')
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='doctor_profile')
    doctor_reg_id = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text="Medical Council Registration / Doctor ID")
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    qualification = models.CharField(max_length=150, default='MBBS, MD')
    specialization = models.CharField(max_length=150, blank=True, default='General Medicine')
    department = models.CharField(max_length=80, choices=DEPARTMENT_CHOICES, default='General Medicine')
    department_obj = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='doctors_in_dept')
    specialty_ref = models.ForeignKey(Specialty, on_delete=models.SET_NULL, null=True, blank=True, related_name='doctors')
    designation = models.CharField(max_length=100, default='Senior Medical Officer')
    experience_years = models.IntegerField(default=12)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    verification_status = models.CharField(max_length=30, choices=VERIFICATION_CHOICES, default='VERIFIED')
    available_days = models.CharField(max_length=100, default='Mon, Tue, Wed, Thu, Fri, Sat')
    consultation_room = models.CharField(max_length=50, default='Room 203')
    opd_start_time = models.CharField(max_length=20, default='09:00 AM')
    opd_end_time = models.CharField(max_length=20, default='01:00 PM')
    appointment_duration = models.IntegerField(default=15, help_text="Duration per patient in minutes")
    max_daily_slots = models.IntegerField(default=35)
    leave_status = models.BooleanField(default=False, help_text="Emergency leave or planned leave flag")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    is_active = models.BooleanField(default=True)
    is_present_today = models.BooleanField(default=True, help_text="Duty presence in hospital today")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['hospital', 'department', 'name']

    @property
    def licensing_id(self):
        return self.doctor_reg_id

    @property
    def working_days(self):
        return self.available_days

    @property
    def start_time(self):
        return self.opd_start_time

    @property
    def end_time(self):
        return self.opd_end_time

    @property
    def slot_duration(self):
        return self.appointment_duration

    @property
    def max_patients_per_day(self):
        return self.max_daily_slots

    def save(self, *args, **kwargs):
        if not self.doctor_reg_id:
            import random
            hosp_code = self.hospital.name[:4].upper().replace(' ', '') if self.hospital else 'GOV'
            self.doctor_reg_id = f"DOC-{hosp_code}-{random.randint(1000, 9999)}"
        self.is_active = (self.status == 'ACTIVE')
        super().save(*args, **kwargs)

    def is_available_for_booking(self):
        return self.status == 'ACTIVE' and self.is_active and self.verification_status == 'VERIFIED' and not self.leave_status

    def patients_taken_today_count(self):
        today = timezone.now().date()
        return self.appointments.filter(appointment_date=today, status='COMPLETED').count()

    def total_patients_taken_count(self):
        return self.appointments.filter(status='COMPLETED').count()

    def total_appointments_count(self):
        return self.appointments.count()

    def __str__(self):
        return f"[{self.doctor_reg_id or 'DOC'}] {self.name} ({self.department}) - {self.hospital.name} [{self.status}]"


# Model Alias
Doctor = DoctorProfile


class AppointmentBooking(models.Model):
    STATUS_CHOICES = (
        ('BOOKED', 'Booked (दर्ज)'),
        ('CHECKED_IN', 'Checked In (उपस्थित)'),
        ('WAITING', 'Waiting in Queue (प्रतीक्षारत)'),
        ('IN_CONSULTATION', 'In Consultation (परामर्श जारी)'),
        ('COMPLETED', 'Completed (पूर्ण)'),
        ('CANCELLED', 'Cancelled (रद्द)'),
        ('NO_SHOW', 'No Show (अनुपस्थित)'),
        ('RESCHEDULED', 'Rescheduled (पुनर्निर्धारित)'),
        # Backward compatibility aliases
        ('CONFIRMED', 'Confirmed (पुष्टित)'),
        ('IN_PROGRESS', 'In Progress (प्रगति पर)'),
    )

    TIME_SLOTS = [
        '09:00 AM - 09:30 AM',
        '09:30 AM - 10:00 AM',
        '10:00 AM - 10:30 AM',
        '10:30 AM - 11:00 AM',
        '11:00 AM - 11:30 AM',
        '11:30 AM - 12:00 PM',
        '12:00 PM - 12:30 PM',
        '02:00 PM - 02:30 PM',
        '02:30 PM - 03:00 PM',
        '03:00 PM - 03:30 PM',
    ]

    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='appointments')
    hospital = models.ForeignKey(HospitalFacility, on_delete=models.CASCADE, related_name='appointments')
    appointment_date = models.DateField(default=timezone.now)
    time_slot = models.CharField(max_length=50, default='10:00 AM - 10:30 AM')
    session = models.CharField(max_length=20, default='MORNING', choices=(('MORNING', 'Morning OPD'), ('AFTERNOON', 'Afternoon OPD'), ('EVENING', 'Evening OPD')))
    token_number = models.IntegerField(default=1)
    opd_token_number = models.CharField(max_length=20, blank=True, help_text="e.g. A-024")
    consultation_room = models.CharField(max_length=50, blank=True, default='')
    symptoms = models.TextField(blank=True, default='Routine follow-up / general consultation')
    consultation_notes = models.TextField(blank=True, help_text="Doctor diagnosis notes and clinical observations")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='BOOKED')
    is_emergency = models.BooleanField(default=False)
    cancellation_reason = models.TextField(blank=True, default='')
    rescheduled_from = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='rescheduled_to')
    booking_reference = models.CharField(max_length=30, unique=True, blank=True)
    booked_at = models.DateTimeField(auto_now_add=True)
    called_at = models.DateTimeField(null=True, blank=True)
    consultation_started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-appointment_date', 'token_number', '-booked_at']

    @property
    def appointment_time(self):
        return self.time_slot

    @property
    def department(self):
        return self.doctor.department if self.doctor else 'General'

    def save(self, *args, **kwargs):
        if not self.booking_reference:
            year = timezone.now().year
            rand_code = random.randint(10000, 99999)
            self.booking_reference = f"GOI-APT-{year}-{rand_code}"
        
        if not self.consultation_room and self.doctor:
            self.consultation_room = self.doctor.consultation_room or 'Room 203'

        if not self.token_number or self.token_number == 1:
            existing_count = AppointmentBooking.objects.filter(
                doctor=self.doctor,
                appointment_date=self.appointment_date
            ).exclude(status__in=['CANCELLED']).exclude(id=self.id).count()
            self.token_number = existing_count + 1

        if not self.opd_token_number:
            dept_prefix = self.doctor.department[:1].upper() if self.doctor and self.doctor.department else 'A'
            self.opd_token_number = f"{dept_prefix}-{self.token_number:03d}"

        super().save(*args, **kwargs)

    def mark_completed(self, notes=""):
        self.status = 'COMPLETED'
        self.completed_at = timezone.now()
        if notes:
            self.consultation_notes = notes
        self.save()

    def get_effective_status(self):
        if self.status in ['CONFIRMED', 'BOOKED']:
            return 'BOOKED'
        return self.status

    @property
    def reference_number(self):
        return self.booking_reference

    def __str__(self):
        return f"[{self.opd_token_number or self.token_number}] {self.booking_reference} - {self.patient.get_display_name()} with {self.doctor.name} on {self.appointment_date} ({self.status})"


# Model Alias
Appointment = AppointmentBooking


class HospitalResource(models.Model):
    hospital = models.OneToOneField(HospitalFacility, on_delete=models.CASCADE, related_name='resource_status')
    general_beds_total = models.IntegerField(default=500)
    general_beds_occupied = models.IntegerField(default=320)
    icu_beds_total = models.IntegerField(default=80)
    icu_beds_occupied = models.IntegerField(default=65)
    ventilator_beds_total = models.IntegerField(default=40)
    ventilator_beds_occupied = models.IntegerField(default=28)
    oxygen_beds_total = models.IntegerField(default=200)
    oxygen_beds_occupied = models.IntegerField(default=145)
    oxygen_supply_status = models.CharField(max_length=100, default='Normal (Pressure: 98%)')
    updated_at = models.DateTimeField(auto_now=True)

    def general_beds_available(self):
        return max(0, self.general_beds_total - self.general_beds_occupied)

    def icu_beds_available(self):
        return max(0, self.icu_beds_total - self.icu_beds_occupied)

    def ventilator_beds_available(self):
        return max(0, self.ventilator_beds_total - self.ventilator_beds_occupied)

    def oxygen_beds_available(self):
        return max(0, self.oxygen_beds_total - self.oxygen_beds_occupied)

    def icu_occupancy_pct(self):
        if self.icu_beds_total == 0: return 0.0
        return round((self.icu_beds_occupied / self.icu_beds_total) * 100, 1)

    def total_beds(self):
        return self.general_beds_total + self.icu_beds_total + self.ventilator_beds_total + self.oxygen_beds_total

    def total_occupied(self):
        return self.general_beds_occupied + self.icu_beds_occupied + self.ventilator_beds_occupied + self.oxygen_beds_occupied

    def total_occupancy_pct(self):
        t = self.total_beds()
        if t == 0: return 0.0
        return round((self.total_occupied() / t) * 100, 1)

    def __str__(self):
        return f"Resource Status for {self.hospital.name} (ICU: {self.icu_occupancy_pct()}%)"


