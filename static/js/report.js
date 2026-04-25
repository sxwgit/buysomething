$(document).ready(function() {
    const now = new Date().getFullYear();
    for (let y = now; y >= 2022; y--) {
        $('#filter-year').append(`<option value="${y}">${y}年</option>`);
    }
    $('#filter-year').val(now);
    loadReports();
});

$('#btn-query').click(loadReports);

async function loadReports() {
    const year = $('#filter-year').val();
    if (!year) { alert('请选择年份'); return; }
    const month = $('#filter-month').val();
    const params = `year=${year}${month ? '&month=' + month : ''}`;

    loadSummary(params);
    loadRatio(params);
    loadCategory(params);
}

async function loadSummary(params) {
    const res = await fetch('/api/reports/department-summary?' + params);
    const data = await res.json();
    const tbody = document.getElementById('summary-body');
    let totalCount = 0, totalQty = 0, totalAmount = 0;
    tbody.innerHTML = data.map(d => {
        totalCount += d.count;
        totalQty += d.total_qty;
        totalAmount += d.total_amount;
        return `<tr><td>${d.department}</td><td>${d.count}</td><td>${d.total_qty}</td><td>¥${d.total_amount.toLocaleString()}</td></tr>`;
    }).join('');
    document.getElementById('summary-count').textContent = totalCount;
    document.getElementById('summary-qty').textContent = totalQty;
    document.getElementById('summary-amount').textContent = '¥' + totalAmount.toLocaleString();
}

async function loadRatio(params) {
    const res = await fetch('/api/reports/department-ratio?' + params);
    const data = await res.json();
    const chart = echarts.init(document.getElementById('ratio-chart'));
    chart.setOption({
        title: { text: '各部门采购金额占比', left: 'center' },
        tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
        legend: { orient: 'vertical', left: 'left', top: 'middle' },
        series: [{
            type: 'pie',
            radius: ['30%', '60%'],
            data: data,
            emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.5)' } },
            label: { formatter: '{b}\n{d}%' },
        }]
    });
    window.addEventListener('resize', () => chart.resize());
}

async function loadCategory(params) {
    const res = await fetch('/api/reports/category-distribution?' + params);
    const data = await res.json();
    const chart = echarts.init(document.getElementById('category-chart'));
    chart.setOption({
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
    window.addEventListener('resize', () => chart.resize());
}

// Export
$('#btn-export-summary').click(() => exportReport('department-summary'));
$('#btn-export-ratio').click(() => exportReport('department-summary'));
$('#btn-export-category').click(() => exportReport('category-distribution'));

function exportReport(type) {
    const year = $('#filter-year').val();
    const month = $('#filter-month').val();
    window.location.href = `/api/reports/export?type=${type}&year=${year}${month ? '&month=' + month : ''}`;
}
