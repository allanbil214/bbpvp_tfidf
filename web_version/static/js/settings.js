/**
 * Settings Page JavaScript
 */

let currentThresholds = { ...INITIAL_THRESHOLDS };

$(document).ready(function() {
    initializePage();
    attachEventHandlers();
});

function initializePage() {
    updateAllDisplays();
}

function attachEventHandlers() {
    // Update percentage displays when values change
    $('.threshold-input').on('input', function() {
        updatePercentageDisplay(this);
        updateAllDisplays();
    });
    
    // Form submission
    $('#settingsForm').submit(handleFormSubmit);
    
    // Reset button
    $('#btnReset').click(handleReset);
}

function updatePercentageDisplay(input) {
    const value = parseFloat(input.value);
    const percent = (value * 100).toFixed(0) + '%';
    $(`.threshold-percent[data-target="${input.id}"]`).text(percent);
}

function updateAllDisplays() {
    updatePreviewTable();
    updateVisualScale();
}

function updatePreviewTable() {
    const excellent = parseFloat($('#excellentThreshold').val());
    const veryGood = parseFloat($('#veryGoodThreshold').val());
    const good = parseFloat($('#goodThreshold').val());
    const fair = parseFloat($('#fairThreshold').val());
    
    const html = `
        <tr class="table-success">
            <td><strong>🟢 Excellent</strong></td>
            <td><strong>≥ ${(excellent * 100).toFixed(0)}%</strong></td>
            <td><span class="badge bg-success">Top Tier</span></td>
        </tr>
        <tr class="table-success">
            <td><strong>🟢 Very Good</strong></td>
            <td><strong>${(veryGood * 100).toFixed(0)}% - ${(excellent * 100 - 0.01).toFixed(0)}%</strong></td>
            <td><span class="badge bg-success">High Quality</span></td>
        </tr>
        <tr class="table-warning">
            <td><strong>🟡 Good</strong></td>
            <td><strong>${(good * 100).toFixed(0)}% - ${(veryGood * 100 - 0.01).toFixed(0)}%</strong></td>
            <td><span class="badge bg-warning text-dark">Acceptable</span></td>
        </tr>
        <tr class="table-warning">
            <td><strong>🟡 Fair</strong></td>
            <td><strong>${(fair * 100).toFixed(0)}% - ${(good * 100 - 0.01).toFixed(0)}%</strong></td>
            <td><span class="badge bg-warning text-dark">Marginal</span></td>
        </tr>
        <tr class="table-danger">
            <td><strong>🔴 Weak</strong></td>
            <td><strong>&lt; ${(fair * 100).toFixed(0)}%</strong></td>
            <td><span class="badge bg-danger">Poor Match</span></td>
        </tr>
    `;
    
    $('#previewTable tbody').html(html);
}

function updateVisualScale() {
    const excellent = parseFloat($('#excellentThreshold').val());
    const veryGood = parseFloat($('#veryGoodThreshold').val());
    const good = parseFloat($('#goodThreshold').val());
    const fair = parseFloat($('#fairThreshold').val());
    
    const scale = $('#visualScale');
    scale.find('.threshold-marker').remove();
    
    // Add markers
    const markers = [
        { value: fair, label: 'Fair', color: '#ffc107' },
        { value: good, label: 'Good', color: '#ffc107' },
        { value: veryGood, label: 'V.Good', color: '#28a745' },
        { value: excellent, label: 'Excellent', color: '#28a745' }
    ];
    
    markers.forEach(marker => {
        const left = (marker.value * 100) + '%';
        scale.append(`
            <div class="threshold-marker position-absolute" 
                 style="left: ${left}; top: 0; bottom: 0; width: 2px; 
                        background: white; box-shadow: 0 0 4px rgba(0,0,0,0.5);">
                <div style="position: absolute; top: -20px; left: -20px; 
                            font-size: 10px; font-weight: bold; color: ${marker.color}; 
                            background: white; padding: 2px 4px; border-radius: 3px; 
                            white-space: nowrap;">
                    ${marker.label}
                </div>
            </div>
        `);
    });
}

function handleFormSubmit(e) {
    e.preventDefault();
    
    const thresholds = {
        excellent: parseFloat($('#excellentThreshold').val()),
        very_good: parseFloat($('#veryGoodThreshold').val()),
        good: parseFloat($('#goodThreshold').val()),
        fair: parseFloat($('#fairThreshold').val())
    };
    
    // Client-side validation
    if (!validateThresholds(thresholds)) {
        return;
    }
    
    // Save to server
    makeRequest('/api/save-settings', 'POST', { thresholds }, {
        onSuccess: function(response) {
            if (response.success) {
                showStatusMessage('success', 
                    '✓ Settings saved successfully! New calculations will use these thresholds.');
                currentThresholds = { ...thresholds };
            } else {
                showStatusMessage('danger', response.message);
            }
        },
        onError: function() {
            showStatusMessage('danger', 'Failed to save settings');
        }
    });
}

function validateThresholds(t) {
    if (t.excellent <= t.very_good ||
        t.very_good <= t.good ||
        t.good <= t.fair ||
        t.fair < 0) {
        showStatusMessage('danger', 
            'Thresholds must be in descending order: Excellent > Very Good > Good > Fair ≥ 0');
        return false;
    }
    return true;
}

function handleReset() {
    if (confirm('Reset all thresholds to default values?')) {
        makeRequest('/api/reset-settings', 'POST', null, {
            onSuccess: function(response) {
                if (response.success) {
                    $('#excellentThreshold').val(response.thresholds.excellent);
                    $('#veryGoodThreshold').val(response.thresholds.very_good);
                    $('#goodThreshold').val(response.thresholds.good);
                    $('#fairThreshold').val(response.thresholds.fair);
                    
                    // Update displays
                    $('.threshold-input').each(function() {
                        updatePercentageDisplay(this);
                    });
                    updateAllDisplays();
                    
                    showStatusMessage('success', '✓ Settings reset to defaults');
                    currentThresholds = { ...response.thresholds };
                } else {
                    showStatusMessage('danger', response.message);
                }
            },
            onError: function() {
                showStatusMessage('danger', 'Failed to reset settings');
            }
        });
    }
}

function showStatusMessage(type, message) {
    const html = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    $('#statusMessage').html(html);
    
    // Auto dismiss after 5 seconds
    setTimeout(() => {
        $('#statusMessage .alert').fadeOut();
    }, 5000);
}