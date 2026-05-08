from django import forms
from .models import AttendanceUpload


class AttendanceUploadForm(forms.ModelForm):
    class Meta:
        model = AttendanceUpload
        fields = ['file', 'month']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx'}),
            'month': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'YYYY-MM'}),
        }
