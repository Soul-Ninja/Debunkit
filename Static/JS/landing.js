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
    // 6. POSTER HEADLINE DECODE / REVEAL
    // =========================================================================
    function initCrazyTitle() {
        const debunkEl = document.getElementById('decode-debunk');
        const itEl = document.getElementById('decode-it');
        const titleEl = document.getElementById('hero-crazy-title');
        const titleWrap = document.getElementById('hero-title-wrap');
        if (!debunkEl) return;

        // Poster headline key word is "TRUST"
        const targetWord = 'TRUST';
        const glyphs = ['?', '!', '#', '※', '§', '¶', 'T', 'R', 'U', 'S'];

        // Gentle staggered reveal if reduced-motion is not requested
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (prefersReducedMotion) {
            debunkEl.textContent = targetWord;
            return;
        }

        let step = 0;
        const revealInterval = setInterval(() => {
            step++;
            if (step <= targetWord.length) {
                let res = targetWord.substring(0, step);
                for (let i = step; i < targetWord.length; i++) {
                    res += glyphs[Math.floor(Math.random() * glyphs.length)];
                }
                debunkEl.textContent = res;
                playTone(480 + (step * 80), 'sine', 0.03, 0.03);
            } else {
                clearInterval(revealInterval);
                debunkEl.textContent = targetWord;
            }
        }, 120);

        if (titleWrap) {
            titleWrap.addEventListener('click', () => {
                playRadarPing();
                let bursts = 0;
                const burstInt = setInterval(() => {
                    bursts++;
                    let r = '';
                    for (let i = 0; i < targetWord.length; i++) {
                        r += glyphs[Math.floor(Math.random() * glyphs.length)];
                    }
                    debunkEl.textContent = r;
                    if (bursts > 4) {
                        clearInterval(burstInt);
                        debunkEl.textContent = targetWord;
                        playSuccessChime();
                    }
                }, 60);
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

        // One-time audio unlock on first interaction
        document.body.addEventListener('click', () => {
            initAudio();
        }, { once: true });
    });
})();
