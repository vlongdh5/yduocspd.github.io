from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from reports.models import AttendanceCalculation
from employees.models import LeaveBalance


def export_calculation_excel(month: str, output_path: str):
    calcs = AttendanceCalculation.objects.filter(month=month).select_related(
        'employee__department'
    ).order_by('employee__department__name', 'employee__code')

    wb = Workbook()
    ws = wb.active
    ws.title = f'Tổng hợp công {month}'

    title_fill = PatternFill(start_color='1F4E79', end_color='1F4E79', fill_type='solid')
    title_font = Font(bold=True, color='FFFFFF', size=12)
    header_fill = PatternFill(start_color='D6E4F0', end_color='D6E4F0', fill_type='solid')
    header_font = Font(bold=True)
    thin = Side(style='thin')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal='center')

    ws.merge_cells('A1:H1')
    ws['A1'] = f'BẢNG TỔNG HỢP CÔNG THÁNG {month}'
    ws['A1'].font = title_font
    ws['A1'].fill = title_fill
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 30

    ws.append([])

    headers = ['STT', 'Mã NV', 'Họ tên', 'Phòng ban', 'Ngày công', 'Ngày phép dùng', 'Phép còn lại', 'Ghi chú']
    ws.append(headers)
    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=3, column=col)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = center

    for i, calc in enumerate(calcs, 1):
        emp = calc.employee
        try:
            lb = LeaveBalance.objects.get(employee=emp, year=int(month[:4]))
            remaining = float(lb.remaining_days)
        except LeaveBalance.DoesNotExist:
            remaining = '-'

        row_data = [i, emp.code, emp.full_name, emp.department.name,
                    float(calc.actual_workdays), float(calc.leave_days_used), remaining, '']
        ws.append(row_data)
        row_idx = ws.max_row
        for col in range(1, len(headers) + 1):
            ws.cell(row=row_idx, column=col).border = border
            if col in (1, 5, 6, 7):
                ws.cell(row=row_idx, column=col).alignment = center

    widths = [6, 10, 25, 20, 12, 18, 14, 20]
    for col, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = width

    wb.save(output_path)
