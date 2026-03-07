const DEBUG_CONFIG = {
    SHOW_DEBUG_UI: false,
    SHOW_SERVER_STATUS: false,
    CONSOLE_LOGGING: false,
    AUTO_SHOW_ERRORS: false
};

class DebugError {
    static errors = [];

    static init() {}

    static add(message, type = 'error', data = null) {
        const timestamp = new Date().toLocaleTimeString('ar-EG');
        this.errors.unshift({ timestamp, message, type, data: data ? JSON.stringify(data, null, 2) : null });
        if (this.errors.length > 50) this.errors.pop();
    }

    static show() {}
    static hide() {}
    static toggle() {}
    static clear() { this.errors = []; }
    static render() {}
}

window.DebugError = DebugError;

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
        if (window.Telegram?.WebApp?.initDataUnsafe?.user) {
            const user = window.Telegram.WebApp.initDataUnsafe.user;
            data.id = user.id;
            data.first_name = user.first_name || 'مستخدم';
            data.last_name = user.last_name || '';
            data.username = user.username || '';
            data.language_code = user.language_code || 'ar';
            if (user.photo_url) data.photo_url = user.photo_url;
            return data;
        }

        const urlParams = new URLSearchParams(window.location.search);
        const urlUserId = urlParams.get('user_id');
        if (urlUserId) {
            data.id = parseInt(urlUserId);
            data.first_name = `مستخدم ${urlUserId}`;
            return data;
        }

        const cachedUserData = localStorage.getItem('telegram_user_data');
        if (cachedUserData) {
            return { ...data, ...JSON.parse(cachedUserData) };
        }
    } catch (error) {
        DebugError.add(`Error getting user data: ${error.message}`, 'error', error);
    }

    return data;
}

function updateUserDisplay(userData) {
    try {
        const userAvatar = document.querySelector('.user-avatar img, #user-avatar img, .profile-photo img');
        if (userAvatar && userData.photo_url) {
            userAvatar.src = userData.photo_url;
            userAvatar.onerror = function() { this.src = '/img/user-placeholder.png'; };
        }

        const userNameElements = document.querySelectorAll('.user-name, #user-name, .username-display');
        userNameElements.forEach(element => {
            if (userData.username) {
                element.textContent = `@${userData.username}`;
            } else {
                element.textContent = `${userData.first_name} ${userData.last_name}`.trim();
            }
        });

        const userIdElements = document.querySelectorAll('.user-id, #user-id');
        userIdElements.forEach(element => {
            if (userData.id) element.textContent = userData.id;
        });
    } catch (error) {
        DebugError.add(`Error updating user display: ${error.message}`, 'error', error);
    }
}

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

    if (typeof showToast === 'function') {
        showToast(message, 'error');
    }
}

window.getEnhancedUserData = getEnhancedUserData;
window.updateUserDisplay = updateUserDisplay;
window.handleApiError = handleApiError;

class ChannelsLogger {
    static logs = [];
    static log(message, data = null) {}
    static getSummary() { return { totalLogs: 0, logs: [] }; }
    static copyToClipboard() {}
    static clear() { this.logs = []; }
}

window.ChannelsLogger = ChannelsLogger;
