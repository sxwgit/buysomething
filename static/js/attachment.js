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
        $('#coverage-grid').html('<div class="text-muted">请选择年份和月份后查看</div>');
        return;
    }

    const res = await fetch(`/api/attachments/coverage?year=${year}&month=${month}`);
    const data = await res.json();
    if (!res.ok) {
        $('#coverage-summary').text(data.msg || '完整性数据加载失败');
        $('#coverage-grid').html('<div class="text-danger">完整性数据加载失败</div>');
        return;
    }

    $('#coverage-summary').text(
        `已上传 ${data.uploaded_departments} 个部门，缺失 ${data.missing_departments} 个部门`
    );

    $('#coverage-grid').html(data.items.map(item => `
        <div class="col-md-3 col-sm-6">
            <div class="attachment-coverage-card ${item.uploaded ? 'is-uploaded' : 'is-missing'}">
                <div class="fw-semibold">${escHtml(item.department)}</div>
                <div class="small">${item.uploaded ? `已上传 ${item.file_count} 个附件` : '未上传附件'}</div>
            </div>
        </div>
    `).join(''));
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
    if (data.length === 0) {
        container.html('<div class="text-muted text-center py-4">当前筛选下暂无附件数据</div>');
        return;
    }

    container.html(data.map(g => `
        <div class="card mb-2">
            <div class="card-header py-2 d-flex justify-content-between">
                <span>${g.year}年${g.month}月 - ${escHtml(g.department)} (${g.count}个附件)</span>
            </div>
            <div class="card-body p-0">
                <table class="table table-sm table-borderless mb-0">
                    ${g.files.map(f => `
                        <tr>
                            <td><a href="/api/attachments/${f.id}/download">${escHtml(f.original_name)}</a></td>
                            <td class="text-muted" style="width:150px">${f.upload_time}</td>
                            <td style="width:70px">${formatSize(f.file_size)}</td>
                            ${isAdmin ? `<td style="width:60px"><button class="btn btn-sm btn-outline-danger" onclick="deleteAttachment(${f.id})">删除</button></td>` : ''}
                        </tr>
                    `).join('')}
                </table>
            </div>
        </div>
    `).join(''));
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
    if (!files.length) {
        alert('请选择文件');
        return;
    }

    const year = $('#upload-year').val();
    const month = $('#upload-month').val();
    const dept = $('#upload-dept').val();
    if (!year || !month || !dept) {
        alert('请选择年月和部门');
        return;
    }

    let ok = 0;
    let fail = 0;

    for (const file of files) {
        const fd = new FormData();
        fd.append('file', file);
        fd.append('year', year);
        fd.append('month', month);
        fd.append('department', dept);
        const res = await fetch('/api/attachments/upload', { method: 'POST', body: fd });
        res.ok ? ok++ : fail++;
    }

    uploadModal.hide();
    alert(`上传完成: 成功 ${ok} 个${fail ? ', 失败 ' + fail + ' 个' : ''}`);

    $('#filter-year').val(year);
    $('#filter-month').val(month);
    await Promise.all([loadCoverage(), loadAttachments()]);
}

window.deleteAttachment = async function(id) {
    if (!confirm('确定删除该附件？')) return;

    const res = await fetch(`/api/attachments/${id}`, { method: 'DELETE' });
    if (!res.ok) {
        const err = await res.json();
        alert(err.msg || '删除失败');
        return;
    }

    await Promise.all([loadCoverage(), loadAttachments()]);
};

window.onDataVersionChange = function() {
    loadAttachments();
};
