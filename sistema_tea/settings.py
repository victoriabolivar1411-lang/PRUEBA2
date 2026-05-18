"""
=============================================================================
SISTEMA EXPERTO PARA APOYO PEDAGÓGICO EN TEA
=============================================================================
Archivo: settings.py
Descripción: Configuración principal del proyecto Django.
             Incluye configuración de media files (Pillow/imágenes),
             correo electrónico y autenticación.
=============================================================================
"""

from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# RUTAS BASE
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent


# ─────────────────────────────────────────────────────────────────────────────
# SEGURIDAD
# ─────────────────────────────────────────────────────────────────────────────
SECRET_KEY = 'django-insecure-tea-sistema-experto-2024-proyecto-grado-sistemas'
DEBUG = True
ALLOWED_HOSTS = ['*']


# ─────────────────────────────────────────────────────────────────────────────
# APLICACIONES
# ─────────────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # App del Sistema Experto TEA
    'experto',
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

ROOT_URLCONF = 'sistema_tea.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],   # Templates globales (para password reset)
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

WSGI_APPLICATION = 'sistema_tea.wsgi.application'


# ─────────────────────────────────────────────────────────────────────────────
# BASE DE DATOS
# ─────────────────────────────────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ─────────────────────────────────────────────────────────────────────────────
# VALIDACIÓN DE CONTRASEÑAS
# ─────────────────────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ─────────────────────────────────────────────────────────────────────────────
# INTERNACIONALIZACIÓN
# ─────────────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True


# ─────────────────────────────────────────────────────────────────────────────
# AUTENTICACIÓN — Redirecciones
# ─────────────────────────────────────────────────────────────────────────────
LOGIN_URL           = '/login/'
LOGIN_REDIRECT_URL  = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'


# ─────────────────────────────────────────────────────────────────────────────
# ARCHIVOS ESTÁTICOS
# ─────────────────────────────────────────────────────────────────────────────
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'


# ─────────────────────────────────────────────────────────────────────────────
# ARCHIVOS MEDIA (fotos carnet con Pillow)
# ─────────────────────────────────────────────────────────────────────────────
MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE CORREO ELECTRÓNICO
# ─────────────────────────────────────────────────────────────────────────────

# ── ACTIVO: Consola (desarrollo) ──────────────────────────────────────────────
# El código aparece en la terminal del servidor. Funciona sin configuración.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ── PARA ENVÍO REAL: Gmail SMTP ───────────────────────────────────────────────
# 1. Activa verificación en 2 pasos en tu cuenta Google
# 2. Ve a: Cuenta Google → Seguridad → Contraseñas de aplicaciones
# 3. Genera una contraseña de 16 caracteres y reemplaza los valores abajo
# 4. Comenta EMAIL_BACKEND de arriba y descomenta las líneas de abajo:
#
# EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST          = 'smtp.gmail.com'
# EMAIL_PORT          = 587
# EMAIL_USE_TLS       = True
# EMAIL_HOST_USER     = 'leonardooliverosv@gmail.com'
# EMAIL_HOST_PASSWORD = 'xxxx xxxx xxxx xxxx'   # ← Contraseña de app de Google

DEFAULT_FROM_EMAIL   = 'Sistema Experto TEA <noreply@sistema-tea.edu>'
EMAIL_SUBJECT_PREFIX = '[TEA] '
