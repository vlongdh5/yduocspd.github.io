from django.core.management.base import BaseCommand
from explanations.models import ExplanationReason

DEFAULTS = [
    {'name': 'Đi muộn/ Về sớm', 'requires_full_day_shift': False, 'is_compensatory': False},
    {'name': 'Quên chấm công', 'requires_full_day_shift': False, 'is_compensatory': False},
    {'name': 'Trị liệu tại nhà', 'requires_full_day_shift': False, 'is_compensatory': False},
    {'name': 'Đi công tác/ tổ chức sự kiện/ công việc khác theo chỉ đạo', 'requires_full_day_shift': False, 'is_compensatory': False},
    {'name': 'Nghỉ phép cả ngày', 'requires_full_day_shift': False, 'is_compensatory': False},
    {'name': 'Nghỉ không lương', 'requires_full_day_shift': False, 'is_compensatory': False},
    {'name': 'Nghỉ phép nửa ngày', 'requires_full_day_shift': True, 'is_compensatory': False},
    {'name': 'Nghỉ bù cả ngày', 'requires_full_day_shift': False, 'is_compensatory': True},
    {'name': 'Nghỉ bù nửa ngày', 'requires_full_day_shift': True, 'is_compensatory': True},
]


class Command(BaseCommand):
    help = 'Seed default explanation reasons'

    def handle(self, *args, **options):
        for i, data in enumerate(DEFAULTS, start=1):
            obj, created = ExplanationReason.objects.get_or_create(
                name=data['name'],
                defaults={
                    'order': i,
                    'requires_full_day_shift': data['requires_full_day_shift'],
                    'is_compensatory': data['is_compensatory'],
                },
            )
            if not created:
                obj.requires_full_day_shift = data['requires_full_day_shift']
                obj.is_compensatory = data['is_compensatory']
                obj.order = i
                obj.save()
        self.stdout.write(self.style.SUCCESS('Seeded explanation reasons.'))
