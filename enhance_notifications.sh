#!/bin/bash
echo 'Making Dashboard Notifications More Prominent'
echo '============================================='

# Create backup
cp templates/dashboard.html templates/dashboard.html.backup

# Check if enhancement already applied
if grep -q 'notificationPulse' templates/dashboard.html; then
    echo 'Enhancement already applied'
else
    echo 'Adding enhanced notification styling...'
    
    # Add CSS before closing head tag
    sed -i '/<\/head>/i\
<style>\
/* Enhanced Dashboard Notification Styling */\
#incident-notifications-dashboard {\
    background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%) !important;\
    border: 3px solid #e67e22 !important;\
    border-radius: 10px !important;\
    box-shadow: 0 4px 15px rgba(230, 126, 34, 0.5) !important;\
    margin: 20px 0 !important;\
    padding: 20px !important;\
    position: relative !important;\
    z-index: 1000 !important;\
    animation: notificationPulse 2s ease-in-out infinite alternate !important;\
}\
\
#incident-notifications-dashboard::before {\
    content:  !important;\
 font-size: 24px !important;\
 position: absolute !important;\
 left: -15px !important;\
 top: -10px !important;\
 background: #e67e22 !important;\
 border-radius: 50% !important;\
 width: 40px !important;\
 height: 40px !important;\
 display: flex !important;\
 align-items: center !important;\
 justify-content: center !important;\
 animation: bounce 1s infinite !important;\
}\
\
#incident-notifications-dashboard .alert-heading {\
 color: #d35400 !important;\
 font-weight: bold !important;\
 font-size: 20px !important;\
 text-shadow: 1px 1px 2px rgba(0,0,0,0.1) !important;\
}\
\
#notifications-count {\
 background: #e74c3c !important;\
 color: white !important;\
 padding: 8px 12px !important;\
 border-radius: 20px !important;\
 font-weight: bold !important;\
 font-size: 18px !important;\
 margin: 0 5px !important;\
 display: inline-block !important;\
 min-width: 35px !important;\
 text-align: center !important;\
 animation: countPulse 1s ease-in-out infinite alternate !important;\
 box-shadow: 0 2px 10px rgba(231, 76, 60, 0.4) !important;\
}\
\
@keyframes notificationPulse {\
 0% { \
 transform: scale(1);\
 box-shadow: 0 4px 15px rgba(230, 126, 34, 0.5);\
 }\
 100% { \
 transform: scale(1.02);\
 box-shadow: 0 8px 25px rgba(230, 126, 34, 0.7);\
 }\
}\
\
@keyframes bounce {\
 0%, 20%, 50%, 80%, 100% {\
 transform: translateY(0);\
 }\
 40% {\
 transform: translateY(-10px);\
 }\
 60% {\
 transform: translateY(-5px);\
 }\
}\
\
@keyframes countPulse {\
 0% { \
 background: #e74c3c;\
 transform: scale(1);\
 }\
 100% { \
 background: #c0392b;\
 transform: scale(1.15);\
 }\
}\
</style>' templates/dashboard.html

 echo 'Enhanced styling added'
fi

echo ''
echo 'ENHANCEMENT COMPLETE!'
echo 'Notifications will now have:'
echo ' Bright gradient background'
echo ' Animated warning icon' 
echo ' Pulsing animation'
echo ' Large red count badge'
