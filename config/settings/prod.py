"""Production settings — dérivés de base.py."""
from .base import *  # noqa: F401,F403

DEBUG = False

import os
ALLOWED_HOSTS = [h.strip() for h in os.environ.get(
    "ALLOWED_HOSTS",
    "zionpay.app,www.zionpay.app,.onrender.com"
).split(",") if h.strip()]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
