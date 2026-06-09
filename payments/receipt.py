"""To'lov cheki — professional PDF generatsiya (reportlab).

Chekda: o'quvchi, kurs, oy, sana/vaqt, o'qituvchi, summa, to'lov turi +
markazning yumaloq pechati (real ko'rinish) + elektron imzo + QR kod.
Pechat va imzo vektor (placeholder) — keyin haqiqiy rasmga almashtirsa bo'ladi.
"""
import io
from datetime import datetime

from django.conf import settings
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

BRAND = HexColor('#D4640F')
INK = HexColor('#1d2230')
MUTED = HexColor('#8a91a4')
LINE = HexColor('#e3e6ee')
SEAL = HexColor('#1f6f8b')   # pechat rangi (ko'k-yashil)
SIGN = HexColor('#13407a')   # imzo siyohi

UZB_MONTHS = [
    "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
    "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr",
]


def _draw_seal(c, cx, cy, r, center_name):
    """Markazning yumaloq rasmiy pechatini chizadi (real ko'rinish)."""
    c.saveState()
    c.setLineWidth(1.6)
    c.setStrokeColor(SEAL)
    c.setFillColor(SEAL)
    # Tashqi va ichki halqalar
    c.circle(cx, cy, r, stroke=1, fill=0)
    c.circle(cx, cy, r - 3, stroke=1, fill=0)
    c.circle(cx, cy, r - 16, stroke=1, fill=0)

    # Aylana bo'ylab matn (yuqori yoy — nom, past yoy — shior)
    top_text = center_name.upper()
    bottom_text = "O'QUV MARKAZI • RASMIY"
    c.setFont('Helvetica-Bold', 6.4)
    n = len(top_text)
    import math
    span = 150  # gradus
    start = 90 + span / 2
    rr = r - 9
    for i, ch in enumerate(top_text):
        ang = math.radians(start - (span * (i / max(n - 1, 1))))
        x = cx + rr * math.cos(ang)
        y = cy + rr * math.sin(ang)
        c.saveState()
        c.translate(x, y)
        c.rotate(math.degrees(ang) - 90)
        c.drawCentredString(0, 0, ch)
        c.restoreState()
    n2 = len(bottom_text)
    start2 = 270 - span / 2
    for i, ch in enumerate(bottom_text):
        ang = math.radians(start2 + (span * (i / max(n2 - 1, 1))))
        x = cx + rr * math.cos(ang)
        y = cy + rr * math.sin(ang)
        c.saveState()
        c.translate(x, y)
        c.rotate(math.degrees(ang) + 90)
        c.drawCentredString(0, 0, ch)
        c.restoreState()

    # Markaziy yulduz + "FL"
    c.setFont('Helvetica-Bold', 13)
    c.drawCentredString(cx, cy + 1, "FL")
    c.setFont('Helvetica', 5)
    c.drawCentredString(cx, cy - 8, "★ CRM ★")
    c.restoreState()


def _draw_signature(c, x, y):
    """Qo'lda yozilgandek elektron imzo (bezier chiziqlar)."""
    c.saveState()
    c.setStrokeColor(SIGN)
    c.setLineWidth(1.4)
    p = c.beginPath()
    p.moveTo(x, y)
    p.curveTo(x + 6, y + 16, x + 12, y - 12, x + 20, y + 6)
    p.curveTo(x + 26, y + 18, x + 30, y - 8, x + 38, y + 4)
    p.curveTo(x + 46, y + 14, x + 52, y - 6, x + 62, y + 10)
    c.drawPath(p, stroke=1, fill=0)
    # tag chiziq
    c.setLineWidth(1.0)
    c.line(x - 2, y - 5, x + 64, y - 5)
    c.restoreState()


def _fmt_amount(v):
    return f"{int(v):,}".replace(',', ' ')


def build_payment_receipt(payment):
    """Payment uchun PDF baytlarini qaytaradi."""
    brand = getattr(settings, 'BRAND_NAME', 'Fan Lider')
    buf = io.BytesIO()
    W, H = A5
    c = canvas.Canvas(buf, pagesize=A5)

    student = payment.student
    invoice = payment.invoice
    course = invoice.course if invoice and invoice.course_id else None
    if course is None:
        enr = student.enrollments.select_related('course__teacher').first()
        course = enr.course if enr else None
    teacher = course.teacher.full_name if course and course.teacher_id else "—"
    if invoice:
        period = f"{UZB_MONTHS[invoice.month - 1]} {invoice.year}"
    else:
        period = f"{UZB_MONTHS[payment.paid_at.month - 1]} {payment.paid_at.year}"

    M = 14 * mm
    # ---- Header ----
    c.setFillColor(BRAND)
    c.rect(0, H - 26 * mm, W, 26 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor('#ffffff'))
    c.setFont('Helvetica-Bold', 17)
    c.drawString(M, H - 14 * mm, f"{brand} ")
    c.setFont('Helvetica', 9)
    c.drawString(M, H - 19 * mm, "O'quv markazi — to'lov cheki / kvitansiya")
    c.setFont('Helvetica-Bold', 10)
    c.drawRightString(W - M, H - 13 * mm, f"CHEK #{payment.pk:05d}")
    c.setFont('Helvetica', 8)
    c.drawRightString(W - M, H - 18 * mm, payment.paid_at.strftime('%d.%m.%Y  %H:%M'))

    # ---- Body rows ----
    y = H - 38 * mm
    rows = [
        ("O'quvchi", student.full_name),
        ("Telefon", student.phone or "—"),
        ("Kurs / guruh", course.name if course else "—"),
        ("Yo'nalish", course.subject.name if course and course.subject_id else "—"),
        ("O'qituvchi", teacher),
        ("Davr (oy)", period),
        ("To'lov turi", payment.get_method_display()),
        ("Qabul qildi", payment.received_by.display_name if payment.received_by_id else "—"),
    ]
    c.setFont('Helvetica', 10)
    for label, value in rows:
        c.setFillColor(MUTED)
        c.setFont('Helvetica', 9)
        c.drawString(M, y, label)
        c.setFillColor(INK)
        c.setFont('Helvetica-Bold', 10)
        c.drawRightString(W - M, y, str(value)[:42])
        c.setStrokeColor(LINE)
        c.setLineWidth(0.5)
        c.line(M, y - 2.5 * mm, W - M, y - 2.5 * mm)
        y -= 8 * mm

    # ---- Summa katta ----
    y -= 2 * mm
    c.setFillColor(HexColor('#fdf1ea'))
    c.roundRect(M, y - 14 * mm, W - 2 * M, 16 * mm, 6, stroke=0, fill=1)
    c.setFillColor(MUTED)
    c.setFont('Helvetica', 9)
    c.drawString(M + 5 * mm, y - 3 * mm, "To'langan summa")
    c.setFillColor(BRAND)
    c.setFont('Helvetica-Bold', 20)
    c.drawRightString(W - M - 5 * mm, y - 8 * mm, f"{_fmt_amount(payment.amount)} so'm")

    # ---- Pechat + imzo ----
    seal_y = 34 * mm
    _draw_seal(c, W - M - 16 * mm, seal_y, 15 * mm, brand)
    _draw_signature(c, M + 2 * mm, seal_y - 2 * mm)
    c.setFillColor(MUTED)
    c.setFont('Helvetica', 7.5)
    c.drawString(M, seal_y - 12 * mm, "Elektron imzo (rahbar)")
    c.drawString(M, seal_y - 16 * mm, "Imzo va pechat elektron tarzda qo'yilgan.")

    # ---- QR (tekshirish) ----
    try:
        import qrcode
        qr_data = (
            f"{brand} CHEK #{payment.pk}\n{student.full_name}\n"
            f"{_fmt_amount(payment.amount)} som\n{payment.paid_at.strftime('%d.%m.%Y %H:%M')}"
        )
        img = qrcode.make(qr_data)
        from reportlab.lib.utils import ImageReader
        bio = io.BytesIO()
        img.save(bio, format='PNG')
        bio.seek(0)
        c.drawImage(ImageReader(bio), W / 2 - 9 * mm, 10 * mm, 18 * mm, 18 * mm)
    except Exception:
        pass

    # ---- Footer ----
    c.setFillColor(MUTED)
    c.setFont('Helvetica', 7)
    c.drawCentredString(W / 2, 6 * mm, f"{brand} CRM • Ushbu chek to'lov tasdig'i hisoblanadi • {datetime.now().year}")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()
