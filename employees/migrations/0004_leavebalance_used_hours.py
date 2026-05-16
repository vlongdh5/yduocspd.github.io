from django.db import migrations, models


def days_to_hours(apps, schema_editor):
    LeaveBalance = apps.get_model('employees', 'LeaveBalance')
    for lb in LeaveBalance.objects.all():
        lb.used_hours = lb.used_hours * 8  # field was renamed; value is still in days
        lb.save(update_fields=['used_hours'])


class Migration(migrations.Migration):

    dependencies = [
        ('employees', '0003_fix_compensatory_transaction_hours_max_digits'),
    ]

    operations = [
        migrations.RenameField(
            model_name='leavebalance',
            old_name='used_days',
            new_name='used_hours',
        ),
        migrations.AlterField(
            model_name='leavebalance',
            name='used_hours',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=7),
        ),
        migrations.RunPython(days_to_hours, migrations.RunPython.noop),
    ]
