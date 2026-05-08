import pytest
from datetime import time, date
from attendance.upload_processor import process_upload
from attendance.models import AttendanceUpload, AttendanceRecord
from attendance.parser import AttendanceRow
from employees.models import Employee, Department
from accounts.models import User

@pytest.fixture
def setup(db):
    hr_user = User.objects.create_user(email='hr@example.com', password='pass', role=User.Role.HR)
    dept = Department.objects.create(name='KD')
    emp = Employee.objects.create(
        user=User.objects.create_user(email='emp@example.com', password='pass'),
        code='NV001', full_name='A', department=dept
    )
    upload = AttendanceUpload.objects.create(month='2026-05', uploaded_by=hr_user)
    return {'upload': upload, 'emp': emp}

@pytest.mark.django_db
def test_process_normal_row(setup):
    rows = [AttendanceRow('NV001', 'A', date(2026, 5, 1), time(8, 0), time(17, 0), 'HC')]
    process_upload(setup['upload'], rows)
    records = AttendanceRecord.objects.filter(upload=setup['upload'])
    assert records.count() == 1
    assert records.first().status == 'ok'

@pytest.mark.django_db
def test_process_missing_checkin_creates_error(setup):
    rows = [AttendanceRow('NV001', 'A', date(2026, 5, 1), None, time(17, 0), 'HC')]
    process_upload(setup['upload'], rows)
    record = AttendanceRecord.objects.get(upload=setup['upload'])
    assert record.status == 'error'
    assert 'MISSING_IN' in record.error_types

@pytest.mark.django_db
def test_process_unknown_employee_skips(setup):
    rows = [AttendanceRow('NV999', 'Unknown', date(2026, 5, 1), time(8, 0), time(17, 0), 'HC')]
    process_upload(setup['upload'], rows)
    assert AttendanceRecord.objects.filter(upload=setup['upload']).count() == 0
