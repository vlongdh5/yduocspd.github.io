from django import forms
from .models import AttendanceUpload

_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


class AttendanceUploadForm(forms.ModelForm):
    class Meta:
        model = AttendanceUpload
        fields = ['file', 'month']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx'}),
            'month': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'YYYY-MM'}),
        }

    def clean_file(self):
        f = self.cleaned_data.get('file')
        if not f:
            return f
        if f.size > _MAX_UPLOAD_BYTES:
            raise forms.ValidationError('File không được vượt quá 10 MB.')
        # XLSX is a ZIP container — magic bytes PK\x03\x04
        header = f.read(4)
        f.seek(0)
        if header != b'PK\x03\x04':
            raise forms.ValidationError('File phải là định dạng Excel (.xlsx) hợp lệ.')
        return f
