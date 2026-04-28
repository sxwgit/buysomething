let table;
let formModal;
let batchModal;
let detailModal;
let selectedYears = [];
let selectedMonths = [];
let selectedDepartments = [];
let selectedStatuses = [];
let keywordTimer;
let departmentOptions = [];
let statusOptions = [];
let currentAdmin = false;
let editingCell = null;

$(document).ready(async function() {
    formModal = new bootstrap.Modal(document.getElementById('formModal'));
    batchModal = new bootstrap.Modal(document.getElementById('batchModal'));
    detailModal = new bootstrap.Modal(document.getElementById('detailModal'));

    const adminInfo = await checkAdmin();
    currentAdmin = !!adminInfo.is_admin;
    await initFilters();
    initTable();
    initFormEvents();
    await loadSummary();
});

async function initFilters() {
    const metadata = await (await fetch('/api/procurements/filter-metadata')).json();
    const yearOptions = [];
    for (const y of metadata.years) {
        $('#f-year').append(`<option value="${y}">${y}年</option>`);
        yearOptions.push({ value: String(y), label: `${y}年` });
    }
    renderMultiSelectMenu('year', yearOptions, selectedYears, '全部年份');

    const monthOptions = [];
    for (const m of metadata.months) {
        monthOptions.push({ value: String(m), label: `${String(m).padStart(2, '0')}月` });
    }
    renderMultiSelectMenu('month', monthOptions, selectedMonths, '全部月份');

    const cats = await (await fetch('/api/options/asset_category')).json();
    cats.forEach(o => $('#f-category').append(`<option value="${o.value}">${o.value}</option>`));

    const depts = await (await fetch('/api/options/department')).json();
    departmentOptions = depts.map(o => o.value);
    depts.forEach(o => {
        $('#f-dept').append(`<option value="${o.value}">${o.value}</option>`);
    });
    renderMultiSelectMenu(
        'department',
        depts.map(o => ({ value: o.value, label: o.value })),
        selectedDepartments,
        '全部部门'
    );

    const statuses = await (await fetch('/api/options/status')).json();
    statusOptions = statuses.map(o => o.value);
    statuses.forEach(o => {
        $('#f-status').append(`<option value="${o.value}">${o.value}</option>`);
        $('#batch-status').append(`<option value="${o.value}">${o.value}</option>`);
    });
    renderMultiSelectMenu(
        'status',
        statuses.map(o => ({ value: o.value, label: o.value })),
        selectedStatuses,
        '全部状态'
    );
}

function renderMultiSelectMenu(type, options, selectedValues, defaultLabel) {
    const menu = document.getElementById(`filter-${type}-menu`);
    const btn = document.getElementById(`filter-${type}-btn`);
    menu.addEventListener('click', function(event) {
        event.stopPropagation();
    });
    menu.innerHTML = `
        <div class="d-flex justify-content-between mb-2">
            <button type="button" class="btn btn-link btn-sm p-0" data-action="select-all">全选</button>
            <button type="button" class="btn btn-link btn-sm p-0" data-action="clear-all">清空</button>
        </div>
        <div class="filter-checklist">
            ${options.map(option => `
                <label class="filter-check-item">
                    <input class="form-check-input me-2" type="checkbox" value="${option.value}" ${selectedValues.includes(option.value) ? 'checked' : ''}>
                    <span>${option.label}</span>
                </label>
            `).join('')}
        </div>
    `;

    menu.querySelector('[data-action="select-all"]').addEventListener('click', function() {
        menu.querySelectorAll('input[type="checkbox"]').forEach(input => {
            input.checked = true;
        });
        syncMultiSelectState(type, defaultLabel);
    });

    menu.querySelector('[data-action="clear-all"]').addEventListener('click', function() {
        menu.querySelectorAll('input[type="checkbox"]').forEach(input => {
            input.checked = false;
        });
        syncMultiSelectState(type, defaultLabel);
    });

    menu.querySelectorAll('input[type="checkbox"]').forEach(input => {
        input.addEventListener('change', function() {
            syncMultiSelectState(type, defaultLabel);
        });
    });

    updateMultiSelectButton(type, defaultLabel);
}

function syncMultiSelectState(type, defaultLabel) {
    const menu = document.getElementById(`filter-${type}-menu`);
    const values = Array.from(menu.querySelectorAll('input[type="checkbox"]:checked')).map(el => el.value);
    if (type === 'year') selectedYears = values;
    if (type === 'month') selectedMonths = values;
    if (type === 'department') selectedDepartments = values;
    if (type === 'status') selectedStatuses = values;
    updateMultiSelectButton(type, defaultLabel);
    if (table) {
        reloadTable();
    }
}

function updateMultiSelectButton(type, defaultLabel) {
    const btn = document.getElementById(`filter-${type}-btn`);
    const values = {
        year: selectedYears,
        month: selectedMonths,
        department: selectedDepartments,
        status: selectedStatuses,
    }[type] || [];
    if (!values.length) {
        btn.textContent = defaultLabel;
        return;
    }
    if (values.length <= 2) {
        btn.textContent = values.map(v => {
            if (type === 'month') return `${String(v).padStart(2, '0')}月`;
            if (type === 'year') return `${v}年`;
            return v;
        }).join('、');
        return;
    }
    btn.textContent = `已选 ${values.length} 项`;
}

function initTable() {
    table = $('#procurement-table').DataTable({
        serverSide: true,
        processing: true,
        searching: false,
        ordering: false,
        ajax: {
            url: '/api/procurements',
            data: function(d) {
                appendFilterParams(d);
            },
            dataSrc: 'data',
        },
        columns: [
            { data: null, orderable: false, width: '32px', render: (d, t, r) => `<input type="checkbox" class="row-check" data-id="${r.id}">` },
            { data: null, orderable: false, width: '70px', render: renderPeriodCell },
            { data: null, width: '220px', render: renderItemCell },
            { data: null, width: '180px', render: renderRequesterCell },
            { data: 'budget_qty', width: '70px', render: (d, t, r) => renderEditableCell(r, 'budget_qty', d, 'number') },
            { data: 'unit_price', width: '90px', render: (d, t, r) => renderEditableCell(r, 'unit_price', formatCurrency(d), 'currency') },
            { data: 'total_price', width: '100px', render: d => formatCurrency(d) },
            { data: 'reason', width: '220px', render: (d, t, r) => renderEditableCell(r, 'reason', d || '-', 'textarea', 40) },
            { data: 'remark', width: '150px', render: (d, t, r) => renderEditableCell(r, 'remark', d || '-', 'textarea', 22) },
            { data: 'status', width: '130px', render: (d, t, r) => renderStatusCell(r) },
            { data: null, orderable: false, width: '150px', render: renderActionCell },
        ],
        language: {
            processing: '正在加载数据...',
            zeroRecords: '没有匹配的采购记录',
            emptyTable: '暂无采购数据',
            info: '显示第 _START_ 到 _END_ 条，共 _TOTAL_ 条',
            infoEmpty: '当前没有数据',
            paginate: {
                first: '首页',
                previous: '上一页',
                next: '下一页',
                last: '末页',
            },
        },
        pagingType: 'simple_numbers',
        pageLength: 20,
        drawCallback: function() {
            checkAdmin().then(info => {
                currentAdmin = !!info.is_admin;
                updateRowActionVisibility(info.is_admin);
                const paginate = document.querySelector('#procurement-table_wrapper .dataTables_paginate');
                if (paginate) {
                    paginate.style.display = table.page.info().pages > 1 ? '' : 'none';
                }
            });
        }
    });
}

function renderPeriodCell(_, __, row) {
    return `<div class="list-main-text">${row.year}年${row.month}月</div>
        <div class="list-sub-text">${escapeHtml(row.asset_category || '')}</div>`;
}

function renderItemCell(_, __, row) {
    const manufacturer = row.manufacturer ? `<span>${escapeHtml(row.manufacturer)}</span>` : '';
    const model = row.model ? `<span>${escapeHtml(row.model)}</span>` : '';
    const parts = [manufacturer, model].filter(Boolean).join(' / ');
    return `<div class="list-main-text">${escapeHtml(row.item_name || '')}</div>
        <div class="list-sub-text">${parts || '未填写厂家/型号'}</div>`;
}

function renderRequesterCell(_, __, row) {
    return `<div class="list-main-text">${escapeHtml(row.department || '')}</div>
        <div class="list-sub-text">${escapeHtml(row.requester_name || '')} / ${escapeHtml(row.requester_id || '')}</div>`;
}

function renderEditableCell(row, field, displayValue, type, limit = 0) {
    const rawValue = row[field] ?? '';
    const shown = type === 'currency'
        ? displayValue
        : (limit && String(displayValue).length > limit
            ? `${String(displayValue).substring(0, limit)}...`
            : displayValue);

    if (!currentAdmin) {
        return `<span title="${escapeHtml(String(rawValue || ''))}">${escapeHtml(String(shown || '-'))}</span>`;
    }

    return `<div class="inline-editable-view"
        data-row-id="${row.id}"
        data-field="${field}"
        data-type="${type}"
        data-raw-value="${escapeHtml(String(rawValue))}"
        title="点击修改">${escapeHtml(String(shown || '-'))}</div>`;
}

function renderActionCell(_, __, row) {
    return `<button class="btn btn-sm btn-outline-secondary" onclick="viewRow(${row.id})">查看</button>
        <button class="btn btn-sm btn-outline-primary admin-only" style="display:none" onclick="editRow(${row.id})">编辑</button>
        <button class="btn btn-sm btn-outline-danger admin-only" style="display:none" onclick="deleteRow(${row.id})">删除</button>`;
}

function updateRowActionVisibility(isAdmin) {
    document.querySelectorAll('.admin-only').forEach(el => {
        el.style.display = isAdmin ? '' : 'none';
    });
}

function renderEllipsisCell(limit) {
    return function(d) {
        if (!d) return '<span class="text-muted">-</span>';
        const text = String(d);
        const short = text.length > limit ? `${text.substring(0, limit)}...` : text;
        return `<span title="${escapeHtml(text)}">${escapeHtml(short)}</span>`;
    };
}

function statusBadge(s) {
    const cls = { '已申请': 'bg-info', '采购中': 'bg-warning text-dark', '已完成': 'bg-success' };
    return `<span class="badge ${cls[s] || 'bg-secondary'}">${escapeHtml(s || '-')}</span>`;
}

function renderStatusCell(row) {
    if (!currentAdmin) {
        return statusBadge(row.status);
    }

    return `<select class="form-select form-select-sm inline-status-select"
        data-row-id="${row.id}"
        data-current-value="${escapeHtml(row.status || '')}">
        ${statusOptions.map(status => `
            <option value="${escapeHtml(status)}" ${row.status === status ? 'selected' : ''}>${escapeHtml(status)}</option>
        `).join('')}
    </select>`;
}

function formatCurrency(value) {
    const amount = Number(value || 0);
    return '¥' + amount.toLocaleString('zh-CN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

$('#btn-search').click(() => reloadTable());
$('#btn-reset').click(() => {
    selectedYears = [];
    selectedMonths = [];
    selectedDepartments = [];
    selectedStatuses = [];
    renderMultiSelectMenu('year',
        Array.from(document.querySelectorAll('#filter-year-menu input[type="checkbox"]')).map(input => ({ value: input.value, label: `${input.value}年` })),
        selectedYears,
        '全部年份'
    );
    renderMultiSelectMenu('month',
        Array.from(document.querySelectorAll('#filter-month-menu input[type="checkbox"]')).map(input => ({ value: input.value, label: `${String(input.value).padStart(2, '0')}月` })),
        selectedMonths,
        '全部月份'
    );
    renderMultiSelectMenu(
        'department',
        Array.from(document.querySelectorAll('#filter-department-menu input[type="checkbox"]')).map(input => ({ value: input.value, label: input.value })),
        selectedDepartments,
        '全部部门'
    );
    renderMultiSelectMenu(
        'status',
        Array.from(document.querySelectorAll('#filter-status-menu input[type="checkbox"]')).map(input => ({ value: input.value, label: input.value })),
        selectedStatuses,
        '全部状态'
    );
    $('#filter-keyword').val('');
    reloadTable();
});

function appendFilterParams(target) {
    target.keyword = $('#filter-keyword').val();
    target.year = selectedYears;
    target.month = selectedMonths;
    target.department = selectedDepartments;
    target.status = selectedStatuses;
}

async function loadSummary() {
    try {
        const params = new URLSearchParams();
        selectedYears.forEach(value => params.append('year', value));
        selectedMonths.forEach(value => params.append('month', value));
        selectedDepartments.forEach(value => params.append('department', value));
        selectedStatuses.forEach(value => params.append('status', value));
        if ($('#filter-keyword').val()) params.set('keyword', $('#filter-keyword').val());

        const res = await fetch('/api/procurements/summary?' + params.toString());
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.msg || '汇总加载失败');
        }

        $('#summary-total-count').text(data.total_count);
        $('#summary-total-amount').text(formatCurrency(data.total_amount));
        $('#summary-pending-count').text(data.pending_count);
        $('#summary-pending-amount').text(formatCurrency(data.pending_amount));
    } catch (error) {
        $('#summary-total-count,#summary-total-amount,#summary-pending-count,#summary-pending-amount').text('-');
        console.error('汇总加载失败:', error);
    }
}

function reloadTable() {
    $('#check-all').prop('checked', false);
    updateBatchBtn();

    table.ajax.reload();
    loadSummary();
}

function initFormEvents() {
    $('#f-qty, #f-price').on('input', updateTotalPrice);
    $('#filter-keyword').on('input', function() {
        clearTimeout(keywordTimer);
        keywordTimer = setTimeout(() => {
            reloadTable();
        }, 300);
    });

    window.onAdminChange = function(isAdmin) {
        currentAdmin = !!isAdmin;
        updateRowActionVisibility(isAdmin);
        if (table) {
            table.ajax.reload(null, false);
        }
    };

    $(document).on('click', '.inline-editable-view', function() {
        if (!currentAdmin) return;
        startInlineEdit(this);
    });

    $(document).on('change', '.inline-status-select', async function() {
        if (!currentAdmin) return;

        const select = this;
        const rowId = select.dataset.rowId;
        const status = select.value;
        const originalValue = select.dataset.currentValue || '';

        if (!status || status === originalValue) {
            return;
        }

        select.disabled = true;
        try {
            const res = await fetch(`/api/procurements/${rowId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status }),
            });
            const data = await res.json();
            if (!res.ok) {
                alert(data.msg || '状态更新失败');
                select.value = originalValue;
                return;
            }

            select.dataset.currentValue = status;
            table.ajax.reload(null, false);
            loadSummary();
        } catch (error) {
            select.value = originalValue;
            alert(`状态更新失败: ${error.message}`);
        } finally {
            select.disabled = false;
        }
    });
}

function updateTotalPrice() {
    const qty = parseFloat($('#f-qty').val()) || 0;
    const price = parseFloat($('#f-price').val()) || 0;
    $('#f-total').val(formatCurrency(qty * price));
}

function resetForm() {
    $('#edit-id').val('');
    $('#formModalLabel').text('新增采购申请');
    $('#formModal input:not([type=hidden]), #formModal textarea').val('');
    $('#formModal select').each((_, el) => {
        el.selectedIndex = 0;
    });
    $('#f-year').val(new Date().getFullYear());
    $('#f-month').val(new Date().getMonth() + 1);
    $('#f-status').val('已申请');
    updateTotalPrice();
}

$('#btn-add').click(function() {
    resetForm();
    formModal.show();
});

$('#btn-save').click(async function() {
    const id = $('#edit-id').val();
    const data = {
        year: parseInt($('#f-year').val(), 10),
        month: parseInt($('#f-month').val(), 10),
        asset_category: $('#f-category').val(),
        item_name: $('#f-item').val().trim(),
        manufacturer: $('#f-manufacturer').val().trim(),
        model: $('#f-model').val().trim(),
        budget_qty: parseInt($('#f-qty').val(), 10),
        unit_price: parseFloat($('#f-price').val()),
        department: $('#f-dept').val(),
        requester_name: $('#f-name').val().trim(),
        requester_id: $('#f-id').val().trim(),
        asset_code: $('#f-asset-code').val().trim(),
        reason: $('#f-reason').val().trim(),
        remark: $('#f-remark').val().trim(),
        status: $('#f-status').val(),
    };

    if (!data.asset_category || !data.item_name || !data.budget_qty || Number.isNaN(data.unit_price) ||
        !data.department || !data.requester_name || !data.requester_id || !data.reason || !data.year || !data.month) {
        alert('请填写完整的必填字段');
        return;
    }

    const url = id ? `/api/procurements/${id}` : '/api/procurements';
    const method = id ? 'PUT' : 'POST';

    try {
        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });

        if (!res.ok) {
            const err = await res.json();
            alert(err.msg || '保存失败');
            return;
        }

        formModal.hide();
        reloadTable();
    } catch (error) {
        alert(`保存失败: ${error.message}`);
    }
});

async function fetchProcurementItem(id) {
    const res = await fetch(`/api/procurements/${id}`);
    const item = await res.json();
    if (!res.ok) {
        throw new Error(item.msg || '记录读取失败');
    }
    return item;
}

window.viewRow = async function(id) {
    try {
        const item = await fetchProcurementItem(id);
        $('#detail-grid').html(buildDetailHtml(item));
        detailModal.show();
    } catch (error) {
        alert(`记录读取失败: ${error.message}`);
    }
};

window.editRow = async function(id) {
    try {
        const item = await fetchProcurementItem(id);

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
        $('#f-dept').val(item.department);
        $('#f-name').val(item.requester_name);
        $('#f-id').val(item.requester_id);
        $('#f-asset-code').val(item.asset_code);
        $('#f-reason').val(item.reason);
        $('#f-remark').val(item.remark);
        $('#f-status').val(item.status);
        updateTotalPrice();
        formModal.show();
    } catch (error) {
        alert(`记录读取失败: ${error.message}`);
    }
};

function buildDetailHtml(item) {
    const fields = [
        ['采购期间', `${item.year}年${item.month}月`],
        ['资产分类', item.asset_category],
        ['物品名称', item.item_name],
        ['生产厂家', item.manufacturer || '-'],
        ['物品型号', item.model || '-'],
        ['预算数量', item.budget_qty],
        ['预计单价', formatCurrency(item.unit_price)],
        ['总金额', formatCurrency(item.total_price)],
        ['需求部门', item.department],
        ['需求人', `${item.requester_name} / ${item.requester_id}`],
        ['资产编码', item.asset_code || '-'],
        ['采购状态', item.status],
        ['申请原因', item.reason],
        ['备注', item.remark || '-'],
        ['创建时间', item.created_at || '-'],
        ['更新时间', item.updated_at || '-'],
    ];

    return fields.map(([label, value]) => `
        <div class="col-md-6">
            <div class="detail-field">
                <div class="detail-label">${escapeHtml(label)}</div>
                <div class="detail-value">${escapeHtml(String(value))}</div>
            </div>
        </div>
    `).join('');
}

window.deleteRow = async function(id) {
    if (!confirm('确定删除该记录？')) return;

    try {
        const res = await fetch(`/api/procurements/${id}`, { method: 'DELETE' });
        if (!res.ok) {
            const err = await res.json();
            alert(err.msg || '删除失败');
            return;
        }
        reloadTable();
    } catch (error) {
        alert(`删除失败: ${error.message}`);
    }
};

function startInlineEdit(element) {
    if (editingCell && editingCell !== element) {
        cancelInlineEdit(editingCell);
    }
    if (element.dataset.editing === '1') {
        return;
    }

    const rowId = element.dataset.rowId;
    const field = element.dataset.field;
    const type = element.dataset.type;
    const rawValue = element.dataset.rawValue || '';
    element.dataset.editing = '1';
    editingCell = element;

    let editorHtml = '';
    if (type === 'textarea') {
        editorHtml = `<textarea class="form-control form-control-sm inline-editor textarea" data-row-id="${rowId}" data-field="${field}" rows="3">${escapeHtml(rawValue)}</textarea>`;
    } else {
        const inputMode = type === 'number' || type === 'currency' ? 'number' : 'text';
        const step = type === 'currency' ? '0.01' : '1';
        editorHtml = `<input class="form-control form-control-sm inline-editor" data-row-id="${rowId}" data-field="${field}" data-type="${type}" type="${inputMode}" step="${step}" value="${escapeHtml(rawValue)}">`;
    }
    element.innerHTML = editorHtml;

    const editor = element.querySelector('.inline-editor');
    editor.focus();
    if (editor.select) editor.select();

    editor.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            event.preventDefault();
            cancelInlineEdit(element);
        } else if (event.key === 'Enter' && type !== 'textarea') {
            event.preventDefault();
            saveInlineEdit(element);
        } else if (event.key === 'Enter' && type === 'textarea' && (event.ctrlKey || event.metaKey)) {
            event.preventDefault();
            saveInlineEdit(element);
        }
    });

    editor.addEventListener('blur', function() {
        saveInlineEdit(element);
    });
}

function cancelInlineEdit(element) {
    const rawValue = element.dataset.rawValue || '';
    const type = element.dataset.type;
    const display = type === 'currency'
        ? formatCurrency(rawValue || 0)
        : (rawValue || '-');
    element.textContent = display;
    element.dataset.editing = '0';
    editingCell = null;
}

async function saveInlineEdit(element) {
    if (element.dataset.saving === '1') return;
    const editor = element.querySelector('.inline-editor');
    if (!editor) return;

    const rowId = element.dataset.rowId;
    const field = element.dataset.field;
    const type = element.dataset.type;
    let value = editor.value.trim();

    if (field === 'budget_qty') {
        if (!value || Number(value) <= 0 || !Number.isInteger(Number(value))) {
            alert('数量必须是大于 0 的整数');
            editor.focus();
            return;
        }
        value = Number(value);
    }

    if (field === 'unit_price') {
        if (value === '' || Number.isNaN(Number(value)) || Number(value) < 0) {
            alert('单价必须是大于等于 0 的数字');
            editor.focus();
            return;
        }
        value = Number(value);
    }

    if (field === 'reason' && !value) {
        alert('申请原因不能为空');
        editor.focus();
        return;
    }

    element.dataset.saving = '1';
    try {
        const res = await fetch(`/api/procurements/${rowId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ [field]: value }),
        });
        const data = await res.json();
        if (!res.ok) {
            alert(data.msg || '保存失败');
            element.dataset.saving = '0';
            editor.focus();
            return;
        }

        editingCell = null;
        table.ajax.reload(null, false);
        loadSummary();
    } catch (error) {
        element.dataset.saving = '0';
        alert(`保存失败: ${error.message}`);
        editor.focus();
    }
}

$('#check-all').on('change', function() {
    $('.row-check').prop('checked', this.checked);
    updateBatchBtn();
});

$(document).on('change', '.row-check', updateBatchBtn);

function updateBatchBtn() {
    const checked = $('.row-check:checked').length;
    $('#btn-batch-status')
        .prop('disabled', !checked)
        .text(checked ? `批量更新 (${checked})` : '批量更新状态');
}

$('#btn-batch-status').click(() => batchModal.show());

$('#btn-batch-confirm').click(async function() {
    const ids = $('.row-check:checked').map((_, el) => $(el).data('id')).get();
    const status = $('#batch-status').val();

    if (!ids.length) {
        alert('请至少选择一条记录');
        return;
    }

    try {
        const res = await fetch('/api/procurements/batch-status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids, status }),
        });

        if (!res.ok) {
            const err = await res.json();
            alert(err.msg || '批量更新失败');
            return;
        }

        batchModal.hide();
        reloadTable();
    } catch (error) {
        alert(`批量更新失败: ${error.message}`);
    }
});
