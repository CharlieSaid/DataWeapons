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
    // Log request method and headers for debugging
    console.log('Request method:', req.method)
    console.log('Content-Type header:', req.headers.get('content-type'))
    
    // Get Stripe secret key from environment
    const STRIPE_SECRET_KEY = Deno.env.get('STRIPE_SECRET_KEY')
    
    // Log for debugging (don't log the full key, just check if it exists)
    console.log('STRIPE_SECRET_KEY exists:', !!STRIPE_SECRET_KEY)
    console.log('STRIPE_SECRET_KEY starts with sk_:', STRIPE_SECRET_KEY?.startsWith('sk_'))
    
    if (!STRIPE_SECRET_KEY) {
      throw new Error('STRIPE_SECRET_KEY is not set. Please add it in function settings.')
    }

    const stripe = new Stripe(STRIPE_SECRET_KEY, {
      apiVersion: '2023-10-16',
      httpClient: Stripe.createFetchHttpClient(),
    })

    // Get request body
    let requestBody
    try {
      // Parse JSON body
      requestBody = await req.json()
      
      console.log('Request body received:', JSON.stringify(requestBody))
      console.log('Request body type:', typeof requestBody)
      console.log('Request body keys:', Object.keys(requestBody || {}))
      console.log('priceId:', requestBody?.priceId, '(type:', typeof requestBody?.priceId, ')')
      console.log('userEmail:', requestBody?.userEmail, '(type:', typeof requestBody?.userEmail, ')')
      console.log('userId:', requestBody?.userId, '(type:', typeof requestBody?.userId, ')')
      console.log('userPassword:', requestBody?.userPassword ? '***' + requestBody.userPassword.slice(-2) : 'MISSING', '(type:', typeof requestBody?.userPassword, ', length:', requestBody?.userPassword?.length || 0, ')')
    } catch (parseError) {
      console.error('Error parsing request body:', parseError)
      console.error('Parse error details:', {
        message: parseError.message,
        name: parseError.name
      })
      throw new Error(`Invalid request body format: ${parseError.message}`)
    }

    if (!requestBody || typeof requestBody !== 'object') {
      throw new Error(`Request body is invalid: ${typeof requestBody}`)
    }

    const { priceId, userId, userEmail, userPassword } = requestBody

    // Check if fields are missing or empty
    if (!priceId) {
      throw new Error(`Missing or empty priceId field. Received: ${JSON.stringify(requestBody)}`)
    }
    
    if (!userEmail) {
      throw new Error(`Missing or empty userEmail field. Received: ${JSON.stringify(requestBody)}`)
    }
    
    if (!userPassword) {
      throw new Error(`Missing or empty userPassword field. Password is required for account creation.`)
    }
    
    // userId is optional - if not provided, webhook will create user account with the provided password

    // Get the origin from request headers (your website URL)
    const origin = req.headers.get('origin') || req.headers.get('referer')?.split('/').slice(0, 3).join('/') || 'http://localhost:5500'

    // Create Stripe Checkout Session
    const session = await stripe.checkout.sessions.create({
      customer_email: userEmail,
      payment_method_types: ['card'],
      line_items: [
        {
          price: priceId,
          quantity: 1,
        },
      ],
      mode: 'subscription',
      success_url: `${origin}/website_files/advanced.html?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${origin}/website_files/advanced.html?canceled=true`,
      metadata: {
        userId: userId || '', // Will be empty if user not logged in - webhook will handle
        userEmail: userEmail, // Store email in metadata for webhook
        userPassword: userPassword, // Store password in metadata for webhook (will be used to create account)
      },
    })

    console.log('Stripe session created:', session.id)
    console.log('Session metadata keys:', Object.keys(session.metadata || {}))
    console.log('Session metadata userEmail:', session.metadata?.userEmail)
    console.log('Session metadata hasPassword:', !!session.metadata?.userPassword)

    return new Response(
      JSON.stringify({ id: session.id }),
      { 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200
      }
    )
  } catch (error) {
    console.error('Error creating checkout session:', error)
    const errorMessage = error instanceof Error ? error.message : String(error)
    const errorStack = error instanceof Error ? error.stack : undefined
    
    // Log full error details for debugging
    console.error('Full error details:', {
      message: errorMessage,
      stack: errorStack,
      name: error instanceof Error ? error.name : undefined
    })
    
    return new Response(
      JSON.stringify({ 
        error: errorMessage,
        details: errorStack ? 'Check function logs for details' : undefined
      }),
      { 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 500
      }
    )
  }
})

