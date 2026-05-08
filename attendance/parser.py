from dataclasses import dataclass
from datetime import date, time, datetime
from typing import Optional
from openpyxl import load_workbook


@dataclass
class AttendanceRow:
    employee_code: str
    employee_name: str
    date: date
    check_in: Optional[time]
    check_out: Optional[time]
    shift_code: str


def _parse_time(value) -> Optional[time]:
    if value is None:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        for fmt in ('%H:%M', '%H:%M:%S'):
            try:
                return datetime.strptime(value, fmt).time()
            except ValueError:
                pass
    return None


def _parse_date(value) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                pass
    return None


def parse_attendance_excel(file_path: str) -> list:
    wb = load_workbook(file_path, data_only=True)
    ws = wb.active
    rows = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue
        if not row[0]:
            continue
        emp_code = str(row[0]).strip()
        if not emp_code:
            continue
        parsed_date = _parse_date(row[2])
        if not parsed_date:
            continue
        rows.append(AttendanceRow(
            employee_code=emp_code,
            employee_name=str(row[1]).strip() if row[1] else '',
            date=parsed_date,
            check_in=_parse_time(row[3]),
            check_out=_parse_time(row[4]),
            shift_code=str(row[5]).strip() if row[5] else '',
        ))
    return rows
