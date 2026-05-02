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
        showToast('请选择年份后再查询', 'warning');
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
        showToast(data.msg || '业务看板加载失败', 'danger');
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
        showToast(data.msg || '部门汇总加载失败', 'danger');
        return;
    }

    const tbody = document.getElementById('summary-body');
    let totalCount = 0;
    let totalQty = 0;
    let totalAmount = 0;

    if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-4">当前条件下暂无部门汇总数据</td></tr>';
        document.getElementById('summary-count').textContent = 0;
        document.getElementById('summary-qty').textContent = 0;
        document.getElementById('summary-amount').textContent = formatCurrency(0);
        return;
    }

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
        showToast(data.msg || '部门占比加载失败', 'danger');
        return;
    }

    const rows = [...data].sort((a, b) => b.value - a.value);
    if (!rows.length) {
        ratioChart.clear();
        ratioChart.setOption({
            title: {
                text: '当前条件下暂无部门占比数据',
                left: 'center',
                top: 'middle',
                textStyle: { color: '#7b8897', fontSize: 14, fontWeight: 500 },
            },
        });
        return;
    }
    ratioChart = ensureChart('ratio-chart');

    ratioChart.setOption({
        color: ['#0f6c78', '#19808c', '#2798a5', '#4fb7bd', '#7dcccf', '#a8dfe2', '#d3eff1'],
        tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
        legend: { orient: 'vertical', right: 0, top: 'middle', textStyle: { color: '#536576' } },
        series: [{
            type: 'pie',
            radius: ['38%', '68%'],
            center: ['38%', '50%'],
            data: rows,
            emphasis: {
                itemStyle: {
                    shadowBlur: 10,
                    shadowOffsetX: 0,
                    shadowColor: 'rgba(0,0,0,0.5)'
                }
            },
            label: { formatter: '{b}\n{d}%', color: '#31404f' },
        }]
    });
}

async function loadCategory(params) {
    const res = await fetch('/api/reports/category-distribution?' + params);
    const data = await res.json();
    if (!res.ok) {
        showToast(data.msg || '分类分布加载失败', 'danger');
        return;
    }

    const rows = [...data].sort((a, b) => b.total_amount - a.total_amount);
    if (!rows.length) {
        categoryChart.clear();
        categoryChart.setOption({
            title: {
                text: '当前条件下暂无分类分布数据',
                left: 'center',
                top: 'middle',
                textStyle: { color: '#7b8897', fontSize: 14, fontWeight: 500 },
            },
        });
        return;
    }
    categoryChart = ensureChart('category-chart');

    categoryChart.setOption({
        color: ['#0f6c78', '#f59f00'],
        tooltip: { trigger: 'axis' },
        legend: { data: ['采购数量', '采购金额'], top: 0, textStyle: { color: '#536576' } },
        grid: { left: 40, right: 24, top: 52, bottom: 34, containLabel: true },
        xAxis: {
            type: 'category',
            data: rows.map(d => d.category),
            axisLabel: { color: '#536576', interval: 0, rotate: rows.length > 5 ? 18 : 0 },
            axisLine: { lineStyle: { color: '#cfd9e3' } },
        },
        yAxis: [
            {
                type: 'value',
                name: '数量',
                axisLabel: { color: '#536576' },
                splitLine: { lineStyle: { color: '#e8eff5' } },
            },
            {
                type: 'value',
                name: '金额 (元)',
                axisLabel: { color: '#536576' },
                splitLine: { show: false },
            },
        ],
        series: [
            { name: '采购数量', type: 'bar', barMaxWidth: 28, borderRadius: [8, 8, 0, 0], data: rows.map(d => d.total_qty) },
            { name: '采购金额', type: 'bar', barMaxWidth: 28, borderRadius: [8, 8, 0, 0], yAxisIndex: 1, data: rows.map(d => d.total_amount) },
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

function statusClass(status) {
    return {
        '已申请': 'status-summary-pending',
        '采购中': 'status-summary-progress',
        '已完成': 'status-summary-done',
    }[status] || '';
}

function ensureChart(id) {
    const el = document.getElementById(id);
    const existing = echarts.getInstanceByDom(el);
    if (existing) {
        return existing;
    }
    return echarts.init(el);
}

window.onDataVersionChange = function() {
    loadReports();
};
