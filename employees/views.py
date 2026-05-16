from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import TemplateView
from django.core.paginator import Paginator
from django.utils import timezone
from .models import Employee, Department, LeaveBalance, LeaveTransaction, CompensatoryBalance, CompensatoryTransaction
from .forms import EmployeeForm, LeaveBalanceForm


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
        from datetime import date
        form = LeaveBalanceForm(initial={'year': date.today().year})
    return render(request, 'employees/leave_balance.html', {
        'emp': emp, 'balances': balances, 'form': form
    })


class MyLeaveView(LoginRequiredMixin, TemplateView):
    template_name = 'employees/my_leave.html'
    PAGE_SIZE = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_year = timezone.now().year

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
                'year_range': range(current_year - 4, current_year + 2),
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
        ).order_by('-date')
        leave_paginator = Paginator(leave_qs, self.PAGE_SIZE)
        leave_page_num = self.request.GET.get('lpage', 1)
        leave_page = leave_paginator.get_page(leave_page_num)

        # Paginated compensatory transactions (all time)
        comp_qs = CompensatoryTransaction.objects.filter(
            employee=employee,
        ).order_by('-date', '-created_at')
        comp_paginator = Paginator(comp_qs, self.PAGE_SIZE)
        comp_page_num = self.request.GET.get('cpage', 1)
        comp_page = comp_paginator.get_page(comp_page_num)

        context.update({
            'employee': employee,
            'leave_balance': leave_balance,
            'comp_balance': comp_balance,
            'leave_page': leave_page,
            'comp_page': comp_page,
            'year': year,
            'current_year': current_year,
            'year_range': range(current_year - 4, current_year + 2),
            'active_tab': self.request.GET.get('tab', 'leave'),
        })
        return context
