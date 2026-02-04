// =====================================
// 🔒 Mandatory Channels Verification System
// =====================================

// Check if user subscribed to required channels
async function checkRequiredChannels() {
    console.log('🔍 Checking required channels...');
    
    try {
        // Check if user already verified today
        const lastCheck = localStorage.getItem('channelsChecked');
        if (lastCheck) {
            const lastCheckTime = new Date(lastCheck);
            const now = new Date();
            const hoursSinceCheck = (now - lastCheckTime) / (1000 * 60 * 60);
            
            // Check once per day (24 hours)
            if (hoursSinceCheck < 24) {
                console.log('✅ Channels already verified today');
                return true;
            }
        }

        // Use required channels from CONFIG
        const requiredChannels = window.CONFIG?.REQUIRED_CHANNELS || [];
        
        console.log(`📢 Found ${requiredChannels.length} required channels from CONFIG`);
        
        if (requiredChannels.length === 0) {
            console.log('ℹ️ No required channels configured');
            localStorage.setItem('channelsChecked', new Date().toISOString());
            return true;
        }

        // Also fetch additional channels from admin panel
        try {
            const response = await fetch(`${window.CONFIG?.API_BASE_URL || '/api'}/admin/channels`);
            const result = await response.json();
            
            if (result.success && result.data && result.data.length > 0) {
                console.log(`📡 Found ${result.data.length} additional channels from admin`);
                // Merge with required channels
                result.data.forEach(channel => {
                    if (!requiredChannels.find(c => c.id === channel.channel_id)) {
                        requiredChannels.push({
                            id: channel.channel_id,
                            name: channel.channel_name,
                            url: channel.channel_url
                        });
                    }
                });
            }
        } catch (apiError) {
            console.warn('⚠️ Could not fetch admin channels:', apiError);
        }

        // Show channels modal
        showChannelsModal(requiredChannels);
        return false;

    } catch (error) {
        console.error('❌ Error checking channels:', error);
        // On error, allow user to continue
        return true;
    }
}

// Show channels verification modal
function showChannelsModal(channels) {
    console.log('📱 Showing channels modal with', channels.length, 'channels');
    
    // لا تعرض المودال الديناميكي - استخدم المودال الموجود في index.html
    console.log('✅ Using existing channels modal from index.html');
    return;
}

// Mark channel as opened when user clicks the link
window.markChannelAsOpened = function(channelId) {
    console.log('📢 Marking channel as opened:', channelId);
    
    if (window.channelStatus) {
        // Wait 1 second to simulate user opening the channel
        setTimeout(() => {
            window.channelStatus[channelId] = true;
            const statusElement = document.getElementById(`status-${channelId}`);
            if (statusElement) {
                statusElement.classList.remove('not-subscribed');
                statusElement.classList.add('subscribed');
                statusElement.innerHTML = '<img src="/img/payment-success.svg" style="width: 16px; height: 16px;">';
                console.log('✅ Channel marked as subscribed:', channelId);
            }
        }, 1000);
    }
};

// Verify all channels subscriptions
window.verifySubscriptions = function() {
    console.log('🔍 Verifying subscriptions...');
    console.log('Channel Status:', window.channelStatus);
    
    if (!window.channelStatus) {
        console.error('❌ Channel status not found');
        return;
    }

    // Check if user opened all channels
    const allChannelsOpened = Object.values(window.channelStatus).every(status => status === true);

    if (!allChannelsOpened) {
        console.log('⚠️ Not all channels opened yet');
        showToast('⚠️ يرجى فتح جميع القنوات أولاً!', 'warning');
        return;
    }

    console.log('✅ All channels opened, marking as verified');
    
    // Mark as verified
    localStorage.setItem('channelsChecked', new Date().toISOString());
    
    // Close modal
    const modal = document.getElementById('channelsModal');
    if (modal) {
        modal.classList.remove('active');
        setTimeout(() => modal.remove(), 300);
    }

    // Reload to show main content
    showToast('<img src="/img/payment-success.svg" style="width: 16px; height: 16px; vertical-align: middle;"> تم التحقق بنجاح! مرحباً بك 🎉', 'success');
    setTimeout(() => {
        console.log('🔄 Reloading page...');
        window.location.reload();
    }, 1000);
};
