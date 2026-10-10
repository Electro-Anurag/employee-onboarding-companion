"""M0 settings. PostgreSQL is required; SQLite is intentionally unsupported."""
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parents[2]
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY or SECRET_KEY == "REPLACE_ME_FOR_LOCAL_ONLY":
    raise ImproperlyConfigured("Set a non-placeholder DJANGO_SECRET_KEY")
DEBUG = os.environ.get("DJANGO_DEBUG") == "1"
ALLOWED_HOSTS = [x.strip() for x in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if x.strip()]
INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions", "django.contrib.staticfiles",
    "procrastinate.contrib.django", "backend.jobs.apps.JobsConfig", "backend.foundation.apps.FoundationConfig",
    "backend.accounts.apps.AccountsConfig", "backend.notifications.apps.NotificationsConfig", "backend.forms.apps.FormsConfig", "backend.provisioning.apps.ProvisioningConfig", "backend.policies.apps.PoliciesConfig", "backend.documents.apps.DocumentsConfig", "backend.training.apps.TrainingConfig", "backend.activities.apps.ActivitiesConfig", "backend.templates.apps.TemplatesConfig", "backend.onboarding.apps.OnboardingConfig", "backend.audit.apps.AuditConfig",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "backend.accounts.middleware.SessionGuard",
]
ROOT_URLCONF = "backend.config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [], "APP_DIRS": True,
              "OPTIONS": {"context_processors": ["django.template.context_processors.request", "django.contrib.auth.context_processors.auth"]}}]
WSGI_APPLICATION = "backend.config.wsgi.application"
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.environ.get("POSTGRES_DB", "onboarding_m0"),
    "USER": os.environ.get("POSTGRES_USER", "onboarding"),
    "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
    "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
    "PORT": int(os.environ.get("POSTGRES_PORT", "5432")),
    "CONN_MAX_AGE": 0,
    "OPTIONS": {"connect_timeout": 5},
}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "backend" / "static"
STORAGES = {"staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}}
USE_TZ = True
TIME_ZONE = "UTC"
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

AUTH_USER_MODEL = 'accounts.User'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.Argon2PasswordHasher']
AUTH_PASSWORD_VALIDATORS = [
    {'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':12}},
    {'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'},
    {'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
]
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 1800
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'
CSRF_TRUSTED_ORIGINS = [s for s in __import__('os').environ.get('DJANGO_CSRF_TRUSTED_ORIGINS','').split(',') if s]
DATA_UPLOAD_MAX_MEMORY_SIZE = 262144

# Separate pre-production quarantine boundary, disabled by default. Never set
# this true without private data controls, configured scanner and an approved
# deployment/data retention design. It does not enable HR document acceptance.
M3_QUARANTINE_INTAKE_ENABLED = os.environ.get('M3_QUARANTINE_INTAKE_ENABLED','0') == '1'
M3_CLAMAV_HOST = os.environ.get('M3_CLAMAV_HOST','')
M3_CLAMAV_PORT = int(os.environ.get('M3_CLAMAV_PORT','3310'))

# Local integration only until secure hosting, retention and access policies qualify.
# Do not accept genuine identity documents in the demo.
M3_REAL_DOCUMENT_ENABLED=os.environ.get('M3_REAL_DOCUMENT_ENABLED','0')=='1'
M3_S3_QUARANTINE_BUCKET=os.environ.get('M3_S3_QUARANTINE_BUCKET','')
M3_S3_CLEAN_BUCKET=os.environ.get('M3_S3_CLEAN_BUCKET','')
M3_S3_ENDPOINT_URL=os.environ.get('M3_S3_ENDPOINT_URL','')
M3_S3_REGION=os.environ.get('M3_S3_REGION','ap-southeast-1')
M3_S3_KMS_KEY_ID=os.environ.get('M3_S3_KMS_KEY_ID','')
M3_S3_ALLOW_LOCAL_TEST_ENDPOINT=os.environ.get('M3_S3_ALLOW_LOCAL_TEST_ENDPOINT','0')=='1'
DATA_UPLOAD_MAX_MEMORY_SIZE=12*1024*1024 if M3_REAL_DOCUMENT_ENABLED else 262144
FILE_UPLOAD_MAX_MEMORY_SIZE=12*1024*1024 if M3_REAL_DOCUMENT_ENABLED else 262144
