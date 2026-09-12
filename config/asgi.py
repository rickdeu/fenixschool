"""
Configuração ASGI do projecto FenixSchool.

Expõe a callable ASGI como a variável de nível de módulo ``application``.

Ver: https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")

application = get_asgi_application()
