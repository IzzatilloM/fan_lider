"""
Django settings for Fan Lider CRM.

O'quv markazi uchun professional CRM tizimi.
Asosiy modullar: Onlayn ro'yxatdan o'tish, To'lovlarni boshqarish,
O'quv jarayonini monitoring qilish.

Kirish: admin/direktor Telegram bot (chat ID + tasdiqlash kodi) orqali
ro'yxatdan o'tadi, so'ng login + parol bilan kiradi. O'qituvchi/o'quvchini
admin yaratadi (login + parol beradi).
"""

from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------- #
#  Asosiy xavfsizlik sozlamalari
# --------------------------------------------------------------------------- #
SECRET_KEY = config(
    'SECRET_KEY',
    default='django-insecure-change-me-in-production-90gf0prtfwgzd',
)
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='127.0.0.1,localhost,.pythonanywhere.com',
    cast=Csv(),
)

CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='https://*.pythonanywhere.com',
    cast=Csv(),
)

# --------------------------------------------------------------------------- #
#  Ilovalar
# --------------------------------------------------------------------------- #
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sites',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
]

LOCAL_APPS = [
    'accounts',
    'courses',
    'students',
    'instructors',
    'enrollments',
    'payments',
    'monitoring',
    'dashboard',
    'salaries',
    'cabinet',
    'api',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'dashboard.context_processors.branding',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# --------------------------------------------------------------------------- #
#  Ma'lumotlar bazasi
# --------------------------------------------------------------------------- #
DB_ENGINE = config('DB_ENGINE', default='sqlite')

if DB_ENGINE == 'postgres':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# --------------------------------------------------------------------------- #
#  Autentifikatsiya — login (yoki email) + parol.
#  Admin/direktor ro'yxatdan o'tishi Telegram kodi bilan tasdiqlanadi.
# --------------------------------------------------------------------------- #
AUTH_USER_MODEL = 'accounts.CustomUser'

# Email orqali ham, username orqali ham kirish mumkin bo'lsin
AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailOrUsernameBackend',
    'django.contrib.auth.backends.ModelBackend',
]

SITE_ID = 1

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 6}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
]

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = 'dashboard:home'
LOGOUT_REDIRECT_URL = 'accounts:login_page'

# --------------------------------------------------------------------------- #
#  Rollar va cheklovlar. Faqat admin/direktor o'zini Telegram orqali
#  ro'yxatdan o'tkazadi; o'qituvchi/o'quvchini admin yaratadi.
# --------------------------------------------------------------------------- #
# Tizimga kira oladigan administratorlarning eng ko'p soni (qattiq cheklov).
MAX_ADMINS = config('MAX_ADMINS', default=2, cast=int)
# Direktor (boshqaruvchi) — faqat bitta bo'lishi mumkin.
MAX_DIRECTORS = config('MAX_DIRECTORS', default=1, cast=int)
# O'zini ro'yxatdan o'tkaza oladigan rollar (qolganlarini admin yaratadi).
SELF_REGISTER_ROLES = ('admin', 'director')

# Telegram tasdiqlash kodi sozlamalari (ro'yxatdan o'tish / parol tiklash)
TG_CODE_TTL_MINUTES = config('TG_CODE_TTL_MINUTES', default=10, cast=int)
TG_CODE_MAX_ATTEMPTS = config('TG_CODE_MAX_ATTEMPTS', default=5, cast=int)
TG_CODE_RESEND_SECONDS = config('TG_CODE_RESEND_SECONDS', default=60, cast=int)

# --------------------------------------------------------------------------- #
#  Suniy intellekt (oylik tahlili)
#  Birinchi navbatda Google Gemini ishlatiladi (GEMINI_API_KEY bo'lsa),
#  bo'lmasa Anthropic Claude, u ham bo'lmasa offline (formula) rejim.
# --------------------------------------------------------------------------- #
GEMINI_API_KEY = config('GEMINI_API_KEY', default='')
GEMINI_MODEL = config('GEMINI_MODEL', default='gemini-2.5-flash')

ANTHROPIC_API_KEY = config('ANTHROPIC_API_KEY', default='')
ANTHROPIC_MODEL = config('ANTHROPIC_MODEL', default='claude-sonnet-4-5')

# --------------------------------------------------------------------------- #
#  Til, vaqt
# --------------------------------------------------------------------------- #
LANGUAGE_CODE = 'uz'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True

# Tizim 3 tilda: O'zbek, Rus, Ingliz — til almashtirgich (set_language)
from django.utils.translation import gettext_lazy as _i18n  # noqa: E402

LANGUAGES = [
    ('uz', _i18n("O'zbekcha")),
    ('ru', _i18n('Русский')),
    ('en', _i18n('English')),
]
LOCALE_PATHS = [BASE_DIR / 'locale']

# --------------------------------------------------------------------------- #
#  Statik va media fayllar
# --------------------------------------------------------------------------- #
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --------------------------------------------------------------------------- #
#  Brending
# --------------------------------------------------------------------------- #
BRAND_NAME = config('BRAND_NAME', default='Fan Lider')
BRAND_COLOR = '#D4640F'
# Markaz aloqa ma'lumotlari (botdagi "Aloqa" bo'limi uchun)
CENTER_PHONE = config('CENTER_PHONE', default='+998 90 000 00 00')
CENTER_ADDRESS = config('CENTER_ADDRESS', default='Toshkent sh.')

MESSAGE_TAGS = {
    10: 'debug', 20: 'info', 25: 'success', 30: 'warning', 40: 'danger',
}

# --------------------------------------------------------------------------- #
#  Production xavfsizligi (DEBUG=False bo'lganda yoqiladi)
# --------------------------------------------------------------------------- #
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

# Email (parolni tiklash uchun emas — faqat tizim xabarnomalari uchun)
EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend',
)
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', cast=int, default=587)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool, default=True)
# SMTP javob bermasa cheksiz osilib qolmasin (sekin tarmoq / bloklangan port).
EMAIL_TIMEOUT = config('EMAIL_TIMEOUT', cast=int, default=20)

# Telegram bot (o'quvchi kabineti havolasi + ommaviy ariza boti)
TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN', default='')
TELEGRAM_WEBHOOK_SECRET = config('TELEGRAM_WEBHOOK_SECRET', default='')
# Bot foydalanuvchi nomi (@siz), masalan: fanlider_bot — parol tiklash havolasi uchun
TELEGRAM_BOT_USERNAME = config('TELEGRAM_BOT_USERNAME', default='')
# Saytning tashqi manzili (botdagi kabinet havolasi uchun), masalan:
# https://foydalanuvchi.pythonanywhere.com
SITE_URL = config('SITE_URL', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER or 'noreply@fanlider.uz')

# --------------------------------------------------------------------------- #
#  Render.com — platforma host nomini avtomatik qo'shadi.
#  RENDER_EXTERNAL_HOSTNAME (masalan: fanlider.onrender.com) ni Render har bir
#  servisga o'zi beradi, shuning uchun ALLOWED_HOSTS/CSRF/SITE_URL ni qo'lda
#  yozish shart emas.
# --------------------------------------------------------------------------- #
RENDER_EXTERNAL_HOSTNAME = config('RENDER_EXTERNAL_HOSTNAME', default='')
if RENDER_EXTERNAL_HOSTNAME:
    if RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    _render_origin = f'https://{RENDER_EXTERNAL_HOSTNAME}'
    if _render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_render_origin)
    if not SITE_URL:
        SITE_URL = _render_origin

# --------------------------------------------------------------------------- #
#  Mobil ilova API (Flutter) — DRF + JWT + CORS
# --------------------------------------------------------------------------- #
from datetime import timedelta  # noqa: E402

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Mobil ilova istalgan manzildan ulanishi mumkin (faqat API uchun).
CORS_ALLOW_ALL_ORIGINS = config('CORS_ALLOW_ALL_ORIGINS', default=True, cast=bool)
CORS_URLS_REGEX = r'^/api/.*$'
