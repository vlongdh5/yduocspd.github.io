from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Employee, Department, LeaveBalance
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
