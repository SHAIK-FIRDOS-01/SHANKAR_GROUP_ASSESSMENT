let socket = null;

// Initial WebSocket Connection setup on page load
document.addEventListener('DOMContentLoaded', () => {
    initWebSockets();
});

// --- WebSockets Integration ---
function initWebSockets() {
    const wsBadge = document.getElementById('ws-status');
    if (!wsBadge) return; // Not on dashboard page
    
    // Connect to Socket.IO server
    socket = io();
    
    socket.on('connect', () => {
        console.log('Connected to WebSocket server');
        wsBadge.textContent = 'Live';
        wsBadge.className = 'ws-badge connected';
    });
    
    socket.on('disconnect', () => {
        console.log('Disconnected from WebSocket server');
        wsBadge.textContent = 'Offline';
        wsBadge.className = 'ws-badge disconnected';
    });
    
    socket.on('conn_ack', (data) => {
        console.log('WS Connection Ack:', data.message);
    });
    
    // Listen for live updates, trigger notification toast, and trigger reload
    socket.on('task_update', (data) => {
        console.log('Received live update:', data);
        
        const taskTitle = data.task.title;
        let toastTitle = '';
        let toastMsg = '';
        
        switch (data.action) {
            case 'created':
                toastTitle = 'New Task Created';
                toastMsg = `"${taskTitle}" was added by ${data.username}`;
                break;
            case 'updated':
                toastTitle = 'Task Updated';
                toastMsg = `"${taskTitle}" was modified by ${data.username}`;
                break;
            case 'deleted':
                toastTitle = 'Task Deleted';
                toastMsg = `"${taskTitle}" was removed by ${data.username}`;
                break;
        }
        
        showNotificationToast(data.action, toastTitle, toastMsg);
        
        // Trigger server-side dynamic re-render by reloading the page
        setTimeout(() => {
            window.location.reload();
        }, 1200);
    });
}

// --- Toast Notifications Helper ---
function showNotificationToast(action, title, message) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${action}`;
    
    let iconClass = 'fa-info-circle';
    if (action === 'created') iconClass = 'fa-plus-circle';
    if (action === 'updated') iconClass = 'fa-pen-to-square';
    if (action === 'deleted') iconClass = 'fa-trash-can';
    
    toast.innerHTML = `
        <div class="toast-icon"><i class="fa-solid ${iconClass}"></i></div>
        <div class="toast-content">
            <h5>${escapeHTML(title)}</h5>
            <p>${escapeHTML(message)}</p>
        </div>
    `;
    
    toast.onclick = () => toast.remove();
    container.appendChild(toast);
    
    setTimeout(() => {
        if (toast.parentNode) {
            toast.style.animation = 'toastSlideIn 0.3s ease reverse forwards';
            setTimeout(() => toast.remove(), 300);
        }
    }, 3000);
}

// --- Utils ---
function escapeHTML(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}
