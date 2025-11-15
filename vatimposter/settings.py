"""
Django settings for vatimposter project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Configurar ALLOWED_HOSTS
# Por padrão, aceitar todos os hosts (seguro no Railway que gerencia a segurança)
# Se ALLOWED_HOSTS estiver definido explicitamente nas variáveis de ambiente, usar ele
allowed_hosts_env = os.environ.get('ALLOWED_HOSTS', '').strip()

# Sempre aceitar todos os hosts por padrão (Railway gerencia a segurança)
ALLOWED_HOSTS = ['*']

# Se ALLOWED_HOSTS foi definido explicitamente e não está vazio, usar ele
if allowed_hosts_env and allowed_hosts_env != '' and allowed_hosts_env != '*':
    hosts_list = [host.strip() for host in allowed_hosts_env.split(',') if host.strip()]
    if hosts_list:
        ALLOWED_HOSTS = hosts_list


# Application definition

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'game',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Para servir arquivos estáticos em produção
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'vatimposter.urls'

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

WSGI_APPLICATION = 'vatimposter.wsgi.application'
ASGI_APPLICATION = 'vatimposter.asgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

# Configuração do banco de dados
# Railway fornece variáveis específicas para PostgreSQL
# Tentar usar variáveis do Railway primeiro, depois variáveis customizadas
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('PGDATABASE') or os.environ.get('DB_NAME', 'vatimposter'),
        'USER': os.environ.get('PGUSER') or os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('PGPASSWORD') or os.environ.get('DB_PASSWORD', 'postgres'),
        'HOST': os.environ.get('PGHOST') or os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('PGPORT') or os.environ.get('DB_PORT', '5432'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'  # Para produção

# WhiteNoise para servir arquivos estáticos em produção
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Channels configuration - Usando InMemoryChannelLayer para servidor único
# Em produção no Railway, ainda funciona com um servidor
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    },
}

