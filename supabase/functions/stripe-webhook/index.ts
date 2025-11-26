import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
// Use Stripe SDK (we'll handle webhook verification manually due to Deno crypto compatibility)
import Stripe from 'https://esm.sh/stripe@14.21.0?target=deno'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, stripe-signature',
}

serve(async (req) => {
  // CRITICAL: Log immediately when function is invoked
  console.log('=== WEBHOOK FUNCTION INVOKED ===')
  console.log('Timestamp:', new Date().toISOString())
  console.log('Request method:', req.method)
  console.log('Request URL:', req.url)
  
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    console.log('OPTIONS request - returning CORS headers')
    return new Response('ok', { headers: corsHeaders })
  }

  console.log('Webhook received request:', {
    method: req.method,
    hasSignature: !!req.headers.get('stripe-signature'),
    contentType: req.headers.get('content-type'),
    url: req.url
  })

  try {
    // Get environment variables
    const STRIPE_SECRET_KEY = Deno.env.get('STRIPE_SECRET_KEY')
    const STRIPE_WEBHOOK_SECRET = Deno.env.get('STRIPE_WEBHOOK_SECRET')
    const SUPABASE_URL = Deno.env.get('SUPABASE_URL')
    const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')

    console.log('Environment check:', {
      hasStripeKey: !!STRIPE_SECRET_KEY,
      hasWebhookSecret: !!STRIPE_WEBHOOK_SECRET,
      hasSupabaseUrl: !!SUPABASE_URL,
      hasServiceRoleKey: !!SUPABASE_SERVICE_ROLE_KEY
    })

    if (!STRIPE_SECRET_KEY || !STRIPE_WEBHOOK_SECRET) {
      throw new Error('Missing Stripe configuration')
    }

    if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
      throw new Error('Missing Supabase configuration')
    }

    const stripe = new Stripe(STRIPE_SECRET_KEY, {
      apiVersion: '2023-10-16',
      httpClient: Stripe.createFetchHttpClient(),
    })

    // Get the signature from headers
    const signature = req.headers.get('stripe-signature')
    if (!signature) {
      throw new Error('Missing stripe-signature header')
    }

    // Get the raw body
    const body = await req.text()

    // Verify the webhook signature using manual implementation (Deno-compatible)
    // Stripe SDK has issues with Deno's async crypto, so we implement it manually
    let event: Stripe.Event
    try {
      // Parse Stripe signature header format: t=timestamp,v1=signature1,v0=signature0
      const elements = signature.split(',')
      const timestamp = elements.find(e => e.startsWith('t='))?.split('=')[1]
      const signatures = elements
        .filter(e => e.startsWith('v1='))
        .map(e => e.split('=')[1])
      
      if (!timestamp || !signatures.length) {
        throw new Error('Invalid signature format')
      }
      
      // Create signed payload: timestamp + '.' + body
      const signedPayload = `${timestamp}.${body}`
      
      // Compute HMAC-SHA256 using Deno's crypto API
      const encoder = new TextEncoder()
      const keyData = encoder.encode(STRIPE_WEBHOOK_SECRET)
      
      const cryptoKey = await crypto.subtle.importKey(
        'raw',
        keyData,
        { name: 'HMAC', hash: 'SHA-256' },
        false,
        ['sign']
      )
      
      const signatureBuffer = await crypto.subtle.sign(
        'HMAC',
        cryptoKey,
        encoder.encode(signedPayload)
      )
      
      // Convert to hex string
      const computedSignature = Array.from(new Uint8Array(signatureBuffer))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('')
      
      // Verify at least one signature matches
      const isValid = signatures.some(sig => {
        // Use constant-time comparison to prevent timing attacks
        if (sig.length !== computedSignature.length) return false
        let match = 0
        for (let i = 0; i < sig.length; i++) {
          match |= sig.charCodeAt(i) ^ computedSignature.charCodeAt(i)
        }
        return match === 0
      })
      
      if (!isValid) {
        throw new Error('Invalid webhook signature - signatures do not match')
      }
      
      // Parse event JSON
      event = JSON.parse(body) as Stripe.Event
      console.log('✅ Webhook signature verified successfully (manual verification)')
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err)
      console.error('❌ Webhook signature verification failed:', errorMessage)
      console.error('Error stack:', err instanceof Error ? err.stack : 'No stack trace')
      
      return new Response(
        JSON.stringify({ 
          error: `Webhook Error: ${errorMessage}`,
          hint: 'Signature verification failed. Ensure webhook secret is correct and request is from Stripe.'
        }),
        { 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          status: 400
        }
      )
    }

    // Initialize Supabase client with service role key (bypasses RLS)
    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    console.log('Webhook event received:', {
      type: event.type,
      id: event.id,
      created: new Date(event.created * 1000).toISOString()
    })

    // Handle different event types
    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object as Stripe.Checkout.Session
        
        console.log('Checkout session metadata:', JSON.stringify(session.metadata, null, 2))
        console.log('Customer email:', session.customer_email)
        
        // Get subscription details
        const subscriptionId = session.subscription as string
        if (!subscriptionId) {
          console.error('No subscription ID in checkout session')
          break
        }

        const subscription = await stripe.subscriptions.retrieve(subscriptionId)
        let userId = session.metadata?.userId
        const userEmail = session.metadata?.userEmail || session.customer_email
        const userPassword = session.metadata?.userPassword // Password provided during checkout

        // Normalize userId - treat empty string as null
        if (userId === '' || userId === null || userId === undefined) {
          userId = null
        }

        console.log('Extracted values:', {
          userId: userId || 'null/empty',
          userEmail: userEmail || 'null',
          hasPassword: !!userPassword,
          passwordLength: userPassword?.length || 0,
          passwordPreview: userPassword ? userPassword.substring(0, 2) + '***' : 'MISSING'
        })

        // If no userId provided (null, empty string, or undefined), find or create user by email
        if (!userId && userEmail) {
          console.log(`No userId provided, finding/creating user for email: ${userEmail}`)
          
          // Try to find existing user by email
          const { data: existingUsers, error: findError } = await supabase.auth.admin.listUsers()
          
          if (findError) {
            console.error('Error listing users:', findError)
          } else if (existingUsers) {
            const existingUser = existingUsers.users.find(u => u.email === userEmail)
            if (existingUser) {
              userId = existingUser.id
              console.log(`Found existing user: ${userId}`)
              
              // IMPORTANT: Update existing user's password with the one from checkout
              // This ensures they can log in with the password they just provided
              if (userPassword && userPassword.trim() !== '') {
                console.log(`Updating password for existing user: ${userId}`)
                const { error: updateError } = await supabase.auth.admin.updateUserById(
                  userId,
                  { password: userPassword.trim() }
                )
                
                if (updateError) {
                  console.error('❌ Error updating existing user password:', updateError)
                  console.error('Update error details:', JSON.stringify(updateError, null, 2))
                  // Continue anyway - subscription will still be saved
                } else {
                  console.log(`✅ Successfully updated password for existing user: ${userId}`)
                }
              } else {
                console.warn(`⚠️ No password provided in metadata - cannot update existing user password`)
              }
            }
          }
          
          // If user doesn't exist, create one with the provided password
          if (!userId) {
            // Check if password is provided and valid
            if (!userPassword || userPassword.trim() === '') {
              console.error('❌ No password provided in metadata - cannot create user account')
              console.error('Session metadata keys:', Object.keys(session.metadata || {}))
              console.error('Full session metadata:', JSON.stringify(session.metadata, null, 2))
              // Still save subscription with customer_id for later linking
              const { error: subError } = await supabase.from('subscriptions').upsert({
                stripe_subscription_id: subscription.id,
                stripe_customer_id: subscription.customer as string,
                status: subscription.status,
                current_period_start: new Date(subscription.current_period_start * 1000).toISOString(),
                current_period_end: new Date(subscription.current_period_end * 1000).toISOString(),
              }, { onConflict: 'stripe_subscription_id' })
              
              if (subError) {
                console.error('❌ Error saving subscription without user:', subError)
                console.error('Subscription error details:', JSON.stringify(subError, null, 2))
              } else {
                console.log('✅ Subscription saved without user_id (no password provided)')
                console.log('⚠️ WARNING: Password was missing from metadata - user account not created')
              }
              // Return success so Stripe doesn't retry, but log the issue
              return new Response(
                JSON.stringify({ 
                  received: true,
                  warning: 'Subscription saved but password missing - user not created'
                }),
                {
                  headers: { ...corsHeaders, 'Content-Type': 'application/json' },
                  status: 200
                }
              )
            }
            
            // Validate password length (Supabase requires at least 6 characters)
            if (userPassword.length < 6) {
              console.error(`❌ Password too short (${userPassword.length} chars). Minimum 6 characters required.`)
              // Still try to create user - Supabase will reject if too short
            }
            
            console.log(`Creating new user account for: ${userEmail} with password length: ${userPassword.length}`)
            console.log(`Password preview: ${userPassword.substring(0, 2)}*** (first 2 chars)`)
            
            const { data: newUser, error: createError } = await supabase.auth.admin.createUser({
              email: userEmail,
              password: userPassword.trim(), // Trim whitespace and use the password provided during checkout
              email_confirm: true, // Auto-confirm email so they can log in immediately
              user_metadata: {
                created_via: 'stripe_subscription',
                stripe_customer_id: subscription.customer as string
              }
            })
            
            if (createError) {
              console.error('❌ Error creating user:', createError)
              console.error('Create error details:', JSON.stringify(createError, null, 2))
              // Don't break here - let it fall through to save subscription without user_id
              userId = null
            } else if (newUser?.user) {
              userId = newUser.user.id
              console.log(`✅ Successfully created new user: ${userId} for email: ${userEmail}`)
            } else {
              console.error('❌ User creation returned no user data:', newUser)
              userId = null
            }
          }
        }

        // Final check - if we still don't have a userId, save subscription without it
        if (!userId) {
          console.error('❌ Could not determine or create userId')
          console.error('Attempting to save subscription without user_id for later linking')
          console.error('This means user account creation failed - check logs above for errors')
          
          // Still save subscription with customer_id for later linking
          const { data: subData, error: subError } = await supabase.from('subscriptions').upsert({
            stripe_subscription_id: subscription.id,
            stripe_customer_id: subscription.customer as string,
            status: subscription.status,
            current_period_start: new Date(subscription.current_period_start * 1000).toISOString(),
            current_period_end: new Date(subscription.current_period_end * 1000).toISOString(),
          }, { onConflict: 'stripe_subscription_id' }).select()
          
          if (subError) {
            console.error('❌ Error saving subscription without user:', subError)
            console.error('Subscription error details:', JSON.stringify(subError, null, 2))
            // Don't break - let it continue to return success so Stripe doesn't retry
          } else {
            console.log('✅ Subscription saved without user_id (user creation failed):', subData)
            console.log('⚠️ WARNING: User must be created manually or subscription linked later')
          }
          // Don't break - continue to return success response
          return new Response(
            JSON.stringify({ 
              received: true,
              warning: 'Subscription saved but user account creation failed',
              customer_email: userEmail
            }),
            {
              headers: { ...corsHeaders, 'Content-Type': 'application/json' },
              status: 200
            }
          )
        }

        console.log(`Creating subscription for user: ${userId}`)

        // Create or update subscription record
        const { data: subscriptionData, error: subError } = await supabase
          .from('subscriptions')
          .upsert({
            user_id: userId,
            stripe_subscription_id: subscription.id,
            stripe_customer_id: subscription.customer as string,
            status: subscription.status,
            current_period_start: new Date(subscription.current_period_start * 1000).toISOString(),
            current_period_end: new Date(subscription.current_period_end * 1000).toISOString(),
          }, {
            onConflict: 'stripe_subscription_id'
          })
          .select()

        if (subError) {
          console.error('❌ Error saving subscription:', subError)
          console.error('Subscription error details:', JSON.stringify(subError, null, 2))
          throw subError
        }

        console.log(`✅ Subscription saved:`, JSON.stringify(subscriptionData, null, 2))

        // Update user profile
        const { data: profileData, error: profileError } = await supabase
          .from('user_profiles')
          .upsert({
            id: userId,
            email: session.customer_email || userEmail,
            stripe_customer_id: subscription.customer as string,
            subscription_status: subscription.status === 'active' ? 'active' : 'inactive',
          }, {
            onConflict: 'id'
          })
          .select()

        if (profileError) {
          console.error('❌ Error updating user profile:', profileError)
          console.error('Profile error details:', JSON.stringify(profileError, null, 2))
          // Don't throw - subscription was saved, profile update is less critical
        } else {
          console.log(`✅ User profile updated:`, JSON.stringify(profileData, null, 2))
        }

        console.log(`✅✅✅ Subscription created successfully for user: ${userId} (${userEmail})`)
        break
      }

      case 'customer.subscription.created': {
        // Handle subscription.created event (may arrive before checkout.session.completed)
        const subscription = event.data.object as Stripe.Subscription
        
        console.log(`Subscription created: ${subscription.id}, customer: ${subscription.customer}`)
        
        // Try to find the checkout session to get password metadata
        // The subscription metadata might not have the password, so we need to find the session
        let userEmail: string | null = null
        let userPassword: string | null = null
        let userId: string | null = null
        
        // Get customer email from Stripe
        const customerId = subscription.customer as string
        if (customerId && customerId.startsWith('cus_')) {
          try {
            const customer = await stripe.customers.retrieve(customerId)
            if (typeof customer !== 'string' && !customer.deleted) {
              userEmail = customer.email || null
              console.log(`Found customer email: ${userEmail}`)
            }
          } catch (err) {
            console.error('Error retrieving customer:', err)
          }
        }
        
        // Try to find checkout session to get password metadata
        // Search by customer email (more reliable than subscription ID)
        if (userEmail) {
          try {
            // List recent checkout sessions for this customer email
            const sessions = await stripe.checkout.sessions.list({
              limit: 10,
              customer_email: userEmail
            })
            
            // Find the most recent session that has this subscription or was created recently
            // Sort by created date (newest first)
            const recentSessions = sessions.data
              .filter(s => s.subscription === subscription.id || 
                          (s.created && s.created > (Date.now() / 1000 - 3600))) // Within last hour
              .sort((a, b) => (b.created || 0) - (a.created || 0))
            
            if (recentSessions.length > 0) {
              const session = recentSessions[0]
              console.log(`Found checkout session: ${session.id}`)
              console.log(`Session metadata:`, JSON.stringify(session.metadata, null, 2))
              
              userEmail = session.metadata?.userEmail || session.customer_email || userEmail
              userPassword = session.metadata?.userPassword || null
              userId = session.metadata?.userId || null
              
              // Normalize userId
              if (userId === '' || userId === null || userId === undefined) {
                userId = null
              }
              
              console.log('Extracted from checkout session:', {
                userId: userId || 'null/empty',
                userEmail: userEmail || 'null',
                hasPassword: !!userPassword,
                passwordLength: userPassword?.length || 0
              })
            } else {
              console.log('No matching checkout session found - will try to find/create user without password update')
            }
          } catch (err) {
            console.error('Error retrieving checkout session:', err)
            console.log('Will proceed without password from checkout session')
          }
        }
        
        // If we have email and password, find or create user
        if (userEmail) {
          // Find existing user by email
          if (!userId) {
            const { data: existingUsers, error: findError } = await supabase.auth.admin.listUsers()
            
            if (findError) {
              console.error('Error listing users:', findError)
            } else if (existingUsers) {
              const existingUser = existingUsers.users.find(u => u.email === userEmail)
              if (existingUser) {
                userId = existingUser.id
                console.log(`Found existing user: ${userId}`)
                
                // Update password if provided
                if (userPassword && userPassword.trim() !== '') {
                  console.log(`Updating password for existing user: ${userId}`)
                  const { error: updateError } = await supabase.auth.admin.updateUserById(
                    userId,
                    { password: userPassword.trim() }
                  )
                  
                  if (updateError) {
                    console.error('❌ Error updating existing user password:', updateError)
                  } else {
                    console.log(`✅ Successfully updated password for existing user: ${userId}`)
                  }
                }
              }
            }
          }
          
          // Create user if doesn't exist and password is provided
          if (!userId && userPassword && userPassword.trim() !== '') {
            console.log(`Creating new user account for: ${userEmail}`)
            
            const { data: newUser, error: createError } = await supabase.auth.admin.createUser({
              email: userEmail,
              password: userPassword.trim(),
              email_confirm: true,
              user_metadata: {
                created_via: 'stripe_subscription',
                stripe_customer_id: customerId
              }
            })
            
            if (createError) {
              console.error('❌ Error creating user:', createError)
              userId = null
            } else if (newUser?.user) {
              userId = newUser.user.id
              console.log(`✅ Successfully created new user: ${userId} for email: ${userEmail}`)
            }
          }
        }
        
        // Save subscription
        const { data: subscriptionData, error: subError } = await supabase
          .from('subscriptions')
          .upsert({
            user_id: userId,
            stripe_subscription_id: subscription.id,
            stripe_customer_id: customerId,
            status: subscription.status,
            current_period_start: new Date(subscription.current_period_start * 1000).toISOString(),
            current_period_end: new Date(subscription.current_period_end * 1000).toISOString(),
          }, {
            onConflict: 'stripe_subscription_id'
          })
          .select()

        if (subError) {
          console.error('❌ Error saving subscription:', subError)
          throw subError
        }

        console.log(`✅ Subscription saved:`, JSON.stringify(subscriptionData, null, 2))

        // Update user profile
        if (userId) {
          const { data: profileData, error: profileError } = await supabase
            .from('user_profiles')
            .upsert({
              id: userId,
              email: userEmail,
              stripe_customer_id: customerId,
              subscription_status: subscription.status === 'active' ? 'active' : 'inactive',
            }, {
              onConflict: 'id'
            })
            .select()

          if (profileError) {
            console.error('❌ Error updating user profile:', profileError)
          } else {
            console.log(`✅ User profile updated:`, JSON.stringify(profileData, null, 2))
          }
        }

        console.log(`✅✅✅ Subscription created successfully for user: ${userId || 'N/A'} (${userEmail || 'N/A'})`)
        break
      }

      case 'customer.subscription.updated':
      case 'customer.subscription.deleted': {
        const subscription = event.data.object as Stripe.Subscription

        console.log(`Updating subscription: ${subscription.id}, status: ${subscription.status}`)

        // Update subscription record
        const { error: subError } = await supabase
          .from('subscriptions')
          .update({
            status: subscription.status,
            current_period_start: new Date(subscription.current_period_start * 1000).toISOString(),
            current_period_end: new Date(subscription.current_period_end * 1000).toISOString(),
          })
          .eq('stripe_subscription_id', subscription.id)

        if (subError) {
          console.error('Error updating subscription:', subError)
          throw subError
        }

        // Update user profile
        const { error: profileError } = await supabase
          .from('user_profiles')
          .update({
            subscription_status: subscription.status === 'active' ? 'active' : 'inactive',
          })
          .eq('stripe_customer_id', subscription.customer as string)

        if (profileError) {
          console.error('Error updating user profile:', profileError)
        }

        console.log(`Subscription updated: ${subscription.id}`)
        break
      }

      default:
        console.log(`Unhandled event type: ${event.type}`)
    }

    return new Response(
      JSON.stringify({ received: true }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200
      }
    )
  } catch (error) {
    console.error('Webhook error:', error)
    return new Response(
      JSON.stringify({ error: error.message }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 500
      }
    )
  }
})

