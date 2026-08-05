document.addEventListener('DOMContentLoaded', function () {
    // 1. Dynamic Doctor Dropdown based on Department
    const departmentSelect = document.getElementById('id_department');
    const doctorSelect = document.getElementById('id_doctor');

    if (departmentSelect && doctorSelect) {
        departmentSelect.addEventListener('change', function () {
            const deptId = this.value;
            
            // Clear existing doctor options
            doctorSelect.innerHTML = '<option value="">--------- Choose Doctor ---------</option>';
            
            if (!deptId) return;

            // Fetch doctors for selected department
            fetch(`/ajax/get-doctors-by-department/?department_id=${deptId}`)
                .then(response => response.json())
                .then(data => {
                    data.forEach(doctor => {
                        const option = document.createElement('option');
                        option.value = doctor.id;
                        option.textContent = `${doctor.doctor_name} (${doctor.specialization})`;
                        doctorSelect.appendChild(option);
                    });
                })
                .catch(error => console.error('Error fetching doctors:', error));
        });
    }

    // 2. Auto-dismiss alerts after 4 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            // Using Bootstrap's alert close API if available, else standard DOM removal
            if (window.bootstrap && bootstrap.Alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            } else {
                alert.style.transition = 'opacity 0.5s ease';
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 500);
            }
        }, 4000);
    });

    // 3. Global Confirm Actions
    const confirmButtons = document.querySelectorAll('.btn-confirm');
    confirmButtons.forEach(button => {
        button.addEventListener('click', function (e) {
            const message = this.getAttribute('data-confirm-msg') || 'Are you sure you want to perform this action?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
});
