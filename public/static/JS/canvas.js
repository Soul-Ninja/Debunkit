/**
 * DEBUNK.IT — Quiet Luxury / Editorial Canvas Engine
 * Subtle floating newsprint marks & typographic proof particles
 * Respects light/dark modes and prefers-reduced-motion
 */
(function() {
    const canvas = document.getElementById('canvas-bg');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let width = 0;
    let height = 0;
    let animationFrameId = null;

    // Check prefers-reduced-motion
    const reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    let prefersReducedMotion = reducedMotionQuery.matches;

    reducedMotionQuery.addEventListener('change', (e) => {
        prefersReducedMotion = e.matches;
        if (prefersReducedMotion) {
            if (animationFrameId) cancelAnimationFrame(animationFrameId);
            renderStatic();
        } else {
            animate();
        }
    });

    function resize() {
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
        initParticles();
        if (prefersReducedMotion) {
            renderStatic();
        }
    }
    window.addEventListener('resize', resize, { passive: true });

    // Typographic fragments inspired by investigative editorial prints
    const words = [
        "VERITAS", "EVIDENCE", "SOURCE", "RECEIPTS", "FACTUM", "RECORD",
        "RETRACTED", "CORROBORATED", "WITNESS", "DOSSIER", "INVESTIGATION",
        "TRUTH", "LEDGER", "DISPATCH", "GAZETTE", "DEBUNK", "CITATIONS",
        "?", "§", "¶", "※", "†", "‡", "№", "—"
    ];

    let particles = [];

    function isDarkMode() {
        const docTheme = document.documentElement.getAttribute('data-theme');
        if (docTheme === 'dark') return true;
        if (docTheme === 'light') return false;
        return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }

    class EditorialParticle {
        constructor() {
            this.reset(true);
        }

        reset(initial = false) {
            this.text = words[Math.floor(Math.random() * words.length)];
            this.isGlyph = this.text.length <= 2;
            this.fontSize = this.isGlyph ? Math.floor(Math.random() * 12 + 14) : Math.floor(Math.random() * 6 + 10);
            ctx.font = `${this.fontSize}px 'Newsreader', Georgia, serif`;
            this.width = ctx.measureText(this.text).width;
            this.height = this.fontSize;
            this.x = Math.random() * (width - this.width);
            this.y = initial ? Math.random() * height : -30;
            
            // Slow, soft, confident motion: gentle vertical drift with subtle horizontal wander
            this.speedY = Math.random() * 0.35 + 0.15;
            this.driftX = (Math.random() - 0.5) * 0.1;
            this.opacity = Math.random() * 0.05 + 0.02; // Refined luxury restraint: 2% to 7% opacity
            this.rotation = (Math.random() - 0.5) * 0.08;
        }

        update() {
            this.y += this.speedY;
            this.x += this.driftX;
            if (this.y > height + 40 || this.x < -100 || this.x > width + 100) {
                this.reset(false);
            }
        }

        draw(dark) {
            ctx.save();
            ctx.translate(this.x, this.y);
            ctx.rotate(this.rotation);
            ctx.font = `${this.fontSize}px 'Newsreader', Georgia, serif`;
            
            if (dark) {
                ctx.fillStyle = `rgba(228, 224, 211, ${this.opacity * 1.2})`;
            } else {
                ctx.fillStyle = `rgba(27, 27, 27, ${this.opacity})`;
            }
            ctx.fillText(this.text, 0, 0);
            ctx.restore();
        }
    }

    function initParticles() {
        particles = [];
        // Low density: restrained whitespace
        const count = Math.min(28, Math.max(12, Math.floor((width * height) / 38000)));
        for (let i = 0; i < count; i++) {
            particles.push(new EditorialParticle());
        }
    }

    function renderStatic() {
        ctx.clearRect(0, 0, width, height);
        const dark = isDarkMode();
        for (let i = 0; i < particles.length; i++) {
            particles[i].draw(dark);
        }
    }

    function animate() {
        if (prefersReducedMotion) {
            renderStatic();
            return;
        }
        ctx.clearRect(0, 0, width, height);
        const dark = isDarkMode();

        for (let i = 0; i < particles.length; i++) {
            particles[i].update();
            particles[i].draw(dark);
        }
        animationFrameId = requestAnimationFrame(animate);
    }

    // Preserve the Easter egg click detection from original canvas.js
    canvas.addEventListener('click', (e) => {
        const mouseX = e.clientX;
        const mouseY = e.clientY;

        for (let i = 0; i < particles.length; i++) {
            const p = particles[i];
            if (mouseX >= p.x - 20 && mouseX <= p.x + p.width + 20 &&
                mouseY >= p.y - p.height - 10 && mouseY <= p.y + 10) {
                console.log(`[Debunkit] Sniped word: ${p.text}`);
                if (p.text.length > 2) {
                    window.open(`https://duckduckgo.com/?q=define+${p.text.toLowerCase()}`, '_blank');
                }
                break;
            }
        }
    });

    
    // Pause RAF when the tab is hidden to conserve resources and maintain battery efficiency
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            if (animationFrameId) {
                cancelAnimationFrame(animationFrameId);
                animationFrameId = null;
            }
        } else {
            if (!prefersReducedMotion && !animationFrameId) {
                animate();
            }
        }
    });

    resize();
    if (!prefersReducedMotion) {
        animate();
    }
})();
