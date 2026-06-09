"""Oylik hisob-kitobining suniy intellekt tahlili.

Tartib: GEMINI_API_KEY bo'lsa — Google Gemini (REST, qo'shimcha kutubxonasiz),
bo'lmasa ANTHROPIC_API_KEY bo'lsa — Claude, ikkalasi ham bo'lmasa — formula
natijalaridan mahalliy (offline) izoh. Barcha holatda natija bir xil ko'rinishda
qaytadi: {analysis, recommendation, rating, ai, model}.
"""
import json
import logging
import urllib.error
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

SYSTEM_RUBRIK = (
    "Siz o'quv markazi uchun adolatli oylik hisoblovchi HR-analitiksiz. "
    "Sizga xodim ma'lumotlari, oylik metrikalari va formula bo'yicha hisoblangan "
    "tarkib beriladi. Siz hisob-kitobni baholaysiz va QAT'IY JSON qaytarasiz "
    "(boshqa matnsiz):\n"
    '{"analysis": "...", "recommendation": "...", "rating": "..."}\n'
    "- analysis: 2-4 jumla, o'zbek tilida, oylik nega shunday chiqqanini tushuntiradi.\n"
    "- recommendation: 1-2 jumla amaliy tavsiya (bonus/jarima/rivojlanish).\n"
    "- rating: xodim oyligi samaradorligi bahosi — 'A'(a'lo), 'B'(yaxshi), "
    "'C'(qoniqarli) yoki 'D'(past) dan biri.\n"
    "Hech qachon summalarni o'zgartirmang — faqat tahlil bering."
)


def _context_text(employee, record):
    b = record.breakdown or {}
    lines = "\n".join(
        f"  - {l['label']}: {l['amount']:,.0f} so'm" for l in b.get('lines', [])
    )
    return (
        f"Xodim: {employee.full_name}\n"
        f"Lavozim: {employee.get_position_display()}\n"
        f"Ish turi: {employee.get_employment_type_display()}\n\n"
        f"Metrikalar:\n"
        f"  - Ishlagan kunlar: {record.worked_days}\n"
        f"  - Ishlagan soatlar: {record.worked_hours}\n"
        f"  - Guruhlar: {record.groups_count}, O'quvchilar: {record.students_count}\n"
        f"  - O'tilgan darslar: {record.lessons_count}\n"
        f"  - Davomat: {record.attendance_rate}%\n"
        f"  - O'rtacha o'zlashtirish: {record.avg_score}%\n"
        f"  - Kechikishlar: {record.late_count}, Sababsiz: {record.absence_count}\n"
        f"  - KPI ko'rsatkichi: {record.kpi_score}/100\n\n"
        f"Hisoblangan tarkib:\n{lines}\n"
        f"  JAMI: {record.total_amount:,.0f} so'm"
    )


def _fallback(employee, record):
    """Offline (AI'siz) izoh."""
    kpi = float(record.kpi_score)
    if kpi >= 85:
        rating, tone = 'A', "a'lo darajada ishlagan"
    elif kpi >= 70:
        rating, tone = 'B', "yaxshi natija ko'rsatgan"
    elif kpi >= 50:
        rating, tone = 'C', "qoniqarli ishlagan"
    else:
        rating, tone = 'D', "natijalarini yaxshilashi kerak"

    analysis = (
        f"{employee.full_name} ushbu davrda {tone}. "
        f"Davomat {record.attendance_rate}% va o'rtacha o'zlashtirish {record.avg_score}% "
        f"bo'lib, KPI ko'rsatkichi {record.kpi_score}/100 ni tashkil etdi. "
        f"Shu asosda KPI bonusi {float(record.kpi_bonus):,.0f} so'm hisoblandi, "
        f"yakuniy oylik {float(record.total_amount):,.0f} so'm."
    )
    if kpi >= 85:
        rec = "Yuqori natija uchun rag'batlantirish yoki qo'shimcha bonusni ko'rib chiqing."
    elif kpi >= 50:
        rec = "Davomat va o'zlashtirishni oshirish orqali KPI bonusini ko'paytirish mumkin."
    else:
        rec = "Davomat va dars sifatini yaxshilash bo'yicha individual reja tuzish tavsiya etiladi."
    if record.late_count:
        rec += f" Kechikishlar soni ({record.late_count}) e'tiborga olinsin."

    return {'analysis': analysis, 'recommendation': rec, 'rating': rating, 'ai': False, 'model': ''}


def _gemini(employee, record):
    """Google Gemini API orqali tahlil (REST). Xato bo'lsa None qaytaradi."""
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key:
        return None

    model = getattr(settings, 'GEMINI_MODEL', '') or 'gemini-2.5-flash'
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_RUBRIK}]},
        "contents": [{
            "role": "user",
            "parts": [{"text": _context_text(employee, record)}],
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.4,
            "maxOutputTokens": 1024,
            # 2.5-flash "thinking" modeli — o'ylashni o'chiramiz (tez + bo'sh
            # javob muammosining oldini oladi). Eski modellar bu maydonni e'tiborsiz qoldiradi.
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'x-goog-api-key': api_key},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode('utf-8'))

        candidates = payload.get('candidates') or []
        if not candidates:
            logger.warning("Gemini bo'sh javob qaytardi: %s", str(payload)[:300])
            return None
        parts = candidates[0].get('content', {}).get('parts', [])
        text = ''.join(p.get('text', '') for p in parts).strip()
        # JSON ni ajratib olish (model qo'shimcha matn qo'shib qo'ysa)
        start, end = text.find('{'), text.rfind('}')
        if start != -1 and end != -1:
            text = text[start:end + 1]
        data = json.loads(text)
        return {
            'analysis': (data.get('analysis') or '').strip(),
            'recommendation': (data.get('recommendation') or '').strip(),
            'rating': (data.get('rating') or '').strip()[:20],
            'ai': True,
            'model': model,
        }
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode('utf-8')[:300]
        except Exception:
            detail = ''
        logger.exception("Gemini AI HTTP %s xatosi. Model=%s detail=%s", e.code, model, detail)
        return None
    except Exception:
        logger.exception("Gemini AI tahlili muvaffaqiyatsiz (keyingi usulga o'tildi). Model=%s", model)
        return None


def _claude(employee, record):
    """Claude API orqali tahlil. Xato bo'lsa None qaytaradi."""
    try:
        import anthropic
    except ImportError:
        return None

    api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
    if not api_key:
        return None

    model = getattr(settings, 'ANTHROPIC_MODEL', '') or 'claude-sonnet-4-5'
    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=model,
            max_tokens=600,
            system=[{
                'type': 'text',
                'text': SYSTEM_RUBRIK,
                'cache_control': {'type': 'ephemeral'},
            }],
            messages=[{
                'role': 'user',
                'content': _context_text(employee, record),
            }],
        )
        text = ''.join(block.text for block in resp.content if block.type == 'text').strip()
        # JSON ni ajratib olish
        start, end = text.find('{'), text.rfind('}')
        if start != -1 and end != -1:
            text = text[start:end + 1]
        data = json.loads(text)
        return {
            'analysis': data.get('analysis', '').strip(),
            'recommendation': data.get('recommendation', '').strip(),
            'rating': (data.get('rating') or '').strip()[:20],
            'ai': True,
            'model': model,
        }
    except Exception:
        # Xato yashirin qolmasin — nega AI ishlamayotgani log'da ko'rinadi
        # (noto'g'ri model nomi, kalit, internet va h.k.).
        logger.exception("Claude AI tahlili muvaffaqiyatsiz (offline rejimga o'tildi). Model=%s", model)
        return None


def analyze(employee, record, save=True):
    """Yozuv uchun AI tahlilini yaratadi va (ixtiyoriy) saqlaydi.

    Avval Gemini, bo'lmasa Claude, ikkalasi ham bo'lmasa offline formula izohi.
    """
    result = _gemini(employee, record) or _claude(employee, record) or _fallback(employee, record)

    record.ai_analysis = result['analysis']
    record.ai_recommendation = result['recommendation']
    record.ai_rating = result['rating']
    record.ai_generated = result['ai']
    record.ai_model = result['model']
    if save:
        record.save(update_fields=[
            'ai_analysis', 'ai_recommendation', 'ai_rating', 'ai_generated', 'ai_model', 'updated_at',
        ])
    return result
