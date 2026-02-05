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

// Show channels verification modal and wait for completion
async function showChannelsModalAndWait(allChannels, missingChannels) {
    return new Promise((resolve) => {
        console.log('📱 Showing channels modal for missing subscriptions');
        
        // Use the existing modal from index.html
        const modal = document.getElementById('channels-modal');
        const channelsList = document.getElementById('channels-list');
        const verifyBtn = document.getElementById('verify-channels-btn');
        
        if (!modal || !channelsList || !verifyBtn) {
            console.warn('⚠️ Channels modal elements not found in DOM');
            resolve(false);
            return;
        }
        
        // Clear existing channels
        channelsList.innerHTML = '';
        
        // Add missing channels to modal
        missingChannels.forEach(channel => {
            const channelEl = document.createElement('div');
            channelEl.className = 'channel-item';
            channelEl.innerHTML = `
                <div class="channel-info">
                    <span class="channel-icon">📺</span>
                    <span class="channel-name">${channel.name || channel.channel_name || channel.id}</span>
                </div>
                <a href="${channel.url || `https://t.me/${channel.id.replace('@', '')}}`}" 
                   target="_blank" class="channel-link">
                    <img src="/img/links.png" alt="@" style="width: 16px; height: 16px;"> فتح
                </a>
            `;
            channelsList.appendChild(channelEl);
        });
        
        // Show modal
        modal.style.display = 'flex';
        
        // Handle verify button
        const handleVerify = async () => {
            verifyBtn.disabled = true;
            verifyBtn.innerHTML = '⏳ جاري التحقق...';
            
            // Re-check subscription
            const recheckResult = await checkSubscriptionStatus();
            
            if (recheckResult) {
                // Success - hide modal and continue
                modal.style.display = 'none';
                if (typeof showToast !== 'undefined') {
                    showToast('✅ تم التحقق من الاشتراك بنجاح!', 'success');
                }
                resolve(true);
            } else {
                // Still not subscribed
                verifyBtn.disabled = false;
                verifyBtn.innerHTML = '<img src="/img/payment-success.svg" alt="تحقق" style="width: 18px; height: 18px; vertical-align: middle; margin-left: 4px;"> تحقق من الاشتراك';
                if (typeof showToast !== 'undefined') {
                    showToast('⚠️ يرجى الاشتراك في جميع القنوات أولاً', 'error');
                }
            }
        };
        
        verifyBtn.onclick = handleVerify;
    });
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

// Check subscription status with server
async function checkSubscriptionStatus() {
    try {
        const userId = TelegramApp?.getUserId();
        if (!userId) {
            console.warn('⚠️ No user ID for subscription check');
            return false;
        }
        
        console.log('🔄 Re-checking subscription status...');
        
        const response = await fetch('/verify-subscription', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId
            })
        });
        
        const result = await response.json();
        console.log('📊 Subscription recheck result:', result);
        
        if (result.success && result.verified) {
            // Save verification status
            localStorage.setItem(`channelsChecked_${userId}`, new Date().toISOString());
            return true;
        }
        
        return false;
        
    } catch (error) {
        console.error('❌ Error checking subscription status:', error);
        return false;
    }
}
