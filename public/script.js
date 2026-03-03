/* ════════════════════════════════════════════════════
     BACKGROUND CANVAS SCRIPT
     12 vehicles: 4 F1 + 4 MotoGP + 4 Stock cars
     Top-down view with ghost trail
════════════════════════════════════════════════════ */
(function initCanvas() {
    const canvas = document.getElementById('bg-canvas');
    const ctx = canvas.getContext('2d');
    let W, H, vehicles = [];

    // Sunrise-harmonious palettes — warm/cool balance
    const PALETTES = [
        ['#dc2626', '#ef4444', '#b91c1c'],   // crimson
        ['#ea580c', '#f97316', '#c2410c'],   // orange
        ['#2563eb', '#3b82f6', '#1d4ed8'],   // royal blue
        ['#059669', '#10b981', '#047857'],   // emerald
        ['#7c3aed', '#8b5cf6', '#6d28d9'],   // violet
        ['#d97706', '#f59e0b', '#b45309'],   // amber
        ['#0e7490', '#0891b2', '#0c4a6e'],   // cyan-dark
        ['#be185d', '#ec4899', '#9d174d'],   // pink
    ];

    function rndPalette() { return PALETTES[Math.floor(Math.random() * PALETTES.length)]; }

    const VEHICLE_TYPES = ['f1', 'moto', 'stock'];

    class Vehicle {
        constructor(init) { this._init(init ? Math.random() * 1000 : 0, true); }

        _init(seed, fullW) {
            this.palette = rndPalette();
            this.type = VEHICLE_TYPES[Math.floor(Math.random() * 3)];
            this.scale = 0.48 + Math.random() * 0.68;
            // Alpha scaled with depth — smaller = farther = more transparent
            this.alpha = 0.07 + (this.scale - 0.48) * 0.18;
            const baseSpeed = 2.8 + Math.random() * 8.5;
            this.speed = (Math.random() > 0.5 ? 1 : -1) * baseSpeed;
            this.y = 55 + Math.random() * (H - 110);
            this.x = fullW
                ? Math.random() * W
                : (this.speed > 0 ? -180 : W + 180);
            this.trail = [];
            this.trailLen = Math.floor(6 + Math.abs(this.speed) * 1.4);
        }

        reset() { this._init(0, false); }

        update() {
            this.trail.push({ x: this.x, y: this.y });
            if (this.trail.length > this.trailLen) this.trail.shift();
            this.x += this.speed;
            if ((this.speed > 0 && this.x > W + 200) || (this.speed < 0 && this.x < -200)) this.reset();
        }

        draw(isDark = false) {
            const mirror = this.speed < 0;
            // Dark mode: vehicles slightly more visible
            const baseAlpha = isDark ? Math.min(this.alpha * 1.55, 0.55) : this.alpha;
            // Trail ghosts
            for (let i = 0; i < this.trail.length; i++) {
                const t = i / this.trail.length;
                ctx.save();
                ctx.globalAlpha = baseAlpha * t * 0.45;
                this._drawShape(this.trail[i].x, this.trail[i].y, mirror);
                ctx.restore();
            }
            // Main vehicle
            ctx.save();
            ctx.globalAlpha = baseAlpha;
            this._drawShape(this.x, this.y, mirror);
            ctx.restore();
        }

        _drawShape(x, y, mirror) {
            ctx.save();
            ctx.translate(x, y);
            if (mirror) ctx.scale(-1, 1);
            ctx.scale(this.scale, this.scale);
            const [c1, c2, c3] = this.palette;

            if (this.type === 'f1') {
                // F1 — top-down bird's eye
                // Nose cone
                ctx.fillStyle = c1;
                ctx.beginPath();
                ctx.moveTo(56, 0);
                ctx.bezierCurveTo(56, -5, 34, -10, 0, -9);
                ctx.bezierCurveTo(-30, -9, -46, -6, -46, 0);
                ctx.bezierCurveTo(-46, 6, -30, 9, 0, 9);
                ctx.bezierCurveTo(34, 10, 56, 5, 56, 0);
                ctx.fill();
                // Cockpit canopy
                ctx.fillStyle = c3;
                ctx.beginPath();
                ctx.ellipse(5, 0, 13, 5, 0, 0, Math.PI * 2);
                ctx.fill();
                // Front wing
                ctx.fillStyle = c2;
                ctx.beginPath();
                ctx.roundRect(46, -17, 8, 34, 2);
                ctx.fill();
                // Rear wing
                ctx.beginPath();
                ctx.roundRect(-54, -20, 9, 40, 2);
                ctx.fill();
                // Wheels x4
                ctx.fillStyle = '#1e293b';
                [[22, 15], [22, -15], [-28, 14], [-28, -14]].forEach(([wx, wy]) => {
                    ctx.beginPath(); ctx.ellipse(wx, wy, 7, 5, 0, 0, Math.PI * 2); ctx.fill();
                    ctx.strokeStyle = 'rgba(255,255,255,0.2)'; ctx.lineWidth = 1;
                    ctx.beginPath(); ctx.ellipse(wx, wy, 4, 2.5, 0, 0, Math.PI * 2); ctx.stroke();
                });
                // Halo
                ctx.strokeStyle = c2; ctx.lineWidth = 1.5;
                ctx.beginPath(); ctx.arc(5, 0, 8, -Math.PI * 0.6, -Math.PI * 0.4, true); ctx.stroke();

            } else if (this.type === 'moto') {
                // MotoGP — side view, leaned
                ctx.fillStyle = c1;
                ctx.beginPath();
                ctx.ellipse(0, -2, 30, 8, -0.12, 0, Math.PI * 2);
                ctx.fill();
                // Front fairing
                ctx.beginPath();
                ctx.moveTo(24, -3); ctx.lineTo(36, -1); ctx.lineTo(35, 3); ctx.lineTo(24, 4);
                ctx.fill();
                // Rider
                ctx.fillStyle = c2;
                ctx.beginPath(); ctx.ellipse(-2, -14, 8, 5, 0.35, 0, Math.PI * 2); ctx.fill();
                ctx.fillStyle = c3;
                ctx.beginPath(); ctx.arc(-3, -22, 5, 0, Math.PI * 2); ctx.fill();
                // Visor
                ctx.fillStyle = 'rgba(255,255,255,0.4)';
                ctx.beginPath(); ctx.ellipse(0, -21, 3, 2, 0.4, 0, Math.PI); ctx.fill();
                // Wheels
                ctx.fillStyle = '#1e293b';
                [[-20, 8], [23, 8]].forEach(([wx, wy]) => {
                    ctx.beginPath(); ctx.arc(wx, wy, 8, 0, Math.PI * 2); ctx.fill();
                    ctx.strokeStyle = 'rgba(255,255,255,0.15)'; ctx.lineWidth = 1.5;
                    ctx.stroke();
                });

            } else {
                // Stock car / NASCAR — top-down
                ctx.fillStyle = c1;
                ctx.beginPath();
                ctx.roundRect(-40, -12, 80, 24, [5, 5, 5, 5]); ctx.fill();
                // Roof
                ctx.fillStyle = c2;
                ctx.beginPath(); ctx.roundRect(-19, -10, 38, 20, 4); ctx.fill();
                // Windshield
                ctx.fillStyle = 'rgba(219,234,254,0.5)';
                ctx.beginPath(); ctx.roundRect(8, -7, 10, 14, 2); ctx.fill();
                // Number
                ctx.fillStyle = 'rgba(15,23,42,0.75)';
                ctx.font = `bold 8px 'Barlow Condensed', sans-serif`;
                ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
                ctx.fillText('48', 0, 0);
                // Sponsor stripe
                ctx.fillStyle = c3;
                ctx.fillRect(-18, -3, 36, 6);
                // Wheels x4
                ctx.fillStyle = '#1e293b';
                [[-26, 14], [-26, -14], [22, 14], [22, -14]].forEach(([wx, wy]) => {
                    ctx.beginPath(); ctx.ellipse(wx, wy, 8, 5.5, 0, 0, Math.PI * 2); ctx.fill();
                });
            }
            ctx.restore();
        }
    }

    function resize() {
        W = canvas.width = window.innerWidth;
        H = canvas.height = window.innerHeight;
        // Recreate offscreen canvas on resize so dimensions stay in sync
        initOffscreen();
    }

    // ── OffscreenCanvas for headlight beams ─────────────────
    let offscreen, offCtx;
    function initOffscreen() {
        try {
            offscreen = new OffscreenCanvas(W, H);
        } catch (e) {
            offscreen = document.createElement('canvas');
            offscreen.width = W; offscreen.height = H;
        }
        offCtx = offscreen.getContext('2d');
    }

    function drawHeadlights() {
        offCtx.clearRect(0, 0, W, H);

        vehicles.forEach(v => {
            const dir = v.speed > 0 ? 1 : -1;
            const mirror = dir < 0;

            // Front tip offset per vehicle type (in local-space units × scale)
            const frontOffsets = { f1: 58, moto: 34, stock: 42 };
            const frontOff = (frontOffsets[v.type] || 42) * v.scale;

            const fx = v.x + dir * frontOff;
            const fy = v.y;

            const beamLen = (220 + v.scale * 180) * v.scale;
            const coneHalf = Math.PI / 7.5;   // ~24° half-angle
            const coneAngle = dir > 0 ? 0 : Math.PI;

            // Two headlights — slight vertical offset
            const offsets = [-5 * v.scale, 5 * v.scale];

            offsets.forEach(yo => {
                const hx = fx;
                const hy = fy + yo;

                // Cone clipping path
                offCtx.save();
                offCtx.beginPath();
                offCtx.moveTo(hx, hy);
                offCtx.arc(hx, hy, beamLen, coneAngle - coneHalf, coneAngle + coneHalf);
                offCtx.closePath();
                offCtx.clip();

                // Radial gradient — warm xenon white fading to transparent
                const grad = offCtx.createRadialGradient(hx, hy, 0, hx, hy, beamLen);
                grad.addColorStop(0, `rgba(255,255,230, 0.55)`);
                grad.addColorStop(0.18, `rgba(230,240,255, 0.28)`);
                grad.addColorStop(0.55, `rgba(180,210,255, 0.10)`);
                grad.addColorStop(1, `rgba(100,160,255, 0)`);

                offCtx.fillStyle = grad;
                offCtx.fillRect(
                    Math.min(hx, hx + dir * beamLen),
                    hy - beamLen,
                    beamLen + 4, beamLen * 2
                );
                offCtx.restore();
            });

            // Rear brake glow (dim red ellipse behind vehicle)
            const rearX = v.x - dir * frontOff;
            const rg = offCtx.createRadialGradient(rearX, fy, 0, rearX, fy, 28 * v.scale);
            rg.addColorStop(0, `rgba(220, 40, 40, 0.45)`);
            rg.addColorStop(0.5, `rgba(200, 20, 20, 0.14)`);
            rg.addColorStop(1, `rgba(180,  0,  0, 0)`);
            offCtx.save();
            offCtx.fillStyle = rg;
            offCtx.beginPath();
            offCtx.ellipse(rearX, fy, 28 * v.scale, 10 * v.scale, 0, 0, Math.PI * 2);
            offCtx.fill();
            offCtx.restore();
        });

        // Composite headlight layer onto main canvas
        ctx.save();
        ctx.globalCompositeOperation = 'screen';
        ctx.globalAlpha = 0.38;           // atmospheric, non-disruptive
        ctx.drawImage(offscreen, 0, 0);
        ctx.restore();
    }

    function init() {
        resize(); // also calls initOffscreen()
        vehicles = Array.from({ length: 12 }, () => new Vehicle(true));
    }

    function frame() {
        ctx.clearRect(0, 0, W, H);

        const isDark = document.documentElement.dataset.theme === 'dark';

        // Speed-lines — adapt color to theme
        ctx.save();
        ctx.globalAlpha = isDark ? 0.025 : 0.015;
        for (let i = 0; i < H; i += 32) {
            const hue = isDark ? (200 + (i % 30)) : (210 + (i % 40));
            ctx.strokeStyle = isDark ? `hsl(${hue},40%,35%)` : `hsl(${hue},30%,60%)`;
            ctx.lineWidth = 0.4;
            ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(W, i); ctx.stroke();
        }
        ctx.restore();

        // Sort + draw vehicles
        vehicles.sort((a, b) => a.scale - b.scale);
        vehicles.forEach(v => { v.update(); v.draw(isDark); });

        // Night headlights pass
        if (isDark) drawHeadlights();

        requestAnimationFrame(frame);
    }

    window.addEventListener('resize', resize);
    init();
    frame();
})();


/* ════════════════════════════════════════════════════
     APP LOGIC
════════════════════════════════════════════════════ */
(() => {
    'use strict';

    // ─────────────────────────────────────────────────
    //  CONFIG
    // ─────────────────────────────────────────────────
    const CATEGORIES = {
        f1: {
            name: 'Formula 1', subtitle: '24 Grand Prix · 2026',
            logo: '/f1.svg', logoInvert: true,
            sessions: [
                { id: 'p1', label: 'P1', alias: 'practice', backendKey: 'p1' },
                { id: 'p2', label: 'P2', alias: 'practice', backendKey: 'p2' },
                { id: 'p3', label: 'P3', alias: 'practice', backendKey: 'p3' },
                { id: 'sprint_qualy', label: 'Sprint Qualy', alias: 'qualifying', backendKey: 'sprint_qualy' },
                { id: 'qualy', label: 'Clasificación', alias: 'qualifying', backendKey: 'qualifying' },
                { id: 'sprint', label: 'Sprint', alias: 'sprint', backendKey: 'sprint' },
                { id: 'race', label: 'Carrera', alias: 'race', backendKey: 'race' },
            ],
        },
        gt: {
            name: 'GT World Challenge', subtitle: 'Europe · Endurance & Sprint',
            logo: '/gt.svg', logoInvert: true,
            sessions: [
                { id: 'fp1', label: 'Free Practice 1', alias: 'practice', backendKey: 'fp1' },
                { id: 'fp2', label: 'Free Practice 2', alias: 'practice', backendKey: 'fp2' },
                { id: 'qualifying', label: 'Qualifying', alias: 'qualifying', backendKey: 'qualifying' },
                { id: 'race', label: 'Carrera / Endurance', alias: 'race', backendKey: 'race' },
                { id: 'race1', label: 'Race 1', alias: 'race', backendKey: 'race' },
                { id: 'race2', label: 'Race 2', alias: 'race', backendKey: 'race' },
            ],
        },
        nascar: {
            name: 'NASCAR Cup Series', subtitle: '38 Carreras · 2026',
            logo: '/nascar.svg', logoInvert: true,
            sessions: [
                { id: 'race', label: 'Carrera', alias: 'race', backendKey: 'race' },
            ],
        },
        motogp: {
            name: 'MotoGP', subtitle: '22 Grand Prix · 2026',
            logo: '/motogp.svg', logoInvert: true,
            sessions: [
                { id: 'fp1', label: 'FP1', alias: 'practice', backendKey: 'fp1' },
                { id: 'fp2', label: 'FP2', alias: 'practice', backendKey: 'fp2' },
                { id: 'practica', label: 'Práctica', alias: 'practice', backendKey: 'practica' },
                { id: 'warmup', label: 'Warm Up', alias: 'practice', backendKey: 'warmup' },
                { id: 'q1', label: 'Q1 Clasificación', alias: 'qualifying', backendKey: 'q1' },
                { id: 'q2', label: 'Q2 Clasificación', alias: 'qualifying', backendKey: 'q2' },
                { id: 'sprint', label: 'Sprint', alias: 'sprint', backendKey: 'sprint' },
                { id: 'race', label: 'Carrera', alias: 'race', backendKey: 'race' },
            ],
        },
    };

    function defaultSessions(catKey) {
        return new Set(
            CATEGORIES[catKey].sessions
                .filter(s => s.alias !== 'practice')
                .map(s => s.id)
        );
    }

    // ─────────────────────────────────────────────────
    //  STATE
    // ─────────────────────────────────────────────────
    const state = {
        races: [], loading: true, error: null,
        catEnabled: { f1: true, gt: true, nascar: true, motogp: true },
        catSessions: {
            f1: defaultSessions('f1'),
            gt: defaultSessions('gt'),
            nascar: defaultSessions('nascar'),
            motogp: defaultSessions('motogp'),
        },
    };

    // ─────────────────────────────────────────────────
    //  URL BUILDER
    // ─────────────────────────────────────────────────
    function buildUrl() {
        const enabledCats = Object.keys(state.catEnabled).filter(k => state.catEnabled[k]);
        if (!enabledCats.length) return '';
        const p = new URLSearchParams();
        let hasAnySessions = false;
        for (const cat of enabledCats) {
            p.append('cats', cat);
            const backendKeys = new Set();
            for (const sess of CATEGORIES[cat].sessions) {
                if (state.catSessions[cat].has(sess.id)) backendKeys.add(sess.backendKey);
            }
            if (backendKeys.size) {
                hasAnySessions = true;
                backendKeys.forEach(k => p.append(`${cat}_sessions`, k));
            }
        }
        if (!hasAnySessions) return '';
        // Include selected timezone (backend uses it for VTIMEZONE headers; calendar apps handle UTC→local automatically)
        const tz = window.apexTz || 'Europe/Madrid';
        if (tz && tz !== 'UTC') p.set('tz', tz);
        return `${window.location.origin}/calendar.ics?${p.toString()}`;
    }

    function syncUrl() {
        const url = buildUrl();
        const input = document.getElementById('urlOutput');
        const copyBtn = document.getElementById('copyBtn');
        const gcalBtn = document.getElementById('gcalBtn');
        const errMsg = document.getElementById('errorMessage');
        if (url) {
            input.value = url;
            errMsg.classList.add('hidden');
            copyBtn.disabled = false;
            if (gcalBtn) gcalBtn.disabled = false;
        } else {
            input.value = '';
            errMsg.classList.remove('hidden');
            copyBtn.disabled = true;
            if (gcalBtn) gcalBtn.disabled = true;
        }
    }

    // ─────────────────────────────────────────────────
    //  RENDER — category cards
    // ─────────────────────────────────────────────────
    function renderCategories() {
        const grid = document.getElementById('categories-grid');
        grid.innerHTML = '';
        for (const [catKey, catCfg] of Object.entries(CATEGORIES)) {
            grid.appendChild(buildCard(catKey, catCfg));
        }
    }

    function buildCard(catKey, catCfg) {
        const enabled = state.catEnabled[catKey];
        const selected = state.catSessions[catKey];

        const card = document.createElement('div');
        card.className = `cat-card p-4 ${enabled ? 'cat-enabled' : 'cat-disabled'}`;
        card.dataset.catKey = catKey;

        // Header
        const header = document.createElement('div');
        header.className = 'flex items-center justify-between mb-3';

        const logoArea = document.createElement('div');
        logoArea.className = 'flex items-center gap-2.5';

        const img = document.createElement('img');
        img.src = catCfg.logo; img.alt = catCfg.name;
        img.className = 'cat-logo';
        img.style.cssText = catCfg.logoInvert
            ? 'filter: brightness(0) opacity(0.72);'
            : 'filter: opacity(0.88);';

        const info = document.createElement('div');
        info.innerHTML = `
            <p class="text-sm font-semibold text-title leading-none mb-0.5">${catCfg.name}</p>
            <p class="text-label" style="font-size:11px;">${catCfg.subtitle}</p>
        `;
        logoArea.append(img, info);

        // Toggle — royal blue
        const toggle = document.createElement('div');
        toggle.className = `toggle-track ${enabled ? 'on' : 'off'}`;
        toggle.dataset.action = 'toggle-cat';
        toggle.dataset.cat = catKey;
        toggle.setAttribute('role', 'switch');
        toggle.setAttribute('aria-checked', String(enabled));
        toggle.setAttribute('aria-label', `Activar ${catCfg.name}`);
        toggle.innerHTML = '<div class="toggle-knob"></div>';
        header.append(logoArea, toggle);

        // Content (dims when off)
        const content = document.createElement('div');
        content.className = `transition-opacity duration-200 ${enabled ? 'opacity-100' : 'opacity-40 pointer-events-none'}`;
        content.dataset.catContent = catKey;

        const controls = document.createElement('div');
        controls.className = 'flex items-center gap-2 mb-3';
        const selAll = document.createElement('button');
        selAll.textContent = 'Seleccionar todo';
        selAll.className = 'text-[11px] px-2.5 py-1 rounded-lg btn-ghost font-medium';
        selAll.dataset.action = 'select-all'; selAll.dataset.cat = catKey;
        const clearBtn = document.createElement('button');
        clearBtn.textContent = 'Borrar selección';
        clearBtn.className = 'text-[11px] px-2.5 py-1 rounded-lg btn-ghost font-medium';
        clearBtn.dataset.action = 'clear'; clearBtn.dataset.cat = catKey;
        controls.append(selAll, clearBtn);

        const pillsRow = document.createElement('div');
        pillsRow.className = 'flex flex-wrap gap-1.5';
        pillsRow.dataset.pillsContainer = catKey;
        catCfg.sessions.forEach(sess =>
            pillsRow.appendChild(buildPill(catKey, sess, selected.has(sess.id)))
        );

        content.append(controls, pillsRow);
        card.append(header, content);
        return card;
    }

    function buildPill(catKey, sess, active) {
        const btn = document.createElement('button');
        btn.className = `pill${active ? ' active' : ''}`;
        btn.dataset.action = 'toggle-session';
        btn.dataset.cat = catKey;
        btn.dataset.session = sess.id;
        btn.dataset.alias = sess.alias;
        btn.textContent = sess.label;
        return btn;
    }

    function rerenderCard(catKey) {
        const old = document.querySelector(`[data-cat-key="${catKey}"]`);
        if (old) old.replaceWith(buildCard(catKey, CATEGORIES[catKey]));
    }

    function rerenderPills(catKey) {
        const c = document.querySelector(`[data-pills-container="${catKey}"]`);
        if (!c) return;
        c.innerHTML = '';
        const sel = state.catSessions[catKey];
        CATEGORIES[catKey].sessions.forEach(sess => c.appendChild(buildPill(catKey, sess, sel.has(sess.id))));
    }

    // ─────────────────────────────────────────────────
    //  EVENT DELEGATION
    // ─────────────────────────────────────────────────
    function onGridClick(e) {
        const t = e.target.closest('[data-action]');
        if (!t) return;
        const { action, cat, session: sessId } = t.dataset;
        switch (action) {
            case 'toggle-cat':
                state.catEnabled[cat] = !state.catEnabled[cat];
                rerenderCard(cat); syncUrl(); break;
            case 'toggle-session': {
                const s = state.catSessions[cat];
                s.has(sessId) ? s.delete(sessId) : s.add(sessId);
                t.classList.toggle('active', s.has(sessId));
                syncUrl(); break;
            }
            case 'select-all':
                CATEGORIES[cat].sessions.forEach(s => state.catSessions[cat].add(s.id));
                rerenderPills(cat); syncUrl(); break;
            case 'clear':
                state.catSessions[cat].clear();
                rerenderPills(cat); syncUrl(); break;
        }
    }

    function onGlobalSelectAll() {
        for (const k of Object.keys(CATEGORIES)) {
            state.catEnabled[k] = true;
            CATEGORIES[k].sessions.forEach(s => state.catSessions[k].add(s.id));
        }
        renderCategories(); syncUrl();
    }
    function onGlobalClear() {
        for (const k of Object.keys(CATEGORIES)) state.catSessions[k].clear();
        renderCategories(); syncUrl();
    }

    // ─────────────────────────────────────────────────
    //  COPY URL
    // ─────────────────────────────────────────────────
    async function handleCopy() {
        const val = document.getElementById('urlOutput')?.value;
        if (!val) return;
        try { await navigator.clipboard.writeText(val); }
        catch { const i = document.getElementById('urlOutput'); i.select(); document.execCommand('copy'); }
        const span = document.getElementById('copyText');
        const orig = span.textContent;
        span.textContent = '¡Copiado! ✓';
        setTimeout(() => { span.textContent = orig; }, 2200);
    }

    // ─────────────────────────────────────────────────
    //  RACE DATA + COUNTDOWN
    // ─────────────────────────────────────────────────
    const SERIES_MAP = {
        f1: { keywords: ['🏎️', 'formula 1', 'f1', 'grand prix'], icon: '🏎️', logo: '/f1.svg' },
        gt: { keywords: ['🏁', 'gt', 'grand touring', 'endurance'], icon: '🏁', logo: '/gt.svg' },
        nascar: { keywords: ['nascar', 'cup series'], icon: '🏁', logo: '/nascar.svg' },
        motogp: { keywords: ['🏍️', 'motogp'], icon: '🏍️', logo: '/motogp.svg' },
    };

    function detectSeries(ev) {
        const tl = ev.title.toLowerCase();
        if (ev.title.includes('🏍️') || tl.includes('motogp')) return SERIES_MAP.motogp;
        if (tl.includes('nascar')) return SERIES_MAP.nascar;
        if (ev.title.includes('🏁') || tl.includes('gt round') || tl.includes('gt prologue')) return SERIES_MAP.gt;
        if (ev.title.includes('🏎️') || tl.includes('formula') || tl.includes('grand prix')) return SERIES_MAP.f1;
        for (const [, cfg] of Object.entries(SERIES_MAP))
            if (cfg.keywords.some(k => tl.includes(k))) return cfg;
        return null;
    }

    function cleanTitle(t) {
        return t.replace(/[\u{1F300}-\u{1F9FF}]/gu, '').replace(/^(NASCAR[^:]*:)\s*/i, '').split(',')[0].trim();
    }

    function processRaceData(data) {
        const now = new Date();
        return data.flatMap(ev => {
            const series = detectSeries(ev);
            const logo = series?.logo || '/logo.svg';
            const icon = series?.icon || '🏆';
            const name = cleanTitle(ev.title);
            const circuit = ev.location ? ev.location.split(',')[0].trim() : '';
            if (Array.isArray(ev.sessions) && ev.sessions.length) {
                return ev.sessions
                    .map(s => ({ ...s, d: new Date(s.start) }))
                    .filter(s => s.d > now && /carrera|race/i.test(s.name))
                    .map(s => ({ name, circuit, date: s.d, logo, icon }));
            }
            if (ev.start) { const d = new Date(ev.start); return d > now ? [{ name, circuit, date: d, logo, icon }] : []; }
            return [];
        }).sort((a, b) => a.date - b.date).slice(0, 3);
    }

    async function loadRaceData() {
        const endpoints = ['/data/formula1.json', '/data/gtworld.json', '/data/nascar.json', '/data/motogp.json'];
        try {
            const results = await Promise.allSettled(
                endpoints.map(u => fetch(u).then(r => r.ok ? r.json() : []))
            );
            const all = results.flatMap(r => r.status === 'fulfilled' ? r.value : []);
            const races = processRaceData(all);
            state.races = races; state.loading = false;
            renderCountdown(races);
        } catch { state.loading = false; document.getElementById('loading-skeleton')?.classList.add('hidden'); }
    }

    function renderCountdown(races) {
        const loadEl = document.getElementById('loading-skeleton');
        const contentEl = document.getElementById('races-content');
        if (!races.length) { loadEl?.classList.add('hidden'); return; }
        loadEl?.classList.add('hidden');
        contentEl?.classList.remove('hidden');

        const tz = window.apexTz || Intl.DateTimeFormat().resolvedOptions().timeZone || 'Europe/Madrid';

        const fmtDate = d => {
            try {
                return new Intl.DateTimeFormat('es-ES', { timeZone: tz, day: '2-digit', month: '2-digit' }).format(d);
            } catch { return d.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' }); }
        };
        const fmtTime = d => {
            try {
                return new Intl.DateTimeFormat('es-ES', { timeZone: tz, hour: '2-digit', minute: '2-digit', hour12: false }).format(d);
            } catch { return '--:--'; }
        };
        const fmtFull = d => {
            try {
                return new Intl.DateTimeFormat('es-ES', {
                    timeZone: tz, weekday: 'short', day: 'numeric', month: 'short',
                    hour: '2-digit', minute: '2-digit', hour12: false
                }).format(d);
            } catch { return d.toLocaleString('es-ES'); }
        };
        const tzAbbr = d => {
            try {
                return new Intl.DateTimeFormat('es-ES', { timeZone: tz, timeZoneName: 'short' })
                    .formatToParts(d).find(p => p.type === 'timeZoneName')?.value || '';
            } catch { return ''; }
        };

        const main = races[0];
        const nameEl = document.getElementById('r1-name');
        if (nameEl) {
            nameEl.innerHTML = '';
            const img = document.createElement('img');
            img.src = main.logo; img.className = 'cat-logo mr-1.5 inline-block align-middle flex-shrink-0';
            img.style.height = '18px'; img.style.maxHeight = '18px';
            img.style.filter = 'brightness(0) opacity(0.75)';
            nameEl.append(img, document.createTextNode(main.name));
        }
        const circEl = document.getElementById('r1-circuit');
        if (circEl) circEl.textContent = main.circuit;

        // Show race start time converted to selected timezone
        const startEl = document.getElementById('r1-start-time');
        if (startEl) {
            const abbr = tzAbbr(main.date);
            startEl.textContent = `Inicio: ${fmtFull(main.date)}${abbr ? ' · ' + abbr : ''}`;
        }

        // Next two races — date + time in selected timezone
        [[races[1], 'r2'], [races[2], 'r3']].forEach(([r, id]) => {
            if (!r) return;
            const icon = document.getElementById(`${id}-icon`);
            const name = document.getElementById(`${id}-name`);
            const date = document.getElementById(`${id}-date`);
            if (icon) icon.textContent = r.icon;
            if (name) name.textContent = r.name;
            if (date) date.textContent = `${fmtDate(r.date)} · ${fmtTime(r.date)}`;
        });
        startCountdown(main.date);
    }

    function startCountdown(target) {
        const tick = () => {
            const diff = target - new Date();
            if (diff <= 0) { location.reload(); return; }
            const pad = n => String(Math.floor(n)).padStart(2, '0');
            document.getElementById('d-days').textContent = pad(diff / 86400000);
            document.getElementById('d-hours').textContent = pad((diff % 86400000) / 3600000);
            document.getElementById('d-mins').textContent = pad((diff % 3600000) / 60000);
            document.getElementById('d-secs').textContent = pad((diff % 60000) / 1000);
            requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
    }

    // ─────────────────────────────────────────────────
    //  TIMEZONE MODULE
    // ─────────────────────────────────────────────────
    const TZ_OPTIONS = [
        { tz: 'Pacific/Honolulu', label: 'UTC−10  · Hawaii' },
        { tz: 'America/Anchorage', label: 'UTC−9   · Alaska' },
        { tz: 'America/Los_Angeles', label: 'UTC−8   · Los Ángeles (PST)' },
        { tz: 'America/Denver', label: 'UTC−7   · Denver (MST)' },
        { tz: 'America/Chicago', label: 'UTC−6   · Chicago (CST)' },
        { tz: 'America/New_York', label: 'UTC−5   · Nueva York (EST)' },
        { tz: 'America/Sao_Paulo', label: 'UTC−3   · São Paulo' },
        { tz: 'America/Buenos_Aires', label: 'UTC−3   · Buenos Aires' },
        { tz: 'UTC', label: 'UTC+0   · Universal (UTC)' },
        { tz: 'Europe/London', label: 'UTC+0/1 · Londres (GMT/BST)' },
        { tz: 'Europe/Madrid', label: 'UTC+1/2 · Madrid (CET/CEST)' },
        { tz: 'Europe/Paris', label: 'UTC+1/2 · París' },
        { tz: 'Europe/Berlin', label: 'UTC+1/2 · Berlín' },
        { tz: 'Europe/Rome', label: 'UTC+1/2 · Roma' },
        { tz: 'Europe/Amsterdam', label: 'UTC+1/2 · Ámsterdam' },
        { tz: 'Europe/Helsinki', label: 'UTC+2/3 · Helsinki' },
        { tz: 'Europe/Moscow', label: 'UTC+3   · Moscú' },
        { tz: 'Asia/Dubai', label: 'UTC+4   · Dubái' },
        { tz: 'Asia/Karachi', label: 'UTC+5   · Karachi' },
        { tz: 'Asia/Kolkata', label: 'UTC+5:30· Mumbai/Delhi' },
        { tz: 'Asia/Bangkok', label: 'UTC+7   · Bangkok' },
        { tz: 'Asia/Singapore', label: 'UTC+8   · Singapur' },
        { tz: 'Asia/Tokyo', label: 'UTC+9   · Tokio' },
        { tz: 'Australia/Sydney', label: 'UTC+10/11· Sydney' },
        { tz: 'Pacific/Auckland', label: 'UTC+12  · Auckland' },
    ];

    let currentTz = 'Europe/Madrid';
    window.apexTz = currentTz;

    function buildTzSelect() {
        const sel = document.getElementById('tzSelect');
        if (!sel) return;
        sel.innerHTML = '';
        TZ_OPTIONS.forEach(({ tz, label }) => {
            const opt = document.createElement('option');
            opt.value = tz; opt.textContent = label;
            if (tz === currentTz) opt.selected = true;
            sel.appendChild(opt);
        });
    }

    function applyTimezone(tz, source = 'manual') {
        // Validate — fallback to Madrid if unknown
        if (!TZ_OPTIONS.some(o => o.tz === tz)) tz = 'Europe/Madrid';
        currentTz = tz;
        window.apexTz = tz;

        // Sync dropdown value
        const sel = document.getElementById('tzSelect');
        if (sel && sel.value !== tz) sel.value = tz;

        // Update badge
        const badge = document.getElementById('tzBadge');
        if (badge) {
            const cfg = {
                ip: { icon: '📡', text: 'Detectado por IP', cls: 'tz-badge detected' },
                browser: { icon: '🌐', text: 'Detectado (navegador)', cls: 'tz-badge detected' },
                manual: { icon: '✎', text: 'Manual', cls: 'tz-badge' },
            };
            const { icon, text, cls } = cfg[source] || cfg.manual;
            badge.innerHTML = `${icon} ${text}`;
            badge.className = cls;
        }

        // Re-render race times if data is already loaded
        if (state.races.length) renderCountdown(state.races);

        // Rebuild URL with new tz
        syncUrl();
    }

    function updateLocalClock() {
        const el = document.getElementById('tzLocalTime');
        if (!el) return;
        try {
            const now = new Date();
            const timeStr = new Intl.DateTimeFormat('es-ES', {
                timeZone: currentTz,
                weekday: 'short', month: 'short', day: 'numeric',
                hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
            }).format(now);
            // Compute UTC offset for display
            const tzOffset = new Intl.DateTimeFormat('en', {
                timeZone: currentTz, timeZoneName: 'shortOffset'
            }).formatToParts(now).find(p => p.type === 'timeZoneName')?.value || '';
            el.textContent = `${timeStr}${tzOffset ? '  (' + tzOffset + ')' : ''}`;
        } catch {
            el.textContent = new Date().toLocaleTimeString('es-ES');
        }
    }

    async function detectTimezone() {
        // 1. Try IP geolocation
        try {
            const ctrl = new AbortController();
            const tid = setTimeout(() => ctrl.abort(), 4000);
            const res = await fetch('https://ipapi.co/json/', { signal: ctrl.signal });
            clearTimeout(tid);
            if (res.ok) {
                const data = await res.json();
                if (data.timezone && TZ_OPTIONS.some(o => o.tz === data.timezone)) {
                    applyTimezone(data.timezone, 'ip');
                    buildTzSelect(); // rebuild to select the new value
                    return;
                }
            }
        } catch { /* network error or abort — fall through */ }

        // 2. Browser Intl API
        try {
            const detected = Intl.DateTimeFormat().resolvedOptions().timeZone;
            if (detected && TZ_OPTIONS.some(o => o.tz === detected)) {
                applyTimezone(detected, 'browser');
                buildTzSelect();
                return;
            }
        } catch { /* ignore */ }

        // 3. Default: Madrid
        applyTimezone('Europe/Madrid', 'manual');
    }

    function handleGcal() {
        const url = document.getElementById('urlOutput')?.value;
        if (!url) return;
        const webcal = url.replace(/^https?:\/\//, 'webcal://');
        window.open(`https://calendar.google.com/calendar/r?cid=${encodeURIComponent(webcal)}`, '_blank');
    }

    function initTimezone() {
        buildTzSelect();
        document.getElementById('tzSelect')
            ?.addEventListener('change', e => applyTimezone(e.target.value, 'manual'));
        // Clock: update every second
        updateLocalClock();
        setInterval(updateLocalClock, 1000);
        // Auto-detect asynchronously (doesn't block render)
        detectTimezone();
    }

    // ─────────────────────────────────────────────────
    //  BOOT
    // ─────────────────────────────────────────────────
    function init() {
        renderCategories();
        syncUrl();
        document.getElementById('categories-grid')?.addEventListener('click', onGridClick);
        document.getElementById('globalSelectAll')?.addEventListener('click', onGlobalSelectAll);
        document.getElementById('globalClear')?.addEventListener('click', onGlobalClear);
        document.getElementById('copyBtn')?.addEventListener('click', handleCopy);
        document.getElementById('gcalBtn')?.addEventListener('click', handleGcal);
        initTimezone();
        loadRaceData();
    }

    document.readyState === 'loading'
        ? document.addEventListener('DOMContentLoaded', init)
        : init();
})();


/* ════════════════════════════════════════════════════
     THEME TOGGLE LOGIC
════════════════════════════════════════════════════ */
(() => {
    'use strict';

    const STORAGE_KEY = 'apex-theme';
    const root = document.documentElement;
    const btn = document.getElementById('theme-toggle');
    const icon = document.getElementById('theme-toggle-icon');
    const iconSun = document.getElementById('icon-sun');
    const iconMoon = document.getElementById('icon-moon');

    // ── Apply theme ──────────────────────────────────────
    function applyTheme(theme, animate) {
        root.dataset.theme = theme;
        const isDark = theme === 'dark';

        // Swap icons
        iconSun.style.display = isDark ? 'none' : 'block';
        iconMoon.style.display = isDark ? 'block' : 'none';

        // Animate button icon
        if (animate) {
            icon.classList.add('is-spinning');
            icon.addEventListener('transitionend', () => {
                icon.classList.remove('is-spinning');
            }, { once: true });
        }

        // Persist
        try { localStorage.setItem(STORAGE_KEY, theme); } catch (e) { }
    }

    // ── Toggle ───────────────────────────────────────────
    btn.addEventListener('click', () => {
        const current = root.dataset.theme === 'dark' ? 'dark' : 'light';
        const next = current === 'dark' ? 'light' : 'dark';
        applyTheme(next, true);
    });

    // ── Init: read preference ────────────────────────────
    let saved = null;
    try { saved = localStorage.getItem(STORAGE_KEY); } catch (e) { }

    // Fall back to OS preference
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const initial = saved || (prefersDark ? 'dark' : 'light');
    applyTheme(initial, false);

    // Listen for OS theme changes (if user hasn't overridden)
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
        let stored = null;
        try { stored = localStorage.getItem(STORAGE_KEY); } catch (ex) { }
        if (!stored) applyTheme(e.matches ? 'dark' : 'light', false);
    });
})();
