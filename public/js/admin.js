/**
 * 🔧 PANDA GIVEAWAYS - ADMIN PANEL SCRIPT
 * Admin Dashboard Management
 */

console.log('📄 admin.js loaded successfully');

// Test: إضافة click listener للـ body للتأكد من الأحداث بتشتغل
document.addEventListener('click', (e) => {
    console.log('🖱️ Global click detected:', e.target.tagName, e.target.className);
}, true);

// ═══════════════════════════════════════════════════════════════
// 🔧 INITIALIZATION
// ═══════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    console.log('🎯 DOM Content Loaded - Starting Admin Panel');
    console.log('Checking required globals:', {
        CONFIG: !!window.CONFIG,
        Telegram: !!window.Telegram,
        showToast: typeof showToast !== 'undefined'
    });
    
    try {
        initAdminPanel();
        loadDashboardData();
        setupEventListeners();
        console.log('✅ Admin Panel initialization complete');
    } catch (error) {
        console.error('❌ Failed to initialize admin panel:', error);
    }
});

// ═══════════════════════════════════════════════════════════════
// 📊 DATA MANAGEMENT
// ═══════════════════════════════════════════════════════════════

let adminData = {
    prizes: [],
    users: [],
    withdrawals: [],
    tasks: [],
    channels: [],
    settings: {}
};

async function initAdminPanel() {
    console.log('🔧 Initializing Admin Panel...');
    console.log('CONFIG:', window.CONFIG);
    console.log('Telegram WebApp:', window.Telegram?.WebApp);
    
    // Initialize Telegram WebApp if available
    if (window.Telegram?.WebApp) {
        window.Telegram.WebApp.ready();
        window.Telegram.WebApp.expand();
    }
    
    // Check if user is admin
    const telegramUser = window.Telegram?.WebApp?.initDataUnsafe?.user;
    console.log('Telegram User:', telegramUser);
    
    // إذا مفيش user من Telegram - ارفض الدخول تماماً
    if (!telegramUser) {
        document.body.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; min-height: 100vh; background: #0d1117; color: #fff; text-align: center; padding: 20px; font-family: Arial;">
                <div>
                    <h1 style="font-size: 48px; margin-bottom: 20px;">🚫</h1>
                    <h2 style="color: #ff4444; margin-bottom: 10px;">غير مسموح بالدخول!</h2>
                    <p style="color: #888; font-size: 18px;">هذه الصفحة تعمل فقط من خلال Telegram Mini App</p>
                    <p style="color: #666; font-size: 14px; margin-top: 20px;">Access Denied: This page only works through Telegram Bot</p>
                </div>
            </div>
        `;
        throw new Error('Not authorized - Not from Telegram');
    }
    
    // التحقق من أن المستخدم أدمن
    const adminIds = window.CONFIG?.ADMIN_IDS || [1797127532, 6603009212];
    if (!adminIds.includes(telegramUser.id)) {
        document.body.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; min-height: 100vh; background: #0d1117; color: #fff; text-align: center; padding: 20px; font-family: Arial;">
                <div>
                    <h1 style="font-size: 48px; margin-bottom: 20px;">⛔</h1>
                    <h2 style="color: #ff4444; margin-bottom: 10px;">غير مصرح لك!</h2>
                    <p style="color: #888; font-size: 18px;">هذه الصفحة للمسؤولين فقط</p>
                    <p style="color: #666; font-size: 14px; margin-top: 20px;">Your ID: ${telegramUser.id}</p>
                    <p style="color: #666; font-size: 14px;">Access Denied: Admin only</p>
                </div>
            </div>
        `;
        throw new Error('Not authorized - Not admin');
    }

    console.log('✅ Admin authorized:', telegramUser.id);
    showToast('✅ مرحباً في لوحة التحكم!', 'success');
}

async function loadDashboardData() {
    showLoading();
    
    // Safety timeout to hide loading after 10 seconds max
    const loadingTimeout = setTimeout(() => {
        console.warn('⏱️ Loading timeout - force hiding loading overlay');
        hideLoading();
    }, 10000);
    
    try {
        // Load all data
        await Promise.all([
            loadStatistics(),
            loadAdvancedStats(),  // 📊 الإحصائيات المتقدمة الجديدة
            loadPrizes(),
            loadUsers(),
            loadWithdrawals(),
            loadTasks(),
            loadChannels(),
            loadSettings()
        ]);
        
        clearTimeout(loadingTimeout);
        hideLoading();
        showToast('✅ تم تحميل البيانات بنجاح', 'success');
    } catch (error) {
        clearTimeout(loadingTimeout);
        hideLoading();
        showToast('❌ خطأ في تحميل البيانات', 'error');
        console.error(error);
    }
}

async function loadStatistics() {
    try {
        const API_BASE_URL = window.CONFIG?.API_BASE_URL || '/api';
        const response = await fetch(`${API_BASE_URL}/stats`);
        const result = await response.json();
        
        if (result.success && result.data) {
            const stats = result.data;
            document.getElementById('total-users').textContent = formatNumber(stats.total_users || 0);
            document.getElementById('total-spins').textContent = formatNumber(stats.total_spins || 0);
            document.getElementById('total-balance').textContent = (stats.total_distributed || 0).toFixed(2);
            document.getElementById('pending-withdrawals').textContent = formatNumber(stats.pending_withdrawals || 0);
        } else {
            console.error('Failed to load statistics:', result.error);
            // Set default values on error
            document.getElementById('total-users').textContent = '0';
            document.getElementById('total-spins').textContent = '0';
            document.getElementById('total-balance').textContent = '0.00';
            document.getElementById('pending-withdrawals').textContent = '0';
        }
    } catch (error) {
        console.error('Error loading statistics:', error);
        // Set default values on error
        document.getElementById('total-users').textContent = '0';
        document.getElementById('total-spins').textContent = '0';
        document.getElementById('total-balance').textContent = '0.00';
        document.getElementById('pending-withdrawals').textContent = '0';
    }
}

function formatNumber(num) {
    return new Intl.NumberFormat('ar-EG').format(num);
}

// ═══════════════════════════════════════════════════════════════
// 📊 ADVANCED STATISTICS
// ═══════════════════════════════════════════════════════════════

async function loadAdvancedStats() {
    try {
        const response = await fetch('/api/admin/advanced-stats');
        const result = await response.json();
        
        if (result.success && result.data) {
            const stats = result.data;
            document.getElementById('stat-total-users').textContent = formatNumber(stats.total_users || 0);
            document.getElementById('stat-active-users').textContent = formatNumber(stats.active_users || 0);
            document.getElementById('stat-banned-users').textContent = formatNumber(stats.banned_users || 0);
            document.getElementById('stat-verified-users').textContent = formatNumber(stats.verified_users || 0);
        } else {
            console.error('Failed to load advanced stats:', result.error);
        }
    } catch (error) {
        console.error('Error loading advanced stats:', error);
    }
}

// ═══════════════════════════════════════════════════════════════
// 🎁 PRIZES MANAGEMENT
// ═══════════════════════════════════════════════════════════════

async function loadPrizes() {
    try {
        console.log('🎁 Loading prizes from API...');
        const response = await fetch('/api/admin/prizes');
        const result = await response.json();
        
        if (result.success && result.data) {
            adminData.prizes = result.data;
            console.log(`✅ Loaded ${adminData.prizes.length} prizes`);
        } else {
            console.error('❌ Failed to load prizes:', result.error);
            showToast('فشل تحميل الجوائز', 'error');
        }
    } catch (error) {
        console.error('❌ Error loading prizes:', error);
        showToast('خطأ في تحميل الجوائز', 'error');
    }
    
    renderPrizesList();
    updatePrizesInfo();
}

function renderPrizesList() {
    const container = document.getElementById('prizes-list');
    if (!container) return;
    
    // 🎨 الألوان الزيتية بالترتيب (نفس العجلة)
    const oilColors = [
        '#9370db',  // Purple (0.01)
        '#00bfff',  // Blue (0.05)
        '#ffa500',  // Orange (0.1)
        '#32cd32',  // Green (0.5)
        '#ff1493',  // Pink (1.0)
        '#808080'   // Gray (حظ أوفر)
    ];
    
    container.innerHTML = adminData.prizes.map((prize, index) => {
        const color = oilColors[index % oilColors.length];
        return `
        <div class="prize-item-compact" data-id="${prize.id}">
            <div class="prize-color-bar" style="background: ${color};"></div>
            <div class="prize-info-compact">
                <div class="prize-name">${prize.name}</div>
                <div class="prize-stats">
                    <span class="stat-item">💰 ${prize.value} TON</span>
                    <span class="stat-item">📊 ${prize.probability}%</span>
                </div>
            </div>
            <div class="prize-actions-compact">
                <button class="icon-btn-small edit" onclick="openEditPrizeModal(${prize.id})" title="تعديل">✏️</button>
                <button class="icon-btn-small delete" onclick="deletePrize(${prize.id})" title="حذف">🗑️</button>
            </div>
        </div>
    `}).join('');
}

function updatePrizesInfo() {
    const totalPrizes = adminData.prizes.length;
    const totalProbability = adminData.prizes.reduce((sum, p) => sum + p.probability, 0);
    const isValid = totalProbability === 100;
    
    document.getElementById('total-prizes-count').textContent = totalPrizes;
    document.getElementById('total-probability').textContent = `${totalProbability}%`;
    
    const statusEl = document.getElementById('system-status');
    if (isValid) {
        statusEl.innerHTML = '<img src="/img/payment-success.svg" alt="✓" style="width: 14px; height: 14px; vertical-align: middle; margin-left: 2px;"> صحيح';
        statusEl.className = 'status-ok';
    } else {
        statusEl.textContent = `✗ خطأ (${totalProbability}%)`;
        statusEl.className = 'status-error';
    }
}

function openAddPrizeModal() {
    const modal = document.getElementById('add-prize-modal');
    modal.classList.add('active');
}

function openEditPrizeModal(prizeId) {
    const prize = adminData.prizes.find(p => p.id === prizeId);
    if (!prize) return;
    
    document.getElementById('edit-prize-id').value = prize.id;
    document.getElementById('edit-prize-name').value = prize.name;
    document.getElementById('edit-prize-value').value = prize.value;
    document.getElementById('edit-prize-probability').value = prize.probability;
    
    const modal = document.getElementById('edit-prize-modal');
    modal.classList.add('active');
}

async function addPrize() {
    const name = document.getElementById('prize-name').value;
    const value = parseFloat(document.getElementById('prize-value').value);
    const probability = parseFloat(document.getElementById('prize-probability').value);
    
    if (!name || isNaN(value) || isNaN(probability)) {
        showToast('❌ يرجى ملء جميع الحقول', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/admin/prizes', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                name,
                value,
                probability,
                position: adminData.prizes.length
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            await loadPrizes();
            closeModal('add-prize-modal');
            showToast('✅ تم إضافة الجائزة بنجاح', 'success');
            
            // Clear form
            document.getElementById('prize-name').value = '';
            document.getElementById('prize-value').value = '';
            document.getElementById('prize-probability').value = '';
        } else {
            showToast('❌ فشل إضافة الجائزة: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Error adding prize:', error);
        showToast('❌ خطأ في إضافة الجائزة', 'error');
    }
}

async function updatePrize() {
    const id = parseInt(document.getElementById('edit-prize-id').value);
    const prize = adminData.prizes.find(p => p.id === id);
    
    if (!prize) return;
    
    const name = document.getElementById('edit-prize-name').value;
    const value = parseFloat(document.getElementById('edit-prize-value').value);
    const probability = parseFloat(document.getElementById('edit-prize-probability').value);
    
    const updatedData = {
        id,
        name,
        value,
        probability,
        position: prize.position
    };
    
    try {
        const response = await fetch('/api/admin/prizes', {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(updatedData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            await loadPrizes();
            closeModal('edit-prize-modal');
            showToast('✅ تم تحديث الجائزة بنجاح', 'success');
        } else {
            showToast('❌ فشل تحديث الجائزة: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Error updating prize:', error);
        showToast('❌ خطأ في تحديث الجائزة', 'error');
    }
}

async function deletePrize(prizeId) {
    if (!confirm('هل أنت متأكد من حذف هذه الجائزة؟')) return;
    
    try {
        const response = await fetch(`/api/admin/prizes?id=${prizeId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            await loadPrizes();
            showToast('✅ تم حذف الجائزة بنجاح', 'success');
        } else {
            showToast('❌ فشل حذف الجائزة: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Error deleting prize:', error);
        showToast('❌ خطأ في حذف الجائزة', 'error');
    }
}

// ═══════════════════════════════════════════════════════════════
// 👥 USERS MANAGEMENT
// ═══════════════════════════════════════════════════════════════

async function loadUsers() {
    // تحميل المستخدمين من API
    try {
        showLoading();
        const API_BASE_URL = window.CONFIG?.API_BASE_URL || '/api';
        const response = await fetch(`${API_BASE_URL}/admin/users`);
        const result = await response.json();
        
        hideLoading();
        
        if (result.success) {
            adminData.users = result.data || [];
            console.log(`✅ Loaded ${adminData.users.length} users`);
        } else {
            console.error('❌ Failed to load users:', result.error);
            adminData.users = [];
            showToast('فشل تحميل المستخدمين', 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('Error loading users:', error);
        adminData.users = [];
        showToast('خطأ في تحميل المستخدمين', 'error');
    }
    
    renderUsersTable();
}

function renderUsersTable() {
    const tbody = document.getElementById('users-table-body');
    if (!tbody) return;
    
    tbody.innerHTML = adminData.users.map(user => {
        const isBanned = user.is_banned === 1;
        const banBadge = isBanned ? `<span style="background: #ff4d4d; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; margin-right: 8px;">محظور</span>` : '';
        const banReasonText = isBanned && user.ban_reason ? `<br><small style="color: #ff6b6b;">${user.ban_reason}</small>` : '';
        
        const actionButtons = isBanned 
            ? `<button class="icon-btn" style="background: #3fb950;" onclick="unbanUser(${user.id}, '${user.username}')">✅ السماح</button>`
            : `<button class="icon-btn" onclick="viewUserReferrals(${user.id}, '${user.name}')">👁️ إحالات</button>
               <button class="icon-btn" style="background: #3fb950;" onclick="quickAddSpins(${user.id}, '${user.username}')">🎰 لفات</button>`;
        
        return `
        <tr style="${isBanned ? 'background: rgba(255, 77, 77, 0.1);' : ''}">
            <td>${user.id}</td>
            <td>${banBadge}${user.name}${banReasonText}</td>
            <td>${user.username}</td>
            <td>${user.balance.toFixed(4)} TON</td>
            <td>${user.spins}</td>
            <td>${user.referrals}</td>
            <td>${user.joined}</td>
            <td>${actionButtons}</td>
        </tr>
        `;
    }).join('');
}

// إلغاء حظر مستخدم
async function unbanUser(userId, username) {
    if (!confirm(`هل تريد السماح للمستخدم ${username} بالدخول بدون تحقق؟`)) {
        return;
    }
    
    try {
        showLoading();
        const API_BASE_URL = window.CONFIG?.API_BASE_URL || '/api';
        const response = await fetch(`${API_BASE_URL}/admin/unban-user`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId })
        });
        
        const result = await response.json();
        hideLoading();
        
        if (result.success) {
            showToast('تم السماح للمستخدم بنجاح ✅', 'success');
            await loadUsers(); // إعادة تحميل قائمة المستخدمين
            await loadAdvancedStats(); // تحديث الإحصائيات
        } else {
            showToast(result.error || 'فشل إلغاء الحظر', 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('Error unbanning user:', error);
        showToast('خطأ في إلغاء الحظر', 'error');
    }
}

// تصفية جدول المستخدمين حسب البحث
function filterUsersTable(query) {
    const tbody = document.getElementById('users-table-body');
    if (!tbody) return;
    
    const filteredUsers = adminData.users.filter(user => {
        const searchText = `${user.id} ${user.name} ${user.username}`.toLowerCase();
        return searchText.includes(query);
    });
    
    if (filteredUsers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 40px; color: #8b95a1;">لا توجد نتائج</td></tr>';
        return;
    }
    
    tbody.innerHTML = filteredUsers.map(user => {
        const isBanned = user.is_banned === 1;
        const banBadge = isBanned ? `<span style="background: #ff4d4d; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; margin-right: 8px;">محظور</span>` : '';
        const banReasonText = isBanned && user.ban_reason ? `<br><small style="color: #ff6b6b;">${user.ban_reason}</small>` : '';
        
        const actionButtons = isBanned 
            ? `<button class="icon-btn" style="background: #3fb950;" onclick="unbanUser(${user.id}, '${user.username}')">✅ السماح</button>`
            : `<button class="icon-btn" onclick="viewUserReferrals(${user.id}, '${user.name}')">👁️ إحالات</button>
               <button class="icon-btn" style="background: #3fb950;" onclick="quickAddSpins(${user.id}, '${user.username}')">🎰 لفات</button>`;
        
        return `
        <tr style="${isBanned ? 'background: rgba(255, 77, 77, 0.1);' : ''}">
            <td>${user.id}</td>
            <td>${banBadge}${user.name}${banReasonText}</td>
            <td>${user.username}</td>
            <td>${user.balance.toFixed(4)} TON</td>
            <td>${user.spins}</td>
            <td>${user.referrals}</td>
            <td>${user.joined}</td>
            <td>${actionButtons}</td>
        </tr>
    `).join('');
}

// ═══════════════════════════════════════════════════════════════
// 💸 WITHDRAWALS MANAGEMENT
// ═══════════════════════════════════════════════════════════════

async function loadWithdrawals() {
    // تحميل طلبات السحب من API
    try {
        const API_BASE_URL = window.CONFIG?.API_BASE_URL || '/api';
        const response = await fetch(`${API_BASE_URL}/withdrawals`);
        const result = await response.json();
        
        if (result.success) {
            adminData.withdrawals = result.data || [];
        } else {
            adminData.withdrawals = [];
        }
    } catch (error) {
        console.error('Error loading withdrawals:', error);
        adminData.withdrawals = [];
    }
    
    renderWithdrawals('pending');
}

function renderWithdrawals(status = 'pending') {
    const container = document.getElementById('withdrawals-list');
    if (!container) return;
    
    let filtered = adminData.withdrawals;
    if (status !== 'all') {
        filtered = adminData.withdrawals.filter(w => w.status === status);
    }
    
    if (filtered.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: var(--text-secondary); padding: 40px;">لا توجد طلبات سحب</p>';
        return;
    }
    
    container.innerHTML = filtered.map(w => {
        const date = w.requested_at ? new Date(w.requested_at).toLocaleString('ar-EG') : 'غير محدد';
        const method = w.withdrawal_type || 'غير محدد';
        const address = w.wallet_address || 'غير محدد';
        const phone = w.phone_number || 'غير محدد';
        
        return `
        <div class="withdrawal-item">
            <div class="withdrawal-info">
                <h4>👤 ${w.user_name || 'Unknown'} (${w.user_id})</h4>
                <div class="withdrawal-details">
                    <span>💰 ${w.amount} TON</span>
                    <span>📱 ${method}</span>
                    <span>🕐 ${date}</span>
                    ${method.toUpperCase().includes('TON') ? `<span>📍 ${address}</span>` : `<span>📞 ${phone}</span>`}
                </div>
            </div>
            ${w.status === 'pending' ? `
                <div class="withdrawal-actions">
                    <button class="approve-btn" onclick="approveWithdrawal(${w.id})"><img src="/img/payment-success.svg" alt="✓" style="width: 14px; height: 14px; vertical-align: middle; margin-left: 2px;"> قبول</button>
                    <button class="reject-btn" onclick="rejectWithdrawal(${w.id})"><img src="/img/payment-failure.svg" alt="✗" style="width: 14px; height: 14px; vertical-align: middle; margin-left: 2px;"> رفض</button>
                </div>
            ` : `
                <span class="status-badge ${w.status}">${w.status === 'completed' ? '<img src="/img/payment-success.svg" alt="✓" style="width: 14px; height: 14px; vertical-align: middle; margin-left: 2px;"> مقبول' : '<img src="/img/payment-failure.svg" alt="✗" style="width: 14px; height: 14px; vertical-align: middle; margin-left: 2px;"> مرفوض'}</span>
            `}
        </div>
        `;
    }).join('');
}

async function approveWithdrawal(id) {
    const withdrawal = adminData.withdrawals.find(w => w.id === id);
    if (!withdrawal) return;
    
    if (!confirm(`هل أنت متأكد من قبول طلب السحب؟\n\nالمبلغ: ${withdrawal.amount} TON\nالمستخدم: ${withdrawal.user_name}`)) {
        return;
    }
    
    try {
        showLoading();
        const API_BASE_URL = window.CONFIG?.API_BASE_URL || '/api';
        const response = await fetch(`${API_BASE_URL}/withdrawal/approve`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                withdrawal_id: id,
                admin_id: window.Telegram?.WebApp?.initDataUnsafe?.user?.id || 1797127532
            })
        });
        
        const result = await response.json();
        hideLoading();
        
        if (result.success) {
            showToast('✅ تم قبول طلب السحب بنجاح', 'success');
            loadWithdrawals(); // إعادة تحميل القائمة
        } else {
            showToast('❌ فشل قبول الطلب: ' + result.error, 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('Error approving withdrawal:', error);
        showToast('❌ خطأ في قبول الطلب', 'error');
    }
}

async function rejectWithdrawal(id) {
    const withdrawal = adminData.withdrawals.find(w => w.id === id);
    if (!withdrawal) return;
    
    const reason = prompt('سبب الرفض (اختياري):');
    if (reason === null) return; // ألغى المستخدم
    
    try {
        showLoading();
        const API_BASE_URL = window.CONFIG?.API_BASE_URL || '/api';
        const response = await fetch(`${API_BASE_URL}/withdrawal/reject`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                withdrawal_id: id,
                admin_id: window.Telegram?.WebApp?.initDataUnsafe?.user?.id || 1797127532,
                reason: reason || 'لم يتم تحديد سبب'
            })
        });
        
        const result = await response.json();
        hideLoading();
        
        if (result.success) {
            showToast('✅ تم رفض طلب السحب وإرجاع المبلغ', 'success');
            loadWithdrawals(); // إعادة تحميل القائمة
        } else {
            showToast('❌ فشل رفض الطلب: ' + result.error, 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('Error rejecting withdrawal:', error);
        showToast('❌ خطأ في رفض الطلب', 'error');
    }
}

// ═══════════════════════════════════════════════════════════════
// 📝 TASKS MANAGEMENT
// ═══════════════════════════════════════════════════════════════

async function loadTasks() {
    console.log('📥 Loading tasks from API...');
    try {
        const API_BASE_URL = window.CONFIG?.API_BASE_URL || '/api';
        const response = await fetch(`${API_BASE_URL}/admin/tasks`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('✅ Tasks loaded:', data);
        
        if (data.success && data.tasks) {
            adminData.tasks = data.tasks;
            renderAdminTasks();
        } else {
            console.error('❌ Failed to load tasks:', data.message);
            showToast('فشل تحميل المهام', 'error');
        }
    } catch (error) {
        console.error('❌ Error loading tasks:', error);
        showToast('خطأ في تحميل المهام', 'error');
        // استخدام بيانات تجريبية في حالة الخطأ
        adminData.tasks = [];
        renderAdminTasks();
    }
}

/**
 * عرض المهام في صفحة الإدمن
 */
function renderAdminTasks() {
    const tasksGrid = document.getElementById('tasks-grid');
    if (!tasksGrid) {
        console.error('❌ Tasks grid not found');
        return;
    }
    
    // فلترة المهام النشطة فقط
    const activeTasks = adminData.tasks.filter(task => task.is_active !== false);
    
    if (!activeTasks || activeTasks.length === 0) {
        tasksGrid.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #8b95a1;">
                <p style="font-size: 48px; margin-bottom: 16px;">📝</p>
                <p style="font-size: 18px;">لا توجد مهام حالياً</p>
                <p style="font-size: 14px; margin-top: 8px;">ابدأ بإضافة مهمة جديدة</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    
    activeTasks.forEach(task => {
        const statusBadge = task.is_active 
            ? '<span class="task-status active">نشط</span>' 
            : '<span class="task-status">غير نشط</span>';
        
        const pinnedBadge = task.is_pinned 
            ? '<span style="background: #ffd436; color: #000; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; margin-left: 8px;">📌 مثبت</span>' 
            : '';
        
        const typeIcon = task.task_type === 'channel' ? '📢' : '🔗';
        const typeText = task.task_type === 'channel' ? 'قناة' : 'رابط';
        
        html += `
            <div class="admin-task-card">
                <div class="task-header">
                    <h3>${typeIcon} ${task.task_name}</h3>
                    ${pinnedBadge}
                    ${statusBadge}
                </div>
                
                ${task.task_description ? `<p class="task-description">${task.task_description}</p>` : ''}
                
                <div class="task-details">
                    <div><strong>النوع:</strong> ${typeText}</div>
                    <div><strong>الرابط:</strong> <a href="${task.task_link}" target="_blank" class="channel-link">${task.task_link}</a></div>
                    ${task.channel_username ? `<div><strong>القناة:</strong> ${task.channel_username}</div>` : ''}
                    <div><strong>المكافأة:</strong> <span class="task-reward">جزء من نظام 5 مهمات = 1 دورة</span></div>
                    <div><strong>تاريخ الإضافة:</strong> ${new Date(task.added_at).toLocaleDateString('ar-EG')}</div>
                </div>
                
                <div class="task-footer">
                    <button class="btn-secondary" onclick="editTask(${task.id})">
                        ✏️ تعديل
                    </button>
                    <button class="delete-btn" onclick="deleteTask(${task.id})">
                        🗑️ حذف
                    </button>
                </div>
            </div>
        `;
    });
    
    tasksGrid.innerHTML = html;
}

/**
 * تعديل مهمة موجودة
 */
function editTask(taskId) {
    console.log('✏️ Editing task:', taskId);
    
    // البحث عن المهمة
    const task = adminData.tasks.find(t => t.id === taskId);
    if (!task) {
        showToast('❌ لم يتم العثور على المهمة', 'error');
        return;
    }
    
    // فتح المودال
    const modal = document.getElementById('add-task-modal');
    if (!modal) {
        showToast('❌ خطأ: لم يتم العثور على النموذج', 'error');
        return;
    }
    
    // ملء البيانات الحالية
    document.getElementById('task-name').value = task.task_name || '';
    document.getElementById('task-link').value = task.task_link || '';
    document.getElementById('task-description').value = task.task_description || '';
    document.getElementById('task-pinned').checked = task.is_pinned || false;
    document.getElementById('task-active').checked = task.is_active !== false;
    
    // تعيين النوع
    selectTaskType(task.task_type || 'channel');
    
    // ملء اسم القناة إذا كان النوع قناة
    if (task.task_type === 'channel' && task.channel_username) {
        document.getElementById('channel-username').value = task.channel_username;
    }
    
    // تغيير عنوان المودال وزر الحفظ
    const modalTitle = modal.querySelector('.modal-header h2');
    if (modalTitle) {
        modalTitle.textContent = '✏️ تعديل مهمة';
    }
    
    const saveBtn = document.getElementById('task-submit-btn');
    if (saveBtn) {
        saveBtn.innerHTML = '<img src="/img/payment-success.svg" alt="✓" style="width: 14px; height: 14px; vertical-align: middle; margin-left: 2px;"> حفظ التعديل';
        saveBtn.onclick = () => updateTask(taskId);
    }
    
    // عرض المودال
    modal.classList.add('active');
    console.log('✅ Edit modal opened for task:', taskId);
}

/**
 * تحديث مهمة موجودة
 */
async function updateTask(taskId) {
    console.log('💾 Updating task:', taskId);
    
    try {
        const taskName = document.getElementById('task-name').value.trim();
        const taskLink = document.getElementById('task-link').value.trim();
        const taskDescription = document.getElementById('task-description').value.trim();
        const isPinned = document.getElementById('task-pinned').checked;
        const isActive = document.getElementById('task-active').checked;
        const taskType = document.querySelector('input[name="task-type"]:checked')?.value || 'channel';
        const channelUsername = document.getElementById('channel-username').value.trim();
        
        // التحقق من البيانات المطلوبة
        if (!taskName) {
            showToast('⚠️ الرجاء إدخال اسم المهمة', 'warning');
            return;
        }
        
        if (!taskLink) {
            showToast('⚠️ الرجاء إدخال رابط المهمة', 'warning');
            return;
        }
        
        if (taskType === 'channel' && !channelUsername) {
            showToast('⚠️ الرجاء إدخال معرف القناة', 'warning');
            return;
        }
        
        // بيانات المهمة المحدثة
        const taskData = {
            task_id: taskId,
            task_name: taskName,
            task_link: taskLink,
            task_description: taskDescription,
            task_type: taskType,
            is_pinned: isPinned,
            is_active: isActive,
            admin_id: 1797127532
        };
        
        if (taskType === 'channel') {
            taskData.channel_username = channelUsername.startsWith('@') ? channelUsername : '@' + channelUsername;
        }
        
        console.log('📤 Sending update:', taskData);
        
        // إرسال البيانات إلى API
        showLoading();
        const API_BASE_URL = window.CONFIG?.API_BASE_URL || '/api';
        const response = await fetch(`${API_BASE_URL}/admin/tasks`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(taskData)
        });
        
        const result = await response.json();
        hideLoading();
        
        console.log('📥 Server response:', result);
        
        if (result.success) {
            showToast('✅ تم تحديث المهمة بنجاح!', 'success');
            closeModal('add-task-modal');
            loadTasks(); // إعادة تحميل القائمة
        } else {
            const errorMsg = result.message || 'فشل تحديث المهمة';
            showToast(`❌ ${errorMsg}`, 'error');
            console.error('❌ Task update failed:', result);
        }
        
    } catch (error) {
        hideLoading();
        console.error('❌ Error updating task:', error);
        showToast('❌ خطأ في الاتصال بالسيرفر', 'error');
    }
}

/**
 * حذف مهمة
 */
async function deleteTask(taskId) {
    if (!confirm('هل أنت متأكد من حذف هذه المهمة؟')) {
        return;
    }
    
    try {
        showLoading();
        const API_BASE_URL = window.CONFIG?.API_BASE_URL || '/api';
        const response = await fetch(`${API_BASE_URL}/admin/tasks?task_id=${taskId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        hideLoading();
        
        if (data.success) {
            showToast('✅ تم حذف المهمة بنجاح', 'success');
            loadTasks(); // إعادة تحميل القائمة
        } else {
            showToast('❌ فشل حذف المهمة', 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('❌ Error deleting task:', error);
        showToast('❌ خطأ في الاتصال', 'error');
    }
}

async function loadChannels() {
    console.log('📥 Loading channels from API...');
    try {
        const API_BASE_URL = window.CONFIG?.API_BASE_URL || '/api';
        const response = await fetch(`${API_BASE_URL}/admin/channels`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('✅ Channels loaded:', data);
        
        if (data.success && data.channels) {
            adminData.channels = data.channels;
            renderAdminChannels();
        } else {
            console.error('❌ Failed to load channels:', data.message);
            showToast('فشل تحميل القنوات', 'error');
        }
    } catch (error) {
        console.error('❌ Error loading channels:', error);
        showToast('خطأ في تحميل القنوات', 'error');
        adminData.channels = [];
        renderAdminChannels();
    }
}

/**
 * عرض القنوات في صفحة الإدمن
 */
function renderAdminChannels() {
    const channelsGrid = document.getElementById('channels-grid');
    if (!channelsGrid) {
        console.error('❌ Channels grid not found');
        return;
    }
    
    if (!adminData.channels || adminData.channels.length === 0) {
        channelsGrid.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #8b95a1;">
                <p style="font-size: 48px; margin-bottom: 16px;">📢</p>
                <p style="font-size: 18px;">لا توجد قنوات حالياً</p>
                <p style="font-size: 14px; margin-top: 8px;">ابدأ بإضافة قناة إجبارية</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    
    adminData.channels.forEach(channel => {
        const statusBadge = channel.is_active 
            ? '<span class="task-status active">نشط</span>' 
            : '<span class="task-status">غير نشط</span>';
        
        html += `
            <div class="admin-task-card">
                <div class="task-header">
                    <h3>📢 ${channel.channel_name}</h3>
                    ${statusBadge}
                </div>
                
                <div class="task-details">
                    <div><strong>المعرف:</strong> ${channel.channel_id}</div>
                    <div><strong>الرابط:</strong> <a href="${channel.channel_url}" target="_blank" class="channel-link">${channel.channel_url}</a></div>
                    <div><strong>تاريخ الإضافة:</strong> ${new Date(channel.added_at).toLocaleDateString('ar-EG')}</div>
                </div>
                
                <div class="task-footer">
                    <button class="delete-btn" onclick="deleteChannel('${channel.channel_id}')">
                        🗑️ حذف
                    </button>
                </div>
            </div>
        `;
    });
    
    channelsGrid.innerHTML = html;
}

/**
 * فتح نموذج إضافة قناة
 */
function openAddChannelModal() {
    console.log('🎯 Opening Add Channel Modal');
    const modal = document.getElementById('add-channel-modal');
    if (!modal) {
        console.error('❌ Modal not found');
        showToast('❌ خطأ: لم يتم العثور على النموذج', 'error');
        return;
    }
    
    // إعادة تعيين النموذج
    document.getElementById('channel-name').value = '';
    document.getElementById('channel-id').value = '';
    document.getElementById('channel-url').value = '';
    
    // عرض النموذج
    modal.style.display = 'flex';
    console.log('✅ Modal opened');
}

/**
 * إغلاق نموذج إضافة القناة
 */
function closeAddChannelModal() {
    console.log('🚪 Closing Add Channel Modal');
    const modal = document.getElementById('add-channel-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * إنشاء قناة جديدة
 */
async function createChannel() {
    console.log('📝 Creating new channel...');
    
    try {
        const channelName = document.getElementById('channel-name').value.trim();
        const channelId = document.getElementById('channel-id').value.trim();
        const channelUrl = document.getElementById('channel-url').value.trim();
        const isActive = document.getElementById('channel-active').checked;
        
        // التحقق من البيانات المطلوبة
        if (!channelName) {
            showToast('⚠️ الرجاء إدخال اسم القناة', 'warning');
            return;
        }
        
        if (!channelId) {
            showToast('⚠️ الرجاء إدخال معرف القناة', 'warning');
            return;
        }
        
        if (!channelUrl) {
            showToast('⚠️ الرجاء إدخال رابط القناة', 'warning');
            return;
        }
        
        // بيانات القناة
        const channelData = {
            channel_name: channelName,
            channel_id: channelId.startsWith('@') ? channelId : '@' + channelId,
            channel_url: channelUrl,
            is_active: isActive,
            admin_id: 1797127532
        };
        
        console.log('📤 Sending channel data:', channelData);
        
        // إرسال البيانات إلى API
        showLoading();
        const API_BASE_URL = window.CONFIG?.API_BASE_URL || '/api';
        const response = await fetch(`${API_BASE_URL}/admin/channels`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(channelData)
        });
        
        const result = await response.json();
        hideLoading();
        
        console.log('📥 Server response:', result);
        
        if (result.success) {
            showToast('✅ تم إضافة القناة بنجاح!', 'success');
            closeAddChannelModal();
            loadChannels(); // إعادة تحميل القائمة
        } else {
            const errorMsg = result.message || 'فشل إضافة القناة';
            showToast(`❌ ${errorMsg}`, 'error');
            console.error('❌ Channel creation failed:', result);
        }
        
    } catch (error) {
        hideLoading();
        console.error('❌ Error creating channel:', error);
        showToast('❌ خطأ في الاتصال بالسيرفر', 'error');
    }
}

/**
 * حذف قناة
 */
async function deleteChannel(channelId) {
    if (!confirm('هل أنت متأكد من حذف هذه القناة؟')) {
        return;
    }
    
    try {
        showLoading();
        const API_BASE_URL = window.CONFIG?.API_BASE_URL || '/api';
        const response = await fetch(`${API_BASE_URL}/admin/channels?channel_id=${encodeURIComponent(channelId)}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        hideLoading();
        
        if (data.success) {
            showToast('✅ تم حذف القناة بنجاح', 'success');
            loadChannels(); // إعادة تحميل القائمة
        } else {
            showToast('❌ فشل حذف القناة', 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('❌ Error deleting channel:', error);
        showToast('❌ خطأ في الاتصال', 'error');
    }
}

// ═══════════════════════════════════════════════════════════════
// ⚙️ SETTINGS MANAGEMENT
// ═══════════════════════════════════════════════════════════════

async function loadSettings() {
    try {
        // جلب الإعدادات من الـ API
        const response = await fetch(`${window.CONFIG.API_BASE_URL}/settings`);
        const result = await response.json();
        
        if (result.success && result.data) {
            // تحميل الإعدادات
            document.getElementById('min-withdrawal').value = result.data.min_withdrawal || 0.1;
            document.getElementById('max-withdrawal').value = result.data.max_withdrawal || 100;
            document.getElementById('auto-withdrawal').checked = result.data.auto_withdrawal_enabled || false;
            
            console.log('✅ Settings loaded:', result.data);
        } else {
            // استخدام القيم الافتراضية
            document.getElementById('min-withdrawal').value = window.CONFIG?.MIN_WITHDRAWAL_AMOUNT || 0.1;
            document.getElementById('max-withdrawal').value = 100;
            document.getElementById('auto-withdrawal').checked = false;
        }
        
        // تحميل إعدادات التحقق من التعدد
        const adminId = window.Telegram?.WebApp?.initDataUnsafe?.user?.id;
        if (adminId) {
            const verificationResponse = await fetch(`${window.CONFIG.API_BASE_URL}/admin/verification-settings?admin_id=${adminId}`);
            const verificationResult = await verificationResponse.json();
            
            if (verificationResult.success) {
                document.getElementById('verification-enabled').checked = verificationResult.verification_enabled !== false;
                console.log('✅ Verification settings loaded:', verificationResult.verification_enabled);
            } else {
                document.getElementById('verification-enabled').checked = true;
            }
        }
        
    } catch (error) {
        console.error('Error loading settings:', error);
        // استخدام القيم الافتراضية
        document.getElementById('min-withdrawal').value = window.CONFIG?.MIN_WITHDRAWAL_AMOUNT || 0.1;
        document.getElementById('max-withdrawal').value = 100;
        document.getElementById('auto-withdrawal').checked = false;
        document.getElementById('verification-enabled').checked = true;
    }
    
    // باقي الإعدادات
    document.getElementById('max-daily-spins').value = 10;
    document.getElementById('spin-cooldown').value = (window.CONFIG?.SPIN_COOLDOWN || 2000) / 1000;
    document.getElementById('initial-spins').value = 3;
    document.getElementById('referrals-per-spin').value = window.CONFIG?.SPINS_PER_REFERRALS || 5;
    document.getElementById('referral-bonus').value = 0.001;
    document.getElementById('rate-limiting').checked = true;
    document.getElementById('event-logging').checked = true;
}

async function saveSettings() {
    showLoading();
    
    try {
        // جمع الإعدادات
        const settings = {
            minWithdrawal: parseFloat(document.getElementById('min-withdrawal').value),
            maxWithdrawal: parseFloat(document.getElementById('max-withdrawal').value),
            auto_withdrawal_enabled: document.getElementById('auto-withdrawal').checked,
            maxDailySpins: parseInt(document.getElementById('max-daily-spins').value),
            spinCooldown: parseInt(document.getElementById('spin-cooldown').value),
            initialSpins: parseInt(document.getElementById('initial-spins').value),
            referralsPerSpin: parseInt(document.getElementById('referrals-per-spin').value),
            referralBonus: parseFloat(document.getElementById('referral-bonus').value),
            rateLimiting: document.getElementById('rate-limiting').checked,
            eventLogging: document.getElementById('event-logging').checked
        };
        
        console.log('Saving settings:', settings);
        
        // حفظ الإعدادات في الـ API
        const response = await fetch(`${window.CONFIG.API_BASE_URL}/settings`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        const result = await response.json();
        
        hideLoading();
        
        if (result.success) {
            showToast('✅ تم حفظ الإعدادات بنجاح', 'success');
            
            // تحديث النص بناءً على الحالة
            const autoWithdrawalStatus = settings.auto_withdrawal_enabled ? 'مفعّل ✅' : 'معطّل ❌';
            console.log(`💡 السحب التلقائي الآن: ${autoWithdrawalStatus}`);
        } else {
            showToast('❌ فشل حفظ الإعدادات: ' + (result.error || 'خطأ غير معروف'), 'error');
        }
        
    } catch (error) {
        console.error('Error saving settings:', error);
        hideLoading();
        showToast('❌ فشل حفظ الإعدادات', 'error');
    }
}

// ═══════════════════════════════════════════════════════════════
// 🎯 EVENT LISTENERS
// ═══════════════════════════════════════════════════════════════

function setupEventListeners() {
    console.log('🎯 Setting up event listeners...');
    
    // Tab switching
    const tabs = document.querySelectorAll('.admin-tab');
    console.log('Found tabs:', tabs.length);
    console.log('Tabs list:', Array.from(tabs).map(t => ({
        text: t.textContent.trim(),
        dataset: t.dataset.tab,
        classList: Array.from(t.classList)
    })));
    
    if (tabs.length === 0) {
        console.error('❌ NO TABS FOUND! Check if .admin-tab elements exist in HTML');
    }
    
    tabs.forEach((tab, index) => {
        console.log(`Adding click listener to tab ${index}:`, tab.dataset.tab);
        tab.addEventListener('click', (e) => {
            console.log('🖱️ Tab clicked:', tab.dataset.tab, e);
            const targetTab = tab.dataset.tab;
            switchTab(targetTab);
        });
    });
    
    console.log('✅ Event listeners setup complete');
    
    // Auto-withdrawal toggle listener
    const autoWithdrawalToggle = document.getElementById('auto-withdrawal');
    if (autoWithdrawalToggle) {
        autoWithdrawalToggle.addEventListener('change', async (e) => {
            const isEnabled = e.target.checked;
            console.log('🔄 Auto-withdrawal toggled:', isEnabled);
            
            try {
                const response = await fetch(`${window.CONFIG.API_BASE_URL}/settings`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ auto_withdrawal_enabled: isEnabled })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    const status = isEnabled ? '✅ مفعّل' : '❌ معطّل';
                    showToast(`السحب التلقائي الآن ${status}`, 'success');
                } else {
                    showToast('❌ فشل تحديث الإعداد', 'error');
                    // إرجاع الحالة السابقة
                    e.target.checked = !isEnabled;
                }
            } catch (error) {
                console.error('Error toggling auto-withdrawal:', error);
                showToast('❌ خطأ في الاتصال', 'error');
                // إرجاع الحالة السابقة
                e.target.checked = !isEnabled;
            }
        });
    }
    
    // Verification toggle listener
    const verificationToggle = document.getElementById('verification-enabled');
    if (verificationToggle) {
        verificationToggle.addEventListener('change', async (e) => {
            const isEnabled = e.target.checked;
            console.log('🔄 Verification toggled:', isEnabled);
            
            const adminId = window.Telegram?.WebApp?.initDataUnsafe?.user?.id;
            if (!adminId) {
                showToast('❌ غير مصرح لك', 'error');
                e.target.checked = !isEnabled;
                return;
            }
            
            try {
                const response = await fetch(`${window.CONFIG.API_BASE_URL}/admin/verification-settings`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        admin_id: adminId,
                        enabled: isEnabled 
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    const status = isEnabled ? '✅ مفعّل' : '❌ معطّل';
                    showToast(`التحقق من التعدد الآن ${status}`, 'success');
                } else {
                    showToast('❌ فشل تحديث الإعداد', 'error');
                    e.target.checked = !isEnabled;
                }
            } catch (error) {
                console.error('Error toggling verification:', error);
                showToast('❌ خطأ في الاتصال', 'error');
                e.target.checked = !isEnabled;
            }
        });
    }
    
    // Filter buttons for withdrawals
    const filterBtns = document.querySelectorAll('.filter-btn');
    console.log('Found filter buttons:', filterBtns.length);
    
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            console.log('Filter clicked:', btn.dataset.status);
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            renderWithdrawals(btn.dataset.status);
        });
    });
    
    // User search
    const searchInput = document.getElementById('user-search');
    if (searchInput) {
        console.log('User search input found');
        // البحث عند الخروج من حقل النص
        searchInput.addEventListener('blur', (e) => {
            const query = e.target.value.toLowerCase().trim();
            if (query) {
                filterUsersTable(query);
            } else {
                renderUsersTable(); // إعادة عرض جميع المستخدمين
            }
        });
        
        // البحث عند الضغط على Enter
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const query = e.target.value.toLowerCase().trim();
                if (query) {
                    filterUsersTable(query);
                } else {
                    renderUsersTable();
                }
            }
        });
    }
    
    // Close modals on outside click
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });
    
    // Add Task Modal - Type selector buttons
    const typeChannelBtn = document.getElementById('type-channel');
    const typeLinkBtn = document.getElementById('type-link');
    
    if (typeChannelBtn) {
        typeChannelBtn.addEventListener('click', () => selectTaskType('channel'));
        console.log('✅ Channel type button listener added');
    }
    
    if (typeLinkBtn) {
        typeLinkBtn.addEventListener('click', () => selectTaskType('link'));
        console.log('✅ Link type button listener added');
    }
    
    // Add Task Modal - Close button
    const closeTaskModalBtn = document.querySelector('#add-task-modal .close-modal');
    if (closeTaskModalBtn) {
        closeTaskModalBtn.addEventListener('click', closeAddTaskModal);
        console.log('✅ Close task modal button listener added');
    }
    
    // Add Task Modal - Cancel button
    const cancelTaskBtn = document.querySelector('#add-task-modal .btn-cancel');
    if (cancelTaskBtn) {
        cancelTaskBtn.addEventListener('click', closeAddTaskModal);
        console.log('✅ Cancel task button listener added');
    }
    
    // Add Task Modal - Character counters
    setupCharacterCounters();
}

/**
 * إعداد عدادات الأحرف للحقول
 */
function setupCharacterCounters() {
    const fields = [
        { id: 'task-name', max: 50, counterId: 'name-count' },
        { id: 'task-link', max: 200, counterId: 'link-count' },
        { id: 'task-description', max: 100, counterId: 'desc-count' },
        { id: 'channel-name', max: 100, counterId: 'channel-name-count' },
        { id: 'channel-url', max: 200, counterId: 'channel-url-count' }
    ];
    
    fields.forEach(field => {
        const input = document.getElementById(field.id);
        const counter = document.getElementById(field.counterId);
        
        if (input && counter) {
            input.addEventListener('input', () => {
                const length = input.value.length;
                counter.textContent = `${length}/${field.max}`;
                
                // تغيير اللون عند الاقتراب من الحد الأقصى
                if (length > field.max * 0.9) {
                    counter.style.color = '#ef5350';
                } else if (length > field.max * 0.7) {
                    counter.style.color = '#ffd436';
                } else {
                    counter.style.color = '#8b95a1';
                }
            });
            
            // تحديد الحد الأقصى
            input.setAttribute('maxlength', field.max);
        }
    });
}

function switchTab(tabName) {
    console.log('🔀 Switching to tab:', tabName);
    
    // Update tab buttons
    document.querySelectorAll('.admin-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    const targetTab = document.querySelector(`.admin-tab[data-tab="${tabName}"]`);
    if (targetTab) {
        targetTab.classList.add('active');
        console.log('✅ Tab button activated');
    } else {
        console.error('❌ Tab button not found for:', tabName);
    }
    
    // Update tab content
    document.querySelectorAll('.admin-tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    const targetContent = document.getElementById(`tab-${tabName}`);
    if (targetContent) {
        targetContent.classList.add('active');
        console.log('✅ Tab content activated');
    } else {
        console.error('❌ Tab content not found for:', tabName);
    }
}

// ═══════════════════════════════════════════════════════════════
// 🛠 UTILITY FUNCTIONS
// ═══════════════════════════════════════════════════════════════

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
}

function refreshData() {
    showToast('🔄 جاري تحديث البيانات...', 'info');
    loadDashboardData();
}

function logout() {
    if (confirm('هل أنت متأكد من تسجيل الخروج؟')) {
        window.Telegram?.WebApp?.close();
    }
}

function showLoading() {
    console.log('🔄 Showing loading overlay');
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.add('active');
        console.log('✅ Loading overlay activated');
    } else {
        console.error('❌ Loading overlay element not found!');
    }
}

function hideLoading() {
    console.log('🔄 Hiding loading overlay');
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.remove('active');
        console.log('✅ Loading overlay deactivated', 'Has active class:', overlay.classList.contains('active'));
    } else {
        console.error('❌ Loading overlay element not found!');
    }
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 10);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ═══════════════════════════════════════════════════════════════
// ➕ ADD TASK MODAL FUNCTIONS
// ═══════════════════════════════════════════════════════════════

/**
 * فتح نموذج إضافة مهمة جديدة
 */
function openAddTaskModal() {
    console.log('🎯 Opening Add Task Modal');
    const modal = document.getElementById('add-task-modal');
    if (!modal) {
        console.error('❌ Modal not found');
        showToast('❌ خطأ: لم يتم العثور على النموذج', 'error');
        return;
    }
    
    // إعادة تعيين النموذج
    document.getElementById('task-name').value = '';
    document.getElementById('task-link').value = '';
    document.getElementById('task-description').value = '';
    document.getElementById('task-pinned').checked = false;
    document.getElementById('task-active').checked = true;
    document.getElementById('channel-username').value = '';
    
    // تعيين النوع الافتراضي إلى قناة
    selectTaskType('channel');
    
    // إعادة تعيين عنوان المودال وزر الحفظ
    const modalTitle = modal.querySelector('.modal-header h2');
    if (modalTitle) {
        modalTitle.textContent = '➕ إضافة مهمة جديدة';
    }
    
    const saveBtn = document.getElementById('task-submit-btn');
    if (saveBtn) {
        saveBtn.innerHTML = '<img src="/img/checksup.png" alt="✓" style="width: 14px; height: 14px; vertical-align: middle; margin-left: 2px;"> إنشاء المهمة';
        saveBtn.onclick = createTask;
    }
    
    // عرض النموذج
    modal.classList.add('active');
    console.log('✅ Modal opened');
}

/**
 * إغلاق نموذج إضافة المهمة
 */
function closeAddTaskModal() {
    console.log('🚪 Closing Add Task Modal');
    const modal = document.getElementById('add-task-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * اختيار نوع المهمة (قناة أو رابط)
 */
function selectTaskType(type) {
    console.log('🔄 Selecting task type:', type);
    
    // تحديث أزرار النوع
    const channelBtn = document.getElementById('type-channel');
    const linkBtn = document.getElementById('type-link');
    const channelUsernameGroup = document.getElementById('channel-username-group');
    
    if (!channelBtn || !linkBtn || !channelUsernameGroup) {
        console.error('❌ Type buttons or channel group not found');
        return;
    }
    
    if (type === 'channel') {
        channelBtn.classList.add('active');
        linkBtn.classList.remove('active');
        channelUsernameGroup.style.display = 'block';
    } else {
        linkBtn.classList.add('active');
        channelBtn.classList.remove('active');
        channelUsernameGroup.style.display = 'none';
    }
}

/**
 * إنشاء مهمة جديدة
 */
async function createTask() {
    console.log('📝 Creating new task...');
    
    try {
        // جمع البيانات من النموذج
        const taskName = document.getElementById('task-name').value.trim();
        const taskLink = document.getElementById('task-link').value.trim();
        const taskDescription = document.getElementById('task-description').value.trim();
        const isPinned = document.getElementById('task-pinned').checked;
        const isActive = document.getElementById('task-active').checked;
        
        // تحديد نوع المهمة
        const isChannel = document.getElementById('type-channel').classList.contains('active');
        const taskType = isChannel ? 'channel' : 'link';
        
        // التحقق من البيانات المطلوبة
        if (!taskName) {
            showToast('⚠️ الرجاء إدخال اسم المهمة', 'warning');
            return;
        }
        
        if (!taskLink) {
            showToast('⚠️ الرجاء إدخال الرابط', 'warning');
            return;
        }
        
        // بيانات المهمة
        const taskData = {
            task_name: taskName,
            task_link: taskLink,
            task_type: taskType,
            task_description: taskDescription,
            is_pinned: isPinned,
            is_active: isActive
        };
        
        // إضافة معرف القناة إذا كان النوع قناة
        if (isChannel) {
            const channelUsername = document.getElementById('channel-username').value.trim();
            if (!channelUsername) {
                showToast('⚠️ الرجاء إدخال معرف القناة', 'warning');
                return;
            }
            taskData.channel_username = channelUsername;
        }
        
        console.log('📤 Sending task data:', taskData);
        
        // إرسال البيانات إلى API
        showLoading();
        const API_BASE_URL = window.CONFIG?.API_BASE_URL || '/api';
        const response = await fetch(`${API_BASE_URL}/admin/tasks`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(taskData)
        });
        
        const result = await response.json();
        hideLoading();
        
        console.log('📥 Server response:', result);
        
        if (result.success) {
            showToast('✅ تم إضافة المهمة بنجاح!', 'success');
            closeAddTaskModal();
            
            // تحديث قائمة المهام
            if (typeof loadAdminTasks === 'function') {
                loadAdminTasks();
            }
        } else {
            const errorMsg = result.message || 'فشل إضافة المهمة';
            showToast(`❌ ${errorMsg}`, 'error');
            console.error('❌ Task creation failed:', result);
        }
        
    } catch (error) {
        hideLoading();
        console.error('❌ Error creating task:', error);
        showToast('❌ خطأ في الاتصال بالسيرفر', 'error');
    }
}

// ═══════════════════════════════════════════════════════════════
// 📤 EXPORT TO BACKEND (OLD CODE - WILL BE REMOVED LATER)
// ═══════════════════════════════════════════════════════════════

async function openAddChannelModal() {
    const channelId = prompt('معرف القناة (مثال: @ChannelName):');
    if (!channelId) return;
    
    const channelName = prompt('اسم القناة:');
    if (!channelName) return;
    
    const channelUrl = prompt('رابط القناة (https://t.me/...):');
    if (!channelUrl) return;
    
    try {
        showLoading();
        const API_BASE_URL = window.CONFIG?.API_BASE_URL || '/api';
        const response = await fetch(`${API_BASE_URL}/admin/channels`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                channel_id: channelId,
                channel_name: channelName,
                channel_url: channelUrl,
                admin_id: window.Telegram?.WebApp?.initDataUnsafe?.user?.id || 1797127532
            })
        });
        
        const result = await response.json();
        hideLoading();
        
        if (result.success) {
            showToast('✅ تم إضافة القناة بنجاح!', 'success');
            loadChannels();
        } else {
            showToast('❌ فشل إضافة القناة', 'error');
        }
    } catch (error) {
        hideLoading();
        showToast('❌ خطأ في الاتصال', 'error');
        console.error(error);
    }
}



// ═══════════════════════════════════════════════════════════════
// 🎰 ADD SPINS TO USER
// ═══════════════════════════════════════════════════════════════

// إضافة لفات سريعة لمستخدم محدد
function quickAddSpins(userId, username) {
    const spins = prompt(`🎰 كم لفة تريد إضافتها لـ ${username}?`);
    
    if (!spins) return;
    
    const spinsAmount = parseInt(spins);
    
    if (isNaN(spinsAmount) || spinsAmount < 1) {
        showToast('❌ يرجى إدخال عدد صحيح', 'error');
        return;
    }
    
    addSpinsToUserByUsername(username, spinsAmount);
}

async function addSpinsToUserByUsername(username, spinsAmount) {
    try {
        showLoading();
        
        const API_BASE_URL = window.CONFIG?.API_BASE_URL || '/api';
        const response = await fetch(`${API_BASE_URL}/admin/add-spins`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: username,
                spins_count: spinsAmount,
                admin_id: window.Telegram?.WebApp?.initDataUnsafe?.user?.id || 1797127532
            })
        });
        
        const result = await response.json();
        
        hideLoading();
        
        if (result.success) {
            showToast(`✅ تم إضافة ${spinsAmount} لفة لـ ${username}`, 'success');
            loadUsers();
        } else {
            showToast('❌ فشل إضافة اللفات: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Error adding spins:', error);
        hideLoading();
        showToast('❌ خطأ في إضافة اللفات', 'error');
    }
}

function openAddSpinsModal() {
    const modal = document.getElementById('add-spins-modal');
    if (modal) {
        modal.classList.add('active');
        // Clear previous inputs
        document.getElementById('target-username').value = '';
        document.getElementById('spins-amount').value = '';
    }
}

async function addSpinsToUser() {
    const username = document.getElementById('target-username').value.trim();
    const spinsAmount = parseInt(document.getElementById('spins-amount').value);
    
    if (!username) {
        showToast('❌ يرجى إدخال اسم المستخدم', 'error');
        return;
    }
    
    if (!spinsAmount || spinsAmount < 1) {
        showToast('❌ يرجى إدخال عدد صحيح من اللفات', 'error');
        return;
    }
    
    try {
        showLoading();
        
        const API_BASE_URL = window.CONFIG?.API_BASE_URL || '/api';
        const response = await fetch(`${API_BASE_URL}/admin/add-spins`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: username,
                spins_count: spinsAmount,
                admin_id: window.Telegram?.WebApp?.initDataUnsafe?.user?.id || 1797127532
            })
        });
        
        const result = await response.json();
        
        hideLoading();
        
        if (result.success) {
            showToast(`✅ تم إضافة ${spinsAmount} لفة لـ ${username}`, 'success');
            closeModal('add-spins-modal');
            
            // Reload users list if on users tab
            if (document.getElementById('tab-users').classList.contains('active')) {
                loadUsers();
            }
        } else {
            showToast('❌ فشل إضافة اللفات: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Error adding spins:', error);
        hideLoading();
        showToast('❌ خطأ في إضافة اللفات', 'error');
    }
}

// ═══════════════════════════════════════════════════════════════
// 🔧 HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════════

async function deleteChannel(channelId) {
    if (!confirm('هل تريد حذف هذه القناة؟')) return;
    
    try {
        showLoading();
        const API_BASE_URL = window.CONFIG?.API_BASE_URL || '/api';
        const response = await fetch(`${API_BASE_URL}/admin/channels?channel_id=${channelId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        hideLoading();
        
        if (result.success) {
            showToast('✅ تم حذف القناة', 'success');
            loadChannels();
        } else {
            showToast('❌ فشل الحذف', 'error');
        }
    } catch (error) {
        hideLoading();
        showToast('❌ خطأ في الاتصال', 'error');
    }
}

// عرض إحالات المستخدم
async function viewUserReferrals(userId, userName) {
    try {
        showLoading();
        const API_BASE_URL = window.CONFIG?.API_BASE_URL || '/api';
        const response = await fetch(`${API_BASE_URL}/admin/user-referrals?user_id=${userId}`);
        const result = await response.json();
        
        hideLoading();
        
        if (result.success) {
            const referrals = result.data || [];
            showReferralsModal(userName, referrals);
        } else {
            showToast('❌ فشل تحميل الإحالات', 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('Error loading referrals:', error);
        showToast('❌ خطأ في تحميل الإحالات', 'error');
    }
}

// عرض modal الإحالات
function showReferralsModal(userName, referrals) {
    const modal = document.getElementById('user-referrals-modal');
    if (!modal) {
        // إنشاء modal جديد
        const modalHtml = `
            <div id="user-referrals-modal" class="modal active">
                <div class="modal-content" style="max-width: 800px;">
                    <div class="modal-header">
                        <h2>👥 إحالات ${userName}</h2>
                        <button class="close-modal" onclick="closeModal('user-referrals-modal')">✕</button>
                    </div>
                    <div class="modal-body" id="referrals-list-container">
                        <!-- سيتم ملؤها بالبيانات -->
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    } else {
        modal.classList.add('active');
    }
    
    // ملء قائمة الإحالات
    const container = document.getElementById('referrals-list-container');
    
    if (referrals.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #8b95a1;">
                <p style="font-size: 48px; margin-bottom: 16px;">👥</p>
                <p style="font-size: 18px;">لا توجد إحالات</p>
                <p style="font-size: 14px; margin-top: 8px;">لم يقم أحد بالتسجيل عبر رابط هذا المستخدم بعد</p>
            </div>
        `;
    } else {
        container.innerHTML = `
            <div style="max-height: 500px; overflow-y: auto;">
                <table class="admin-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>الاسم</th>
                            <th>اسم المستخدم</th>
                            <th>تاريخ التسجيل</th>
                            <th>الحالة</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${referrals.map(ref => `
                            <tr>
                                <td>${ref.id}</td>
                                <td>${ref.name}</td>
                                <td>${ref.username || '-'}</td>
                                <td>${new Date(ref.joined_at).toLocaleDateString('ar-EG')}</td>
                                <td><span class="status-badge ${ref.is_verified ? 'active' : ''}">${ref.is_verified ? '✅ مفعّل' : '⏳ معلق'}</span></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
                <div style="padding: 20px; text-align: center; color: #8b95a1; border-top: 1px solid #30363d; margin-top: 20px;">
                    <strong>إجمالي الإحالات:</strong> ${referrals.length}
                </div>
            </div>
        `;
    }
}
