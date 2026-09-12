"""
Configuração WSGI do projecto FenixSchool.

Expõe a callable WSGI como a variável de nível de módulo ``application``.

Ver: https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")

application = get_wsgi_application()
