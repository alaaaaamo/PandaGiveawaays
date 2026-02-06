// ═══════════════════════════════════════════════════════════════
// 🌐 API CLIENT - التواصل مع السيرفر
// ═══════════════════════════════════════════════════════════════

const API = {
    baseUrl: CONFIG.API_BASE_URL,
    isServerWake: false,
    
    // ═══════════════════════════════════════════════════════════
    // 🌐 SERVER WAKE UP & HEALTH CHECK
    // ═══════════════════════════════════════════════════════════
    
    async wakeUpServer() {
        if (this.isServerWake) return true;
        
        try {
            DebugError.add('Attempting to wake up server...', 'info');
            updateServerStatus('connecting', 'يقظة السيرفر...');
            showLoadingWithMessage('🌐 جاري تشغيل السيرفر...');
            
            // محاولة ping بسيط
            const pingUrl = `${this.baseUrl}/ping`;
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 ثانية
            
            const response = await fetch(pingUrl, {
                method: 'GET',
                signal: controller.signal,
                mode: 'cors'
            });
            
            clearTimeout(timeoutId);
            
            if (response.ok) {
                this.isServerWake = true;
                DebugError.add('Server is awake and responding', 'info');
                updateServerStatus('online', 'السيرفر متصل');
                return true;
            } else {
                DebugError.add(`Server ping failed: ${response.status}`, 'warn');
                updateServerStatus('error', 'السيرفر غير مستجيب');
                return false;
            }
            
        } catch (error) {
            if (error.name === 'AbortError') {
                DebugError.add('Server wake up timeout - server may be sleeping', 'warn');
                updateServerStatus('offline', 'السيرفر نائم');
            } else {
                DebugError.add(`Server wake up error: ${error.message}`, 'error', error);
                updateServerStatus('error', 'خطأ في الاتصال');
            }
            return false;
        }
    },
    
    // ═══════════════════════════════════════════════════════════
    // 🔧 ENHANCED REQUEST WITH RETRY
    // ═══════════════════════════════════════════════════════════
    
    async request(endpoint, method = 'GET', data = null, retries = 2) {
        const url = `${this.baseUrl}${endpoint}`;
        DebugError.add(`API Request: ${method} ${url}`, 'info');
        
        // محاولة إيقاظ السيرفر أولاً إذا كان نائم
        if (!this.isServerWake && endpoint !== '/ping') {
            await this.wakeUpServer();
        }
        
        const headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Session-ID': UserState?.sessionId || 'no-session',
            'X-User-ID': TelegramApp.getUserId()?.toString() || ''
        };
        
        const options = {
            method,
            headers,
            mode: 'cors'
        };
        
        if (data && method !== 'GET') {
            options.body = JSON.stringify(data);
            DebugError.add(`API Request body:`, 'info', data);
        }
        
        for (let attempt = 0; attempt <= retries; attempt++) {
            try {
                if (attempt > 0) {
                    DebugError.add(`Retry attempt ${attempt}/${retries} for ${endpoint}`, 'info');
                    showLoadingWithMessage(`🔄 محاولة ${attempt}/${retries}...`);
                    // انتظار قصير بين المحاولات
                    await new Promise(resolve => setTimeout(resolve, 2000 * attempt));
                }
                
                DebugError.add(`Sending request to: ${url}`, 'info');
                
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 ثانية
                
                const response = await fetch(url, {
                    ...options,
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
                DebugError.add(`API Response Status: ${response.status}`, 'info');
                
                if (!response.ok) {
                    const errorText = await response.text();
                    DebugError.add(`API Error Response: ${errorText}`, 'error');
                    
                    // إذا كان server error (5xx)، نحاول مرة أخرى
                    if (response.status >= 500 && attempt < retries) {
                        DebugError.add(`Server error ${response.status}, retrying...`, 'warn');
                        continue;
                    }
                    
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const result = await response.json();
                DebugError.add(`API Success:`, 'info', result);
                
                // تأكيد أن السيرفر شغال
                this.isServerWake = true;
                
                return result;
                
            } catch (error) {
                DebugError.add(`API Attempt ${attempt + 1} failed: ${error.message}`, 'error', {
                    url,
                    method,
                    attempt: attempt + 1,
                    error: error.message
                });
                
                // إذا كانت آخر محاولة، ارمي الخطأ
                if (attempt >= retries) {
                    // إضافة معلومات مفيدة للخطأ
                    if (error.name === 'AbortError') {
                        throw new Error('انتهت مهلة الاستجابة - السيرفر قد يكون بطيء');
                    } else if (error.message.includes('fetch')) {
                        throw new Error('فشل الاتصال بالسيرفر - تحقق من الإنترنت أو حالة السيرفر');
                    } else {
                        throw error;
                    }
                }
            }
        }
    },
    
    // ═══════════════════════════════════════════════════════════
    // 👤 USER ENDPOINTS
    // ═══════════════════════════════════════════════════════════
    
    async getUserData(userId) {
        return await this.request(`/user/${userId}`, 'GET');
    },
    
    async updateUser(userId, updates) {
        return await this.request(`/user/${userId}`, 'PUT', updates);
    },
    
    // ═══════════════════════════════════════════════════════════
    // 🎰 SPIN ENDPOINTS
    // ═══════════════════════════════════════════════════════════
    
    async spinWheel(userId) {
        DebugError.add(`🎲 Real API spinWheel called for user ${userId}`, 'info');
        return await this.request(`/spin`, 'POST', { 
            user_id: userId,
            session_id: UserState.sessionId,
            timestamp: Date.now()
        });
    },
    
    async getSpinHistory(userId, limit = 50) {
        return await this.request(`/user/${userId}/spins?limit=${limit}`, 'GET');
    },
    
    // ═══════════════════════════════════════════════════════════
    // 👥 REFERRAL ENDPOINTS
    // ═══════════════════════════════════════════════════════════
    
    async getReferrals(userId) {
        return await this.request(`/user/${userId}/referrals`, 'GET');
    },
    
    async validateReferral(userId) {
        return await this.request(`/referral/validate`, 'POST', { user_id: userId });
    },
    
    // ═══════════════════════════════════════════════════════════
    // 📝 TASK ENDPOINTS
    // ═══════════════════════════════════════════════════════════
    
    async getTasks() {
        return await this.request(`/tasks`, 'GET');
    },
    
    async completeTask(userId, taskId) {
        return await this.request(`/task/complete`, 'POST', { 
            user_id: userId, 
            task_id: taskId 
        });
    },
    
    async getCompletedTasks(userId) {
        return await this.request(`/user/${userId}/tasks`, 'GET');
    },
    
    // ═══════════════════════════════════════════════════════════
    // 💸 WITHDRAWAL ENDPOINTS
    // ═══════════════════════════════════════════════════════════
    
    async requestWithdrawal(userId, data) {
        return await this.request(`/withdrawal/request`, 'POST', {
            user_id: userId,
            ...data
        });
    },
    
    async getWithdrawals(userId) {
        return await this.request(`/user/${userId}/withdrawals`, 'GET');
    },
    
    // ═══════════════════════════════════════════════════════════
    // 📢 CHANNEL ENDPOINTS
    // ═══════════════════════════════════════════════════════════
    
    async getMandatoryChannels() {
        return await this.request(`/channels`, 'GET');
    },
    
    async checkChannelMembership(userId) {
        return await this.request(`/check-membership`, 'POST', { user_id: userId });
    }
};

// ═══════════════════════════════════════════════════════════════
// 📊 MOCK DATA (للتطوير فقط - يتم حذفه في الإنتاج)
// ═══════════════════════════════════════════════════════════════

const MockAPI = {
    userData: {
        user_id: 123456789,
        username: 'testuser',
        full_name: 'Test User',
        balance: 2.5432,
        total_spins: 150,
        available_spins: 3,
        total_referrals: 12,
        valid_referrals: 10,
        created_at: '2024-01-15T10:00:00',
        last_active: new Date().toISOString()
    },
    
    spinHistory: [
        { prize_name: '0.1 TON', prize_amount: 0.1, spin_time: new Date(Date.now() - 3600000).toISOString() },
        { prize_name: '0.05 TON', prize_amount: 0.05, spin_time: new Date(Date.now() - 7200000).toISOString() },
        { prize_name: 'حظ أوفر', prize_amount: 0, spin_time: new Date(Date.now() - 10800000).toISOString() },
        { prize_name: '0.2 TON', prize_amount: 0.2, spin_time: new Date(Date.now() - 14400000).toISOString() },
        { prize_name: '0.05 TON', prize_amount: 0.05, spin_time: new Date(Date.now() - 18000000).toISOString() }
    ],
    
    referrals: [
        { username: 'user1', full_name: 'Ahmed Mohamed', created_at: new Date(Date.now() - 86400000).toISOString(), is_valid: 1 },
        { username: 'user2', full_name: 'Sara Ali', created_at: new Date(Date.now() - 172800000).toISOString(), is_valid: 1 },
        { username: 'user3', full_name: 'Omar Hassan', created_at: new Date(Date.now() - 259200000).toISOString(), is_valid: 0 }
    ],
    
    tasks: [
        { id: 1, task_type: 'join_channel', task_name: 'انضم لقناة Panda', task_description: 'انضم لقناتنا على تيليجرام', channel_id: '@pandachannel', is_active: 1 },
        { id: 2, task_type: 'join_channel', task_name: 'انضم لقناة العروض', task_description: 'لا تفوت أحدث العروض', channel_id: '@offerschannel', is_active: 1 },
        { id: 3, task_type: 'share_bot', task_name: 'شارك البوت', task_description: 'شارك البوت مع 5 أصدقاء', is_active: 1 }
    ],
    
    completedTasks: [1],
    
    withdrawals: [
        { id: 1, amount: 1.5, withdrawal_type: 'ton', status: 'completed', requested_at: new Date(Date.now() - 86400000).toISOString(), tx_hash: 'abc123...' },
        { id: 2, amount: 1.0, withdrawal_type: 'vodafone', status: 'pending', requested_at: new Date(Date.now() - 3600000).toISOString() }
    ],
    
    async simulateDelay(min = 300, max = 800) {
        const delay = Math.random() * (max - min) + min;
        return new Promise(resolve => setTimeout(resolve, delay));
    },
    
    async getUserData(userId) {
        await this.simulateDelay();
        return { success: true, data: this.userData };
    },
    
    async spinWheel(userId) {
        DebugError.add(`⚠️ WARNING: Still using MockAPI spinWheel for user ${userId}`, 'warn');
        DebugError.add('Mock prizes being used:', 'warn', CONFIG.WHEEL_PRIZES);
        
        await this.simulateDelay(1000, 2000);
        
        // محاكاة نظام الاحتمالات
        const rand = Math.random() * 100;
        let cumulative = 0;
        let selectedPrize = CONFIG.WHEEL_PRIZES[CONFIG.WHEEL_PRIZES.length - 1];
        
        for (const prize of CONFIG.WHEEL_PRIZES) {
            cumulative += prize.probability;
            if (rand <= cumulative) {
                selectedPrize = prize;
                break;
            }
        }
        
        DebugError.add('Mock selected prize:', 'warn', selectedPrize);
        
        // تحديث البيانات المحلية
        this.userData.available_spins--;
        this.userData.total_spins++;
        this.userData.balance += selectedPrize.amount;
        
        return {
            success: true,
            data: {
                prize: selectedPrize,
                new_balance: this.userData.balance,
                new_spins: this.userData.available_spins
            }
        };
    },
    
    async getSpinHistory(userId, limit) {
        await this.simulateDelay();
        return { success: true, data: this.spinHistory.slice(0, limit) };
    },
    
    async getReferrals(userId) {
        await this.simulateDelay();
        return { success: true, data: this.referrals };
    },
    
    async getTasks() {
        await this.simulateDelay();
        return { success: true, data: this.tasks };
    },
    
    async completeTask(userId, taskId) {
        await this.simulateDelay();
        if (!this.completedTasks.includes(taskId)) {
            this.completedTasks.push(taskId);
        }
        return { success: true, data: { task_id: taskId, completed: true } };
    },
    
    async getCompletedTasks(userId) {
        await this.simulateDelay();
        return { success: true, data: this.completedTasks };
    },
    
    async requestWithdrawal(userId, data) {
        await this.simulateDelay(500, 1000);
        
        if (this.userData.balance < data.amount) {
            return { success: false, error: 'رصيد غير كافٍ' };
        }
        
        if (data.amount < CONFIG.MIN_WITHDRAWAL_AMOUNT) {
            return { success: false, error: `الحد الأدنى للسحب ${CONFIG.MIN_WITHDRAWAL_AMOUNT} TON` };
        }
        
        // خصم الرصيد
        this.userData.balance -= data.amount;
        
        const withdrawal = {
            id: this.withdrawals.length + 1,
            amount: data.amount,
            withdrawal_type: data.withdrawal_type,
            wallet_address: data.wallet_address,
            phone_number: data.phone_number,
            status: 'pending',
            requested_at: new Date().toISOString()
        };
        
        this.withdrawals.unshift(withdrawal);
        
        return { success: true, data: withdrawal };
    },
    
    async getWithdrawals(userId) {
        await this.simulateDelay();
        return { success: true, data: this.withdrawals };
    }
};

// ═══════════════════════════════════════════════════════════════
// 🔀 CONDITIONAL EXPORT (استخدام API الحقيقي في الإنتاج)
// ═══════════════════════════════════════════════════════════════

const USE_MOCK = false;  // ❌ تم تعطيل Mock API لاستخدام البيانات الحقيقية

window.API = USE_MOCK ? MockAPI : API;

console.log('🌐 API Client Loaded', USE_MOCK ? '(Mock Mode)' : '(Production Mode)');
DebugError.add(`🌐 API initialized in ${USE_MOCK ? 'MOCK' : 'PRODUCTION'} mode`, 'info');
