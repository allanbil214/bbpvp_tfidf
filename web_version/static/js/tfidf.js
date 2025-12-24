/**
 * TF-IDF & Similarity Page JavaScript
 */

let currentStepData = {
    trainingIdx: null,
    jobIdx: null,
    tokens1: null,
    tokens2: null,
    allTerms: null,
    tfD1: null,
    tfD2: null,
    dfDict: null,
    idfDict: null,
    tfidfD1: null,
    tfidfD2: null,
    similarity: null
};

$(document).ready(function() {
    attachEventHandlers();
});

function attachEventHandlers() {
    // Load document options
    $('#btnLoadDocuments').click(loadDocumentOptions);
    
    // Step buttons
    $('#btnStep1').click(() => executeStep(1));
    $('#btnStep2').click(() => executeStep(2));
    $('#btnStep3').click(() => executeStep(3));
    $('#btnStep4').click(() => executeStep(4));
    $('#btnStep5').click(() => executeStep(5));
    $('#btnStep6').click(() => executeStep(6));
    
    // Run all steps
    $('#btnRunAllSteps').click(runAllSteps);
    
    // Calculate all documents
    $('#btnCalculateAll').click(calculateAllDocuments);
    
    // Clear output
    $('#btnClearOutput').click(clearOutput);
    
    // Enable step buttons when documents selected
    $('#trainingSelect, #jobSelect').change(function() {
        const bothSelected = $('#trainingSelect').val() && $('#jobSelect').val();
        $('#btnStep1, #btnStep2, #btnStep3, #btnStep4, #btnStep5, #btnStep6, #btnRunAllSteps')
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

function executeStep(step, appendMode = false) {
    const trainingIdx = $('#trainingSelect').val();
    const jobIdx = $('#jobSelect').val();
    
    if (!trainingIdx || !jobIdx) {
        showAlert('warning', 'Please select both documents first!', '#calculationOutput');
        return;
    }
    
    currentStepData.trainingIdx = parseInt(trainingIdx);
    currentStepData.jobIdx = parseInt(jobIdx);
    
    const stepNames = ['', 'Show Tokens', 'Calculate TF', 'Calculate DF', 
                       'Calculate IDF', 'Calculate TF-IDF', 'Calculate Similarity'];
    
    if (!appendMode) {
        $('#outputTitle').text(`Step ${step}: ${stepNames[step]}`);
    }
    
    makeRequest('/api/tfidf-step', 'POST', {
        step: step,
        training_idx: trainingIdx,
        job_idx: jobIdx,
        step_data: currentStepData
    }, {
        showLoading: !appendMode,
        loadingTarget: appendMode ? null : '#calculationOutput',
        loadingMessage: `Executing Step ${step}...`,
        onSuccess: function(response) {
            if (response.success) {
                // Update step data
                if (response.step_data) {
                    Object.assign(currentStepData, response.step_data);
                }
                
                // Display result
                const html = displayStepResult(step, response, true);
                if (appendMode) {
                    const currentContent = $('#calculationOutput').html();
                    $('#calculationOutput').html(currentContent + '<hr class="my-4">' + html);
                } else {
                    $('#calculationOutput').html(html);
                }
                
                $('#btnClearOutput').show();
            }
        }
    });
}

function displayStepResult(step, response, returnOnly = false) {
    let html = '';
    
    switch(step) {
        case 1:
            html = createTokensDisplay(response);
            break;
        case 2:
            html = createTFDisplay(response);
            break;
        case 3:
            html = createDFDisplay(response);
            break;
        case 4:
            html = createIDFDisplay(response);
            break;
        case 5:
            html = createTFIDFDisplay(response);
            break;
        case 6:
            html = createSimilarityDisplay(response);
            break;
    }
    
    if (returnOnly) {
        return html;
    } else {
        $('#calculationOutput').html(html);
    }
}

function createTokensDisplay(response) {
    return `
        <div class="alert alert-info">
            <h5><i class="fas fa-tags me-2"></i>STEP 1: TOKENIZATION</h5>
        </div>
        
        <div class="card mb-3">
            <div class="card-header bg-primary text-white">
                <i class="fas fa-chalkboard-teacher me-2"></i>
                Document 1 (Training): ${response.training_name}
            </div>
            <div class="card-body">
                <p class="small text-muted mb-2">Tokens:</p>
                <div class="alert alert-secondary">
                    ${response.tokens1.join(', ')}
                </div>
                <p class="mb-0"><strong>Total tokens: ${response.tokens1.length}</strong></p>
            </div>
        </div>
        
        <div class="card mb-3">
            <div class="card-header bg-success text-white">
                <i class="fas fa-briefcase me-2"></i>
                Document 2 (Job): ${response.job_name}
            </div>
            <div class="card-body">
                <p class="small text-muted mb-2">Tokens:</p>
                <div class="alert alert-secondary">
                    ${response.tokens2.join(', ')}
                </div>
                <p class="mb-0"><strong>Total tokens: ${response.tokens2.length}</strong></p>
            </div>
        </div>
        
        <div class="alert alert-info">
            <i class="fas fa-chart-bar me-2"></i>
            <strong>Unique terms across both documents: ${response.all_terms.length}</strong>
        </div>
    `;
}

function createTFDisplay(response) {
    return `
        <div class="alert alert-info">
            <h5><i class="fas fa-hashtag me-2"></i>STEP 2: TERM FREQUENCY (TF)</h5>
            <p class="mb-0 small">Formula: TF(t,d) = count of term t in document d / total terms in d</p>
        </div>
        
        ${createTFTable('Training', response.training_name, response.tf_d1, response.tokens1_count)}
        ${createTFTable('Job', response.job_name, response.tf_d2, response.tokens2_count)}
    `;
}

function createDFDisplay(response) {
    return `
        <div class="alert alert-info">
            <h5><i class="fas fa-file-alt me-2"></i>STEP 3: DOCUMENT FREQUENCY (DF)</h5>
            <p class="mb-0 small">DF(t) = Number of documents containing term t</p>
        </div>
        
        ${createDFTable(response.df_dict, response.tf_d1, response.tf_d2)}
    `;
}

function createIDFDisplay(response) {
    return `
        <div class="alert alert-info">
            <h5><i class="fas fa-chart-line me-2"></i>STEP 4: INVERSE DOCUMENT FREQUENCY (IDF)</h5>
            <p class="mb-0 small">Formula: IDF(t) = log(N / DF(t)), where N = total documents = 2</p>
        </div>
        
        ${createIDFTable(response.idf_dict, response.df_dict)}
    `;
}

function createTFIDFDisplay(response) {
    return `
        <div class="alert alert-info">
            <h5><i class="fas fa-calculator me-2"></i>STEP 5: TF-IDF CALCULATION</h5>
            <p class="mb-0 small">Formula: TF-IDF(t,d) = TF(t,d) × IDF(t)</p>
        </div>
        
        ${createTFIDFTable('Training', response.training_name, response.tfidf_d1, response.tf_d1, response.idf_dict)}
        ${createTFIDFTable('Job', response.job_name, response.tfidf_d2, response.tf_d2, response.idf_dict)}
    `;
}

function createSimilarityDisplay(response) {
    return `
        <div class="alert alert-info">
            <h5><i class="fas fa-equals me-2"></i>STEP 6: COSINE SIMILARITY</h5>
            <p class="mb-0 small">Formula: Cosine Similarity = (A · B) / (||A|| × ||B||)</p>
        </div>
        
        ${createSimilarityCalculation(response)}
        
        <div class="alert ${getSimilarityClass(response.similarity)} mt-4">
            <h4 class="mb-2"><i class="fas fa-chart-line me-2"></i>FINAL RESULT</h4>
            <p class="mb-2"><strong>Cosine Similarity: ${response.similarity.toFixed(6)} (${(response.similarity * 100).toFixed(2)}%)</strong></p>
            <p class="mb-0"><strong>Interpretation: ${getSimilarityInterpretation(response.similarity)}</strong></p>
        </div>
    `;
}

function createTFTable(docType, docName, tfDict, totalTokens) {
    const terms = Object.keys(tfDict).slice(0, 15);
    const remaining = Object.keys(tfDict).length - 15;
    
    let rows = '';
    terms.forEach(term => {
        const data = tfDict[term];
        rows += `
            <tr>
                <td>${term}</td>
                <td class="text-center">${data.count}</td>
                <td class="text-end">${data.count}/${totalTokens} = ${data.tf.toFixed(4)}</td>
            </tr>
        `;
    });
    
    return `
        <div class="card mb-3">
            <div class="card-header">
                <strong>${docType} Document:</strong> ${docName}
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-sm table-striped">
                        <thead>
                            <tr>
                                <th>Term</th>
                                <th class="text-center">Count</th>
                                <th class="text-end">TF Calculation</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows}
                            ${remaining > 0 ? `<tr><td colspan="3" class="text-center text-muted">... and ${remaining} more terms</td></tr>` : ''}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
}

function createDFTable(dfDict, tfD1, tfD2) {
    const terms = Object.keys(dfDict);
    
    let rows = '';
    terms.forEach(term => {
        const inD1 = tfD1[term].count > 0 ? '✓' : '✗';
        const inD2 = tfD2[term].count > 0 ? '✓' : '✗';
        rows += `
            <tr>
                <td>${term}</td>
                <td class="text-center">${inD1}</td>
                <td class="text-center">${inD2}</td>
                <td class="text-center"><strong>${dfDict[term]}</strong></td>
            </tr>
        `;
    });
    
    return `
        <div class="table-responsive">
            <table class="table table-sm table-striped">
                <thead>
                    <tr>
                        <th>Term</th>
                        <th class="text-center">In Training?</th>
                        <th class="text-center">In Job?</th>
                        <th class="text-center">DF</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
    `;
}

function createIDFTable(idfDict, dfDict) {
    const terms = Object.keys(idfDict);
    
    let rows = '';
    terms.forEach(term => {
        const df = dfDict[term];
        const idf = idfDict[term];
        const calc = df > 0 ? `log(2/${df})` : '0';
        rows += `
            <tr>
                <td>${term}</td>
                <td class="text-center">${df}</td>
                <td class="text-center">${calc}</td>
                <td class="text-end"><strong>${idf.toFixed(4)}</strong></td>
            </tr>
        `;
    });
    
    return `
        <div class="table-responsive">
            <table class="table table-sm table-striped">
                <thead>
                    <tr>
                        <th>Term</th>
                        <th class="text-center">DF</th>
                        <th class="text-center">IDF Calculation</th>
                        <th class="text-end">IDF Value</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
    `;
}

function createTFIDFTable(docType, docName, tfidfDict, tfDict, idfDict) {
    const terms = Object.keys(tfidfDict).slice(0, 15);
    const remaining = Object.keys(tfidfDict).length - 15;
    
    let rows = '';
    terms.forEach(term => {
        const tf = tfDict[term].tf;
        const idf = idfDict[term];
        const tfidf = tfidfDict[term];
        rows += `
            <tr>
                <td>${term}</td>
                <td class="text-end">${tf.toFixed(4)}</td>
                <td class="text-end">${idf.toFixed(4)}</td>
                <td class="text-end"><strong>${tfidf.toFixed(4)}</strong></td>
            </tr>
        `;
    });
    
    return `
        <div class="card mb-3">
            <div class="card-header">
                <strong>${docType} Document:</strong> ${docName}
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-sm table-striped">
                        <thead>
                            <tr>
                                <th>Term</th>
                                <th class="text-end">TF</th>
                                <th class="text-end">IDF</th>
                                <th class="text-end">TF-IDF</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows}
                            ${remaining > 0 ? `<tr><td colspan="4" class="text-center text-muted">... and ${remaining} more terms</td></tr>` : ''}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
}

function createSimilarityCalculation(response) {
    return `
        <div class="card mb-3">
            <div class="card-body">
                <h6 class="mb-3">1️⃣ Dot Product (A · B):</h6>
                <div class="alert alert-light">
                    <code>A · B = ${response.dot_product.toFixed(6)}</code>
                </div>
                
                <h6 class="mb-3 mt-4">2️⃣ Magnitude ||A|| (Training):</h6>
                <div class="alert alert-light">
                    <code>||A|| = ${response.mag_d1.toFixed(6)}</code>
                </div>
                
                <h6 class="mb-3 mt-4">3️⃣ Magnitude ||B|| (Job):</h6>
                <div class="alert alert-light">
                    <code>||B|| = ${response.mag_d2.toFixed(6)}</code>
                </div>
                
                <h6 class="mb-3 mt-4">4️⃣ Cosine Similarity:</h6>
                <div class="alert alert-light">
                    <code>Similarity = ${response.dot_product.toFixed(6)} / (${response.mag_d1.toFixed(6)} × ${response.mag_d2.toFixed(6)})</code><br>
                    <code>Similarity = <strong>${response.similarity.toFixed(6)}</strong></code>
                </div>
            </div>
        </div>
    `;
}

function getSimilarityClass(similarity) {
    if (similarity >= 0.80) return 'alert-success';
    if (similarity >= 0.65) return 'alert-info';
    if (similarity >= 0.50) return 'alert-warning';
    return 'alert-secondary';
}

function getSimilarityInterpretation(similarity) {
    if (similarity >= 0.80) return 'VERY HIGH - Excellent match!';
    if (similarity >= 0.65) return 'HIGH - Good match';
    if (similarity >= 0.50) return 'MEDIUM - Moderate match';
    return 'LOW - Poor match';
}

function runAllSteps() {
    $('#calculationOutput').html(showLoading('Running all steps...'));
    $('#outputTitle').text('Running All TF-IDF Steps');
    
    [1, 2, 3, 4, 5, 6].forEach((step, index) => {
        setTimeout(() => {
            executeStep(step, true);
        }, (index + 1) * 1000);
    });
}

function calculateAllDocuments() {
    const $btn = $('#btnCalculateAll');
    $btn.prop('disabled', true)
        .html('<i class="fas fa-spinner fa-spin me-2"></i>Calculating...');
    
    $('#outputTitle').text('Full Similarity Matrix Calculation');
    
    $('#calculationOutput').html(`
        <div class="text-center py-5">
            ${showLoading('Calculating TF-IDF and Cosine Similarity for ALL documents...')}
            <p class="text-muted mt-3">This may take a moment depending on dataset size</p>
        </div>
    `);
    
    makeRequest('/api/calculate-similarity', 'POST', null, {
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
                    <h5 class="mb-1">✅ SIMILARITY CALCULATION COMPLETED</h5>
                    <p class="mb-0">Full similarity matrix has been calculated for all document pairs.</p>
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
                        <small>Average Similarity</small>
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
                        <h4 class="mb-1">${(stats.min * 100).toFixed(2)}%</h4>
                        <small>Minimum</small>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="alert alert-info">
            <i class="fas fa-arrow-right me-2"></i>
            <strong>Next Step:</strong> Go to the <a href="/recommendations" class="alert-link">Recommendations</a> page to view matching results!
        </div>
    `;
    
    $('#calculationOutput').html(html);
    
    // Update statistics card
    $('#avgSimilarity').text((stats.avg * 100).toFixed(2) + '%');
    $('#maxSimilarity').text((stats.max * 100).toFixed(2) + '%');
    $('#minSimilarity').text((stats.min * 100).toFixed(2) + '%');
    $('#statsCard').slideDown();
}

function clearOutput() {
    $('#calculationOutput').html(`
        <div class="text-center text-muted py-5">
            <i class="fas fa-calculator fa-3x mb-3 opacity-50"></i>
            <p>Output cleared. Select documents and click a step to begin.</p>
        </div>
    `);
    $('#outputTitle').text('TF-IDF Calculation Output');
    $('#btnClearOutput').hide();
    $('#statsCard').hide();
}