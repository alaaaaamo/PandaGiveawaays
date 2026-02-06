// ═══════════════════════════════════════════════════════════════
// 🐛 DEBUG & ERROR DISPLAY SYSTEM - DISABLED FOR PRODUCTION
// ═══════════════════════════════════════════════════════════════

// Enable/disable debug modes for production
const DEBUG_CONFIG = {
    SHOW_DEBUG_UI: true,         // ✅ إظهار UI الـ debug على الشاشة
    SHOW_SERVER_STATUS: true,    // ✅ إظهار مؤشر حالة السيرفر
    CONSOLE_LOGGING: true,       // ✅ الـ logging في الـ console
    AUTO_SHOW_ERRORS: true       // ✅ إظهار تلقائي للأخطاء
};

class DebugError {
    static container = null;
    static isVisible = false;
    static errors = [];
    
    static init() {
        // تعطيل الـ debug UI في الإنتاج
        if (!DEBUG_CONFIG.SHOW_DEBUG_UI) {
            return;
        }
        
        // إنشاء container للأخطاء (معطل في الإنتاج)
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'debug-error-container';
            this.container.style.cssText = `
                position: fixed;
                top: 10px;
                right: 10px;
                max-width: 350px;
                max-height: 400px;
                overflow-y: auto;
                background: rgba(40, 40, 40, 0.95);
                border: 2px solid #ff4444;
                border-radius: 10px;
                padding: 15px;
                z-index: 10000;
                color: #fff;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                display: none;
            `;
            
            // إضافة header
            this.container.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; border-bottom: 1px solid #555; padding-bottom: 10px;">
                    <strong style="color: #ff4444;">🐛 Debug Console</strong>
                    <button onclick="DebugError.toggle()" style="background: #666; color: #fff; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer;">Hide</button>
                </div>
                <div id="debug-error-list"></div>
                <div style="margin-top: 10px; text-align: center;">
                    <button onclick="DebugError.clear()" style="background: #ff4444; color: #fff; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer;">Clear</button>
                </div>
            `;
            
            document.body.appendChild(this.container);
            
            // إضافة زر toggle في الزاوية (معطل في الإنتاج)
            const toggleBtn = document.createElement('div');
            toggleBtn.id = 'debug-toggle-btn';
            toggleBtn.style.cssText = `
                position: fixed;
                top: 10px;
                left: 10px;
                background: #ff4444;
                color: #fff;
                width: 40px;
                height: 40px;
                border-radius: 50%;
                display: none; /* مخفي في الإنتاج */
                align-items: center;
                justify-content: center;
                cursor: pointer;
                z-index: 10001;
                font-weight: bold;
                box-shadow: 0 2px 10px rgba(255, 68, 68, 0.3);
            `;
            toggleBtn.innerHTML = '🐛';
            toggleBtn.onclick = () => this.toggle();
            document.body.appendChild(toggleBtn);
        }
    }
    
    static add(message, type = 'error', data = null) {
        const timestamp = new Date().toLocaleTimeString('ar-EG');
        const error = {
            timestamp,
            message,
            type,
            data: data ? JSON.stringify(data, null, 2) : null
        };
        
        this.errors.unshift(error); // إضافة في البداية
        if (this.errors.length > 50) {
            this.errors.pop(); // حذف القديم
        }
        
        // Console logging فقط إذا مفعل
        if (DEBUG_CONFIG.CONSOLE_LOGGING) {
            console.error(`[${timestamp}] ${message}`, data);
        }
        
        // تحديث UI فقط إذا مفعل
        if (DEBUG_CONFIG.SHOW_DEBUG_UI) {
            this.render();
            
            // إظهار تلقائياً عند الخطأ إذا مفعل
            if (DEBUG_CONFIG.AUTO_SHOW_ERRORS && type === 'error' && !this.isVisible) {
                this.show();
            }
        }
    }
    
    static render() {
        if (!this.container) return;
        
        const list = this.container.querySelector('#debug-error-list');
        list.innerHTML = this.errors.map(error => `
            <div style="margin-bottom: 10px; padding: 8px; background: rgba(255, 255, 255, 0.05); border-radius: 5px; border-left: 3px solid ${error.type === 'error' ? '#ff4444' : error.type === 'warn' ? '#ffa500' : '#4444ff'};">
                <div style="color: #ccc; font-size: 10px;">${error.timestamp}</div>
                <div style="color: ${error.type === 'error' ? '#ff6666' : error.type === 'warn' ? '#ffbb66' : '#66aaff'}; margin: 5px 0;">${error.message}</div>
                ${error.data ? `<pre style="color: #999; font-size: 10px; white-space: pre-wrap; max-height: 100px; overflow-y: auto;">${error.data}</pre>` : ''}
            </div>
        `).join('');
    }
    
    static show() {
        // لا تظهر UI إذا كان معطل في الإنتاج
        if (!DEBUG_CONFIG.SHOW_DEBUG_UI) {
            return;
        }
        
        if (!this.container) this.init();
        this.container.style.display = 'block';
        this.isVisible = true;
    }
    
    static hide() {
        if (this.container) {
            this.container.style.display = 'none';
            this.isVisible = false;
        }
    }
    
    static toggle() {
        if (this.isVisible) {
            this.hide();
        } else {
            this.show();
        }
    }
    
    static clear() {
        this.errors = [];
        this.render();
    }
}

// تهيئة النظام (فقط إذا مفعل)
if (DEBUG_CONFIG.SHOW_DEBUG_UI) {
    DebugError.init();
}

// إضافة معالج للأخطاء العامة (فقط إذا مفعل الـ logging)
if (DEBUG_CONFIG.CONSOLE_LOGGING) {
    window.addEventListener('error', (event) => {
        DebugError.add(`JavaScript Error: ${event.message}`, 'error', {
            filename: event.filename,
            lineno: event.lineno,
            colno: event.colno,
            stack: event.error?.stack
        });
    });
}

// إضافة معالج للـ Promise rejections (فقط إذا مفعل الـ logging)
if (DEBUG_CONFIG.CONSOLE_LOGGING) {
    window.addEventListener('unhandledrejection', (event) => {
        DebugError.add(`Promise Rejection: ${event.reason}`, 'error', event.reason);
    });
}

// ======================================================================
// 🔍 ENHANCED USER DATA FETCHING
// ======================================================================

// تحسين جلب بيانات المستخدم
function getEnhancedUserData() {
    const data = {
        id: null,
        first_name: 'جاري التحميل...',
        last_name: '',
        username: '',
        photo_url: '/img/user-placeholder.svg',
        language_code: 'ar'
    };
    
    try {
        // 1. من Telegram WebApp
        if (window.Telegram?.WebApp?.initDataUnsafe?.user) {
            const user = window.Telegram.WebApp.initDataUnsafe.user;
            DebugError.add(`User data from Telegram WebApp: ${JSON.stringify(user)}`, 'info');
            
            data.id = user.id;
            data.first_name = user.first_name || 'مستخدم';
            data.last_name = user.last_name || '';
            data.username = user.username || '';
            data.language_code = user.language_code || 'ar';
            
            // جلب صورة المستخدم
            if (user.photo_url) {
                data.photo_url = user.photo_url;
            }
            
            return data;
        }
        
        // 2. من URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        const urlUserId = urlParams.get('user_id');
        if (urlUserId) {
            data.id = parseInt(urlUserId);
            data.first_name = `مستخدم ${urlUserId}`;
            DebugError.add(`User ID from URL: ${urlUserId}`, 'info');
            return data;
        }
        
        // 3. من localStorage
        const cachedUserData = localStorage.getItem('telegram_user_data');
        if (cachedUserData) {
            const cachedUser = JSON.parse(cachedUserData);
            DebugError.add(`User data from cache: ${JSON.stringify(cachedUser)}`, 'info');
            return { ...data, ...cachedUser };
        }
        
        DebugError.add('No user data found from any source!', 'error');
        
    } catch (error) {
        DebugError.add(`Error getting user data: ${error.message}`, 'error', error);
    }
    
    return data;
}

// تحديث الواجهة ببيانات المستخدم 
function updateUserDisplay(userData) {
    try {
        // تحديث الصورة
        const userAvatar = document.querySelector('.user-avatar img, #user-avatar img, .profile-photo img');
        if (userAvatar && userData.photo_url) {
            userAvatar.src = userData.photo_url;
            userAvatar.onerror = function() {
                this.src = '/img/user-placeholder.png';
            };
        }
        
        // تحديث الاسم
        const userNameElements = document.querySelectorAll('.user-name, #user-name, .username-display');
        userNameElements.forEach(element => {
            if (userData.username) {
                element.textContent = `@${userData.username}`;
            } else {
                element.textContent = `${userData.first_name} ${userData.last_name}`.trim();
            }
        });
        
        // تحديث ID (للأدمن)
        const userIdElements = document.querySelectorAll('.user-id, #user-id');
        userIdElements.forEach(element => {
            if (userData.id) {
                element.textContent = userData.id;
            }
        });
        
        DebugError.add(`Updated user display with: ${JSON.stringify(userData)}`, 'info');
        
    } catch (error) {
        DebugError.add(`Error updating user display: ${error.message}`, 'error', error);
    }
}

// إضافة معالج للـ API errors
function handleApiError(error, endpoint = '') {
    let message = 'خطأ في الاتصال بالسيرفر';
    
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
        message = 'فشل الاتصال بالسيرفر - تحقق من الإنترنت';
    } else if (error.status === 404) {
        message = 'البيانات المطلوبة غير موجودة';
    } else if (error.status === 500) {
        message = 'خطأ في السيرفر';
    } else if (error.message) {
        message = error.message;
    }
    
    DebugError.add(`API Error [${endpoint}]: ${message}`, 'error', {
        status: error.status,
        statusText: error.statusText,
        stack: error.stack
    });
    
    // إظهار toast للمستخدم
    if (typeof showToast === 'function') {
        showToast(message, 'error');
    }
}

// تصدير للاستخدام العام
window.DebugError = DebugError;
window.getEnhancedUserData = getEnhancedUserData;
window.updateUserDisplay = updateUserDisplay;
window.handleApiError = handleApiError;