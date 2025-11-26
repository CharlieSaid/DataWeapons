import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import Stripe from 'https://esm.sh/stripe@14.21.0?target=deno'

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
    // Get the authorization header
    const authHeader = req.headers.get('authorization')
    if (!authHeader) {
      return new Response(
        JSON.stringify({ error: 'Missing authorization header' }),
        { 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401
        }
      )
    }

    // Initialize Supabase client with service role key (for admin operations)
    const SUPABASE_URL = Deno.env.get('SUPABASE_URL') || ''
    const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') || ''
    const STRIPE_SECRET_KEY = Deno.env.get('STRIPE_SECRET_KEY') || ''

    if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY || !STRIPE_SECRET_KEY) {
      console.error('Missing required environment variables')
      return new Response(
        JSON.stringify({ error: 'Server configuration error' }),
        { 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 500
        }
      )
    }

    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    const stripe = new Stripe(STRIPE_SECRET_KEY, {
      apiVersion: '2023-10-16',
      httpClient: Stripe.createFetchHttpClient(),
    })

    // Verify the user's JWT token and get their user ID
    const token = authHeader.replace('Bearer ', '')
    const { data: { user }, error: authError } = await supabase.auth.getUser(token)

    if (authError || !user) {
      console.error('Authentication error:', authError)
      return new Response(
        JSON.stringify({ error: 'Invalid or expired token' }),
        { 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 401
        }
      )
    }

    const userId = user.id
    const userEmail = user.email

    console.log(`Account deletion requested for user: ${userId} (${userEmail})`)

    // Get user's subscription info from database
    const { data: subscriptionData, error: subError } = await supabase
      .from('subscriptions')
      .select('stripe_subscription_id, stripe_customer_id')
      .eq('user_id', userId)
      .single()

    if (subError && subError.code !== 'PGRST116') { // PGRST116 = no rows returned
      console.error('Error fetching subscription:', subError)
      // Continue with deletion even if subscription lookup fails
    }

    // Cancel Stripe subscription if it exists
    if (subscriptionData?.stripe_subscription_id) {
      try {
        console.log(`Cancelling Stripe subscription: ${subscriptionData.stripe_subscription_id}`)
        await stripe.subscriptions.cancel(subscriptionData.stripe_subscription_id)
        console.log(`✅ Stripe subscription cancelled: ${subscriptionData.stripe_subscription_id}`)
      } catch (stripeError) {
        console.error('Error cancelling Stripe subscription:', stripeError)
        // Continue with deletion even if Stripe cancellation fails
        // (subscription might already be cancelled or deleted)
      }
    } else {
      console.log('No active subscription found for user')
    }

    // Delete subscription record from database
    if (subscriptionData) {
      const { error: deleteSubError } = await supabase
        .from('subscriptions')
        .delete()
        .eq('user_id', userId)

      if (deleteSubError) {
        console.error('Error deleting subscription record:', deleteSubError)
        // Continue with other deletions
      } else {
        console.log('✅ Subscription record deleted from database')
      }
    }

    // Delete user profile from database
    const { error: deleteProfileError } = await supabase
      .from('user_profiles')
      .delete()
      .eq('id', userId)

    if (deleteProfileError) {
      console.error('Error deleting user profile:', deleteProfileError)
      // Continue with user deletion
    } else {
      console.log('✅ User profile deleted from database')
    }

    // Delete user from Supabase auth (this is the main deletion)
    const { error: deleteUserError } = await supabase.auth.admin.deleteUser(userId)

    if (deleteUserError) {
      console.error('Error deleting user from auth:', deleteUserError)
      return new Response(
        JSON.stringify({ 
          error: 'Failed to delete user account',
          details: deleteUserError.message
        }),
        { 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 500
        }
      )
    }

    console.log(`✅✅✅ Account successfully deleted for user: ${userId} (${userEmail})`)

    return new Response(
      JSON.stringify({ 
        success: true,
        message: 'Account deleted successfully'
      }),
      { 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200
      }
    )

  } catch (error) {
    console.error('Unexpected error during account deletion:', error)
    const errorMessage = error instanceof Error ? error.message : String(error)
    
    return new Response(
      JSON.stringify({ 
        error: 'An unexpected error occurred',
        details: errorMessage
      }),
      { 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 500
      }
    )
  }
})

