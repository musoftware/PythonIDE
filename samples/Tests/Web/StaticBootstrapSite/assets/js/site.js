// Boot Site - your scripts
document.getElementById('year').textContent = new Date().getFullYear();

// Bootstrap form validation (contact.html)
const form = document.getElementById('contactForm');
if (form) {
    form.addEventListener('submit', ev => {
        ev.preventDefault();
        form.classList.add('was-validated');
        if (form.checkValidity()) {
            document.getElementById('sent').classList.remove('d-none');
            form.reset();
            form.classList.remove('was-validated');
        }
    });
}
