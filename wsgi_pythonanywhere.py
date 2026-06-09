# ===================================================================
#  PythonAnywhere WSGI konfiguratsiyasi
#  Web tab -> Code -> WSGI configuration file ichidagi MATNNI
#  to'liq o'chirib, quyidagini joylashtiring.
#  <YOURUSERNAME> ni o'z PythonAnywhere foydalanuvchi nomingizga almashtiring.
# ===================================================================
import os
import sys

# Loyiha papkasi yo'li
path = '/home/<YOURUSERNAME>/Fan_lider_CRM'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
