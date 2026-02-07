// ═══════════════════════════════════════════════════════════════
// 🐼 PANDA GIVEAWAYS - MAIN APP
// ═══════════════════════════════════════════════════════════════

let wheel = null;

// ═══════════════════════════════════════════════════════════════
// � VISUAL DEBUGGING & LOADING MESSAGES
// ═══════════════════════════════════════════════════════════════

// 🏁 Updated v2.1 - تم تحديث جوائز العجلة

// Clear cache for updated configuration
localStorage.removeItem('wheel-config-cache');
sessionStorage.clear();

function showLoadingWithMessage(message) {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        const loadingText = loadingOverlay.querySelector('.loading-text');
        if (loadingText) {
            loadingText.textContent = message;
        } else {
            // إنشاء عنصر النص إذا لم يكن موجود
            const textElement = document.createElement('p');
            textElement.className = 'loading-text';
            textElement.textContent = message;
            loadingOverlay.appendChild(textElement);
        }
    }
    DebugError.add(`Loading Status: ${message}`, 'info');
}

// إضافة مؤشر حالة السيرفر
function addServerStatusIndicator() {
    // تعطيل مؤشر حالة السيرفر في الإنتاج
    if (!DEBUG_CONFIG.SHOW_SERVER_STATUS) {
        return;
    }
    
    // تحقق من عدم وجود المؤشر بالفعل
    if (document.getElementById('server-status-indicator')) return;
    
    const indicator = document.createElement('div');
    indicator.id = 'server-status-indicator';
    indicator.style.cssText = `
        position: fixed;
        top: 60px;
        right: 10px;
        background: rgba(40, 40, 40, 0.9);
        color: #fff;
        padding: 8px 12px;
        border-radius: 15px;
        font-size: 12px;
        z-index: 9999;
        display: flex;
        align-items: center;
        gap: 8px;
        transition: all 0.3s ease;
        border: 1px solid #555;
    `;
    
    indicator.innerHTML = `
        <div id="server-status-dot" style="width: 8px; height: 8px; background: #ffa500; border-radius: 50%; animation: pulse 1.5s infinite;"></div>
        <span id="server-status-text">جاري الاتصال...</span>
    `;
    
    // إضافة CSS للـ animation
    if (!document.getElementById('server-status-style')) {
        const style = document.createElement('style');
        style.id = 'server-status-style';
        style.textContent = `
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.5; }
                100% { opacity: 1; }
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(indicator);
}

// تحديث مؤشر حالة السيرفر
function updateServerStatus(status, message) {
    // لا تحديث إذا كان مؤشر السيرفر معطل
    if (!DEBUG_CONFIG.SHOW_SERVER_STATUS) {
        return;
    }
    
    const indicator = document.getElementById('server-status-indicator');
    const dot = document.getElementById('server-status-dot');
    const text = document.getElementById('server-status-text');
    
    if (!indicator || !dot || !text) return;
    
    switch (status) {
        case 'connecting':
            dot.style.background = '#ffa500';
            dot.style.animation = 'pulse 1.5s infinite';
            text.textContent = message || 'جاري الاتصال...';
            break;
        case 'online':
            dot.style.background = '#4CAF50';
            dot.style.animation = 'none';
            text.textContent = message || 'متصل';
            break;
        case 'offline':
            dot.style.background = '#ff4444';
            dot.style.animation = 'pulse 1.5s infinite';
            text.textContent = message || 'غير متصل';
            break;
        case 'error':
            dot.style.background = '#ff6b6b';
            dot.style.animation = 'pulse 0.8s infinite';
            text.textContent = message || 'خطأ في الاتصال';
            break;
    }
}

// ═══════════════════════════════════════════════════════════════
// �🚀 APP INITIALIZATION
// ═══════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', async () => {
    // إضافة مؤشر حالة السيرفر
    addServerStatusIndicator();
    updateServerStatus('connecting', 'جاري التهيئة...');
    
    // إضافة timeout للتحميل لمنع التحميل اللا نهائي
    const LOADING_TIMEOUT = 60000; // 60 ثانية
    const timeoutId = setTimeout(() => {
        showLoading(false);
        document.body.innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; 
                min-height: 100vh; background: #0d1117; padding: 20px; text-align: center;">
                <h2 style="color: #ff4444; margin: 20px 0;">⏰ انتهت مهلة التحميل</h2>
                <p style="color: #8b95a1; font-size: 16px;">قد تكون المشكلة في الاتصال بالسيرفر</p>
                <button onclick="window.location.reload()" 
                    style="padding: 12px 24px; background: #ffa500; color: #000; border: none; 
                    border-radius: 8px; font-size: 16px; font-weight: bold; margin-top: 20px; cursor: pointer;">
                    إعادة المحاولة
                </button>
                <p style="color: #666; font-size: 14px; margin-top: 20px;">
                    إذا استمرت المشكلة، تواصل مع الدعم
                </p>
            </div>
        `;
    }, LOADING_TIMEOUT);
    
    // حفظ ID للاستخدام من خارج هذا السياق
    window.globalTimeoutId = timeoutId;
    
    try {
        // تهيئة Telegram Web App
        TelegramApp.init();
        
        // ═══════════════════════════════════════════════════════
        // 🔐 التحقق من فتح الصفحة من تليجرام أولاً
        // ═══════════════════════════════════════════════════════
        
        // انتظار قصير لضمان تحميل Telegram WebApp بشكل كامل
        await new Promise(resolve => setTimeout(resolve, 500));
        
        const userId = TelegramApp.getUserId();
        const isValidTelegram = TelegramApp.isValidTelegram();
        
        // إذا لم يتم فتح الصفحة من تليجرام أصلاً أو لا توجد بيانات مستخدم صحيحة
        if (!isValidTelegram) {
            document.body.innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; 
                    min-height: 100vh; background: #0d1117; padding: 20px; text-align: center;">
                    <lottie-player src="/img/notallowed.json" 
                        background="transparent" speed="1" 
                        style="width: 200px; height: 200px;" 
                        loop autoplay>
                    </lottie-player>
                    <img src="/img/payment-failure.svg" alt="X" 
                        style="width: 60px; height: 60px; margin: 20px 0;">
                    <h2 style="color: #ff4444; margin: 20px 0; font-size: 24px; font-weight: bold;">
                        🚫 يجب فتح الصفحة من تليجرام
                    </h2>
                    <p style="color: #8b95a1; font-size: 16px; line-height: 1.6; max-width: 400px; margin-bottom: 30px;">
                        هذا التطبيق يعمل داخل تليجرام فقط. يرجى فتحه من خلال البوت.
                    </p>
                    <a href="https://t.me/${window.CONFIG?.BOT_USERNAME || 'PandaGiveawaysBot'}" 
                        style="display: inline-flex; align-items: center; gap: 10px; margin-top: 20px; padding: 16px 40px; 
                        background: linear-gradient(135deg, #ffa500, #ff8c00); color: #000; 
                        text-decoration: none; border-radius: 12px; font-weight: bold; 
                        font-size: 18px; box-shadow: 0 4px 15px rgba(255, 165, 0, 0.3); 
                        transition: transform 0.2s;" 
                        onmouseover="this.style.transform='scale(1.05)'" 
                        onmouseout="this.style.transform='scale(1)'">
                        🚀 فتح البوت
                    </a>
                </div>
            `;
            return;
        }
        
        // تم التحقق من صحة جلسة تليجرام
        
        // عرض Loading مع رسالة تبين التقدم
        showLoadingWithMessage('🔄 جاري التهيئة...');
        showLoading(true);
        
        // ═══════════════════════════════════════════════════════
        // � التحقق من حالة البوت أولاً
        // ═══════════════════════════════════════════════════════
        const isAdmin = CONFIG.ADMIN_IDS && CONFIG.ADMIN_IDS.includes(userId);
        
        if (!isAdmin) {
            try {
                showLoadingWithMessage('🔎 جاري التحقق من حالة البوت...');
                const botStatusResp = await fetch(`${CONFIG.API_BASE_URL}/bot/status`);
                const botStatusData = await botStatusResp.json();
                
                if (!botStatusData.bot_enabled) {
                    // البوت معطل - عرض رسالة
                    showLoading(false);
                    
                    document.body.innerHTML = `
                        <div id="bot-disabled-screen" style="display: flex; flex-direction: column; align-items: center; justify-content: center; 
                            min-height: 100vh; background: #0d1117; padding: 20px; text-align: center;">
                            <lottie-player src="/img/notallowed.json" 
                                background="transparent" speed="1" 
                                style="width: 250px; height: 250px; margin-bottom: 20px;" 
                                loop autoplay>
                            </lottie-player>
                            <img src="/img/payment-failure.svg" alt="X" 
                                style="width: 80px; height: 80px; margin: 20px 0; opacity: 0.9;">
                            <h2 style="color: #ff4444; margin: 20px 0; font-size: 28px; font-weight: bold;">
                                🔴 البوت مغلق حالياً
                            </h2>
                            <p style="color: #8b95a1; font-size: 18px; line-height: 1.8; max-width: 450px; margin-bottom: 20px;">
                                البوت غير متاح في الوقت الحالي للصيانة.
                            </p>
                            <p style="color: #666; font-size: 16px; margin-top: 10px;">
                                ⏰ سيتم تفعيل البوت قريباً، يرجى المحاولة لاحقاً.
                            </p>
                            <p style="color: #555; font-size: 14px; margin-top: 30px;">
                                📢 تابعنا للحصول على آخر التحديثات
                            </p>
                        </div>
                    `;
                    
                    return;
                }
            } catch (statusError) {
                // في حالة الخطأ، نستمر عادياً
            }
        }
        
        // ═══════════════════════════════════════════════════════
        // 🔐 التحقق من حالة المستخدم (device verification)
        // ═══════════════════════════════════════════════════════
        
        // استخراج referrer_id من start_param إن وجد
        let referrerId = null;
        try {
            const initData = window.Telegram?.WebApp?.initDataUnsafe;
            if (initData?.start_param) {
                const startParam = initData.start_param;
                if (startParam.startsWith('ref_')) {
                    referrerId = parseInt(startParam.replace('ref_', ''));
                    // Referrer detected silently
                }
            }
        } catch (e) {
            console.warn('Could not extract referrer:', e);
        }
        
        if (userId && !isAdmin) {
            try {
                showLoadingWithMessage('🔐 جاري التحقق من الحساب...');
                const verifyStatusResp = await fetch(`${CONFIG.API_BASE_URL}/verification/status/${userId}`);
                const verifyData = await verifyStatusResp.json();
                
                if (!verifyData.verified) {
                    // المستخدم غير متحقق - عرض زر للتوجه للبوت
                    showLoading(false);
                    
                    // إنشاء رابط البوت مع الإحالة إن وجدت
                    let botUrl;
                    if (referrerId) {
                        botUrl = `https://t.me/${window.CONFIG?.BOT_USERNAME || 'PandaGiveawaysBot'}?start=ref_${referrerId}`;
                        // Using referral link
                    } else {
                        botUrl = `https://t.me/${window.CONFIG?.BOT_USERNAME || 'PandaGiveawaysBot'}`;
                    }
                    
                    // عرض رسالة مع زر فقط (بدون توجيه تلقائي)
                    document.body.innerHTML = `
                        <div id="redirect-screen" style="display: flex; flex-direction: column; align-items: center; justify-content: center; 
                            min-height: 100vh; background: #0d1117; padding: 20px; text-align: center;">
                            <lottie-player src="/img/notallowed.json" 
                                background="transparent" speed="1" 
                                style="width: 200px; height: 200px;" 
                                loop autoplay>
                            </lottie-player>
                            <img src="/img/payment-failure.svg" alt="X" 
                                style="width: 60px; height: 60px; margin: 20px 0;">
                            <h2 style="color: #ff4444; margin: 20px 0;">
                                🚫 يجب التحقق من حسابك أولاً
                            </h2>
                            <p style="color: #8b95a1; font-size: 16px; line-height: 1.6; max-width: 400px; margin-bottom: 30px;">
                                للمتابعة في استخدام المينى آب، يجب التحقق من جهازك أولاً عبر البوت.
                            </p>
                            <a href="${botUrl}" 
                                style="display: inline-flex; align-items: center; gap: 10px; margin-top: 20px; padding: 16px 40px; 
                                background: linear-gradient(135deg, #ffa500, #ff8c00); color: #000; 
                                text-decoration: none; border-radius: 12px; font-weight: bold; 
                                font-size: 18px; box-shadow: 0 4px 15px rgba(255, 165, 0, 0.3); 
                                transition: transform 0.2s;" 
                                onmouseover="this.style.transform='scale(1.05)'" 
                                onmouseout="this.style.transform='scale(1)'">
                                <img src="/img/links.png" alt="Link" style="width: 24px; height: 24px;">
                                🚀 فتح البوت للتحقق
                            </a>
                            <p style="color: #666; font-size: 14px; margin-top: 20px;">
                                اضغط على الزر أعلاه لفتح البوت
                            </p>
                        </div>
                    `
                    
                    return;
                }
            } catch (verifyError) {
                // في حالة الخطأ، نستمر عادياً
            }
        }
        
        // إرسال رسالة ترحيبية (سيظهر تليجرام "Allow bot to message you?" تلقائياً)
        showLoadingWithMessage('📩 جاري إعداد الاتصال...');
        await sendWelcomeMessage();
        
        // حفظ referrer_id مؤقتاً إذا موجود (سيتم تسجيله بعد التحقق من القنوات)
        savePendingReferral();
        
        // Check required channels FIRST before loading anything
        showLoadingWithMessage('📺 جاري التحقق من اشتراكك في القنوات...');
        
        let channelsVerified = false;
        try {
            // Use the proper channels check module
            if (typeof ChannelsCheck !== 'undefined') {
                await ChannelsCheck.loadChannels();
                channelsVerified = await ChannelsCheck.verifySubscription();
            } else {
                channelsVerified = await checkRequiredChannels();
            }
        } catch (error) {
            // في حالة الخطأ، نسمح للمستخدم بالمتابعة
            channelsVerified = true;
        }
        
        // Channels verification completed
        
        if (!channelsVerified) {
            // Hide loading - channels modal will be shown
            clearTimeout(timeoutId);
            clearTimeout(window.globalTimeoutId);
            showLoading(false);
            return;
        }
        
        // إذا تم التحقق من القنوات، ننتقل لعملية الإعداد الأساسية
        await continueAppInitialization();
        
    } catch (error) {
        console.error('❌ App Initialization Error:', error);
        clearTimeout(timeoutId);
        clearTimeout(window.globalTimeoutId);
        showLoading(false);
        // لا نزيل loading class في حالة الخطأ للحفاظ على إخفاء المحتوى الثابت
        // حدث خطأ في تحميل التطبيق
    }
});

// ═══════════════════════════════════════════════════════════════
// 🎁 WHEEL PRIZES LOADER
// ═══════════════════════════════════════════════════════════════

async function loadWheelPrizes() {
    // ❌ تعطيل تحميل الجوائز من API - استخدام الافتراضية فقط
    DebugError.add('🎁 Using default wheel prizes from config.js', 'info', CONFIG.WHEEL_PRIZES);
    DebugError.add(`✅ Wheel configured with ${CONFIG.WHEEL_PRIZES.length} prizes`, 'info');
    
    // التحقق من تطابق الجوائز
    const totalProbability = CONFIG.WHEEL_PRIZES.reduce((sum, p) => sum + p.probability, 0);
    DebugError.add(`📊 Total wheel probability: ${totalProbability}%`, 'info');
    
    if (Math.abs(totalProbability - 100) > 0.1 && totalProbability !== 0) {
        DebugError.add(`⚠️ Warning: Total probability is ${totalProbability}%, not 100%`, 'warn');
    }
    
    return CONFIG.WHEEL_PRIZES;
}

// ═══════════════════════════════════════════════════════════════
// 🔗 REFERRAL HANDLING
// ═══════════════════════════════════════════════════════════════

// ═══════════════════════════════════════════════════════════════
// 🔗 REFERRAL HANDLING (بعد التحقق من القنوات)
// ═══════════════════════════════════════════════════════════════

/**
 * حفظ referrer_id مؤقتاً في localStorage
 */
function savePendingReferral() {
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const startParam = urlParams.get('tgWebAppStartParam');
        
        if (startParam && startParam.startsWith('ref_')) {
            const referrerId = parseInt(startParam.replace('ref_', ''));
            const currentUserId = TelegramApp.getUserId() || urlParams.get('user_id');
            
            if (referrerId && currentUserId && referrerId !== parseInt(currentUserId)) {
                console.log('💾 Saving pending referral:', referrerId, '->', currentUserId);
                
                // حفظ في localStorage
                localStorage.setItem('pendingReferral', JSON.stringify({
                    referrer_id: referrerId,
                    referred_id: parseInt(currentUserId),
                    timestamp: Date.now()
                }));
            }
        }
    } catch (error) {
        console.error('Error saving pending referral:', error);
    }
}

/**
 * تسجيل الإحالة بعد التحقق من القنوات
 */
async function registerPendingReferral() {
    // تجنب التسجيل المكرر
    if (window.referralProcessing) {
        console.log('⚠️ Referral already being processed, skipping...');
        return;
    }
    
    try {
        window.referralProcessing = true;
        
        const pendingData = localStorage.getItem('pendingReferral');
        
        if (!pendingData) {
            console.log('ℹ️ No pending referral');
            return;
        }
        
        const referralData = JSON.parse(pendingData);
        console.log('📎 Registering pending referral after channel verification:', referralData);
        
        // timeout قصير لتسجيل الإحالة
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 8000); // 8 ثوان فقط
        
        // تسجيل الإحالة
        const response = await fetch(`${CONFIG.API_BASE_URL}/referral/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                referrer_id: referralData.referrer_id,
                referred_id: referralData.referred_id
            }),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        const result = await response.json();
        if (result.success) {
            console.log('✅ Referral registered successfully after channel verification');
            showToast('تم تسجيل الإحالة بنجاح! 🎉', 'success');
            
            // حذف البيانات المؤقتة
            localStorage.removeItem('pendingReferral');
        } else {
            console.log('⚠️ Referral registration failed:', result.error);
            // نبقي البيانات للمحاولة مرة أخرى
        }
        
    } catch (error) {
        if (error.name === 'AbortError') {
            console.log('⚠️ Referral registration timeout - will retry later');
        } else {
            console.error('Error registering pending referral:', error);
        }
        // نبقي البيانات للمحاولة مرة أخرى
    } finally {
        window.referralProcessing = false;
    }
}

async function handleReferral() {
    try {
        // الحصول على معامل الإحالة من URL
        const urlParams = new URLSearchParams(window.location.search);
        const startParam = urlParams.get('tgWebAppStartParam');
        
        if (startParam && startParam.startsWith('ref_')) {
            const referrerId = parseInt(startParam.replace('ref_', ''));
            const currentUserId = TelegramApp.getUserId() || urlParams.get('user_id');
            
            if (referrerId && currentUserId && referrerId !== parseInt(currentUserId)) {
                console.log('📎 Registering referral:', referrerId, '->', currentUserId);
                
                // تسجيل الإحالة
                const response = await fetch(`${CONFIG.API_BASE_URL}/referral/register`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        referrer_id: referrerId,
                        referred_id: parseInt(currentUserId)
                    })
                });
                
                const result = await response.json();
                if (result.success) {
                    console.log('✅ Referral registered successfully');
                    // تم تسجيل الإحالة بنجاح
                } else {
                    console.log('⚠️ Referral registration failed:', result.error);
                }
            }
        }
    } catch (error) {
        console.error('Error handling referral:', error);
    }
}

// ═══════════════════════════════════════════════════════════════
// 👤 USER DATA
// ═══════════════════════════════════════════════════════════════

async function loadUserData() {
    try {
        DebugError.add('Starting user data loading...', 'info');
        
        let userId = TelegramApp.getUserId();
        
        // إذا لم نجد user_id حقيقي، لا نستمر
        if (!userId) {
            DebugError.add('No valid user ID found!', 'error');
            throw new Error('لا يمكن التحميل بدون معرف مستخدم صحيح من تليجرام');
        }
        
        DebugError.add(`Loading data for user ID: ${userId}`, 'info');
        
        // الحصول على بيانات محسنة من Telegram
        const enhancedUserData = getEnhancedUserData();
        DebugError.add('Enhanced user data retrieved:', 'info', enhancedUserData);
        
        // تحديث بيانات المستخدم من Telegram أولاً
        try {
            const username = TelegramApp.getUsername() || `user_${userId}`;
            const fullName = TelegramApp.getFullName() || username;
            
            DebugError.add(`Updating profile: ${username} | ${fullName}`, 'info');
            
            await fetch(`${CONFIG.API_BASE_URL}/user/${userId}/update-profile`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username: username,
                    full_name: fullName
                })
            });
        } catch (profileError) {
            DebugError.add(`Profile update error: ${profileError.message}`, 'warn', profileError);
        }
        
        DebugError.add('Fetching user data from API...', 'info');
        
        const response = await Promise.race([
            API.getUserData(userId),
            new Promise((_, reject) => setTimeout(() => reject(new Error('getUserData API timeout')), 8000))
        ]);
        
        DebugError.add('API Response received:', 'info', response);
        
        if (response.success) {
            UserState.init(response.data);
            
            DebugError.add('User state initialized successfully', 'info', response.data);
            
            // تأكيد الاتصال بالسيرفر
            updateServerStatus('online', 'متصل بنجاح');
            
            // تحديث الواجهة بالبيانات المحسنة
            updateUserDisplay(enhancedUserData);
            
            updateUserProfile();
            
            updateUI();
            
        } else {
            DebugError.add(`Failed to load user data: ${response.error}`, 'error', response);
            throw new Error('فشل تحميل بيانات المستخدم: ' + (response.error || 'Unknown error'));
        }
    } catch (error) {
        DebugError.add(`Critical error in loadUserData: ${error.message}`, 'error', error);
        handleApiError(error, 'loadUserData');
        
        // تحديث حالة السيرفر
        updateServerStatus('error', 'فشل الاتصال');
        
        // إذا فشل تحميل البيانات من API، استخدم بيانات أساسية
        DebugError.add('Using offline fallback for user data', 'warn');
        
        const offlineUserData = {
            id: userId,
            balance: 0,
            available_spins: 0,
            total_referrals: 0,
            total_withdrawals: 0,
            registration_date: new Date().toISOString(),
            last_spin: null,
            username: TelegramApp.getUsername() || `user_${userId}`,
            full_name: TelegramApp.getFullName() || 'مستخدم'
        };
        
        UserState.init(offlineUserData);
        
        // تحديث الواجهة بالبيانات المحسنة
        updateUserDisplay(getEnhancedUserData());
        updateUserProfile();
        updateUI();
        
        // إظهار رسالة للمستخدم
        showToast('⚠️ تم التحميل في وضع محدود - تحقق من الاتصال', 'warn', 5000);
        // لا نرمي الخطأ لنسمح للتطبيق بالاستمرار
    }
}

function updateUserProfile() {
    try {
        DebugError.add('Updating user profile UI...', 'info');
        
        const avatar = document.getElementById('user-avatar');
        const name = document.getElementById('user-name');
        const username = document.getElementById('user-username');
        
        // الحصول على البيانات المحسنة
        const enhancedUserData = getEnhancedUserData();
        
        // تحديث الصورة
        if (avatar) {
            const userPhoto = enhancedUserData.photo_url;
            DebugError.add(`Setting avatar: ${userPhoto}`, 'info');
            avatar.src = userPhoto;
            avatar.onerror = function() {
                DebugError.add('Avatar failed to load, using default', 'warn');
                this.src = '/img/user-placeholder.svg';
            };
        }
        
        // تحديث الاسم الكامل
        if (name) {
            const fullName = enhancedUserData.first_name && enhancedUserData.first_name !== 'جاري التحميل...' 
                ? `${enhancedUserData.first_name} ${enhancedUserData.last_name}`.trim()
                : 'جاري التحميل...';
            DebugError.add(`Setting full name: ${fullName}`, 'info');
            name.textContent = fullName;
        }
        
        // تحديث اسم المستخدم
        if (username) {
            const telegramUsername = enhancedUserData.username;
            if (telegramUsername && telegramUsername !== '') {
                DebugError.add(`Setting username: @${telegramUsername}`, 'info');
                username.textContent = `@${telegramUsername}`;
            } else {
                const userId = enhancedUserData.id;
                const fallbackUsername = userId ? `user${userId}` : 'username';
                DebugError.add(`Setting fallback username: ${fallbackUsername}`, 'warn');
                username.textContent = fallbackUsername;
            }
        }
        
        DebugError.add('User profile UI updated successfully', 'info');
        
    } catch (error) {
        DebugError.add(`Error updating user profile UI: ${error.message}`, 'error', error);
    }
}

function updateUI() {
    // تحديث الرصيد
    const balanceElements = document.querySelectorAll('[id*="balance"]');
    balanceElements.forEach(el => {
        if (el.id === 'user-balance' || el.id === 'withdraw-balance') {
            el.textContent = formatNumber(UserState.get('balance'));
        }
    });
    
    // تحديث اللفات
    const spinsElement = document.getElementById('available-spins');
    if (spinsElement) {
        spinsElement.textContent = UserState.get('available_spins') || 0;
    }
    
    // تحديث الإحالات
    const referralsElement = document.getElementById('total-referrals');
    if (referralsElement) {
        referralsElement.textContent = UserState.get('total_referrals') || 0;
    }
}

// ═══════════════════════════════════════════════════════════════
// 📊 LOAD INITIAL DATA
// ═══════════════════════════════════════════════════════════════

async function loadInitialData() {
    console.log('🔄 Loading initial data modules...');
    
    try {
        // Channels already verified in main init
        await Promise.race([
            Promise.allSettled([
                loadSpinHistory().catch(e => {
                    console.warn('⚠️ loadSpinHistory failed:', e);
                    return null;
                }),
                loadReferrals().catch(e => {
                    console.warn('⚠️ loadReferrals failed:', e);
                    return null;
                }),
                loadTasks().catch(e => {
                    console.warn('⚠️ loadTasks failed:', e);
                    return null;
                }),
                loadWithdrawals().catch(e => {
                    console.warn('⚠️ loadWithdrawals failed:', e);
                    return null;
                })
            ]),
            new Promise((_, reject) => setTimeout(() => reject(new Error('loadInitialData timeout')), 6000)) // تقليل إلى 6 ثوان
        ]);
        console.log('✅ Initial data loading completed (some may have failed, but continuing)');
    } catch (error) {
        console.error('⚠️ loadInitialData timeout (continuing anyway):', error);
        // لا نوقف التطبيق، نكمل عادي
    }
}

// ═══════════════════════════════════════════════════════════════
// 🎨 UI INITIALIZATION
// ═══════════════════════════════════════════════════════════════

function initUI() {
    // Bottom Navigation
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const page = item.dataset.page;
            switchPage(page);
        });
    });
    
    // Copy Link Button
    const copyBtn = document.getElementById('copy-link-btn');
    if (copyBtn) {
        copyBtn.addEventListener('click', copyReferralLink);
    }
    
    // Share Link Button
    const shareBtn = document.getElementById('share-link-btn');
    if (shareBtn) {
        shareBtn.addEventListener('click', shareReferralLink);
    }
    
    // Withdrawal Method Tabs
    const methodTabs = document.querySelectorAll('.method-tab');
    methodTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            switchWithdrawalMethod(tab.dataset.method);
        });
    });
    
    // MAX Buttons
    document.getElementById('max-btn-ton')?.addEventListener('click', () => {
        setMaxAmount('ton');
    });
    document.getElementById('max-btn-vodafone')?.addEventListener('click', () => {
        setMaxAmount('vodafone');
    });
    
    // Withdrawal Buttons
    const withdrawBtnTon = document.getElementById('withdraw-btn-ton');
    if (withdrawBtnTon) {
        withdrawBtnTon.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('💰 TON Withdraw button clicked');
            submitWithdrawal('ton');
        }, true);
    }
    
    const withdrawBtnVodafone = document.getElementById('withdraw-btn-vodafone');
    if (withdrawBtnVodafone) {
        withdrawBtnVodafone.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('💰 Vodafone Withdraw button clicked');
            submitWithdrawal('vodafone');
        }, true);
    }
}

// ═══════════════════════════════════════════════════════════════
// 📱 PAGE NAVIGATION
// ═══════════════════════════════════════════════════════════════

function switchPage(pageName) {
    // Update pages
    const pages = document.querySelectorAll('.page');
    pages.forEach(page => {
        page.classList.remove('active');
    });
    
    const targetPage = document.getElementById(`page-${pageName}`);
    if (targetPage) {
        targetPage.classList.add('active');
    }
    
    // Update nav items
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.classList.remove('active');
        if (item.dataset.page === pageName) {
            item.classList.add('active');
        }
    });
    
    // Haptic feedback
    TelegramApp.hapticFeedback('soft');
    
    // Load page-specific data
    switch(pageName) {
        case 'referrals':
            loadReferralsWithAnimation();
            break;
        case 'tasks':
            loadTasks();
            break;
        case 'withdraw':
            loadWithdrawals();
            break;
    }
}

// ═══════════════════════════════════════════════════════════════
// 👥 REFERRALS PAGE
// ═══════════════════════════════════════════════════════════════

async function loadReferralsWithAnimation() {
    const loadingEl = document.getElementById('referrals-loading');
    const contentEl = document.getElementById('referrals-content');
    
    // Show loading animation
    if (loadingEl && contentEl) {
        loadingEl.style.display = 'flex';
        contentEl.style.display = 'none';
    }
    
    try {
        // Simulate API delay for smooth animation
        await new Promise(resolve => setTimeout(resolve, 1500));
        await loadReferrals();
        
        // Hide loading and show content
        if (loadingEl && contentEl) {
            loadingEl.style.display = 'none';
            contentEl.style.display = 'block';
        }
    } catch (error) {
        console.error('Error loading referrals:', error);
        if (loadingEl) loadingEl.style.display = 'none';
        if (contentEl) contentEl.style.display = 'block';
    }
}

async function loadReferrals() {
    try {
        const response = await API.getReferrals(TelegramApp.getUserId());
        
        if (response.success) {
            displayReferralStats(response.data);
            displayReferralsList(response.data);
        }
    } catch (error) {
        console.error('Error loading referrals:', error);
    }
}

function displayReferralStats(referrals) {
    const totalReferrals = referrals.length;
    const validReferrals = referrals.filter(r => r.is_valid).length;
    const earnedSpins = Math.floor(validReferrals / CONFIG.SPINS_PER_REFERRALS);
    const nextSpinIn = CONFIG.SPINS_PER_REFERRALS - (validReferrals % CONFIG.SPINS_PER_REFERRALS);
    
    document.getElementById('total-referrals').textContent = totalReferrals;
    document.getElementById('earned-spins').textContent = earnedSpins;
    document.getElementById('next-spin-in').textContent = nextSpinIn;
    
    // Set referral link
    const refLink = `https://t.me/${CONFIG.BOT_USERNAME}?startapp=ref_${TelegramApp.getUserId()}`;
    document.getElementById('referral-link').value = refLink;
}

function displayReferralsList(referrals) {
    const listContent = document.getElementById('referrals-list-content');
    listContent.innerHTML = '';
    
    if (referrals.length === 0) {
        listContent.innerHTML = '<p style="text-align: center; color: var(--text-secondary); padding: 20px;">لم تقم بدعوة أحد بعد! شارك رابطك الآن 🚀</p>';
        return;
    }
    
    referrals.forEach(ref => {
        const item = document.createElement('div');
        item.className = 'referral-item';
        
        const info = document.createElement('div');
        info.className = 'referral-info';
        
        const name = document.createElement('div');
        name.className = 'referral-name';
        name.textContent = ref.full_name + (ref.username ? ` (@${ref.username})` : '');
        
        const date = document.createElement('div');
        date.className = 'referral-date';
        date.textContent = formatDate(ref.created_at);
        
        info.appendChild(name);
        info.appendChild(date);
        
        const status = document.createElement('div');
        status.className = 'referral-status';
        status.innerHTML = ref.is_valid ? '<img src="/img/payment-success.svg" style="width: 16px; height: 16px;">' : '⏳';
        
        item.appendChild(info);
        item.appendChild(status);
        
        listContent.appendChild(item);
    });
}

function copyReferralLink() {
    const copyBtn = document.getElementById('copy-link-btn');
    const input = document.getElementById('referral-link');
    
    // Add loading state
    copyBtn.classList.add('loading');
    copyBtn.querySelector('.btn-text').textContent = 'جاري النسخ...';
    
    setTimeout(() => {
        input.select();
        document.execCommand('copy');
        
        // Show success state
        copyBtn.classList.remove('loading');
        copyBtn.querySelector('.btn-icon').innerHTML = '<img src="/img/payment-success.svg" style="width: 16px; height: 16px;">';
        copyBtn.querySelector('.btn-text').textContent = 'تم النسخ!';
        
        showToast('تم نسخ الرابط! 📋', 'success');
        TelegramApp.hapticFeedback('success');
        
        // Reset button after 2 seconds
        setTimeout(() => {
            copyBtn.querySelector('.btn-icon').textContent = '📋';
            copyBtn.querySelector('.btn-text').textContent = 'نسخ';
        }, 2000);
    }, 500);
}

function shareReferralLink() {
    const shareBtn = document.getElementById('share-link-btn');
    const refLink = document.getElementById('referral-link').value;
    const text = '🐼 انضم معي في Panda Giveaways واربح TON مجاناً! 🎁\n\nاستخدم رابطي الخاص وابدأ الربح الآن:';
    
    // Add loading state
    shareBtn.classList.add('loading');
    shareBtn.querySelector('.btn-text').textContent = 'جاري المشاركة...';
    
    setTimeout(() => {
        TelegramApp.shareUrl(refLink, text);
        shareBtn.classList.remove('loading');
        shareBtn.querySelector('.btn-text').textContent = 'مشاركة الرابط';
        TelegramApp.hapticFeedback('success');
    }, 500);
}

// ═══════════════════════════════════════════════════════════════
// 📝 TASKS PAGE
// ═══════════════════════════════════════════════════════════════

async function loadTasks() {
    try {
        const [tasksResponse, completedResponse] = await Promise.all([
            API.getTasks(),
            API.getCompletedTasks(TelegramApp.getUserId())
        ]);
        
        if (tasksResponse.success && completedResponse.success) {
            displayTasks(tasksResponse.data, completedResponse.data);
        }
    } catch (error) {
        console.error('Error loading tasks:', error);
    }
}

function displayTasks(tasks, completedTaskIds) {
    const tasksList = document.getElementById('tasks-list');
    const completedCount = document.getElementById('completed-tasks-count');
    const totalCount = document.getElementById('total-tasks-count');
    const progressFill = document.getElementById('tasks-progress-fill');
    
    tasksList.innerHTML = '';
    
    if (tasks.length === 0) {
        tasksList.innerHTML = '<p style="text-align: center; color: var(--text-secondary); padding: 20px;">لا توجد مهام حالياً. تحقق لاحقاً!</p>';
        return;
    }
    
    completedCount.textContent = completedTaskIds.length;
    totalCount.textContent = tasks.length;
    const progress = (completedTaskIds.length / tasks.length) * 100;
    progressFill.style.width = `${progress}%`;
    
    tasks.forEach(task => {
        const isCompleted = completedTaskIds.includes(task.id);
        
        const item = document.createElement('div');
        item.className = `task-item ${isCompleted ? 'completed' : ''}`;
        
        const info = document.createElement('div');
        info.className = 'task-info';
        
        const name = document.createElement('div');
        name.className = 'task-name';
        name.textContent = task.task_name;
        
        const description = document.createElement('div');
        description.className = 'task-description';
        description.textContent = task.task_description;
        
        info.appendChild(name);
        info.appendChild(description);
        
        const button = document.createElement('button');
        button.className = 'task-action';
        if (isCompleted) {
            button.innerHTML = '<img src="/img/payment-success.svg" alt="✓" style="width: 14px; height: 14px; vertical-align: middle; margin-left: 2px;"> مكتمل';
        } else {
            button.textContent = '▶️ ابدأ';
        }
        button.disabled = isCompleted;
        
        if (!isCompleted) {
            button.addEventListener('click', () => handleTaskClick(task));
        }
        
        item.appendChild(info);
        item.appendChild(button);
        
        tasksList.appendChild(item);
    });
}

async function handleTaskClick(task) {
    TelegramApp.hapticFeedback('light');
    
    if (task.task_type === 'join_channel' && task.channel_id) {
        // فتح القناة
        TelegramApp.openLink(`https://t.me/${task.channel_id.replace('@', '')}`);
        
        // الانتظار قليلاً ثم التحقق
        setTimeout(async () => {
            TelegramApp.showConfirm('هل انضممت للقناة؟', async (confirmed) => {
                if (confirmed) {
                    await completeTask(task.id);
                }
            });
        }, 3000);
    } else if (task.task_type === 'share_bot') {
        shareReferralLink();
        setTimeout(async () => {
            await completeTask(task.id);
        }, 2000);
    } else if (task.link_url) {
        TelegramApp.openLink(task.link_url);
        setTimeout(async () => {
            await completeTask(task.id);
        }, 2000);
    }
}

async function completeTask(taskId) {
    try {
        showLoading(true);
        const response = await API.completeTask(TelegramApp.getUserId(), taskId);
        
        if (response.success) {
            showToast('<img src="/img/payment-success.svg" style="width: 16px; height: 16px; vertical-align: middle;"> تم إكمال المهمة!', 'success');
            TelegramApp.hapticFeedback('success');
            await loadTasks();
        } else {
            showToast('<img src="/img/payment-failure.svg" style="width: 16px; height: 16px; vertical-align: middle;"> فشل إكمال المهمة', 'error');
        }
    } catch (error) {
        console.error('Error completing task:', error);
        showToast('حدث خطأ', 'error');
    } finally {
        showLoading(false);
    }
}

// ═══════════════════════════════════════════════════════════════
// 💸 WITHDRAWAL PAGE
// ═══════════════════════════════════════════════════════════════

function switchWithdrawalMethod(method) {
    // Update tabs
    document.querySelectorAll('.method-tab').forEach(tab => {
        tab.classList.remove('active');
        if (tab.dataset.method === method) {
            tab.classList.add('active');
        }
    });
    
    // Update forms
    document.querySelectorAll('.withdraw-form').forEach(form => {
        form.classList.remove('active');
    });
    document.getElementById(`withdraw-form-${method}`).classList.add('active');
    
    TelegramApp.hapticFeedback('soft');
}

function setMaxAmount(method) {
    const balance = UserState.get('balance');
    const input = document.getElementById(`${method}-amount-input`);
    input.value = balance.toFixed(4);
    TelegramApp.hapticFeedback('light');
}

// منع الضغطات المتعددة على زر السحب
let isWithdrawalProcessing = false;
let lastWithdrawalAttempt = 0;
const WITHDRAWAL_COOLDOWN = 1000; // 1 ثانية

async function submitWithdrawal(method) {
    console.log('🔄 submitWithdrawal called for:', method);
    
    // منع الضغطات السريعة المتتالية
    const now = Date.now();
    if (now - lastWithdrawalAttempt < WITHDRAWAL_COOLDOWN) {
        console.log('⏳ Cooldown active, ignoring click');
        return;
    }
    lastWithdrawalAttempt = now;
    
    // منع الضغطات المتعددة أثناء المعالجة
    if (isWithdrawalProcessing) {
        console.log('⏳ Already processing withdrawal');
        showToast('⏳ جاري معالجة الطلب...', 'warning');
        return;
    }
    
    const amountInput = document.getElementById(`${method}-amount-input`);
    const amount = parseFloat(amountInput.value);
    
    // Validation
    if (isNaN(amount) || amount <= 0) {
        showToast('أدخل مبلغاً صحيحاً', 'error');
        addAnimation(amountInput, 'shake');
        return;
    }
    
    if (amount < CONFIG.MIN_WITHDRAWAL_AMOUNT) {
        showToast(`الحد الأدنى ${CONFIG.MIN_WITHDRAWAL_AMOUNT} TON`, 'error');
        addAnimation(amountInput, 'shake');
        return;
    }
    
    if (amount > UserState.get('balance')) {
        showToast('رصيد غير كافٍ', 'error');
        addAnimation(amountInput, 'shake');
        return;
    }
    
    let withdrawalData = {
        amount: amount,
        withdrawal_type: method
    };
    
    if (method === 'ton') {
        const walletInput = document.getElementById('ton-wallet-input');
        const wallet = sanitizeInput(walletInput.value);
        
        if (!isValidTonAddress(wallet)) {
            showToast('عنوان محفظة غير صحيح', 'error');
            addAnimation(walletInput, 'shake');
            return;
        }
        
        withdrawalData.wallet_address = wallet;
        
    } else if (method === 'vodafone') {
        const phoneInput = document.getElementById('vodafone-number-input');
        const phone = sanitizeInput(phoneInput.value);
        
        if (!isValidVodafoneNumber(phone)) {
            showToast('رقم فودافون غير صحيح', 'error');
            addAnimation(phoneInput, 'shake');
            return;
        }
        
        withdrawalData.phone_number = phone;
    }
    
    // تعطيل الزر
    const withdrawBtn = document.getElementById(`withdraw-btn-${method}`);
    if (withdrawBtn) {
        withdrawBtn.disabled = true;
        withdrawBtn.style.opacity = '0.6';
    }
    
    // Confirm
    TelegramApp.showConfirm(
        `هل تريد سحب ${amount} TON؟\n\nسيتم خصم المبلغ من رصيدك فوراً وسيتم المراجعة من قبل الإدارة.`,
        async (confirmed) => {
            if (confirmed) {
                isWithdrawalProcessing = true;
                try {
                    await processWithdrawal(withdrawalData);
                } finally {
                    isWithdrawalProcessing = false;
                    // إعادة تفعيل الزر
                    if (withdrawBtn) {
                        withdrawBtn.disabled = false;
                        withdrawBtn.style.opacity = '1';
                    }
                }
            } else {
                // إعادة تفعيل الزر عند الإلغاء
                if (withdrawBtn) {
                    withdrawBtn.disabled = false;
                    withdrawBtn.style.opacity = '1';
                }
            }
        }
    );
}

async function processWithdrawal(data) {
    try {
        showLoading(true);
        const response = await API.requestWithdrawal(TelegramApp.getUserId(), data);
        
        if (response.success) {
            showToast('<img src="/img/payment-success.svg" style="width: 16px; height: 16px; vertical-align: middle;"> تم إرسال طلب السحب بنجاح!', 'success');
            TelegramApp.hapticFeedback('success');
            
            // Update balance
            UserState.update({
                balance: UserState.get('balance') - data.amount
            });
            updateUI();
            
            // Clear inputs
            document.querySelectorAll('.withdraw-form input').forEach(input => {
                input.value = '';
            });
            
            // Reload withdrawals
            await loadWithdrawals();
            
        } else {
            showToast(response.error || 'فشل طلب السحب', 'error');
        }
    } catch (error) {
        console.error('Withdrawal error:', error);
        showToast('حدث خطأ', 'error');
    } finally {
        showLoading(false);
    }
}

// ═══════════════════════════════════════════════════════════════
// 📝 TASKS PAGE
// ═══════════════════════════════════════════════════════════════

async function loadTasks() {
    try {
        // Initialize tasks module
        if (window.TasksModule) {
            await TasksModule.init();
        }
    } catch (error) {
        console.error('Error loading tasks:', error);
    }
}

// ═══════════════════════════════════════════════════════════════
// 💸 WITHDRAWAL PAGE
// ═══════════════════════════════════════════════════════════════

async function loadWithdrawals() {
    try {
        const response = await API.getWithdrawals(TelegramApp.getUserId());
        
        if (response.success) {
            displayWithdrawals(response.data);
        }
    } catch (error) {
        console.error('Error loading withdrawals:', error);
    }
}

function displayWithdrawals(withdrawals) {
    const historyList = document.getElementById('withdrawal-history-list');
    historyList.innerHTML = '';
    
    if (withdrawals.length === 0) {
        historyList.innerHTML = '<p style="text-align: center; color: var(--text-secondary); padding: 20px;">لا توجد سحوبات سابقة</p>';
        return;
    }
    
    withdrawals.forEach(w => {
        const item = document.createElement('div');
        item.className = `history-item ${w.status}`;
        
        const header = document.createElement('div');
        header.className = 'history-header';
        
        const amount = document.createElement('div');
        amount.className = 'history-amount';
        amount.textContent = `${w.amount} TON`;
        
        const status = document.createElement('span');
        status.className = `history-status ${w.status}`;
        if (w.status === 'pending') {
            status.textContent = '⏳ معلق';
        } else if (w.status === 'completed') {
            status.innerHTML = '<img src="/img/payment-success.svg" alt="✓" style="width: 14px; height: 14px; vertical-align: middle; margin-left: 2px;"> مكتمل';
        } else {
            status.innerHTML = '<img src="/img/payment-failure.svg" alt="✗" style="width: 14px; height: 14px; vertical-align: middle; margin-left: 2px;"> مرفوض';
        }
        
        header.appendChild(amount);
        header.appendChild(status);
        
        const details = document.createElement('div');
        details.className = 'history-details';
        details.innerHTML = `
            📅 ${formatDate(w.requested_at)}<br>
            ${w.withdrawal_type === 'ton' ? '💎 TON Wallet' : '📱 Vodafone Cash'}
            ${w.tx_hash ? `<br>🔐 TX: ${w.tx_hash.substring(0, 16)}...` : ''}
        `;
        
        item.appendChild(header);
        item.appendChild(details);
        
        historyList.appendChild(item);
    });
}

// ═══════════════════════════════════════════════════════════════
// 💬 SEND WELCOME MESSAGE
// ═══════════════════════════════════════════════════════════════

async function sendWelcomeMessage() {
    try {
        const userId = TelegramApp.getUserId();
        const username = TelegramApp.getUsername();
        const fullName = TelegramApp.getFullName();
        
        if (!userId) {
            console.log('⚠️ No user ID found, skipping welcome message');
            return;
        }
        
        console.log('📤 Sending welcome message to trigger bot permission...');
        
        const response = await fetch('http://localhost:8081/send-welcome', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: userId,
                username: username,
                full_name: fullName
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log('✅ Welcome message sent - Telegram will show permission dialog if needed');
        } else {
            console.log('⚠️ Welcome message failed:', data.error);
            // لا نوقف التطبيق إذا فشلت الرسالة
        }
    } catch (error) {
        console.error('❌ Error sending welcome message:', error);
        // لا نوقف التطبيق
    }
}

// ═══════════════════════════════════════════════════════════════
// 🎯 EXPORTS & READY
// ═══════════════════════════════════════════════════════════════

// تصدير الوظائف للاستخدام من ملفات أخرى
window.registerPendingReferral = registerPendingReferral;
window.loadUserData = loadUserData;

console.log('🐼 Panda Giveaways App Loaded');

// ═══════════════════════════════════════════════════════════════
// 🚀 CONTINUE APP INITIALIZATION AFTER CHANNELS CHECK
// ═══════════════════════════════════════════════════════════════

window.continueAppInitialization = async function() {
    try {
        // تم التحقق من القنوات
        
        // إلغاء الـ timeout العام إذا كان موجود
        if (window.globalTimeoutId) {
            clearTimeout(window.globalTimeoutId);
        }
        
        // عرض Loading مع رسائل التحديث
        showLoading(true);
        showLoadingWithMessage('✅ تم التحقق من القنوات! جاري المتابعة...');

        // بعد التحقق من القنوات، نسجل الإحالة (بدون انتظار وبحماية من التكرار)
        if (!window.referralProcessed) { // حماية إضافية من التكرار
            window.referralProcessed = true;
            setTimeout(() => {
                if (!window.referralProcessing) {
                    registerPendingReferral().catch(err => {
                        console.log('⚠️ Referral registration failed silently:', err.message);
                        window.referralProcessed = false; // إعادة تعيين في حالة الفشل للمحاولة لاحقاً
                    });
                }
            }, 200); // تأخير أطول قليلاً لتجنب التداخل
        }
        
        // تحميل بيانات المستخدม بtimeout محسن
        showLoadingWithMessage('📊 جاري تحميل بياناتك...');
        
        try {
            await Promise.race([
                loadUserData(),
                new Promise((_, reject) => 
                    setTimeout(() => reject(new Error('loadUserData timeout')), 8000) // تقليل إلى 8 ثوان
                )
            ]);
        } catch (loadError) {
            console.warn('⚠️ Load user data timeout, using fallback');
            // فالباك بسيط بدلاً من الفشل
            const userId = TelegramApp.getUserId();
            if (userId) {
                const userIdEl = document.getElementById('user-id');
                if (userIdEl) userIdEl.textContent = userId;
            }
        }
        showLoadingWithMessage('✅ تم تحميل بياناتك!');
        
        // تحميل جوائز العجلة من API
        showLoadingWithMessage('🎁 جاري تحميل جوائز العجلة...');
        await Promise.race([
            loadWheelPrizes(),
            new Promise((_, reject) => setTimeout(() => reject(new Error('loadWheelPrizes timeout')), 8000))
        ]);
        showLoadingWithMessage('✅ تم تحميل الجوائز!');
        
        // تهيئة UI
        showLoadingWithMessage('🎨 جاري إعداد الواجهة...');
        try {
            initUI();
            // تم إعداد الواجهة بنجاح
        } catch (error) {
            // خطأ في إعداد الواجهة
        }
        
        // تهيئة عجلة الحظ
        showLoadingWithMessage('🎰 جاري إعداد عجلة الحظ...');
        // تأخير صغير لضمان أن DOM جاهز للعجلة
        await new Promise(resolve => setTimeout(resolve, 200));
        
        try {
            // التأكد من وجود الجوائز
            if (!CONFIG.WHEEL_PRIZES || CONFIG.WHEEL_PRIZES.length === 0) {
                showToast('⚠️ جوائز العجلة غير متوفرة، سيتم استخدام الجوائز الافتراضية', 'warning');
                CONFIG.WHEEL_PRIZES = [
                    { name: '0.05 TON', amount: 0.05, probability: 45 },
                    { name: '0.1 TON', amount: 0.1, probability: 30 },
                    { name: '0.15 TON', amount: 0.15, probability: 15 },
                    { name: '0.5 TON', amount: 0.5, probability: 0 },
                    { name: '1.0 TON', amount: 1.0, probability: 0 },
                    { name: 'حظ أوفر', amount: 0, probability: 10 }
                ];
            }
            
            // التحقق من وجود العجلة في DOM
            const wheelCanvas = document.getElementById('wheel-canvas');
            if (!wheelCanvas) {
                throw new Error('عنصر العجلة غير موجود في الصفحة');
            }
            
            showToast('🎯 بدء إنشاء العجلة...', 'info');
            wheel = new WheelOfFortune('wheel-canvas', CONFIG.WHEEL_PRIZES);
            
            if (!wheel || !wheel.canvas) {
                throw new Error('فشل في إنشاء العجلة');
            }
        } catch (error) {
            // عرض رسالة خطأ على العجلة
            const wheelContainer = document.querySelector('.wheel-container');
            if (wheelContainer) {
                wheelContainer.innerHTML = `
                    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; 
                        height: 300px; background: #1a1a1a; border-radius: 20px; padding: 20px; text-align: center;">
                        <div style="font-size: 60px; margin-bottom: 20px;">🔧</div>
                        <h3 style="color: #ff4444; margin-bottom: 10px;">خطأ في عجلة الحظ</h3>
                        <p style="color: #999; font-size: 14px;">${error.message}</p>
                        <button onclick="window.location.reload()" 
                            style="margin-top: 15px; padding: 8px 16px; background: #ffa500; color: #000; 
                            border: none; border-radius: 6px; cursor: pointer;">إعادة تحميل</button>
                    </div>
                `;
            }
        }
        
        // تحميل البيانات الأولية مع timeout مختصر
        showLoadingWithMessage('📊 جاري تحميل البيانات...');
        try {
            await Promise.race([
                loadInitialData(),
                new Promise((_, reject) => setTimeout(() => reject(new Error('loadInitialData timeout')), 5000)) // 5 ثوان
            ]);
        } catch (dataError) {
            console.warn('⚠️ Initial data loading timeout, continuing anyway:', dataError.message);
            // نواصل بدون إيقاف التطبيق
        }
        
        // التحقق من معاملات URL للتنقل
        const urlParams = new URLSearchParams(window.location.search);
        const targetPage = urlParams.get('page');
        if (targetPage && ['wheel', 'tasks', 'withdraw'].includes(targetPage)) {
            switchPage(targetPage);
        }
        
        // إخفاء Loading وإظهار المحتوى
        setTimeout(() => {
            if (window.globalTimeoutId) {
                clearTimeout(window.globalTimeoutId);
            }
            showLoading(false);
            document.body.classList.remove('loading');
        }, 500);
        
    } catch (error) {
        // عرض رسالة خطأ مرئية
        if (window.globalTimeoutId) {
            clearTimeout(window.globalTimeoutId);
        }
        showLoading(false);
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = `
            position: fixed; top: 20px; left: 50%; transform: translateX(-50%); 
            background: #ff4444; color: white; padding: 15px 20px; border-radius: 8px; 
            z-index: 9999; max-width: 90%; text-align: center; font-weight: bold;
        `;
        errorDiv.innerHTML = `🚫 خطأ في التحميل: ${error.message}`;
        document.body.appendChild(errorDiv);
        
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.parentNode.removeChild(errorDiv);
            }
        }, 5000);
    }
};

// ═══════════════════════════════════════════════════════════════
// 🔄 SAFE NAVIGATION - للحفاظ على Telegram WebApp Context
// ═══════════════════════════════════════════════════════════════

/**
 * الانتقال الآمن بين الصفحات مع الحفاظ على Telegram WebApp context
 * @param {string} page - اسم الصفحة (مثل: 'referral-program.html', 'index.html')
 * @param {object} params - معاملات إضافية
 */
function safeNavigate(page, params = {}) {
    try {
        // حفظ Telegram init data قبل الانتقال
        if (window.Telegram?.WebApp?.initData) {
            sessionStorage.setItem('tg_init_data', window.Telegram.WebApp.initData);
            sessionStorage.setItem('tg_init_data_timestamp', Date.now().toString());
        }
        
        // بناء URL مع المعاملات
        let url = page;
        const queryParams = new URLSearchParams(params);
        if (queryParams.toString()) {
            url += '?' + queryParams.toString();
        }
        
        console.log('🔄 Safe navigation to:', url);
        
        // الانتقال
        window.location.href = url;
    } catch (error) {
        console.error('❌ Navigation error:', error);
        // Fallback: انتقال عادي
        window.location.href = page;
    }
}

/**
 * الانتقال لصفحة الإحالات
 */
function navigateToReferrals() {
    safeNavigate('referral-program.html');
}

/**
 * الانتقال لصفحة index مع page معين
 */
function navigateToIndex(pageName = 'wheel') {
    safeNavigate('index.html', { page: pageName });
}
