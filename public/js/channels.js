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
    
    // Track which channels user opened
    const channelStatus = {};
    channels.forEach(channel => {
        const channelId = channel.id || channel.channel_id;
        channelStatus[channelId] = false;
    });

    const modalHTML = `
        <div class="modal-overlay active" id="channelsModal">
            <div class="modal-content">
                <h2>🔒 الانضمام للقنوات الإجبارية</h2>
                <p>يرجى الانضمام إلى القنوات التالية للمتابعة:</p>
                
                <div class="channels-list">
                    ${channels.map(channel => {
                        const channelId = channel.id || channel.channel_id;
                        const channelName = channel.name || channel.channel_name;
                        const channelUrl = channel.url || channel.channel_url;
                        return `
                        <div class="channel-item" data-channel-id="${channelId}">
                            <div class="channel-info">
                                <h3>${channelName}</h3>
                                <p style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">${channelId}</p>
                            </div>
                            <div class="channel-actions">
                                <a href="${channelUrl}" 
                                   target="_blank" 
                                   class="channel-link"
                                   onclick="markChannelAsOpened('${channelId}')">
                                    📢 اشترك هنا
                                </a>
                                <span class="channel-status not-subscribed" id="status-${channelId}">
                                    <img src="/img/payment-failure.svg" alt="✗" style="width: 18px; height: 18px;">
                                </span>
                            </div>
                        </div>
                    `}).join('')}
                </div>
                
                <button class="verify-btn" onclick="verifySubscriptions()">
                    <img src="/img/payment-success.svg" style="width: 16px; height: 16px; vertical-align: middle;"> تحقق من الاشتراك
                </button>
            </div>
        </div>
    `;

    // Add modal to body
    const existingModal = document.getElementById('channelsModal');
    if (existingModal) {
        existingModal.remove();
    }
    document.body.insertAdjacentHTML('beforeend', modalHTML);

    // Store channel status globally
    window.channelStatus = channelStatus;
    console.log('✅ Modal displayed successfully');
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
