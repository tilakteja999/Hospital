from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from .models import User, AadhaarOTPRecord
import random
import json

def role_portal_view(request):
    if request.user.is_authenticated:
        if request.user.role == 'ADMIN':
            return redirect('admin_portal')
        elif request.user.role == 'HOSPITAL':
            return redirect('hospital_portal')
        elif request.user.role == 'DOCTOR':
            return redirect('doctor_portal')
        return redirect('dashboard')
    return render(request, 'auth/login_portal.html')

def patient_login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '').strip()

        user = authenticate(request, username=phone, password=password)
        if user is not None:
            login(request, user)
            if user.role == 'ADMIN':
                return redirect('admin_portal')
            elif user.role == 'HOSPITAL':
                return redirect('hospital_portal')
            elif user.role == 'DOCTOR':
                return redirect('doctor_portal')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid Phone Number or Password. Please try again or create an account.')

    return render(request, 'auth/patient_login.html')

def doctor_login_view(request):
    if request.user.is_authenticated:
        if request.user.role == 'DOCTOR':
            return redirect('doctor_portal')
        return redirect('dashboard')

    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '').strip()

        user = authenticate(request, username=phone, password=password)
        if user is not None:
            login(request, user)
            return redirect('doctor_portal')
        else:
            messages.error(request, 'Invalid Doctor Phone/Registration credentials.')

    return render(request, 'auth/doctor_login.html')

def hospital_login_view(request):
    if request.user.is_authenticated:
        if request.user.role == 'HOSPITAL':
            return redirect('hospital_portal')
        elif request.user.role == 'ADMIN':
            return redirect('admin_portal')
        return redirect('dashboard')

    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '').strip()

        user = authenticate(request, username=phone, password=password)
        if user is not None and (user.role in ['HOSPITAL', 'ADMIN'] or hasattr(user, 'hospital_admin_profile')):
            login(request, user)
            return redirect('hospital_portal')
        else:
            messages.error(request, 'Invalid Hospital Admin ID or Password.')

    return render(request, 'auth/hospital_login.html')

def admin_login_view(request):
    if request.user.is_authenticated:
        if request.user.role == 'ADMIN':
            return redirect('admin_portal')
        return redirect('dashboard')

    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '').strip()

        user = authenticate(request, username=phone, password=password)
        if user is not None:
            login(request, user)
            return redirect('admin_portal')
        else:
            messages.error(request, 'Invalid Admin Officer credentials.')

    return render(request, 'auth/admin_login.html')

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        full_name = request.POST.get('full_name', '').strip()
        password = request.POST.get('password', '').strip()
        aadhaar_number = request.POST.get('aadhaar_number', '').strip()
        gender = request.POST.get('gender', 'Male')
        age = request.POST.get('age', '30')
        blood_group = request.POST.get('blood_group', 'B+')
        city = request.POST.get('city', 'New Delhi')
        state = request.POST.get('state', 'Delhi')
        is_verified = request.POST.get('is_aadhaar_verified', 'false') == 'true'

        if not phone or not password or not full_name:
            messages.error(request, 'Please fill all required fields.')
            return render(request, 'auth/register.html')

        if User.objects.filter(phone=phone).exists():
            messages.error(request, 'A user with this phone number already exists. Please log in.')
            return render(request, 'auth/register.html')

        abha_rand = f"ABHA-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"
        user = User.objects.create_user(
            phone=phone,
            password=password,
            full_name=full_name,
            role='PATIENT',
            aadhaar_number=aadhaar_number if len(aadhaar_number) == 12 else None,
            is_aadhaar_verified=is_verified,
            abha_id=abha_rand,
            gender=gender,
            age=int(age) if age.isdigit() else 30,
            blood_group=blood_group,
            city=city,
            state=state
        )
        login(request, user)
        messages.success(request, f'Welcome {full_name}! Your Ayushman / Government Health profile has been created successfully.')
        return redirect('dashboard')

    return render(request, 'auth/register.html')

def forgot_password_view(request):
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        otp = request.POST.get('otp', '').strip()

        try:
            user = User.objects.get(phone=phone)
            # Verify OTP record or allow master simulation
            otp_record = AadhaarOTPRecord.objects.filter(phone=phone, is_used=False).first()
            if otp in ['123456', getattr(otp_record, 'otp', None)]:
                user.set_password(new_password)
                user.save()
                messages.success(request, 'Password reset successful! Please log in with your new password.')
                return redirect('patient_login')
            else:
                messages.error(request, 'Invalid or expired OTP. Use demo OTP: 123456 or generated OTP.')
        except User.DoesNotExist:
            messages.error(request, 'No registered user found with this phone number.')

    return render(request, 'auth/forgot_password.html')

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been safely logged out of Government of India Health Portal.')
    return redirect('role_portal')

@csrf_exempt
def generate_aadhaar_otp_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    aadhaar = data.get('aadhaar_number', '').replace('-', '').replace(' ', '').strip()
    phone = data.get('phone', '').strip()

    if len(aadhaar) != 12 or not aadhaar.isdigit():
        return JsonResponse({'success': False, 'message': 'Please enter a valid 12-digit Aadhaar number.'})

    otp_val = AadhaarOTPRecord.generate_otp(aadhaar, phone)
    masked = f"XXXX-XXXX-{aadhaar[-4:]}"

    return JsonResponse({
        'success': True,
        'message': f'UIDAI OTP generated for Aadhaar {masked} and sent to registered mobile ending with ***{phone[-4:] if len(phone)>=4 else "8921"}.',
        'demo_otp': otp_val,
        'masked_aadhaar': masked
    })

@csrf_exempt
def verify_aadhaar_otp_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    aadhaar = data.get('aadhaar_number', '').replace('-', '').replace(' ', '').strip()
    otp = data.get('otp', '').strip()

    valid_record = AadhaarOTPRecord.objects.filter(aadhaar_number=aadhaar, otp=otp, is_used=False).first()

    if otp == '123456' or valid_record:
        if valid_record:
            valid_record.is_used = True
            valid_record.save()

        # If user is logged in, mark user verified
        if request.user.is_authenticated:
            request.user.aadhaar_number = aadhaar
            request.user.is_aadhaar_verified = True
            if not request.user.abha_id:
                request.user.abha_id = f"ABHA-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"
            request.user.save()

        return JsonResponse({
            'success': True,
            'message': 'Aadhaar Identity Successfully Verified with UIDAI Central Identity Repository.',
            'is_verified': True
        })
    else:
        return JsonResponse({
            'success': False,
            'message': 'Invalid OTP entered. Please enter the 6-digit code received or use default test OTP 123456.'
        })

@login_required
@csrf_exempt
def update_profile_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    user = request.user
    user.full_name = data.get('full_name', user.full_name)
    user.age = int(data.get('age', user.age or 30))
    user.gender = data.get('gender', user.gender)
    user.blood_group = data.get('blood_group', user.blood_group)
    user.city = data.get('city', user.city)
    user.state = data.get('state', user.state)
    user.emergency_contact = data.get('emergency_contact', user.emergency_contact)
    user.preferred_language = data.get('preferred_language', user.preferred_language)
    user.save()

    return JsonResponse({
        'success': True,
        'message': 'Profile details updated successfully.',
        'user': {
            'name': user.full_name,
            'phone': user.phone,
            'age': user.age,
            'blood_group': user.blood_group,
            'city': user.city,
            'emergency_contact': user.emergency_contact,
            'language': user.preferred_language
        }
    })
