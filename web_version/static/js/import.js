/**
 * Import Data Page JavaScript
 */

$(document).ready(function() {
    initializePage();
    attachEventHandlers();
});

function initializePage() {
    // Initialize with default source
    updateSourceOptions();
}

function attachEventHandlers() {
    // Toggle data source options
    $('input[name="dataSource"]').change(function() {
        updateSourceOptions();
    });
    
    // Load data buttons
    $('#btnLoadBoth').click(() => loadData('both'));
    $('#btnLoadTraining').click(() => loadData('training'));
    $('#btnLoadJobs').click(() => loadData('jobs'));
    $('#btnLoadRealisasi').click(() => loadData('realisasi'));  // NEW
    
    // Clear logs
    $('#btnClearLogs').click(clearLogs);
}

function updateSourceOptions() {
    const source = $('input[name="dataSource"]:checked').val();
    
    if (source === 'github') {
        $('#githubOptions').show();
        $('#localOptions').hide();
    } else {
        $('#githubOptions').hide();
        $('#localOptions').show();
    }
}

function loadData(type) {
    const source = $('input[name="dataSource"]:checked').val();
    const buttonId = type === 'both' ? '#btnLoadBoth' : 
                     type === 'training' ? '#btnLoadTraining' : 
                     type === 'jobs' ? '#btnLoadJobs' :
                     '#btnLoadRealisasi';  // NEW
    const $button = $(buttonId);
    
    // Validate files for local source
    if (source === 'local' && type !== 'realisasi') {
        const validation = validateLocalFiles(type);
        if (!validation.valid) {
            showAlert('danger', validation.message);
            return;
        }
    }
    
    // NEW: Validate realisasi file for local
    if (source === 'local' && type === 'realisasi') {
        const realisasiFile = $('#realisasiFile')[0].files[0];
        if (!realisasiFile) {
            showAlert('danger', '<strong>Error!</strong> Please select a realisasi file.');
            return;
        }
    }
    
    // Disable button and show loading
    const originalText = $button.html();
    $button.prop('disabled', true)
           .html('<i class="fas fa-spinner fa-spin me-2"></i>Loading...');
    
    // Show loading in output
    $('#importStatus').html(`
        <div class="text-center py-4">
            ${showLoading('Loading data from ' + source + '...')}
            <p class="text-muted mt-3">This may take a moment depending on dataset size</p>
        </div>
    `);
    
    // Add log entries
    addImportLog('='.repeat(80), 'info');
    addImportLog(`Starting data import: ${type.toUpperCase()}`, 'info');
    addImportLog('='.repeat(80), 'info');
    addImportLog(`Source: ${source}`, 'info');
    
    if (source === 'github') {
        if (type === 'realisasi') {
            loadRealisasiFromGithub($button, originalText);  // NEW
        } else {
            loadFromGithub(type, $button, originalText);
        }
    } else {
        if (type === 'realisasi') {
            loadRealisasiFromLocal($button, originalText);  // NEW
        } else {
            loadFromLocal(type, $button, originalText);
        }
    }
}

function validateLocalFiles(type) {
    if (type === 'both' || type === 'training') {
        const trainingFile = $('#trainingFile')[0].files[0];
        if (!trainingFile) {
            return {
                valid: false,
                message: '<strong>Error!</strong> Please select a training programs file.'
            };
        }
    }
    
    if (type === 'both' || type === 'jobs') {
        const jobFile = $('#jobFile')[0].files[0];
        if (!jobFile) {
            return {
                valid: false,
                message: '<strong>Error!</strong> Please select a job positions file.'
            };
        }
    }
    
    return { valid: true };
}

function loadFromGithub(type, $button, originalText) {
    makeRequest('/api/load-data', 'POST', {
        source: 'github',
        type: type
    }, {
        onSuccess: function(response) {
            if (response.success) {
                handleLoadSuccess(response);
            } else {
                handleLoadError(response.message);
            }
        },
        onError: function(xhr, status, error) {
            handleLoadError('An unexpected error occurred. Please try again.');
        },
        onComplete: function() {
            $button.prop('disabled', false).html(originalText);
        }
    });
}

function loadFromLocal(type, $button, originalText) {
    const formData = new FormData();
    formData.append('source', 'local');
    formData.append('type', type);
    
    // Add files based on type
    if (type === 'both' || type === 'training') {
        const trainingFile = $('#trainingFile')[0].files[0];
        if (trainingFile) {
            formData.append('training_file', trainingFile);
            addImportLog(`Training file: ${trainingFile.name} (${formatFileSize(trainingFile.size)})`, 'info');
        }
    }
    
    if (type === 'both' || type === 'jobs') {
        const jobFile = $('#jobFile')[0].files[0];
        if (jobFile) {
            formData.append('job_file', jobFile);
            addImportLog(`Job file: ${jobFile.name} (${formatFileSize(jobFile.size)})`, 'info');
        }
    }
    
    if (type === 'both') {
        const realisasiFile = $('#realisasiFile')[0].files[0];
        if (realisasiFile) {
            formData.append('realisasi_file', realisasiFile);
            addImportLog(`Realisasi file: ${realisasiFile.name} (${formatFileSize(realisasiFile.size)})`, 'info');
        }
    }
    
    addImportLog('Uploading files...', 'info');
    
    // Use jQuery AJAX for file upload
    $.ajax({
        url: '/api/load-data',
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                handleLoadSuccess(response);
            } else {
                handleLoadError(response.message);
            }
        },
        error: function(xhr, status, error) {
            let errorMessage = 'An unexpected error occurred. Please try again.';
            try {
                const response = JSON.parse(xhr.responseText);
                if (response.message) {
                    errorMessage = response.message;
                }
            } catch (e) {
                // Use default error message
            }
            handleLoadError(errorMessage);
        },
        complete: function() {
            $button.prop('disabled', false).html(originalText);
        }
    });
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function handleLoadSuccess(response) {
    addImportLog('', 'info');
    addImportLog('✓ Data loaded successfully!', 'success');
    addImportLog('='.repeat(80), 'success');
    
    if (response.training_count) {
        addImportLog(`📚 Training Programs: ${response.training_count} records`, 'success');
        $('#trainingCount').text(response.training_count);
        animateValue('trainingCount', 0, response.training_count, 1000);
    }
    
    if (response.job_count) {
        addImportLog(`💼 Job Positions: ${response.job_count} records`, 'success');
        $('#jobCount').text(response.job_count);
        animateValue('jobCount', 0, response.job_count, 1000);
    }
    
    if (response.realisasi_count !== undefined) {
        addImportLog(`📈 Realisasi Penempatan: ${response.realisasi_count} records`, 'success');
        $('#realisasiCount').text(response.realisasi_count);
        animateValue('realisasiCount', 0, response.realisasi_count, 1000);
    }

    addImportLog('='.repeat(80), 'success');
    addImportLog('', 'info');
    
    const totalRecords =
    (response.training_count || 0) +
    (response.job_count || 0) +
    (response.realisasi_count || 0);
    
    addImportLog(`📊 Total records loaded: ${totalRecords}`, 'info');
    addImportLog('', 'info');
    
    addImportLog('✨ Ready for next step!', 'success');
    addImportLog('👉 Go to "Preprocessing" tab to process the data', 'info');
    
    // Show success alert
    const successAlert = showAlert('success', 
        '<strong>Success!</strong> Data loaded successfully. You can now proceed to preprocessing.');
    $('#importStatus').append(successAlert);
}

function handleLoadError(message) {
    addImportLog('', 'error');
    addImportLog('✗ Failed to load data', 'error');
    addImportLog(`Error: ${message}`, 'error');
    
    const errorAlert = showAlert('danger', 
        `<strong>Error!</strong> ${message}`);
    $('#importStatus').append(errorAlert);
}

function addImportLog(message, type = 'info') {
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
    
    const $container = $('#importStatus');
    
    // Clear placeholder if exists
    if ($container.find('.text-center').length > 0) {
        $container.html('');
    }
    
    $container.append(log);
    $container.scrollTop($container[0].scrollHeight);
}

function clearLogs() {
    $('#importStatus').html(`
        <div class="text-center text-muted py-5">
            <i class="fas fa-file-import fa-3x mb-3 opacity-50"></i>
            <p>Logs cleared. Ready to import data.</p>
        </div>
    `);
}

function loadRealisasiFromGithub($button, originalText) {
    makeRequest('/api/load-realisasi', 'POST', {
        source: 'github'
    }, {
        onSuccess: function(response) {
            if (response.success) {
                addImportLog('', 'info');
                addImportLog('✓ Realisasi data loaded successfully!', 'success');
                addImportLog('='.repeat(80), 'success');
                addImportLog(`📊 Realisasi Records: ${response.realisasi_count}`, 'success');
                
                $('#realisasiCount').text(response.realisasi_count);
                animateValue('realisasiCount', 0, response.realisasi_count, 1000);
                
                const successAlert = showAlert('success', 
                    '<strong>Success!</strong> Realisasi data loaded successfully.');
                $('#importStatus').append(successAlert);
            } else {
                handleLoadError(response.message);
            }
        },
        onError: function(xhr, status, error) {
            handleLoadError('An unexpected error occurred. Please try again.');
        },
        onComplete: function() {
            $button.prop('disabled', false).html(originalText);
        }
    });
}

// NEW: Load realisasi from local file
function loadRealisasiFromLocal($button, originalText) {
    const formData = new FormData();
    formData.append('source', 'local');
    
    const realisasiFile = $('#realisasiFile')[0].files[0];
    if (realisasiFile) {
        formData.append('realisasi_file', realisasiFile);
        addImportLog(`Realisasi file: ${realisasiFile.name} (${formatFileSize(realisasiFile.size)})`, 'info');
    }
    
    addImportLog('Uploading file...', 'info');
    
    $.ajax({
        url: '/api/load-realisasi',
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.success) {
                addImportLog('', 'info');
                addImportLog('✓ Realisasi data loaded successfully!', 'success');
                addImportLog('='.repeat(80), 'success');
                addImportLog(`📊 Realisasi Records: ${response.realisasi_count}`, 'success');
                
                $('#realisasiCount').text(response.realisasi_count);
                animateValue('realisasiCount', 0, response.realisasi_count, 1000);
                
                const successAlert = showAlert('success', 
                    '<strong>Success!</strong> Realisasi data loaded successfully.');
                $('#importStatus').append(successAlert);
            } else {
                handleLoadError(response.message);
            }
        },
        error: function(xhr, status, error) {
            let errorMessage = 'An unexpected error occurred. Please try again.';
            try {
                const response = JSON.parse(xhr.responseText);
                if (response.message) {
                    errorMessage = response.message;
                }
            } catch (e) {
                // Use default error message
            }
            handleLoadError(errorMessage);
        },
        complete: function() {
            $button.prop('disabled', false).html(originalText);
        }
    });
}