import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.test import Client
from django.conf import settings
from django.contrib.auth import get_user_model

settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver']
LANG_COOKIE = settings.LANGUAGE_COOKIE_NAME
User = get_user_model()

admin = User.objects.filter(is_superuser=True).first() or \
        User.objects.filter(role='admin').first() or \
        User.objects.filter(is_staff=True).first()
if not admin:
    print('No admin/staff user in DB — skipping authenticated render test.')
    raise SystemExit(0)

print('Using user:', admin.username, '(role=%s)' % getattr(admin, 'role', '?'))

pages = ['/', '/students/', '/courses/', '/payments/', '/salaries/', '/instructors/',
         '/monitoring/', '/registration/', '/accounts/users/', '/accounts/settings/']

for lang in ('en', 'ru'):
    c = Client()
    c.force_login(admin)
    c.cookies[LANG_COOKIE] = lang
    print(f'\n=== lang={lang} ===')
    for url in pages:
        try:
            r = c.get(url, follow=True)
            print(f'  {url:24} -> {r.status_code}')
        except Exception as e:
            print(f'  {url:24} -> EXCEPTION {type(e).__name__}: {e}')
