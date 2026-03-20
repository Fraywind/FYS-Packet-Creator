/* FYS Packet Creator - Frontend Logic */

document.addEventListener('DOMContentLoaded', () => {
    const fileSaved = document.getElementById('file-saved');
    const fileCurrent = document.getElementById('file-current');
    const fileHolygrail = document.getElementById('file-holygrail');
    const btnGenerate = document.getElementById('btn-generate');
    const btnDownloadAll = document.getElementById('btn-download-all');
    const btnClosePreview = document.getElementById('btn-close-preview');
    const searchInput = document.getElementById('search-dept');

    let departmentsData = [];

    // File input change handlers
    function setupFileInput(input, nameId, boxId) {
        input.addEventListener('change', () => {
            const nameEl = document.getElementById(nameId);
            const boxEl = document.getElementById(boxId);
            if (input.files.length > 0) {
                nameEl.textContent = input.files[0].name;
                boxEl.classList.add('has-file');
            } else {
                nameEl.textContent = '';
                boxEl.classList.remove('has-file');
            }
            checkCanGenerate();
        });
    }

    setupFileInput(fileSaved, 'name-saved', 'box-saved');
    setupFileInput(fileCurrent, 'name-current', 'box-current');
    setupFileInput(fileHolygrail, 'name-holygrail', 'box-holygrail');

    function checkCanGenerate() {
        const hasFile = fileSaved.files.length > 0 ||
                        fileCurrent.files.length > 0 ||
                        fileHolygrail.files.length > 0;
        btnGenerate.disabled = !hasFile;
    }

    // Generate button
    btnGenerate.addEventListener('click', async () => {
        // Upload files first
        const formData = new FormData();
        if (fileSaved.files.length > 0)
            formData.append('saved_xlsx', fileSaved.files[0]);
        if (fileCurrent.files.length > 0)
            formData.append('application_current_xlsx', fileCurrent.files[0]);
        if (fileHolygrail.files.length > 0)
            formData.append('holygrail_xlsx', fileHolygrail.files[0]);

        // Show progress
        document.getElementById('progress-section').classList.remove('hidden');
        document.getElementById('results-section').classList.add('hidden');
        document.getElementById('preview-section').classList.add('hidden');

        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');

        progressFill.style.width = '20%';
        progressText.textContent = 'Uploading spreadsheets...';

        try {
            // Upload
            const uploadRes = await fetch('/upload', {
                method: 'POST',
                body: formData,
            });
            const uploadData = await uploadRes.json();

            if (uploadData.status !== 'ok') {
                progressText.textContent = 'Upload failed: ' + JSON.stringify(uploadData);
                return;
            }

            progressFill.style.width = '40%';
            progressText.textContent = 'Generating PDF packets for all departments...';

            // Generate
            const genRes = await fetch('/generate', { method: 'POST' });
            const genData = await genRes.json();

            progressFill.style.width = '80%';
            progressText.textContent = 'Loading results...';

            if (genData.status !== 'ok') {
                progressText.textContent = 'Generation failed: ' + (genData.message || JSON.stringify(genData));
                progressFill.style.width = '100%';
                return;
            }

            // Load department listing
            const deptRes = await fetch('/departments');
            departmentsData = await deptRes.json();

            progressFill.style.width = '100%';
            progressText.textContent = 'Done!';

            // Show results
            setTimeout(() => {
                document.getElementById('progress-section').classList.add('hidden');
                showResults(genData.results, departmentsData);
            }, 500);

        } catch (err) {
            progressText.textContent = 'Error: ' + err.message;
            progressFill.style.width = '100%';
        }
    });

    function showResults(results, departments) {
        const section = document.getElementById('results-section');
        section.classList.remove('hidden');

        // Stats
        const statsBar = document.getElementById('stats-bar');
        statsBar.innerHTML = `
            <div class="stat">Departments: <span class="stat-value">${departments.length}</span></div>
            <div class="stat">PDFs Generated: <span class="stat-value">${results.pdfs_generated}</span></div>
            ${results.errors.length > 0 ? `<div class="stat">Warnings: <span class="stat-value" style="color:#c62828">${results.errors.length}</span></div>` : ''}
        `;

        renderDepartments(departments);
    }

    function renderDepartments(departments) {
        const grid = document.getElementById('dept-grid');
        grid.innerHTML = '';

        departments.forEach(dept => {
            const card = document.createElement('div');
            card.className = 'dept-card';
            card.dataset.code = dept.code.toLowerCase();
            card.dataset.fullname = dept.full_name.toLowerCase();

            const pdfBadges = dept.pdfs
                .filter(f => !f.startsWith('ALL'))
                .map(f => {
                    const shortName = f.length > 35 ? f.substring(0, 32) + '...' : f;
                    return `<span class="pdf-badge" title="${f}" data-dept="${dept.code}" data-file="${f}">${shortName}</span>`;
                })
                .join('');

            card.innerHTML = `
                <div class="dept-card-header">
                    <span class="dept-code">[${dept.code}]</span>
                </div>
                <div class="dept-full-name">${dept.full_name}</div>
                <div class="dept-pdfs">${pdfBadges}</div>
                <div class="dept-actions">
                    <button class="btn-preview" data-dept="${dept.code}">Preview Combined</button>
                    <button class="btn-download" data-dept="${dept.code}">Download ZIP</button>
                </div>
            `;

            grid.appendChild(card);
        });

        // Attach event listeners
        grid.querySelectorAll('.pdf-badge').forEach(badge => {
            badge.addEventListener('click', () => {
                const dept = badge.dataset.dept;
                const file = badge.dataset.file;
                showPreview(dept, file);
            });
        });

        grid.querySelectorAll('.btn-preview').forEach(btn => {
            btn.addEventListener('click', () => {
                const dept = btn.dataset.dept;
                const deptData = departments.find(d => d.code === dept);
                const combined = deptData.pdfs.find(f => f.startsWith('ALL'));
                if (combined) {
                    showPreview(dept, combined);
                } else if (deptData.pdfs.length > 0) {
                    showPreview(dept, deptData.pdfs[0]);
                }
            });
        });

        grid.querySelectorAll('.btn-download').forEach(btn => {
            btn.addEventListener('click', () => {
                window.location.href = `/download/department/${btn.dataset.dept}`;
            });
        });
    }

    function showPreview(dept, filename) {
        const section = document.getElementById('preview-section');
        section.classList.remove('hidden');
        document.getElementById('preview-title').textContent = `Preview: [${dept}] - ${filename}`;
        document.getElementById('pdf-preview').src = `/preview/${dept}/${encodeURIComponent(filename)}`;
        section.scrollIntoView({ behavior: 'smooth' });
    }

    // Close preview
    btnClosePreview.addEventListener('click', () => {
        document.getElementById('preview-section').classList.add('hidden');
        document.getElementById('pdf-preview').src = 'about:blank';
    });

    // Download all
    btnDownloadAll.addEventListener('click', () => {
        window.location.href = '/download/all';
    });

    // Search
    searchInput.addEventListener('input', () => {
        const query = searchInput.value.toLowerCase().trim();
        document.querySelectorAll('.dept-card').forEach(card => {
            const match = card.dataset.code.includes(query) ||
                          card.dataset.fullname.includes(query);
            card.style.display = match ? '' : 'none';
        });
    });
});
