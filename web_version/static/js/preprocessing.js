/**
 * Preprocessing Page JavaScript
 */

$(document).ready(function() {
    attachEventHandlers();
});

function attachEventHandlers() {
    // Process all data
    $('#btnProcessAll').click(processAllData);
    
    // Clear output
    $('#btnClearOutput').click(clearOutput);
    
    // Update row index max based on dataset
    $('#datasetSelect').change(updateRowIndexMax);
}

function showStep(step) {
    const dataset = $('#datasetSelect').val();
    const rowIdx = parseInt($('#rowIndex').val());
    
    makeRequest('/api/preprocess-step', 'POST', {
        dataset: dataset,
        row_idx: rowIdx,
        step: step
    }, {
        showLoading: true,
        loadingTarget: '#preprocessOutput',
        loadingMessage: 'Processing step...',
        onSuccess: function(response) {
            if (response.success) {
                displayStepOutput(step, response);
            } else {
                showAlert('danger', response.message, '#preprocessOutput');
            }
        }
    });
}

function displayStepOutput(step, response) {
    const stepNames = [
        'Original Text',
        'Step 1: Normalization',
        'Step 2: Stopword Removal',
        'Step 3: Tokenization',
        'Step 4: Stemming'
    ];
    
    let html = `
        <div class="mb-4">
            <div class="d-flex align-items-center mb-3">
                <h5 class="mb-0">
                    <span class="badge bg-primary me-2">${step}</span>
                    ${stepNames[step]}
                </h5>
            </div>
            <div class="alert alert-light">
                <strong><i class="fas fa-file-alt me-2"></i>Record:</strong> ${response.record_name}
            </div>
        </div>
    `;
    
    if (step < 3) {
        // Text output
        html += createTextOutput(response.output);
    } else if (step === 3) {
        // Tokenization output
        html += createTokenOutput(response.output, response.token_count);
    } else if (step === 4) {
        // Stemming output
        html += createStemmingOutput(response);
    }
    
    $('#preprocessOutput').html(html);
}

function createTextOutput(text) {
    return `
        <div class="card bg-light">
            <div class="card-body">
                <h6 class="card-title">Output:</h6>
                <pre class="mb-0" style="white-space: pre-wrap; word-wrap: break-word;">${text}</pre>
            </div>
        </div>
    `;
}

function createTokenOutput(tokens, count) {
    let html = `
        <div class="card bg-light">
            <div class="card-body">
                <h6 class="card-title">Tokens:</h6>
                <div class="mb-3">
    `;
    
    tokens.forEach(token => {
        html += `<span class="badge bg-info me-1 mb-1">${token}</span>`;
    });
    
    html += `
                </div>
                <div class="alert alert-info mb-0">
                    <i class="fas fa-info-circle me-2"></i>
                    <strong>Total tokens:</strong> ${count}
                </div>
            </div>
        </div>
    `;
    
    return html;
}

function createStemmingOutput(response) {
    let html = `
        <div class="card bg-light mb-3">
            <div class="card-body">
                <h6 class="card-title">Stemmed Tokens:</h6>
                <div class="mb-3">
    `;
    
    response.output.forEach(token => {
        html += `<span class="badge bg-success me-1 mb-1">${token}</span>`;
    });
    
    html += `
                </div>
                <div class="alert alert-success mb-0">
                    <i class="fas fa-check-circle me-2"></i>
                    <strong>Total tokens after stemming:</strong> ${response.token_count}
                </div>
            </div>
        </div>
    `;
    
    // Comparison table
    if (response.original_tokens) {
        html += createComparisonTable(response.original_tokens, response.output);
    }
    
    return html;
}

function createComparisonTable(originalTokens, stemmedTokens) {
    let html = `
        <div class="card">
            <div class="card-header">
                <i class="fas fa-exchange-alt me-2"></i>
                Before & After Stemming (First 20 tokens)
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-sm table-striped">
                        <thead>
                            <tr>
                                <th width="50">#</th>
                                <th>Before Stemming</th>
                                <th>After Stemming</th>
                                <th width="100">Status</th>
                            </tr>
                        </thead>
                        <tbody>
    `;
    
    const maxShow = Math.min(20, originalTokens.length);
    for (let i = 0; i < maxShow; i++) {
        const before = originalTokens[i];
        const after = stemmedTokens[i];
        const changed = before !== after;
        
        html += `
            <tr>
                <td>${i + 1}</td>
                <td><code>${before}</code></td>
                <td><code>${after}</code></td>
                <td>
                    ${changed ? 
                        '<span class="badge bg-warning text-dark">Changed</span>' : 
                        '<span class="badge bg-secondary">Same</span>'}
                </td>
            </tr>
        `;
    }
    
    html += `
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
    
    return html;
}

function processAllData() {
    const $btn = $('#btnProcessAll');
    $btn.prop('disabled', true)
        .html('<i class="fas fa-spinner fa-spin me-2"></i>Processing...');
    
    $('#progressCard').show();
    updateProgress(0, 'Starting preprocessing...', 'Initializing...');
    
    makeRequest('/api/process-all', 'POST', null, {
        onSuccess: function(response) {
            if (response.success) {
                updateProgress(100, 'Processing complete!', '✓ All data processed successfully');
                displayProcessingComplete();
                
                setTimeout(() => {
                    $('#progressCard').slideUp();
                }, 3000);
            } else {
                updateProgress(0, 'Error occurred', response.message);
                showAlert('danger', response.message, '#preprocessOutput');
            }
        },
        onError: function() {
            updateProgress(0, 'Error occurred', 'Failed to process data');
            showAlert('danger', 'Failed to process data', '#preprocessOutput');
        },
        onComplete: function() {
            $btn.prop('disabled', false)
                .html('<i class="fas fa-rocket me-2"></i>Process All Data');
        }
    });
    
    // Simulate progress
    simulateProgress();
}

function simulateProgress() {
    const steps = [
        {percent: 25, label: 'Normalizing text...', detail: 'Converting to lowercase, removing punctuation'},
        {percent: 50, label: 'Removing stopwords...', detail: 'Filtering out common Indonesian words'},
        {percent: 75, label: 'Tokenizing...', detail: 'Splitting text into words'},
        {percent: 95, label: 'Stemming...', detail: 'Converting to root words using Sastrawi'}
    ];
    
    let currentStep = 0;
    const interval = setInterval(() => {
        if (currentStep < steps.length) {
            const step = steps[currentStep];
            updateProgress(step.percent, step.label, step.detail);
            currentStep++;
        } else {
            clearInterval(interval);
        }
    }, 800);
}

function displayProcessingComplete() {
    $('#preprocessOutput').html(`
        <div class="text-center py-5">
            <i class="fas fa-check-circle fa-4x text-success mb-4"></i>
            <h4 class="text-success mb-3">Processing Complete!</h4>
            <p class="text-muted mb-4">All data has been preprocessed successfully.</p>
            <div class="alert alert-success text-start">
                <h6><i class="fas fa-clipboard-check me-2"></i>What was processed:</h6>
                <ul class="mb-0">
                    <li>Normalization: Converted to lowercase, removed punctuation and numbers</li>
                    <li>Stopword Removal: Filtered out common Indonesian words</li>
                    <li>Tokenization: Split text into individual words</li>
                    <li>Stemming: Converted words to their root forms using Sastrawi</li>
                </ul>
            </div>
            <div class="mt-4">
                <a href="/tfidf" class="btn btn-primary btn-lg">
                    <i class="fas fa-arrow-right me-2"></i>
                    Proceed to TF-IDF Calculation
                </a>
            </div>
        </div>
    `);
}

function clearOutput() {
    $('#preprocessOutput').html(`
        <div class="text-center text-muted py-5">
            <i class="fas fa-cogs fa-3x mb-3 opacity-50"></i>
            <p>Select a preprocessing step to view the output</p>
        </div>
    `);
}

function updateRowIndexMax() {
    const dataset = $('#datasetSelect').val();
    // This would need to be populated from backend data
    // For now, keeping it simple
}

function displayStepOutput(step, response) {
    const stepNames = [
        'Original Text',
        'Step 1: Normalization',
        'Step 2: Stopword Removal',
        'Step 3: Tokenization',
        'Step 4: Stemming',
        'All Preprocessing Steps'  // Add this
    ];
    
    let html = `
        <div class="mb-4">
            <div class="d-flex align-items-center mb-3">
                <h5 class="mb-0">
                    <span class="badge bg-primary me-2">${step}</span>
                    ${stepNames[step]}
                </h5>
            </div>
            <div class="alert alert-light">
                <strong><i class="fas fa-file-alt me-2"></i>Record:</strong> ${response.record_name}
            </div>
        </div>
    `;
    
    if (step === 5) {
        // All steps output
        html += createAllStepsOutput(response.all_steps);
    } else if (step < 3) {
        // Text output
        html += createTextOutput(response.output);
    } else if (step === 3) {
        // Tokenization output
        html += createTokenOutput(response.output, response.token_count);
    } else if (step === 4) {
        // Stemming output
        html += createStemmingOutput(response);
    }
    
    $('#preprocessOutput').html(html);
}

function createAllStepsOutput(steps) {
    return `
        <div class="accordion" id="allStepsAccordion">
            <!-- Original Text -->
            <div class="accordion-item">
                <h2 class="accordion-header">
                    <button class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#step0">
                        <i class="fas fa-file-alt me-2"></i>
                        Original Text
                    </button>
                </h2>
                <div id="step0" class="accordion-collapse collapse show">
                    <div class="accordion-body">
                        <pre class="mb-0" style="white-space: pre-wrap; word-wrap: break-word;">${steps.original}</pre>
                    </div>
                </div>
            </div>
            
            <!-- Normalization -->
            <div class="accordion-item">
                <h2 class="accordion-header">
                    <button class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#step1">
                        <i class="fas fa-filter me-2"></i>
                        Step 1: Normalization
                    </button>
                </h2>
                <div id="step1" class="accordion-collapse collapse show">
                    <div class="accordion-body">
                        <div class="alert alert-info mb-3">
                            <strong>Changes:</strong> Lowercase, removed punctuation & numbers
                        </div>
                        <pre class="mb-0" style="white-space: pre-wrap; word-wrap: break-word;">${steps.normalized}</pre>
                    </div>
                </div>
            </div>
            
            <!-- Stopword Removal -->
            <div class="accordion-item">
                <h2 class="accordion-header">
                    <button class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#step2">
                        <i class="fas fa-ban me-2"></i>
                        Step 2: Stopword Removal
                    </button>
                </h2>
                <div id="step2" class="accordion-collapse collapse show">
                    <div class="accordion-body">
                        <div class="alert alert-info mb-3">
                            <strong>Changes:</strong> Filtered out common Indonesian words
                        </div>
                        <pre class="mb-0" style="white-space: pre-wrap; word-wrap: break-word;">${steps.no_stopwords}</pre>
                    </div>
                </div>
            </div>
            
            <!-- Tokenization -->
            <div class="accordion-item">
                <h2 class="accordion-header">
                    <button class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#step3">
                        <i class="fas fa-cut me-2"></i>
                        Step 3: Tokenization
                    </button>
                </h2>
                <div id="step3" class="accordion-collapse collapse show">
                    <div class="accordion-body">
                        <div class="mb-3">
                            ${steps.tokens.map(token => `<span class="badge bg-info me-1 mb-1">${token}</span>`).join('')}
                        </div>
                        <div class="alert alert-info mb-0">
                            <i class="fas fa-info-circle me-2"></i>
                            <strong>Total tokens:</strong> ${steps.tokens.length}
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Stemming with Comparison Table -->
            <div class="accordion-item">
                <h2 class="accordion-header">
                    <button class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#step4">
                        <i class="fas fa-leaf me-2"></i>
                        Step 4: Stemming
                    </button>
                </h2>
                <div id="step4" class="accordion-collapse collapse show">
                    <div class="accordion-body">
                        <!-- Stemmed Tokens -->
                        <h6 class="mb-3">Stemmed Tokens:</h6>
                        <div class="mb-3">
                            ${steps.stemmed_tokens.map(token => `<span class="badge bg-success me-1 mb-1">${token}</span>`).join('')}
                        </div>
                        <div class="alert alert-success mb-3">
                            <i class="fas fa-check-circle me-2"></i>
                            <strong>Total tokens after stemming:</strong> ${steps.token_count}
                        </div>
                        
                        <!-- Before & After Comparison Table -->
                        <div class="card">
                            <div class="card-header">
                                <i class="fas fa-exchange-alt me-2"></i>
                                Before & After Stemming Comparison (First 99 tokens)
                            </div>
                            <div class="card-body">
                                <div class="table-responsive">
                                    <table class="table table-sm table-striped table-hover">
                                        <thead class="table-dark">
                                            <tr>
                                                <th width="60">#</th>
                                                <th>Before Stemming</th>
                                                <th>After Stemming</th>
                                                <th width="100">Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${createStemmingComparisonRows(steps.tokens, steps.stemmed_tokens)}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function createStemmingComparisonRows(beforeTokens, afterTokens) {
    const maxShow = Math.min(99, beforeTokens.length);
    let rows = '';
    
    for (let i = 0; i < maxShow; i++) {
        const before = beforeTokens[i];
        const after = afterTokens[i];
        const changed = before !== after;
        
        rows += `
            <tr>
                <td><strong>${i + 1}</strong></td>
                <td><code>${before}</code></td>
                <td><code class="${changed ? 'text-success fw-bold' : ''}">${after}</code></td>
                <td>
                    ${changed ? 
                        '<span class="badge bg-warning text-dark">Changed</span>' : 
                        '<span class="badge bg-secondary">Same</span>'}
                </td>
            </tr>
        `;
    }
    
    if (beforeTokens.length > 99) {
        rows += `
            <tr class="table-info">
                <td colspan="4" class="text-center">
                    <em>... and ${beforeTokens.length - 99} more tokens</em>
                </td>
            </tr>
        `;
    }
    
    return rows;
}

// Make showStep globally available for inline onclick handlers
window.showStep = showStep;

