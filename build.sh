#!/usr/bin/env bash
# Render.com build skripti — har bir deployda ishga tushadi.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

# Superuser (faqat env'da DJANGO_SUPERUSER_* berilgan bo'lsa).
# Foydalanuvchi allaqachon mavjud bo'lsa — xatosiz o'tkazib yuboriladi.
if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
  python manage.py createsuperuser --noinput || true
fi
