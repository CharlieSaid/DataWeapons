/**
 * Simple page view tracking using Supabase
 * Tracks page visits without collecting personally identifiable information
 */

// Supabase configuration (using the same as other scripts)
const SUPABASE_URL = 'https://uxdqrswbcgkkftvompwd.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV4ZHFyc3diY2dra2Z0dm9tcHdkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI2MjIwOTQsImV4cCI6MjA3ODE5ODA5NH0.BzGPmvy5YpvPQ6His7SAoYlFnuWGQWHnBUXw5B7huWQ';

// Generate or retrieve session ID from localStorage
function getSessionId() {
    let sessionId = localStorage.getItem('analytics_session_id');
    if (!sessionId) {
        // Generate a simple session ID (not cryptographically secure, but good enough for analytics)
        sessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('analytics_session_id', sessionId);
        // Session expires after 30 minutes of inactivity
        localStorage.setItem('analytics_session_expiry', Date.now() + (30 * 60 * 1000));
    } else {
        // Check if session has expired
        const expiry = localStorage.getItem('analytics_session_expiry');
        if (expiry && Date.now() > parseInt(expiry)) {
            // Generate new session
            sessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('analytics_session_id', sessionId);
            localStorage.setItem('analytics_session_expiry', Date.now() + (30 * 60 * 1000));
        } else {
            // Update expiry on activity
            localStorage.setItem('analytics_session_expiry', Date.now() + (30 * 60 * 1000));
        }
    }
    return sessionId;
}

// Get page name from current URL
function getPageName() {
    const path = window.location.pathname;
    const filename = path.split('/').pop() || 'index.html';
    return filename;
}

// Track a page view
async function trackPageView() {
    try {
        // Initialize Supabase client
        const supabaseLib = window.supabase || (typeof supabase !== 'undefined' ? supabase : null);
        
        if (!supabaseLib || typeof supabaseLib.createClient !== 'function') {
            console.warn('Supabase SDK not available for analytics');
            return;
        }
        
        const supabaseClient = supabaseLib.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
        
        // Collect page view data
        const pageViewData = {
            page_name: getPageName(),
            page_path: window.location.pathname,
            user_agent: navigator.userAgent,
            referrer: document.referrer || null,
            session_id: getSessionId()
        };
        
        // Insert page view (fire and forget - don't block page load)
        supabaseClient
            .from('page_views')
            .insert([pageViewData])
            .then(({ error }) => {
                if (error) {
                    console.warn('Failed to track page view:', error);
                }
            })
            .catch((error) => {
                // Silently fail - don't interrupt user experience
                console.warn('Analytics error (non-critical):', error);
            });
            
    } catch (error) {
        // Silently fail - analytics should never break the site
        console.warn('Analytics error (non-critical):', error);
    }
}

// Track page view when script loads
// Use requestIdleCallback if available for better performance, otherwise use setTimeout
if (window.requestIdleCallback) {
    requestIdleCallback(trackPageView, { timeout: 2000 });
} else {
    setTimeout(trackPageView, 100);
}

// Also track when page becomes visible (for SPA navigation or tab switching)
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        // Small delay to avoid duplicate tracking on initial load
        setTimeout(() => {
            trackPageView();
        }, 500);
    }
});

