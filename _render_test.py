import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.test import Client
from django.conf import settings

settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver']
LANG_COOKIE = settings.LANGUAGE_COOKIE_NAME  # 'django_language'

checks = {
    'uz': {'/accounts/login/': "Tizimga kirish", '/registration/apply/': "Ro'yxatdan o'tish arizasi"},
    'en': {'/accounts/login/': "Sign in to the system", '/registration/apply/': "Registration application"},
    'ru': {'/accounts/login/': "Вход в систему", '/registration/apply/': "Заявка на регистрацию"},
}

ok = 0
fail = 0
for lang, urls in checks.items():
    c = Client()
    c.cookies[LANG_COOKIE] = lang
    for url, expect in urls.items():
        r = c.get(url)
        body = r.content.decode('utf-8', 'replace')
        status = r.status_code
        found = expect in body
        if status == 200 and found:
            ok += 1
            print(f'OK   [{lang}] {url} ({status}) contains: {expect!r}')
        else:
            fail += 1
            print(f'FAIL [{lang}] {url} ({status}) expected {expect!r} found={found}')
print(f'\nRENDER TEST: ok={ok} fail={fail}')
