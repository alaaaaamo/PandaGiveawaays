// ═══════════════════════════════════════════════════════════════
// 🔧 CONFIGURATION - v2.1 (Updated)
// ═══════════════════════════════════════════════════════════════

const CONFIG = {
    // API Endpoints
    API_BASE_URL: '/api',
    FRONTEND_URL: '',
    BOT_USERNAME: 'PandaGiveawaysBot',
    
    // Admin IDs (استثناء من التحقق)
    ADMIN_IDS: [1797127532, 6603009212],
    
    // Wheel Configuration - نفس النسب بالضبط من صفحة الأدمن
    WHEEL_PRIZES: [
        { name: '0.05 TON', amount: 0.05, probability: 94, color: '#808080', emoji: '🎁', id: 1 },
        { name: '0.1 TON', amount: 0.1, probability: 5, color: '#FFA500', emoji: '🎁', id: 2 },
        { name: '0.15 TON', amount: 0.15, probability: 1, color: '#9370DB', emoji: '🎁', id: 3 },
        { name: '0.5 TON', amount: 0.5, probability: 0, color: '#32CD32', emoji: '🏆', id: 4 },
        { name: '1.0 TON', amount: 1.0, probability: 0, color: '#FF1493', emoji: '🎁', id: 5 },
        { name: '0.25 TON', amount: 0.25, probability: 0, color: '#808080', emoji: '🎁', id: 6 }
    ],
    
    // Referral & Tasks (تذاكر بدلاً من عملات)
    SPINS_PER_REFERRALS: 5,        // عدد الإحالات للحصول على لفة
    TICKETS_PER_TASK: 1,           // عدد التذاكر لكل مهمة
    TICKETS_FOR_SPIN: 5,           // عدد التذاكر للحصول على لفة
    REFERRALS_FOR_SPIN: 5,         // عدد الإحالات للحصول على لفة
    MIN_WITHDRAWAL_AMOUNT: 0.1,    // 0.1 TON لكل طرق السحب
    
    // Required Channels
    REQUIRED_CHANNELS: [
        { id: '@PandaAdds', name: 'Panda Adds', url: 'https://t.me/PandaAdds' },
        { id: '@CRYPTO_FLASSH', name: 'Crypto Flash', url: 'https://t.me/CRYPTO_FLASSH' }
    ],
    
    // Admin IDs
    ADMIN_IDS: [1797127532, 6603009212],
    
    // Security
    MAX_SPINS_PER_DAY: 100,  // حد أقصى للفات اليومية
    SPIN_COOLDOWN: 2000,     // فترة الانتظار بين اللفات (2 ثانية)
    
    // Animation Durations
    SPIN_DURATION: 5000,     // مدة دوران العجلة (5 ثواني)
    TOAST_DURATION: 3000     // مدة ظهور الإشعارات
};

// ═══════════════════════════════════════════════════════════════
// 🔐 SECURITY & VALIDATION
// ═══════════════════════════════════════════════════════════════

// توليد Session ID آمن
function generateSessionId() {
    return Array.from(crypto.getRandomValues(new Uint8Array(32)))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');
}

// التحقق من صحة TON Wallet Address
function isValidTonAddress(address) {
    // TON addresses start with UQ, EQ, or kQ and are 48 characters
    const regex = /^[UEk]Q[A-Za-z0-9_-]{46}$/;
    return regex.test(address);
}

// التحقق من رقم فودافون مصري
function isValidVodafoneNumber(number) {
    // Egyptian Vodafone: starts with 010, 11 digits
    const regex = /^010\d{8}$/;
    return regex.test(number);
}

// منع SQL Injection & XSS
function sanitizeInput(input) {
    if (typeof input !== 'string') return input;
    return input
        .replace(/[<>]/g, '')
        .replace(/['";]/g, '')
        .trim();
}

// تشفير بيانات حساسة
async function hashData(data) {
    const encoder = new TextEncoder();
    const dataBuffer = encoder.encode(data);
    const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

// ═══════════════════════════════════════════════════════════════
// 💾 LOCAL STORAGE MANAGER
// ═══════════════════════════════════════════════════════════════

const Storage = {
    // حفظ بيانات
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (e) {
            console.error('Storage Error:', e);
        }
    },
    
    // جلب بيانات
    get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (e) {
            console.error('Storage Error:', e);
            return defaultValue;
        }
    },
    
    // حذف بيانات
    remove(key) {
        try {
            localStorage.removeItem(key);
        } catch (e) {
            console.error('Storage Error:', e);
        }
    },
    
    // مسح كل البيانات
    clear() {
        try {
            localStorage.clear();
        } catch (e) {
            console.error('Storage Error:', e);
        }
    }
};

// ═══════════════════════════════════════════════════════════════
// 📊 USER STATE MANAGER
// ═══════════════════════════════════════════════════════════════

const UserState = {
    data: null,
    sessionId: null,
    lastSpinTime: 0,
    spinLock: false,  // منع اللفات المتعددة
    
    // تهيئة البيانات
    init(userData) {
        this.data = userData;
        this.sessionId = Storage.get('sessionId') || generateSessionId();
        Storage.set('sessionId', this.sessionId);
        this.lastSpinTime = Storage.get('lastSpinTime', 0);
    },
    
    // تحديث البيانات
    update(updates) {
        this.data = { ...this.data, ...updates };
    },
    
    // الحصول على البيانات
    get(key) {
        return this.data ? this.data[key] : null;
    },
    
    // التحقق من إمكانية اللف
    canSpin() {
        const now = Date.now();
        const timeSinceLastSpin = now - this.lastSpinTime;
        
        if (this.spinLock) {
            return { can: false, reason: 'جاري اللف...' };
        }
        
        if (this.get('available_spins') <= 0) {
            return { can: false, reason: 'لا توجد لفات متاحة' };
        }
        
        if (timeSinceLastSpin < CONFIG.SPIN_COOLDOWN) {
            return { can: false, reason: 'انتظر قليلاً...' };
        }
        
        return { can: true };
    },
    
    // قفل اللف
    lockSpin() {
        this.spinLock = true;
        this.lastSpinTime = Date.now();
        Storage.set('lastSpinTime', this.lastSpinTime);
    },
    
    // فك قفل اللف
    unlockSpin() {
        this.spinLock = false;
    }
};

// ═══════════════════════════════════════════════════════════════
// 🎨 UI HELPERS
// ═══════════════════════════════════════════════════════════════

// عرض Toast Notification
function showToast(message, type = 'info', duration = CONFIG.TOAST_DURATION) {
    const container = document.getElementById('toast-container');
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// عرض/إخفاء Loading
function showLoading(show = true) {
    const loading = document.getElementById('loading-overlay');
    if (show) {
        loading.classList.remove('hidden');
    } else {
        loading.classList.add('hidden');
    }
}

// تنسيق التاريخ
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 1) return 'الآن';
    if (minutes < 60) return `منذ ${minutes} دقيقة`;
    if (hours < 24) return `منذ ${hours} ساعة`;
    if (days < 7) return `منذ ${days} يوم`;
    
    return date.toLocaleDateString('ar-EG', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
}

// تنسيق الأرقام
function formatNumber(number, decimals = 4) {
    return Number(number).toFixed(decimals);
}

// إضافة Animation Class
function addAnimation(element, animationClass) {
    element.classList.add(animationClass);
    element.addEventListener('animationend', () => {
        element.classList.remove(animationClass);
    }, { once: true });
}

// ═══════════════════════════════════════════════════════════════
// 📱 TELEGRAM WEB APP INTEGRATION
// ═══════════════════════════════════════════════════════════════

const TelegramApp = {
    isReady: false,
    webApp: null,
    user: null,
    isTelegram: false,
    
    // تهيئة التطبيق
    init() {
        console.log('🔄 Initializing TelegramApp...'); 
        
        // التحقق من وجود Telegram WebApp
        if (typeof Telegram === 'undefined' || !Telegram.WebApp) {
            console.warn('❌ Telegram WebApp not available - not running inside Telegram');
            this.isTelegram = false;
            this.isReady = true;
            return;
        }
        
        console.log('✅ Telegram WebApp detected');
        this.isTelegram = true;
        this.webApp = Telegram.WebApp;
        
        try {
            this.webApp.ready();
            this.webApp.expand();
            
            // تخصيص الألوان
            this.webApp.setHeaderColor('#1a1f16');
            this.webApp.setBackgroundColor('#1a1f16');
            
            // الحصول على بيانات المستخدم
            console.log('🔍 Checking initDataUnsafe:', this.webApp.initDataUnsafe);
            
            if (this.webApp.initDataUnsafe && this.webApp.initDataUnsafe.user) {
                this.user = this.webApp.initDataUnsafe.user;
                console.log('✅ User data found:', this.user);
                
                // حفظ الـ user ID في localStorage للمرات القادمة
                try {
                    localStorage.setItem('telegram_user_id', this.user.id.toString());
                    localStorage.setItem('telegram_user_data', JSON.stringify(this.user));
                } catch (e) {
                    console.warn('Could not save user data to localStorage');
                }
            } else {
                console.warn('⚠️ No user data in initDataUnsafe');
                this.user = null;
                
                // محاولة استرداد من localStorage
                try {
                    const cachedUserData = localStorage.getItem('telegram_user_data');
                    if (cachedUserData) {
                        this.user = JSON.parse(cachedUserData);
                        console.log('📱 Retrieved user data from cache:', this.user);
                    }
                } catch (e) {
                    console.warn('Could not retrieve cached user data');
                }
            }
            
            this.isReady = true;
            
            // إعداد زر الرجوع
            this.webApp.BackButton.onClick(() => {
                window.history.back();
            });
            
        } catch (error) {
            console.error('❌ Error initializing Telegram WebApp:', error);
            this.isReady = true;
        }
    },
    
    // الحصول على معرف المستخدم  
    getUserId() {
        try {
            // 1. من Telegram WebApp (الخيار المفضل)
            let userId = this.user?.id || null;
            
            if (userId) {
                DebugError.add(`getUserId() from Telegram WebApp: ${userId}`, 'info');
                return userId;
            }
            
            // 2. من URL parameters (fallback)
            const urlParams = new URLSearchParams(window.location.search);
            const urlUserId = urlParams.get('user_id');
            if (urlUserId) {
                userId = parseInt(urlUserId);
                DebugError.add(`getUserId() from URL params: ${userId}`, 'info');
                return userId;
            }
            
            // 3. من localStorage (cache)
            const cachedUserId = localStorage.getItem('telegram_user_id');
            if (cachedUserId) {
                userId = parseInt(cachedUserId);
                DebugError.add(`getUserId() from localStorage: ${userId}`, 'info');
                return userId;
            }
            
            // 4. من Telegram initData (alternative method)
            if (window.Telegram?.WebApp?.initData) {
                const initData = window.Telegram.WebApp.initData;
                const urlParams = new URLSearchParams(initData);
                const userString = urlParams.get('user');
                if (userString) {
                    const userObj = JSON.parse(decodeURIComponent(userString));
                    userId = userObj.id;
                    DebugError.add(`getUserId() from initData: ${userId}`, 'info');
                    // حفظ في localStorage للمرات القادمة
                    localStorage.setItem('telegram_user_id', userId.toString());
                    return userId;
                }
            }
            
            DebugError.add('No user ID found from any source!', 'error');
            return null;
            
        } catch (error) {
            DebugError.add(`Error in getUserId(): ${error.message}`, 'error', error);
            return null;
        }
    },
    
    // التحقق من صحة التشغيل
    isValidTelegram() {
        return this.isTelegram && this.user && this.user.id;
    },
    
    // الحصول على الاسم الكامل
    getFullName() {
        try {
            if (!this.user) {
                // محاولة الحصول من cache
                const cachedUserData = localStorage.getItem('telegram_user_data');
                if (cachedUserData) {
                    const user = JSON.parse(cachedUserData);
                    return `${user.first_name} ${user.last_name || ''}`.trim();
                }
                return 'جاري التحميل...';
            }
            
            const fullName = `${this.user.first_name} ${this.user.last_name || ''}`.trim();
            DebugError.add(`getFullName(): ${fullName}`, 'info');
            return fullName;
            
        } catch (error) {
            DebugError.add(`Error in getFullName(): ${error.message}`, 'error', error);
            return 'مستخدم';
        }
    },
    
    // الحصول على اسم المستخدم
    getUsername() {
        try {
            if (this.user?.username) {
                DebugError.add(`getUsername(): @${this.user.username}`, 'info');
                return this.user.username;
            }
            
            // محاولة الحصول من cache
            const cachedUserData = localStorage.getItem('telegram_user_data');
            if (cachedUserData) {
                const user = JSON.parse(cachedUserData);
                if (user.username) {
                    return user.username;
                }
            }
            
            // fallback للـ user ID
            const userId = this.getUserId();
            return userId ? `user${userId}` : 'username';
            
        } catch (error) {
            DebugError.add(`Error in getUsername(): ${error.message}`, 'error', error);
            return 'username';
        }
    },
    
    // الحصول على صورة البروفايل
    getPhotoUrl() {
        try {
            // 1. من Telegram user data
            if (this.user?.photo_url) {
                DebugError.add(`getPhotoUrl(): ${this.user.photo_url}`, 'info');
                return this.user.photo_url;
            }
            
            // 2. محاولة الحصول من cache
            const cachedUserData = localStorage.getItem('telegram_user_data');
            if (cachedUserData) {
                const user = JSON.parse(cachedUserData);
                if (user.photo_url) {
                    return user.photo_url;
                }
            }
            
            // 3. استخدام Telegram API لجلب الصورة
            if (this.webApp && this.user?.id) {
                // محاولة جلب الصورة عبر API
                this.fetchUserPhoto(this.user.id);
            }
            
            // 4. صورة افتراضية
            const defaultPhoto = '/img/user-placeholder.svg';
            DebugError.add(`getPhotoUrl(): Using default photo`, 'warn');
            return defaultPhoto;
            
        } catch (error) {
            DebugError.add(`Error in getPhotoUrl(): ${error.message}`, 'error', error);
            return '/img/user-placeholder.svg';
        }
    },
    
    // جلب صورة المستخدم من الـ API
    async fetchUserPhoto(userId) {
        try {
            const response = await fetch(`${CONFIG.API_BASE_URL}/user/${userId}/photo`);
            if (response.ok) {
                const data = await response.json();
                if (data.photo_url) {
                    DebugError.add(`Fetched user photo from API: ${data.photo_url}`, 'info');
                    // حفظ في cache
                    if (this.user) {
                        this.user.photo_url = data.photo_url;
                        localStorage.setItem('telegram_user_data', JSON.stringify(this.user));
                    }
                    // تحديث الواجهة
                    updateUserDisplay({ photo_url: data.photo_url });
                    return data.photo_url;
                }
            }
        } catch (error) {
            DebugError.add(`Error fetching user photo: ${error.message}`, 'error', error);
        }
    },
    
    // إغلاق التطبيق
    close() {
        if (this.webApp) {
            this.webApp.close();
        }
    },
    
    // فتح رابط
    openLink(url) {
        if (this.webApp) {
            this.webApp.openLink(url);
        } else {
            window.open(url, '_blank');
        }
    },
    
    // مشاركة رابط
    shareUrl(url, text) {
        const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`;
        this.openLink(shareUrl);
    },
    
    // اهتزاز
    hapticFeedback(style = 'medium') {
        if (this.webApp?.HapticFeedback) {
            this.webApp.HapticFeedback.impactOccurred(style);
        }
    },
    
    // إشعار
    showAlert(message) {
        if (this.webApp) {
            this.webApp.showAlert(message);
        } else {
            alert(message);
        }
    },
    
    // تأكيد
    showConfirm(message, callback) {
        if (this.webApp) {
            this.webApp.showConfirm(message, callback);
        } else {
            const result = confirm(message);
            callback(result);
        }
    }
};

// ═══════════════════════════════════════════════════════════════
// 🔄 RATE LIMITER (منع الإساءة)
// ═══════════════════════════════════════════════════════════════

const RateLimiter = {
    limits: {},
    
    // التحقق من الحد
    check(action, maxAttempts, timeWindow) {
        const now = Date.now();
        const key = `${action}_${UserState.get('user_id')}`;
        
        if (!this.limits[key]) {
            this.limits[key] = { count: 0, resetTime: now + timeWindow };
        }
        
        const limit = this.limits[key];
        
        // إعادة تعيين إذا انتهت الفترة
        if (now > limit.resetTime) {
            limit.count = 0;
            limit.resetTime = now + timeWindow;
        }
        
        // التحقق من تجاوز الحد
        if (limit.count >= maxAttempts) {
            return false;
        }
        
        limit.count++;
        return true;
    }
};

// ═══════════════════════════════════════════════════════════════
// 📸 TELEGRAM CHANNEL PHOTOS
// ═══════════════════════════════════════════════════════════════

/**
 * استخراج اسم المستخدم من رابط أو معرف Telegram
 * @param {string} input - channel_id, channel_url, or task_link
 * @returns {string|null} - username without @, or null if not found
 */
function extractTelegramUsername(input) {
    if (!input) return null;
    
    // إزالة المسافات
    input = input.trim();
    
    // إذا كان يبدأ بـ @، نزيله ونرجع الاسم
    if (input.startsWith('@')) {
        return input.substring(1);
    }
    
    // محاولة استخراجه من رابط t.me
    const tmeLinkMatch = input.match(/t\.me\/([a-zA-Z0-9_]+)/);
    if (tmeLinkMatch) {
        return tmeLinkMatch[1];
    }
    
    // محاولة استخراجه من رابط telegram.me
    const telegramMeMatch = input.match(/telegram\.me\/([a-zA-Z0-9_]+)/);
    if (telegramMeMatch) {
        return telegramMeMatch[1];
    }
    
    // إذا كان اسم مستخدم بدون @ أو رابط
    if (/^[a-zA-Z0-9_]+$/.test(input)) {
        return input;
    }
    
    return null;
}

/**
 * إنشاء HTML لصورة قناة Telegram مع fallback
 * @param {string} input - channel_id, channel_url, or task_link
 * @param {string} fallbackEmoji - emoji to show if image fails (default: 📢)
 * @param {string} size - CSS size (default: 40px)
 * @returns {string} HTML string with img and fallback
 */
function createChannelPhotoHTML(input, fallbackEmoji = '📢', size = '40px') {
    const username = extractTelegramUsername(input);
    
    if (!username) {
        // لا يوجد username، نرجع الإيموجي مباشرة
        return `<span class="channel-icon" style="font-size: ${size}">${fallbackEmoji}</span>`;
    }
    
    const photoUrl = `https://t.me/i/userpic/320/${username}.jpg`;
    
    return `
        <img class="channel-photo" 
             src="${photoUrl}" 
             alt="${username}"
             style="width: ${size}; height: ${size}; border-radius: 50%; object-fit: cover; display: inline-block;"
             onerror="this.style.display='none'; this.nextElementSibling.style.display='inline';">
        <span class="channel-icon-fallback" 
              style="font-size: ${size}; display: none;">${fallbackEmoji}</span>
    `;
}

// ═══════════════════════════════════════════════════════════════
// 🎯 EXPORTS
// ═══════════════════════════════════════════════════════════════

window.CONFIG = CONFIG;
window.Storage = Storage;
window.UserState = UserState;
window.showToast = showToast;
window.showLoading = showLoading;
window.formatDate = formatDate;
window.formatNumber = formatNumber;
window.addAnimation = addAnimation;
window.TelegramApp = TelegramApp;
window.RateLimiter = RateLimiter;
window.isValidTonAddress = isValidTonAddress;
window.isValidVodafoneNumber = isValidVodafoneNumber;
window.sanitizeInput = sanitizeInput;
window.hashData = hashData;
window.extractTelegramUsername = extractTelegramUsername;
window.createChannelPhotoHTML = createChannelPhotoHTML;

console.log('✅ Panda Giveaways Config Loaded Successfully');
console.log('📊 CONFIG:', {
    API_BASE_URL: CONFIG.API_BASE_URL,
    ADMIN_IDS: CONFIG.ADMIN_IDS,
    MIN_WITHDRAWAL_AMOUNT: CONFIG.MIN_WITHDRAWAL_AMOUNT,
    REQUIRED_CHANNELS: CONFIG.REQUIRED_CHANNELS
});
