console.log(' TESTING: Notification script starting...');

document.addEventListener('DOMContentLoaded', function() {
    console.log(' DOM loaded, testing notifications...');
    
    setTimeout(function() {
        console.log(' Running notification test...');
        
        // Find the notification panel
        const panel = document.getElementById('incident-notifications-dashboard');
        console.log(' Panel found:', panel);
        
        if (panel) {
            // Force show the panel
            panel.style.display = 'block';
            panel.style.visibility = 'visible';
            panel.style.opacity = '1';
            panel.classList.remove('d-none');
            
            // Update the count
            const countSpan = document.getElementById('notifications-count');
            if (countSpan) {
                countSpan.textContent = '1';
                console.log(' Count updated to 1');
            }
            
            // Update the summary
            const summaryDiv = document.getElementById('notifications-summary');
            if (summaryDiv) {
                summaryDiv.innerHTML = '<strong>TEST: 1 pending assignment (DAVID-NOTIFICATION-TEST)</strong>';
                console.log(' Summary updated');
            }
            
            console.log(' NOTIFICATION PANEL SHOULD NOW BE VISIBLE!');
        } else {
            console.log(' Notification panel not found!');
        }
    }, 3000);
});
