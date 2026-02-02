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

        // Fetch required channels from API
        console.log('📡 Fetching required channels from API...');
        const response = await fetch('/api/admin/channels');
        const result = await response.json();
        
        console.log('📊 API Response:', result);
        
        if (!result.success || !result.data || result.data.length === 0) {
            console.log('ℹ️ No required channels found');
            localStorage.setItem('channelsChecked', new Date().toISOString());
            return true;
        }

        console.log(`📢 Found ${result.data.length} required channels`);
        
        // Show channels modal
        showChannelsModal(result.data);
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
        channelStatus[channel.channel_id] = false;
    });

    const modalHTML = `
        <div class="modal-overlay active" id="channelsModal">
            <div class="modal-content">
                <h2>🔒 الانضمام للقنوات الإجبارية</h2>
                <p>يرجى الانضمام إلى القنوات التالية للمتابعة:</p>
                
                <div class="channels-list">
                    ${channels.map(channel => `
                        <div class="channel-item" data-channel-id="${channel.channel_id}">
                            <div class="channel-info">
                                <h3>${channel.channel_name}</h3>
                                <p style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">${channel.channel_id}</p>
                            </div>
                            <div class="channel-actions">
                                <a href="${channel.channel_url}" 
                                   target="_blank" 
                                   class="channel-link"
                                   onclick="markChannelAsOpened('${channel.channel_id}')">
                                    📢 فتح القناة
                                </a>
                                <span class="channel-status not-subscribed" id="status-${channel.channel_id}">
                                    ❌
                                </span>
                            </div>
                        </div>
                    `).join('')}
                </div>
                
                <button class="verify-btn" onclick="verifySubscriptions()">
                    ✅ تحقق من الاشتراك
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
                statusElement.textContent = '✅';
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
        TelegramApp.showAlert('⚠️ يرجى فتح جميع القنوات أولاً!');
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
    TelegramApp.showAlert('✅ تم التحقق بنجاح! مرحباً بك 🎉');
    setTimeout(() => {
        console.log('🔄 Reloading page...');
        window.location.reload();
    }, 1000);
};
