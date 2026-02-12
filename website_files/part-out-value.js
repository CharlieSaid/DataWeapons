// Supabase configuration
const SUPABASE_URL = 'https://uxdqrswbcgkkftvompwd.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV4ZHFyc3diY2dra2Z0dm9tcHdkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI2MjIwOTQsImV4cCI6MjA3ODE5ODA5NH0.BzGPmvy5YpvPQ6His7SAoYlFnuWGQWHnBUXw5B7huWQ';

// Initialize Supabase client (SDK is loaded in HTML head)
let supabaseClient = null;

function initSupabase() {
    const supabaseLib = window.supabase || (typeof supabase !== 'undefined' ? supabase : null);
    
    if (supabaseLib && typeof supabaseLib.createClient === 'function') {
        supabaseClient = supabaseLib.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
        return true;
    }
    return false;
}

// Numeric column patterns - columns matching these patterns should be sorted numerically
// This includes base names and names with suffixes like _current, _past_6m
const NUMERIC_COLUMN_PATTERNS = [
    'profit_pct',
    'profit_margin_pct',
    'msrp',
    'sale_price',
    'pov_vs_sale_profit',
    'pov_vs_msrp_profit',
    'pov_current_listings',
    'pov_past_6_months',
    'pov_per_piece',
    'value_ratio',
    'item_number',
    'piece_count',
    'price_per_piece'
];

// Sort data by column
function sortData(data, column, direction) {
    const sorted = [...data];
    
    sorted.sort((a, b) => {
        let aVal = a[column];
        let bVal = b[column];
        
        // Check if this is a numeric column by matching against patterns
        // This handles columns with suffixes like profit_pct_current, pov_per_piece_past_6m, etc.
        const isNumeric = NUMERIC_COLUMN_PATTERNS.some(pattern => 
            column === pattern || 
            column.startsWith(pattern + '_') || 
            column.endsWith('_' + pattern)
        );
        
        if (isNumeric) {
            // Parse numeric values (handles both numbers and strings with currency symbols)
            const parseNumeric = (val) => {
                if (val === null || val === undefined || val === '') return null;
                if (typeof val === 'number') {
                    return isNaN(val) ? null : val;
                }
                // Remove currency symbols, commas, and other non-numeric characters
                const cleaned = val.toString().replace(/[^0-9.-]/g, '');
                const parsed = parseFloat(cleaned);
                return isNaN(parsed) ? null : parsed;
            };
            
            aVal = parseNumeric(aVal);
            bVal = parseNumeric(bVal);
            
            // Handle null values - put them at the end
            if (aVal === null && bVal === null) return 0;
            if (aVal === null) return 1;  // null values go to end
            if (bVal === null) return -1; // null values go to end
            
            // Numeric comparison
            if (aVal < bVal) return direction === 'asc' ? -1 : 1;
            if (aVal > bVal) return direction === 'asc' ? 1 : -1;
            return 0;
        } else {
            // String comparison
            aVal = (aVal || '').toString().toLowerCase();
            bVal = (bVal || '').toString().toLowerCase();
            
            if (aVal < bVal) return direction === 'asc' ? -1 : 1;
            if (aVal > bVal) return direction === 'asc' ? 1 : -1;
            return 0;
        }
    });
    
    return sorted;
}

// Format currency values
function formatCurrency(value) {
    if (!value || value === '') return 'N/A';
    return value;
}

// Base column definitions (without time period suffix)
const BASE_DISPLAY_COLUMNS = [
    'set_name',
    'profit_pct',
    'msrp',
    'sale_price',
    'pov_vs_sale_profit',
    'pov_absolute',
    'pov_per_piece'
];

// Column display names mapping (base names, will be resolved to actual column names)
const BASE_COLUMN_DISPLAY_NAMES = {
    'set_name': 'Set Name',
    'profit_pct': 'Profit %',
    'msrp': 'MSRP',
    'sale_price': 'Sale Price',
    'pov_vs_sale_profit': 'POV minus Cost',
    'pov_absolute': 'POV (Absolute)',
    'pov_per_piece': 'POV per Piece'
};

// Get the actual column names based on the selected POV period
function getDisplayColumns() {
    const suffix = povPeriod === 'current' ? '_current' : '_past_6m';
    return BASE_DISPLAY_COLUMNS.map(col => {
        if (col === 'set_name' || col === 'msrp' || col === 'sale_price') {
            return col; // These don't have time period variants
        } else if (col === 'pov_absolute') {
            return povPeriod === 'current' ? 'pov_current_listings' : 'pov_past_6_months';
        } else {
            return col + suffix;
        }
    });
}

// Get column display names (same for both periods)
function getColumnDisplayNames() {
    return BASE_COLUMN_DISPLAY_NAMES;
}

// Create table HTML with sorting
function createTable(data, sortColumn = null, sortDirection = 'asc') {
    if (!data || data.length === 0) {
        return '<p>No data available</p>';
    }
    
    // Get the actual column names based on current POV period
    const displayColumns = getDisplayColumns();
    const columnDisplayNames = getColumnDisplayNames();
    
    // Map base column names to actual column names for display name lookup
    const baseToActual = {};
    BASE_DISPLAY_COLUMNS.forEach((baseCol, idx) => {
        baseToActual[displayColumns[idx]] = baseCol;
    });
    
    // Filter to only show specified columns
    const headers = displayColumns.filter(col => data[0].hasOwnProperty(col));
    let html = '<table><thead><tr>';
    
    headers.forEach(header => {
        const baseCol = baseToActual[header] || header;
        const displayName = columnDisplayNames[baseCol] || header.replace(/_/g, ' ').toUpperCase();
        let sortIndicator = '';
        
        if (sortColumn === header) {
            sortIndicator = sortDirection === 'asc' ? ' ↑' : ' ↓';
        }
        
        html += `<th class="sortable" data-column="${header}">${displayName}${sortIndicator}</th>`;
    });
    html += '</tr></thead><tbody>';
    
    // Display all data, not just top 50
    data.forEach(row => {
        html += '<tr>';
        headers.forEach(header => {
            let value = row[header];
            // Make set_name a clickable link if url is available
            if (header === 'set_name') {
                const url = row['url'];
                if (url && url.trim() !== '') {
                    value = `<a href="${url}" target="_blank" rel="noopener noreferrer" class="set-name-link">${value || 'N/A'}</a>`;
                } else {
                    value = value || 'N/A';
                }
            } else if (header.includes('profit_pct')) {
                // Format profit percentage with % sign
                if (value == null || value === '') {
                    value = 'N/A';
                } else {
                    const numValue = typeof value === 'number' ? value : parseFloat(value);
                    value = isNaN(numValue) ? 'N/A' : `${numValue.toFixed(2)}%`;
                }
            } else if (header.includes('per_piece')) {
                // Format per piece with 4 decimal places
                if (value == null || value === '') {
                    value = 'N/A';
                } else {
                    const numValue = typeof value === 'number' ? value : parseFloat(value);
                    value = isNaN(numValue) ? 'N/A' : `$${numValue.toFixed(4)}`;
                }
            } else if (header === 'msrp' || header.includes('price') || header.includes('pov') || header.includes('profit')) {
                // Format as currency
                if (value == null || value === '') {
                    value = 'N/A';
                } else if (typeof value === 'number') {
                    value = `$${value.toFixed(2)}`;
                } else {
                    value = formatCurrency(value);
                }
            }
            html += `<td>${value ?? ''}</td>`;
        });
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    return html;
}

// Global state for sorting and filtering
let currentData = [];
let currentSortColumn = 'pov_vs_sale_profit_current';
let currentSortDirection = 'desc';
let currentSearchTerm = ''; // Current search filter
let hideNAData = true; // Default to hiding NA data
let povPeriod = 'current'; // 'current' or 'past_6m' - which POV period to use for derived fields

// Filter data by set name (case-insensitive substring match)
function filterDataBySearch(data, searchTerm) {
    if (!searchTerm || searchTerm.trim() === '') {
        return data;
    }
    
    const term = searchTerm.toLowerCase().trim();
    return data.filter(row => {
        const setName = (row.set_name || '').toLowerCase();
        return setName.includes(term);
    });
}

// Filter out rows with NA values in POV-related columns
function filterNAData(data, hideNA) {
    if (!hideNA) {
        return data;
    }
    
    // Get the actual column names based on current POV period
    const suffix = povPeriod === 'current' ? '_current' : '_past_6m';
    const povAbsoluteCol = povPeriod === 'current' ? 'pov_current_listings' : 'pov_past_6_months';
    
    // POV-related columns that should not be NA (using current period's columns)
    const povColumns = [
        'profit_pct' + suffix,
        'pov_vs_sale_profit' + suffix,
        povAbsoluteCol,
        'pov_per_piece' + suffix,
        'pov_vs_msrp_profit' + suffix
    ];
    
    return data.filter(row => {
        // Check if at least one POV column has a valid (non-NA) value
        return povColumns.some(col => {
            const value = row[col];
            // Consider value valid if it's not null, undefined, empty string, or 'N/A'
            return value !== null && 
                   value !== undefined && 
                   value !== '' && 
                   value !== 'N/A' &&
                   !(typeof value === 'number' && isNaN(value));
        });
    });
}

// Initialize search bar (called once when data loads)
function initializeSearchBar() {
    if (currentData.length === 0) return;
    
    const container = document.getElementById('data-container');
    let searchBarContainer = document.getElementById('search-container-placeholder');
    
    // Create container if it doesn't exist
    if (!searchBarContainer) {
        searchBarContainer = document.createElement('div');
        searchBarContainer.id = 'search-container-placeholder';
        searchBarContainer.style.marginBottom = '1.5rem';
        container.parentNode.insertBefore(searchBarContainer, container);
    }
    
    // Get or create search input
    let searchInput = document.getElementById('search-input');
    let hideNAToggle = document.getElementById('hide-na-toggle');
    let povPeriodSelect = document.getElementById('pov-period-select');
    
    if (!searchInput) {
        // Create search bar HTML if input doesn't exist
        const escapedSearchTerm = (currentSearchTerm || '').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
        const checkedAttr = hideNAData ? ' checked' : '';
        const selectedCurrent = povPeriod === 'current' ? ' selected' : '';
        const selectedPast6m = povPeriod === 'past_6m' ? ' selected' : '';
        searchBarContainer.innerHTML = '<div class="search-container">' +
            '<input type="text" id="search-input" class="search-input" placeholder="Search by set name..." value="' + escapedSearchTerm + '">' +
            '<span class="search-results-count" id="search-results-count">0 sets</span>' +
            '<label class="hide-na-toggle">' +
            '<input type="checkbox" id="hide-na-toggle"' + checkedAttr + '>' +
            '<span>Hide NA data</span>' +
            '</label>' +
            '<label class="pov-period-selector">' +
            '<span>POV Period:</span>' +
            '<select id="pov-period-select" class="pov-period-select">' +
            '<option value="current"' + selectedCurrent + '>Current Listings</option>' +
            '<option value="past_6m"' + selectedPast6m + '>Past 6 Months</option>' +
            '</select>' +
            '</label>' +
            '</div>';
        searchInput = document.getElementById('search-input');
        hideNAToggle = document.getElementById('hide-na-toggle');
        povPeriodSelect = document.getElementById('pov-period-select');
    }
    
    // Always ensure event listener is attached (in case input exists from HTML)
    if (searchInput && !searchInput.hasAttribute('data-listener-attached')) {
        searchInput.setAttribute('data-listener-attached', 'true');
        searchInput.addEventListener('input', (e) => {
            currentSearchTerm = e.target.value;
            renderTable();
        });
    }
    
    // Attach event listener to hide NA toggle
    if (hideNAToggle && !hideNAToggle.hasAttribute('data-listener-attached')) {
        hideNAToggle.setAttribute('data-listener-attached', 'true');
        hideNAToggle.addEventListener('change', (e) => {
            hideNAData = e.target.checked;
            renderTable();
        });
    }
    
    // Attach event listener to POV period selector
    if (povPeriodSelect && !povPeriodSelect.hasAttribute('data-listener-attached')) {
        povPeriodSelect.setAttribute('data-listener-attached', 'true');
        povPeriodSelect.addEventListener('change', (e) => {
            povPeriod = e.target.value;
            // Update sort column if it's a derived field
            const suffix = povPeriod === 'current' ? '_current' : '_past_6m';
            if (currentSortColumn.endsWith('_current') || currentSortColumn.endsWith('_past_6m')) {
                const baseCol = currentSortColumn.replace(/_current$|_past_6m$/, '');
                currentSortColumn = baseCol + suffix;
            } else if (currentSortColumn === 'pov_current_listings') {
                currentSortColumn = povPeriod === 'current' ? 'pov_current_listings' : 'pov_past_6_months';
            } else if (currentSortColumn === 'pov_past_6_months') {
                currentSortColumn = povPeriod === 'current' ? 'pov_current_listings' : 'pov_past_6_months';
            }
            renderTable();
        });
    }
    
    // Sync input value with current search term
    if (searchInput && searchInput.value !== currentSearchTerm) {
        searchInput.value = currentSearchTerm;
    }
    
    // Sync toggle state
    if (hideNAToggle && hideNAToggle.checked !== hideNAData) {
        hideNAToggle.checked = hideNAData;
    }
    
    // Sync period selector state
    if (povPeriodSelect && povPeriodSelect.value !== povPeriod) {
        povPeriodSelect.value = povPeriod;
    }
    
    searchBarContainer.style.display = 'block';
}

// Update search results count
function updateSearchResultsCount(filteredCount, totalCount) {
    const resultsCount = document.getElementById('search-results-count');
    if (resultsCount) {
        resultsCount.textContent = filteredCount + ' of ' + totalCount + ' sets';
    }
}

// Render table with current sort and search filter
function renderTable() {
    const container = document.getElementById('data-container');
    
    // Filter data: first by NA, then by search, then sort
    let filteredData = filterNAData(currentData, hideNAData);
    filteredData = filterDataBySearch(filteredData, currentSearchTerm);
    const sortedData = sortData(filteredData, currentSortColumn, currentSortDirection);
    
    // Update search results count (show filtered count vs total after NA filter)
    const totalAfterNAFilter = hideNAData ? filterNAData(currentData, true).length : currentData.length;
    updateSearchResultsCount(filteredData.length, totalAfterNAFilter);
    
    // Render table content
    const tableHtml = createTable(sortedData, currentSortColumn, currentSortDirection);
    container.innerHTML = tableHtml;
    
    const sortableHeaders = container.querySelectorAll('th.sortable');
    sortableHeaders.forEach(header => {
        header.addEventListener('click', () => {
            const column = header.getAttribute('data-column');
            
            if (currentSortColumn === column) {
                currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                currentSortColumn = column;
                currentSortDirection = 'asc';
            }
            
            renderTable();
        });
    });
}

// Load and display data
async function loadData() {
    const container = document.getElementById('data-container');
    
    try {
        if (!supabaseClient) {
            if (!initSupabase()) {
                throw new Error('Supabase SDK not loaded. Please check script tag in HTML.');
            }
        }

        const tableName = 'lego_sets_with_pov';
        console.log(`Querying Supabase table: ${tableName}`);
        
        // Load ALL rows by using pagination (Supabase default limit is 1000)
        // Fetch in batches to get all data
        let allData = [];
        let hasMore = true;
        let offset = 0;
        const batchSize = 1000; // Supabase max per request
        
        while (hasMore) {
            const { data, error } = await supabaseClient
                .from(tableName) 
                .select('set_name, url, profit_pct_current, profit_pct_past_6m, msrp, sale_price, pov_vs_sale_profit_current, pov_vs_sale_profit_past_6m, pov_current_listings, pov_past_6_months, pov_per_piece_current, pov_per_piece_past_6m')
                .range(offset, offset + batchSize - 1); // Fetch batch
            
            if (error) {
                console.error('Supabase error details:', error);
                throw new Error(`Supabase error: ${error.message} (Code: ${error.code || 'unknown'})`);
            }
            
            if (data && data.length > 0) {
                allData = allData.concat(data);
                offset += batchSize;
                hasMore = data.length === batchSize; // If we got a full batch, there might be more
            } else {
                hasMore = false;
            }
        }
        
        const data = allData;
    
        console.log('Supabase response:', { data, dataLength: data?.length });
        
        if (!data) {
            throw new Error(`No data returned from table "${tableName}". Check if the table exists.`);
        }
        
        if (!data.length) {
            throw new Error(`Table "${tableName}" exists but is empty. No rows found.`);
        }
    
        console.log(`Successfully loaded ${data.length} rows from ${tableName}`);
        currentData = data;
    
        // Initialize search bar first, then render table
        initializeSearchBar();
        renderTable();
    
    } catch (error) {
        console.error('Error loading data:', error);
        container.innerHTML = `<p>Error loading data: ${error.message}</p>`;
    }
}

// Load data when the page loads
document.addEventListener('DOMContentLoaded', () => {
    function waitForSupabase() {
        if (window.supabaseReady || typeof window.supabase !== 'undefined') {
            loadData();
        } else {
            const startTime = Date.now();
            const checkInterval = setInterval(() => {
                if (window.supabaseReady || typeof window.supabase !== 'undefined') {
                    clearInterval(checkInterval);
                    loadData();
                } else if (Date.now() - startTime > 2000) {
                    clearInterval(checkInterval);
                    console.error('Supabase SDK failed to load after 2 seconds');
                    document.getElementById('data-container').innerHTML = 
                        '<p>Error: Supabase SDK failed to load. Please refresh the page.</p>';
                }
            }, 50);
        }
    }
    waitForSupabase();
});
