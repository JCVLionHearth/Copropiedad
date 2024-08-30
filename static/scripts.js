document.addEventListener("DOMContentLoaded", function() {
    const form = document.getElementById('ticketForm');
    const messageDiv = document.getElementById('message');
    form.addEventListener('submit', function(event) {
        event.preventDefault();
        const ticket = document.getElementById('ticket').value;
        fetch('/registrar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `ticket=${ticket}`
        })
        .then(response => response.json())
        .then(data => {
            messageDiv.innerHTML = `<p>${data.message}</p>`;
            if (data.status === 'success') {
                messageDiv.style.color = 'green';
            } else {
                messageDiv.style.color = 'red';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            messageDiv.innerHTML = '<p>Ocurrió un error, por favor intente de nuevo.</p>';
            messageDiv.style.color = 'red';
        });
    });
 });

