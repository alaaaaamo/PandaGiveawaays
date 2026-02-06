// ═══════════════════════════════════════════════════════════════
// 📝 TASKS MODULE
// ═══════════════════════════════════════════════════════════════

const TasksModule = {
    tasks: [],
    completedTasks: [],
    
    async init() {
        console.log('📝 Initializing Tasks Module...');
        await this.loadTasks();
        await this.loadCompletedTasks();
        this.renderTasks();
        this.updateProgress();
    },
    
    async loadTasks() {
        try {
            DebugError.add('📝 Loading tasks from API...', 'info');
            const data = await API.request('/tasks', 'GET');
            
            if (data.success && data.tasks) {
                this.tasks = data.tasks;
                DebugError.add(`✅ Loaded ${this.tasks.length} tasks`, 'info', this.tasks);
            } else {
                DebugError.add('❌ Failed to load tasks', 'error', data);
                this.tasks = [];
            }
        } catch (error) {
            DebugError.add(`❌ Error loading tasks: ${error.message}`, 'error', error);
            this.tasks = [];
        }
    },
    
    async loadCompletedTasks() {
        try {
            const userId = TelegramApp.getUserId();
            DebugError.add(`📝 Loading completed tasks for user ${userId}...`, 'info');
            const data = await API.request(`/user/${userId}/completed-tasks`, 'GET');
            
            if (data.success && data.completed_tasks) {
                // تحويل إلى array من الـ IDs فقط
                this.completedTasks = data.completed_tasks.map(t => t.task_id);
                DebugError.add(`✅ Loaded ${this.completedTasks.length} completed tasks`, 'info', this.completedTasks);
            } else {
                this.completedTasks = [];
            }
        } catch (error) {
            DebugError.add(`❌ Error loading completed tasks: ${error.message}`, 'error', error);
            this.completedTasks = [];
        }
    },
    
    isTaskCompleted(taskId) {
        return this.completedTasks.includes(taskId);
    },
    
    renderTasks() {
        const container = document.getElementById('tasks-list');
        if (!container) return;
        
        if (this.tasks.length === 0) {
            container.innerHTML = `
                <div class="tasks-empty">
                    <div class="tasks-empty-icon">📝</div>
                    <div class="tasks-empty-text">لا توجد مهام متاحة حالياً</div>
                    <div class="tasks-empty-hint">تحقق مرة أخرى لاحقاً!</div>
                </div>
            `;
            return;
        }
        
        // Sort tasks: pinned first, then by id
        const sortedTasks = [...this.tasks].sort((a, b) => {
            if (a.is_pinned === b.is_pinned) return a.id - b.id;
            return b.is_pinned - a.is_pinned;
        });
        
        let html = '';
        sortedTasks.forEach(task => {
            const isCompleted = this.isTaskCompleted(task.id);
            html += this.createTaskCard(task, isCompleted);
        });
        
        container.innerHTML = html;
        
        // Attach event listeners
        this.attachEventListeners();
    },
    
    createTaskCard(task, isCompleted) {
        const taskIcon = task.task_type === 'channel' ? '📢' : '🔗';
        const taskTypeText = task.task_type === 'channel' ? 'قناة' : 'رابط';
        const description = task.task_description || 'اشترك في القناة واحصل على المكافأة';
        
        // حساب التقدم
        const completedCount = this.completedTasks.length;
        const progress = completedCount % 5;
        const nextReward = 5 - progress;
        
        return `
            <div class="task-card ${task.is_pinned ? 'pinned' : ''} ${isCompleted ? 'completed' : ''}" data-task-id="${task.id}">
                <div class="task-header">
                    <div class="task-icon-wrapper">
                        ${task.is_pinned ? '<span class="pin-badge-inline">📌</span>' : ''}
                        <div class="task-icon">${taskIcon}</div>
                    </div>
                    <div class="task-info">
                        <div class="task-title">
                            ${task.task_name}
                            <span class="task-type-badge">${taskTypeText}</span>
                        </div>
                        <div class="task-description">${description}</div>
                    </div>
                </div>
                
                <div class="task-actions">
                    ${isCompleted ? 
                        '<button class="task-btn task-btn-completed" disabled><img src="/img/payment-success.svg" alt="✓" style="width: 14px; height: 14px; vertical-align: middle; margin-left: 2px;"> مكتمل</button>' :
                        `
                        <button class="task-btn task-btn-subscribe" onclick="TasksModule.openTaskLink('${task.task_link}', ${task.id})">
                            <img src="/img/links.png" alt="اشتراك" style="width: 16px; height: 16px; vertical-align: middle; margin-left: 4px;"> اشتراك
                        </button>
                        <button class="task-btn task-btn-verify" onclick="TasksModule.verifyTask(${task.id})">
                            <img src="/img/payment-success.svg" alt="تحقق" style="width: 16px; height: 16px; vertical-align: middle; margin-left: 4px;"> تحقق
                        </button>
                        `
                    }
                </div>
            </div>
        `;
    },
    
    openTaskLink(link, taskId) {
        console.log(`📲 Opening task ${taskId}: ${link}`);
        
        // Open link in Telegram or external browser
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.openLink(link);
        } else {
            window.open(link, '_blank');
        }
        
        // Save that user clicked
        this.markTaskAsClicked(taskId);
    },
    
    async markTaskAsClicked(taskId) {
        try {
            const userId = TelegramApp.getUserId();
            await API.request(`/tasks/${taskId}/click`, 'POST', {
                user_id: userId
            });
            DebugError.add(`✅ Task ${taskId} marked as clicked`, 'info');
        } catch (error) {
            DebugError.add(`Error marking task as clicked: ${error.message}`, 'error', error);
        }
    },
    
    async verifyTask(taskId) {
        const btn = event.target;
        const originalText = btn.innerHTML;
        
        btn.disabled = true;
        btn.innerHTML = '⏳ جاري التحقق...';
        
        try {
            const userId = TelegramApp.getUserId();
            DebugError.add(`🔍 Verifying task ${taskId} for user ${userId}...`, 'info');
            
            const data = await API.request(`/tasks/${taskId}/verify`, 'POST', {
                user_id: userId
            });
            
            if (data.success) {
                // Task completed successfully
                DebugError.add(`✅ Task ${taskId} verified successfully`, 'info', data);
                showToast(data.message || `<img src="/img/payment-success.svg" style="width: 16px; height: 16px; vertical-align: middle;"> تم إكمال المهمة! +${data.reward_spins} دورة`, 'success');
                
                // Reload tasks and user data
                await this.loadCompletedTasks();
                this.renderTasks();
                this.updateProgress();
                
                // Update user spins
                if (window.loadUserData) {
                    await loadUserData();
                }
            } else {
                DebugError.add(`❌ Task ${taskId} verification failed`, 'warn', data);
                showToast(data.message || '<img src="/img/payment-failure.svg" style="width: 16px; height: 16px; vertical-align: middle;"> لم يتم التحقق. تأكد من اشتراكك!', 'error');
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        } catch (error) {
            DebugError.add(`Error verifying task: ${error.message}`, 'error', error);
            showToast('<img src="/img/payment-failure.svg" style="width: 16px; height: 16px; vertical-align: middle;"> حدث خطأ في التحقق', 'error');
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    },
    
    updateProgress() {
        const totalEl = document.getElementById('total-tasks-count');
        const completedEl = document.getElementById('completed-tasks-count');
        const progressFill = document.getElementById('tasks-progress-fill');
        
        if (!totalEl || !completedEl || !progressFill) return;
        
        const total = this.tasks.length;
        const completed = this.completedTasks.length;
        const percentage = total > 0 ? (completed / total) * 100 : 0;
        
        // حساب المتبقي للفة القادمة (كل 5 مهمات = لفة)
        const remaining = 5 - (completed % 5);
        const remainingEl = document.getElementById('tasks-remaining');
        if (remainingEl) {
            remainingEl.textContent = remaining;
        }
        
        totalEl.textContent = total;
        completedEl.textContent = completed;
        progressFill.style.width = `${percentage}%`;
    },
    
    attachEventListeners() {
        // Event listeners already attached via onclick in HTML
    }
};

// Export for use in other modules
window.TasksModule = TasksModule;
