"""
Django settings for hospital_core project.
Government of India Hospital Management & Health Portal.
"""

import os
import secrets
import shutil
import tempfile
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, '.env'))
except Exception:
    pass

MAPS_PROVIDER = os.getenv('MAPS_PROVIDER', 'leaflet')
MAPS_API_KEY = os.getenv('MAPS_API_KEY', '')

DEBUG = os.getenv('DJANGO_DEBUG', 'False' if os.getenv('VERCEL') else 'True').lower() in ('true', '1', 'yes')
IS_VERCEL = bool(os.getenv('VERCEL'))
DATABASE_URL = os.getenv('DATABASE_URL')
USE_MYSQL = os.getenv('USE_MYSQL', 'False').lower() in ('true', '1', 'yes')
EPHEMERAL_DEMO_MODE = IS_VERCEL and not DATABASE_URL and not USE_MYSQL
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if not DEBUG and not EPHEMERAL_DEMO_MODE:
        raise ImproperlyConfigured('Set DJANGO_SECRET_KEY in the deployment environment.')
    SECRET_KEY = secrets.token_urlsafe(50) if EPHEMERAL_DEMO_MODE else 'django-insecure-local-development-key'

ALLOWED_HOSTS = [host.strip() for host in os.getenv('DJANGO_ALLOWED_HOSTS', '').split(',') if host.strip()]
if os.getenv('VERCEL'):
    ALLOWED_HOSTS.append('.vercel.app')
    if os.getenv('VERCEL_URL'):
        ALLOWED_HOSTS.append(os.environ['VERCEL_URL'])
elif not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'core',
    'patients',
    'appointments',
    'voice_ai',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'hospital_core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'hospital_core.wsgi.application'

# Database Configuration
if DATABASE_URL:
    import dj_database_url

    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=bool(os.getenv('VERCEL')),
        )
    }
    if DATABASES['default']['ENGINE'] == 'django.db.backends.mysql':
        import pymysql

        pymysql.install_as_MySQLdb()
elif USE_MYSQL:
    import pymysql

    pymysql.install_as_MySQLdb()

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.getenv('DB_NAME', 'hospital_db'),
            'USER': os.getenv('DB_USER', 'root'),
            'PASSWORD': os.getenv('DB_PASSWORD', 'root'),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            }
        }
    }
elif IS_VERCEL:
    source_database = BASE_DIR / 'db.sqlite3'
    database_path = Path(tempfile.gettempdir()) / 'hospital-demo.sqlite3'
    if not source_database.is_file():
        raise ImproperlyConfigured('The demo SQLite database is missing from the deployment bundle.')
    if not database_path.exists():
        temporary_database = database_path.with_name(f'{database_path.name}.{os.getpid()}.tmp')
        try:
            shutil.copyfile(source_database, temporary_database)
            os.replace(temporary_database, database_path)
        finally:
            temporary_database.unlink(missing_ok=True)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': database_path,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Custom User Model
AUTH_USER_MODEL = 'core.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 4}
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

if IS_VERCEL:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = not DEBUG
    CSRF_COOKIE_SECURE = not DEBUG
