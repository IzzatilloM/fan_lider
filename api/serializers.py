"""Mobil ilova (Flutter) uchun DRF serializerlari.

Maqsad: platformadagi o'quvchi kabineti va o'qituvchi paneli ko'rsatadigan
ma'lumotlarni mobil ilovaga aynan o'sha shaklda yetkazish.
"""
from rest_framework import serializers

from accounts.models import CustomUser
from courses.models import Course
from enrollments.models import Enrollment
from instructors.models import Instructor
from monitoring.models import Assessment, Attendance, Lesson
from payments.models import Invoice, Payment
from students.models import Student


def _abs_url(request, file_field):
    """ImageField uchun to'liq (absolyut) URL — mobil ilova ochishi uchun."""
    if not file_field:
        return ''
    try:
        url = file_field.url
    except ValueError:
        return ''
    if request is not None:
        return request.build_absolute_uri(url)
    return url


# --------------------------------------------------------------------------- #
#  Foydalanuvchi / auth
# --------------------------------------------------------------------------- #
class UserSerializer(serializers.ModelSerializer):
    """Kirgan foydalanuvchi haqida umumiy ma'lumot (rolga qarab panel tanlanadi)."""

    display_name = serializers.CharField(read_only=True)
    initials = serializers.CharField(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    avatar = serializers.SerializerMethodField()
    has_student_profile = serializers.SerializerMethodField()
    has_instructor_profile = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'display_name', 'initials', 'role', 'role_display', 'phone',
            'avatar', 'is_verified', 'must_change_password',
            'has_student_profile', 'has_instructor_profile',
        ]

    def get_avatar(self, obj):
        request = self.context.get('request')
        if obj.avatar:
            return _abs_url(request, obj.avatar)
        return obj.google_picture or ''

    def get_has_student_profile(self, obj):
        return hasattr(obj, 'student_profile') and obj.student_profile is not None

    def get_has_instructor_profile(self, obj):
        return hasattr(obj, 'instructor_profile') and obj.instructor_profile is not None


# --------------------------------------------------------------------------- #
#  O'quv tarkibi (kurs / guruh)
# --------------------------------------------------------------------------- #
class SubjectMiniSerializer(serializers.Serializer):
    name = serializers.CharField()
    color = serializers.CharField()
    icon = serializers.CharField()


class CourseSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', default='', read_only=True)
    subject_color = serializers.CharField(source='subject.color', default='#D4640F', read_only=True)
    subject_icon = serializers.CharField(source='subject.icon', default='📘', read_only=True)
    teacher_name = serializers.CharField(source='teacher.full_name', default='', read_only=True)
    weekdays_display = serializers.CharField(source='get_weekdays_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    students_count = serializers.IntegerField(source='active_students_count', read_only=True)
    start_time = serializers.TimeField(format='%H:%M', read_only=True)

    class Meta:
        model = Course
        fields = [
            'id', 'name', 'slug', 'level', 'subject_name', 'subject_color',
            'subject_icon', 'teacher_name', 'monthly_fee', 'weekdays',
            'weekdays_display', 'start_time', 'room', 'status', 'status_display',
            'students_count', 'capacity',
        ]


# --------------------------------------------------------------------------- #
#  Baho / davomat / to'lov
# --------------------------------------------------------------------------- #
class AssessmentSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name', default='', read_only=True)
    subject_icon = serializers.CharField(source='course.subject.icon', default='📘', read_only=True)
    subject_color = serializers.CharField(source='course.subject.color', default='#D4640F', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    grade_5 = serializers.IntegerField(read_only=True)
    badge_class = serializers.CharField(read_only=True)

    class Meta:
        model = Assessment
        fields = [
            'id', 'course_name', 'subject_icon', 'subject_color', 'type',
            'type_display', 'title', 'date', 'score', 'max_score',
            'percentage', 'grade_5', 'badge_class', 'comment',
        ]


class AttendanceSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name', default='', read_only=True)
    subject_icon = serializers.CharField(source='course.subject.icon', default='📘', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Attendance
        fields = [
            'id', 'course_name', 'subject_icon', 'date', 'status',
            'status_display', 'note',
        ]


class PaymentSerializer(serializers.ModelSerializer):
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    course_name = serializers.CharField(source='invoice.course.name', default='', read_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'amount', 'method', 'method_display', 'paid_at', 'course_name', 'note']


class InvoiceSerializer(serializers.ModelSerializer):
    month_name = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    course_name = serializers.CharField(source='course.name', default='', read_only=True)
    remaining = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'year', 'month', 'month_name', 'amount', 'paid_amount',
            'remaining', 'due_date', 'status', 'status_display', 'course_name',
            'is_overdue',
        ]


# --------------------------------------------------------------------------- #
#  Yozilish (enrollment)
# --------------------------------------------------------------------------- #
class EnrollmentSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    net_fee = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            'id', 'course', 'monthly_fee', 'discount_percent', 'net_fee',
            'start_date', 'status', 'status_display',
        ]


# --------------------------------------------------------------------------- #
#  Profil (o'quvchi / o'qituvchi)
# --------------------------------------------------------------------------- #
class StudentProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    initials = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    photo = serializers.SerializerMethodField()
    is_debtor = serializers.BooleanField(read_only=True)
    debt_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Student
        fields = [
            'id', 'first_name', 'last_name', 'middle_name', 'full_name',
            'initials', 'phone', 'parent_phone', 'email', 'gender',
            'birth_date', 'address', 'school_name', 'grade', 'photo',
            'status', 'status_display', 'balance', 'is_debtor', 'debt_amount',
        ]

    def get_photo(self, obj):
        return _abs_url(self.context.get('request'), obj.photo)


class InstructorProfileSerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()
    active_groups = serializers.IntegerField(read_only=True)

    class Meta:
        model = Instructor
        fields = [
            'id', 'full_name', 'phone', 'email', 'specialty',
            'experience_years', 'salary', 'bio', 'photo', 'is_active',
            'active_groups',
        ]

    def get_photo(self, obj):
        request = self.context.get('request')
        if obj.image:
            return _abs_url(request, obj.image)
        if obj.user and obj.user.google_picture:
            return obj.user.google_picture
        return ''


# --------------------------------------------------------------------------- #
#  Profilni tahrirlash (mobil ilova — o'quvchi/o'qituvchi o'zi yangilaydi)
# --------------------------------------------------------------------------- #
class StudentProfileUpdateSerializer(serializers.ModelSerializer):
    """O'quvchi o'z profilini tahrirlaydi. Faqat shaxsiy maydonlar yoziladi.

    `photo` — rasm yuklash (multipart/form-data). Holat/balans kabi maydonlar
    bu yerda yo'q (faqat admin o'zgartiradi).
    """

    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'middle_name', 'phone', 'parent_phone',
            'email', 'gender', 'birth_date', 'address', 'school_name', 'grade',
            'photo',
        ]
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
        }


class InstructorProfileUpdateSerializer(serializers.ModelSerializer):
    """O'qituvchi o'z profilini tahrirlaydi. Oylik/faollik bu yerda yo'q."""

    class Meta:
        model = Instructor
        fields = [
            'full_name', 'phone', 'email', 'specialty', 'experience_years',
            'bio', 'image',
        ]
        extra_kwargs = {
            'full_name': {'required': False},
        }


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['id', 'date', 'topic', 'description', 'homework']


class StudentMiniSerializer(serializers.ModelSerializer):
    """O'qituvchi guruhidagi o'quvchilar ro'yxati uchun ixcham serializer."""

    full_name = serializers.CharField(read_only=True)
    initials = serializers.CharField(read_only=True)
    photo = serializers.SerializerMethodField()
    average_score = serializers.SerializerMethodField()
    attendance_percentage = serializers.IntegerField(read_only=True)

    class Meta:
        model = Student
        fields = [
            'id', 'full_name', 'initials', 'phone', 'photo', 'status',
            'balance', 'average_score', 'attendance_percentage',
        ]

    def get_photo(self, obj):
        return _abs_url(self.context.get('request'), obj.photo)

    def get_average_score(self, obj):
        return float(obj.average_score)
