from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from datetime import date, timedelta

from .models import Department, Doctor, Patient, Appointment

class HospitalAppointmentTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create department
        self.dept = Department.objects.create(department_name="Cardiology")
        
        # Create doctor
        self.doctor = Doctor.objects.create(
            full_name="Dr. Smith",
            specialization="Heart Specialist",
            department=self.dept,
            email="smith@hospital.com",
            phone="1234567890"
        )
        
        # Create patient user
        self.user = User.objects.create_user(
            username="john_patient",
            password="patientpassword",
            email="john@example.com",
            first_name="John",
            last_name="Doe"
        )
        self.patient = Patient.objects.create(
            user=self.user,
            phone="9876543210",
            address="123 Health Ave"
        )
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            username="admin_user",
            password="adminpassword",
            email="admin@hospital.com",
            is_staff=True
        )

    def test_patient_registration(self):
        # Test registering a new patient
        response = self.client.post(reverse('patient_register'), {
            'username': 'new_patient',
            'first_name': 'Alice',
            'last_name': 'Smith',
            'email': 'alice@example.com',
            'gender': 'Female',
            'date_of_birth': '1995-05-15',
            'password': 'alicepassword',
            'confirm_password': 'alicepassword',
            'phone': '5555555555',
            'address': '456 Medical Way'
        })
        self.assertEqual(response.status_code, 302) # Redirect to login page
        self.assertTrue(User.objects.filter(username='new_patient').exists())
        user = User.objects.get(username='new_patient')
        self.assertEqual(user.patient_profile.phone, '5555555555')

    def test_patient_login(self):
        # Test logging in as patient
        response = self.client.post(reverse('patient_login'), {
            'username': 'john_patient',
            'password': 'patientpassword'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('patient_dashboard'))

    def test_admin_login(self):
        # Test logging in as staff
        response = self.client.post(reverse('admin_login'), {
            'username': 'admin_user',
            'password': 'adminpassword'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('admin_dashboard'))

    def test_unauthenticated_dashboard_redirect(self):
        # Unauthenticated users should be redirected to login
        response = self.client.get(reverse('patient_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_patient_cannot_access_admin_dashboard(self):
        # Log in as normal patient
        self.client.login(username='john_patient', password='patientpassword')
        response = self.client.get(reverse('admin_dashboard'))
        # Should redirect to admin login page (user_passes_test behavior)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin-panel/login/', response.url)

    def test_book_appointment(self):
        self.client.login(username='john_patient', password='patientpassword')
        
        tomorrow = date.today() + timedelta(days=1)
        response = self.client.post(reverse('patient_book_appointment'), {
            'department': self.dept.id,
            'doctor': self.doctor.id,
            'appointment_date': tomorrow.strftime('%Y-%m-%d'),
            'appointment_time': '10:00:00',
            'reason': 'Annual general cardiology check-up.'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Appointment.objects.filter(patient=self.patient).exists())
        appt = Appointment.objects.get(patient=self.patient)
        self.assertEqual(appt.status, 'Pending')
        self.assertEqual(appt.doctor, self.doctor)

    def test_book_appointment_past_date_fails(self):
        self.client.login(username='john_patient', password='patientpassword')
        
        yesterday = date.today() - timedelta(days=1)
        response = self.client.post(reverse('patient_book_appointment'), {
            'department': self.dept.id,
            'doctor': self.doctor.id,
            'appointment_date': yesterday.strftime('%Y-%m-%d'),
            'appointment_time': '10:00:00',
            'reason': 'Failing past booking test.'
        })
        # Should render form with error, status 200
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Appointment.objects.filter(reason='Failing past booking test.').exists())

    def test_cancel_appointment(self):
        # Create booking first
        tomorrow = date.today() + timedelta(days=1)
        appt = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            department=self.dept,
            appointment_date=tomorrow,
            appointment_time='10:00:00',
            reason='Cancel test',
            status='Pending'
        )
        
        self.client.login(username='john_patient', password='patientpassword')
        response = self.client.post(reverse('patient_cancel_appointment', args=[appt.id]))
        self.assertEqual(response.status_code, 302)
        
        appt.refresh_from_db()
        self.assertEqual(appt.status, 'Cancelled')

    def test_admin_update_appointment_status(self):
        # Create booking
        tomorrow = date.today() + timedelta(days=1)
        appt = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            department=self.dept,
            appointment_date=tomorrow,
            appointment_time='10:00:00',
            reason='Status change test',
            status='Pending'
        )
        
        # Log in as admin
        self.client.login(username='admin_user', password='adminpassword')
        response = self.client.get(reverse('admin_update_appointment_status', args=[appt.id, 'Approved']))
        self.assertEqual(response.status_code, 302)
        
        appt.refresh_from_db()
        self.assertEqual(appt.status, 'Approved')
