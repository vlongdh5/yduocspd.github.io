import pytest
from datetime import date, time
from attendance.parser import parse_attendance_excel, AttendanceRow
from openpyxl import Workbook
import tempfile, os


def make_sample_excel(rows):
    wb = Workbook()
    ws = wb.active
    ws.append(['Mã NV', 'Họ tên', 'Ngày', 'Giờ vào', 'Giờ ra', 'Mã ca'])
    for row in rows:
        ws.append(row)
    tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    wb.save(tmp.name)
    return tmp.name


def test_parse_valid_rows():
    path = make_sample_excel([
        ['NV001', 'Nguyen Van A', '2026-05-01', '08:00', '17:00', 'HC'],
        ['NV002', 'Tran Thi B', '2026-05-01', '08:05', '17:10', 'HC'],
    ])
    rows = parse_attendance_excel(path)
    os.unlink(path)
    assert len(rows) == 2
    assert rows[0].employee_code == 'NV001'
    assert rows[0].check_in == time(8, 0)
    assert rows[0].check_out == time(17, 0)
    assert rows[0].shift_code == 'HC'


def test_parse_missing_checkin():
    path = make_sample_excel([
        ['NV001', 'Nguyen Van A', '2026-05-01', None, '17:00', 'HC'],
    ])
    rows = parse_attendance_excel(path)
    os.unlink(path)
    assert rows[0].check_in is None
    assert rows[0].check_out == time(17, 0)


def test_parse_empty_row_skipped():
    path = make_sample_excel([
        ['NV001', 'Nguyen Van A', '2026-05-01', '08:00', '17:00', 'HC'],
        [None, None, None, None, None, None],
    ])
    rows = parse_attendance_excel(path)
    os.unlink(path)
    assert len(rows) == 1
