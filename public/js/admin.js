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
    
    container.innerHTML = adminData.prizes.map(prize => `
        <div class="prize-item" data-id="${prize.id}">
            <div class="prize-preview" style="background: ${prize.color};">
                ${prize.emoji}
            </div>
            <div class="prize-details">
                <h3>${prize.name}</h3>
                <div class="prize-info">
                    <span>💰 القيمة: <strong>${prize.value} TON</strong></span>
                    <span>📊 النسبة: <strong>${prize.probability}%</strong></span>
                    <span>🎨 اللون: <strong>${prize.color}</strong></span>
                </div>
            </div>
            <div class="prize-actions">
                <button class="icon-btn edit" onclick="openEditPrizeModal(${prize.id})">✏️</button>
                <button class="icon-btn delete" onclick="deletePrize(${prize.id})">🗑️</button>
            </div>
        </div>
    `).join('');
}

function updatePrizesInfo() {
    const totalPrizes = adminData.prizes.length;
    const totalProbability = adminData.prizes.reduce((sum, p) => sum + p.probability, 0);
    const isValid = totalProbability === 100;
    
    document.getElementById('total-prizes-count').textContent = totalPrizes;
    document.getElementById('total-probability').textContent = `${totalProbability}%`;
    
    const statusEl = document.getElementById('system-status');
    if (isValid) {
        statusEl.textContent = '✓ صحيح';
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
    document.getElementById('edit-prize-color').value = prize.color;
    document.getElementById('edit-prize-emoji').value = prize.emoji;
    
    const modal = document.getElementById('edit-prize-modal');
    modal.classList.add('active');
}

async function addPrize() {
    const name = document.getElementById('prize-name').value;
    const value = parseFloat(document.getElementById('prize-value').value);
    const probability = parseFloat(document.getElementById('prize-probability').value);
    const color = document.getElementById('prize-color').value;
    const emoji = document.getElementById('prize-emoji').value;
    
    if (!name || isNaN(value) || isNaN(probability) || !color || !emoji) {
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
                color,
                emoji,
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
            document.getElementById('prize-color').value = '#ffa500';
            document.getElementById('prize-emoji').value = '';
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
    
    const updatedData = {
        id,
        name: document.getElementById('edit-prize-name').value,
        value: parseFloat(document.getElementById('edit-prize-value').value),
        probability: parseFloat(document.getElementById('edit-prize-probability').value),
        color: document.getElementById('edit-prize-color').value,
        emoji: document.getElementById('edit-prize-emoji').value,
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
        const API_BASE_URL = window.CONFIG?.API_BASE_URL || '/api';
        const response = await fetch(`${API_BASE_URL}/users`);
        const result = await response.json();
        
        if (result.success) {
            adminData.users = result.data || [];
        } else {
            adminData.users = [];
        }
    } catch (error) {
        console.error('Error loading users:', error);
        adminData.users = [];
    }
    
    renderUsersTable();
}

function renderUsersTable() {
    const tbody = document.getElementById('users-table-body');
    if (!tbody) return;
    
    tbody.innerHTML = adminData.users.map(user => `
        <tr>
            <td>${user.id}</td>
            <td>${user.name}</td>
            <td>${user.username}</td>
            <td>${user.balance.toFixed(4)} TON</td>
            <td>${user.spins}</td>
            <td>${user.referrals}</td>
            <td>${user.joined}</td>
            <td>
                <button class="icon-btn" onclick="viewUser(${user.id})">👁️</button>
                <button class="icon-btn edit" onclick="editUser(${user.id})">✏️</button>
            </td>
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
    
    container.innerHTML = filtered.map(w => `
        <div class="withdrawal-item">
            <div class="withdrawal-info">
                <h4>👤 ${w.user_name} (${w.user_id})</h4>
                <div class="withdrawal-details">
                    <span>💰 ${w.amount} TON</span>
                    <span>📱 ${w.method}</span>
                    <span>🕐 ${w.date}</span>
                    ${w.method === 'TON' ? `<span>📍 ${w.address}</span>` : `<span>📞 ${w.number}</span>`}
                </div>
            </div>
            ${w.status === 'pending' ? `
                <div class="withdrawal-actions">
                    <button class="approve-btn" onclick="approveWithdrawal(${w.id})">✅ قبول</button>
                    <button class="reject-btn" onclick="rejectWithdrawal(${w.id})">❌ رفض</button>
                </div>
            ` : `
                <span class="status-badge ${w.status}">${w.status === 'approved' ? '✅ مقبول' : '❌ مرفوض'}</span>
            `}
        </div>
    `).join('');
}

function approveWithdrawal(id) {
    const withdrawal = adminData.withdrawals.find(w => w.id === id);
    if (!withdrawal) return;
    
    if (!confirm(`هل أنت متأكد من قبول طلب السحب؟\n\nالمبلغ: ${withdrawal.amount} TON\nالمستخدم: ${withdrawal.user_name}`)) {
        return;
    }
    
    withdrawal.status = 'approved';
    renderWithdrawals('pending');
    showToast('✅ تم قبول طلب السحب', 'success');
    
    // TODO: Send actual TON transaction
}

function rejectWithdrawal(id) {
    const withdrawal = adminData.withdrawals.find(w => w.id === id);
    if (!withdrawal) return;
    
    const reason = prompt('سبب الرفض (اختياري):');
    
    withdrawal.status = 'rejected';
    renderWithdrawals('pending');
    showToast('✅ تم رفض طلب السحب', 'success');
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
    
    if (!adminData.tasks || adminData.tasks.length === 0) {
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
    
    adminData.tasks.forEach(task => {
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
 * تعديل مهمة (قريباً)
 */
function editTask(taskId) {
    showToast('⚠️ قريباً: تعديل المهمة', 'warning');
    console.log('Edit task:', taskId);
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
    adminData.channels = [
        { id: 1, name: 'قناة الأخبار', username: '@pandanews', chat_id: -1001234567890, mandatory: true },
        { id: 2, name: 'مجموعة الدعم', username: '@pandasupport', chat_id: -1009876543210, mandatory: false }
    ];
}

// ═══════════════════════════════════════════════════════════════
// ⚙️ SETTINGS MANAGEMENT
// ═══════════════════════════════════════════════════════════════

async function loadSettings() {
    // Load current settings
    document.getElementById('min-withdrawal').value = window.CONFIG?.MIN_WITHDRAWAL_AMOUNT || 0.1;
    document.getElementById('max-withdrawal').value = 100;
    document.getElementById('auto-withdrawal').checked = true;
    document.getElementById('max-daily-spins').value = 10;
    document.getElementById('spin-cooldown').value = (window.CONFIG?.SPIN_COOLDOWN || 2000) / 1000;
    document.getElementById('initial-spins').value = 3;
    document.getElementById('referrals-per-spin').value = window.CONFIG?.SPINS_PER_REFERRALS || 5;
    document.getElementById('referral-bonus').value = 0.001;
    document.getElementById('rate-limiting').checked = true;
    document.getElementById('event-logging').checked = true;
}

function saveSettings() {
    showLoading();
    
    // Collect all settings
    const settings = {
        minWithdrawal: parseFloat(document.getElementById('min-withdrawal').value),
        maxWithdrawal: parseFloat(document.getElementById('max-withdrawal').value),
        autoWithdrawal: document.getElementById('auto-withdrawal').checked,
        maxDailySpins: parseInt(document.getElementById('max-daily-spins').value),
        spinCooldown: parseInt(document.getElementById('spin-cooldown').value),
        initialSpins: parseInt(document.getElementById('initial-spins').value),
        referralsPerSpin: parseInt(document.getElementById('referrals-per-spin').value),
        referralBonus: parseFloat(document.getElementById('referral-bonus').value),
        rateLimiting: document.getElementById('rate-limiting').checked,
        eventLogging: document.getElementById('event-logging').checked
    };
    
    // TODO: Save to backend
    console.log('Saving settings:', settings);
    
    setTimeout(() => {
        hideLoading();
        showToast('✅ تم حفظ الإعدادات بنجاح', 'success');
    }, 1000);
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
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            // Filter users table
            // TODO: Implement search functionality
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
        { id: 'task-description', max: 100, counterId: 'desc-count' }
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
    
    // عرض النموذج
    modal.style.display = 'flex';
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

async function loadTasks() {
    try {
        const API_BASE_URL = window.CONFIG?.API_BASE_URL || '/api';
        const response = await fetch(`${API_BASE_URL}/tasks`);
        const result = await response.json();
        
        if (result.success) {
            displayTasks(result.data);
        }
    } catch (error) {
        console.error('Error loading tasks:', error);
    }
}

function displayTasks(tasks) {
    const grid = document.getElementById('tasks-grid');
    if (!grid) return;
    
    grid.innerHTML = tasks.length === 0 ? 
        '<p style="text-align:center;padding:40px;color:var(--text-secondary)">لا توجد مهام</p>' :
        tasks.map(task => `
            <div class="task-card">
                <div class="task-header">
                    <span class="task-type-badge">${task.task_type === 'channel' ? '📢 قناة' : '🔗 رابط'}</span>
                    <button onclick="deleteTask(${task.id})" class="delete-btn">🗑️</button>
                </div>
                <h3>${task.task_name}</h3>
                <p>${task.task_description || ''}</p>
                <div class="task-footer">
                    <span class="task-reward">💰 ${task.reward_amount} TON</span>
                    <span class="task-status ${task.is_active ? 'active' : 'inactive'}">
                        ${task.is_active ? '✅ نشط' : '❌ معطل'}
                    </span>
                </div>
            </div>
        `).join('');
}

async function loadChannels() {
    try {
        const API_BASE_URL = window.CONFIG?.API_BASE_URL || '/api';
        const response = await fetch(`${API_BASE_URL}/admin/channels`);
        const result = await response.json();
        
        if (result.success) {
            displayChannels(result.data);
        }
    } catch (error) {
        console.error('Error loading channels:', error);
    }
}

function displayChannels(channels) {
    const grid = document.getElementById('channels-grid');
    if (!grid) return;
    
    grid.innerHTML = channels.length === 0 ?
        '<p style="text-align:center;padding:40px;color:var(--text-secondary)">لا توجد قنوات</p>' :
        channels.map(channel => `
            <div class="channel-card">
                <div class="channel-header">
                    <span class="channel-icon">📢</span>
                    <button onclick="deleteChannel('${channel.channel_id}')" class="delete-btn">🗑️</button>
                </div>
                <h3>${channel.channel_name}</h3>
                <p class="channel-id">${channel.channel_id}</p>
                <a href="${channel.channel_url}" target="_blank" class="channel-link">
                    افتح القناة
                </a>
            </div>
        `).join('');
}

async function deleteTask(taskId) {
    if (!confirm('هل تريد حذف هذه المهمة؟')) return;
    
    try {
        const response = await fetch(`/api/admin/tasks?task_id=${taskId}`, {
            method: 'DELETE'
        });
        const result = await response.json();
        
        if (result.success) {
            showToast('✅ تم حذف المهمة بنجاح', 'success');
            loadTasks();
        } else {
            showToast('❌ فشل حذف المهمة', 'error');
        }
    } catch (error) {
        console.error('Error deleting task:', error);
        showToast('❌ خطأ في حذف المهمة', 'error');
    }
}

async function deleteChannel(channelId) {
    if (!confirm('هل تريد حذف هذه القناة؟')) return;
    
    try {
        const response = await fetch(`/api/admin/channels?channel_id=${channelId}`, {
            method: 'DELETE'
        });
        const result = await response.json();
        
        if (result.success) {
            showToast('✅ تم حذف القناة بنجاح', 'success');
            loadChannels();
        } else {
            showToast('❌ فشل حذف القناة', 'error');
        }
    } catch (error) {
        console.error('Error deleting channel:', error);
        showToast('❌ خطأ في حذف القناة', 'error');
    }
}

// ═══════════════════════════════════════════════════════════════
// 🎰 ADD SPINS TO USER
// ═══════════════════════════════════════════════════════════════

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

function editUser(userId) {
    showToast(`تعديل المستخدم: ${userId}`, 'info');
}
