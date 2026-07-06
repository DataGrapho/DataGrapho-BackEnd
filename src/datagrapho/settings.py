"""Django settings for datagrapho project."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-e9&$42kn^5kt$(l)@het&r(0=3i(9qgpb*u$88ssd24=#k+26z",
)

# Ambiente de produção deve falhar fechado: habilite DEBUG apenas de forma
# explícita no ambiente local.
DEBUG = os.getenv("DEBUG", "False") == "True"

allowed_hosts_env = os.getenv("ALLOWED_HOSTS", "pendengas.com.br,localhost,127.0.0.1")
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(",") if host.strip()]


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    'corsheaders',
    'accounts',
    'catalogo_depara',
    'depara',
    'chatbot',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "datagrapho.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [PROJECT_ROOT / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "datagrapho.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.getenv("DB_NAME", str(PROJECT_ROOT / "db.sqlite3")),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", ""),
        "PORT": os.getenv("DB_PORT", ""),
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Cache configuration for chatbot session storage
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'chatbot-cache',
        'OPTIONS': {
            'MAX_ENTRIES': 1000
        }
    }
}


LANGUAGE_CODE = os.getenv('LANGUAGE_CODE', 'pt-br')
TIME_ZONE = os.getenv('TIME_ZONE', 'America/Sao_Paulo')
USE_I18N = True
USE_TZ = True


STATIC_URL = "/static/"
STATIC_ROOT = PROJECT_ROOT / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = PROJECT_ROOT / "media"


DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

AUTH_USER_MODEL = "accounts.Usuario"


REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": int(os.getenv("PAGE_SIZE", "100")),
    "DEFAULT_FILTER_BACKENDS": [
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    'DEFAULT_THROTTLE_RATES': {
        'chatbot': f"{int(os.getenv('CHATBOT_RATE_LIMIT', '10'))}/min",
    }
}


SIMPLE_JWT = {
    "USER_ID_FIELD": "id_usuario",
}


CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "https://pendengas.com.br").split(",")
    if origin.strip()
]

CORS_ALLOWED_ORIGIN_REGEXES = [
    regex.strip()
    for regex in os.getenv("CORS_ALLOWED_ORIGIN_REGEXES", "").split(",")
    if regex.strip()
]

CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "True") == "True"

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", ",".join(CORS_ALLOWED_ORIGINS)).split(",")
    if origin.strip()
]

PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES = int(
    os.getenv("PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES", "30")
)
FRONTEND_PASSWORD_RESET_URL = os.getenv(
    "FRONTEND_PASSWORD_RESET_URL",
    "https://pendengas.com.br/reset-password?token={token}",
)

# Email configuration
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")

# Chatbot Configuration
CHATBOT_CONFIG = {
    # Active domains - add 'hr', 'sales', etc. to enable multiple domains
    'ACTIVE_DOMAINS': os.getenv('CHATBOT_ACTIVE_DOMAINS', 'wine').split(','),
    
    # AI Provider settings (generic)
    'AI_PROVIDER': os.getenv('AI_PROVIDER', 'gemini').lower(),
    'AI_API_KEY': os.getenv('AI_API_KEY', ''),
    'AI_MODEL': os.getenv('AI_MODEL', 'gemini-1.5-flash'),
    'AI_BASE_URL': os.getenv('AI_BASE_URL', None),  # For LM Studio, Ollama, etc.
    'AI_TIMEOUT': int(os.getenv('AI_TIMEOUT', '30')),
    'AI_MAX_RETRIES': int(os.getenv('AI_MAX_RETRIES', '3')),
    
    # Execution settings
    'MAX_TOOL_CALLS_PER_QUESTION': int(os.getenv('MAX_TOOL_CALLS_PER_QUESTION', '5')),
    'AI_TEMPERATURE': float(os.getenv('AI_TEMPERATURE', '0.0')),
    
    # Rate limiting and caching
    'RATE_LIMIT': int(os.getenv('CHATBOT_RATE_LIMIT', '10')),
    'CACHE_TTL': int(os.getenv('CHATBOT_CACHE_TTL', '300')),
    
    # Session management
    'SESSION_EXPIRY': int(os.getenv('CHATBOT_SESSION_EXPIRY', '3600')),
}


# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'chatbot': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@datagrapho.local")
