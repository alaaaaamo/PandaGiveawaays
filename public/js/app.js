// ═══════════════════════════════════════════════════════════════
// 🐼 PANDA GIVEAWAYS - MAIN APP
// ═══════════════════════════════════════════════════════════════

let wheel = null;

// ═══════════════════════════════════════════════════════════════
// 🚀 APP INITIALIZATION
// ═══════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', async () => {
    console.log('🐼 Panda Giveaways Starting...');
    
    try {
        // تهيئة Telegram Web App
        TelegramApp.init();
        
        // عرض Loading
        showLoading(true);
        
        // ═══════════════════════════════════════════════════════
        // 🔐 التحقق من حالة المستخدم (device verification)
        // ═══════════════════════════════════════════════════════
        const userId = TelegramApp.getUserId();
        
        // استثناء الأدمن من التحقق
        const isAdmin = CONFIG.ADMIN_IDS && CONFIG.ADMIN_IDS.includes(userId);
        
        if (userId && !isAdmin) {
            try {
                const verifyStatusResp = await fetch(`${CONFIG.API_BASE_URL}/verification/status/${userId}`);
                const verifyData = await verifyStatusResp.json();
                
                if (!verifyData.verified) {
                    // المستخدم غير متحقق - توجيه تلقائي للبوت
                    showLoading(false);
                    
                    const botUrl = `https://t.me/${window.CONFIG?.BOT_USERNAME || 'PandaGiveawaysBot'}`;
                    let redirectFailed = false;
                    
                    // عرض رسالة التوجيه
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
                            <p id="redirect-message" style="color: #8b95a1; font-size: 16px; line-height: 1.6; max-width: 400px;">
                                جاري توجيهك للبوت للتحقق من جهازك...
                            </p>
                            <div id="spinner" style="margin-top: 20px;">
                                <div style="width: 40px; height: 40px; border: 4px solid #ffa500; 
                                    border-top-color: transparent; border-radius: 50%; 
                                    animation: spin 1s linear infinite;">
                                </div>
                            </div>
                            <p id="countdown" style="color: #ffa500; font-size: 18px; font-weight: bold; margin-top: 15px;">5</p>
                            <p style="color: #666; font-size: 14px; margin-top: 10px;">
                                Redirecting to bot...
                            </p>
                            <a id="manual-redirect" href="${botUrl}" 
                                style="display: none; margin-top: 20px; padding: 14px 32px; 
                                background: linear-gradient(135deg, #ffa500, #ff8c00); color: #000; 
                                text-decoration: none; border-radius: 12px; font-weight: bold; 
                                font-size: 16px; box-shadow: 0 4px 15px rgba(255, 165, 0, 0.3); 
                                transition: transform 0.2s; align-items: center; gap: 8px;" 
                                onmouseover="this.style.transform='scale(1.05)'" 
                                onmouseout="this.style.transform='scale(1)'">
                                <img src="/img/links.png" alt="Link" style="width: 24px; height: 24px; vertical-align: middle;">
                                فتح البوت للتحقق
                            </a>
                        </div>
                    `;
                    
                    // إضافة animation للـ spinner
                    const style = document.createElement('style');
                    style.textContent = `
                        @keyframes spin {
                            0% { transform: rotate(0deg); }
                            100% { transform: rotate(360deg); }
                        }
                    `;
                    document.head.appendChild(style);
                    
                    // Countdown من 5 إلى 1
                    let countdown = 5;
                    const countdownEl = document.getElementById('countdown');
                    const countdownInterval = setInterval(() => {
                        countdown--;
                        if (countdownEl && countdown > 0) {
                            countdownEl.textContent = countdown;
                        } else {
                            clearInterval(countdownInterval);
                        }
                    }, 1000);
                    
                    // محاولة التوجيه التلقائي بعد 5 ثوانٍ
                    setTimeout(() => {
                        console.log('🔄 Attempting automatic redirect to bot...');
                        
                        if (window.Telegram?.WebApp) {
                            try {
                                // محاولة 1: استخدام openTelegramLink (الأفضل)
                                console.log('Trying openTelegramLink...');
                                window.Telegram.WebApp.openTelegramLink(botUrl);
                                
                                // إذا نجح، إخفاء الـ spinner وإظهار رسالة النجاح
                                setTimeout(() => {
                                    const spinner = document.getElementById('spinner');
                                    const message = document.getElementById('redirect-message');
                                    const countdownEl = document.getElementById('countdown');
                                    
                                    if (spinner) spinner.style.display = 'none';
                                    if (countdownEl) countdownEl.style.display = 'none';
                                    if (message) {
                                        message.textContent = '✅ تم فتح البوت! يمكنك إغلاق هذه النافذة.';
                                        message.style.color = '#4caf50';
                                    }
                                    
                                    // محاولة إغلاق المينى آب بعد 2 ثانية
                                    setTimeout(() => {
                                        try {
                                            window.Telegram.WebApp.close();
                                        } catch (e) {
                                            console.log('Could not close Mini App:', e);
                                        }
                                    }, 2000);
                                }, 500);
                                
                            } catch (e) {
                                console.warn('openTelegramLink failed, trying openLink...', e);
                                
                                // محاولة 2: استخدام openLink
                                try {
                                    window.Telegram.WebApp.openLink(botUrl);
                                    setTimeout(() => {
                                        const spinner = document.getElementById('spinner');
                                        const message = document.getElementById('redirect-message');
                                        const countdownEl = document.getElementById('countdown');
                                        
                                        if (spinner) spinner.style.display = 'none';
                                        if (countdownEl) countdownEl.style.display = 'none';
                                        if (message) {
                                            message.textContent = '✅ تم فتح البوت! يمكنك إغلاق هذه النافذة.';
                                            message.style.color = '#4caf50';
                                        }
                                    }, 500);
                                } catch (e2) {
                                    console.error('Both redirect methods failed:', e2);
                                    redirectFailed = true;
                                    showManualRedirectButton();
                                }
                            }
                        } else {
                            // في حالة عدم وجود Telegram WebApp
                            console.log('Telegram WebApp not available, using window.open');
                            try {
                                window.open(botUrl, '_blank');
                            } catch (e) {
                                console.error('window.open failed:', e);
                                redirectFailed = true;
                                showManualRedirectButton();
                            }
                        }
                        
                        // إذا فشل كل شيء بعد 3 ثوانٍ، إظهار الزر اليدوي
                        setTimeout(() => {
                            if (document.getElementById('manual-redirect').style.display === 'none') {
                                showManualRedirectButton();
                            }
                        }, 3000);
                        
                    }, 5000);
                    
                    // دالة لإظهار زر التوجيه اليدوي
                    function showManualRedirectButton() {
                        console.log('Showing manual redirect button');
                        const spinner = document.getElementById('spinner');
                        const message = document.getElementById('redirect-message');
                        const manualBtn = document.getElementById('manual-redirect');
                        const countdownEl = document.getElementById('countdown');
                        
                        if (spinner) spinner.style.display = 'none';
                        if (countdownEl) countdownEl.style.display = 'none';
                        if (message) {
                            message.textContent = '⚠️ فشل التوجيه التلقائي. الرجاء الضغط على الزر أدناه.';
                            message.style.color = '#ff9800';
                        }
                        if (manualBtn) {
                            manualBtn.style.display = 'inline-flex';
                        }
                    }
                    
                    return;
                }
            } catch (verifyError) {
                console.warn('⚠️ Could not check verification status:', verifyError);
                // في حالة الخطأ، نستمر عادياً
            }
        }
        
        // إرسال رسالة ترحيبية (سيظهر تليجرام "Allow bot to message you?" تلقائياً)
        await sendWelcomeMessage();
        
        // حفظ referrer_id مؤقتاً إذا موجود (سيتم تسجيله بعد التحقق من القنوات)
        savePendingReferral();
        
        // Check required channels FIRST before loading anything
        const channelsVerified = await checkRequiredChannels();
        
        if (!channelsVerified) {
            // Hide loading - channels modal will be shown
            showLoading(false);
            console.log('⏸️ Waiting for channel verification...');
            return;
        }
        
        // بعد التحقق من القنوات، نسجل الإحالة
        await registerPendingReferral();
        
        // تحميل بيانات المستخدم
        await loadUserData();
        
        // تحميل جوائز العجلة من API
        await loadWheelPrizes();
        
        // تهيئة UI
        initUI();
        
        // تهيئة عجلة الحظ
        wheel = new WheelOfFortune('wheel-canvas', CONFIG.WHEEL_PRIZES);
        
        // تحميل البيانات الأولية
        await loadInitialData();
        
        // التحقق من معاملات URL للتنقل
        const urlParams = new URLSearchParams(window.location.search);
        const targetPage = urlParams.get('page');
        if (targetPage && ['wheel', 'tasks', 'withdraw'].includes(targetPage)) {
            switchPage(targetPage);
        }
        
        // إخفاء Loading
        showLoading(false);
        
        console.log('✅ App Initialized Successfully');
        
    } catch (error) {
        console.error('❌ App Initialization Error:', error);
        showLoading(false);
        showToast('حدث خطأ في تحميل التطبيق', 'error');
    }
});

// ═══════════════════════════════════════════════════════════════
// 🎁 WHEEL PRIZES LOADER
// ═══════════════════════════════════════════════════════════════

async function loadWheelPrizes() {
    try {
        console.log('🎁 Loading wheel prizes from API...');
        const response = await fetch('/api/admin/prizes');
        const result = await response.json();
        
        if (result.success && result.data && result.data.length > 0) {
            // تحويل صيغة الجوائز من DB إلى صيغة العجلة
            CONFIG.WHEEL_PRIZES = result.data.map(prize => ({
                name: prize.name,
                amount: prize.value,
                probability: prize.probability,
                color: prize.color
            }));
            console.log(`✅ Loaded ${CONFIG.WHEEL_PRIZES.length} prizes from database`);
        } else {
            console.log('⚠️ Using default prizes from config');
        }
    } catch (error) {
        console.error('❌ Error loading prizes:', error);
        console.log('⚠️ Using default prizes from config');
    }
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
    try {
        const pendingData = localStorage.getItem('pendingReferral');
        
        if (!pendingData) {
            console.log('ℹ️ No pending referral');
            return;
        }
        
        const referralData = JSON.parse(pendingData);
        console.log('📎 Registering pending referral after channel verification:', referralData);
        
        // تسجيل الإحالة
        const response = await fetch(`${CONFIG.API_BASE_URL}/referral/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                referrer_id: referralData.referrer_id,
                referred_id: referralData.referred_id
            })
        });
        
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
        console.error('Error registering pending referral:', error);
        // نبقي البيانات للمحاولة مرة أخرى
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
                    showToast('تم تسجيل الإحالة بنجاح! 🎉', 'success');
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
        let userId = TelegramApp.getUserId();
        
        // إذا كان getUserId يرجع null، حاول الحصول عليه من URL
        if (!userId) {
            const urlParams = new URLSearchParams(window.location.search);
            userId = urlParams.get('user_id');
        }
        
        // إذا لم نجد user_id، استخدم قيمة تجريبية
        if (!userId) {
            console.warn('No user ID found, using test ID');
            userId = 123456789; // Test user
        }
        
        console.log('Loading data for user:', userId);
        
        // تحديث بيانات المستخدم من Telegram أولاً
        try {
            const username = TelegramApp.getUsername() || `user_${userId}`;
            const fullName = TelegramApp.getFullName() || username;
            
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
            console.log('✅ Profile updated with Telegram data');
        } catch (profileError) {
            console.warn('⚠️ Could not update profile:', profileError);
        }
        
        const response = await API.getUserData(userId);
        
        if (response.success) {
            UserState.init(response.data);
            updateUserProfile();
            updateUI();
        } else {
            throw new Error('فشل تحميل بيانات المستخدم');
        }
    } catch (error) {
        console.error('Error loading user data:', error);
        showToast('حدث خطأ في تحميل البيانات', 'error');
        // لا نرمي الخطأ لنسمح للتطبيق بالاستمرار
    }
}

function updateUserProfile() {
    const avatar = document.getElementById('user-avatar');
    const name = document.getElementById('user-name');
    const username = document.getElementById('user-username');
    
    avatar.src = TelegramApp.getPhotoUrl();
    name.textContent = TelegramApp.getFullName();
    username.textContent = `@${TelegramApp.getUsername()}`;
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
    // Channels already verified in main init
    await Promise.all([
        loadSpinHistory(),
        loadReferrals(),
        loadTasks(),
        loadWithdrawals()
    ]);
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
    document.getElementById('withdraw-btn-ton')?.addEventListener('click', () => {
        submitWithdrawal('ton');
    });
    document.getElementById('withdraw-btn-vodafone')?.addEventListener('click', () => {
        submitWithdrawal('vodafone');
    });
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

async function submitWithdrawal(method) {
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
    
    // Confirm
    TelegramApp.showConfirm(
        `هل تريد سحب ${amount} TON؟\n\nسيتم خصم المبلغ من رصيدك فوراً وسيتم المراجعة من قبل الإدارة.`,
        async (confirmed) => {
            if (confirmed) {
                await processWithdrawal(withdrawalData);
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
