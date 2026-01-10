/**
 * Market Analysis Page JavaScript - FIXED VERSION
 */

let currentAnalysisData = null;

$(document).ready(function() {
    attachEventHandlers();
});

function attachEventHandlers() {
    // Update threshold displays
    $('#jobThreshold').on('input', function() {
        $('#jobThresholdValue').text($(this).val() + '%');
    });
    
    $('#programThreshold').on('input', function() {
        $('#programThresholdValue').text($(this).val() + '%');
    });
    
    // Calculate button
    $('#btnCalculate').click(calculateAnalysis);
    
    // Export button
    $('#btnExport').click(exportAnalysis);
}

function calculateAnalysis() {
    const jobThreshold = parseFloat($('#jobThreshold').val()) / 100;
    const programThreshold = parseFloat($('#programThreshold').val()) / 100;
    
    const $btn = $('#btnCalculate');
    $btn.prop('disabled', true)
        .html('<i class="fas fa-spinner fa-spin me-2"></i>Calculating...');
    
    $('#resultsContainer').html(showLoading('Calculating market analysis...<br><small class="text-muted">This may take a moment</small>'));
    
    makeRequest('/api/calculate-market-analysis', 'POST', {
        job_threshold: jobThreshold,
        program_threshold: programThreshold
    }, {
        onSuccess: function(response) {
            console.log('Analysis response:', response);
            
            if (response.success) {
                currentAnalysisData = response;
                displaySummary(response.summary);
                displayResults(response.results);
                displayUnmatched(response.unmatched);
                $('#btnExport').prop('disabled', false);
            } else {
                console.error('Analysis failed:', response.message);
                showAlert('danger', response.message, '#resultsContainer');
            }
        },
        onError: function(xhr, status, error) {
            console.error('AJAX error:', {xhr, status, error});
            console.error('Response text:', xhr.responseText);
            
            let errorMsg = 'Failed to calculate analysis';
            try {
                const response = JSON.parse(xhr.responseText);
                errorMsg = response.message || errorMsg;
            } catch (e) {
                console.error('Failed to parse error response:', e);
                errorMsg += ': ' + (xhr.responseText || error);
            }
            showAlert('danger', errorMsg, '#resultsContainer');
        },
        onComplete: function() {
            $btn.prop('disabled', false)
                .html('<i class="fas fa-calculator me-2"></i>Calculate Analysis');
        }
    });
}

function displaySummary(summary) {
    $('#summaryCards').show();
    
    // ✅ FIX: Set values directly WITHOUT animation to prevent flickering
    $('#totalGraduates').text(summary.total_graduates.toLocaleString());
    $('#totalPlaced').text(summary.total_placed.toLocaleString());
    $('#overallPlacementRate').text(summary.overall_placement_rate.toFixed(2) + '%');
    
    $('#totalVacancies').text(summary.total_vacancies.toLocaleString());
    $('#overallMarketCapacity').text(summary.overall_market_capacity.toFixed(2) + '%');
    
    const gap = summary.overall_gap;
    $('#overallGap').text((gap >= 0 ? '+' : '') + gap.toFixed(2) + '%');
    
    let interpretation = '';
    let cardClass = '';
    
    if (gap > 20) {
        interpretation = 'High Oversupply';
        cardClass = 'bg-danger text-white';
    } else if (gap > 10) {
        interpretation = 'External Demand';
        cardClass = 'bg-warning text-dark';
    } else if (gap >= -10) {
        interpretation = 'Balanced';
        cardClass = 'bg-success text-white';
    } else if (gap >= -20) {
        interpretation = 'Undersupply';
        cardClass = 'bg-info text-white';
    } else {
        interpretation = 'Critical Undersupply';
        cardClass = 'bg-primary text-white';
    }
    
    $('#gapInterpretation').text(interpretation);
    
    // Update card styling
    $('#overallGap').closest('.card').removeClass().addClass('card ' + cardClass);
    
    // ✅ REMOVED: No more animateValue() calls that cause flickering
}

function displayResults(results) {
    $('#resultCount').text(`${results.length} programs`);
    
    if (results.length === 0) {
        $('#resultsContainer').html(`
            <div class="text-center text-muted py-5">
                <i class="fas fa-inbox fa-3x mb-3"></i>
                <p>No results to display</p>
            </div>
        `);
        return;
    }
    
    let html = '<div class="table-responsive">';
    html += '<table class="table table-hover table-sm" id="analysisTable">';
    html += '<thead><tr>';
    html += '<th>Program Name</th>';
    html += '<th class="text-center">Graduates</th>';
    html += '<th class="text-center">Placed</th>';
    html += '<th class="text-center">Placement %</th>';
    html += '<th class="text-center">Matching Jobs</th>';
    html += '<th class="text-center">Vacancies</th>';
    html += '<th class="text-center">Market Cap %</th>';
    html += '<th class="text-center">Gap %</th>';
    html += '<th class="text-center">Status</th>';
    html += '<th class="text-center">Confidence</th>';
    html += '<th class="text-center">Actions</th>';
    html += '</tr></thead><tbody>';
    
    results.forEach((result, index) => {
        const statusBadge = getStatusBadge(result.status);
        const confidenceBadge = getConfidenceBadge(result.confidence);
        const gapSign = result.gap >= 0 ? '+' : '';
        
        html += '<tr>';
        html += `<td><strong>${result.program_name}</strong></td>`;
        html += `<td class="text-center">${result.graduates.toLocaleString()}</td>`;
        html += `<td class="text-center">${result.placed.toLocaleString()}</td>`;
        html += `<td class="text-center"><strong>${result.placement_rate.toFixed(2)}%</strong></td>`;
        html += `<td class="text-center">${result.matching_jobs}</td>`;
        html += `<td class="text-center"><strong>${result.total_vacancies.toLocaleString()}</strong></td>`;
        html += `<td class="text-center">${result.market_capacity.toFixed(2)}%</td>`;
        html += `<td class="text-center"><strong>${gapSign}${result.gap.toFixed(2)}%</strong></td>`;
        html += `<td class="text-center">${statusBadge}</td>`;
        html += `<td class="text-center">${confidenceBadge}</td>`;
        html += `<td class="text-center">
            <button class="btn btn-sm btn-outline-primary" onclick="showProgramDetail(${index})">
                <i class="fas fa-eye"></i>
            </button>
        </td>`;
        html += '</tr>';
    });
    
    html += '</tbody></table></div>';
    
    $('#resultsContainer').html(html);
    
    // ✅ FIX: Destroy existing DataTable before reinitializing
    if ($.fn.DataTable.isDataTable('#analysisTable')) {
        $('#analysisTable').DataTable().destroy();
    }
    
    // Initialize DataTable
    $('#analysisTable').DataTable({
        pageLength: 25,
        order: [[7, 'desc']],  // Sort by gap
        language: {
            search: "Search programs:"
        }
    });
}

function displayUnmatched(unmatched) {
    if (!unmatched || unmatched.length === 0) {
        $('#unmatchedAlert').hide();
        return;
    }
    
    $('#unmatchedAlert').show();
    
    let html = `<p class="mb-2"><strong>${unmatched.length} program(s) could not be matched confidently:</strong></p>`;
    html += '<ul class="mb-0">';
    
    unmatched.forEach(item => {
        html += `<li><strong>${item.program_name}</strong> → Best match: <em>${item.best_match}</em> (${item.confidence}% confidence)</li>`;
    });
    
    html += '</ul>';
    
    $('#unmatchedList').html(html);
}

function getStatusBadge(status) {
    const badges = {
        'OVERSUPPLY': '<span class="badge bg-danger">OVERSUPPLY</span>',
        'HIGH_EXTERNAL': '<span class="badge bg-warning text-dark">HIGH EXTERNAL</span>',
        'BALANCED': '<span class="badge bg-success">BALANCED</span>',
        'UNDERSUPPLY': '<span class="badge bg-info">UNDERSUPPLY</span>',
        'CRITICAL_UNDERSUPPLY': '<span class="badge bg-primary">CRITICAL</span>',
        'UNMATCHED': '<span class="badge bg-secondary">UNMATCHED</span>'
    };
    return badges[status] || '<span class="badge bg-secondary">UNKNOWN</span>';
}

function getConfidenceBadge(confidence) {
    if (confidence >= 90) {
        return `<span class="badge bg-success">${confidence}%</span>`;
    } else if (confidence >= 70) {
        return `<span class="badge bg-info">${confidence}%</span>`;
    } else if (confidence >= 50) {
        return `<span class="badge bg-warning text-dark">${confidence}%</span>`;
    } else {
        return `<span class="badge bg-danger">${confidence}%</span>`;
    }
}

function showProgramDetail(index) {
    if (!currentAnalysisData || !currentAnalysisData.results) return;
    
    const result = currentAnalysisData.results[index];
    
    $('#modalProgramName').text(result.program_name);
    
    let html = '<div class="row g-4">';
    
    // Left column: Program stats
    html += '<div class="col-md-6">';
    html += '<div class="card">';
    html += '<div class="card-header"><strong>Program Statistics</strong></div>';
    html += '<div class="card-body">';
    html += `<div class="mb-3">
        <label class="form-label text-muted">Training Match</label>
        <div class="alert alert-light mb-0">
            <strong>${result.training_match}</strong>
            <span class="badge bg-info float-end">${result.confidence}% confidence</span>
        </div>
    </div>`;
    html += `<div class="mb-3">
        <label class="form-label text-muted">Graduates</label>
        <h4>${result.graduates.toLocaleString()}</h4>
    </div>`;
    html += `<div class="mb-3">
        <label class="form-label text-muted">Actually Placed</label>
        <h4>${result.placed.toLocaleString()} <small class="text-muted">(${result.placement_rate.toFixed(2)}%)</small></h4>
    </div>`;
    html += `<div class="mb-3">
        <label class="form-label text-muted">Unplaced</label>
        <h4>${(result.graduates - result.placed).toLocaleString()}</h4>
    </div>`;
    html += '</div></div>';
    
    // Market data
    html += '<div class="card mt-3">';
    html += '<div class="card-header"><strong>Market Data</strong></div>';
    html += '<div class="card-body">';
    html += `<div class="mb-3">
        <label class="form-label text-muted">Matching Jobs Found</label>
        <h4>${result.matching_jobs}</h4>
    </div>`;
    html += `<div class="mb-3">
        <label class="form-label text-muted">Total Vacancy Positions</label>
        <h4>${result.total_vacancies.toLocaleString()}</h4>
    </div>`;
    html += `<div class="mb-3">
        <label class="form-label text-muted">Market Absorption Capacity</label>
        <h4>${result.market_capacity.toFixed(2)}%</h4>
    </div>`;
    html += '</div></div>';
    
    // Gap analysis
    html += '<div class="card mt-3">';
    html += '<div class="card-header"><strong>Gap Analysis</strong></div>';
    html += '<div class="card-body">';
    html += `<div class="mb-3">
        <label class="form-label text-muted">Gap (Placement - Capacity)</label>
        <h4>${(result.gap >= 0 ? '+' : '')}${result.gap.toFixed(2)}%</h4>
    </div>`;
    html += `<div class="mb-3">
        <label class="form-label text-muted">Status</label>
        <div>${getStatusBadge(result.status)}</div>
    </div>`;
    html += `<div class="alert alert-light mb-0">
        <strong>Interpretation:</strong><br>
        ${getInterpretation(result)}
    </div>`;
    html += '</div></div>';
    
    html += '</div>';
    
    // Right column: Matching jobs
    html += '<div class="col-md-6">';
    html += '<div class="card">';
    html += '<div class="card-header"><strong>Matching Job Opportunities</strong></div>';
    html += '<div class="card-body" style="max-height: 600px; overflow-y: auto;">';
    
    if (result.top_jobs && result.top_jobs.length > 0) {
        html += '<div class="table-responsive">';
        html += '<table class="table table-sm table-striped">';
        html += '<thead><tr><th>Company</th><th>Job Name</th><th class="text-center">Similarity</th><th class="text-center">Vacancies</th></tr></thead>';  // NEW: Added Company column
        html += '<tbody>';
        
        result.top_jobs.forEach(job => {
            html += '<tr>';
            html += `<td><small class="text-muted">${job.company_name || '-'}</small></td>`;  // NEW
            html += `<td>${job.job_name}</td>`;
            html += `<td class="text-center"><span class="badge bg-primary">${job.similarity}%</span></td>`;
            html += `<td class="text-center"><strong>${job.vacancies}</strong></td>`;
            html += '</tr>';
        });
        
        html += '</tbody></table></div>';
    } else {
        html += '<div class="text-center text-muted py-4">';
        html += '<i class="fas fa-inbox fa-2x mb-2"></i>';
        html += '<p class="mb-0">No matching jobs found</p>';
        html += '</div>';
    }
    
    html += '</div></div>';
    html += '</div>';
    
    html += '</div>';
    
    $('#modalBody').html(html);
    
    const modal = new bootstrap.Modal(document.getElementById('programDetailModal'));
    modal.show();
}

function getInterpretation(result) {
    const status = result.status;
    
    if (status === 'OVERSUPPLY') {
        return `Placement rate (${result.placement_rate.toFixed(2)}%) significantly exceeds market capacity (${result.market_capacity.toFixed(2)}%). Graduates are likely finding jobs outside this vacancy database or in related fields.`;
    } else if (status === 'HIGH_EXTERNAL') {
        return `Placement rate (${result.placement_rate.toFixed(2)}%) is higher than identified market capacity (${result.market_capacity.toFixed(2)}%). This suggests strong external demand or incomplete vacancy data.`;
    } else if (status === 'BALANCED') {
        return `Market capacity (${result.market_capacity.toFixed(2)}%) aligns well with placement rate (${result.placement_rate.toFixed(2)}%). The training program is well-matched to available opportunities.`;
    } else if (status === 'UNDERSUPPLY') {
        return `Market has ${result.total_vacancies} positions available (${result.market_capacity.toFixed(2)}% capacity) but only ${result.placement_rate.toFixed(2)}% placement achieved. Opportunity to improve job matching and placement.`;
    } else if (status === 'CRITICAL_UNDERSUPPLY') {
        return `Critical gap: ${result.total_vacancies} positions available (${result.market_capacity.toFixed(2)}% capacity) with only ${result.placement_rate.toFixed(2)}% placement. Significant opportunity for improvement in job matching, marketing, or graduate readiness.`;
    } else if (status === 'UNMATCHED') {
        return `This program could not be confidently matched to training data (${result.confidence}% confidence). Manual review recommended.`;
    }
    
    return 'Analysis completed.';
}

function exportAnalysis() {
    if (!currentAnalysisData) {
        alert('No data to export. Please calculate analysis first.');
        return;
    }
    
    const $btn = $('#btnExport');
    $btn.prop('disabled', true)
        .html('<i class="fas fa-spinner fa-spin me-2"></i>Exporting...');
    
    $.ajax({
        url: '/api/export-market-analysis',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            data: currentAnalysisData
        }),
        xhrFields: {
            responseType: 'blob'
        },
        success: function(blob) {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'market_analysis.xlsx';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        },
        error: function() {
            alert('Failed to export analysis');
        },
        complete: function() {
            $btn.prop('disabled', false)
                .html('<i class="fas fa-file-excel me-2"></i>Export to Excel');
        }
    });
}

// Make function globally available
window.showProgramDetail = showProgramDetail;