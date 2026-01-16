// Main JavaScript file for Interac e-Transfer app

// Add any global JavaScript functionality here
document.addEventListener('DOMContentLoaded', function () {
    // Initialize any global functionality
    console.log('Interac e-Transfer app loaded');
});

// Modal Component Functions
function showInfoModal(title, message) {
    const modal = document.getElementById('infoModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalMessage = document.getElementById('modalMessage');

    if (modal && modalTitle && modalMessage) {
        modalTitle.textContent = title || 'Information';
        modalMessage.innerHTML = message || ''; // Use innerHTML to support <br> or newlines if converted
        modal.style.display = 'flex';
    }
}

function closeInfoModal() {
    const modal = document.getElementById('infoModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

