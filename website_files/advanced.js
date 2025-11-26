// Advanced page - Premium subscription access control
// Supabase configuration
const SUPABASE_URL = 'https://uxdqrswbcgkkftvompwd.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV4ZHFyc3diY2dra2Z0dm9tcHdkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI2MjIwOTQsImV4cCI6MjA3ODE5ODA5NH0.BzGPmvy5YpvPQ6His7SAoYlFnuWGQWHnBUXw5B7huWQ';

// Stripe configuration
const STRIPE_PUBLISHABLE_KEY = 'pk_test_51SSNqWBsxzyv4brS9kVt71Hdng6jnEEUHMX6t9u2I3O1mEuapNjUHGOZnKDuXczOpc4H3Sa1Q6BBoujn6MzqFGea00FQPQDKMg'; 
const STRIPE_PRICE_ID = 'price_1SSjwTBsxzyv4brSwgAQiwko'; 

// Initialize clients
let supabaseClient = null;
let stripe = null;

// Global state
let currentUser = null;
let subscriptionStatus = null;
let currentData = [];
let currentSortColumn = 'msrp';
let currentSortDirection = 'asc';

// Initialize Supabase
function initSupabase() {
    const supabaseLib = window.supabase || (typeof supabase !== 'undefined' ? supabase : null);
    
    if (supabaseLib && typeof supabaseLib.createClient === 'function') {
        supabaseClient = supabaseLib.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
        return true;
    }
    return false;
}

// Initialize Stripe
function initStripe() {
    if (typeof Stripe !== 'undefined') {
        stripe = Stripe(STRIPE_PUBLISHABLE_KEY);
        return true;
    }
    return false;
}

// Check if user is authenticated
async function checkAuth() {
    if (!supabaseClient) return null;
    
    const { data: { user }, error } = await supabaseClient.auth.getUser();
    if (error || !user) return null;
    return user;
}

// Check subscription status by userId
async function checkSubscription(userId) {
    if (!supabaseClient || !userId) {
        return false;
    }
    
    try {
        // Check subscriptions table
        const { data: subscriptionData, error: subError } = await supabaseClient
            .from('subscriptions')
            .select('status, stripe_subscription_id')
            .eq('user_id', userId)
            .eq('status', 'active')
            .maybeSingle();
        
        if (subscriptionData && subscriptionData.status === 'active') {
            return true;
        }
        
        // Also check user_profiles table
        const { data: profile, error: profileError } = await supabaseClient
            .from('user_profiles')
            .select('subscription_status')
            .eq('id', userId)
            .maybeSingle();
        
        if (profile && profile.subscription_status === 'active') {
            return true;
        }
        
        return false;
    } catch (error) {
        console.error('Error checking subscription:', error);
        return false;
    }
}

// Load premium data
async function loadPremiumData() {
    const container = document.getElementById('data-container');
    
    try {
        const tableName = 'pov';
        console.log(`Loading premium data from: ${tableName}`);
        
        const { data, error } = await supabaseClient
            .from(tableName)
            .select('*')
            .order('msrp', { ascending: true });
        
        if (error) {
            throw new Error(`Supabase error: ${error.message}`);
        }
        
        if (!data || !data.length) {
            throw new Error('No premium data available');
        }
        
        console.log(`Loaded ${data.length} premium rows`);
        currentData = data;
        renderTable();
        
    } catch (error) {
        console.error('Error loading premium data:', error);
        container.innerHTML = `<p>Error loading premium data: ${error.message}</p>`;
    }
}

// Sort data by column
function sortData(data, column, direction) {
    const sorted = [...data];
    
    sorted.sort((a, b) => {
        let aVal = a[column];
        let bVal = b[column];
        
        if (column.includes('price') || column.includes('count') || column === 'piece_count') {
            aVal = parseFloat(aVal?.toString().replace(/[^0-9.-]/g, '') || 0);
            bVal = parseFloat(bVal?.toString().replace(/[^0-9.-]/g, '') || 0);
        } else if (column === 'item_number') {
            aVal = parseInt(aVal || 0);
            bVal = parseInt(bVal || 0);
        } else {
            aVal = (aVal || '').toString().toLowerCase();
            bVal = (bVal || '').toString().toLowerCase();
        }
        
        if (aVal < bVal) return direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return direction === 'asc' ? 1 : -1;
        return 0;
    });
    
    return sorted;
}

// Create table HTML with sorting
function createTable(data, sortColumn = null, sortDirection = 'asc') {
    if (!data || data.length === 0) {
        return '<p>No data available</p>';
    }
    
    const headers = Object.keys(data[0]);
    let html = '<table><thead><tr>';
    
    headers.forEach(header => {
        const displayName = header.replace('_', ' ').toUpperCase();
        let sortIndicator = '';
        
        if (sortColumn === header) {
            sortIndicator = sortDirection === 'asc' ? ' ↑' : ' ↓';
        }
        
        html += `<th class="sortable" data-column="${header}">${displayName}${sortIndicator}</th>`;
    });
    html += '</tr></thead><tbody>';
    
    data.forEach(row => {
        html += '<tr>';
        headers.forEach(header => {
            let value = row[header];
            if (header === 'url' && value) {
                value = `<a href="${value}" target="_blank" rel="noopener">View Product</a>`;
            } else if (header.includes('price')) {
                value = value || 'N/A';
            }
            html += `<td>${value}</td>`;
        });
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    return html;
}

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
                currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                currentSortColumn = column;
                currentSortDirection = 'asc';
            }
            
            renderTable();
        });
    });
}

// Handle login
async function handleLogin(email, password) {
    if (!supabaseClient) {
        throw new Error('Supabase not initialized');
    }
    
    const { data, error } = await supabaseClient.auth.signInWithPassword({
        email: email,
        password: password
    });
    
    if (error) {
        throw error;
    }
    
    return data.user;
}

// Handle subscribe - collect email/password and proceed to Stripe
async function handleSubscribe(email, password) {
    if (!stripe) {
        throw new Error('Stripe not initialized');
    }
    
    // Store credentials temporarily for after checkout
    sessionStorage.setItem('pending_subscription', JSON.stringify({
        email: email,
        password: password,
        timestamp: Date.now()
    }));
    
    // Call edge function to create checkout session
    const { data: session, error } = await supabaseClient.functions.invoke('create-checkout-session', {
        body: {
            priceId: STRIPE_PRICE_ID,
            userId: null, // Will be created by webhook
            userEmail: email,
            userPassword: password // Pass password to webhook via metadata
        }
    });
    
    if (error) {
        throw new Error(`Failed to create checkout session: ${error.message || JSON.stringify(error)}`);
    }
    
    if (!session || !session.id) {
        throw new Error('No session ID returned from server');
    }
    
    // Redirect to Stripe Checkout
    const { error: redirectError } = await stripe.redirectToCheckout({
        sessionId: session.id
    });
    
    if (redirectError) {
        throw redirectError;
    }
}

// Handle logout
async function handleLogout() {
    if (!supabaseClient) return;
    
    const { error } = await supabaseClient.auth.signOut();
    if (error) {
        console.error('Error logging out:', error);
        alert('Error logging out: ' + error.message);
    } else {
        currentUser = null;
        subscriptionStatus = false;
        sessionStorage.removeItem('pending_subscription');
        updateUI();
    }
}

// Handle delete account
async function handleDeleteAccount() {
    if (!supabaseClient || !currentUser) return;
    
    const confirmDelete = confirm('Are you sure you want to delete your account? This action cannot be undone. This will cancel your subscription and delete all your data.');
    if (!confirmDelete) return;
    
    try {
        // Show loading state
        const deleteBtn = document.getElementById('delete-account-btn');
        const originalText = deleteBtn.textContent;
        deleteBtn.disabled = true;
        deleteBtn.textContent = 'Deleting...';
        
        // Call the delete-account Edge Function
        const { data, error } = await supabaseClient.functions.invoke('delete-account', {
            method: 'POST'
        });
        
        if (error) {
            throw new Error(error.message || 'Failed to delete account');
        }
        
        if (data?.error) {
            throw new Error(data.error);
        }
        
        // Success - account deleted
        alert('Your account has been successfully deleted. Your subscription has been cancelled and all your data has been removed.');
        
        // Sign out and redirect
        await handleLogout();
        window.location.href = 'advanced.html';
        
    } catch (error) {
        console.error('Error deleting account:', error);
        alert(`Failed to delete account: ${error.message || 'Unknown error'}. Please try again or contact support.`);
        
        // Restore button state
        const deleteBtn = document.getElementById('delete-account-btn');
        deleteBtn.disabled = false;
        deleteBtn.textContent = 'Delete Account';
    }
}

// Update UI based on auth and subscription status
async function updateUI() {
    const loading = document.getElementById('loading');
    const premiumSignup = document.getElementById('premium-signup');
    const premiumContent = document.getElementById('premium-content');
    const accountMenu = document.getElementById('account-menu');
    const accountEmail = document.getElementById('account-email');
    
    loading.style.display = 'none';
    
    if (subscriptionStatus && currentUser) {
        // User is subscribed and logged in - show premium content
        premiumSignup.style.display = 'none';
        premiumContent.style.display = 'block';
        accountMenu.style.display = 'flex';
        accountEmail.textContent = currentUser.email;
        loadPremiumData();
    } else {
        // User is not subscribed - show signup
        premiumSignup.style.display = 'block';
        premiumContent.style.display = 'none';
        accountMenu.style.display = 'none';
    }
}

// Initialize page
async function init() {
    function waitForSupabase() {
        if (window.supabaseReady || typeof window.supabase !== 'undefined') {
            if (!initSupabase()) {
                console.error('Failed to initialize Supabase');
                document.getElementById('loading').innerHTML = 
                    '<p>Error: Failed to initialize Supabase. Please refresh the page.</p>';
                return;
            }
            
            if (!initStripe()) {
                console.warn('Stripe not loaded - subscription features may not work');
            }
            
            checkAccess();
        } else {
            setTimeout(waitForSupabase, 50);
        }
    }
    
    waitForSupabase();
}

// Check user access
async function checkAccess() {
    try {
        currentUser = await checkAuth();
        
        if (currentUser) {
            subscriptionStatus = await checkSubscription(currentUser.id);
        } else {
            subscriptionStatus = false;
        }
        
        updateUI();
    } catch (error) {
        console.error('Error checking access:', error);
        document.getElementById('loading').innerHTML = 
            `<p>Error checking access: ${error.message}</p>`;
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    init();
    
    // Modal elements
    const loginModal = document.getElementById('login-modal');
    const subscribeModal = document.getElementById('subscribe-modal');
    const loginForm = document.getElementById('login-form');
    const subscribeForm = document.getElementById('subscribe-form');
    
    // Open login modal
    document.getElementById('login-link').addEventListener('click', (e) => {
        e.preventDefault();
        loginModal.style.display = 'block';
        document.getElementById('login-email').focus();
    });
    
    // Close login modal
    document.getElementById('close-login-modal').addEventListener('click', () => {
        loginModal.style.display = 'none';
    });
    
    // Close subscribe modal
    document.getElementById('close-subscribe-modal').addEventListener('click', () => {
        subscribeModal.style.display = 'none';
    });
    
    // Close modals when clicking outside
    window.addEventListener('click', (e) => {
        if (e.target === loginModal) {
            loginModal.style.display = 'none';
        }
        if (e.target === subscribeModal) {
            subscribeModal.style.display = 'none';
        }
    });
    
    // Handle login form submission
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;
        const errorDiv = document.getElementById('login-error');
        
        errorDiv.style.display = 'none';
        const submitBtn = loginForm.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Logging in...';
        
        try {
            const user = await handleLogin(email, password);
            currentUser = user;
            subscriptionStatus = await checkSubscription(user.id);
            
            if (subscriptionStatus) {
                loginModal.style.display = 'none';
                updateUI();
            } else {
                errorDiv.textContent = 'This account does not have an active subscription.';
                errorDiv.style.display = 'block';
            }
        } catch (error) {
            errorDiv.textContent = error.message || 'Invalid email or password';
            errorDiv.style.display = 'block';
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Log In';
        }
    });
    
    // Handle subscribe button
    document.getElementById('subscribe-btn').addEventListener('click', () => {
        subscribeModal.style.display = 'block';
        document.getElementById('subscribe-email').focus();
    });
    
    // Handle subscribe form submission
    subscribeForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('subscribe-email').value;
        const password = document.getElementById('subscribe-password').value;
        const errorDiv = document.getElementById('subscribe-error');
        
        if (password.length < 6) {
            errorDiv.textContent = 'Password must be at least 6 characters';
            errorDiv.style.display = 'block';
            return;
        }
        
        errorDiv.style.display = 'none';
        const submitBtn = subscribeForm.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Processing...';
        
        try {
            await handleSubscribe(email, password);
            // User will be redirected to Stripe
        } catch (error) {
            errorDiv.textContent = error.message || 'Failed to start checkout';
            errorDiv.style.display = 'block';
            submitBtn.disabled = false;
            submitBtn.textContent = 'Continue to Payment';
        }
    });
    
    // Account menu toggle
    document.getElementById('account-icon').addEventListener('click', (e) => {
        e.stopPropagation();
        const dropdown = document.getElementById('account-dropdown');
        dropdown.classList.toggle('show');
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.account-menu')) {
            document.getElementById('account-dropdown').classList.remove('show');
        }
    });
    
    // Logout from menu
    document.getElementById('logout-menu-btn').addEventListener('click', handleLogout);
    
    // Delete account
    document.getElementById('delete-account-btn').addEventListener('click', handleDeleteAccount);
    
    // Handle checkout success redirect
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id');
    const canceled = urlParams.get('canceled');

    if (canceled === 'true') {
        alert('Checkout was canceled. You can try again anytime.');
        window.history.replaceState({}, document.title, window.location.pathname);
    } else if (sessionId) {
        // Checkout successful - wait for webhook, then auto-login
        handleCheckoutSuccess();
    }
});

// Handle successful checkout - auto-login user
async function handleCheckoutSuccess() {
    const loading = document.getElementById('loading');
    const premiumSignup = document.getElementById('premium-signup');
    loading.style.display = 'block';
    premiumSignup.style.display = 'none';
    loading.innerHTML = '<p>Processing your subscription... Please wait.</p>';
    
    // Get stored credentials
    const pendingData = sessionStorage.getItem('pending_subscription');
    if (!pendingData) {
        loading.innerHTML = '<p>Error: Subscription data not found. Please log in manually.</p>';
        return;
    }
    
    const { email, password } = JSON.parse(pendingData);
    
    // Wait for webhook to process (create user account)
    let retries = 0;
    const maxRetries = 10;
    
    const attemptAutoLogin = async () => {
        try {
            // Try to log in with the credentials
            const { data: signInData, error: signInError } = await supabaseClient.auth.signInWithPassword({
                email: email,
                password: password
            });
            
            if (!signInError && signInData.user) {
                // Successfully logged in!
                currentUser = signInData.user;
                subscriptionStatus = await checkSubscription(currentUser.id);
                
                if (subscriptionStatus) {
                    console.log('Auto-login successful!');
                    sessionStorage.removeItem('pending_subscription');
                    updateUI();
                    window.history.replaceState({}, document.title, window.location.pathname);
                    return;
                } else {
                    // User exists but subscription not found yet
                    if (retries < maxRetries) {
                        retries++;
                        setTimeout(attemptAutoLogin, 2000);
                    } else {
                        loading.innerHTML = '<p>Subscription is being processed. Please refresh the page in a moment.</p>';
                    }
                }
            } else {
                // Login failed - user might not be created yet
                if (retries < maxRetries) {
                    retries++;
                    console.log(`Auto-login attempt ${retries}/${maxRetries} - waiting for webhook...`);
                    console.log('Login error:', signInError);
                    if (signInError) {
                        console.log('Error message:', signInError.message);
                        console.log('Error code:', signInError.status);
                    }
                    setTimeout(attemptAutoLogin, 2000);
                } else {
                    console.error('Max retries reached. Login failed.');
                    console.error('Final error:', signInError);
                    loading.innerHTML = '<p>Account creation is taking longer than expected. Please check:<br>1. Supabase Edge Function logs for webhook errors<br>2. Stripe webhook logs<br>3. Try logging in manually in a few moments</p>';
                }
            }
        } catch (error) {
            console.error('Error during auto-login:', error);
            if (retries < maxRetries) {
                retries++;
                setTimeout(attemptAutoLogin, 2000);
            } else {
                loading.innerHTML = '<p>Error: ' + error.message + '</p>';
            }
        }
    };
    
    // Start attempting login after initial delay
    setTimeout(attemptAutoLogin, 3000);
}
