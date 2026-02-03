// ═══════════════════════════════════════════════════════════════
// 🔧 CONFIGURATION
// ═══════════════════════════════════════════════════════════════

const CONFIG = {
    // API Endpoints
    API_BASE_URL: 'https://pandagiveawaays.onrender.com/api',
    BOT_USERNAME: 'PandaGiveawaysBot',
    
    // Wheel Configuration
    WHEEL_PRIZES: [
        { name: '0.1 TON', amount: 0.1, probability: 5, color: '#FF9500' },      // برتقالي زاهي
        { name: '0.2 TON', amount: 0.2, probability: 3, color: '#FF3B30' },      // أحمر زاهي
        { name: '0.5 TON', amount: 0.5, probability: 1, color: '#34C759' },      // أخضر زاهي
        { name: '1.0 TON', amount: 1.0, probability: 0.5, color: '#FF2D55' },    // وردي زاهي
        { name: '0.05 TON', amount: 0.05, probability: 10, color: '#00C7BE' },   // سيان زاهي
        { name: '0.01 TON', amount: 0.01, probability: 30, color: '#AF52DE' },   // بنفسجي زاهي
        { name: 'حظ أوفر', amount: 0, probability: 50.5, color: '#8E8E93' }       // رمادي
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
    
    // تهيئة التطبيق
    init() {
        if (typeof Telegram === 'undefined' || !Telegram.WebApp) {
            console.warn('Telegram WebApp not available');
            // Development mode - استخدام بيانات تجريبية
            this.user = {
                id: 123456789,
                first_name: 'Test',
                last_name: 'User',
                username: 'testuser',
                photo_url: 'https://via.placeholder.com/100'
            };
            this.isReady = true;
            return;
        }
        
        this.webApp = Telegram.WebApp;
        this.webApp.ready();
        this.webApp.expand();
        
        // تخصيص الألوان
        this.webApp.setHeaderColor('#0d1117');
        this.webApp.setBackgroundColor('#0d1117');
        
        // الحصول على بيانات المستخدم
        this.user = this.webApp.initDataUnsafe?.user || null;
        this.isReady = true;
        
        // إعداد زر الرجوع
        this.webApp.BackButton.onClick(() => {
            window.history.back();
        });
    },
    
    // الحصول على معرف المستخدم
    getUserId() {
        return this.user?.id || null;
    },
    
    // الحصول على الاسم الكامل
    getFullName() {
        if (!this.user) return 'Guest';
        return `${this.user.first_name} ${this.user.last_name || ''}`.trim();
    },
    
    // الحصول على اسم المستخدم
    getUsername() {
        return this.user?.username || `user${this.getUserId()}`;
    },
    
    // الحصول على صورة البروفايل
    getPhotoUrl() {
        return this.user?.photo_url || 'https://via.placeholder.com/100';
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

console.log('✅ Panda Giveaways Config Loaded Successfully');
console.log('📊 CONFIG:', {
    API_BASE_URL: CONFIG.API_BASE_URL,
    ADMIN_IDS: CONFIG.ADMIN_IDS,
    MIN_WITHDRAWAL_AMOUNT: CONFIG.MIN_WITHDRAWAL_AMOUNT,
    REQUIRED_CHANNELS: CONFIG.REQUIRED_CHANNELS
});
