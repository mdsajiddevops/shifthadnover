                        // Permanent fix: ensure panel visibility
                        setTimeout(() => {
                            const panel = document.getElementById('incident-notifications-dashboard');
                            if (panel && data.assignments && data.assignments.length > 0) {
                                panel.style.display = 'block';
                                console.log(' Showing notification panel');
                            }
                        }, 100);
