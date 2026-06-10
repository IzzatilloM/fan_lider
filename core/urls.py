"""Fan Lider CRM — asosiy URL konfiguratsiyasi."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from . import diag  # VAQTINCHALIK diagnostika (keyin olib tashlanadi)

urlpatterns = [
    path('admin/', admin.site.urls),

    # VAQTINCHALIK: Render'dagi xatolikni aniqlash uchun (diagnostika tugagach o'chiriladi)
    path('__diag__/<str:token>/', diag.run_diag),

    # Til almashtirish (set_language) — O'zbek / Rus / Ingliz
    path('i18n/', include('django.conf.urls.i18n')),

    # Mobil ilova (Flutter) API — JWT auth, o'quvchi/o'qituvchi paneli
    path('api/', include('api.urls')),

    # Hisob sahifalari: ro'yxatdan o'tish, tasdiqlash kodi, kirish, profil
    path('accounts/', include('accounts.urls')),

    # O'quvchi shaxsiy kabineti
    path('cabinet/', include('cabinet.urls')),

    # Asosiy modullar
    path('', include('dashboard.urls')),
    path('courses/', include('courses.urls')),
    path('students/', include('students.urls')),
    path('instructors/', include('instructors.urls')),
    path('registration/', include('enrollments.urls')),
    path('payments/', include('payments.urls')),
    path('monitoring/', include('monitoring.urls')),
    path('salaries/', include('salaries.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
