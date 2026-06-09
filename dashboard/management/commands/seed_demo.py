"""Demo ma'lumotlar bilan to'ldirish: python manage.py seed_demo"""
import datetime
import random

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "O'quv markazi uchun namunaviy demo ma'lumotlarni yaratadi."

    def handle(self, *args, **options):
        from courses.models import Course, Subject
        from enrollments.models import Enrollment, RegistrationApplication
        from instructors.models import Instructor
        from monitoring.models import Assessment, Attendance, Lesson
        from payments.models import Invoice, Payment
        from students.models import Student
        from django.contrib.auth import get_user_model

        User = get_user_model()
        now = timezone.now()

        teacher, _ = User.objects.get_or_create(
            username='ustoz_aziz',
            defaults={'email': 'aziz@fanlider.uz', 'first_name': 'Aziz', 'last_name': 'Karimov'},
        )
        teacher.role = 'teacher'
        teacher.save()
        ins = Instructor.objects.get(user=teacher)
        ins.specialty = 'Matematika'
        ins.experience_years = 6
        ins.salary = 5000000
        ins.save()

        subjects = {}
        for name, icon, color in [
            ('Matematika', '🧮', '#D4640F'), ('Ingliz tili', '🇬🇧', '#2563eb'),
            ('Fizika', '⚛️', '#1f9d55'), ('Ona tili', '📖', '#9333ea'),
        ]:
            subjects[name], _ = Subject.objects.get_or_create(
                name=name, defaults={'icon': icon, 'color': color})

        courses = []
        for nm, subj, fee, status, hour in [
            ('Matematika A1', 'Matematika', 400000, 'recruiting', 15),
            ('Ingliz tili Beginner', 'Ingliz tili', 350000, 'ongoing', 17),
            ('Fizika Intensiv', 'Fizika', 450000, 'ongoing', 16),
        ]:
            c, _ = Course.objects.get_or_create(
                name=nm,
                defaults={'subject': subjects[subj], 'teacher': ins, 'monthly_fee': fee,
                          'capacity': 12, 'status': status, 'start_time': datetime.time(hour, 0)},
            )
            courses.append(c)

        names = [('Ali', 'Valiyev'), ('Laylo', 'Tosheva'), ('Bobur', 'Aliyev'),
                 ('Madina', 'Yusupova'), ('Sardor', 'Rashidov'), ('Diyora', 'Qodirova'),
                 ('Jasur', 'Ne\'matov'), ('Malika', 'Saidova')]
        students = []
        for fn, ln in names:
            s, _ = Student.objects.get_or_create(
                first_name=fn, last_name=ln,
                defaults={'phone': '+99890' + str(random.randint(1000000, 9999999)),
                          'parent_phone': '+99893' + str(random.randint(1000000, 9999999)),
                          'status': 'active', 'grade': f"{random.randint(7,11)}-sinf"},
            )
            students.append(s)

        for i, s in enumerate(students):
            Enrollment.objects.get_or_create(
                student=s, course=courses[i % len(courses)],
                defaults={'monthly_fee': courses[i % len(courses)].monthly_fee})

        for en in Enrollment.objects.filter(status='active'):
            Invoice.objects.get_or_create(
                student=en.student, enrollment=en, year=now.year, month=now.month,
                defaults={'amount': en.net_fee, 'course': en.course, 'due_date': now.date()})

        for s in students[:5]:
            Payment.objects.get_or_create(
                student=s, amount=s.enrollments.first().net_fee if s.enrollments.exists() else 400000,
                defaults={'method': random.choice(['cash', 'card', 'click']), 'paid_at': now})

        for c in courses:
            Lesson.objects.get_or_create(
                course=c, date=now.date(), topic='Kirish darsi', defaults={'homework': '1-mashq'})
            for en in c.enrollments.filter(status='active'):
                Attendance.objects.get_or_create(
                    student=en.student, course=c, date=now.date(),
                    defaults={'status': random.choice(['present', 'present', 'late', 'absent'])})
                Assessment.objects.get_or_create(
                    student=en.student, course=c, type='exam', title='Nazorat ishi', date=now.date(),
                    defaults={'score': random.randint(55, 100), 'max_score': 100})

        for fn, phone, subj, src, st in [
            ('Jasur Tursunov', '+998901112233', 'Matematika', 'instagram', 'new'),
            ('Nilufar Abdullayeva', '+998905556677', 'Ingliz tili', 'telegram', 'contacted'),
            ('Otabek Yunusov', '+998907778899', 'Fizika', 'friend', 'new'),
        ]:
            RegistrationApplication.objects.get_or_create(
                full_name=fn, phone=phone,
                defaults={'subject': subjects[subj], 'source': src, 'status': st})

        self.stdout.write(self.style.SUCCESS(
            f"Demo tayyor: {Student.objects.count()} o'quvchi, {Course.objects.count()} guruh, "
            f"{Payment.objects.count()} to'lov, {RegistrationApplication.objects.count()} ariza."))
