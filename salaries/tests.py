from decimal import Decimal

from django.test import TestCase

from .engine import compute, compute_kpi_score
from .models import Employee


class EngineTests(TestCase):
    def test_kpi_score_bounds(self):
        self.assertEqual(compute_kpi_score(100, 100, 0, 0), Decimal('100.00'))
        self.assertEqual(compute_kpi_score(0, 0, 50, 50), Decimal('0.00'))

    def test_mixed_salary(self):
        emp = Employee(
            full_name="Test", employment_type='mixed',
            base_salary=Decimal('3000000'), kpi_bonus_pct=Decimal('20'),
            late_penalty=Decimal('50000'),
        )
        result = compute(emp, {
            'attendance_rate': 100, 'avg_score': 100,
            'late_count': 0, 'absence_count': 0,
            'worked_hours': 0, 'students_count': 0,
            'manual_bonus': 0, 'manual_penalty': 0,
        })
        # 3,000,000 + 20% bonus (KPI=100) = 3,600,000
        self.assertEqual(result['total_amount'], Decimal('3600000.00'))

    def test_penalty_applied(self):
        emp = Employee(
            full_name="Test", employment_type='fixed',
            base_salary=Decimal('2000000'), kpi_bonus_pct=Decimal('0'),
            late_penalty=Decimal('100000'),
        )
        result = compute(emp, {'late_count': 2})
        self.assertEqual(result['total_amount'], Decimal('1800000.00'))
