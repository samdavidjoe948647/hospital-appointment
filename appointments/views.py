from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Q
from django.contrib.auth.models import User
import datetime
import csv

from .models import Department, Doctor, Patient, Appointment
from .forms import (
    PatientRegistrationForm,
    PatientProfileForm,
    AppointmentBookingForm,
    AppointmentRescheduleForm,
    DepartmentForm,
    DoctorForm,
    AdminAppointmentResolveForm
)

# Helper check for admin access
def admin_required(user):
    return user.is_authenticated and user.is_staff

# ----------------- PUBLIC / AUTH VIEWS -----------------

def home(request):
    departments = Department.objects.filter(status='Active')
    context = {
        'departments': departments,
        'departments_count': Department.objects.filter(status='Active').count(),
        'doctors_count': Doctor.objects.filter(status='Active').count(),
        'patients_count': Patient.objects.count(),
    }
    return render(request, 'patient/home.html', context)


def patient_register(request):
    if request.user.is_authenticated:
        return redirect('patient_dashboard')
        
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            # Create User
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            # Create Patient Profile
            Patient.objects.create(
                user=user,
                gender=form.cleaned_data['gender'],
                date_of_birth=form.cleaned_data['date_of_birth'],
                phone=form.cleaned_data['phone'],
                address=form.cleaned_data['address']
            )
            
            messages.success(request, "Registration successful! You can now log in.")
            return redirect('patient_login')
    else:
        form = PatientRegistrationForm()
    return render(request, 'patient/register.html', {'form': form})


def patient_login(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        return redirect('patient_dashboard')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if not user.is_staff:
                login(request, user)
                messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                return redirect('patient_dashboard')
            else:
                messages.error(request, "Admins should log in through the Admin login portal.")
        else:
            messages.error(request, "Invalid username or password.")
    return render(request, 'patient/login.html')


def admin_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_staff:
                login(request, user)
                messages.success(request, f"Welcome Administrator, {user.first_name or user.username}!")
                return redirect('admin_dashboard')
            else:
                messages.error(request, "Access denied. Standard user accounts cannot log in here.")
        else:
            messages.error(request, "Invalid administrator credentials.")
    return render(request, 'admin/login.html')


def user_logout(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')


@login_required
def patient_change_password(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        user = request.user
        if not user.check_password(old_password):
            messages.error(request, "Your current password was entered incorrectly.")
        elif new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
        elif len(new_password) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
        else:
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)  # Keep the user logged in
            messages.success(request, "Your password was successfully updated!")
            return redirect('patient_dashboard')
    return render(request, 'patient/change_password.html')


def patient_forgot_password(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        try:
            user = User.objects.get(username=username, email=email, is_staff=False)
            # Simulate password reset by changing it to sydney123 for demo
            temp_pass = "sydney123"
            user.set_password(temp_pass)
            user.save()
            messages.success(request, f"Password reset simulation successful! Your temporary password is: '{temp_pass}'")
            return redirect('patient_login')
        except User.DoesNotExist:
            messages.error(request, "No matching patient account was found with the provided credentials.")
    return render(request, 'patient/forgot_password.html')


# ----------------- PATIENT MODULE -----------------

@login_required
def patient_dashboard(request):
    try:
        patient = request.user.patient_profile
    except Patient.DoesNotExist:
        messages.error(request, "Administrative accounts do not have patient profiles.")
        return redirect('admin_dashboard')
        
    appointments = Appointment.objects.filter(patient=patient).order_by('-created_at')
    
    # Calculate stats matching the 4 required dashboard widgets
    upcoming_appts = appointments.filter(status='Approved').count()
    pending_appts = appointments.filter(status='Pending').count()
    completed_appts = appointments.filter(status='Completed').count()
    cancelled_appts = appointments.filter(status='Cancelled').count()
    
    context = {
        'patient': patient,
        'recent_appointments': appointments[:5],
        'upcoming_appts': upcoming_appts,
        'pending_appts': pending_appts,
        'completed_appts': completed_appts,
        'cancelled_appts': cancelled_appts,
        'total_appts': appointments.count(),
    }
    return render(request, 'patient/dashboard.html', context)


@login_required
def patient_profile(request):
    try:
        patient = request.user.patient_profile
    except Patient.DoesNotExist:
        return redirect('admin_dashboard')
        
    if request.method == 'POST':
        form = PatientProfileForm(request.POST, instance=request.user, patient=patient)
        if form.is_valid():
            form.save()
            # Update patient profile fields
            patient.phone = form.cleaned_data['phone']
            patient.address = form.cleaned_data['address']
            patient.gender = form.cleaned_data['gender']
            patient.date_of_birth = form.cleaned_data['date_of_birth']
            patient.save()
            messages.success(request, "Your profile has been updated successfully!")
            return redirect('patient_profile')
    else:
        form = PatientProfileForm(instance=request.user, patient=patient)
    return render(request, 'patient/profile.html', {'form': form})


@login_required
def patient_book_appointment(request):
    try:
        patient = request.user.patient_profile
    except Patient.DoesNotExist:
        return redirect('admin_dashboard')
        
    if request.method == 'POST':
        form = AppointmentBookingForm(request.POST, patient=patient)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.patient = patient
            appointment.status = 'Pending'
            appointment.save()
            messages.success(request, "Your appointment has been booked successfully and is pending approval.")
            return redirect('patient_dashboard')
    else:
        form = AppointmentBookingForm(patient=patient)
        
    return render(request, 'patient/book_appointment.html', {'form': form})


@login_required
def patient_appointment_history(request):
    try:
        patient = request.user.patient_profile
    except Patient.DoesNotExist:
        return redirect('admin_dashboard')
        
    appointments = Appointment.objects.filter(patient=patient).order_by('-appointment_date', '-appointment_time')
    return render(request, 'patient/appointment_history.html', {'appointments': appointments})


@login_required
def patient_cancel_appointment(request, appointment_id):
    try:
        patient = request.user.patient_profile
    except Patient.DoesNotExist:
        return redirect('admin_dashboard')
        
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=patient)
    if appointment.status in ['Pending', 'Approved']:
        appointment.status = 'Cancelled'
        appointment.save()
        messages.success(request, f"Appointment #{appointment.id} was successfully cancelled.")
    else:
        messages.error(request, "This appointment cannot be cancelled because it is already completed or cancelled.")
    return redirect('patient_appointment_history')


@login_required
def patient_reschedule_appointment(request, appointment_id):
    try:
        patient = request.user.patient_profile
    except Patient.DoesNotExist:
        return redirect('admin_dashboard')
        
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=patient)
    
    if appointment.status != 'Pending':
        messages.error(request, "Rescheduling is only allowed for Pending appointments.")
        return redirect('patient_appointment_history')
        
    if request.method == 'POST':
        form = AppointmentRescheduleForm(request.POST, instance=appointment, patient=patient)
        if form.is_valid():
            form.save()
            messages.success(request, f"Appointment #{appointment.id} has been successfully rescheduled.")
            return redirect('patient_dashboard')
    else:
        form = AppointmentRescheduleForm(instance=appointment, patient=patient)
        
    return render(request, 'patient/reschedule.html', {'form': form, 'appointment': appointment})


@login_required
def patient_doctors(request):
    try:
        patient = request.user.patient_profile
    except Patient.DoesNotExist:
        return redirect('admin_dashboard')
    doctors = Doctor.objects.filter(status='Active').select_related('department')
    return render(request, 'patient/doctors.html', {'doctors': doctors})


@login_required
def patient_appointment_detail(request, appointment_id):
    try:
        patient = request.user.patient_profile
    except Patient.DoesNotExist:
        return redirect('admin_dashboard')
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=patient)
    return render(request, 'patient/appointment_detail.html', {'appointment': appointment})


# ----------------- ADMIN MODULE -----------------

@user_passes_test(admin_required, login_url='admin_login')
def admin_dashboard(request):
    patients_count = Patient.objects.count()
    doctors_count = Doctor.objects.count()
    depts_count = Department.objects.count()
    appts_count = Appointment.objects.count()
    
    pending_appts = Appointment.objects.filter(status='Pending').count()
    approved_appts = Appointment.objects.filter(status='Approved').count()
    completed_appts = Appointment.objects.filter(status='Completed').count()
    cancelled_appts = Appointment.objects.filter(status='Cancelled').count()
    rejected_appts = Appointment.objects.filter(status='Rejected').count()
    
    today = datetime.date.today()
    todays_appointments = Appointment.objects.filter(appointment_date=today).count()
    
    recent_appointments = Appointment.objects.order_by('-created_at')[:5]
    
    # Compile chart datasets
    # 1. Monthly appointments (counts for last 6 months)
    months_labels = []
    months_counts = []
    for i in range(5, -1, -1):
        # Estimate month offsets safely
        d = today - datetime.timedelta(days=i*30)
        month_name = d.strftime('%B')
        count = Appointment.objects.filter(appointment_date__year=d.year, appointment_date__month=d.month).count()
        months_labels.append(month_name)
        months_counts.append(count)
        
    # 2. Department-wise appointments
    departments_list = Department.objects.filter(status='Active')
    dept_labels = []
    dept_counts = []
    for dept in departments_list:
        dept_labels.append(dept.department_name)
        dept_counts.append(Appointment.objects.filter(department=dept).count())
        
    # 3. Doctor-wise appointments
    doctors_list = Doctor.objects.filter(status='Active')
    doc_labels = []
    doc_counts = []
    for doc in doctors_list:
        doc_labels.append(doc.full_name)
        doc_counts.append(Appointment.objects.filter(doctor=doc).count())
        
    context = {
        'patients_count': patients_count,
        'doctors_count': doctors_count,
        'depts_count': depts_count,
        'appts_count': appts_count,
        'pending_appts': pending_appts,
        'approved_appts': approved_appts,
        'completed_appts': completed_appts,
        'cancelled_appts': cancelled_appts,
        'rejected_appts': rejected_appts,
        'todays_appointments': todays_appointments,
        'recent_appointments': recent_appointments,
        
        # Charts Context
        'months_labels': months_labels,
        'months_counts': months_counts,
        'dept_labels': dept_labels,
        'dept_counts': dept_counts,
        'doc_labels': doc_labels,
        'doc_counts': doc_counts,
    }
    return render(request, 'admin/dashboard.html', context)


# --- DEPARTMENTS CRUD ---
@user_passes_test(admin_required, login_url='admin_login')
def admin_manage_departments(request):
    departments = Department.objects.all().annotate(num_doctors=Count('doctors'))
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Department added successfully!")
            return redirect('admin_manage_departments')
    else:
        form = DepartmentForm()
    return render(request, 'admin/departments.html', {'departments': departments, 'form': form})


@user_passes_test(admin_required, login_url='admin_login')
def admin_edit_department(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, "Department updated successfully!")
            return redirect('admin_manage_departments')
    else:
        form = DepartmentForm(instance=department)
    return render(request, 'admin/edit_department.html', {'form': form, 'department': department})


@user_passes_test(admin_required, login_url='admin_login')
def admin_delete_department(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    department.delete()
    messages.success(request, "Department deleted successfully!")
    return redirect('admin_manage_departments')


# --- DOCTORS CRUD ---
@user_passes_test(admin_required, login_url='admin_login')
def admin_manage_doctors(request):
    doctors = Doctor.objects.all().select_related('department')
    if request.method == 'POST':
        form = DoctorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Doctor added successfully!")
            return redirect('admin_manage_doctors')
    else:
        form = DoctorForm()
    return render(request, 'admin/doctors.html', {'doctors': doctors, 'form': form})


@user_passes_test(admin_required, login_url='admin_login')
def admin_edit_doctor(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    if request.method == 'POST':
        form = DoctorForm(request.POST, instance=doctor)
        if form.is_valid():
            form.save()
            messages.success(request, "Doctor updated successfully!")
            return redirect('admin_manage_doctors')
    else:
        form = DoctorForm(instance=doctor)
    return render(request, 'admin/edit_doctor.html', {'form': form, 'doctor': doctor})


@user_passes_test(admin_required, login_url='admin_login')
def admin_delete_doctor(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    doctor.delete()
    messages.success(request, "Doctor deleted successfully!")
    return redirect('admin_manage_doctors')


# --- PATIENTS LIST ---
@user_passes_test(admin_required, login_url='admin_login')
def admin_manage_patients(request):
    query = request.GET.get('q', '')
    patients = Patient.objects.all().select_related('user').annotate(num_appts=Count('appointments'))
    
    if query:
        patients = patients.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(phone__icontains=query) |
            Q(user__username__icontains=query)
        )
    
    return render(request, 'admin/patients.html', {'patients': patients, 'query': query})


@user_passes_test(admin_required, login_url='admin_login')
def admin_patient_detail(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    appointments = Appointment.objects.filter(patient=patient).order_by('-appointment_date', '-appointment_time')
    return render(request, 'admin/patient_detail.html', {'patient': patient, 'appointments': appointments})


# --- APPOINTMENTS CONTROL ---
@user_passes_test(admin_required, login_url='admin_login')
def admin_manage_appointments(request):
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    dept_filter = request.GET.get('department_id', '')
    doc_filter = request.GET.get('doctor_id', '')
    
    appointments = Appointment.objects.all().select_related('patient', 'patient__user', 'doctor', 'department').order_by('-created_at')
    
    if query:
        appointments = appointments.filter(
            Q(patient__user__first_name__icontains=query) |
            Q(patient__user__last_name__icontains=query) |
            Q(doctor__full_name__icontains=query) |
            Q(reason__icontains=query)
        )
        
    if status_filter:
        appointments = appointments.filter(status=status_filter)
        
    if date_filter:
        appointments = appointments.filter(appointment_date=date_filter)
        
    if dept_filter:
        appointments = appointments.filter(department_id=dept_filter)
        
    if doc_filter:
        appointments = appointments.filter(doctor_id=doc_filter)
        
    context = {
        'appointments': appointments,
        'query': query,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'dept_filter': int(dept_filter) if dept_filter else '',
        'doc_filter': int(doc_filter) if doc_filter else '',
        'departments': Department.objects.all(),
        'doctors': Doctor.objects.all(),
    }
    return render(request, 'admin/appointments.html', context)


@user_passes_test(admin_required, login_url='admin_login')
def admin_update_appointment_status(request, appointment_id, status):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    if status in ['Approved', 'Rejected', 'Completed', 'Cancelled']:
        appointment.status = status
        appointment.save()
        messages.success(request, f"Appointment #{appointment.id} status updated to {status}.")
    else:
        messages.error(request, "Invalid status choice.")
    
    referer = request.META.get('HTTP_REFERER')
    if referer and ('appointments' in referer or 'dashboard' in referer or 'patient' in referer):
        return redirect(referer)
    return redirect('admin_manage_appointments')


@user_passes_test(admin_required, login_url='admin_login')
def admin_update_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    if request.method == 'POST':
        form = AdminAppointmentResolveForm(request.POST, instance=appointment)
        if form.is_valid():
            form.save()
            messages.success(request, f"Appointment #{appointment.id} resolved successfully with status: {appointment.status}.")
            return redirect('admin_manage_appointments')
    else:
        form = AdminAppointmentResolveForm(instance=appointment)
    return render(request, 'admin/update_appointment.html', {'form': form, 'appointment': appointment})


# --- REPORTS GENERATION ---
@user_passes_test(admin_required, login_url='admin_login')
def admin_reports(request):
    report_type = request.GET.get('report_type', '')
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    doctor_id = request.GET.get('doctor_id', '')
    department_id = request.GET.get('department_id', '')
    patient_id = request.GET.get('patient_id', '')
    
    appointments = None
    stats = {}
    
    # Filter queryset baseline
    qs = Appointment.objects.all().select_related('patient', 'patient__user', 'doctor', 'department').order_by('appointment_date', 'appointment_time')
    
    is_filtered = False
    
    if report_type == 'daily':
        target_date = request.GET.get('daily_date', str(datetime.date.today()))
        if target_date:
            qs = qs.filter(appointment_date=target_date)
            is_filtered = True
            
    elif report_type == 'monthly':
        target_month_str = request.GET.get('monthly_month', '') # Expects 'YYYY-MM'
        if target_month_str:
            try:
                yr, mn = map(int, target_month_str.split('-'))
                qs = qs.filter(appointment_date__year=yr, appointment_date__month=mn)
                is_filtered = True
            except ValueError:
                pass
                
    elif report_type == 'doctor':
        if doctor_id:
            qs = qs.filter(doctor_id=doctor_id)
            is_filtered = True
            
    elif report_type == 'department':
        if department_id:
            qs = qs.filter(department_id=department_id)
            is_filtered = True
            
    elif report_type == 'patient_history':
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
            is_filtered = True
            
    elif report_type == 'date_range' or (start_date_str and end_date_str):
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                qs = qs.filter(appointment_date__range=[start_date, end_date])
                is_filtered = True
            except ValueError:
                messages.error(request, "Invalid date range format.")
                
    if is_filtered or request.GET:
        appointments = qs
        stats = {
            'total': appointments.count(),
            'pending': appointments.filter(status='Pending').count(),
            'approved': appointments.filter(status='Approved').count(),
            'completed': appointments.filter(status='Completed').count(),
            'cancelled': appointments.filter(status='Cancelled').count(),
            'rejected': appointments.filter(status='Rejected').count(),
        }
    
    context = {
        'report_type': report_type,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'doctor_id': int(doctor_id) if doctor_id else '',
        'department_id': int(department_id) if department_id else '',
        'patient_id': int(patient_id) if patient_id else '',
        'daily_date': request.GET.get('daily_date', str(datetime.date.today())),
        'monthly_month': request.GET.get('monthly_month', ''),
        
        'appointments': appointments,
        'stats': stats,
        
        # Options lists
        'doctors': Doctor.objects.all(),
        'departments': Department.objects.all(),
        'patients': Patient.objects.all().select_related('user'),
    }
    return render(request, 'admin/reports.html', context)


@user_passes_test(admin_required, login_url='admin_login')
def admin_reports_export(request):
    report_type = request.GET.get('report_type', '')
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    doctor_id = request.GET.get('doctor_id', '')
    department_id = request.GET.get('department_id', '')
    patient_id = request.GET.get('patient_id', '')
    
    # Filter queryset baseline
    qs = Appointment.objects.all().select_related('patient', 'patient__user', 'doctor', 'department').order_by('appointment_date', 'appointment_time')
    
    if report_type == 'daily':
        target_date = request.GET.get('daily_date', str(datetime.date.today()))
        if target_date:
            qs = qs.filter(appointment_date=target_date)
            
    elif report_type == 'monthly':
        target_month_str = request.GET.get('monthly_month', '')
        if target_month_str:
            try:
                yr, mn = map(int, target_month_str.split('-'))
                qs = qs.filter(appointment_date__year=yr, appointment_date__month=mn)
            except ValueError:
                pass
                
    elif report_type == 'doctor':
        if doctor_id:
            qs = qs.filter(doctor_id=doctor_id)
            
    elif report_type == 'department':
        if department_id:
            qs = qs.filter(department_id=department_id)
            
    elif report_type == 'patient_history':
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
            
    elif report_type == 'date_range' or (start_date_str and end_date_str):
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                qs = qs.filter(appointment_date__range=[start_date, end_date])
            except ValueError:
                pass

    # Create CSV HTTP Response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="sydney_clinic_report_{datetime.date.today()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Appointment ID', 'Patient Name', 'Patient Phone', 'Doctor Name', 'Department', 'Date', 'Time', 'Reason', 'Status', 'Admin Remarks'])
    
    for appt in qs:
        writer.writerow([
            appt.id,
            appt.patient.user.get_full_name() or appt.patient.user.username,
            appt.patient.phone,
            appt.doctor.full_name,
            appt.department.department_name,
            appt.appointment_date,
            appt.appointment_time.strftime('%H:%M:%S'),
            appt.reason,
            appt.status,
            appt.admin_remarks
        ])
        
    return response


# ----------------- JSON API ENDPOINT -----------------

def get_doctors_by_department(request):
    department_id = request.GET.get('department_id')
    if department_id:
        doctors = Doctor.objects.filter(department_id=department_id, status='Active').values('id', 'full_name', 'specialization', 'available_days', 'available_time', 'consultation_fee')
        # Return full_name mapped to doctor_name to keep JS dropdown parser happy
        doctors_mapped = []
        for doc in doctors:
            doctors_mapped.append({
                'id': doc['id'],
                'doctor_name': doc['full_name'],
                'specialization': doc['specialization'],
                'available_days': doc['available_days'],
                'available_time': doc['available_time'],
                'consultation_fee': str(doc['consultation_fee']),
            })
        return JsonResponse(doctors_mapped, safe=False)
    return JsonResponse([], safe=False)
