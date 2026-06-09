import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.test import Client
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse

settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver']
LC = settings.LANGUAGE_COOKIE_NAME
User = get_user_model()
admin = User.objects.filter(is_superuser=True).first() or User.objects.filter(role='admin').first()

# (url, {lang: expected_substring})
cases = [
    (reverse('dashboard:home'), {'en': 'Dashboard', 'ru': 'Панель управления'}),
    (reverse('dashboard:director'), {'en': 'Director panel', 'ru': 'Панель директора'}),
    (reverse('students:list'), {'en': 'Students', 'ru': 'Ученики'}),
    (reverse('payments:debtors'), {'en': 'Debtors', 'ru': 'Должники'}),
    (reverse('salaries:home'), {'en': 'Salary table', 'ru': 'Таблица зарплат'}),
    (reverse('accounts:settings_home'), {'en': 'Settings', 'ru': 'Настройки'}),
]
ok = fail = 0
for url, langs in cases:
    for lang, expect in langs.items():
        c = Client(); c.force_login(admin); c.cookies[LC] = lang
        r = c.get(url, follow=True)
        body = r.content.decode('utf-8', 'replace')
        if r.status_code == 200 and expect in body:
            ok += 1; print(f'OK   [{lang}] {url} -> {expect!r}')
        else:
            fail += 1; print(f'FAIL [{lang}] {url} ({r.status_code}) expected {expect!r}')
print(f'\nCONTENT TEST: ok={ok} fail={fail}')
