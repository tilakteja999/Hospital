#!/usr/bin/env python
"""Test all portal login flows."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_core.settings')

import django
django.setup()

from django.test import Client

def test_portal(name, login_url, login_data, portal_url):
    c = Client()
    r = c.post(login_url, login_data)
    loc = r.get('Location', 'no-redirect')
    print(f"\n=== {name} ===")
    print(f"  Login POST {login_url} => {r.status_code} -> {loc}")
    
    r2 = c.get(portal_url, follow=True)
    print(f"  Portal GET {portal_url} => {r2.status_code}")
    if r2.status_code >= 400:
        content = r2.content.decode('utf-8', 'replace')
        # Try to find error message
        if 'Exception' in content or 'Error' in content or 'Traceback' in content:
            start = content.find('<pre')
            if start >= 0:
                end = content.find('</pre>', start)
                print(f"  ERROR: {content[start:end+6][:800]}")
            else:
                # find the exception type
                for line in content.split('\n'):
                    if 'Error' in line or 'Exception' in line:
                        print(f"  ERROR LINE: {line.strip()[:200]}")
        else:
            print(f"  Content length: {len(content)}")
    else:
        print(f"  OK - Content length: {len(r2.content)}")
    c.get('/logout/')

# Patient
test_portal(
    "PATIENT",
    '/login/patient/',
    {'phone': '9876543210', 'password': 'pass123'},
    '/dashboard/'
)

# Doctor
test_portal(
    "DOCTOR",
    '/login/doctor/',
    {'phone': '9123456780', 'password': 'doc123'},
    '/doctor-portal/'
)

# Admin
test_portal(
    "ADMIN",
    '/login/admin/',
    {'phone': '9998887770', 'password': 'admin123'},
    '/admin-portal/'
)

# Hospital
test_portal(
    "HOSPITAL",
    '/login/hospital/',
    {'phone': '9811111111', 'password': 'hospital123'},
    '/hospital-portal/'
)
