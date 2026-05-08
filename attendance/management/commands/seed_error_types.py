from django.core.management.base import BaseCommand
from attendance.models import ErrorType

DEFAULTS = [
    {'code': 'MISSING_IN', 'name': 'Thiếu giờ vào', 'description': 'Không có dữ liệu chấm thẻ vào', 'detection_rule': {}},
    {'code': 'MISSING_OUT', 'name': 'Thiếu giờ ra', 'description': 'Không có dữ liệu chấm thẻ ra', 'detection_rule': {}},
    {'code': 'ABSENT', 'name': 'Vắng mặt', 'description': 'Không có dữ liệu chấm công cả ngày', 'detection_rule': {}},
    {'code': 'LATE', 'name': 'Đi muộn', 'description': 'Giờ vào trễ hơn tiêu chuẩn',
     'detection_rule': {'standard_start': '08:00', 'late_threshold_minutes': 15}},
    {'code': 'EARLY_LEAVE', 'name': 'Về sớm', 'description': 'Giờ ra sớm hơn tiêu chuẩn',
     'detection_rule': {'standard_end': '17:00', 'early_leave_threshold_minutes': 15}},
]


class Command(BaseCommand):
    help = 'Seed default error types'

    def handle(self, *args, **options):
        for d in DEFAULTS:
            ErrorType.objects.get_or_create(code=d['code'], defaults=d)
        self.stdout.write(self.style.SUCCESS('Seeded error types.'))
