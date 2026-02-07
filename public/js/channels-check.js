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
        console.log('🔍 Starting channels verification...');
        
        if (this.channels.length === 0) {
            console.log('✅ No required channels');
            return true;
        }
        
        console.log(`📢 Verifying ${this.channels.length} channels:`, this.channels);
        
        try {
            const userId = TelegramApp.getUserId();
            console.log(`👤 User ID: ${userId}`);
            
            // محاولتين مع timeout أطول
            let response;
            for (let attempt = 0; attempt < 2; attempt++) {
                try {
                    // AbortController لتحديد timeout
                    const controller = new AbortController();
                    const timeoutId = setTimeout(() => controller.abort(), 20000); // 20 ثانية
                    
                    response = await fetch('/api/verify-channels', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({user_id: userId}),
                        signal: controller.signal
                    });
                    
                    clearTimeout(timeoutId);
                    break;
                    
                } catch (fetchError) {
                    if (attempt === 0) {
                        console.warn(`⚠️ Verification attempt ${attempt + 1} failed:`, fetchError.message);
                        await new Promise(resolve => setTimeout(resolve, 2000)); // انتظار ثانيتين
                        continue;
                    } else {
                        throw fetchError;
                    }
                }
            }
            
            if (!response || !response.ok) {
                throw new Error(`Server responded with status: ${response?.status || 'unknown'}`);
            }
            
            const data = await response.json();
            console.log('📊 Verification response:', data);
            
            if (!data.all_subscribed) {
                console.log('❌ User not subscribed to all channels. Missing:', data.not_subscribed);
                this.showSubscriptionModal(data.not_subscribed);
                return false;
            }
            
            console.log('✅ User subscribed to all channels!');
            return true;
            
        } catch (error) {
            console.error('❌ Error verifying channels:', error);
            
            // في حالة timeout أو خطأ في الشبكة، نعطي فرصة أخرى
            if (error.name === 'AbortError' || error.message.includes('timeout') || error.message.includes('fetch')) {
                console.log('⚠️ Network issue detected, allowing user to continue');
                if (typeof showToast !== 'undefined') {
                    showToast('⚠️ مشكلة في الشبكة - يمكنك المتابعة مؤقتاً', 'warning');
                }
                return true; // السماح بالمتابعة في حالة مشاكل الشبكة
            }
            
            return false;
        }
    },
    
    showSubscriptionModal(notSubscribed) {
        console.log('🔔 Showing channels subscription modal for', notSubscribed.length, 'channels');
        
        // 🔥 إخفاء الـ loading overlay أولاً قبل عرض الـ modal
        if (typeof showLoading !== 'undefined') {
            showLoading(false);
        }
        
        // إنشاء modal للقنوات غير المشترك فيها
        let channelsHTML = '';
        
        notSubscribed.forEach(channel => {
            const channelLink = channel.channel_id.startsWith('@') 
                ? `https://t.me/${channel.channel_id.substring(1)}`
                : `https://t.me/${channel.channel_id}`;
            
            // استخدام صورة القناة من Telegram
            const channelInput = channelLink || channel.channel_url || channel.channel_id;
            const channelIconHTML = createChannelPhotoHTML(channelInput, '📢', '36px');
            
            channelsHTML += `
                <div class="required-channel-item">
                    <div class="channel-info">
                        ${channelIconHTML}
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
            
            // ⚠️ إزالة تسجيل الإحالة من هنا - سيتم في continueAppInitialization
            // تسجيل الإحالة المعلقة بعد التحقق من القنوات
            // if (typeof registerPendingReferral !== 'undefined') {
            //     await registerPendingReferral();
            // }
            
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

// ⚠️ لا تقم بالتشغيل التلقائي - سيتم الاستدعاء من app.js
// التشغيل التلقائي يسبب تضارب مع app.js initialization
