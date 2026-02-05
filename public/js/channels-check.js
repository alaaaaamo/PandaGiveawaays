// ═══════════════════════════════════════════════════════════════
// 📢 REQUIRED CHANNELS CHECK MODULE
// ═══════════════════════════════════════════════════════════════

const ChannelsCheck = {
    channels: [],
    
    async init() {
        console.log('📢 Initializing Required Channels Check...');
        await this.loadChannels();
        await this.verifySubscription();
    },
    
    async loadChannels() {
        try {
            const response = await fetch('/api/required-channels');
            const data = await response.json();
            
            if (data.success && data.channels) {
                this.channels = data.channels;
                console.log(`✅ Loaded ${this.channels.length} required channels`);
            }
        } catch (error) {
            console.error('❌ Error loading channels:', error);
        }
    },
    
    async verifySubscription() {
        if (this.channels.length === 0) {
            console.log('✅ No required channels');
            return true;
        }
        
        try {
            const userId = TelegramApp.getUserId();
            const response = await fetch('/api/verify-channels', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({user_id: userId})
            });
            
            const data = await response.json();
            
            if (!data.all_subscribed) {
                this.showSubscriptionModal(data.not_subscribed);
                return false;
            }
            
            return true;
            
        } catch (error) {
            console.error('❌ Error verifying channels:', error);
            return false;
        }
    },
    
    showSubscriptionModal(notSubscribed) {
        // إنشاء modal للقنوات غير المشترك فيها
        let channelsHTML = '';
        
        notSubscribed.forEach(channel => {
            const channelLink = channel.channel_id.startsWith('@') 
                ? `https://t.me/${channel.channel_id.substring(1)}`
                : `https://t.me/${channel.channel_id}`;
            
            channelsHTML += `
                <div class="required-channel-item">
                    <div class="channel-info">
                        <span class="channel-icon">📢</span>
                        <span class="channel-name">${channel.channel_name}</span>
                    </div>
                    <button class="subscribe-channel-btn" onclick="ChannelsCheck.openChannel('${channelLink}')">
                        <img src="/img/links.png" alt="اشتراك" style="width: 16px; height: 16px; vertical-align: middle; margin-left: 4px;"> اشتراك
                    </button>
                </div>
            `;
        });
        
        const modalHTML = `
            <div id="channels-modal" class="channels-modal">
                <div class="channels-modal-content">
                    <div class="channels-modal-header">
                        <h2>🔔 اشتراك إجباري</h2>
                        <p>للاستمرار، يجب الاشتراك في القنوات التالية:</p>
                    </div>
                    <div class="channels-modal-body">
                        ${channelsHTML}
                    </div>
                    <div class="channels-modal-footer">
                        <button class="btn-verify-channels" onclick="ChannelsCheck.recheckSubscription()">
                            <img src="/img/payment-success.svg" alt="تحقق" style="width: 18px; height: 18px; vertical-align: middle; margin-left: 4px;"> تحققت من الاشتراك
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // إضافة المودال للصفحة
        const existingModal = document.getElementById('channels-modal');
        if (existingModal) {
            existingModal.remove();
        }
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // منع التفاعل مع بقية الصفحة
        document.body.style.overflow = 'hidden';
    },
    
    openChannel(link) {
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.openLink(link);
        } else {
            window.open(link, '_blank');
        }
    },
    
    async recheckSubscription() {
        const btn = event.target;
        const originalText = btn.innerHTML;
        
        btn.disabled = true;
        btn.innerHTML = '⏳ جاري التحقق...';
        
        const result = await this.verifySubscription();
        
        if (result) {
            // نجح الاشتراك
            const modal = document.getElementById('channels-modal');
            if (modal) {
                modal.remove();
                document.body.style.overflow = 'auto';
            }
            
            if (typeof showToast !== 'undefined') {
                showToast('<img src="/img/payment-success.svg" style="width: 16px; height: 16px; vertical-align: middle;"> تم التحقق من الاشتراك بنجاح!', 'success');
            }
            
            // تسجيل الإحالة المعلقة بعد التحقق من القنوات
            if (typeof registerPendingReferral !== 'undefined') {
                await registerPendingReferral();
            }
            
            // بدلاً من reload، استدعي استكمال تهيئة التطبيق مباشرة
            console.log('✅ Channels verified, continuing app initialization...');
            if (typeof continueAppInitialization !== 'undefined') {
                await continueAppInitialization();
            } else {
                // Fallback - reload if function not available  
                console.log('🔄 continueAppInitialization not found, reloading...');
                setTimeout(() => window.location.reload(), 1000);
            }
        } else {
            btn.disabled = false;
            btn.innerHTML = originalText;
            
            if (typeof showToast !== 'undefined') {
                showToast('<img src="/img/payment-failure.svg" style="width: 16px; height: 16px; vertical-align: middle;"> يجب الاشتراك في جميع القنوات أولاً', 'error');
            }
        }
    },
    
    /**
     * التحقق الدوري من القنوات عند عودة المستخدم للتطبيق
     */
    setupVisibilityCheck() {
        document.addEventListener('visibilitychange', async () => {
            if (!document.hidden) {
                console.log('👁️ User returned to app, re-checking channels...');
                await this.loadChannels();
                await this.verifySubscription();
            }
        });
        
        // التحقق عند استعادة التركيز
        window.addEventListener('focus', async () => {
            console.log('🔍 App focused, re-checking channels...');
            await this.loadChannels();
            await this.verifySubscription();
        });
        
        console.log('✅ Visibility check listeners registered');
    }
};

// تشغيل الفحص عند تحميل الصفحة
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        // انتظار تهيئة Telegram App أولاً
        setTimeout(() => {
            ChannelsCheck.init();
            ChannelsCheck.setupVisibilityCheck();
        }, 500);
    });
} else {
    setTimeout(() => {
        ChannelsCheck.init();
        ChannelsCheck.setupVisibilityCheck();
    }, 500);
}
