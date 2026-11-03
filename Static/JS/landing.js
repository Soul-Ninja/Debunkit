/**
 * DEBUNK.IT — Editorial Interactive Engine
 * Handles BS-o-Meter truth gauge, Accessible SFX, Tickers & Editorial Reviews
 */

(function () {
    'use strict';

    // =========================================================================
    // 1. SOUND FX ENGINE (DEFAULTS TO OFF, ACCESSIBLE)
    // =========================================================================
    let audioCtx = null;
    let sfxEnabled = localStorage.getItem('debunkit_sfx') === 'on'; // default OFF

    function initAudio() {
        if (!audioCtx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                audioCtx = new AudioContext();
            }
        }
        if (audioCtx && audioCtx.state === 'suspended') {
            audioCtx.resume();
        }
    }

    function playTone(freq, type, duration, gainStart = 0.12, gainEnd = 0.001) {
        if (!sfxEnabled || !audioCtx) return;
        try {
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();

            osc.type = type;
            osc.frequency.setValueAtTime(freq, audioCtx.currentTime);

            gain.gain.setValueAtTime(gainStart, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(gainEnd, audioCtx.currentTime + duration);

            osc.connect(gain);
            gain.connect(audioCtx.destination);

            osc.start();
            osc.stop(audioCtx.currentTime + duration);
        } catch (e) {
            console.debug('Audio error:', e);
        }
    }

    function playBuzzer() {
        if (!sfxEnabled || !audioCtx) return;
        try {
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.type = 'sawtooth';

            osc.frequency.setValueAtTime(280, audioCtx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(90, audioCtx.currentTime + 0.35);

            gain.gain.setValueAtTime(0.14, audioCtx.currentTime);
            gain.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + 0.35);

            osc.connect(gain);
            gain.connect(audioCtx.destination);

            osc.start();
            osc.stop(audioCtx.currentTime + 0.35);
        } catch (e) {}
    }

    function playSuccessChime() {
        if (!sfxEnabled || !audioCtx) return;
        const notes = [523.25, 659.25, 783.99, 1046.50];
        notes.forEach((freq, idx) => {
            setTimeout(() => {
                playTone(freq, 'sine', 0.2, 0.1, 0.001);
            }, idx * 60);
        });
    }

    function playRadarPing() {
        playTone(1600, 'sine', 0.1, 0.06, 0.001);
    }

    function playClick() {
        playTone(700, 'triangle', 0.03, 0.04, 0.001);
    }

    function playChime() {
        playTone(980, 'triangle', 0.12, 0.05);
    }

    // =========================================================================
    // 2. PRESET VIRAL CLAIMS FOR BS-O-METER (CLEAN TYPOGRAPHY, NO EMOJIS)
    // =========================================================================
    const VIRAL_PRESETS = [
        {
            id: 'garlic',
            btnText: 'Garlic Cures Loans & 5G',
            claim: 'Drinking boiled garlic water cures student loans and 5G radiation.',
            verdict: '100% REFUTED',
            score: '99.9%',
            tone: 'danger',
            angle: 78,
            readoutText: 'MAXIMUM CAP',
            diagnosis: 'Confirmed rumor dynamics. Boiling garlic leaves your student debt untouched while assuring social distancing through pungent breath.',
            type: 'headline'
        },
        {
            id: 'microwave',
            btnText: 'Microwave Fast-Charge',
            claim: 'Putting your iPhone in the microwave for 30 seconds supercharges the battery to 100%.',
            verdict: 'CRITICAL HAZARD',
            score: '100%',
            tone: 'danger',
            angle: 80,
            readoutText: 'HAZARDOUS BOGUS',
            diagnosis: 'Debunked by basic thermodynamics. The only outcome is destroyed circuitry and an expensive insurance deductible.',
            type: 'headline'
        },
        {
            id: 'aliens',
            btnText: 'Pyramids Alien Wi-Fi',
            claim: 'The Egyptian pyramids were ancient wireless power transmitters built by extraterrestrials.',
            verdict: 'UNFOUNDED SPECULATION',
            score: '99.8%',
            tone: 'danger',
            angle: 75,
            readoutText: 'COSMIC NONSENSE',
            diagnosis: 'Limestone masonry and human labor documented. Zero intergalactic blueprints or electronic components uncovered.',
            type: 'headline'
        },
        {
            id: 'avocado',
            btnText: 'Avocado 5G Shield',
            claim: 'Eating ground avocado pits makes the human body immune to electromagnetic Wi-Fi signals.',
            verdict: 'ORGANIC BOGUS',
            score: '96.4%',
            tone: 'danger',
            angle: 70,
            readoutText: 'GRADE-A BOLOGNA',
            diagnosis: 'Woody seed stones containing bitter tannins offer zero Faraday cage properties. Please do not damage teeth on seed stones.',
            type: 'headline'
        },
        {
            id: 'ai-laundry',
            btnText: 'AI Laundry Singularity',
            claim: 'AI models have secretly agreed to automate all laundry and fold clothes by next Tuesday.',
            verdict: 'DELUSIONAL HOPE',
            score: '50.0%',
            tone: 'sus',
            angle: 0,
            readoutText: 'WISHFUL THINKING',
            diagnosis: 'While modern models compose sonnets, robotic manipulators still struggle with cloth physics and missing laundry socks.',
            type: 'headline'
        },
        {
            id: 'water',
            btnText: 'Water Hydrates Humans',
            claim: 'Drinking clean fresh water is necessary for human hydration and organ function.',
            verdict: 'VERIFIED FACT',
            score: '0.1%',
            tone: 'legit',
            angle: -78,
            readoutText: 'CONFIRMED TRUTH',
            diagnosis: 'Established biological reality. H2O is required for mammalian cellular metabolism and kidney filtration.',
            type: 'headline'
        }
    ];

    // =========================================================================
    // 3. BS-O-METER UI CONTROLLER
    // =========================================================================
    let currentActivePreset = null;

    function renderMeterPreset(preset) {
        initAudio();

        currentActivePreset = preset;
        const needle = document.getElementById('gauge-needle');
        const score = document.getElementById('gauge-score');
        const label = document.getElementById('gauge-label');
        const roastStamp = document.getElementById('roast-stamp');
        const roastText = document.getElementById('roast-text');
        const roastCard = document.getElementById('roast-card');
        const scanFullBtn = document.getElementById('btn-scan-full');
        const customInput = document.getElementById('custom-claim-input');

        if (customInput) {
            customInput.value = preset.claim;
        }

        if (needle) {
            needle.style.transform = `rotate(${preset.angle}deg)`;
        }

        if (score) {
            score.textContent = preset.score;
            score.className = `gauge-score ${preset.tone}`;
        }

        if (label) {
            label.textContent = preset.readoutText;
        }

        if (roastStamp) {
            roastStamp.textContent = preset.verdict;
            roastStamp.className = `roast-stamp ${preset.tone}`;
        }

        if (roastText) {
            roastText.textContent = preset.diagnosis;
        }

        if (roastCard) {
            roastCard.className = `roast-card ${preset.tone}`;
        }

        if (scanFullBtn) {
            scanFullBtn.href = `/scanner?claim=${encodeURIComponent(preset.claim)}&mode=${preset.type || 'title'}`;
        }

        document.querySelectorAll('.sample-chip').forEach(chip => {
            if (chip.dataset.id === preset.id) {
                chip.classList.add('active');
                chip.setAttribute('aria-pressed', 'true');
            } else {
                chip.classList.remove('active');
                chip.setAttribute('aria-pressed', 'false');
            }
        });

        if (preset.tone === 'legit') {
            playSuccessChime();
        } else if (preset.tone === 'danger') {
            playBuzzer();
        } else {
            playRadarPing();
        }
    }

    function evaluateCustomClaim(text) {
        if (!text || text.trim().length < 5) {
            showLandingToast('Please enter at least 5 characters to analyze.');
            return;
        }

        initAudio();
        playRadarPing();

        const clean = text.toLowerCase().trim();
        let scoreVal = 85;
        let angleVal = 55;
        let verdictVal = 'HIGH SUSPICION';
        let readoutVal = 'PROBABLE BOGUS';
        let toneVal = 'danger';
        let diagVal = 'Heuristic indicators suggest unverified rumor dynamics or sensationalist phrasing. Check full citations below.';

        if (clean.includes('water') && (clean.includes('drink') || clean.includes('hydrate'))) {
            scoreVal = 0.5;
            angleVal = -75;
            verdictVal = 'VERIFIED ACCURATE';
            readoutVal = 'SOLID TRUTH';
            toneVal = 'legit';
            diagVal = 'Hydration and hydration biology confirmed by scientific consensus.';
        } else if (clean.includes('alien') || clean.includes('ufo') || clean.includes('flat earth')) {
            scoreVal = 99.8;
            angleVal = 78;
            verdictVal = 'UNVERIFIED CONSPIRACY';
            readoutVal = 'SPECULATIVE LORE';
            toneVal = 'danger';
            diagVal = 'This hypothesis relies on fringe message board discussions lacking documented evidence.';
        } else if (clean.includes('cure') || clean.includes('miracle') || clean.includes('garlic') || clean.includes('5g')) {
            scoreVal = 97.5;
            angleVal = 72;
            verdictVal = 'UNVERIFIED WELLNESS CLAIM';
            readoutVal = 'VIRAL RUMOR';
            toneVal = 'danger';
            diagVal = 'Medical assertions without clinical trials or regulatory approval.';
        } else {
            scoreVal = Math.min(99, Math.max(45, 60 + (text.length % 35)));
            angleVal = ((scoreVal / 100) * 160) - 80;
            diagVal = `Forensic analysis flags a ${scoreVal}% probability of misinformation or omission of primary context.`;
        }

        const customPreset = {
            id: 'custom',
            btnText: 'Custom Input',
            claim: text,
            verdict: verdictVal,
            score: scoreVal + '%',
            tone: toneVal,
            angle: angleVal,
            readoutText: readoutVal,
            diagnosis: diagVal,
            type: text.startsWith('http://') || text.startsWith('https://') ? 'url' : 'title'
        };

        renderMeterPreset(customPreset);
    }

    // =========================================================================
    // 4. STATS COUNTERS ANIMATION (INTERSECTION OBSERVER)
    // =========================================================================
    function initCounters() {
        const counters = document.querySelectorAll('.stat-num[data-target]');
        if (!counters.length) return;

        const observer = new IntersectionObserver((entries, obs) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const targetEl = entry.target;
                    const targetVal = parseFloat(targetEl.getAttribute('data-target'));
                    const prefix = targetEl.getAttribute('data-prefix') || '';
                    const suffix = targetEl.getAttribute('data-suffix') || '';
                    const duration = 1600;
                    const startTime = performance.now();

                    function updateCount(currentTime) {
                        const elapsed = currentTime - startTime;
                        const progress = Math.min(elapsed / duration, 1);
                        const ease = 1 - Math.pow(1 - progress, 3);
                        const currentNum = Math.floor(targetVal * ease);

                        targetEl.textContent = prefix + currentNum.toLocaleString() + suffix;

                        if (progress < 1) {
                            requestAnimationFrame(updateCount);
                        } else {
                            targetEl.textContent = prefix + targetVal.toLocaleString() + suffix;
                        }
                    }

                    requestAnimationFrame(updateCount);
                    obs.unobserve(targetEl);
                }
            });
        }, { threshold: 0.3 });

        counters.forEach(c => observer.observe(c));
    }

    // =========================================================================
    // 5. TOAST NOTIFICATION HELPER
    // =========================================================================
    function showLandingToast(msg) {
        let toast = document.getElementById('landing-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'landing-toast';
            toast.className = 'debunk-toast';
            document.body.appendChild(toast);
        }

        toast.textContent = msg;
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
        }, 3200);
    }

    // =========================================================================
    // 6. POSTER HEADLINE DECODE / REVEAL (DYNAMIC INTERACTIVE CIPHER)
    // =========================================================================
    function initCrazyTitle() {
        const debunkEl = document.getElementById('decode-debunk');
        const titleEl = document.getElementById('hero-crazy-title');
        const titleWrap = document.getElementById('hero-title-wrap');
        if (!debunkEl) return;

        const targetWord = 'TRUST';
        const glyphs = ['?', '!', '#', '※', '§', '¶', 'X', 'Ø', '0', '1', 'T', 'R', 'U', 'S'];

        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (prefersReducedMotion) {
            debunkEl.textContent = targetWord;
            return;
        }

        // Ensure each letter has its own interactive span
        let charEls = Array.from(debunkEl.querySelectorAll('.decode-char'));
        if (charEls.length !== targetWord.length) {
            debunkEl.innerHTML = '';
            for (let i = 0; i < targetWord.length; i++) {
                const s = document.createElement('span');
                s.className = 'decode-char';
                s.dataset.orig = targetWord[i];
                s.textContent = targetWord[i];
                debunkEl.appendChild(s);
            }
            charEls = Array.from(debunkEl.querySelectorAll('.decode-char'));
        }

        let isHovered = false;
        let hoverLoopTimer = null;
        let resolveTimer = null;
        let lastSoundTime = 0;

        function playHoverTick(freq = 600) {
            const now = performance.now();
            if (now - lastSoundTime > 80) {
                lastSoundTime = now;
                playTone(freq, 'sine', 0.025, 0.025);
            }
        }

        // Lock in letters cleanly in sequential cascade
        function resolveToWord(instant = false) {
            if (hoverLoopTimer) {
                clearInterval(hoverLoopTimer);
                hoverLoopTimer = null;
            }
            if (resolveTimer) {
                clearTimeout(resolveTimer);
                resolveTimer = null;
            }

            if (instant) {
                charEls.forEach((el, i) => {
                    el.textContent = targetWord[i];
                    el.classList.remove('char-active');
                });
                return;
            }

            charEls.forEach((el, i) => {
                setTimeout(() => {
                    if (isHovered) return; // Abort if user re-entered
                    el.textContent = targetWord[i];
                    el.classList.remove('char-active');
                    if (i === charEls.length - 1 && !isHovered) {
                        playHoverTick(840);
                    }
                }, i * 35);
            });
        }

        // Dynamic cipher loop while hovering: stays alive as long as mouse is on TRUST!
        function startDynamicHover() {
            if (isHovered) return;
            isHovered = true;

            if (resolveTimer) {
                clearTimeout(resolveTimer);
                resolveTimer = null;
            }

            // Immediately scramble letters on touch
            charEls.forEach(el => {
                el.textContent = glyphs[Math.floor(Math.random() * glyphs.length)];
                el.classList.add('char-active');
            });
            playHoverTick(540);

            if (hoverLoopTimer) clearInterval(hoverLoopTimer);

            // Continuously loop while mouse is on TRUST: letters stay dynamic and alive!
            hoverLoopTimer = setInterval(() => {
                if (!isHovered) {
                    clearInterval(hoverLoopTimer);
                    hoverLoopTimer = null;
                    return;
                }

                // Randomly scramble 2 to 3 characters each tick
                const count = Math.floor(Math.random() * 2) + 2;
                for (let k = 0; k < count; k++) {
                    const idx = Math.floor(Math.random() * charEls.length);
                    const el = charEls[idx];
                    el.textContent = glyphs[Math.floor(Math.random() * glyphs.length)];
                    el.classList.add('char-active');
                }

                // Others occasionally settle or flicker
                charEls.forEach((el, idx) => {
                    if (Math.random() > 0.6) {
                        el.textContent = targetWord[idx];
                        el.classList.remove('char-active');
                    }
                });

                playHoverTick(480 + Math.random() * 320);
            }, 85);
        }

        function stopDynamicHover() {
            if (!isHovered) return;
            isHovered = false;
            resolveToWord(false);
        }

        // Interactive mouse movement over the word: characters dynamically react under cursor!
        function handleMouseMove(e) {
            if (!isHovered) {
                startDynamicHover();
            }

            const targetChar = e.target.closest('.decode-char');
            if (targetChar) {
                targetChar.textContent = glyphs[Math.floor(Math.random() * glyphs.length)];
                targetChar.classList.add('char-active');
                playHoverTick(680);
                setTimeout(() => {
                    if (isHovered && targetChar) {
                        targetChar.classList.remove('char-active');
                    }
                }, 140);
            }
        }

        // Attach listeners directly to TRUST and verdict line
        const directTargets = [debunkEl, titleEl].filter(Boolean);
        directTargets.forEach(target => {
            target.addEventListener('mouseenter', startDynamicHover);
            target.addEventListener('mousemove', handleMouseMove);
            target.addEventListener('mouseleave', (e) => {
                const related = e.relatedTarget;
                if (related && (debunkEl.contains(related) || (titleEl && titleEl.contains(related)))) {
                    return;
                }
                stopDynamicHover();
            });
        });

        // 1. Initial letter reveal on page load
        function runIntroSequence() {
            let step = 0;
            const introTimer = setInterval(() => {
                step++;
                charEls.forEach((el, i) => {
                    if (i < step) {
                        el.textContent = targetWord[i];
                        el.classList.remove('char-active');
                    } else {
                        el.textContent = glyphs[Math.floor(Math.random() * glyphs.length)];
                        el.classList.add('char-active');
                    }
                });
                playHoverTick(460 + step * 70);

                if (step >= targetWord.length) {
                    clearInterval(introTimer);
                    resolveToWord(true);
                }
            }, 70);
        }

        runIntroSequence();

        // 2. Trigger letter decode every time user scrolls to the hero section (if not currently hovered)
        if ('IntersectionObserver' in window && titleWrap) {
            const heroObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting && !isHovered) {
                        runIntroSequence();
                    }
                });
            }, {
                threshold: 0.35
            });
            heroObserver.observe(titleWrap);
        }

        // 3. Click interaction for full burst
        if (titleWrap) {
            titleWrap.addEventListener('click', () => {
                playRadarPing();
                charEls.forEach(el => {
                    el.textContent = glyphs[Math.floor(Math.random() * glyphs.length)];
                    el.classList.add('char-active');
                });
                setTimeout(() => {
                    if (!isHovered) resolveToWord(false);
                }, 220);
            });
        }
    }

    // =========================================================================
    // 7. COMMUNITY REVIEWS SYSTEM
    // =========================================================================
    function initCommunityReviews() {
        const modalBackdrop = document.getElementById('review-modal-backdrop');
        const openBtn = document.getElementById('btn-open-review-modal');
        const closeBtn = document.getElementById('btn-close-review-modal');
        const cancelBtn = document.getElementById('btn-cancel-review');
        const form = document.getElementById('community-review-form');
        const starPicker = document.getElementById('star-picker');
        const ratingVal = document.getElementById('review-rating-val');
        const quotesGrid = document.getElementById('quotes-grid');

        function openModal() {
            if (!modalBackdrop) return;
            initAudio();
            modalBackdrop.classList.add('open');
            modalBackdrop.setAttribute('aria-hidden', 'false');
            playChime();
            const firstInput = document.getElementById('review-author');
            if (firstInput) firstInput.focus();
        }

        function closeModal() {
            if (!modalBackdrop) return;
            modalBackdrop.classList.remove('open');
            modalBackdrop.setAttribute('aria-hidden', 'true');
        }

        if (openBtn) openBtn.addEventListener('click', openModal);
        if (closeBtn) closeBtn.addEventListener('click', closeModal);
        if (cancelBtn) cancelBtn.addEventListener('click', closeModal);
        if (modalBackdrop) {
            modalBackdrop.addEventListener('click', (e) => {
                if (e.target === modalBackdrop) closeModal();
            });
            window.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && modalBackdrop.classList.contains('open')) {
                    closeModal();
                }
            });
        }

        if (starPicker && ratingVal) {
            const stars = starPicker.querySelectorAll('.star-pick');
            stars.forEach(star => {
                star.addEventListener('click', () => {
                    const val = parseInt(star.getAttribute('data-val') || '5', 10);
                    ratingVal.value = val;
                    stars.forEach(s => {
                        const sVal = parseInt(s.getAttribute('data-val') || '1', 10);
                        if (sVal <= val) {
                            s.classList.add('active');
                        } else {
                            s.classList.remove('active');
                        }
                    });
                    playTone(550 + (val * 80), 'triangle', 0.04, 0.04);
                });
            });
        }

        function createReviewCard(author, role, rating, content, isNew = false) {
            const card = document.createElement('div');
            card.className = `quote-card ${isNew ? 'new-community-review' : ''}`;
            const starsStr = '★'.repeat(rating) + '☆'.repeat(Math.max(0, 5 - rating));

            card.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                    <div class="quote-stars">${starsStr}</div>
                    <span class="community-verified-badge">VERIFIED</span>
                </div>
                <p class="quote-body">"${escapeHtml(content)}"</p>
                <div class="quote-author">
                    <div class="author-avatar">${escapeHtml(author.charAt(0).toUpperCase())}</div>
                    <div class="author-info">
                        <h4>${escapeHtml(author)}</h4>
                        <p>${escapeHtml(role)}</p>
                    </div>
                </div>
            `;
            return card;
        }

        function escapeHtml(str) {
            const div = document.createElement('div');
            div.textContent = str || '';
            return div.innerHTML;
        }

        function loadCommunityReviews() {
            if (!quotesGrid) return;
            try {
                const saved = JSON.parse(localStorage.getItem('debunkit_community_reviews') || '[]');
                saved.reverse().forEach(r => {
                    const card = createReviewCard(r.author, r.role, r.rating, r.content);
                    quotesGrid.insertBefore(card, quotesGrid.firstChild);
                });
            } catch (e) {}

            fetch('/api/reviews')
                .then(res => res.json())
                .then(data => {
                    if (data && data.status === 'success' && Array.isArray(data.reviews)) {
                        data.reviews.forEach(r => {
                            const card = createReviewCard(r.author_name, r.author_role, r.rating, r.content);
                            quotesGrid.insertBefore(card, quotesGrid.firstChild);
                        });
                    }
                })
                .catch(() => {});
        }

        loadCommunityReviews();

        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                const authorInput = document.getElementById('review-author');
                const roleInput = document.getElementById('review-role');
                const contentInput = document.getElementById('review-content');

                const author = authorInput ? authorInput.value.trim() : '';
                const role = roleInput ? roleInput.value.trim() : 'Reader';
                const content = contentInput ? contentInput.value.trim() : '';
                const rating = parseInt(ratingVal ? ratingVal.value : '5', 10);

                if (!author || !content) return;

                if (quotesGrid) {
                    const newCard = createReviewCard(author, role, rating, content, true);
                    quotesGrid.insertBefore(newCard, quotesGrid.firstChild);
                    newCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }

                try {
                    const existing = JSON.parse(localStorage.getItem('debunkit_community_reviews') || '[]');
                    existing.push({ author, role, rating, content, date: new Date().toISOString() });
                    localStorage.setItem('debunkit_community_reviews', JSON.stringify(existing));
                } catch (e) {}

                fetch('/api/reviews', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ author, role, rating, content })
                }).catch(() => {});

                playSuccessChime();
                showLandingToast('Review added to the community wall.');
                closeModal();
                form.reset();
            });
        }
    }

    // =========================================================================
    // 9. SIGNATURE MOTION ENGINE: "PRINTED, REDACTED, STAMPED"
    // =========================================================================

    // 9.1 Data-reveal IntersectionObserver: triggers EVERY TIME user scrolls down!
    function initScrollReveals() {
        const revealElements = document.querySelectorAll('[data-reveal]');
        if (!revealElements.length) return;

        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (prefersReducedMotion || !('IntersectionObserver' in window)) {
            revealElements.forEach(el => el.classList.add('is-in'));
            return;
        }

        const revealObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-in');
                } else {
                    // Reset when scrolling out of view so appearing animation runs every time you scroll down!
                    entry.target.classList.remove('is-in');
                }
            });
        }, {
            rootMargin: '-40px 0px',
            threshold: 0.12
        });

        revealElements.forEach(el => revealObserver.observe(el));
    }

    // 9.2 Sticky Nav hairline and backdrop toggle past 8px
    function initStickyNavScroll() {
        const nav = document.querySelector('.landing-nav');
        if (!nav) return;

        let isScrolled = false;
        let ticking = false;

        const onScroll = () => {
            const scrolled = window.scrollY > 8;
            if (scrolled !== isScrolled) {
                isScrolled = scrolled;
                nav.classList.toggle('nav-scrolled', isScrolled);
            }
            ticking = false;
        };

        window.addEventListener('scroll', () => {
            if (!ticking) {
                window.requestAnimationFrame(onScroll);
                ticking = true;
            }
        }, { passive: true });

        onScroll();
    }

    // 9.3 Ticker headline snap highlight sweep
    function initTickerSnap() {
        const tickerViewport = document.querySelector('.ticker-viewport');
        const tickerItems = document.querySelectorAll('.ticker-item');
        if (!tickerViewport || !tickerItems.length || !('IntersectionObserver' in window)) return;

        const snapObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('ticker-snap');
                    setTimeout(() => {
                        entry.target.classList.remove('ticker-snap');
                    }, 400);
                }
            });
        }, {
            root: tickerViewport,
            rootMargin: '0px 0px 0px -10px',
            threshold: 0.5
        });

        tickerItems.forEach(item => snapObserver.observe(item));
    }

    // 9.4 Hero collage cursor-follow subtle parallax (max 6px, smoothed with lerp)
    function initHeroParallax() {
        const collage = document.querySelector('.hero-collage-graphic');
        if (!collage) return;

        const isFinePointer = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (!isFinePointer || prefersReducedMotion) return;

        let targetX = 0;
        let targetY = 0;
        let currentX = 0;
        let currentY = 0;
        let animId = null;

        const hero = document.querySelector('.hero-section');
        if (!hero) return;

        hero.addEventListener('mousemove', (e) => {
            const rect = hero.getBoundingClientRect();
            const relX = (e.clientX - rect.left) / rect.width - 0.5;
            const relY = (e.clientY - rect.top) / rect.height - 0.5;
            targetX = relX * 12; // max ±6px
            targetY = relY * 12;

            if (!animId) {
                animId = requestAnimationFrame(updateParallax);
            }
        }, { passive: true });

        hero.addEventListener('mouseleave', () => {
            targetX = 0;
            targetY = 0;
        });

        function updateParallax() {
            currentX += (targetX - currentX) * 0.08;
            currentY += (targetY - currentY) * 0.08;

            collage.style.transform = `translate3d(${currentX.toFixed(2)}px, ${currentY.toFixed(2)}px, 0)`;

            if (Math.abs(targetX - currentX) > 0.05 || Math.abs(targetY - currentY) > 0.05) {
                animId = requestAnimationFrame(updateParallax);
            } else {
                animId = null;
            }
        }
    }

    // 9.5 Page-to-page navigation: 150ms opacity fade only
    function initPageFadeTransition() {
        document.addEventListener('click', (e) => {
            const anchor = e.target.closest('a');
            if (!anchor) return;
            const href = anchor.getAttribute('href');
            if (!href || href.startsWith('#') || href.startsWith('javascript:') || anchor.target === '_blank') return;
            if (e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
            if (href.startsWith('/') || href.startsWith(window.location.origin)) {
                e.preventDefault();
                document.body.classList.add('page-leaving');
                setTimeout(() => {
                    window.location.href = href;
                }, 120);
            }
        });
    }

    // =========================================================================
    // 8. INITIALIZE ON DOM READY
    // =========================================================================
    document.addEventListener('DOMContentLoaded', () => {
        // SFX Toggle Setup (default OFF)
        const sfxBtn = document.getElementById('sfx-toggle-btn');
        if (sfxBtn) {
            function updateSFXButtonUI() {
                if (sfxEnabled) {
                    sfxBtn.classList.add('active');
                    sfxBtn.setAttribute('aria-pressed', 'true');
                    sfxBtn.innerHTML = `
                        <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>
                        <span>SFX: ON</span>
                    `;
                } else {
                    sfxBtn.classList.remove('active');
                    sfxBtn.setAttribute('aria-pressed', 'false');
                    sfxBtn.innerHTML = `
                        <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><line x1="23" y1="9" x2="17" y2="15"></line><line x1="17" y1="9" x2="23" y2="15"></line></svg>
                        <span>SFX: OFF</span>
                    `;
                }
            }
            updateSFXButtonUI();

            sfxBtn.addEventListener('click', () => {
                initAudio();
                sfxEnabled = !sfxEnabled;
                localStorage.setItem('debunkit_sfx', sfxEnabled ? 'on' : 'off');
                updateSFXButtonUI();
                if (sfxEnabled) {
                    playSuccessChime();
                    showLandingToast('Sound effects enabled.');
                } else {
                    showLandingToast('Sound effects muted.');
                }
            });
        }

        // Mobile Nav Toggle
        const mobileBtn = document.querySelector('.mobile-menu-btn');
        const navLinks = document.querySelector('.nav-links');
        if (mobileBtn && navLinks) {
            mobileBtn.addEventListener('click', () => {
                navLinks.classList.toggle('open');
                const isOpen = navLinks.classList.contains('open');
                mobileBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
                playClick();
            });

            // Close mobile menu when an item is selected
            navLinks.querySelectorAll('.nav-link').forEach(link => {
                link.addEventListener('click', () => {
                    if (navLinks.classList.contains('open')) {
                        navLinks.classList.remove('open');
                        mobileBtn.setAttribute('aria-expanded', 'false');
                    }
                });
            });
        }

        // Render Preset Chips
        const chipsContainer = document.getElementById('samples-container');
        if (chipsContainer) {
            chipsContainer.innerHTML = '';
            VIRAL_PRESETS.forEach(preset => {
                const chip = document.createElement('button');
                chip.className = 'sample-chip';
                chip.dataset.id = preset.id;
                chip.textContent = preset.btnText;
                chip.addEventListener('click', () => {
                    playClick();
                    renderMeterPreset(preset);
                });
                chipsContainer.appendChild(chip);
            });
        }

        renderMeterPreset(VIRAL_PRESETS[0]);

        // Custom Claim Input
        const testBtn = document.getElementById('btn-test-custom');
        const customInput = document.getElementById('custom-claim-input');
        if (testBtn && customInput) {
            testBtn.addEventListener('click', () => {
                evaluateCustomClaim(customInput.value);
            });
            customInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    evaluateCustomClaim(customInput.value);
                }
            });
        }

        // Ticker item clicks
        document.querySelectorAll('.ticker-item').forEach(item => {
            item.addEventListener('click', () => {
                const claimText = item.getAttribute('data-claim');
                if (claimText) {
                    if (customInput) customInput.value = claimText;
                    evaluateCustomClaim(claimText);
                    const meterSection = document.getElementById('meter');
                    if (meterSection) {
                        meterSection.scrollIntoView({ behavior: 'smooth' });
                    }
                }
            });
        });

        initCounters();
        initCommunityReviews();
        initCrazyTitle();
        initScrollReveals();
        initStickyNavScroll();
        initTickerSnap();
        initHeroParallax();
        initPageFadeTransition();

        // One-time audio unlock on first interaction
        document.body.addEventListener('click', () => {
            initAudio();
        }, { once: true });
    });
})();
