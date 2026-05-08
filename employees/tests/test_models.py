import pytest
from employees.models import Department, Employee
from accounts.models import User

@pytest.mark.django_db
def test_create_department():
    dept = Department.objects.create(name='Kinh doanh')
    assert str(dept) == 'Kinh doanh'

@pytest.mark.django_db
def test_department_has_manager():
    user = User.objects.create_user(email='tbp@example.com', password='pass', role=User.Role.TBP)
    dept = Department.objects.create(name='Kinh doanh', manager=user)
    assert dept.manager == user

@pytest.mark.django_db
def test_create_employee():
    user = User.objects.create_user(email='emp@example.com', password='pass')
    dept = Department.objects.create(name='Kinh doanh')
    emp = Employee.objects.create(
        user=user, code='NV001', full_name='Nguyen Van A',
        department=dept, position='Sales'
    )
    assert emp.code == 'NV001'
    assert emp.is_active is True
    assert str(emp) == 'NV001 - Nguyen Van A'

@pytest.mark.django_db
def test_employee_code_unique():
    user1 = User.objects.create_user(email='emp1@example.com', password='pass')
    user2 = User.objects.create_user(email='emp2@example.com', password='pass')
    dept = Department.objects.create(name='Kinh doanh')
    Employee.objects.create(user=user1, code='NV001', full_name='A', department=dept)
    with pytest.raises(Exception):
        Employee.objects.create(user=user2, code='NV001', full_name='B', department=dept)
