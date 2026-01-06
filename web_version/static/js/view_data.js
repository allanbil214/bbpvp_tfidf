/**
 * View Data Page JavaScript
 */

let currentPage = 1;
let currentDataset = 'training';
let currentPerPage = 10;
let isSearchMode = false;

$(document).ready(function() {
    attachEventHandlers();
});

function attachEventHandlers() {
    // Load data
    $('#btnLoadData').click(loadData);
    
    // Search
    $('#btnSearch').click(performSearch);
    $('#btnClearSearch').click(clearSearch);
    
    // Enter key for search
    $('#searchInput').keypress(function(e) {
        if (e.which === 13) {
            performSearch();
        }
    });
    
    // Dataset change
    $('#datasetSelect').change(function() {
        currentDataset = $(this).val();
        currentPage = 1;
        updateDataTitle();
        if (!isSearchMode) {
            loadData();
        }
    });
    
    // Per page change
    $('#perPageSelect').change(function() {
        currentPerPage = parseInt($(this).val());
        currentPage = 1;
        if (isSearchMode) {
            performSearch();
        } else {
            loadData();
        }
    });
}

function updateDataTitle() {
    const title = currentDataset === 'training' ? 
        'Training Programs Data' : 'Job Positions Data';
    $('#dataTitle').text(title);
}

function loadData() {
    isSearchMode = false;
    $('#btnClearSearch').hide();
    
    const $btn = $('#btnLoadData');
    $btn.prop('disabled', true)
        .html('<i class="fas fa-spinner fa-spin me-2"></i>Loading...');
    
    updateDataTitle();
    
    makeRequest('/api/get-data', 'POST', {
        dataset: currentDataset,
        page: currentPage,
        per_page: currentPerPage
    }, {
        showLoading: true,
        loadingTarget: '#dataDisplay',
        loadingMessage: 'Loading data...',
        onSuccess: function(response) {
            if (response.success) {
                displayData(response);
                displayPagination(response.pagination);
            } else {
                showAlert('danger', response.message, '#dataDisplay');
            }
        },
        onComplete: function() {
            $btn.prop('disabled', false)
                .html('<i class="fas fa-sync-alt me-2"></i>Load Data');
        }
    });
}

function performSearch() {
    const searchTerm = $('#searchInput').val().trim();
    
    if (!searchTerm) {
        showAlert('warning', 'Please enter a search term', '#dataDisplay');
        return;
    }
    
    isSearchMode = true;
    $('#btnClearSearch').show();
    
    const $btn = $('#btnSearch');
    $btn.prop('disabled', true)
        .html('<i class="fas fa-spinner fa-spin me-2"></i>Searching...');
    
    makeRequest('/api/search-data', 'POST', {
        dataset: currentDataset,
        search: searchTerm
    }, {
        showLoading: true,
        loadingTarget: '#dataDisplay',
        loadingMessage: 'Searching data...',
        onSuccess: function(response) {
            if (response.success) {
                displaySearchResults(response);
                $('#paginationCard').hide();
            } else {
                showAlert('danger', response.message, '#dataDisplay');
            }
        },
        onComplete: function() {
            $btn.prop('disabled', false)
                .html('<i class="fas fa-search me-2"></i>Search');
        }
    });
}

function clearSearch() {
    $('#searchInput').val('');
    isSearchMode = false;
    $('#btnClearSearch').hide();
    currentPage = 1;
    loadData();
}

function displayData(response) {
    const records = response.records;
    const columns = response.columns;
    
    if (records.length === 0) {
        $('#dataDisplay').html(`
            <div class="text-center text-muted py-5">
                <i class="fas fa-inbox fa-3x mb-3 opacity-50"></i>
                <p>No records found</p>
            </div>
        `);
        $('#recordCount').text('0 records');
        return;
    }
    
    $('#recordCount').text(`${response.pagination.total_records} records`);
    
    let html = '<div class="table-responsive">';
    html += '<table class="table table-hover table-striped">';
    html += '<thead><tr>';
    html += '<th width="60">#</th>';
    
    columns.forEach(col => {
        html += `<th>${col}</th>`;
    });
    
    html += '<th width="100">Actions</th>';
    html += '</tr></thead><tbody>';
    
    records.forEach(record => {
        html += '<tr>';
        html += `<td class="text-muted">${record.index}</td>`;
        
        columns.forEach(col => {
            const value = record[col] || '';
            const displayValue = value.length > 150 ? value.substring(0, 150) + '...' : value;
            html += `<td><small>${displayValue}</small></td>`;
        });
        
        html += `<td>
            <button class="btn btn-sm btn-outline-primary" onclick="viewRecordDetail(${record.index})">
                <i class="fas fa-eye"></i>
            </button>
        </td>`;
        html += '</tr>';
    });
    
    html += '</tbody></table></div>';
    
    $('#dataDisplay').html(html);
}

function displaySearchResults(response) {
    const records = response.records;
    const columns = response.columns;
    
    if (records.length === 0) {
        $('#dataDisplay').html(`
            <div class="text-center py-5">
                <i class="fas fa-search fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No results found</h5>
                <p class="text-muted">Try a different search term</p>
                <button class="btn btn-outline-primary mt-3" onclick="clearSearch()">
                    <i class="fas fa-times me-2"></i>
                    Clear Search
                </button>
            </div>
        `);
        $('#recordCount').text('0 results');
        return;
    }
    
    $('#recordCount').text(`${response.total_found} results`);
    
    const alert = `
        <div class="alert alert-success mb-3">
            <i class="fas fa-check-circle me-2"></i>
            Found <strong>${response.total_found}</strong> matching records
        </div>
    `;
    
    let html = alert + '<div class="table-responsive">';
    html += '<table class="table table-hover table-striped">';
    html += '<thead><tr>';
    html += '<th width="60">#</th>';
    
    columns.forEach(col => {
        html += `<th>${col}</th>`;
    });
    
    html += '<th width="100">Actions</th>';
    html += '</tr></thead><tbody>';
    
    records.forEach(record => {
        html += '<tr>';
        html += `<td class="text-muted">${record.index}</td>`;
        
        columns.forEach(col => {
            const value = record[col] || '';
            const displayValue = value.length > 150 ? value.substring(0, 150) + '...' : value;
            html += `<td><small>${displayValue}</small></td>`;
        });
        
        html += `<td>
            <button class="btn btn-sm btn-outline-primary" onclick="viewRecordDetail(${record.index})">
                <i class="fas fa-eye"></i>
            </button>
        </td>`;
        html += '</tr>';
    });
    
    html += '</tbody></table></div>';
    
    $('#dataDisplay').html(html);
}

function displayPagination(pagination) {
    if (pagination.total_pages <= 1) {
        $('#paginationCard').hide();
        return;
    }
    
    $('#paginationCard').show();
    
    // Update info text
    $('#paginationInfo').text(
        `Showing ${pagination.start_idx} to ${pagination.end_idx} of ${pagination.total_records} records`
    );
    
    // Generate pagination buttons
    let html = '';
    
    // Previous button
    html += `
        <li class="page-item ${pagination.page === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="goToPage(${pagination.page - 1}); return false;">
                <i class="fas fa-chevron-left"></i>
            </a>
        </li>
    `;
    
    // Page numbers
    const maxButtons = 5;
    let startPage = Math.max(1, pagination.page - Math.floor(maxButtons / 2));
    let endPage = Math.min(pagination.total_pages, startPage + maxButtons - 1);
    
    if (endPage - startPage < maxButtons - 1) {
        startPage = Math.max(1, endPage - maxButtons + 1);
    }
    
    if (startPage > 1) {
        html += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="goToPage(1); return false;">1</a>
            </li>
        `;
        if (startPage > 2) {
            html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
        }
    }
    
    for (let i = startPage; i <= endPage; i++) {
        html += `
            <li class="page-item ${i === pagination.page ? 'active' : ''}">
                <a class="page-link" href="#" onclick="goToPage(${i}); return false;">${i}</a>
            </li>
        `;
    }
    
    if (endPage < pagination.total_pages) {
        if (endPage < pagination.total_pages - 1) {
            html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
        }
        html += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="goToPage(${pagination.total_pages}); return false;">
                    ${pagination.total_pages}
                </a>
            </li>
        `;
    }
    
    // Next button
    html += `
        <li class="page-item ${pagination.page === pagination.total_pages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="goToPage(${pagination.page + 1}); return false;">
                <i class="fas fa-chevron-right"></i>
            </a>
        </li>
    `;
    
    $('#paginationControls').html(html);
}

function goToPage(page) {
    currentPage = page;
    loadData();
    
    // Scroll to top
    $('html, body').animate({
        scrollTop: $('#dataDisplay').offset().top - 100
    }, 300);
}

function viewRecordDetail(index) {
    makeRequest('/api/get-record-detail', 'POST', {
        dataset: currentDataset,
        index: index
    }, {
        onSuccess: function(response) {
            if (response.success) {
                displayRecordDetail(response.record);
            } else {
                alert('Failed to load record details');
            }
        }
    });
}

function displayRecordDetail(record) {
    let html = '<div class="record-detail">';
    
    html += `<div class="alert alert-info mb-3">
        <strong><i class="fas fa-hashtag me-2"></i>Record Index:</strong> ${record.index}
    </div>`;
    
    // Display all fields
    for (const [key, value] of Object.entries(record)) {
        if (key === 'index') continue;
        
        html += '<div class="mb-3">';
        html += `<label class="form-label fw-bold"><i class="fas fa-tag me-2 text-primary"></i>${key}</label>`;
        
        if (value.length > 500) {
            html += `<textarea class="form-control" rows="10" readonly>${value}</textarea>`;
        } else {
            html += `<div class="form-control" style="min-height: 60px; background: #f8fafc;">${value}</div>`;
        }
        
        html += '</div>';
    }
    
    html += '</div>';
    
    $('#recordDetailBody').html(html);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('recordDetailModal'));
    modal.show();
}

// Make functions globally available
window.goToPage = goToPage;
window.viewRecordDetail = viewRecordDetail;
window.clearSearch = clearSearch;