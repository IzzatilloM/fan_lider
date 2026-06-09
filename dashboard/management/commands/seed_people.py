"""50 ta o'quvchi + 30 ta o'qituvchi (va bir nechta guruh) qo'shadi.

Foydalanish:
  python manage.py seed_people
  python manage.py seed_people --students 50 --teachers 30
"""
import random
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from courses.models import Course, Subject
from enrollments.models import Enrollment
from instructors.models import Instructor
from students.models import Student

User = get_user_model()

FIRST_M = ["Aziz", "Bekzod", "Jasur", "Sardor", "Akmal", "Bobur", "Diyor", "Eldor",
           "Farrux", "G'olib", "Hasan", "Islom", "Javlon", "Kamol", "Laziz", "Murod",
           "Nodir", "Otabek", "Qodir", "Rustam", "Sanjar", "Tohir", "Ulug'bek", "Valijon",
           "Shoxrux", "Yusuf", "Zafar", "Asror", "Behruz", "Doston"]
FIRST_F = ["Aziza", "Barno", "Dilnoza", "Feruza", "Gulnora", "Hilola", "Iroda", "Kamola",
           "Lola", "Madina", "Nilufar", "Oysha", "Ra'no", "Sevara", "Shahnoza", "Umida",
           "Zarina", "Malika", "Nigora", "Yulduz"]
LAST = ["Aliyev", "Karimov", "Rashidov", "Yusupov", "Tursunov", "Sobirov", "Ergashev",
        "Qodirov", "Mirzayev", "Saidov", "Umarov", "Xolmatov", "Nazarov", "Ibragimov",
        "Sharipov", "Toshpo'latov", "Yo'ldoshev", "Abdullayev", "Rahimov", "Hasanov",
        "Jo'rayev", "Madaliyev", "Norqulov", "Otajonov", "Pardayev"]
SPECIALTIES = ["Ingliz tili", "Matematika", "Fizika", "Kimyo", "Biologiya", "Ona tili",
               "Tarix", "Informatika", "Rus tili", "Geografiya"]
LEVELS = ["Beginner", "Elementary", "Pre-Intermediate", "Intermediate", "Upper-Intermediate",
          "A1", "A2", "B1", "B2"]
WEEKDAYS = ['mon_wed_fri', 'tue_thu_sat']


def _phone():
    return "+99890" + "".join(random.choice("0123456789") for _ in range(7))


def _last(name):
    return random.choice(LAST)


class Command(BaseCommand):
    help = "Namuna o'quvchi va o'qituvchilar qo'shadi"

    def add_arguments(self, parser):
        parser.add_argument('--students', type=int, default=50)
        parser.add_argument('--teachers', type=int, default=30)

    def handle(self, *args, **opts):
        random.seed()
        n_students = opts['students']
        n_teachers = opts['teachers']

        # --- Yo'nalishlar (fanlar) ---
        icons = {'Ingliz tili': '🇬🇧', 'Matematika': '📐', 'Fizika': '🔬', 'Kimyo': '⚗️',
                 'Biologiya': '🧬', 'Ona tili': '📖', 'Tarix': '🏛️', 'Informatika': '💻',
                 'Rus tili': '🇷🇺', 'Geografiya': '🌍'}
        subjects = []
        for s in SPECIALTIES:
            subj, _ = Subject.objects.get_or_create(
                name=s, defaults={'icon': icons.get(s, '📘')}
            )
            subjects.append(subj)

        # --- O'qituvchilar (umumiy son n_teachers ga yetguncha) ---
        existing_t = Instructor.objects.count()
        to_add_t = max(n_teachers - existing_t, 0)
        added_t = 0
        for i in range(to_add_t):
            male = random.random() < 0.6
            fn = random.choice(FIRST_M if male else FIRST_F)
            ln = random.choice(LAST)
            full = f"{fn} {ln}"
            base = (slugify(f"{fn}{ln}") or 'teacher').replace('-', '')[:18]
            username = base
            k = 1
            while User.objects.filter(username=username).exists():
                k += 1
                username = f"{base}{k}"
            u = User.objects.create_user(username=username, role='teacher',
                                         first_name=fn, last_name=ln)
            u.set_unusable_password()
            u.save()
            # Signal avtomatik instructor_profile yaratgan bo'lishi mumkin
            u.refresh_from_db()
            ins = getattr(u, 'instructor_profile', None) or Instructor(user=u)
            ins.full_name = full
            ins.phone = _phone()
            ins.specialty = random.choice(SPECIALTIES)
            ins.experience_years = random.randint(1, 15)
            ins.salary = Decimal(random.randint(3, 9) * 1_000_000)
            ins.is_active = True
            ins.save()
            added_t += 1
        teachers = list(Instructor.objects.all())
        self.stdout.write(self.style.SUCCESS(f"{added_t} o'qituvchi qo'shildi (jami {len(teachers)})."))

        # --- Guruhlar (har fan uchun 1-2 ta) ---
        all_courses = list(Course.objects.all())
        if len(all_courses) < 8:
            for subj in subjects:
                for _ in range(random.randint(1, 2)):
                    tt = random.choice(teachers) if teachers else None
                    h = random.choice([9, 10, 14, 16, 18])
                    c = Course.objects.create(
                        name=f"{subj.name} — {random.choice(['ertalabki','kunduzgi','kechki'])} guruh",
                        subject=subj,
                        level=random.choice(LEVELS) if subj.name in ('Ingliz tili', 'Rus tili') else '',
                        teacher=tt,
                        monthly_fee=Decimal(random.randint(30, 60) * 10000),
                        duration_months=random.choice([3, 4, 6]),
                        capacity=random.randint(10, 18),
                        weekdays=random.choice(WEEKDAYS),
                        start_time=f"{h:02d}:00",
                        status=random.choice(['recruiting', 'ongoing', 'ongoing']),
                    )
                    all_courses.append(c)
        self.stdout.write(self.style.SUCCESS(f"Jami guruhlar: {len(all_courses)}"))

        # --- O'quvchilar (umumiy son n_students ga yetguncha) ---
        to_add_s = max(n_students - Student.objects.count(), 0)
        created = 0
        for i in range(to_add_s):
            male = random.random() < 0.55
            fn = random.choice(FIRST_M if male else FIRST_F)
            ln = random.choice(LAST)
            st = Student.objects.create(
                first_name=fn, last_name=ln, phone=_phone(),
                parent_phone=_phone(),
                gender='male' if male else 'female',
                status='active',
                balance=Decimal(random.choice([0, 0, 0, -300000, -450000, 200000])),
            )
            # 1-2 ta guruhga yozish
            for c in random.sample(all_courses, k=min(len(all_courses), random.randint(1, 2))):
                Enrollment.objects.get_or_create(
                    student=st, course=c,
                    defaults={'monthly_fee': c.monthly_fee},
                )
            created += 1
        self.stdout.write(self.style.SUCCESS(f"{created} o'quvchi qo'shildi (jami {Student.objects.count()})."))
        self.stdout.write(self.style.SUCCESS("Tayyor."))
