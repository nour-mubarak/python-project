/**
 * LinguaEval Main JavaScript
 * ==========================
 */

// Initialize tooltips
document.addEventListener('DOMContentLoaded', function () {
    // Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});

// Utility functions
const LinguaEval = {
    /**
     * Format a number as percentage
     */
    formatPercent: function (value, decimals = 1) {
        if (value === null || value === undefined) return '-';
        return value.toFixed(decimals) + '%';
    },

    /**
     * Get severity class based on gap value
     */
    getGapClass: function (gap) {
        if (gap < 10) return 'success';
        if (gap < 20) return 'warning';
        if (gap < 30) return 'danger';
        return 'dark';
    },

    /**
     * Get score class based on score value
     */
    getScoreClass: function (score) {
        if (score >= 80) return 'success';
        if (score >= 60) return 'warning';
        return 'danger';
    },

    /**
     * Get deployment status based on scores
     */
    getDeploymentStatus: function (score, gap, criticalGaps) {
        if (score >= 80 && gap < 10 && (!criticalGaps || criticalGaps.length === 0)) {
            return { status: 'Ready for Pilot', class: 'success' };
        }
        if (score >= 65) {
            return { status: 'Restricted Pilot Only', class: 'warning' };
        }
        return { status: 'Not Ready', class: 'danger' };
    },

    /**
     * Create a simple progress bar element
     */
    createProgressBar: function (value, colorClass = 'primary') {
        const container = document.createElement('div');
        container.className = 'progress';
        container.style.height = '20px';

        const bar = document.createElement('div');
        bar.className = `progress-bar bg-${colorClass}`;
        bar.style.width = `${value}%`;
        bar.textContent = `${value.toFixed(1)}%`;

        container.appendChild(bar);
        return container;
    },

    /**
     * Show loading overlay
     */
    showLoading: function (message = 'Loading...') {
        const overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.className = 'position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center';
        overlay.style.backgroundColor = 'rgba(255,255,255,0.8)';
        overlay.style.zIndex = '9999';

        overlay.innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-primary mb-3" role="status" style="width: 3rem; height: 3rem;">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="text-muted">${message}</p>
            </div>
        `;

        document.body.appendChild(overlay);
    },

    /**
     * Hide loading overlay
     */
    hideLoading: function () {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.remove();
        }
    },

    /**
     * Show toast notification
     */
    showToast: function (message, type = 'info') {
        const toastContainer = document.getElementById('toast-container') || this.createToastContainer();

        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        toastContainer.appendChild(toast);
        new bootstrap.Toast(toast, { delay: 3000 }).show();

        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    },

    /**
     * Create toast container
     */
    createToastContainer: function () {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
        return container;
    },

    /**
     * Detect language of text
     */
    detectLanguage: function (text) {
        const arabicPattern = /[\u0600-\u06FF]/;
        const arabicChars = (text.match(arabicPattern) || []).length;
        const ratio = arabicChars / Math.max(text.length, 1);
        return ratio > 0.3 ? 'ar' : 'en';
    },

    /**
     * Format date
     */
    formatDate: function (dateStr) {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    },

    /**
     * Copy text to clipboard
     */
    copyToClipboard: async function (text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showToast('Copied to clipboard', 'success');
        } catch (err) {
            this.showToast('Failed to copy', 'danger');
        }
    }
};

// Export for use in other scripts
window.LinguaEval = LinguaEval;

// Auto-refresh for running evaluations
(function () {
    const runningBadges = document.querySelectorAll('.badge:contains("running"), .badge:contains("pending")');
    if (runningBadges.length > 0) {
        setTimeout(() => location.reload(), 10000);
    }
})();

// Add fade-in animation to cards
document.querySelectorAll('.card').forEach((card, index) => {
    card.style.opacity = '0';
    card.style.animation = `fadeIn 0.3s ease-out ${index * 0.05}s forwards`;
});
