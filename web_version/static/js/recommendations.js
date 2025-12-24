/**
 * Recommendations Page JavaScript
 */

let currentRecommendations = [];
let jobPositions = [];
let matchThresholds = {
    excellent: 0.80,
    very_good: 0.65,
    good: 0.50,
    fair: 0.35
};

$(document).ready(function() {
    initializePage();
    attachEventHandlers();
});

function initializePage() {
    loadMatchLevels();
    
    // Load job positions if data is available
    if ($('#recMode').length && !$('#recMode').prop('disabled')) {
        loadJobPositions();
    }
}

function attachEventHandlers() {
    // Update threshold display
    $('#threshold').on('input', function() {
        $('#thresholdValue').text($(this).val() + '%');
    });
    
    // Toggle single job config
    $('#recMode').change(function() {
        if ($(this).val() === 'single') {
            $('#singleJobConfig').slideDown();
            if (jobPositions.length === 0) {
                loadJobPositions();
            }
        } else {
            $('#singleJobConfig').slideUp();
        }
    });
    
    // Get recommendations
    $('#btnGetRecommendations').click(getRecommendations);
    
    // Export buttons
    $('#btnExportExcel').click(() => exportRecommendations('excel'));
    $('#btnExportCSV').click(() => exportRecommendations('csv'));
}

function loadJobPositions() {
    console.log('Loading job positions...');
    
    $('#jobSelect')
        .html('<option value="">Loading job positions...</option>')
        .prop('disabled', true);
    
    makeRequest('/api/get-job-positions', 'GET', null, {
        onSuccess: function(response) {
            if (response.success && response.jobs) {
                jobPositions = response.jobs;
                
                let options = '<option value="">-- Select a job position --</option>';
                response.jobs.forEach((job, index) => {
                    options += `<option value="${index}">${job.name}</option>`;
                });
                
                $('#jobSelect').html(options).prop('disabled', false);
                console.log(`✓ Loaded ${response.jobs.length} job positions`);
            } else {
                $('#jobSelect').html('<option value="">No job positions available</option>');
                console.error('Failed to load job positions:', response.message);
            }
        },
        onError: function() {
            $('#jobSelect').html('<option value="">Error loading jobs</option>');
            showAlert('danger', 'Failed to load job positions. Please refresh the page.', '#singleJobConfig');
        }
    });
}

function loadMatchLevels() {
    makeRequest('/api/get-settings', 'GET', null, {
        onSuccess: function(response) {
            if (response.success) {
                matchThresholds = response.thresholds;
                displayMatchLevels(response.thresholds);
            }
        },
        onError: function() {
            console.error('Failed to load match levels');
        }
    });
}

function displayMatchLevels(t) {
    const html = `
        <div class="mb-2">
            <span class="badge match-excellent me-2">Excellent</span>
            <span class="small">≥ ${(t.excellent * 100).toFixed(0)}%</span>
        </div>
        <div class="mb-2">
            <span class="badge match-very-good me-2">Very Good</span>
            <span class="small">${(t.very_good * 100).toFixed(0)}% - ${(t.excellent * 100 - 0.01).toFixed(0)}%</span>
        </div>
        <div class="mb-2">
            <span class="badge match-good me-2">Good</span>
            <span class="small">${(t.good * 100).toFixed(0)}% - ${(t.very_good * 100 - 0.01).toFixed(0)}%</span>
        </div>
        <div class="mb-2">
            <span class="badge match-fair me-2">Fair</span>
            <span class="small">${(t.fair * 100).toFixed(0)}% - ${(t.good * 100 - 0.01).toFixed(0)}%</span>
        </div>
        <div>
            <span class="badge match-weak me-2">Weak</span>
            <span class="small">&lt; ${(t.fair * 100).toFixed(0)}%</span>
        </div>
        <hr class="my-3">
        <div class="text-center">
            <a href="/settings" class="btn btn-sm btn-outline-primary">
                <i class="fas fa-cog me-1"></i>
                Customize Thresholds
            </a>
        </div>
    `;
    
    $('#matchLevelsBody').html(html);
}

function getRecommendations() {
    const mode = $('#recMode').val();
    const topN = parseInt($('#topN').val());
    const threshold = parseFloat($('#threshold').val()) / 100;
    const jobIdx = mode === 'single' ? $('#jobSelect').val() : null;
    
    // Validation
    if (mode === 'single' && (!jobIdx || jobIdx === '')) {
        showAlert('warning', 'Please select a job position first!', '#resultsContainer');
        return;
    }
    
    $('#btnGetRecommendations').prop('disabled', true);
    
    const requestData = {
        top_n: topN,
        threshold: threshold
    };
    
    if (mode === 'single' && jobIdx) {
        requestData.job_idx = parseInt(jobIdx);
    }
    
    makeRequest('/api/get-recommendations', 'POST', requestData, {
        showLoading: true,
        loadingTarget: '#resultsContainer',
        loadingMessage: 'Generating recommendations...',
        onSuccess: function(response) {
            if (response.success) {
                currentRecommendations = response.recommendations;
                displayRecommendations(response.recommendations);
                $('#btnExportExcel, #btnExportCSV').prop('disabled', false);
            } else {
                showAlert('danger', response.message, '#resultsContainer');
            }
        },
        onComplete: function() {
            $('#btnGetRecommendations').prop('disabled', false);
        }
    });
}

function displayRecommendations(recommendations) {
    if (recommendations.length === 0) {
        $('#resultsContainer').html(
            showAlert('info', 'No recommendations found. Try lowering the threshold or increasing Top N.')
        );
        $('#resultCount').text('0 results');
        return;
    }
    
    $('#resultCount').text(`${recommendations.length} results`);
    
    const t = matchThresholds;
    
    let html = '<div class="table-responsive"><table class="table table-hover" id="recTable">';
    html += '<thead><tr>';
    html += '<th>Rank</th><th>Job Position</th><th>Training Program</th>';
    html += '<th>Similarity</th><th>Match</th>';
    html += '</tr></thead><tbody>';
    
    recommendations.forEach(rec => {
        const score = rec.Similarity_Score;
        const { matchClass, matchLabel } = getMatchLevel(score, t);
        
        html += '<tr>';
        html += `<td><span class="badge bg-primary">${rec.Rank}</span></td>`;
        html += `<td>${rec.Job_Name}</td>`;
        html += `<td>${rec.Training_Program}</td>`;
        html += `<td><strong>${(score * 100).toFixed(2)}%</strong></td>`;
        html += `<td><span class="badge ${matchClass}">${matchLabel}</span></td>`;
        html += '</tr>';
    });
    
    html += '</tbody></table></div>';
    $('#resultsContainer').html(html);
    
    // Initialize DataTable
    $('#recTable').DataTable({
        pageLength: 25,
        order: [[0, 'asc']],
        language: {
            search: "Search recommendations:"
        }
    });
}

function getMatchLevel(score, t) {
    if (score >= t.excellent) {
        return { matchClass: 'match-excellent', matchLabel: 'Excellent' };
    } else if (score >= t.very_good) {
        return { matchClass: 'match-very-good', matchLabel: 'Very Good' };
    } else if (score >= t.good) {
        return { matchClass: 'match-good', matchLabel: 'Good' };
    } else if (score >= t.fair) {
        return { matchClass: 'match-fair', matchLabel: 'Fair' };
    } else {
        return { matchClass: 'match-weak', matchLabel: 'Weak' };
    }
}

function exportRecommendations(format) {
    if (currentRecommendations.length === 0) {
        alert('No recommendations to export');
        return;
    }
    
    exportData(
        '/api/export-recommendations',
        { recommendations: currentRecommendations },
        'recommendations',
        format
    );
}