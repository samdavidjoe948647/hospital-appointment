from django import forms
from django.contrib.auth.models import User
from .models import Patient, Doctor, Department, Appointment
from django.core.exceptions import ValidationError
from datetime import date

class PatientRegistrationForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=True, label="First Name")
    last_name = forms.CharField(max_length=150, required=True, label="Last Name")
    email = forms.EmailField(required=True, label="Email Address")
    gender = forms.ChoiceField(choices=Patient.GENDER_CHOICES, required=True, label="Gender")
    date_of_birth = forms.DateField(
        required=True,
        label="Date of Birth",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    password = forms.CharField(widget=forms.PasswordInput(), required=True, label="Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput(), required=True, label="Confirm Password")
    
    phone = forms.CharField(max_length=15, required=True, label="Phone Number")
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=True, label="Residential Address")

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': 'Choose a unique username'})
        for field in self.fields.values():
            if not isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({'class': 'form-control'})
        self.fields['gender'].widget.attrs.update({'class': 'form-select'})

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError("A user with that username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with that email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data


class PatientProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=True, label="First Name")
    last_name = forms.CharField(max_length=150, required=True, label="Last Name")
    email = forms.EmailField(required=True, label="Email Address")
    gender = forms.ChoiceField(choices=Patient.GENDER_CHOICES, required=True, label="Gender")
    date_of_birth = forms.DateField(
        required=True,
        label="Date of Birth",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    phone = forms.CharField(max_length=15, required=True, label="Phone Number")
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=True, label="Residential Address")

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        patient = kwargs.pop('patient', None)
        super().__init__(*args, **kwargs)
        if patient:
            self.fields['phone'].initial = patient.phone
            self.fields['address'].initial = patient.address
            self.fields['gender'].initial = patient.gender
            self.fields['date_of_birth'].initial = patient.date_of_birth
        for field in self.fields.values():
            if not isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({'class': 'form-control'})
        self.fields['gender'].widget.attrs.update({'class': 'form-select'})


class AppointmentBookingForm(forms.ModelForm):
    appointment_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Preferred Date"
    )
    appointment_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        label="Preferred Time"
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        label="Reason for Appointment"
    )

    class Meta:
        model = Appointment
        fields = ['department', 'doctor', 'appointment_date', 'appointment_time', 'reason']
        widgets = {
            'department': forms.Select(attrs={'class': 'form-select', 'id': 'id_department'}),
            'doctor': forms.Select(attrs={'class': 'form-select', 'id': 'id_doctor'}),
        }

    def __init__(self, *args, **kwargs):
        self.patient = kwargs.pop('patient', None)
        super().__init__(*args, **kwargs)
        self.fields['department'].queryset = Department.objects.filter(status='Active')
        self.fields['doctor'].queryset = Doctor.objects.filter(status='Active')

    def clean_appointment_date(self):
        appt_date = self.cleaned_data.get('appointment_date')
        if appt_date and appt_date < date.today():
            raise ValidationError("Appointment date cannot be in the past.")
        return appt_date

    def clean(self):
        cleaned_data = super().clean()
        appt_date = cleaned_data.get('appointment_date')
        appt_time = cleaned_data.get('appointment_time')
        doctor = cleaned_data.get('doctor')

        if appt_date and appt_time and doctor:
            # 1. Overlapping Doctor Appointment Check
            conflicting_doc = Appointment.objects.filter(
                doctor=doctor,
                appointment_date=appt_date,
                appointment_time=appt_time
            ).exclude(status__in=['Cancelled', 'Rejected'])
            if conflicting_doc.exists():
                raise ValidationError("The selected doctor is not available at this date and time due to an overlapping appointment.")

            # 2. Doctor Availability Weekdays Check
            weekday_name = appt_date.strftime('%A')
            available_days = doctor.available_days or ""
            if weekday_name.lower() not in available_days.lower():
                raise ValidationError(f"{doctor.full_name} is only available on: {doctor.available_days}")

            # 3. Patient Double Booking Check
            if self.patient:
                conflicting_pat = Appointment.objects.filter(
                    patient=self.patient,
                    appointment_date=appt_date,
                    appointment_time=appt_time
                ).exclude(status__in=['Cancelled', 'Rejected'])
                if conflicting_pat.exists():
                    raise ValidationError("You already have an appointment booked at this date and time.")

        return cleaned_data


class AppointmentRescheduleForm(forms.ModelForm):
    appointment_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="New Date"
    )
    appointment_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        label="New Time"
    )

    class Meta:
        model = Appointment
        fields = ['appointment_date', 'appointment_time']

    def __init__(self, *args, **kwargs):
        self.appointment_instance = kwargs.get('instance')
        self.patient = kwargs.pop('patient', None)
        super().__init__(*args, **kwargs)

    def clean_appointment_date(self):
        appt_date = self.cleaned_data.get('appointment_date')
        if appt_date and appt_date < date.today():
            raise ValidationError("Appointment date cannot be in the past.")
        return appt_date

    def clean(self):
        cleaned_data = super().clean()
        appt_date = cleaned_data.get('appointment_date')
        appt_time = cleaned_data.get('appointment_time')

        if appt_date and appt_time and self.appointment_instance:
            doctor = self.appointment_instance.doctor

            # 1. Overlapping Doctor Appointment Check
            conflicting_doc = Appointment.objects.filter(
                doctor=doctor,
                appointment_date=appt_date,
                appointment_time=appt_time
            ).exclude(status__in=['Cancelled', 'Rejected']).exclude(id=self.appointment_instance.id)
            if conflicting_doc.exists():
                raise ValidationError("The doctor is already booked at the selected date and time.")

            # 2. Doctor Availability Weekdays Check
            weekday_name = appt_date.strftime('%A')
            available_days = doctor.available_days or ""
            if weekday_name.lower() not in available_days.lower():
                raise ValidationError(f"{doctor.full_name} is only available on: {doctor.available_days}")

            # 3. Patient Double Booking Check
            if self.patient:
                conflicting_pat = Appointment.objects.filter(
                    patient=self.patient,
                    appointment_date=appt_date,
                    appointment_time=appt_time
                ).exclude(status__in=['Cancelled', 'Rejected']).exclude(id=self.appointment_instance.id)
                if conflicting_pat.exists():
                    raise ValidationError("You already have an appointment booked at this date and time.")

        return cleaned_data


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['department_name', 'description', 'status']
        widgets = {
            'department_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Cardiology'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Provide a description...'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class DoctorForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['full_name', 'specialization', 'department', 'email', 'phone', 'qualification', 'experience', 'available_days', 'available_time', 'consultation_fee', 'status']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dr. John Doe'}),
            'specialization': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Heart Surgeon'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'doctor@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., +1234567890'}),
            'qualification': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., MBBS, MD'}),
            'experience': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Years of experience'}),
            'available_days': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Monday, Wednesday, Friday'}),
            'available_time': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 09:00 - 17:00'}),
            'consultation_fee': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Fee'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class AdminAppointmentResolveForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['status', 'admin_remarks']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'admin_remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Add admin remarks...'}),
        }
