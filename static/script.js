document.addEventListener('DOMContentLoaded', function() {
    const fontStyleElement = document.getElementById('fontStyle');
    if (fontStyleElement) {
        fontStyleElement.addEventListener('change', function() {
            console.log('Font Style changed to:', this.value);
        });
    } else {
        console.error('Element with id "fontStyle" not found.');
    }
});


function confirmLogout() {
    const confirmed = confirm("Are you sure you want to log out?");
    return confirmed; // Redirects to the '/logout' Flask route if true
}
