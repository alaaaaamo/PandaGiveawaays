// ═══════════════════════════════════════════════════════════════
// 🎰 WHEEL OF FORTUNE - عجلة الحظ
// ═══════════════════════════════════════════════════════════════

class WheelOfFortune {
    constructor(canvasId, prizes) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            this.showError('❌ عجلة الحظ غير متاحة');
            return;
        }
        
        this.ctx = this.canvas.getContext('2d');
        if (!this.ctx) {
            this.showError('❌ لا يمكن رسم العجلة');
            return;
        }
        
        if (!prizes || prizes.length === 0) {
            this.showError('❌ لا توجد جوائز للعجلة');
            return;
        }
        
        this.prizes = prizes;
        this.rotation = 0;
        this.isSpinning = false;
        this.spinButton = document.getElementById('spin-button');
        
        if (!this.spinButton) {
            this.showError('⚠️ زر اللف غير متاح');
        }
        
        // 🎨 إصلاح البكسلة - High DPI Support
        this.setupHighDPI();
        
        // التحقق من نجح إعداد الأبعاد
        if (!this.centerX || !this.centerY || !this.radius || this.radius <= 0) {
            this.showError('❌ فشل في إعداد أبعاد العجلة');
            return;
        }
        
        // Sound effects
        this.sounds = {
            spin: null, // يمكن إضافة صوت لاحقاً
            win: null
        };
        
        // رسم العجلة الأولية مع تأخير صغير لضمان DOM جاهز
        setTimeout(() => {
            try {
                this.draw();
            } catch (drawError) {
                this.showError('❌ خطأ في رسم العجلة: ' + drawError.message);
                return;
            }
        }, 100);
        
        // إضافة مستمع للنقر
        if (this.spinButton) {
            this.spinButton.addEventListener('click', () => this.spin());
        }
        
        this.showSuccess('✅ تم تحميل عجلة الحظ بنجاح');
    }
    
    // ═══════════════════════════════════════════════════════════
    // 📱 VISUAL ERROR HANDLING
    // ═══════════════════════════════════════════════════════
    
    showError(message) {
        if (typeof showToast !== 'undefined') {
            showToast(message, 'error');
        } else {
            // Fallback - عرض على العجلة مباشرة
            const wheelContainer = document.querySelector('.wheel-container');
            if (wheelContainer) {
                wheelContainer.innerHTML = `
                    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; 
                        height: 300px; background: #1a1a1a; border-radius: 20px; padding: 20px; text-align: center;">
                        <div style="font-size: 60px; margin-bottom: 20px;">😔</div>
                        <h3 style="color: #ff4444; margin-bottom: 10px;">خطأ في عجلة الحظ</h3>
                        <p style="color: #999; font-size: 14px;">${message}</p>
                    </div>
                `;
            }
        }
    }
    
    showSuccess(message) {
        if (typeof showToast !== 'undefined') {
            showToast(message, 'success');
        }
    }
    
    
    // ═══════════════════════════════════════════════════════
    // 🎨 HIGH DPI SUPPORT - إصلاح البكسلة
    // ═══════════════════════════════════════════════════════
    
    setupHighDPI() {
        try {
            const dpr = window.devicePixelRatio || 1;
            const rect = this.canvas.getBoundingClientRect();
            
            // حفظ الأبعاد الأصلية - استخدم الأبعاد من HTML إذا لم تكن موجودة في CSS
            let width = rect.width;
            let height = rect.height;
            
            // إذا لم تكن الأبعاد محددة في CSS، استخدم أبعاد HTML
            if (!width || width < 50) {
                width = this.canvas.getAttribute('width') || 350;
            }
            if (!height || height < 50) {
                height = this.canvas.getAttribute('height') || 350;
            }
            
            // تحويل إلى رقم
            width = Number(width);
            height = Number(height);
            
            // التحقق من صحة الأبعاد
            if (!width || !height || width < 50 || height < 50) {
                this.showError('❌ أبعاد العجلة صغيرة جداً');
                return;
            }
            
            // تعيين حجم canvas الداخلي بناءً على DPI
            this.canvas.width = width * dpr;
            this.canvas.height = height * dpr;
            
            // تعيين حجم العرض CSS
            this.canvas.style.width = width + 'px';
            this.canvas.style.height = height + 'px';
            
            // تكبير السياق لمطابقة DPI
            this.ctx.scale(dpr, dpr);
            
            // تحديث إعدادات العجلة بعد التكبير مع حماية من القيم السالبة
            this.centerX = width / 2;
            this.centerY = height / 2;
            const calculatedRadius = Math.min(this.centerX, this.centerY) - 10;
            
            // التأكد من أن نصف القطر موجب دائماً
            this.radius = Math.max(calculatedRadius, 30); // الحد الأدنى 30px
            
            // التحقق النهائي من صحة القيم
            if (this.radius <= 0 || !this.centerX || !this.centerY) {
                this.showError('❌ لا يمكن حساب أبعاد العجلة');
                return;
            }
            
            this.showSuccess('✅ تم إعداد أبعاد العجلة بنجاح');
            
        } catch (error) {
            this.showError('❌ خطأ في إعداد العجلة: ' + error.message);
        }
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
                // Sound play failed silently
            }
        }
    }
    
    // ═══════════════════════════════════════════════════════════
    // 🎨 DRAWING
    // ═══════════════════════════════════════════════════════════
    
    draw() {
        const { ctx, centerX, centerY, radius, prizes, rotation } = this;
        
        // معالجة البيانات قبل الرسم
        if (!ctx || !centerX || !centerY || !radius || radius <= 0) {
            this.showError('❌ بيانات العجلة غير صالحة للرسم');
            return;
        }
        
        if (!prizes || prizes.length === 0) {
            this.showError('❌ لا توجد جوائز للعرض');
            return;
        }
        
        // مسح الـ canvas
        const canvasWidth = this.canvas.width / (window.devicePixelRatio || 1);
        const canvasHeight = this.canvas.height / (window.devicePixelRatio || 1);
        ctx.clearRect(0, 0, canvasWidth, canvasHeight);
        
        // حساب زاوية كل قطاع
        const anglePerSegment = (2 * Math.PI) / prizes.length;
        
        // 🎨 ألوان زيتية محسنة - بالترتيب للجوائز
        const oilColors = [
            { start: '#9370db', end: '#6a4fb5' },  // Purple (0.01)
            { start: '#00bfff', end: '#0080cc' },  // Blue (0.05)
            { start: '#ffa500', end: '#cc7700' },  // Orange (0.1)
            { start: '#32cd32', end: '#228b22' },  // Green (0.5)
            { start: '#ff1493', end: '#cc0066' },  // Pink (1.0)
            { start: '#808080', end: '#404040' }   // Gray (حظ أوفر)
        ];
        
        // رسم القطاعات بـ Gradients
        prizes.forEach((prize, index) => {
            try {
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
                
                // رسم القطاع مع حماية إضافية
                ctx.beginPath();
                if (radius > 0 && centerX > 0 && centerY > 0) {
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
                }
                
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
                
            } catch (segmentError) {
                // تسجيل الخطأ بصمت ومتابعة رسم باقي القطاعات
            }
        });
        
        // 🌟 رسم الإطار الذهبي الناعم
        try {
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
        } catch (borderError) {
            // في حالة خطأ الحدود، لا نفعل شيء (العجلة ستكون بدون حدود فقط)
        }
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
            // Requesting spin from server...
            const response = await API.spinWheel(TelegramApp.getUserId());
            
            if (!response.success) {
                throw new Error(response.error || 'فشل اللف');
            }
            
            const { prize, new_balance, new_spins } = response.data;
            // استلام نتيجة اللفة من الخادم
            
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
            
            // Prize matched successfully - server response processed
            
            const anglePerSegment = (2 * Math.PI) / this.prizes.length;
            
            // الزاوية الحالية (منظمة)
            const currentRotation = this.rotation % (2 * Math.PI);
            
            // 🎯 حساب الزاوية المستهدفة بدقة
            // المؤشر في الأعلى (270 درجة = -90 درجة = 3π/2)
            // في Canvas، الزاوية 0 على اليمين، وتزيد عكس اتجاه عقارب الساعة
            // الأعلى = -π/2 أو 3π/2
            
            // زاوية بداية الجائزة من الزاوية الأولى (0)
            const prizeStartAngle = prizeIndex * anglePerSegment;
            
            // مركز الجائزة = بداية الجائزة + نصف حجم القطاع
            const prizeCenterAngle = prizeStartAngle + (anglePerSegment / 2);
            
            // المؤشر عند الأعلى (3π/2 أو -π/2)
            const pointerAngle = -Math.PI / 2;
            
            // الزاوية المطلوبة = نريد أن prizeCenterAngle يكون عند المؤشر
            // rotation + prizeCenterAngle = pointerAngle
            // rotation = pointerAngle - prizeCenterAngle
            let targetAngle = pointerAngle - prizeCenterAngle;
            
            // تطبيع الزاوية لتكون بين 0 و 2π
            while (targetAngle < 0) targetAngle += 2 * Math.PI;
            while (targetAngle >= 2 * Math.PI) targetAngle -= 2 * Math.PI;
            
            // حساب أقصر مسافة للوصول للهدف
            let angleDiff = targetAngle - currentRotation;
            
            // تطبيع الزاوية لتكون موجبة
            while (angleDiff < 0) angleDiff += 2 * Math.PI;
            while (angleDiff >= 2 * Math.PI) angleDiff -= 2 * Math.PI;
            
            // عدد الدورات الإضافية (5-7 دورات)
            const extraRotations = 5 + Math.floor(Math.random() * 3);
            const totalRotation = (extraRotations * 2 * Math.PI) + angleDiff;
            
            // Spin calculation completed successfully
            
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
                    
                    // 🔍 تحقق من الجائزة التي توقفت عندها العجلة
                    const finalRotation = this.rotation;
                    const anglePerSegment = (2 * Math.PI) / this.prizes.length;
                    const pointerAngle = -Math.PI / 2;
                    
                    // حساب أي قطاع تحت المؤشر
                    let adjustedAngle = (pointerAngle - finalRotation) % (2 * Math.PI);
                    if (adjustedAngle < 0) adjustedAngle += 2 * Math.PI;
                    
                    const stoppedIndex = Math.floor(adjustedAngle / anglePerSegment);
                    const stoppedPrize = this.prizes[stoppedIndex];
                    
                    // Wheel stopped successfully 
                    
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

// 🎰 Wheel of Fortune Loaded Successfully
