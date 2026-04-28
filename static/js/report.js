let ratioChart;
let categoryChart;

$(document).ready(function() {
    const now = new Date().getFullYear();
    for (let y = now; y >= 2022; y--) {
        $('#filter-year').append(`<option value="${y}">${y}年</option>`);
    }
    $('#filter-year').val(now);

    ratioChart = echarts.init(document.getElementById('ratio-chart'));
    categoryChart = echarts.init(document.getElementById('category-chart'));
    window.addEventListener('resize', () => {
        ratioChart.resize();
        categoryChart.resize();
    });

    loadReports();
});

$('#btn-query').click(loadReports);

async function loadReports() {
    const year = $('#filter-year').val();
    if (!year) {
        alert('请选择年份');
        return;
    }

    const month = $('#filter-month').val();
    const params = `year=${year}${month ? '&month=' + month : ''}`;

    await Promise.all([
        loadOverview(params),
        loadSummary(params),
        loadRatio(params),
        loadCategory(params),
    ]);
}

async function loadOverview(params) {
    const res = await fetch('/api/reports/overview?' + params);
    const data = await res.json();
    if (!res.ok) {
        alert(data.msg || '业务看板加载失败');
        return;
    }

    $('#overview-total-count').text(data.total_count);
    $('#overview-total-amount').text(formatCurrency(data.total_amount));
    $('#overview-pending-count').text(data.pending_count);
    $('#overview-pending-amount').text(formatCurrency(data.pending_amount));

    if (data.top_department) {
        $('#overview-top-department').text(data.top_department.department);
        $('#overview-top-department-detail').text(
            `${formatCurrency(data.top_department.amount)} / ${data.top_department.count} 条`
        );
    } else {
        $('#overview-top-department').text('无数据');
        $('#overview-top-department-detail').text('-');
    }

    if (data.top_record) {
        $('#overview-top-item').text(data.top_record.item_name);
        $('#overview-top-item-detail').text(
            `${data.top_record.department} / ${formatCurrency(data.top_record.amount)} / ${data.top_record.status}`
        );
    } else {
        $('#overview-top-item').text('无数据');
        $('#overview-top-item-detail').text('-');
    }

    $('#status-summary').html(data.status_summary.map(item => `
        <div class="col-md-4">
            <div class="status-summary-card ${statusClass(item.status)}">
                <div class="small text-muted">${item.status}</div>
                <div class="fs-4 fw-semibold">${item.count}</div>
                <div class="small text-muted">${formatCurrency(item.amount)}</div>
            </div>
        </div>
    `).join(''));
}

async function loadSummary(params) {
    const res = await fetch('/api/reports/department-summary?' + params);
    const data = await res.json();
    if (!res.ok) {
        alert(data.msg || '部门汇总加载失败');
        return;
    }

    const tbody = document.getElementById('summary-body');
    let totalCount = 0;
    let totalQty = 0;
    let totalAmount = 0;

    tbody.innerHTML = data.map(d => {
        totalCount += d.count;
        totalQty += d.total_qty;
        totalAmount += d.total_amount;
        return `<tr>
            <td>${escapeHtml(d.department)}</td>
            <td>${d.count}</td>
            <td>${d.total_qty}</td>
            <td>${formatCurrency(d.total_amount)}</td>
        </tr>`;
    }).join('');

    document.getElementById('summary-count').textContent = totalCount;
    document.getElementById('summary-qty').textContent = totalQty;
    document.getElementById('summary-amount').textContent = formatCurrency(totalAmount);
}

async function loadRatio(params) {
    const res = await fetch('/api/reports/department-ratio?' + params);
    const data = await res.json();
    if (!res.ok) {
        alert(data.msg || '部门占比加载失败');
        return;
    }

    ratioChart.setOption({
        title: { text: '各部门采购金额占比', left: 'center' },
        tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
        legend: { orient: 'vertical', left: 'left', top: 'middle' },
        series: [{
            type: 'pie',
            radius: ['30%', '60%'],
            data: data,
            emphasis: {
                itemStyle: {
                    shadowBlur: 10,
                    shadowOffsetX: 0,
                    shadowColor: 'rgba(0,0,0,0.5)'
                }
            },
            label: { formatter: '{b}\n{d}%' },
        }]
    });
}

async function loadCategory(params) {
    const res = await fetch('/api/reports/category-distribution?' + params);
    const data = await res.json();
    if (!res.ok) {
        alert(data.msg || '分类分布加载失败');
        return;
    }

    categoryChart.setOption({
        title: { text: '资产分类采购分布', left: 'center' },
        tooltip: { trigger: 'axis' },
        legend: { data: ['采购数量', '采购金额'], top: 30 },
        xAxis: { type: 'category', data: data.map(d => d.category) },
        yAxis: [
            { type: 'value', name: '数量' },
            { type: 'value', name: '金额 (元)' },
        ],
        series: [
            { name: '采购数量', type: 'bar', data: data.map(d => d.total_qty) },
            { name: '采购金额', type: 'bar', yAxisIndex: 1, data: data.map(d => d.total_amount) },
        ]
    });
}

$('#btn-export-summary').click(() => exportReport('department-summary'));
$('#btn-export-ratio').click(() => exportReport('department-ratio'));
$('#btn-export-category').click(() => exportReport('category-distribution'));

function exportReport(type) {
    const year = $('#filter-year').val();
    const month = $('#filter-month').val();
    window.location.href = `/api/reports/export?type=${type}&year=${year}${month ? '&month=' + month : ''}`;
}

function formatCurrency(value) {
    return '¥' + Number(value || 0).toLocaleString('zh-CN', {
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

function statusClass(status) {
    return {
        '已申请': 'status-summary-pending',
        '采购中': 'status-summary-progress',
        '已完成': 'status-summary-done',
    }[status] || '';
}
