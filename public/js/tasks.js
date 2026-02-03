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
            const response = await fetch('/api/tasks');
            const data = await response.json();
            
            if (data.success && data.tasks) {
                this.tasks = data.tasks;
                console.log(`✅ Loaded ${this.tasks.length} tasks`);
            } else {
                console.error('❌ Failed to load tasks:', data.message);
                this.tasks = [];
            }
        } catch (error) {
            console.error('❌ Error loading tasks:', error);
            this.tasks = [];
        }
    },
    
    async loadCompletedTasks() {
        try {
            const userId = TelegramApp.getUserId();
            const response = await fetch(`/api/user/${userId}/completed-tasks`);
            const data = await response.json();
            
            if (data.success && data.completed_tasks) {
                // تحويل إلى array من الـ IDs فقط
                this.completedTasks = data.completed_tasks.map(t => t.task_id);
                console.log(`✅ Loaded ${this.completedTasks.length} completed tasks`);
            } else {
                this.completedTasks = [];
            }
        } catch (error) {
            console.error('❌ Error loading completed tasks:', error);
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
                ${task.is_pinned ? '<div class="pin-badge">📌</div>' : ''}
                
                <div class="task-header">
                    <div class="task-icon">${taskIcon}</div>
                    <div class="task-info">
                        <div class="task-title">
                            ${task.task_name}
                            <span class="task-type-badge">${taskTypeText}</span>
                        </div>
                        <div class="task-description">${description}</div>
                    </div>
                </div>
                
                <div class="task-reward">
                    <span>🎯</span>
                    <span>${progress}/5 للحصول على دورة</span>
                </div>
                
                <div class="task-actions">
                    ${isCompleted ? 
                        '<button class="task-btn task-btn-completed" disabled>✅ مكتمل</button>' :
                        `
                        <button class="task-btn task-btn-subscribe" onclick="TasksModule.openTaskLink('${task.task_link}', ${task.id})">
                            📲 اشتراك
                        </button>
                        <button class="task-btn task-btn-verify" onclick="TasksModule.verifyTask(${task.id})">
                            ✔️ تحقق
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
            await fetch(`/api/tasks/${taskId}/click`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({user_id: userId})
            });
        } catch (error) {
            console.error('Error marking task as clicked:', error);
        }
    },
    
    async verifyTask(taskId) {
        const btn = event.target;
        const originalText = btn.innerHTML;
        
        btn.disabled = true;
        btn.innerHTML = '⏳ جاري التحقق...';
        
        try {
            const userId = TelegramApp.getUserId();
            const response = await fetch(`/api/tasks/${taskId}/verify`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({user_id: userId})
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Task completed successfully
                showToast(data.message || `✅ تم إكمال المهمة! +${data.reward_spins} دورة`, 'success');
                
                // Reload tasks and user data
                await this.loadCompletedTasks();
                this.renderTasks();
                this.updateProgress();
                
                // Update user spins
                if (window.loadUserData) {
                    await loadUserData();
                }
            } else {
                showToast(data.message || '❌ لم يتم التحقق. تأكد من اشتراكك!', 'error');
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        } catch (error) {
            console.error('Error verifying task:', error);
            showToast('❌ حدث خطأ في التحقق', 'error');
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
        
        totalEl.textContent = total;
        completedEl.textContent = completed;
        progressFill.style.width = `${percentage}%`;
    },
    
    attachEventListeners() {
        // Event listeners already attached via onclick in HTML
    }
};

// Helper function for toast notifications
function showToast(message, type = 'info') {
    if (window.Telegram && window.Telegram.WebApp) {
        window.Telegram.WebApp.showAlert(message);
    } else {
        alert(message);
    }
}

// Export for use in other modules
window.TasksModule = TasksModule;
