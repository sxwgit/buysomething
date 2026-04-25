$(document).ready(function() {
    initAttachmentPage();
});

async function initAttachmentPage() {
    const now = new Date();
    for (let y = now.getFullYear(); y >= 2022; y--) {
        $('#filter-year, #upload-year').append(`<option value="${y}">${y}年</option>`);
    }
    $('#filter-year').val(now.getFullYear());
    $('#upload-year').val(now.getFullYear());

    // Load departments for upload
    const depts = await (await fetch('/api/options/department')).json();
    depts.forEach(o => $('#upload-dept').append(`<option value="${o.value}">${o.value}</option>`));

    // Enable upload button when admin
    checkAdmin().then(isAdmin => {
        $('#btn-upload').prop('disabled', !isAdmin);
    });

    loadAttachments();
}

$('#btn-search').click(loadAttachments);

async function loadAttachments() {
    const year = $('#filter-year').val();
    const month = $('#filter-month').val();
    const params = new URLSearchParams();
    if (year) params.set('year', year);
    if (month) params.set('month', month);

    const res = await fetch('/api/attachments?' + params.toString());
    const data = await res.json();
    const isAdmin = await checkAdmin();

    const container = $('#attachment-list');
    if (data.length === 0) {
        container.html('<div class="text-muted text-center py-4">暂无附件数据</div>');
        return;
    }

    container.html(data.map(g => `
        <div class="card mb-2">
            <div class="card-header py-2 d-flex justify-content-between">
                <span>${g.year}年${g.month}月 - ${g.department} (${g.count}个附件)</span>
            </div>
            <div class="card-body p-0">
                <table class="table table-sm table-borderless mb-0">
                    ${g.files.map(f => `
                        <tr>
                            <td><a href="/api/attachments/${f.id}/download">${escHtml(f.original_name)}</a></td>
                            <td class="text-muted" style="width:150px">${f.upload_time}</td>
                            <td style="width:60px">${formatSize(f.file_size)}</td>
                            ${isAdmin ? `<td style="width:50px"><button class="btn btn-sm btn-outline-danger" onclick="deleteAttachment(${f.id})">删除</button></td>` : ''}
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
    if (bytes < 1024*1024) return (bytes/1024).toFixed(1) + 'KB';
    return (bytes/1024/1024).toFixed(1) + 'MB';
}

function escHtml(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// Upload
$('#btn-upload').click(() => new bootstrap.Modal('#uploadModal').show());

$('#btn-do-upload').click(async function() {
    const files = document.getElementById('upload-file').files;
    if (!files.length) { alert('请选择文件'); return; }
    const year = $('#upload-year').val();
    const month = $('#upload-month').val();
    const dept = $('#upload-dept').val();
    if (!year || !month || !dept) { alert('请选择年月和部门'); return; }

    let ok = 0, fail = 0;
    for (const file of files) {
        const fd = new FormData();
        fd.append('file', file);
        fd.append('year', year);
        fd.append('month', month);
        fd.append('department', dept);
        const res = await fetch('/api/attachments/upload', {method: 'POST', body: fd});
        res.ok ? ok++ : fail++;
    }
    bootstrap.Modal.getInstance('#uploadModal').hide();
    alert(`上传完成: 成功 ${ok} 个${fail ? ', 失败 ' + fail + ' 个' : ''}`);
    loadAttachments();
});

window.deleteAttachment = async function(id) {
    if (!confirm('确定删除该附件？')) return;
    await fetch(`/api/attachments/${id}`, {method: 'DELETE'});
    loadAttachments();
};
