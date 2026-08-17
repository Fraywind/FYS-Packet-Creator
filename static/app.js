/* ─────────────────────────────────────────────────────────────
   FYS Packet Creator — Frontend Logic
   ───────────────────────────────────────────────────────── */

(function () {
    'use strict';

    const SOURCES = [
        { key: 'saved',     field: 'saved_xlsx',            friendly: 'Faculty Teaching History', inputId: 'file-saved' },
        { key: 'current',   field: 'current_seminars_xlsx', friendly: 'Current Seminars Offered', inputId: 'file-current' },
        { key: 'holygrail', field: 'holygrail_xlsx',        friendly: 'Prior-Year Evaluations',   inputId: 'file-holygrail' },
    ];

    const state = {
        files: {},          // key -> File
        departments: [],
        results: null,
    };

    /* ─── Init ─── */
    document.addEventListener('DOMContentLoaded', () => {
        setupDropzones();
        setupActions();
        setupSearchAndSort();
        setupPreview();
        updateRunStatus();
    });

    /* ─────────────────────────────────────────────────────────
       DROPZONES
       ──────────────────────────────────────────────────────── */
    function setupDropzones() {
        document.querySelectorAll('.dropzone').forEach(zone => {
            const key = zone.dataset.key;
            const input = zone.querySelector('input[type="file"]');
            const drop = zone.querySelector('.dz-drop');
            const replace = zone.querySelector('.dz-replace');

            // Click → browse
            drop.addEventListener('click', () => input.click());
            drop.addEventListener('keydown', e => {
                if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); }
            });

            // File chosen
            input.addEventListener('change', () => {
                if (input.files && input.files[0]) {
                    attachFile(zone, key, input.files[0]);
                }
            });

            // Replace
            if (replace) {
                replace.addEventListener('click', e => {
                    e.stopPropagation();
                    input.value = '';
                    delete state.files[key];
                    renderZone(zone, null);
                    updateRunStatus();
                });
            }

            // Drag & drop
            ['dragenter', 'dragover'].forEach(evt => {
                drop.addEventListener(evt, e => {
                    e.preventDefault();
                    e.stopPropagation();
                    drop.classList.add('is-dragover');
                });
            });
            ['dragleave', 'drop'].forEach(evt => {
                drop.addEventListener(evt, e => {
                    e.preventDefault();
                    e.stopPropagation();
                    drop.classList.remove('is-dragover');
                });
            });
            drop.addEventListener('drop', e => {
                if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
                    const file = e.dataTransfer.files[0];
                    if (!/\.xlsx?$/i.test(file.name)) {
                        flashStatus('That looks unlike an Excel file (.xlsx / .xls).', true);
                        return;
                    }
                    input.files = e.dataTransfer.files;
                    attachFile(zone, key, file);
                }
            });
        });

        // Prevent browser opening dropped files outside the dropzone
        ['dragover', 'drop'].forEach(evt => {
            window.addEventListener(evt, e => { e.preventDefault(); });
        });
    }

    function attachFile(zone, key, file) {
        state.files[key] = file;
        renderZone(zone, file);
        updateRunStatus();
    }

    function renderZone(zone, file) {
        const empty = zone.querySelector('.dz-empty');
        const filled = zone.querySelector('.dz-filled');
        const fnameEl = zone.querySelector('.dz-fname');

        if (file) {
            empty.hidden = true;
            filled.hidden = false;
            fnameEl.textContent = file.name;
            zone.classList.add('is-filled');
        } else {
            empty.hidden = false;
            filled.hidden = true;
            fnameEl.textContent = '—';
            zone.classList.remove('is-filled');
        }
    }

    /* ─────────────────────────────────────────────────────────
       ACTIONS (generate / reset / download)
       ──────────────────────────────────────────────────────── */
    function setupActions() {
        document.getElementById('btn-generate').addEventListener('click', runGeneration);

        document.getElementById('btn-reset').addEventListener('click', () => {
            SOURCES.forEach(s => {
                const zone = document.querySelector(`.dropzone[data-key="${s.key}"]`);
                const input = document.getElementById(s.inputId);
                input.value = '';
                renderZone(zone, null);
            });
            state.files = {};
            state.departments = [];
            state.results = null;
            document.getElementById('results-section').hidden = true;
            document.getElementById('progress-section').hidden = true;
            document.getElementById('errors-shelf').hidden = true;
            updateRunStatus();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });

        document.getElementById('btn-download-all').addEventListener('click', () => {
            window.location.href = '/download/all';
        });
    }

    function updateRunStatus() {
        const count = Object.keys(state.files).length;
        const btn = document.getElementById('btn-generate');
        const status = document.getElementById('run-status');

        if (count === 0) {
            btn.disabled = true;
            status.textContent = 'Choose at least one workbook to continue.';
            status.classList.remove('is-ready', 'is-error');
        } else {
            btn.disabled = false;
            const labels = Object.keys(state.files)
                .map(k => SOURCES.find(s => s.key === k).friendly)
                .join(' · ');
            status.textContent = `Ready with ${count} workbook${count > 1 ? 's' : ''} — ${labels}.`;
            status.classList.add('is-ready');
            status.classList.remove('is-error');
        }
    }

    function flashStatus(msg, isError) {
        const status = document.getElementById('run-status');
        status.textContent = msg;
        status.classList.toggle('is-error', !!isError);
        status.classList.remove('is-ready');
    }

    /* ─────────────────────────────────────────────────────────
       GENERATION
       ──────────────────────────────────────────────────────── */
    async function runGeneration() {
        if (Object.keys(state.files).length === 0) return;

        // Reveal progress, hide results
        const progress = document.getElementById('progress-section');
        const results = document.getElementById('results-section');
        progress.hidden = false;
        results.hidden = true;
        resetPhases();
        progress.scrollIntoView({ behavior: 'smooth', block: 'start' });

        try {
            // ── Phase 1: Upload ──
            activatePhase('upload', 'Uploading workbooks', 'Transferring your spreadsheets to the workbench.');
            setProgress(15);

            const formData = new FormData();
            SOURCES.forEach(s => {
                if (state.files[s.key]) formData.append(s.field, state.files[s.key]);
            });

            const uploadRes = await fetch('/upload', { method: 'POST', body: formData });
            const uploadData = await uploadRes.json();
            if (uploadData.status !== 'ok') throw new Error('Upload failed: ' + JSON.stringify(uploadData));
            completePhase('upload');

            // ── Phase 2: Read ──
            activatePhase('read', 'Reading workbooks', 'Parsing departments, faculty, and seminars.');
            setProgress(35);
            await sleep(200);

            // ── Phase 3: Generate ──
            activatePhase('generate', 'Generating PDFs', 'Composing each report for every department.');
            setProgress(55);

            const genRes = await fetch('/generate', { method: 'POST' });
            const genData = await genRes.json();
            completePhase('read');
            completePhase('generate');

            if (genData.status !== 'ok') {
                activatePhase('combine', 'Generation failed', genData.message || JSON.stringify(genData));
                setProgress(100);
                return;
            }

            // ── Phase 4: Combine ──
            activatePhase('combine', 'Combining packets', 'Stitching each department\'s PDFs together.');
            setProgress(80);

            const deptRes = await fetch('/departments');
            const departments = await deptRes.json();
            completePhase('combine');

            // ── Phase 5: Done ──
            activatePhase('done', 'Composition complete', 'Your packets are ready below.');
            setProgress(100);

            state.results = genData.results;
            state.departments = departments;

            await sleep(550);
            progress.hidden = true;
            renderResults();
        } catch (err) {
            console.error(err);
            const headline = document.getElementById('progress-headline');
            const detail = document.getElementById('progress-detail');
            headline.textContent = 'Something went wrong';
            detail.textContent = err.message || String(err);
            setProgress(100);
        }
    }

    function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

    /* ─── Phase machinery ─── */
    function resetPhases() {
        document.querySelectorAll('.phase').forEach(p => {
            p.classList.remove('is-active', 'is-done');
        });
        setProgress(0);
    }

    function activatePhase(phase, headline, detail) {
        document.querySelectorAll('.phase').forEach(p => p.classList.remove('is-active'));
        const el = document.querySelector(`.phase[data-phase="${phase}"]`);
        if (el) el.classList.add('is-active');
        document.getElementById('progress-headline').textContent = headline;
        document.getElementById('progress-detail').textContent = detail;
    }

    function completePhase(phase) {
        const el = document.querySelector(`.phase[data-phase="${phase}"]`);
        if (el) { el.classList.remove('is-active'); el.classList.add('is-done'); }
    }

    function setProgress(pct) {
        document.getElementById('progress-fill').style.width = pct + '%';
    }

    /* ─────────────────────────────────────────────────────────
       RESULTS RENDERING
       ──────────────────────────────────────────────────────── */
    function renderResults() {
        const section = document.getElementById('results-section');
        section.hidden = false;
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });

        const sub = document.getElementById('results-sub');
        const r = state.results || { pdfs_generated: 0, errors: [] };
        const deptCount = state.departments.length;
        const warns = r.errors ? r.errors.length : 0;

        sub.innerHTML = `
            <span class="stat-pill">${deptCount}</span> departments ·
            <span class="stat-pill">${r.pdfs_generated || 0}</span> PDFs composed
            ${warns > 0 ? ` · <span class="stat-pill is-warn">${warns}</span> warning${warns > 1 ? 's' : ''}` : ''}
        `;

        renderNotes(r);

        if (warns > 0) {
            const shelf = document.getElementById('errors-shelf');
            const list = document.getElementById('errors-list');
            list.innerHTML = '';
            r.errors.forEach(msg => {
                const li = document.createElement('li');
                li.textContent = msg;
                list.appendChild(li);
            });
            shelf.hidden = false;
        }

        renderDepartments(currentSort());
    }

    /* The run always writes a notes file recording what was produced, what was
       left out on purpose, and what changes next year. Show it here so nobody
       has to know to go looking for it in the output folder. */
    function renderNotes(r) {
        const shelf = document.getElementById('notes-shelf');
        if (!r.notes) { shelf.hidden = true; return; }

        const attention = r.attention || [];
        document.getElementById('notes-headline').textContent = attention.length
            ? attention.join(' · ')
            : 'Nothing needs a second look. The notes list what was produced and what changes next year.';
        document.getElementById('notes-body').textContent = r.notes;
        document.getElementById('notes-file').textContent = r.notes_filename || 'README.txt';
        shelf.classList.toggle('has-attention', attention.length > 0);
        shelf.hidden = false;
        shelf.open = false;
    }

    function currentSort() {
        return document.getElementById('sort-dept').value || 'code';
    }

    function renderDepartments(sortBy) {
        const grid = document.getElementById('dept-grid');
        grid.innerHTML = '';

        const sorted = [...state.departments].sort((a, b) => {
            if (sortBy === 'name') return (a.full_name || '').localeCompare(b.full_name || '');
            if (sortBy === 'count') return (b.pdfs || []).length - (a.pdfs || []).length;
            return (a.code || '').localeCompare(b.code || '');
        });

        sorted.forEach((dept, idx) => {
            const li = document.createElement('li');
            li.className = 'dept-row';
            li.dataset.code = (dept.code || '').toLowerCase();
            li.dataset.fullname = (dept.full_name || '').toLowerCase();

            const pdfTags = (dept.pdfs || [])
                .filter(f => !f.startsWith('ALL'))
                .map(f => {
                    const num = (f.match(/^(\d+)\./) || [, '·'])[1];
                    const niceName = f
                        .replace(/^\d+\.\s*\[[^\]]+\]\s*/, '')
                        .replace(/\.pdf$/i, '');
                    const safe = escapeHtml(f);
                    return `<button class="dept-pdf" data-dept="${escapeHtml(dept.code)}" data-file="${safe}" title="${safe}"><span class="dept-pdf-num">${num}</span>${escapeHtml(niceName)}</button>`;
                })
                .join('');

            const combinedFile = (dept.pdfs || []).find(f => f.startsWith('ALL'));

            li.innerHTML = `
                <div>
                    <span class="dept-code-num">№ ${String(idx + 1).padStart(2, '0')}</span>
                    <span class="dept-code">[${escapeHtml(dept.code)}]</span>
                </div>
                <div class="dept-main">
                    <p class="dept-fullname">${escapeHtml(dept.full_name || dept.code)}</p>
                    <div class="dept-pdfs">${pdfTags || '<span class="dept-pdf" style="cursor:default">No PDFs</span>'}</div>
                </div>
                <div class="dept-actions">
                    ${combinedFile ? `<button class="btn-tiny btn-preview-combined" data-dept="${escapeHtml(dept.code)}" data-file="${escapeHtml(combinedFile)}">Preview combined</button>` : ''}
                    <button class="btn-tiny btn-download-dept" data-dept="${escapeHtml(dept.code)}">Download ZIP</button>
                </div>
            `;

            grid.appendChild(li);
        });

        // Attach listeners
        grid.querySelectorAll('.dept-pdf[data-file]').forEach(b => {
            b.addEventListener('click', () => openPreview(b.dataset.dept, b.dataset.file));
        });
        grid.querySelectorAll('.btn-preview-combined').forEach(b => {
            b.addEventListener('click', () => openPreview(b.dataset.dept, b.dataset.file));
        });
        grid.querySelectorAll('.btn-download-dept').forEach(b => {
            b.addEventListener('click', () => {
                window.location.href = `/download/department/${encodeURIComponent(b.dataset.dept)}`;
            });
        });
    }

    /* ─────────────────────────────────────────────────────────
       SEARCH + SORT
       ──────────────────────────────────────────────────────── */
    function setupSearchAndSort() {
        const search = document.getElementById('search-dept');
        search.addEventListener('input', () => {
            const q = search.value.toLowerCase().trim();
            document.querySelectorAll('.dept-row').forEach(row => {
                const match = !q || row.dataset.code.includes(q) || row.dataset.fullname.includes(q);
                row.classList.toggle('is-hidden', !match);
            });
        });

        document.getElementById('sort-dept').addEventListener('change', () => {
            renderDepartments(currentSort());
            // Reapply search filter
            const evt = new Event('input');
            search.dispatchEvent(evt);
        });
    }

    /* ─────────────────────────────────────────────────────────
       PREVIEW DRAWER
       ──────────────────────────────────────────────────────── */
    function setupPreview() {
        document.getElementById('btn-close-preview').addEventListener('click', closePreview);
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') closePreview();
        });
    }

    function openPreview(dept, file) {
        const url = `/preview/${encodeURIComponent(dept)}/${encodeURIComponent(file)}`;
        document.getElementById('pdf-preview').src = url;
        document.getElementById('preview-eyebrow').textContent = `[${dept}]`;
        const niceName = file
            .replace(/^\d+\.\s*\[[^\]]+\]\s*/, '')
            .replace(/^ALL\s*\[[^\]]+\]\s*/, 'All — ')
            .replace(/\.pdf$/i, '');
        document.getElementById('preview-title').textContent = niceName;
        document.getElementById('preview-open-tab').href = url;
        document.getElementById('preview-section').hidden = false;
    }

    function closePreview() {
        document.getElementById('preview-section').hidden = true;
        document.getElementById('pdf-preview').src = 'about:blank';
    }

    /* ─── util ─── */
    function escapeHtml(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
})();
