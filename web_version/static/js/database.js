/**
 * Database Configuration Page JavaScript
 */

$(document).ready(function() {
    attachEventHandlers();
});

function attachEventHandlers() {
    // Toggle password visibility
    $('#togglePassword').click(togglePasswordVisibility);
    
    // Test connection
    $('#btnTestConnection').click(testConnection);
    
    // Save configuration
    $('#btnSaveConfig').click(saveConfiguration);
}

function togglePasswordVisibility() {
    const $passwordInput = $('#dbPassword');
    const $icon = $('#togglePassword i');
    
    if ($passwordInput.attr('type') === 'password') {
        $passwordInput.attr('type', 'text');
        $icon.removeClass('fa-eye').addClass('fa-eye-slash');
    } else {
        $passwordInput.attr('type', 'password');
        $icon.removeClass('fa-eye-slash').addClass('fa-eye');
    }
}

function testConnection() {
    const $btn = $('#btnTestConnection');
    $btn.prop('disabled', true)
        .html('<i class="fas fa-spinner fa-spin me-2"></i>Testing...');
    
    $('#statusBadge')
        .removeClass('bg-success bg-danger bg-secondary')
        .addClass('bg-warning')
        .text('Testing...');
    
    $('#statusDisplay').html(showLoading('Testing database connection...'));
    
    const config = getConnectionConfig();
    
    addLog('Starting connection test...', 'info');
    addLog(`Host: ${config.host}`, 'info');
    addLog(`Port: ${config.port}`, 'info');
    addLog(`Database: ${config.database}`, 'info');
    addLog(`User: ${config.user}`, 'info');
    
    makeRequest('/api/test-connection', 'POST', config, {
        onSuccess: function(response) {
            if (response.success) {
                handleConnectionSuccess(config, response.message);
            } else {
                handleConnectionError(response.message);
            }
        },
        onError: function(xhr, status, error) {
            handleConnectionError('An unexpected error occurred');
        },
        onComplete: function() {
            $btn.prop('disabled', false)
                .html('<i class="fas fa-plug me-2"></i>Test Connection');
        }
    });
}

function getConnectionConfig() {
    return {
        host: $('#dbHost').val(),
        port: parseInt($('#dbPort').val()),
        database: $('#dbName').val(),
        user: $('#dbUser').val(),
        password: $('#dbPassword').val()
    };
}

function handleConnectionSuccess(config, message) {
    $('#statusBadge')
        .removeClass('bg-warning bg-danger bg-secondary')
        .addClass('bg-success')
        .text('Connected');
    
    $('#statusDisplay').html(`
        <div class="text-center py-4">
            <i class="fas fa-check-circle fa-4x text-success mb-3"></i>
            <h5 class="text-success mb-3">Connection Successful!</h5>
            <div class="alert alert-success text-start">
                <strong><i class="fas fa-server me-2"></i>Connection Details:</strong>
                <hr>
                <div class="row">
                    <div class="col-6"><strong>Host:</strong></div>
                    <div class="col-6">${config.host}</div>
                    <div class="col-6"><strong>Port:</strong></div>
                    <div class="col-6">${config.port}</div>
                    <div class="col-6"><strong>Database:</strong></div>
                    <div class="col-6">${config.database}</div>
                    <div class="col-6"><strong>User:</strong></div>
                    <div class="col-6">${config.user}</div>
                    <div class="col-6"><strong>Status:</strong></div>
                    <div class="col-6"><span class="badge bg-success">Active</span></div>
                </div>
            </div>
            <p class="text-muted">${message}</p>
        </div>
    `);
    
    addLog('✓ Connection successful!', 'success');
    addLog(message, 'success');
}

function handleConnectionError(message) {
    $('#statusBadge')
        .removeClass('bg-warning bg-success bg-secondary')
        .addClass('bg-danger')
        .text('Failed');
    
    $('#statusDisplay').html(`
        <div class="text-center py-4">
            <i class="fas fa-times-circle fa-4x text-danger mb-3"></i>
            <h5 class="text-danger mb-3">Connection Failed</h5>
            <div class="alert alert-danger text-start">
                <strong><i class="fas fa-exclamation-triangle me-2"></i>Error:</strong>
                <hr>
                <p class="mb-0">${message}</p>
            </div>
            <p class="text-muted">Please check your settings and try again</p>
        </div>
    `);
    
    addLog('✗ Connection failed!', 'error');
    addLog(message, 'error');
}

function saveConfiguration() {
    const config = getConnectionConfig();
    
    // In a real application, this would save to backend
    addLog('Configuration saved locally', 'success');
    
    const alert = showAlert('success', 
        'Configuration saved successfully! <br><small>Note: Configuration is saved for this session only.</small>');
    
    $('#dbConfigForm').prepend(alert);
    
    setTimeout(() => {
        $('.alert').fadeOut();
    }, 3000);
}

function addLog(message, type = 'info') {
    const timestamp = new Date().toLocaleTimeString();
    const icons = {
        'info': 'fa-info-circle text-info',
        'success': 'fa-check-circle text-success',
        'error': 'fa-times-circle text-danger',
        'warning': 'fa-exclamation-triangle text-warning'
    };
    
    const log = `
        <div class="mb-2">
            <span class="text-muted">[${timestamp}]</span>
            <i class="fas ${icons[type]} me-2"></i>
            ${message}
        </div>
    `;
    
    $('#connectionLogs').append(log);
    $('#connectionLogs').scrollTop($('#connectionLogs')[0].scrollHeight);
}