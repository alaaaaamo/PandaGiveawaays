// ═══════════════════════════════════════════════════════════════
// 📢 CHANNELS VERIFICATION SYSTEM
// ═══════════════════════════════════════════════════════════════

async function checkRequiredChannels() {
    try {
        // Get required channels from backend
        const response = await fetch(`${CONFIG.API_BASE_URL}/admin/channels`);
        const result = await response.json();
        
        if (!result.success || !result.data || result.data.length === 0) {
            // No required channels, proceed normally
            return true;
        }
        
        const channels = result.data;
        
        // Check if user has verified channels before (using localStorage)
        const verifiedKey = `channels_verified_${TelegramApp.getUserId()}`;
        const lastVerified = Storage.get(verifiedKey, 0);
        const now = Date.now();
        
        // Check every 24 hours
        if (now - lastVerified < 24 * 60 * 60 * 1000) {
            return true;
        }
        
        // Show channels modal
        await showChannelsModal(channels);
        
        return false;
        
    } catch (error) {
        console.error('Error checking channels:', error);
        // Don't block user if there's an error
        return true;
    }
}

async function showChannelsModal(channels) {
    return new Promise((resolve) => {
        const modal = document.getElementById('channels-modal');
        const channelsList = document.getElementById('channels-list');
        const verifyBtn = document.getElementById('verify-channels-btn');
        
        // Build channels list
        channelsList.innerHTML = '';
        channels.forEach(channel => {
            const channelItem = document.createElement('div');
            channelItem.className = 'channel-item';
            channelItem.innerHTML = `
                <div class="channel-info">
                    <svg class="channel-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
                    </svg>
                    <div>
                        <div class="channel-name">${channel.channel_name}</div>
                        <div class="channel-id">${channel.channel_id}</div>
                    </div>
                </div>
                <a href="${channel.channel_url}" target="_blank" class="channel-join-btn" onclick="TelegramApp.hapticFeedback('light')">
                    اشترك الآن
                </a>
            `;
            channelsList.appendChild(channelItem);
        });
        
        // Show modal
        modal.style.display = 'flex';
        
        // Handle verify button
        verifyBtn.onclick = async () => {
            TelegramApp.hapticFeedback('medium');
            verifyBtn.disabled = true;
            verifyBtn.textContent = '⏳ جاري التحقق...';
            
            // Simulate verification (in real app, you'd check with Telegram Bot API)
            await new Promise(r => setTimeout(r, 2000));
            
            // Mark as verified
            const verifiedKey = `channels_verified_${TelegramApp.getUserId()}`;
            Storage.set(verifiedKey, Date.now());
            
            // Close modal
            modal.style.display = 'none';
            showToast('✅ تم التحقق من الاشتراك بنجاح!', 'success');
            TelegramApp.hapticFeedback('success');
            
            resolve(true);
        };
    });
}
