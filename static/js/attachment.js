let uploadModal;

$(document).ready(function() {
    uploadModal = new bootstrap.Modal(document.getElementById('uploadModal'));
    initAttachmentPage();
});

async function initAttachmentPage() {
    const now = new Date();
    for (let y = now.getFullYear(); y >= 2022; y--) {
        $('#filter-year, #upload-year').append(`<option value="${y}">${y}年</option>`);
    }

    $('#filter-year').val(now.getFullYear());
    $('#filter-month').val(now.getMonth() + 1);
    $('#upload-year').val(now.getFullYear());
    $('#upload-month').val(now.getMonth() + 1);

    const depts = await (await fetch('/api/options/department')).json();
    depts.forEach(o => $('#upload-dept').append(`<option value="${o.value}">${o.value}</option>`));

    const adminInfo = await checkAdmin();
    refreshAttachmentAdminState(adminInfo.is_admin);
    await Promise.all([loadCoverage(), loadAttachments()]);
}

function refreshAttachmentAdminState(isAdmin) {
    $('#btn-upload').prop('disabled', !isAdmin);
}

window.onAdminChange = function(isAdmin) {
    refreshAttachmentAdminState(isAdmin);
    loadAttachments();
};

$('#btn-search').click(async function() {
    await Promise.all([loadCoverage(), loadAttachments()]);
});

async function loadCoverage() {
    const year = $('#filter-year').val();
    const month = $('#filter-month').val();

    if (!year || !month) {
        $('#coverage-summary').text('请选择年份和月份');
        $('#coverage-grid').html('<div class="empty-state">请选择年份和月份后查看附件完整性</div>');
        return;
    }

    const res = await fetch(`/api/attachments/coverage?year=${year}&month=${month}`);
    const data = await res.json();
    if (!res.ok) {
        $('#coverage-summary').text(data.msg || '完整性数据加载失败');
        $('#coverage-grid').html('<div class="empty-state">完整性数据加载失败</div>');
        return;
    }

    const completion = data.total_departments
        ? (data.uploaded_departments / data.total_departments) * 100
        : 0;
    $('#coverage-summary').text(
        `覆盖率 ${formatPercent(completion)}，已上传 ${data.uploaded_departments} 个部门，缺失 ${data.missing_departments} 个部门`
    );

    $('#coverage-grid').html(`
        <div class="coverage-summary-rich">
            <div class="coverage-stat">
                <div class="coverage-stat-label">已上传部门</div>
                <div class="coverage-stat-value">${data.uploaded_departments}</div>
            </div>
            <div class="coverage-stat">
                <div class="coverage-stat-label">缺失部门</div>
                <div class="coverage-stat-value">${data.missing_departments}</div>
            </div>
            <div class="coverage-stat">
                <div class="coverage-stat-label">当前覆盖率</div>
                <div class="coverage-stat-value">${formatPercent(completion)}</div>
            </div>
        </div>
        <div class="mb-3">
            <div class="coverage-progress">
                <div class="coverage-progress-bar" style="width:${completion}%"></div>
            </div>
        </div>
        <div class="row g-2">
            ${data.items.map(item => `
                <div class="col-md-3 col-sm-6">
                    <div class="attachment-coverage-card ${item.uploaded ? 'is-uploaded' : 'is-missing'}">
                        <div class="d-flex align-items-center gap-2">
                            <span class="coverage-state-dot"></span>
                            <div class="fw-semibold">${escHtml(item.department)}</div>
                        </div>
                        <div class="small mt-2">${item.uploaded ? `已上传 ${item.file_count} 个附件` : '未上传附件'}</div>
                    </div>
                </div>
            `).join('')}
        </div>
    `);
}

async function loadAttachments() {
    const year = $('#filter-year').val();
    const month = $('#filter-month').val();
    const params = new URLSearchParams();
    if (year) params.set('year', year);
    if (month) params.set('month', month);

    const res = await fetch('/api/attachments?' + params.toString());
    const data = await res.json();
    const adminInfo = await checkAdmin();
    const isAdmin = adminInfo.is_admin;

    const container = $('#attachment-list');
    const totalFiles = data.reduce((sum, group) => sum + Number(group.count || 0), 0);
    $('#attachment-group-meta').text(data.length ? `共 ${data.length} 个分组 · ${totalFiles} 个附件` : '当前无归档分组');
    if (data.length === 0) {
        container.html('<div class="empty-state">当前筛选下暂无附件数据</div>');
        return;
    }

    container.html(`
        <div class="attachment-archive-grid">
            ${data.map(g => `
                <div class="attachment-group-card">
                    <div class="group-header">
                        <div>
                            <h3 class="group-title">${g.year}年${g.month}月 · ${escHtml(g.department)}</h3>
                            <div class="group-subtitle">按部门归档的采购附件</div>
                        </div>
                        <span class="file-count-badge">${g.count} 个附件</span>
                    </div>
                    <div class="file-list">
                        ${g.files.map(f => `
                            <div class="file-row">
                                <div class="file-row-main">
                                    <span class="file-type-badge">${getFileExtension(f.original_name)}</span>
                                    <div class="min-w-0">
                                        <a class="file-name" href="/api/attachments/${f.id}/download">${escHtml(f.original_name)}</a>
                                        ${f.description ? `<div class="file-desc">${escHtml(f.description)}</div>` : ''}
                                        <div class="file-meta">
                                            <span class="file-meta-chip">${formatSize(f.file_size)}</span>
                                            <span class="file-meta-chip">${escHtml(f.upload_time || '-')}</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="file-row-actions">
                                    <a class="btn btn-sm btn-outline-primary" href="/api/attachments/${f.id}/download">下载</a>
                                    ${isAdmin ? `<button class="btn btn-sm btn-outline-danger" onclick="deleteAttachment(${f.id})">删除</button>` : ''}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `).join('')}
        </div>
    `);
}

function getFileExtension(filename) {
    const parts = String(filename || '').split('.');
    if (parts.length <= 1) return 'FILE';
    return parts.pop().slice(0, 4).toUpperCase();
}

function formatSize(bytes) {
    if (!bytes) return '-';
    if (bytes < 1024) return bytes + 'B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB';
    return (bytes / 1024 / 1024).toFixed(1) + 'MB';
}

function escHtml(s) {
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

$('#btn-upload').click(() => uploadModal.show());

$('#btn-do-upload').click(async function() {
    const files = document.getElementById('upload-file').files;
    const uploadBtn = this;
    if (!files.length) {
        showToast('请选择文件后再上传', 'warning');
        return;
    }

    const year = $('#upload-year').val();
    const month = $('#upload-month').val();
    const dept = $('#upload-dept').val();
    if (!year || !month || !dept) {
        showToast('请选择年份、月份和部门', 'warning');
        return;
    }

    let ok = 0;
    let fail = 0;

    setButtonBusy(uploadBtn, true, '上传中...');
    try {
        for (const file of files) {
            const fd = new FormData();
            fd.append('file', file);
            fd.append('year', year);
            fd.append('month', month);
            fd.append('department', dept);
            const desc = document.getElementById('upload-description').value.trim();
            if (desc) fd.append('description', desc);
            const res = await fetch('/api/attachments/upload', { method: 'POST', body: fd });
            res.ok ? ok++ : fail++;
        }

        uploadModal.hide();
        showToast(`上传完成：成功 ${ok} 个${fail ? `，失败 ${fail} 个` : ''}`, fail ? 'warning' : 'success', 3200);

        $('#filter-year').val(year);
        $('#filter-month').val(month);
        await Promise.all([loadCoverage(), loadAttachments()]);
    } finally {
        setButtonBusy(uploadBtn, false);
    }
});

window.deleteAttachment = async function(id) {
    if (!confirm('确定删除该附件？')) return;

    const res = await fetch(`/api/attachments/${id}`, { method: 'DELETE' });
    if (!res.ok) {
        const err = await res.json();
        showToast(err.msg || '删除失败', 'danger');
        return;
    }

    showToast('附件已删除', 'success');
    await Promise.all([loadCoverage(), loadAttachments()]);
};

window.onDataVersionChange = function() {
    loadAttachments();
};
