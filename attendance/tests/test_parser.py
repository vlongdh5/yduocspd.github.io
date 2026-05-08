import pytest
from datetime import date, time
from attendance.parser import parse_attendance_excel, AttendanceRow, InvalidAttendanceFile
from openpyxl import Workbook
import tempfile, os


# MCC header: 12 columns matching the real file format
HEADER = [
    'Mã nhân viên', 'Tên', 'Họ và tên', 'Ngày công', 'Phòng ban',
    'Ca làm việc đăng ký', 'Giờ vào theo ca đăng ký', 'Giờ ra theo ca đăng ký',
    'Giờ bắt đầu nghỉ trưa', 'Giờ kết thúc nghỉ trưa',
    'Giờ vào Máy chấm công', 'Giờ ra Máy chấm công',
]


def make_sample_excel(data_rows, header=None):
    wb = Workbook()
    ws = wb.active
    ws.append(header or HEADER)
    for row in data_rows:
        # Pad to 12 columns
        padded = list(row) + [None] * (12 - len(row))
        ws.append(padded)
    tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    wb.save(tmp.name)
    return tmp.name


def _row(code, name, date_str, shift, check_in=None, check_out=None):
    """Helper: build a full 12-col row with key fields filled."""
    return [code, None, name, date_str, 'DEPT', shift, None, None, None, None, check_in, check_out]


def test_parse_valid_rows():
    path = make_sample_excel([
        _row('NV001', 'Nguyen Van A', '2026-05-01', 'Ca 8-17', '08:00', '17:00'),
        _row('NV002', 'Tran Thi B',   '2026-05-01', 'Ca 8-17', '08:05', '17:10'),
    ])
    rows = parse_attendance_excel(path)
    os.unlink(path)
    assert len(rows) == 2
    assert rows[0].employee_code == 'NV001'
    assert rows[0].employee_name == 'Nguyen Van A'
    assert rows[0].check_in == time(8, 0)
    assert rows[0].check_out == time(17, 0)
    assert rows[0].shift_code == 'Ca 8-17'


def test_parse_missing_checkin():
    path = make_sample_excel([
        _row('NV001', 'Nguyen Van A', '2026-05-01', 'Ca 8-17', None, '17:00'),
    ])
    rows = parse_attendance_excel(path)
    os.unlink(path)
    assert rows[0].check_in is None
    assert rows[0].check_out == time(17, 0)


def test_parse_empty_row_skipped():
    path = make_sample_excel([
        _row('NV001', 'Nguyen Van A', '2026-05-01', 'Ca 8-17', '08:00', '17:00'),
        [None] * 12,
    ])
    rows = parse_attendance_excel(path)
    os.unlink(path)
    assert len(rows) == 1


def test_parse_invalid_header_raises():
    bad_header = ['Wrong col'] + HEADER[1:]
    path = make_sample_excel([], header=bad_header)
    with pytest.raises(InvalidAttendanceFile):
        parse_attendance_excel(path)
    os.unlink(path)
