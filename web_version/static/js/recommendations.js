/**
 * Recommendations Page JavaScript
 */

let currentRecommendations = [];
let jobPositions = [];
let trainingPrograms = [];
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
    
    // Load both job positions and training programs if data is available
    if ($('#recMode').length && !$('#recMode').prop('disabled')) {
        loadJobPositions();
        loadTrainingPrograms();
    }
}

function attachEventHandlers() {
    // Update threshold display
    $('#threshold').on('input', function() {
        $('#thresholdValue').text($(this).val() + '%');
    });
    
    // Toggle direction-specific options
    $('#recDirection').change(function() {
        updateDirectionDisplay();
    });
    
    // Toggle single item config
    $('#recMode').change(function() {
        if ($(this).val() === 'single') {
            $('#singleItemConfig').slideDown();
            updateDirectionDisplay();
        } else {
            $('#singleItemConfig').slideUp();
        }
    });
    
    // Get recommendations
    $('#btnGetRecommendations').click(getRecommendations);
    
    // Export buttons
    $('#btnExportExcel').click(() => exportRecommendations('excel'));
    $('#btnExportCSV').click(() => exportRecommendations('csv'));
}

function updateDirectionDisplay() {
    const direction = $('#recDirection').val();
    const mode = $('#recMode').val();
    
    // Update results title
    if (direction === 'by_job') {
        $('#resultsTitle').html('<i class="fas fa-briefcase me-2"></i>Jobs → Training Programs');
    } else {
        $('#resultsTitle').html('<i class="fas fa-graduation-cap me-2"></i>Training Programs → Jobs');
    }
    
    // Show/hide appropriate selection dropdowns
    if (mode === 'single') {
        if (direction === 'by_job') {
            $('#jobSelectionDiv').show();
            $('#trainingSelectionDiv').hide();
        } else {
            $('#jobSelectionDiv').hide();
            $('#trainingSelectionDiv').show();
        }
    }
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
                    options += `<option value="${job.index}">${job.name}</option>`;
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
            showAlert('danger', 'Failed to load job positions. Please refresh the page.', '#singleItemConfig');
        }
    });
}

function loadTrainingPrograms() {
    console.log('Loading training programs...');
    
    $('#trainingSelect')
        .html('<option value="">Loading training programs...</option>')
        .prop('disabled', true);
    
    makeRequest('/api/get-training-programs', 'GET', null, {
        onSuccess: function(response) {
            if (response.success && response.programs) {
                trainingPrograms = response.programs;
                
                let options = '<option value="">-- Select a training program --</option>';
                response.programs.forEach((program, index) => {
                    options += `<option value="${program.index}">${program.name}</option>`;
                });
                
                $('#trainingSelect').html(options).prop('disabled', false);
                console.log(`✓ Loaded ${response.programs.length} training programs`);
            } else {
                $('#trainingSelect').html('<option value="">No training programs available</option>');
                console.error('Failed to load training programs:', response.message);
            }
        },
        onError: function() {
            $('#trainingSelect').html('<option value="">Error loading programs</option>');
            showAlert('danger', 'Failed to load training programs. Please refresh the page.', '#singleItemConfig');
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
    const direction = $('#recDirection').val();
    const mode = $('#recMode').val();
    const topN = parseInt($('#topN').val());
    const threshold = parseFloat($('#threshold').val()) / 100;
    
    let itemIdx = null;
    
    // Get selected item index based on mode and direction
    if (mode === 'single') {
        if (direction === 'by_job') {
            itemIdx = $('#jobSelect').val();
            if (!itemIdx || itemIdx === '') {
                showAlert('warning', 'Please select a job position first!', '#resultsContainer');
                return;
            }
        } else {
            itemIdx = $('#trainingSelect').val();
            if (!itemIdx || itemIdx === '') {
                showAlert('warning', 'Please select a training program first!', '#resultsContainer');
                return;
            }
        }
        itemIdx = parseInt(itemIdx);
    }
    
    $('#btnGetRecommendations').prop('disabled', true);
    
    const requestData = {
        mode: direction,
        top_n: topN,
        threshold: threshold
    };
    
    if (itemIdx !== null) {
        requestData.item_idx = itemIdx;
    }
    
    makeRequest('/api/get-recommendations', 'POST', requestData, {
        showLoading: true,
        loadingTarget: '#resultsContainer',
        loadingMessage: 'Generating recommendations...',
        onSuccess: function(response) {
            if (response.success) {
                currentRecommendations = response.recommendations;
                displayRecommendations(response.recommendations, response.mode);
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

function displayRecommendations(recommendations, mode) {
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
    
    if (mode === 'by_job') {
        html += '<th>Rank</th><th>Job Position</th><th>Company</th><th>Training Program</th>';
    } else {
        html += '<th>Rank</th><th>Training Program</th><th>Job Position</th><th>Company</th>';
    }
    
    html += '<th>Similarity</th><th>Match</th><th>Recommendation</th>';
    html += '</tr></thead><tbody>';
    
    recommendations.forEach(rec => {
        const score = rec.Similarity_Score;
        const { matchClass, matchLabel } = getMatchLevel(score, t);
        const isNoMatch = rec.Status === 'NO_MATCH';
        
        html += '<tr>';
        html += `<td><span class="badge bg-primary">${rec.Rank}</span></td>`;
        
        if (mode === 'by_job') {
            html += `<td>${rec.Job_Name}</td>`;
            html += `<td><small class="text-muted">${rec.Company_Name || '-'}</small></td>`;
            html += `<td>${isNoMatch ? '<em class="text-muted">-</em>' : rec.Training_Program}</td>`;
        } else {
            // Training → Jobs mode
            html += `<td>${rec.Training_Program}</td>`;
            html += `<td>${isNoMatch ? '<em class="text-muted">-</em>' : rec.Job_Name}</td>`;  // NEW: blank if 0
            html += `<td><small class="text-muted">${rec.Company_Name || '-'}</small></td>`;  // ALWAYS show company
        }
        
        html += `<td><strong>${(score * 100).toFixed(2)}%</strong></td>`;
        html += `<td><span class="badge ${isNoMatch ? 'bg-secondary' : matchClass}">${isNoMatch ? 'NO MATCH' : matchLabel}</span></td>`;
        html += `<td><small class="text-danger">${rec.Recommendation || '-'}</small></td>`;
        html += '</tr>';
    });
    
    html += '</tbody></table></div>';
    $('#resultsContainer').html(html);
    
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