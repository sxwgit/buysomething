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

function showToast(message, level = 'info', delay = 2600) {
    const stack = document.getElementById('app-toast-stack');
    if (!stack || typeof bootstrap === 'undefined' || !bootstrap.Toast) {
        alert(message);
        return;
    }

    const toneMap = {
        success: 'app-toast-success',
        danger: 'app-toast-danger',
        warning: 'app-toast-warning',
        info: 'app-toast-info',
    };
    const toneClass = toneMap[level] || toneMap.info;
    const toast = document.createElement('div');
    toast.className = `toast app-toast ${toneClass}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    toast.innerHTML = `
        <div class="toast-body d-flex align-items-start justify-content-between gap-3">
            <div>${escapeHtml(message)}</div>
            <button type="button" class="btn-close btn-close-white ms-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    stack.appendChild(toast);

    const instance = new bootstrap.Toast(toast, { delay });
    toast.addEventListener('hidden.bs.toast', () => toast.remove());
    instance.show();
}

function setButtonBusy(button, busy, busyText = '处理中...') {
    if (!button) return;
    if (busy) {
        if (!button.dataset.originalText) {
            button.dataset.originalText = button.innerHTML;
        }
        button.disabled = true;
        button.innerHTML = busyText;
        return;
    }

    button.disabled = false;
    if (button.dataset.originalText) {
        button.innerHTML = button.dataset.originalText;
        delete button.dataset.originalText;
    }
}

function formatPercent(value) {
    return `${Number(value || 0).toFixed(0)}%`;
}
