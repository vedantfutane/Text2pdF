document.getElementById('fontStyle').addEventListener('change', function() {
    console.log('Font Style changed to:', this.value);
});


function handleLogout() {
    // Redirect the user to the register page
    window.location.href = '/login';
}