import unicodedata
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import TemplateView
from django.core.paginator import Paginator
from django.db import transaction as db_transaction
from django.db.models import F
from django.http import HttpResponse
from django.utils import timezone
from decimal import Decimal
import openpyxl


def _normalize(text):
    """Bỏ dấu tiếng Việt, lowercase — dùng để so sánh fuzzy."""
    return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode().lower()
from .models import Employee, Department, LeaveBalance, LeaveTransaction, CompensatoryBalance, CompensatoryTransaction
from .forms import EmployeeForm, LeaveBalanceForm, CompensatoryCreditForm


def _hr_only(request):
    return request.user.is_authenticated and request.user.is_hr


@login_required
def employee_list(request):
    if not _hr_only(request):
        return redirect('attendance:my_attendance')
    employees = Employee.objects.select_related('department', 'user').order_by('code')
    return render(request, 'employees/list.html', {'employees': employees})


@login_required
def employee_create(request):
    if not _hr_only(request):
        return redirect('attendance:my_attendance')
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã thêm nhân viên.')
            return redirect('employees:list')
    else:
        form = EmployeeForm()
    return render(request, 'employees/form.html', {'form': form, 'action': 'Thêm mới'})


@login_required
def employee_edit(request, pk):
    if not _hr_only(request):
        return redirect('attendance:my_attendance')
    emp = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=emp)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã cập nhật nhân viên.')
            return redirect('employees:list')
    else:
        form = EmployeeForm(instance=emp)
    return render(request, 'employees/form.html', {'form': form, 'action': 'Cập nhật', 'emp': emp})


@login_required
def leave_balance_view(request, pk):
    if not _hr_only(request):
        return redirect('attendance:my_attendance')
    emp = get_object_or_404(Employee, pk=pk)
    balances = LeaveBalance.objects.filter(employee=emp).order_by('-year')
    if request.method == 'POST':
        form = LeaveBalanceForm(request.POST)
        if form.is_valid():
            lb = form.save(commit=False)
            lb.employee = emp
            lb.save()
            messages.success(request, 'Đã cập nhật ngày phép.')
            return redirect('employees:leave_balance', pk=pk)
    else:
        form = LeaveBalanceForm(initial={'year': timezone.now().year})
    return render(request, 'employees/leave_balance.html', {
        'emp': emp, 'balances': balances, 'form': form
    })


class MyLeaveView(LoginRequiredMixin, TemplateView):
    template_name = 'employees/my_leave.html'
    PAGE_SIZE = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_year = timezone.now().year
        year_range = range(current_year - 4, current_year + 2)

        # Year filter (for leave-transaction tab)
        try:
            year = int(self.request.GET.get('year', current_year))
        except (TypeError, ValueError):
            year = current_year

        # Fetch the employee profile; if the user has no profile, show empty state
        try:
            employee = self.request.user.employee_profile
        except Employee.DoesNotExist:
            context.update({
                'employee': None,
                'leave_balance': None,
                'comp_balance': None,
                'leave_page': None,
                'comp_page': None,
                'year': year,
                'current_year': current_year,
                'year_range': year_range,
                'active_tab': self.request.GET.get('tab', 'leave'),
            })
            return context

        # Leave balance for selected year
        try:
            leave_balance = LeaveBalance.objects.get(employee=employee, year=year)
        except LeaveBalance.DoesNotExist:
            leave_balance = None

        # Compensatory balance (one per employee, no year filter)
        try:
            comp_balance = employee.compensatory_balance
        except CompensatoryBalance.DoesNotExist:
            comp_balance = None

        # Paginated leave transactions (filtered by year)
        leave_qs = LeaveTransaction.objects.filter(
            employee=employee,
            leave_balance__year=year,
        ).select_related('leave_balance').order_by('-date')
        leave_paginator = Paginator(leave_qs, self.PAGE_SIZE)
        leave_page_num = self.request.GET.get('lpage', 1)
        leave_page = leave_paginator.get_page(leave_page_num)

        # Paginated compensatory transactions (all time)
        comp_qs = CompensatoryTransaction.objects.filter(
            employee=employee,
        ).select_related('balance').order_by('-date', '-created_at')
        comp_paginator = Paginator(comp_qs, self.PAGE_SIZE)
        comp_page_num = self.request.GET.get('cpage', 1)
        comp_page = comp_paginator.get_page(comp_page_num)

        context.update({
            'employee': employee,
            'leave_balance': leave_balance,
            'comp_balance': comp_balance,
            'leave_page': leave_page,
            'leave_elided_range': leave_paginator.get_elided_page_range(leave_page.number),
            'comp_page': comp_page,
            'comp_elided_range': comp_paginator.get_elided_page_range(comp_page.number),
            'year': year,
            'current_year': current_year,
            'year_range': year_range,
            'active_tab': self.request.GET.get('tab', 'leave'),
        })
        return context


@login_required
def leave_management(request):
    if not _hr_only(request):
        return redirect('attendance:my_attendance')
    current_year = timezone.now().year
    dept_id = request.GET.get('dept')
    employees_qs = Employee.objects.select_related(
        'department', 'compensatory_balance'
    ).filter(is_active=True)
    if dept_id:
        employees_qs = employees_qs.filter(department_id=dept_id)
    employees_list = list(employees_qs.order_by('code'))

    q = request.GET.get('q', '').strip()
    if q:
        q_norm = _normalize(q)
        employees_list = [
            emp for emp in employees_list
            if q_norm in _normalize(emp.full_name) or q.lower() in emp.code.lower()
        ]

    leave_by_emp = {
        lb.employee_id: lb
        for lb in LeaveBalance.objects.filter(employee__in=employees_list, year=current_year)
    }
    emp_data = [
        {
            'emp': emp,
            'lb': leave_by_emp.get(emp.pk),
            'cb': getattr(emp, 'compensatory_balance', None),
        }
        for emp in employees_list
    ]

    departments = Department.objects.all()

    if 'export' in request.GET:
        return _export_leave_management(emp_data, current_year)

    return render(request, 'employees/leave_management.html', {
        'emp_data': emp_data,
        'departments': departments,
        'dept_id': dept_id,
        'current_year': current_year,
        'q': q,
    })


def _export_leave_management(emp_data, year):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f'Phep_Bu_{year}'
    ws.append(['Mã NV', 'Họ tên', 'Phòng ban',
               f'Phép tổng {year}', 'Phép đã dùng', 'Phép còn lại',
               'Bù tổng (h)', 'Bù đã dùng (h)', 'Bù còn lại (h)'])
    for item in emp_data:
        emp, lb, cb = item['emp'], item['lb'], item['cb']
        ws.append([
            emp.code, emp.full_name, emp.department.name,
            float(lb.total_days) if lb else 0,
            float(lb.used_days) if lb else 0,
            float(lb.remaining_days) if lb else 0,
            float(cb.total_hours) if cb else 0,
            float(cb.used_hours) if cb else 0,
            float(cb.remaining_hours) if cb else 0,
        ])
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="phep_bu_{year}.xlsx"'
    wb.save(response)
    return response


@login_required
def compensatory_credit(request, emp_pk):
    if not _hr_only(request):
        return redirect('attendance:my_attendance')
    emp = get_object_or_404(Employee, pk=emp_pk)
    comp_balance, _ = CompensatoryBalance.objects.get_or_create(employee=emp)
    transactions = CompensatoryTransaction.objects.filter(
        employee=emp
    ).select_related('created_by').order_by('-date', '-created_at')[:30]

    if request.method == 'POST':
        form = CompensatoryCreditForm(request.POST)
        if form.is_valid():
            hours = form.cleaned_data['hours']
            with db_transaction.atomic():
                CompensatoryBalance.objects.filter(pk=comp_balance.pk).update(
                    total_hours=F('total_hours') + hours
                )
                CompensatoryTransaction.objects.create(
                    employee=emp,
                    balance=comp_balance,
                    transaction_type=CompensatoryTransaction.Type.CREDIT,
                    hours=hours,
                    date=form.cleaned_data['date'],
                    note=form.cleaned_data.get('note', ''),
                    created_by=request.user,
                )
            messages.success(request, f'Đã cấp {hours}h nghỉ bù cho {emp.full_name}.')
            return redirect('employees:compensatory_credit', emp_pk=emp_pk)
    else:
        form = CompensatoryCreditForm()

    return render(request, 'employees/compensatory_credit.html', {
        'emp': emp,
        'comp_balance': comp_balance,
        'form': form,
        'transactions': transactions,
    })
