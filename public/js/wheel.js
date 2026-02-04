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
        
        // 🎨 إصلاح البكسلة - High DPI Support
        this.setupHighDPI();
        
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
    // 🎨 HIGH DPI SUPPORT - إصلاح البكسلة
    // ═══════════════════════════════════════════════════════════
    
    setupHighDPI() {
        const dpr = window.devicePixelRatio || 1;
        const rect = this.canvas.getBoundingClientRect();
        
        // حفظ الأبعاد الأصلية
        const width = rect.width;
        const height = rect.height;
        
        // تعيين حجم canvas الداخلي بناءً على DPI
        this.canvas.width = width * dpr;
        this.canvas.height = height * dpr;
        
        // تعيين حجم العرض CSS
        this.canvas.style.width = width + 'px';
        this.canvas.style.height = height + 'px';
        
        // تكبير السياق لمطابقة DPI
        this.ctx.scale(dpr, dpr);
        
        // تحديث إعدادات العجلة بعد التكبير
        this.centerX = width / 2;
        this.centerY = height / 2;
        this.radius = Math.min(this.centerX, this.centerY) - 10;
        
        console.log('🎨 High DPI setup:', { dpr, width, height });
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
        const canvasWidth = this.canvas.width / (window.devicePixelRatio || 1);
        const canvasHeight = this.canvas.height / (window.devicePixelRatio || 1);
        ctx.clearRect(0, 0, canvasWidth, canvasHeight);
        
        // حساب زاوية كل قطاع
        const anglePerSegment = (2 * Math.PI) / prizes.length;
        
        // 🎨 ألوان زيتية محسنة
        const oilColors = [
            { start: '#1E5F63', end: '#0F3438' },  // Teal Oil
            { start: '#3A2E5C', end: '#1F1836' },  // Purple Oil
            { start: '#1F3B4D', end: '#0F1D26' },  // Deep Blue
            { start: '#2E2A24', end: '#1A1714' },  // Charcoal
            { start: '#9E7C2F', end: '#6B5320' },  // Dark Gold
            { start: '#4A2C2A', end: '#2A1715' }   // Brown Oil
        ];
        
        // رسم القطاعات بـ Gradients
        prizes.forEach((prize, index) => {
            const startAngle = rotation + (index * anglePerSegment);
            const endAngle = startAngle + anglePerSegment;
            
            // حساب نقاط الـ gradient
            const gradStartX = centerX + Math.cos(startAngle) * radius * 0.3;
            const gradStartY = centerY + Math.sin(startAngle) * radius * 0.3;
            const gradEndX = centerX + Math.cos(endAngle) * radius * 0.9;
            const gradEndY = centerY + Math.sin(endAngle) * radius * 0.9;
            
            // إنشاء gradient لكل قطاع
            const gradient = ctx.createLinearGradient(gradStartX, gradStartY, gradEndX, gradEndY);
            const colorPair = oilColors[index % oilColors.length];
            gradient.addColorStop(0, colorPair.start);
            gradient.addColorStop(1, colorPair.end);
            
            // رسم القطاع
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius, startAngle, endAngle);
            ctx.lineTo(centerX, centerY);
            ctx.fillStyle = gradient;
            ctx.fill();
            
            // إضافة حدود ناعمة
            ctx.strokeStyle = '#000000';
            ctx.lineWidth = 2;
            ctx.globalAlpha = 0.3;
            ctx.stroke();
            ctx.globalAlpha = 1;
            
            // رسم النص بخط محسن
            ctx.save();
            ctx.translate(centerX, centerY);
            ctx.rotate(startAngle + anglePerSegment / 2);
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            
            // ظل النص
            ctx.shadowColor = 'rgba(0, 0, 0, 0.8)';
            ctx.shadowBlur = 6;
            ctx.shadowOffsetX = 0;
            ctx.shadowOffsetY = 2;
            
            // النص نفسه
            ctx.fillStyle = '#F2F2F2';
            ctx.font = '600 16px Inter, system-ui, sans-serif';
            ctx.fillText(prize.name, radius * 0.65, 0);
            ctx.restore();
        });
        
        // 🌟 رسم الإطار الذهبي الناعم
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
        ctx.strokeStyle = '#C9A24D';
        ctx.lineWidth = 6;
        ctx.shadowColor = 'rgba(201, 162, 77, 0.6)';
        ctx.shadowBlur = 12;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 0;
        ctx.stroke();
        
        // إطار داخلي إضافي
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius - 3, 0, 2 * Math.PI);
        ctx.strokeStyle = '#E5C76A';
        ctx.lineWidth = 2;
        ctx.shadowBlur = 6;
        ctx.stroke();
        
        // 🎯 رسم الدائرة الداخلية (للزر) مع gradient
        ctx.shadowColor = 'rgba(0, 0, 0, 0.5)';
        ctx.shadowBlur = 15;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 3;
        
        const innerGradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, 50);
        innerGradient.addColorStop(0, '#1a1f2e');
        innerGradient.addColorStop(1, '#0d1117');
        
        ctx.beginPath();
        ctx.arc(centerX, centerY, 50, 0, 2 * Math.PI);
        ctx.fillStyle = innerGradient;
        ctx.fill();
        
        // إطار ذهبي للدائرة الداخلية
        ctx.strokeStyle = '#C9A24D';
        ctx.lineWidth = 3;
        ctx.shadowBlur = 8;
        ctx.shadowColor = 'rgba(201, 162, 77, 0.5)';
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
            
            // الزاوية الحالية (منظمة)
            const currentRotation = this.rotation % (2 * Math.PI);
            
            // 🎯 حساب الزاوية المستهدفة بدقة
            // المؤشر في الأعلى (π/2 radians = 90 degrees)
            // نريد أن يكون مركز الجائزة تحت المؤشر مباشرة
            
            // زاوية بداية الجائزة
            const prizeStartAngle = prizeIndex * anglePerSegment;
            
            // مركز الجائزة = بداية الجائزة + نصف حجم القطاع
            const prizeCenterAngle = prizeStartAngle + (anglePerSegment / 2);
            
            // الزاوية المستهدفة لجعل مركز الجائزة عند المؤشر (الأعلى = π/2)
            // نحتاج إلى جعل prizeCenterAngle عند موضع المؤشر (π/2)
            const pointerAngle = Math.PI / 2; // 90 درجة (الأعلى)
            const targetAngle = pointerAngle - prizeCenterAngle;
            
            // حساب أقصر مسافة للوصول للهدف
            let angleDiff = targetAngle - currentRotation;
            
            // تطبيع الزاوية لتكون موجبة
            while (angleDiff < 0) angleDiff += 2 * Math.PI;
            while (angleDiff >= 2 * Math.PI) angleDiff -= 2 * Math.PI;
            
            // عدد الدورات الإضافية (5-7 دورات)
            const extraRotations = 5 + Math.floor(Math.random() * 3);
            const totalRotation = (extraRotations * 2 * Math.PI) + angleDiff;
            
            console.log('🎲 Spin calculation:', {
                prizeName: prize.name,
                prizeIndex,
                anglePerSegment: (anglePerSegment * 180 / Math.PI).toFixed(2) + '°',
                prizeStartAngle: (prizeStartAngle * 180 / Math.PI).toFixed(2) + '°',
                prizeCenterAngle: (prizeCenterAngle * 180 / Math.PI).toFixed(2) + '°',
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
