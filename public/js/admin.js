/**
 * 🔧 PANDA GIVEAWAYS - ADMIN PANEL SCRIPT
 * Admin Dashboard Management
 */

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
    
    // Check if user is admin
    const telegramUser = window.Telegram?.WebApp?.initDataUnsafe?.user;
    console.log('Telegram User:', telegramUser);
    
    if (!telegramUser) {
        console.warn('⚠️ No Telegram user found - allowing access for testing');
        showToast('⚠️ وضع الاختبار', 'info');
        return;
    }
    
    const adminIds = window.CONFIG?.ADMIN_IDS || [];
    if (!adminIds.includes(telegramUser.id)) {
        showToast('❌ غير مصرح لك بالدخول!', 'error');
        setTimeout(() => {
            window.Telegram?.WebApp?.close();
        }, 2000);
        return;
    }

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
    // Mock users data
    adminData.users = [
        { id: 123456, name: 'أحمد محمد', username: '@ahmed123', balance: 5.42, spins: 3, referrals: 12, joined: '2026-01-15' },
        { id: 234567, name: 'محمد علي', username: '@mohamed', balance: 2.18, spins: 1, referrals: 5, joined: '2026-01-20' },
        { id: 345678, name: 'فاطمة أحمد', username: '@fatima', balance: 8.95, spins: 5, referrals: 25, joined: '2026-01-10' }
    ];
    
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
    // Mock withdrawals data
    adminData.withdrawals = [
        { id: 1, user_id: 123456, user_name: 'أحمد محمد', amount: 5.0, method: 'TON', address: 'UQxx...xxxx', status: 'pending', date: '2026-02-02 10:30' },
        { id: 2, user_id: 234567, user_name: 'محمد علي', amount: 2.0, method: 'Vodafone', number: '01012345678', status: 'pending', date: '2026-02-02 09:15' }
    ];
    
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
    adminData.tasks = [
        { id: 1, title: 'انضم لقناة الأخبار', type: 'channel', link: 't.me/pandanews', reward: 0.01, active: true },
        { id: 2, title: 'تابعنا على تويتر', type: 'social', link: 'twitter.com/panda', reward: 0.02, active: true }
    ];
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
    document.getElementById('min-withdrawal').value = CONFIG.MIN_WITHDRAWAL_AMOUNT;
    document.getElementById('max-withdrawal').value = 100;
    document.getElementById('auto-withdrawal').checked = true;
    document.getElementById('max-daily-spins').value = 10;
    document.getElementById('spin-cooldown').value = (config.SPIN_COOLDOWN || 2000) / 1000;
    document.getElementById('initial-spins').value = 3;
    document.getElementById('referrals-per-spin').value = config.SPINS_PER_REFERRALS || 5;
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
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            console.log('Tab clicked:', tab.dataset.tab);
            const targetTab = tab.dataset.tab;
            switchTab(targetTab);
        });
    });
    
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
}

function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.admin-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`.admin-tab[data-tab="${tabName}"]`).classList.add('active');
    
    // Update tab content
    document.querySelectorAll('.admin-tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`tab-${tabName}`).classList.add('active');
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
    document.getElementById('loading-overlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.remove('active');
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
// 📤 EXPORT TO BACKEND
// ═══════════════════════════════════════════════════════════════

async function openAddTaskModal() {
    const taskType = prompt('نوع المهمة (channel/link):');
    if (!taskType || !['channel', 'link'].includes(taskType)) return;
    
    const taskName = prompt('اسم المهمة:');
    if (!taskName) return;
    
    const taskDescription = prompt('وصف المهمة:');
    const reward = parseFloat(prompt('المكافأة (TON):') || '0.01');
    
    let taskData = {
        task_type: taskType,
        task_name: taskName,
        task_description: taskDescription,
        reward_amount: reward,
        admin_id: window.Telegram?.WebApp?.initDataUnsafe?.user?.id || 1797127532
    };
    
    if (taskType === 'channel') {
        const channelId = prompt('معرف القناة (مثال: @ChannelName):');
        if (!channelId) return;
        taskData.channel_id = channelId;
    } else {
        const linkUrl = prompt('رابط المهمة:');
        if (!linkUrl) return;
        taskData.link_url = linkUrl;
        taskData.duration = parseInt(prompt('المدة بالثواني:') || '10');
    }
    
    try {
        showLoading();
        const API_BASE_URL = window.CONFIG?.API_BASE_URL || '/api';
        const response = await fetch(`${API_BASE_URL}/admin/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(taskData)
        });
        
        const result = await response.json();
        hideLoading();
        
        if (result.success) {
            showToast('✅ تم إضافة المهمة بنجاح!', 'success');
            loadTasks();
        } else {
            showToast('❌ فشل إضافة المهمة', 'error');
        }
    } catch (error) {
        hideLoading();
        showToast('❌ خطأ في الاتصال', 'error');
        console.error(error);
    }
}

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
        showLoading(true);
        
        const response = await fetch('/api/admin/add-spins', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: username,
                spins_count: spinsAmount,
                admin_id: TelegramApp.getUserId() || 1797127532
            })
        });
        
        const result = await response.json();
        
        showLoading(false);
        
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
        showLoading(false);
        showToast('❌ خطأ في إضافة اللفات', 'error');
    }
}

// ═══════════════════════════════════════════════════════════════
// 🔧 HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════════
    
    try {
        showLoading();
        const API_BASE_URL = window.CONFIG?.API_BASE_URL || '/api';
        const response = await fetch(`${API_BASE_URL}/admin/tasks?task_id=${taskId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        hideLoading();
        
        if (result.success) {
            showToast('✅ تم حذف المهمة', 'success');
            loadTasks();
        } else {
            showToast('❌ فشل الحذف', 'error');
        }
    } catch (error) {
        hideLoading();
        showToast('❌ خطأ في الاتصال', 'error');
    }
}

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
