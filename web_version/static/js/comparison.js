/**
 * Cosine vs Jaccard Comparison Page JavaScript
 */

let currentComparisons = [];

$(document).ready(function() {
    attachEventHandlers();
    loadDocumentOptions();
});

function attachEventHandlers() {
    // Update threshold display
    $('#minThreshold').on('input', function() {
        $('#thresholdValue').text($(this).val() + '%');
    });
    
    // Toggle comparison mode
    $('#comparisonMode').change(function() {
        if ($(this).val() === 'single') {
            $('#singlePairConfig').slideDown();
        } else {
            $('#singlePairConfig').slideUp();
        }
    });
    
    // Compare button
    $('#btnCompare').click(generateComparison);
    
    // Export button
    $('#btnExport').click(exportComparison);
}

function loadDocumentOptions() {
    // Load training programs
    makeRequest('/api/get-training-programs', 'GET', null, {
        onSuccess: function(response) {
            if (response.success) {
                populateTrainingSelect(response.programs);
            }
        }
    });
    
    // Load job positions
    makeRequest('/api/get-job-positions', 'GET', null, {
        onSuccess: function(response) {
            if (response.success) {
                populateJobSelect(response.jobs);
            }
        }
    });
}

function populateTrainingSelect(programs) {
    $('#trainingSelect').empty()
        .append('<option value="">-- Select --</option>');
    
    programs.forEach(prog => {
        $('#trainingSelect').append(
            `<option value="${prog.index}">${prog.name}</option>`
        );
    });
}

function populateJobSelect(jobs) {
    $('#jobSelect').empty()
        .append('<option value="">-- Select --</option>');
    
    jobs.forEach(job => {
        $('#jobSelect').append(
            `<option value="${job.index}">${job.name}</option>`
        );
    });
}

function generateComparison() {
    const mode = $('#comparisonMode').val();
    const minThreshold = parseFloat($('#minThreshold').val()) / 100;
    
    let requestData = {
        mode: mode,
        min_threshold: minThreshold
    };
    
    if (mode === 'single') {
        const trainingIdx = $('#trainingSelect').val();
        const jobIdx = $('#jobSelect').val();
        
        if (!trainingIdx || !jobIdx) {
            showAlert('warning', 'Please select both training program and job position!', '#resultsContainer');
            return;
        }
        
        requestData.training_idx = parseInt(trainingIdx);
        requestData.job_idx = parseInt(jobIdx);
    }
    
    const $btn = $('#btnCompare');
    $btn.prop('disabled', true)
        .html('<i class="fas fa-spinner fa-spin me-2"></i>Comparing...');
    
    makeRequest('/api/get-comparison', 'POST', requestData, {
        showLoading: true,
        loadingTarget: '#resultsContainer',
        loadingMessage: 'Generating comparison...',
        onSuccess: function(response) {
            if (response.success) {
                currentComparisons = response.comparisons;
                displayComparison(response.comparisons, response.stats);
                $('#btnExport').prop('disabled', false);
            } else {
                showAlert('danger', response.message, '#resultsContainer');
            }
        },
        onComplete: function() {
            $btn.prop('disabled', false)
                .html('<i class="fas fa-equals me-2"></i>Generate Comparison');
        }
    });
}

function displayComparison(comparisons, stats) {
    $('#resultCount').text(`${comparisons.length} pairs`);
    
    if (comparisons.length === 0) {
        $('#resultsContainer').html(`
            <div class="text-center text-muted py-5">
                <i class="fas fa-inbox fa-3x mb-3"></i>
                <p>No comparisons found. Try lowering the threshold.</p>
            </div>
        `);
        $('#statsCard').hide();
        return;
    }
    
    // Display statistics
    $('#totalComparisons').text(stats.total_comparisons.toLocaleString());
    $('#avgCosine').text((stats.avg_cosine * 100).toFixed(2) + '%');
    $('#avgJaccard').text((stats.avg_jaccard * 100).toFixed(2) + '%');
    $('#avgDifference').text((stats.avg_difference * 100).toFixed(2) + '%');
    $('#correlation').text(stats.correlation.toFixed(4));
    $('#statsCard').slideDown();
    
    // Display table
    let html = '<div class="table-responsive">';
    html += '<table class="table table-hover table-sm" id="comparisonTable">';
    html += '<thead><tr>';
    html += '<th>Training Program</th>';
    html += '<th>Job Position</th>';
    html += '<th class="text-center">Cosine</th>';
    html += '<th class="text-center">Jaccard</th>';
    html += '<th class="text-center">Difference</th>';
    html += '<th class="text-center">Relation</th>';
    html += '</tr></thead><tbody>';
    
    comparisons.forEach(comp => {
        const cosinePct = comp.cosine_percentage.toFixed(2);
        const jaccardPct = comp.jaccard_percentage.toFixed(2);
        const diffPct = (comp.difference * 100).toFixed(2);
        
        // Determine which is higher
        let relation = '';
        if (comp.cosine_similarity > comp.jaccard_similarity) {
            relation = '<span class="badge bg-primary">Cosine Higher</span>';
        } else if (comp.jaccard_similarity > comp.cosine_similarity) {
            relation = '<span class="badge bg-success">Jaccard Higher</span>';
        } else {
            relation = '<span class="badge bg-secondary">Equal</span>';
        }
        
        html += '<tr>';
        html += `<td>${comp.training_name}</td>`;
        html += `<td>${comp.job_name}</td>`;
        html += `<td class="text-center"><strong>${cosinePct}%</strong></td>`;
        html += `<td class="text-center"><strong>${jaccardPct}%</strong></td>`;
        html += `<td class="text-center">${diffPct}%</td>`;
        html += `<td class="text-center">${relation}</td>`;
        html += '</tr>';
    });
    
    html += '</tbody></table></div>';
    
    $('#resultsContainer').html(html);
    
    // Destroy existing DataTable if any
    if ($.fn.DataTable.isDataTable('#comparisonTable')) {
        $('#comparisonTable').DataTable().destroy();
    }
    
    // Initialize DataTable
    $('#comparisonTable').DataTable({
        pageLength: 25,
        order: [[4, 'desc']], // Sort by difference
        language: {
            search: "Search comparisons:"
        }
    });
}

function exportComparison() {
    if (currentComparisons.length === 0) {
        alert('No comparisons to export');
        return;
    }
    
    const $btn = $('#btnExport');
    $btn.prop('disabled', true)
        .html('<i class="fas fa-spinner fa-spin me-2"></i>Exporting...');
    
    $.ajax({
        url: '/api/export-comparison',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            comparisons: currentComparisons
        }),
        xhrFields: {
            responseType: 'blob'
        },
        success: function(blob) {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'cosine_vs_jaccard_comparison.xlsx';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        },
        error: function() {
            alert('Failed to export comparison');
        },
        complete: function() {
            $btn.prop('disabled', false)
                .html('<i class="fas fa-file-excel me-2"></i>Export to Excel');
        }
    });
}