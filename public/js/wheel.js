// ═══════════════════════════════════════════════════════════════
// 🎰 WHEEL OF FORTUNE - عجلة الحظ
// ═══════════════════════════════════════════════════════════════

class WheelOfFortune {
    constructor(canvasId, prizes) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.prizes = prizes;
        this.rotation = 0;
        this.isSpinning = false;
        this.spinButton = document.getElementById('spin-button');
        
        // إعدادات العجلة
        this.centerX = this.canvas.width / 2;
        this.centerY = this.canvas.height / 2;
        this.radius = Math.min(this.centerX, this.centerY) - 10;
        
        // Sound effects
        this.sounds = {
            spin: null, // يمكن إضافة صوت لاحقاً
            win: null
        };
        
        // رسم العجلة الأولية
        this.draw();
        
        // إضافة مستمع للنقر
        this.spinButton.addEventListener('click', () => this.spin());
    }
    
    // ═══════════════════════════════════════════════════════════
    // 🔊 SOUND EFFECTS
    // ═══════════════════════════════════════════════════════════
    
    playSound(type) {
        // Placeholder for sound effects
        // يمكن إضافة أصوات لاحقاً
        if (this.sounds[type]) {
            try {
                this.sounds[type].currentTime = 0;
                this.sounds[type].play();
            } catch (e) {
                console.log('Sound play failed:', e);
            }
        }
    }
    
    // ═══════════════════════════════════════════════════════════
    // 🎨 DRAWING
    // ═══════════════════════════════════════════════════════════
    
    draw() {
        const { ctx, centerX, centerY, radius, prizes, rotation } = this;
        
        // مسح الـ canvas
        ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Add subtle shadow to canvas
        ctx.shadowColor = 'rgba(0, 0, 0, 0.3)';
        ctx.shadowBlur = 20;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 5;
        
        // حساب زاوية كل قطاع
        const anglePerSegment = (2 * Math.PI) / prizes.length;
        
        // رسم القطاعات
        prizes.forEach((prize, index) => {
            const startAngle = rotation + (index * anglePerSegment);
            const endAngle = startAngle + anglePerSegment;
            
            // رسم القطاع
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius, startAngle, endAngle);
            ctx.lineTo(centerX, centerY);
            ctx.fillStyle = prize.color;
            ctx.fill();
            
            // إضافة حدود
            ctx.strokeStyle = '#0d1117';
            ctx.lineWidth = 3;
            ctx.stroke();
            
            // رسم النص
            ctx.save();
            ctx.translate(centerX, centerY);
            ctx.rotate(startAngle + anglePerSegment / 2);
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 14px Arial';
            ctx.shadowColor = 'rgba(0, 0, 0, 0.5)';
            ctx.shadowBlur = 4;
            ctx.fillText(prize.name, radius * 0.65, 0);
            ctx.restore();
        });
        
        // رسم الدائرة الخارجية
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
        ctx.strokeStyle = '#ffa500';
        ctx.lineWidth = 5;
        ctx.stroke();
        
        // رسم الدائرة الداخلية (للزر)
        ctx.beginPath();
        ctx.arc(centerX, centerY, 50, 0, 2 * Math.PI);
        ctx.fillStyle = '#0d1117';
        ctx.fill();
        ctx.strokeStyle = '#ffa500';
        ctx.lineWidth = 4;
        ctx.stroke();
    }
    
    // ═══════════════════════════════════════════════════════════
    // 🎲 SPINNING LOGIC
    // ═══════════════════════════════════════════════════════════
    
    async spin() {
        // التحقق من إمكانية اللف
        const canSpin = UserState.canSpin();
        if (!canSpin.can) {
            showToast(canSpin.reason, 'error');
            TelegramApp.hapticFeedback('error');
            return;
        }
        
        // التحقق من Rate Limiting
        if (!RateLimiter.check('spin', 10, 60000)) {
            showToast('الكثير من المحاولات! انتظر دقيقة.', 'error');
            return;
        }
        
        // قفل اللف
        UserState.lockSpin();
        this.isSpinning = true;
        this.spinButton.disabled = true;
        this.spinButton.classList.add('spinning');
        
        // اهتزاز خفيف
        TelegramApp.hapticFeedback('light');
        
        // إظهار Loading
        showLoading(true);
        
        try {
            // طلب اللف من السيرفر أولاً
            console.log('🎲 Requesting spin from server...');
            const response = await API.spinWheel(TelegramApp.getUserId());
            
            if (!response.success) {
                throw new Error(response.error || 'فشل اللف');
            }
            
            const { prize, new_balance, new_spins } = response.data;
            console.log('🎁 Server response:', prize);
            
            // إخفاء Loading
            showLoading(false);
            
            // الآن نبدأ دوران العجلة بناءً على نتيجة السيرفر
            
            // الآن نبدأ دوران العجلة بناءً على نتيجة السيرفر
            // حساب زاوية الدوران للجائزة
            // نبحث عن الجائزة بناءً على amount بدلاً من الاسم لضمان الدقة
            let prizeIndex = -1;
            
            // إذا كانت الجائزة "حظ أوفر" (amount = 0 واسم يحتوي على "حظ")
            if (prize.amount === 0 && (prize.name.includes('حظ') || prize.name.includes('أوفر'))) {
                prizeIndex = this.prizes.findIndex(p => p.amount === 0 && (p.name.includes('حظ') || p.name.includes('أوفر')));
            } else {
                // ابحث عن الجائزة بناءً على المبلغ
                prizeIndex = this.prizes.findIndex(p => Math.abs(p.amount - prize.amount) < 0.001);
            }
            
            if (prizeIndex === -1) {
                console.error('Prize not found in wheel! Prize:', prize, 'Available prizes:', this.prizes);
                throw new Error('الجائزة غير موجودة في العجلة');
            }
            
            console.log('🎯 Prize matched:', {
                serverPrize: prize,
                wheelPrize: this.prizes[prizeIndex],
                prizeIndex
            });
            
            const anglePerSegment = (2 * Math.PI) / this.prizes.length;
            
            // الزاوية الحالية (مطبعة)
            const currentRotation = this.rotation % (2 * Math.PI);
            
            // حساب الزاوية المستهدفة بدقة
            // المؤشر في الأعلى (الزاوية 0)، نريد أن يكون مركز الجائزة عند الأعلى
            const prizeAngle = prizeIndex * anglePerSegment;
            const targetAngle = (2 * Math.PI) - prizeAngle - (anglePerSegment / 2);
            
            // حساب أقصر مسافة للوصول للهدف
            let angleDiff = targetAngle - currentRotation;
            while (angleDiff < 0) angleDiff += 2 * Math.PI;
            while (angleDiff >= 2 * Math.PI) angleDiff -= 2 * Math.PI;
            
            // عدد الدورات الإضافية (5-7 دورات)
            const extraRotations = 5 + Math.floor(Math.random() * 3);
            const totalRotation = (extraRotations * 2 * Math.PI) + angleDiff;
            
            console.log('Spin calculation:', {
                prizeName: prize.name,
                prizeIndex,
                currentRotation: (currentRotation * 180 / Math.PI).toFixed(2) + '°',
                targetAngle: (targetAngle * 180 / Math.PI).toFixed(2) + '°',
                angleDiff: (angleDiff * 180 / Math.PI).toFixed(2) + '°',
                extraRotations,
                totalRotation: (totalRotation * 180 / Math.PI).toFixed(2) + '°'
            });
            
            // تدوير العجلة
            await this.animateSpin(totalRotation);
            
            // اهتزاز قوي عند الفوز
            if (prize.amount > 0) {
                TelegramApp.hapticFeedback('heavy');
            }
            
            // تحديث الحالة
            UserState.update({
                balance: new_balance,
                available_spins: new_spins,
                total_spins: UserState.get('total_spins') + 1
            });
            
            // عرض النتيجة
            this.showResult(prize);
            
            // تحديث UI
            updateUI();
            
            // إضافة للتاريخ
            addWinToHistory(prize);
            
        } catch (error) {
            console.error('Spin Error:', error);
            showLoading(false);
            showToast(error.message || 'حدث خطأ أثناء اللف', 'error');
            TelegramApp.hapticFeedback('error');
        } finally {
            // فك القفل
            UserState.unlockSpin();
            this.isSpinning = false;
            this.spinButton.disabled = false;
            this.spinButton.classList.remove('spinning');
        }
    }
    
    // ═══════════════════════════════════════════════════════════
    // 🎬 ANIMATION
    // ═══════════════════════════════════════════════════════════
    
    animateSpin(totalRotation) {
        return new Promise((resolve) => {
            const startTime = Date.now();
            const duration = CONFIG.SPIN_DURATION;
            const startRotation = this.rotation;
            
            // Play spinning sound if available
            this.playSound('spin');
            
            const animate = () => {
                const now = Date.now();
                const elapsed = now - startTime;
                const progress = Math.min(elapsed / duration, 1);
                
                // Smooth easing function (ease-out cubic) بدون bounce
                const easeOut = 1 - Math.pow(1 - progress, 3);
                
                // تحديث الدوران
                this.rotation = startRotation + (totalRotation * easeOut);
                
                // رسم العجلة
                this.draw();
                
                if (progress < 1) {
                    requestAnimationFrame(animate);
                } else {
                    // تطبيع الزاوية
                    this.rotation = this.rotation % (2 * Math.PI);
                    resolve();
                }
            };
            
            animate();
        });
    }
    
    // ═══════════════════════════════════════════════════════════
    // 🎉 RESULT DISPLAY
    // ═══════════════════════════════════════════════════════════
    
    showResult(prize) {
        const resultDiv = document.getElementById('spin-result');
        const resultText = document.getElementById('result-text');
        const resultAmount = document.getElementById('result-amount');
        
        if (prize.amount > 0) {
            resultText.textContent = '🎉 تهانينا!';
            // إضافة أيقونة TON
            const tonIcon = '<img src="img/Ton.png" alt="TON" class="ton-icon">';
            resultAmount.innerHTML = `ربحت ${prize.amount} ${tonIcon}`;
            resultDiv.style.borderColor = '#3fb950';
        } else {
            resultText.textContent = '😢 حظ أوفر المرة القادمة!';
            resultAmount.textContent = prize.name;
            resultDiv.style.borderColor = '#808080';
        }
        
        resultDiv.classList.remove('hidden');
        addAnimation(resultDiv, 'bounce');
        
        // إخفاء بعد 5 ثواني
        setTimeout(() => {
            resultDiv.classList.add('hidden');
        }, 5000);
        
        // عرض Modal للفوز الكبير
        if (prize.amount >= 0.5) {
            showWinModal(prize);
        }
    }
}

// ═══════════════════════════════════════════════════════════════
// 🎊 WIN MODAL
// ═══════════════════════════════════════════════════════════════

function showWinModal(prize) {
    const modal = document.getElementById('win-modal');
    const title = document.getElementById('modal-win-title');
    const amount = document.getElementById('modal-win-amount');
    
    title.textContent = '🎊 فوز عظيم!';
    // إضافة أيقونة TON
    const tonIcon = '<img src="img/Ton.png" alt="TON" class="ton-icon">';
    amount.innerHTML = `ربحت ${prize.amount} ${tonIcon}`;
    
    modal.classList.add('active');
    
    // صوت الفوز (إن وجد)
    TelegramApp.hapticFeedback('heavy');
}

function closeWinModal() {
    const modal = document.getElementById('win-modal');
    modal.classList.remove('active');
}

// ═══════════════════════════════════════════════════════════════
// 📜 SPIN HISTORY
// ═══════════════════════════════════════════════════════════════

async function loadSpinHistory() {
    try {
        const response = await API.getSpinHistory(TelegramApp.getUserId(), 5);
        
        if (response.success) {
            const historyList = document.getElementById('recent-wins-list');
            historyList.innerHTML = '';
            
            if (response.data.length === 0) {
                historyList.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">لا توجد أرباح بعد. جرب حظك الآن!</p>';
                return;
            }
            
            response.data.forEach(spin => {
                const winItem = document.createElement('div');
                winItem.className = 'win-item';
                
                const leftDiv = document.createElement('div');
                const nameSpan = document.createElement('div');
                nameSpan.className = 'win-item-name';
                nameSpan.textContent = spin.prize_name;
                
                const timeSpan = document.createElement('div');
                timeSpan.className = 'win-item-time';
                timeSpan.textContent = formatDate(spin.spin_time);
                
                leftDiv.appendChild(nameSpan);
                leftDiv.appendChild(timeSpan);
                
                const amountSpan = document.createElement('div');
                amountSpan.className = 'win-item-amount';
                amountSpan.textContent = spin.prize_amount > 0 ? `+${spin.prize_amount} TON` : '---';
                
                winItem.appendChild(leftDiv);
                winItem.appendChild(amountSpan);
                
                historyList.appendChild(winItem);
            });
        }
    } catch (error) {
        console.error('Error loading spin history:', error);
    }
}

function addWinToHistory(prize) {
    const historyList = document.getElementById('recent-wins-list');
    
    // إزالة رسالة "لا توجد أرباح"
    if (historyList.querySelector('p')) {
        historyList.innerHTML = '';
    }
    
    const winItem = document.createElement('div');
    winItem.className = 'win-item';
    
    const leftDiv = document.createElement('div');
    const nameSpan = document.createElement('div');
    nameSpan.className = 'win-item-name';
    nameSpan.textContent = prize.name;
    
    const timeSpan = document.createElement('div');
    timeSpan.className = 'win-item-time';
    timeSpan.textContent = 'الآن';
    
    leftDiv.appendChild(nameSpan);
    leftDiv.appendChild(timeSpan);
    
    const amountSpan = document.createElement('div');
    amountSpan.className = 'win-item-amount';
    amountSpan.textContent = prize.amount > 0 ? `+${prize.amount} TON` : '---';
    
    winItem.appendChild(leftDiv);
    winItem.appendChild(amountSpan);
    
    // إضافة في البداية
    historyList.insertBefore(winItem, historyList.firstChild);
    
    // حذف القديم (أكثر من 5)
    while (historyList.children.length > 5) {
        historyList.removeChild(historyList.lastChild);
    }
    
    // Animation
    addAnimation(winItem, 'fadeIn');
}

// ═══════════════════════════════════════════════════════════════
// 🎯 EXPORTS
// ═══════════════════════════════════════════════════════════════

window.WheelOfFortune = WheelOfFortune;
window.closeWinModal = closeWinModal;
window.loadSpinHistory = loadSpinHistory;

console.log('🎰 Wheel of Fortune Loaded');
