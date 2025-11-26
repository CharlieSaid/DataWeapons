// Supabase configuration
const SUPABASE_URL = 'https://uxdqrswbcgkkftvompwd.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV4ZHFyc3diY2dra2Z0dm9tcHdkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI2MjIwOTQsImV4cCI6MjA3ODE5ODA5NH0.BzGPmvy5YpvPQ6His7SAoYlFnuWGQWHnBUXw5B7huWQ';

// Initialize Supabase client (SDK is loaded in HTML head)
let supabaseClient = null;

function initSupabase() {
    // Check if Supabase SDK is available (loaded via script tag in HTML)
    // The SDK can be available as window.supabase or just supabase
    const supabaseLib = window.supabase || (typeof supabase !== 'undefined' ? supabase : null);
    
    if (supabaseLib && typeof supabaseLib.createClient === 'function') {
        supabaseClient = supabaseLib.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
        return true;
    }
    return false;
}

// Sort data by column
function sortData(data, column, direction) {
    const sorted = [...data];
    
    sorted.sort((a, b) => {
        let aVal = a[column];
        let bVal = b[column];
        
        // Handle numeric values (remove $ and parse)
        if (column.includes('price') || column.includes('count') || column === 'piece_count') {
            // Remove $ and parse as float
            aVal = parseFloat(aVal?.replace(/[^0-9.-]/g, '') || 0);
            bVal = parseFloat(bVal?.replace(/[^0-9.-]/g, '') || 0);
        } else if (column === 'item_number') {
            // Parse as integer
            aVal = parseInt(aVal || 0);
            bVal = parseInt(bVal || 0);
        } else {
            // String comparison
            aVal = (aVal || '').toString().toLowerCase();
            bVal = (bVal || '').toString().toLowerCase();
        }
        
        if (aVal < bVal) return direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return direction === 'asc' ? 1 : -1;
        return 0;
    });
    
    return sorted;
}

// Format currency values
function formatCurrency(value) {
    if (!value || value === '') return 'N/A';
    return value;
}

// Create table HTML with sorting
function createTable(data, sortColumn = null, sortDirection = 'asc') {
    if (!data || data.length === 0) {
        return '<p>No data available</p>';
    }
    
    const headers = Object.keys(data[0]);
    let html = '<table><thead><tr>';
    
    // Create header row with clickable sortable headers
    headers.forEach(header => {
        const displayName = header.replace('_', ' ').toUpperCase();
        let sortIndicator = '';
        
        if (sortColumn === header) {
            sortIndicator = sortDirection === 'asc' ? ' ↑' : ' ↓';
        }
        
        html += `<th class="sortable" data-column="${header}">${displayName}${sortIndicator}</th>`;
    });
    html += '</tr></thead><tbody>';
    
    // Create data rows (limit to top 50)
    const top50 = data.slice(0, 50);
    top50.forEach(row => {
        html += '<tr>';
        headers.forEach(header => {
            let value = row[header];
            if (header === 'url' && value) {
                value = `<a href="${value}" target="_blank" rel="noopener">View Product</a>`;
            } else if (header.includes('price')) {
                value = formatCurrency(value);
            }
            html += `<td>${value}</td>`;
        });
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    return html;
}

// Global state for sorting
let currentData = [];
let currentSortColumn = 'msrp'; // Default sort column
let currentSortDirection = 'asc'; // Default sort direction

// Render table with current sort
function renderTable() {
    const container = document.getElementById('data-container');
    const sortedData = sortData(currentData, currentSortColumn, currentSortDirection);
    container.innerHTML = createTable(sortedData, currentSortColumn, currentSortDirection);
    
    // Add click handlers to sortable headers
    const sortableHeaders = container.querySelectorAll('th.sortable');
    sortableHeaders.forEach(header => {
        header.addEventListener('click', () => {
            const column = header.getAttribute('data-column');
            
            if (currentSortColumn === column) {
                // Toggle direction if same column
                currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                // New column, start with ascending
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
        // Initialize Supabase if not already done
        if (!supabaseClient) {
            if (!initSupabase()) {
                throw new Error('Supabase SDK not loaded. Please check script tag in HTML.');
            }
        }

        const tableName = 'lego_sets_overview_unprocessed';
        console.log(`Querying Supabase table: ${tableName}`);
        
        const { data, error } = await supabaseClient
            .from(tableName) 
            .select('*')  
            .order('msrp', { ascending: true });
    
        // Log the full response for debugging
        console.log('Supabase response:', { data, error, dataLength: data?.length });
    
        if (error) {
            console.error('Supabase error details:', error);
            throw new Error(`Supabase error: ${error.message} (Code: ${error.code || 'unknown'})`);
        }
        
        if (!data) {
            throw new Error(`No data returned from table "${tableName}". Check if the table exists.`);
        }
        
        if (!data.length) {
            throw new Error(`Table "${tableName}" exists but is empty. No rows found.`);
        }
    
        console.log(`Successfully loaded ${data.length} rows from ${tableName}`);
        currentData = data;
    
        renderTable();
    
    } catch (error) {
        console.error('Error loading data:', error);
        container.innerHTML = `<p>Error loading data: ${error.message}</p>`;
    }

}

// Load data when the page loads (wait for Supabase SDK to be ready)
document.addEventListener('DOMContentLoaded', () => {
    // Wait for Supabase to be ready
    function waitForSupabase() {
        if (window.supabaseReady || typeof window.supabase !== 'undefined') {
            loadData();
        } else {
            // Retry after a short delay (max 2 seconds)
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

