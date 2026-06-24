from pathlib import Path
import os

try:
    import pymysql
    pymysql.install_as_MySQLdb()
except Exception:  # pragma: no cover - mysql driver may be absent in pure unit tests
    pass

BASE_DIR = Path(__file__).resolve().parents[1]
SECRET_KEY = os.environ.get("SMART_ASSEMBLY_DJANGO_SECRET", "dev-smart-assembly-dashboard")
DEBUG = os.environ.get("SMART_ASSEMBLY_DJANGO_DEBUG", "1") != "0"
ALLOWED_HOSTS = os.environ.get("SMART_ASSEMBLY_ALLOWED_HOSTS", "127.0.0.1,localhost,0.0.0.0").split(",")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "dashboard_backend.operations",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]
ROOT_URLCONF = "dashboard_backend.urls"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "Asia/Seoul"

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "web" / "dist" / "assets"] if (BASE_DIR / "web" / "dist" / "assets").exists() else []

if os.environ.get("SMART_ASSEMBLY_DB_BACKEND", "mysql").lower() == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "smart_assembly_dashboard.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.environ.get("SMART_ASSEMBLY_DB_NAME", "smart_assembly_transport"),
            "USER": os.environ.get("SMART_ASSEMBLY_DB_USER", "smart_assembly"),
            "PASSWORD": os.environ.get("SMART_ASSEMBLY_DB_PASSWORD", "smart_assembly"),
            "HOST": os.environ.get("SMART_ASSEMBLY_DB_HOST", "127.0.0.1"),
            "PORT": os.environ.get("SMART_ASSEMBLY_DB_PORT", "3306"),
            "OPTIONS": {"charset": "utf8mb4"},
        }
    }
