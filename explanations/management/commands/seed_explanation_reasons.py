from django.core.management.base import BaseCommand
from explanations.models import ExplanationReason

DEFAULTS = [
    'Đi muộn/ Về sớm',
    'Quên chấm công',
    'Trị liệu tại nhà',
    'Đi công tác/ tổ chức sự kiện/ công việc khác theo chỉ đạo',
    'Nghỉ phép cả ngày',
    'Nghỉ không lương',
    'Nghỉ phép nửa ngày',
]


class Command(BaseCommand):
    help = 'Seed default explanation reasons'

    def handle(self, *args, **options):
        for i, name in enumerate(DEFAULTS, start=1):
            ExplanationReason.objects.get_or_create(name=name, defaults={'order': i})
        self.stdout.write(self.style.SUCCESS('Seeded explanation reasons.'))
