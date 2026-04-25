let table;

$(document).ready(function() {
    initFilters();
    initTable();
    initFormEvents();
});

async function initFilters() {
    // Year filter
    const now = new Date().getFullYear();
    for (let y = now; y >= 2022; y--) {
        $('#filter-year, #upload-year').append(`<option value="${y}">${y}年</option>`);
        $('#f-year').append(`<option value="${y}">${y}年</option>`);
    }

    // Load dropdown options
    const cats = await (await fetch('/api/options/asset_category')).json();
    cats.forEach(o => $('#f-category, #filter-dept').append(`<option value="${o.value}">${o.value}</option>`));
    const depts = await (await fetch('/api/options/department')).json();
    depts.forEach(o => {
        $('#f-dept').append(`<option value="${o.value}">${o.value}</option>`);
        $('#upload-dept').append(`<option value="${o.value}">${o.value}</option>`);
    });
    $('#filter-dept').prepend('<option value="">全部部门</option>');
    const statuses = await (await fetch('/api/options/status')).json();
    statuses.forEach(o => {
        $('#f-status').append(`<option value="${o.value}">${o.value}</option>`);
        $('#batch-status').append(`<option value="${o.value}">${o.value}</option>`);
    });
    $('#filter-status').prepend('<option value="">全部状态</option>');
}

function initTable() {
    table = $('#procurement-table').DataTable({
        serverSide: false,
        ajax: { url: '/api/procurements', dataSrc: 'items' },
        columns: [
            { data: null, orderable: false, render: (d,t,r) => `<input type="checkbox" class="row-check" data-id="${r.id}">` },
            { data: 'year', width: '50px' },
            { data: 'month', width: '40px', render: d => d + '月' },
            { data: 'asset_category', width: '80px' },
            { data: 'item_name', width: '120px' },
            { data: 'manufacturer', width: '100px' },
            { data: 'model', width: '100px' },
            { data: 'budget_qty', width: '50px' },
            { data: 'unit_price', width: '70px', render: d => '¥' + Number(d).toFixed(2) },
            { data: 'total_price', width: '80px', render: d => '¥' + Number(d).toFixed(2) },
            { data: 'department', width: '70px' },
            { data: 'requester_name', width: '70px' },
            { data: 'requester_id', width: '70px' },
            { data: 'asset_code', width: '90px' },
            { data: 'reason', width: '150px', render: d => d ? `<span title="${d}">${d.substring(0, 20)}${d.length > 20 ? '...' : ''}</span>` : '' },
            { data: 'remark', width: '100px', render: d => d ? `<span title="${d}">${d.substring(0, 15)}${d.length > 15 ? '...' : ''}</span>` : '' },
            { data: 'status', width: '60px', render: statusBadge },
            { data: null, orderable: false, width: '80px', render: (d,t,r) => {
                return `<button class="btn btn-sm btn-outline-primary admin-only" style="display:none" onclick="editRow(${r.id})">编辑</button> ` +
                       `<button class="btn btn-sm btn-outline-danger admin-only" style="display:none" onclick="deleteRow(${r.id})">删除</button>`;
            }},
        ],
        language: { url: '//cdn.datatables.net/plug-ins/1.13.8/i18n/zh.json' },
        pageLength: 20,
        drawCallback: function() {
            checkAdmin().then(isAdmin => {
                document.querySelectorAll('.admin-only').forEach(el => el.style.display = isAdmin ? '' : 'none');
            });
        }
    });
}

function statusBadge(s) {
    const cls = {'已申请': 'bg-info', '采购中': 'bg-warning', '已完成': 'bg-success'};
    return `<span class="badge ${cls[s] || 'bg-secondary'}">${s}</span>`;
}

// Search & reset
$('#btn-search').click(() => reloadTable());
$('#btn-reset').click(() => {
    $('#filter-year,#filter-month,#filter-dept,#filter-status,#filter-keyword').val('');
    reloadTable();
});

function reloadTable() {
    table.ajax.url('/api/procurements?' + $.param({
        year: $('#filter-year').val(),
        month: $('#filter-month').val(),
        department: $('#filter-dept').val(),
        status: $('#filter-status').val(),
        keyword: $('#filter-keyword').val(),
    })).load();
}

// Auto calculate total
$('#f-qty, #f-price').on('input', function() {
    const qty = parseFloat($('#f-qty').val()) || 0;
    const price = parseFloat($('#f-price').val()) || 0;
    $('#f-total').val('¥' + (qty * price).toFixed(2));
});

// Add new
$('#btn-add').click(function() {
    $('#edit-id').val('');
    $('#formModalLabel').text('新增采购申请');
    $('#formModal input:not([type=hidden]), #formModal textarea').val('');
    $('#f-year').val(new Date().getFullYear());
    $('#f-month').val(new Date().getMonth() + 1);
    $('#f-status').val('已申请');
    new bootstrap.Modal('#formModal').show();
});

// Save
$('#btn-save').click(async function() {
    const id = $('#edit-id').val();
    const data = {
        year: parseInt($('#f-year').val()),
        month: parseInt($('#f-month').val()),
        asset_category: $('#f-category').val(),
        item_name: $('#f-item').val(),
        manufacturer: $('#f-manufacturer').val(),
        model: $('#f-model').val(),
        budget_qty: parseInt($('#f-qty').val()),
        unit_price: parseFloat($('#f-price').val()),
        department: $('#f-dept').val(),
        requester_name: $('#f-name').val(),
        requester_id: $('#f-id').val(),
        asset_code: $('#f-asset-code').val(),
        reason: $('#f-reason').val(),
        remark: $('#f-remark').val(),
        status: $('#f-status').val(),
    };

    if (!data.item_name || !data.budget_qty || !data.unit_price || !data.department || !data.requester_name || !data.requester_id || !data.reason) {
        alert('请填写所有必填字段');
        return;
    }

    const url = id ? `/api/procurements/${id}` : '/api/procurements';
    const method = id ? 'PUT' : 'POST';
    const res = await fetch(url, { method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });

    if (res.ok) {
        bootstrap.Modal.getInstance('#formModal').hide();
        reloadTable();
    } else {
        const err = await res.json();
        alert(err.msg || '保存失败');
    }
});

// Edit
window.editRow = async function(id) {
    const res = await fetch(`/api/procurements`);
    const allData = await res.json();
    const item = allData.items.find(i => i.id === id);
    if (!item) return;

    $('#edit-id').val(id);
    $('#formModalLabel').text('编辑采购申请');
    $('#f-year').val(item.year);
    $('#f-month').val(item.month);
    $('#f-category').val(item.asset_category);
    $('#f-item').val(item.item_name);
    $('#f-manufacturer').val(item.manufacturer);
    $('#f-model').val(item.model);
    $('#f-qty').val(item.budget_qty);
    $('#f-price').val(item.unit_price);
    $('#f-total').val('¥' + item.total_price.toFixed(2));
    $('#f-dept').val(item.department);
    $('#f-name').val(item.requester_name);
    $('#f-id').val(item.requester_id);
    $('#f-asset-code').val(item.asset_code);
    $('#f-reason').val(item.reason);
    $('#f-remark').val(item.remark);
    $('#f-status').val(item.status);
    new bootstrap.Modal('#formModal').show();
};

// Delete
window.deleteRow = async function(id) {
    if (!confirm('确定删除该记录？')) return;
    const res = await fetch(`/api/procurements/${id}`, {method: 'DELETE'});
    if (res.ok) reloadTable();
    else alert('删除失败');
};

// Batch status
$('#check-all').on('change', function() {
    $('.row-check').prop('checked', this.checked);
    updateBatchBtn();
});
$(document).on('change', '.row-check', updateBatchBtn);

function updateBatchBtn() {
    const checked = $('.row-check:checked').length;
    $('#btn-batch-status').prop('disabled', !checked).text(checked ? `批量更新 (${checked})` : '批量更新状态');
}

$('#btn-batch-status').click(() => new bootstrap.Modal('#batchModal').show());

$('#btn-batch-confirm').click(async function() {
    const ids = $('.row-check:checked').map((_, el) => $(el).data('id')).get();
    const status = $('#batch-status').val();
    const res = await fetch('/api/procurements/batch-status', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ids, status}),
    });
    if (res.ok) {
        bootstrap.Modal.getInstance('#batchModal').hide();
        reloadTable();
    }
});

function initFormEvents() {}
