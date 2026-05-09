from django.core.management.base import BaseCommand
from explanations.models import ExplanationReason

DEFAULTS = [
    {'name': 'Đi muộn/ Về sớm', 'requires_full_day_shift': False},
    {'name': 'Quên chấm công', 'requires_full_day_shift': False},
    {'name': 'Trị liệu tại nhà', 'requires_full_day_shift': False},
    {'name': 'Đi công tác/ tổ chức sự kiện/ công việc khác theo chỉ đạo', 'requires_full_day_shift': False},
    {'name': 'Nghỉ phép cả ngày', 'requires_full_day_shift': False},
    {'name': 'Nghỉ không lương', 'requires_full_day_shift': False},
    {'name': 'Nghỉ phép nửa ngày', 'requires_full_day_shift': True},
]


class Command(BaseCommand):
    help = 'Seed default explanation reasons'

    def handle(self, *args, **options):
        for i, data in enumerate(DEFAULTS, start=1):
            obj, created = ExplanationReason.objects.get_or_create(
                name=data['name'],
                defaults={'order': i, 'requires_full_day_shift': data['requires_full_day_shift']},
            )
            if not created:
                obj.requires_full_day_shift = data['requires_full_day_shift']
                obj.order = i
                obj.save()
        self.stdout.write(self.style.SUCCESS('Seeded explanation reasons.'))
