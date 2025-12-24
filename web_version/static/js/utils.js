/**
 * BBPVP Job Matching System - Utility Functions
 */

// Show loading indicator
function showLoading(message = 'Processing...') {
    return `
        <div class="text-center py-4">
            <div class="spinner-border text-primary mb-3" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="text-muted">${message}</p>
        </div>
    `;
}

// Show alert message
function showAlert(type, message, target = null) {
    const iconMap = {
        'success': 'check-circle',
        'danger': 'exclamation-circle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    };
    
    const html = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            <i class="fas fa-${iconMap[type] || 'info-circle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    if (target) {
        $(target).html(html);
    }
    
    return html;
}

// Add log entry
function addLog(message, type = 'info', containerId) {
    const timestamp = new Date().toLocaleTimeString();
    const icons = {
        'info': 'fa-info-circle text-info',
        'success': 'fa-check-circle text-success',
        'error': 'fa-times-circle text-danger',
        'warning': 'fa-exclamation-triangle text-warning'
    };
    
    const borderColors = {
        'info': 'info',
        'success': 'success',
        'error': 'danger',
        'warning': 'warning'
    };
    
    const log = `
        <div class="mb-2 p-2 border-start border-3 border-${borderColors[type]}" style="background: #f8fafc;">
            <small class="text-muted">[${timestamp}]</small>
            <i class="fas ${icons[type]} me-2"></i>
            <span>${message}</span>
        </div>
    `;
    
    const $container = $(`#${containerId}`);
    
    // Clear placeholder if exists
    if ($container.find('.text-center').length > 0) {
        $container.html('');
    }
    
    $container.append(log);
    $container.scrollTop($container[0].scrollHeight);
}

// Animate number counter
function animateValue(elementId, start, end, duration) {
    const obj = document.getElementById(elementId);
    if (!obj) return;
    
    const range = end - start;
    const increment = end > start ? 1 : -1;
    const stepTime = Math.abs(Math.floor(duration / range));
    let current = start;
    
    const timer = setInterval(function() {
        current += increment;
        obj.textContent = current.toLocaleString();
        if (current === end) {
            clearInterval(timer);
        }
    }, stepTime);
}

// Format percentage
function formatPercent(value, decimals = 2) {
    return (value * 100).toFixed(decimals) + '%';
}

// Update progress bar
function updateProgress(percent, label = '', detail = '', containerId = 'progressCard') {
    $(`#${containerId} .progress-bar`).css('width', percent + '%');
    $(`#${containerId} #progressPercent`).text(percent + '%');
    $(`#${containerId} #progressLabel`).text(label);
    $(`#${containerId} #progressText`).text(percent + '%');
    
    if (detail) {
        const timestamp = new Date().toLocaleTimeString();
        $(`#${containerId} #progressDetails`).append(`
            <div>
                <span class="text-muted">[${timestamp}]</span>
                <i class="fas fa-arrow-right text-primary me-2"></i>
                ${detail}
            </div>
        `);
    }
}

// AJAX helper with error handling
function makeRequest(url, method, data, options = {}) {
    const defaults = {
        showLoading: false,
        loadingTarget: null,
        loadingMessage: 'Processing...',
        onSuccess: null,
        onError: null,
        onComplete: null
    };
    
    const settings = { ...defaults, ...options };
    
    if (settings.showLoading && settings.loadingTarget) {
        $(settings.loadingTarget).html(showLoading(settings.loadingMessage));
    }
    
    return $.ajax({
        url: url,
        method: method,
        contentType: 'application/json',
        data: data ? JSON.stringify(data) : null,
        success: function(response) {
            if (settings.onSuccess) {
                settings.onSuccess(response);
            }
        },
        error: function(xhr, status, error) {
            console.error(`Request failed: ${url}`, error);
            if (settings.onError) {
                settings.onError(xhr, status, error);
            } else if (settings.loadingTarget) {
                $(settings.loadingTarget).html(
                    showAlert('danger', 'An error occurred. Please try again.')
                );
            }
        },
        complete: function() {
            if (settings.onComplete) {
                settings.onComplete();
            }
        }
    });
}

// Set active navigation link
function setActiveNav() {
    const path = window.location.pathname;
    $('.nav-link').each(function() {
        if ($(this).attr('href') === path) {
            $(this).addClass('active');
        }
    });
}

// Export data as file
function exportData(url, data, filename, format) {
    $.ajax({
        url: url,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            ...data,
            format: format
        }),
        xhrFields: {
            responseType: 'blob'
        },
        success: function(blob) {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${filename}.${format === 'excel' ? 'xlsx' : 'csv'}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        },
        error: function() {
            alert(`Failed to export ${format.toUpperCase()}`);
        }
    });
}

// Initialize on document ready
$(document).ready(function() {
    // Set active navigation
    setActiveNav();
    
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        $('.alert-dismissible').fadeOut();
    }, 5000);
});

// Make functions globally available
window.showLoading = showLoading;
window.showAlert = showAlert;
window.addLog = addLog;
window.animateValue = animateValue;
window.formatPercent = formatPercent;
window.updateProgress = updateProgress;
window.makeRequest = makeRequest;
window.setActiveNav = setActiveNav;
window.exportData = exportData;