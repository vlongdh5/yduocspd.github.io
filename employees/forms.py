from django import forms
from decimal import Decimal
from .models import Employee, LeaveBalance


class EmployeeForm(forms.ModelForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        label='Email đăng nhập'
    )
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Để trống nếu không đổi mật khẩu',
        label='Mật khẩu'
    )
    role = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Vai trò hệ thống'
    )

    class Meta:
        model = Employee
        fields = ['code', 'full_name', 'department', 'position', 'start_date', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from accounts.models import User
        self.fields['role'].choices = User.Role.choices
        if self.instance and self.instance.pk:
            self.fields['email'].initial = self.instance.user.email
            self.fields['role'].initial = self.instance.user.role

    def clean_password(self):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError
        password = self.cleaned_data.get('password')
        if password:
            try:
                validate_password(password)
            except DjangoValidationError as e:
                raise forms.ValidationError(e.messages)
        return password

    def save(self, commit=True):
        from accounts.models import User
        emp = super().save(commit=False)
        email = self.cleaned_data['email']
        password = self.cleaned_data.get('password')
        role = self.cleaned_data.get('role', User.Role.EMPLOYEE)
        if emp.pk:
            user = emp.user
            user.email = email
            user.username = email
            user.role = role
            if password:
                user.set_password(password)
            user.save()
        else:
            user = User.objects.create_user(
                email=email,
                password=password or User.objects.make_random_password(),
                role=role
            )
            emp.user = user
        if commit:
            emp.save()
        return emp


class LeaveBalanceForm(forms.ModelForm):
    class Meta:
        model = LeaveBalance
        fields = ['year', 'total_days', 'used_days']
        widgets = {
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'total_days': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'used_days': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
        }


class CompensatoryCreditForm(forms.Form):
    hours = forms.DecimalField(
        max_digits=4, decimal_places=1, min_value=Decimal('0.5'), max_value=Decimal('999.9'),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
        label='Số giờ cấp bù'
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Ngày'
    )
    note = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        label='Ghi chú', required=False
    )
