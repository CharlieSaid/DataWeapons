/**
 * Supabase Edge Function to trigger scraper execution.
 * 
 * Note: This function cannot directly run Python scrapers with Playwright.
 * Instead, it can:
 * 1. Trigger an external service (e.g., GitHub Actions, external API)
 * 2. Or be used with pg_cron to schedule database operations
 * 
 * For actual scraper execution, use:
 * - A cron job on a server
 * - GitHub Actions scheduled workflow
 * - A cloud function that can run Python/Playwright
 */

import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    // Get environment variables
    const SUPABASE_URL = Deno.env.get('SUPABASE_URL')
    const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')
    const SCRAPER_WEBHOOK_URL = Deno.env.get('SCRAPER_WEBHOOK_URL') // Optional: URL to trigger external scraper service

    if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
      throw new Error('Missing Supabase configuration')
    }

    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    // Log the scraper run request
    const { data: logData, error: logError } = await supabase
      .from('scraper_runs')
      .insert({
        run_type: 'scheduled',
        status: 'triggered',
        triggered_at: new Date().toISOString(),
      })
      .select()
      .single()

    if (logError) {
      console.warn('Could not log scraper run (table may not exist):', logError)
    }

    // If a webhook URL is configured, trigger external scraper service
    if (SCRAPER_WEBHOOK_URL) {
      try {
        const webhookResponse = await fetch(SCRAPER_WEBHOOK_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            triggered_by: 'supabase_edge_function',
            timestamp: new Date().toISOString(),
          }),
        })

        if (!webhookResponse.ok) {
          throw new Error(`Webhook returned status ${webhookResponse.status}`)
        }

        console.log('✅ External scraper service triggered successfully')
      } catch (webhookError) {
        console.error('❌ Error triggering external scraper:', webhookError)
        throw webhookError
      }
    } else {
      console.log('⚠️  SCRAPER_WEBHOOK_URL not configured. Scrapers must be run externally.')
    }

    return new Response(
      JSON.stringify({
        success: true,
        message: 'Scraper run triggered',
        timestamp: new Date().toISOString(),
        webhook_triggered: !!SCRAPER_WEBHOOK_URL,
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200,
      }
    )

  } catch (error) {
    console.error('Error in run-scrapers function:', error)
    return new Response(
      JSON.stringify({
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date().toISOString(),
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 500,
      }
    )
  }
})

