/**
 * Jaccard Similarity Page JavaScript
 */

$(document).ready(function() {
    attachEventHandlers();
});

function attachEventHandlers() {
    // Load documents
    $('#btnLoadDocuments').click(loadDocumentOptions);
    
    // Step buttons
    $('#btnStep1').click(() => executeStep(1));
    $('#btnStep2').click(() => executeStep(2));
    $('#btnStep3').click(() => executeStep(3));
    $('#btnStep4').click(() => executeStep(4));
    $('#btnStep5').click(() => executeStep(5));
    
    // Calculate all
    $('#btnCalculateAll').click(calculateAllDocuments);
    
    // Clear output
    $('#btnClearOutput').click(clearOutput);
    
    // Enable step buttons when documents selected
    $('#trainingSelect, #jobSelect').change(function() {
        const bothSelected = $('#trainingSelect').val() && $('#jobSelect').val();
        $('#btnStep1, #btnStep2, #btnStep3, #btnStep4, #btnStep5')
            .prop('disabled', !bothSelected);
    });
}

function loadDocumentOptions() {
    const $btn = $('#btnLoadDocuments');
    $btn.prop('disabled', true)
        .html('<i class="fas fa-spinner fa-spin me-2"></i>Loading...');
    
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
                showAlert('success', 'Document options loaded successfully!', '#calculationOutput');
            }
        },
        onComplete: function() {
            $btn.prop('disabled', false)
                .html('<i class="fas fa-download me-2"></i>Load Document Options');
        }
    });
}

function populateTrainingSelect(programs) {
    $('#trainingSelect').empty()
        .append('<option value="">-- Select Training Program --</option>');
    
    programs.forEach(prog => {
        $('#trainingSelect').append(
            `<option value="${prog.index}">${prog.index}: ${prog.name}</option>`
        );
    });
}

function populateJobSelect(jobs) {
    $('#jobSelect').empty()
        .append('<option value="">-- Select Job Position --</option>');
    
    jobs.forEach(job => {
        $('#jobSelect').append(
            `<option value="${job.index}">${job.index}: ${job.name}</option>`
        );
    });
}

function executeStep(step) {
    const trainingIdx = $('#trainingSelect').val();
    const jobIdx = $('#jobSelect').val();
    
    if (!trainingIdx || !jobIdx) {
        showAlert('warning', 'Please select both documents first!', '#calculationOutput');
        return;
    }
    
    const stepNames = ['', 'Tokens & Sets', 'Intersection', 'Union', 
                       'Jaccard Similarity', 'All Steps'];
    
    $('#outputTitle').text(`Step ${step}: ${stepNames[step]}`);
    
    makeRequest('/api/jaccard-step', 'POST', {
        step: step,
        training_idx: trainingIdx,
        job_idx: jobIdx
    }, {
        showLoading: true,
        loadingTarget: '#calculationOutput',
        loadingMessage: `Executing Step ${step}...`,
        onSuccess: function(response) {
            if (response.success) {
                displayStepResult(step, response);
                $('#btnClearOutput').show();
            }
        }
    });
}

function displayStepResult(step, response) {
    let html = '';
    
    switch(step) {
        case 1:
            html = createTokensDisplay(response);
            break;
        case 2:
            html = createIntersectionDisplay(response);
            break;
        case 3:
            html = createUnionDisplay(response);
            break;
        case 4:
            html = createJaccardDisplay(response);
            break;
        case 5:
            html = createAllStepsDisplay(response);
            break;
    }
    
    $('#calculationOutput').html(html);
}

function createTokensDisplay(response) {
    return `
        <div class="alert alert-info">
            <h5><i class="fas fa-tags me-2"></i>STEP 1: TOKENS & SETS</h5>
        </div>
        
        <div class="card mb-3">
            <div class="card-header bg-primary text-white">
                <i class="fas fa-chalkboard-teacher me-2"></i>
                Document 1 (Training): ${response.training_name}
            </div>
            <div class="card-body">
                <h6>Tokens (${response.tokens1.length}):</h6>
                <div class="alert alert-secondary mb-3">
                    ${response.tokens1.join(', ')}
                </div>
                <h6>Unique Terms Set (${response.unique_count1}):</h6>
                <div class="alert alert-light">
                    ${response.set1.map(t => `<span class="badge bg-primary me-1">${t}</span>`).join('')}
                </div>
            </div>
        </div>
        
        <div class="card mb-3">
            <div class="card-header bg-success text-white">
                <i class="fas fa-briefcase me-2"></i>
                Document 2 (Job): ${response.job_name}
            </div>
            <div class="card-body">
                <h6>Tokens (${response.tokens2.length}):</h6>
                <div class="alert alert-secondary mb-3">
                    ${response.tokens2.join(', ')}
                </div>
                <h6>Unique Terms Set (${response.unique_count2}):</h6>
                <div class="alert alert-light">
                    ${response.set2.map(t => `<span class="badge bg-success me-1">${t}</span>`).join('')}
                </div>
            </div>
        </div>
    `;
}

function createIntersectionDisplay(response) {
    return `
        <div class="alert alert-info">
            <h5><i class="fas fa-intersection me-2"></i>STEP 2: INTERSECTION (A ∩ B)</h5>
            <p class="mb-0 small">Common terms appearing in BOTH documents</p>
        </div>
        
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">Set A (Training)</div>
                    <div class="card-body">
                        ${response.set1.map(t => `<span class="badge bg-primary me-1 mb-1">${t}</span>`).join('')}
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">Set B (Job)</div>
                    <div class="card-body">
                        ${response.set2.map(t => `<span class="badge bg-success me-1 mb-1">${t}</span>`).join('')}
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header bg-warning text-dark">
                <strong>Intersection (A ∩ B) = ${response.intersection_count} terms</strong>
            </div>
            <div class="card-body">
                ${response.intersection.length > 0 ? 
                    response.intersection.map(t => `<span class="badge bg-warning text-dark me-1 mb-1">${t}</span>`).join('') :
                    '<p class="text-muted mb-0">No common terms</p>'
                }
            </div>
        </div>
    `;
}

function createUnionDisplay(response) {
    return `
        <div class="alert alert-info">
            <h5><i class="fas fa-union me-2"></i>STEP 3: UNION (A ∪ B)</h5>
            <p class="mb-0 small">All unique terms from BOTH documents combined</p>
        </div>
        
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">Set A (Training)</div>
                    <div class="card-body">
                        ${response.set1.map(t => `<span class="badge bg-primary me-1 mb-1">${t}</span>`).join('')}
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">Set B (Job)</div>
                    <div class="card-body">
                        ${response.set2.map(t => `<span class="badge bg-success me-1 mb-1">${t}</span>`).join('')}
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header bg-info text-white">
                <strong>Union (A ∪ B) = ${response.union_count} terms</strong>
            </div>
            <div class="card-body">
                ${response.union.map(t => `<span class="badge bg-info me-1 mb-1">${t}</span>`).join('')}
            </div>
        </div>
    `;
}

function createJaccardDisplay(response) {
    const percentage = (response.jaccard_similarity * 100).toFixed(2);
    const resultClass = response.jaccard_similarity >= 0.5 ? 'alert-success' : 
                       response.jaccard_similarity >= 0.3 ? 'alert-info' : 'alert-secondary';
    
    return `
        <div class="alert alert-info">
            <h5><i class="fas fa-calculator me-2"></i>STEP 4: JACCARD SIMILARITY</h5>
            <p class="mb-0 small">Formula: J(A,B) = |A ∩ B| / |A ∪ B|</p>
        </div>
        
        <div class="card mb-3">
            <div class="card-body">
                <h6 class="mb-3">Calculation:</h6>
                <div class="alert alert-light">
                    <p class="mb-2"><strong>Intersection Size:</strong> |A ∩ B| = ${response.intersection_count}</p>
                    <p class="mb-2"><strong>Union Size:</strong> |A ∪ B| = ${response.union_count}</p>
                    <hr>
                    <p class="mb-0">
                        <strong>Jaccard Similarity:</strong><br>
                        <code>J(A,B) = ${response.intersection_count} / ${response.union_count} = ${response.jaccard_similarity.toFixed(6)}</code>
                    </p>
                </div>
            </div>
        </div>
        
        <div class="${resultClass}">
            <h4 class="mb-2"><i class="fas fa-chart-line me-2"></i>FINAL RESULT</h4>
            <p class="mb-2"><strong>Jaccard Similarity: ${response.jaccard_similarity.toFixed(6)} (${percentage}%)</strong></p>
            <p class="mb-0"><strong>Interpretation: ${getJaccardInterpretation(response.jaccard_similarity)}</strong></p>
        </div>
    `;
}

function createAllStepsDisplay(response) {
    return `
        <div class="accordion" id="allStepsAccordion">
            <!-- Step 1: Tokens -->
            <div class="accordion-item">
                <h2 class="accordion-header">
                    <button class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#step1">
                        <i class="fas fa-tags me-2"></i> Step 1: Tokens & Sets
                    </button>
                </h2>
                <div id="step1" class="accordion-collapse collapse show">
                    <div class="accordion-body">
                        ${createTokensDisplay(response).replace(/<div class="alert alert-info">.*?<\/div>/s, '')}
                    </div>
                </div>
            </div>
            
            <!-- Step 2: Intersection -->
            <div class="accordion-item">
                <h2 class="accordion-header">
                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#step2">
                        <i class="fas fa-intersection me-2"></i> Step 2: Intersection
                    </button>
                </h2>
                <div id="step2" class="accordion-collapse collapse show">
                    <div class="accordion-body">
                        <div class="alert alert-warning">
                            <strong>Intersection (A ∩ B) = ${response.intersection_count} terms</strong>
                        </div>
                        ${response.intersection.length > 0 ? 
                            response.intersection.map(t => `<span class="badge bg-warning text-dark me-1 mb-1">${t}</span>`).join('') :
                            '<p class="text-muted">No common terms</p>'
                        }
                    </div>
                </div>
            </div>
            
            <!-- Step 3: Union -->
            <div class="accordion-item">
                <h2 class="accordion-header">
                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#step3">
                        <i class="fas fa-union me-2"></i> Step 3: Union
                    </button>
                </h2>
                <div id="step3" class="accordion-collapse collapse show">
                    <div class="accordion-body">
                        <div class="alert alert-info">
                            <strong>Union (A ∪ B) = ${response.union_count} terms</strong>
                        </div>
                        ${response.union.map(t => `<span class="badge bg-info me-1 mb-1">${t}</span>`).join('')}
                    </div>
                </div>
            </div>
            
            <!-- Step 4: Jaccard -->
            <div class="accordion-item">
                <h2 class="accordion-header">
                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#step4">
                        <i class="fas fa-calculator me-2"></i> Step 4: Jaccard Similarity
                    </button>
                </h2>
                <div id="step4" class="accordion-collapse collapse show">
                    <div class="accordion-body">
                        ${createJaccardDisplay(response).replace(/<div class="alert alert-info">.*?<\/div>/s, '')}
                    </div>
                </div>
            </div>
        </div>
    `;
}

function getJaccardInterpretation(similarity) {
    if (similarity >= 0.70) return 'VERY HIGH - Excellent overlap!';
    if (similarity >= 0.50) return 'HIGH - Good overlap';
    if (similarity >= 0.30) return 'MEDIUM - Moderate overlap';
    if (similarity > 0) return 'LOW - Limited overlap';
    return 'NONE - No common terms';
}

function calculateAllDocuments() {
    const $btn = $('#btnCalculateAll');
    $btn.prop('disabled', true)
        .html('<i class="fas fa-spinner fa-spin me-2"></i>Calculating...');
    
    $('#outputTitle').text('Full Jaccard Matrix Calculation');
    
    $('#calculationOutput').html(`
        <div class="text-center py-5">
            ${showLoading('Calculating Jaccard Similarity for ALL documents...')}
            <p class="text-muted mt-3">This may take a moment depending on dataset size</p>
        </div>
    `);
    
    makeRequest('/api/calculate-jaccard-all', 'POST', null, {
        onSuccess: function(response) {
            if (response.success) {
                displayFullResults(response);
                $('#btnClearOutput').show();
            } else {
                showAlert('danger', response.message, '#calculationOutput');
            }
        },
        onComplete: function() {
            $btn.prop('disabled', false)
                .html('<i class="fas fa-rocket me-2"></i>Calculate All Documents');
        }
    });
}

function displayFullResults(response) {
    const stats = response.stats;
    
    const html = `
        <div class="alert alert-success">
            <div class="d-flex align-items-center">
                <i class="fas fa-check-circle fa-2x me-3"></i>
                <div>
                    <h5 class="mb-1">✅ JACCARD CALCULATION COMPLETED</h5>
                    <p class="mb-0">Full Jaccard similarity matrix has been calculated for all document pairs.</p>
                </div>
            </div>
        </div>
        
        <div class="row g-3 mb-4">
            <div class="col-md-3">
                <div class="card bg-primary text-white">
                    <div class="card-body text-center">
                        <h4 class="mb-1">${stats.total_calculations.toLocaleString()}</h4>
                        <small>Total Calculations</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-success text-white">
                    <div class="card-body text-center">
                        <h4 class="mb-1">${(stats.avg * 100).toFixed(2)}%</h4>
                        <small>Average Jaccard</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-info text-white">
                    <div class="card-body text-center">
                        <h4 class="mb-1">${(stats.max * 100).toFixed(2)}%</h4>
                        <small>Maximum</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-warning text-dark">
                    <div class="card-body text-center">
                        <h4 class="mb-1">${stats.non_zero_percentage.toFixed(1)}%</h4>
                        <small>Non-Zero Pairs</small>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="alert alert-info">
            <i class="fas fa-arrow-right me-2"></i>
            <strong>Next Step:</strong> Go to the <a href="/comparison" class="alert-link">Comparison</a> page to compare Jaccard with Cosine Similarity!
        </div>
    `;
    
    $('#calculationOutput').html(html);
    
    // Update statistics card
    $('#avgJaccard').text((stats.avg * 100).toFixed(2) + '%');
    $('#maxJaccard').text((stats.max * 100).toFixed(2) + '%');
    $('#minJaccard').text((stats.min * 100).toFixed(2) + '%');
    $('#nonZeroPercent').text(stats.non_zero_percentage.toFixed(1) + '%');
    $('#statsCard').slideDown();
}

function clearOutput() {
    $('#calculationOutput').html(`
        <div class="text-center text-muted py-5">
            <i class="fas fa-project-diagram fa-3x mb-3 opacity-50"></i>
            <p>Output cleared. Select documents and click a step to begin.</p>
        </div>
    `);
    $('#outputTitle').text('Jaccard Calculation Output');
    $('#btnClearOutput').hide();
    $('#statsCard').hide();
}