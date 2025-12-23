# Complete AWS S3 Deployment Guide

Complete step-by-step guide for deploying your website with authentication, payments, and Supabase integration to AWS S3 + CloudFront.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [S3 Bucket Configuration](#s3-bucket-configuration)
4. [CloudFront Setup (Required for HTTPS)](#cloudfront-setup-required-for-https)
5. [Supabase Edge Functions](#supabase-edge-functions)
6. [Deployment Steps](#deployment-steps)
7. [Testing Your Deployment](#testing-your-deployment)
8. [Domain Setup (Optional)](#domain-setup-optional)
9. [Troubleshooting](#troubleshooting)
10. [Automated Deployment](#automated-deployment)

---

## Overview

Your website includes:
- ✅ Static HTML/CSS/JavaScript files
- ✅ Supabase authentication (login/signup)
- ✅ Stripe payment integration
- ✅ Supabase Edge Functions (checkout, webhooks, account deletion)
- ✅ Dynamic data loading from Supabase tables

**Important**: Since you're using Stripe, you **MUST** use CloudFront with HTTPS. Stripe requires HTTPS for security.

---

## Prerequisites

Before starting, ensure you have:

- ✅ AWS account with appropriate permissions
- ✅ S3 bucket created (you mentioned this is done)
- ✅ AWS CLI installed and configured (`aws configure`)
- ✅ Supabase project set up with Edge Functions deployed
- ✅ Stripe account with test/live keys
- ✅ All website files in `website_files/` directory

**Check your current setup:**
```bash
# Verify AWS CLI is installed
aws --version

# Verify you're authenticated
aws sts get-caller-identity

# List your S3 buckets
aws s3 ls
```

---

## S3 Bucket Configuration

### Step 1: Enable Static Website Hosting

1. Go to **AWS Console** → **S3** → Select your bucket
2. Click **Properties** tab
3. Scroll to **Static website hosting**
4. Click **Edit** and configure:
   - **Static website hosting**: ✅ Enable
   - **Hosting type**: Host a static website
   - **Index document**: `index.html`
   - **Error document**: `index.html` (important for SPA routing)
5. Click **Save changes**
6. **Note the website endpoint URL** (you'll need this for CloudFront)



## CloudFront Setup (Required for HTTPS)

CloudFront is **required** because:
- ✅ Stripe requires HTTPS (won't work on HTTP)
- ✅ Better security
- ✅ Better performance (CDN)
- ✅ Custom domain support

### Step 1: Create CloudFront Distribution

1. Go to **AWS Console** → **CloudFront** → **Create distribution**

2. **Origin settings**:
   - **Origin domain**: Select your S3 bucket **website endpoint**
     - Should look like: `your-bucket-name.s3-website-us-east-1.amazonaws.com`
     - ⚠️ **Important**: Use the website endpoint, NOT the REST API endpoint
   - **Origin path**: Leave empty
   - **Name**: Auto-filled
   - **Origin access**: Select "Public" (since bucket is public)

3. **Default cache behavior**:
   - **Viewer protocol policy**: ✅ **Redirect HTTP to HTTPS** (required for Stripe)
   - **Allowed HTTP methods**: GET, HEAD, OPTIONS
   - **Cache policy**: 
     - For development: `CachingDisabled`
     - For production: `CachingOptimized`
   - **Compress objects automatically**: ✅ Yes

4. **Distribution settings**:
   - **Price class**: Use all edge locations (or cheapest for testing)
   - **Alternate domain names (CNAMEs)**: Leave empty for now (add after domain setup)
   - **SSL certificate**: Default CloudFront certificate (for now)
   - **Default root object**: `index.html`
   - **Custom error responses**: 
     - Click **Create custom error response**
     - **HTTP error code**: 403
     - **Customize error response**: ✅ Yes
     - **Response page path**: `/index.html`
     - **HTTP response code**: 200
     - **Repeat for 404 errors** (same settings)

5. Click **Create distribution**

6. **Wait 10-15 minutes** for distribution to deploy (status will change from "In Progress" to "Deployed")

7. **Note your CloudFront domain**: `https://d1234abcd5678.cloudfront.net`

### Step 2: Update Supabase CORS Settings

After CloudFront is deployed:

1. Go to **Supabase Dashboard** → Your project → **Settings** → **API**
2. Add your CloudFront domain to allowed origins:
   - Format: `https://your-cloudfront-id.cloudfront.net`
   - Or your custom domain: `https://yourdomain.com` (if you set one up)

**Note**: Your Edge Functions already have `'Access-Control-Allow-Origin': '*'` in the code, so they should work from any origin. But it's good practice to restrict it for production.

---

## Supabase Edge Functions

Your Edge Functions should already be deployed, but verify:

### Check Deployed Functions

1. Go to **Supabase Dashboard** → Your project → **Edge Functions**
2. Verify these functions are deployed:
   - ✅ `create-checkout-session`
   - ✅ `stripe-webhook`
   - ✅ `delete-account`

### Verify Environment Variables

Each Edge Function needs these environment variables (set in Supabase Dashboard):

**For `create-checkout-session`:**
- `STRIPE_SECRET_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

**For `stripe-webhook`:**
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

**For `delete-account`:**
- `STRIPE_SECRET_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

### Update Webhook URL in Stripe

1. Go to **Stripe Dashboard** → **Developers** → **Webhooks**
2. Find your webhook endpoint
3. Verify the URL is: `https://uxdqrswbcgkkftvompwd.supabase.co/functions/v1/stripe-webhook`
4. If you have a custom domain, you can keep using the Supabase URL (it's fine)

---

## Deployment Steps

### Step 1: Prepare Files for Deployment

1. **Verify all files exist** in `website_files/`:
   ```
   website_files/
   ├── index.html
   ├── about.html
   ├── advanced.html
   ├── script.js
   ├── advanced.js
   ├── styles.css
   └── website_data/ (optional, if you want to keep CSV backups)
   ```

2. **Check file paths** are relative (not absolute):
   - ✅ `href="styles.css"` (good)
   - ✅ `src="script.js"` (good)
   - ❌ `href="/styles.css"` (might cause issues)
   - ❌ `href="C:/path/to/styles.css"` (won't work)

3. **Verify Supabase/Stripe keys** are correct in:
   - `script.js` (line 2-3)
   - `advanced.js` (line 3-8)

### Step 2: Upload Files to S3

**Option A: Using AWS CLI (Recommended)**

```bash
# Navigate to project directory
cd /Users/charlie/Desktop/DataWeapons

# Sync all files to S3 (removes files not in local directory)
aws s3 sync website_files/ s3://YOUR-BUCKET-NAME/ \
  --delete \
  --exclude "website_data/*" \
  --exclude "*.csv"

# Set correct content types for HTML files
aws s3 cp website_files/*.html s3://YOUR-BUCKET-NAME/ \
  --content-type "text/html" \
  --recursive

# Set correct content types for CSS
aws s3 cp website_files/*.css s3://YOUR-BUCKET-NAME/ \
  --content-type "text/css" \
  --recursive

# Set correct content types for JavaScript
aws s3 cp website_files/*.js s3://YOUR-BUCKET-NAME/ \
  --content-type "application/javascript" \
  --recursive
```

**Option B: Using AWS Console (Manual)**

1. Go to **S3 Console** → Your bucket
2. Click **Upload**
3. **Add files** from `website_files/` directory:
   - Select all `.html`, `.js`, `.css` files
   - **Do NOT** upload `website_data/` folder (not needed)
4. Click **Upload**

### Step 3: Invalidate CloudFront Cache

After uploading files, you need to invalidate CloudFront cache:

**Using AWS CLI:**
```bash
# Replace YOUR-DISTRIBUTION-ID with your actual CloudFront distribution ID
aws cloudfront create-invalidation \
  --distribution-id YOUR-DISTRIBUTION-ID \
  --paths "/*"
```

**Using AWS Console:**
1. Go to **CloudFront Console** → Your distribution
2. Click **Invalidations** tab
3. Click **Create invalidation**
4. **Object paths**: `/*` (to invalidate everything)
5. Click **Create invalidation**
6. Wait 2-5 minutes for invalidation to complete

**Note**: CloudFront invalidations are free for the first 1,000 per month, then $0.005 per invalidation.

---

## Testing Your Deployment

### Step 1: Test Basic Access

1. **Test S3 website endpoint** (HTTP only):
   - URL: `http://your-bucket-name.s3-website-region.amazonaws.com`
   - Should load your homepage

2. **Test CloudFront URL** (HTTPS):
   - URL: `https://your-cloudfront-id.cloudfront.net`
   - Should load your homepage over HTTPS
   - ✅ Check browser shows lock icon (secure connection)

### Step 2: Test All Pages

Visit each page:
- ✅ `https://your-cloudfront-id.cloudfront.net/index.html`
- ✅ `https://your-cloudfront-id.cloudfront.net/about.html`
- ✅ `https://your-cloudfront-id.cloudfront.net/advanced.html`

### Step 3: Test Supabase Integration

1. **Open browser console** (F12)
2. **Visit your CloudFront URL**
3. **Check for errors**:
   - Should see: "Supabase client initialized" (if you have logging)
   - No CORS errors
   - No 404 errors for Supabase SDK

4. **Test data loading**:
   - Homepage should load data from Supabase table
   - Check Network tab for successful API calls

### Step 4: Test Authentication

1. **Go to Advanced page**
2. **Click "Subscribe Now"** or "Log in"
3. **Test signup flow**:
   - Enter email and password
   - Should redirect to Stripe Checkout
   - Complete test payment
   - Should auto-login after payment

4. **Test login flow**:
   - Log out
   - Log back in with existing credentials
   - Should show account menu

### Step 5: Test Stripe Integration

1. **Verify Stripe.js loads**:
   - Check browser console for Stripe errors
   - Check Network tab for `js.stripe.com` requests

2. **Test checkout**:
   - Click "Subscribe Now"
   - Fill in email/password
   - Should redirect to Stripe Checkout
   - Use test card: `4242 4242 4242 4242`
   - Complete checkout
   - Should redirect back and auto-login

3. **Verify webhook**:
   - Go to Stripe Dashboard → Developers → Webhooks
   - Check for successful webhook events
   - Should see `checkout.session.completed` event

### Step 6: Test Edge Functions

1. **Test `create-checkout-session`**:
   - Open browser console
   - Try to subscribe
   - Check Network tab for function call
   - Should return checkout session ID

2. **Test `delete-account`**:
   - Log in
   - Click "Delete Account"
   - Should successfully delete account

### Testing Checklist

- [ ] Website loads at CloudFront URL
- [ ] All pages accessible
- [ ] HTTPS working (lock icon in browser)
- [ ] Supabase client initializes
- [ ] Data loads from Supabase tables
- [ ] Login works
- [ ] Signup works
- [ ] Stripe Checkout redirects correctly
- [ ] Payment webhook processes successfully
- [ ] Auto-login after payment works
- [ ] Account deletion works
- [ ] No CORS errors in console
- [ ] No 404 errors
- [ ] All assets load correctly

---

## Domain Setup (Optional)

If you want to use a custom domain (e.g., `yourdomain.com`):

### Step 1: Request SSL Certificate

1. Go to **AWS Certificate Manager (ACM)**
2. **Important**: Select **us-east-1** region (required for CloudFront)
3. Click **Request a certificate**
4. **Domain name**: `yourdomain.com`
5. **Add additional names**: `www.yourdomain.com` (optional)
6. **Validation method**: DNS validation (recommended)
7. **Add CNAME records** to your DNS provider as instructed
8. **Wait for validation** (usually 5-30 minutes)

### Step 2: Update CloudFront Distribution

1. Go to **CloudFront Console** → Your distribution → **General** tab → **Edit**
2. **Alternate domain names (CNAMEs)**: 
   - Add `yourdomain.com`
   - Add `www.yourdomain.com` (if you requested it)
3. **Custom SSL certificate**: Select your ACM certificate
4. Click **Save changes**
5. **Wait 10-15 minutes** for changes to deploy

### Step 3: Update DNS Records

At your DNS provider (Route 53, Namecheap, GoDaddy, etc.):

**For root domain (`yourdomain.com`)**:
- **Type**: A (or Alias if using Route 53)
- **Name**: `@` or leave blank
- **Value**: Your CloudFront distribution domain (e.g., `d1234abcd5678.cloudfront.net`)
- **TTL**: 300 (or default)

**For www subdomain (`www.yourdomain.com`)**:
- **Type**: CNAME
- **Name**: `www`
- **Value**: Your CloudFront distribution domain
- **TTL**: 300 (or default)

### Step 4: Update Supabase/Stripe Settings

1. **Update Supabase allowed origins** with your domain
2. **Update any hardcoded URLs** in your code (if any)
3. **Stripe webhook URL** can stay as Supabase URL (no change needed)

**Wait 24-48 hours** for DNS propagation to complete.

---

## Troubleshooting

### Issue: 403 Forbidden Error

**Symptoms**: Website shows "403 Forbidden" or "Access Denied"

**Solutions**:
1. Check bucket policy allows public read access
2. Check Block Public Access settings are disabled
3. Verify you're using the website endpoint (not REST API endpoint) in CloudFront
4. Check file permissions in S3

### Issue: CORS Errors

**Symptoms**: Browser console shows CORS errors when calling Supabase

**Solutions**:
1. Verify Supabase Edge Functions have CORS headers (they should)
2. Check Supabase project settings allow your CloudFront domain
3. Verify CloudFront is forwarding appropriate headers
4. Check browser console for specific error messages

### Issue: Supabase Connection Fails

**Symptoms**: Data doesn't load, authentication doesn't work

**Solutions**:
1. Check Supabase URL and anon key are correct in `script.js` and `advanced.js`
2. Verify Supabase project is active
3. Check browser console for specific error messages
4. Verify you're accessing site over HTTPS (required for some browsers)

### Issue: Stripe Checkout Not Working

**Symptoms**: Clicking "Subscribe" doesn't redirect to Stripe

**Solutions**:
1. **Most common**: Site must be served over HTTPS (Stripe requirement)
   - Verify you're using CloudFront URL (HTTPS)
   - Don't use S3 website endpoint (HTTP only)
2. Check Stripe publishable key is correct in `advanced.js`
3. Check browser console for errors
4. Verify Edge Function `create-checkout-session` is deployed
5. Check Network tab for function call errors

### Issue: CloudFront Shows Old Content

**Symptoms**: Changes don't appear after uploading new files

**Solutions**:
1. Create CloudFront invalidation for `/*`
2. Wait 2-5 minutes for invalidation to complete
3. Clear browser cache (Ctrl+Shift+Delete or Cmd+Shift+Delete)
4. Try incognito/private browsing mode

### Issue: Domain Not Resolving

**Symptoms**: Custom domain doesn't load

**Solutions**:
1. Wait 24-48 hours for DNS propagation
2. Verify DNS records are correct using `dig yourdomain.com` or `nslookup yourdomain.com`
3. Check CloudFront distribution has your domain in CNAMEs
4. Verify SSL certificate is attached to CloudFront distribution

### Issue: Edge Function Returns 404

**Symptoms**: Calls to Supabase Edge Functions return 404

**Solutions**:
1. Verify function is deployed in Supabase Dashboard
2. Check function name is correct (case-sensitive)
3. Verify you're calling: `supabase.functions.invoke('function-name', ...)`
4. Check Supabase project URL is correct

---

## Automated Deployment

### Option 1: Simple Deployment Script

Create `deploy.sh`:

```bash
#!/bin/bash

# Configuration
BUCKET_NAME="your-bucket-name"
DISTRIBUTION_ID="your-cloudfront-distribution-id"

# Upload files
echo "Uploading files to S3..."
aws s3 sync website_files/ s3://$BUCKET_NAME/ \
  --delete \
  --exclude "website_data/*" \
  --exclude "*.csv"

# Set content types
echo "Setting content types..."
aws s3 cp website_files/*.html s3://$BUCKET_NAME/ \
  --content-type "text/html" --recursive

aws s3 cp website_files/*.css s3://$BUCKET_NAME/ \
  --content-type "text/css" --recursive

aws s3 cp website_files/*.js s3://$BUCKET_NAME/ \
  --content-type "application/javascript" --recursive

# Invalidate CloudFront
echo "Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/*"

echo "Deployment complete!"
```

Make it executable:
```bash
chmod +x deploy.sh
```

Run it:
```bash
./deploy.sh
```

### Option 2: GitHub Actions (Advanced)

You can set up automatic deployment on every push. Create `.github/workflows/deploy-website.yml`:

```yaml
name: Deploy Website to S3

on:
  push:
    branches: [ main ]
    paths:
      - 'website_files/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Deploy to S3
        run: |
          aws s3 sync website_files/ s3://${{ secrets.S3_BUCKET_NAME }}/ --delete
          aws s3 cp website_files/*.html s3://${{ secrets.S3_BUCKET_NAME }}/ \
            --content-type "text/html" --recursive
          aws s3 cp website_files/*.css s3://${{ secrets.S3_BUCKET_NAME }}/ \
            --content-type "text/css" --recursive
          aws s3 cp website_files/*.js s3://${{ secrets.S3_BUCKET_NAME }}/ \
            --content-type "application/javascript" --recursive
      
      - name: Invalidate CloudFront
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }} \
            --paths "/*"
```

Add these secrets in GitHub:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `S3_BUCKET_NAME`
- `CLOUDFRONT_DISTRIBUTION_ID`

---

## Quick Reference

### Important URLs

- **S3 Website Endpoint**: `http://your-bucket-name.s3-website-region.amazonaws.com`
- **CloudFront URL**: `https://your-cloudfront-id.cloudfront.net`
- **Supabase Project**: `https://uxdqrswbcgkkftvompwd.supabase.co`
- **Supabase Edge Functions**: `https://uxdqrswbcgkkftvompwd.supabase.co/functions/v1/`

### Key Files to Deploy

- `index.html`
- `about.html`
- `advanced.html`
- `script.js`
- `advanced.js`
- `styles.css`

### Key Configuration Values

**In `script.js` and `advanced.js`:**
- `SUPABASE_URL`: `https://uxdqrswbcgkkftvompwd.supabase.co`
- `SUPABASE_ANON_KEY`: (your anon key)
- `STRIPE_PUBLISHABLE_KEY`: (your Stripe publishable key)
- `STRIPE_PRICE_ID`: (your Stripe price ID)

### Common Commands

```bash
# Upload files
aws s3 sync website_files/ s3://YOUR-BUCKET-NAME/ --delete

# Invalidate CloudFront
aws cloudfront create-invalidation \
  --distribution-id YOUR-DISTRIBUTION-ID \
  --paths "/*"

# Check S3 bucket policy
aws s3api get-bucket-policy --bucket YOUR-BUCKET-NAME

# List CloudFront distributions
aws cloudfront list-distributions
```

---

## Cost Estimation

**S3 Storage**: ~$0.00023/month for small website (~10 MB)

**S3 Requests**: ~$0.0004 per 1,000 GET requests

**CloudFront**: 
- Data transfer: $0.085 per GB (first 10 TB)
- Requests: $0.0075 per 10,000 HTTPS requests
- For 1,000 visitors/month: ~$0.09/month

**Total**: ~$1-5/month for low-medium traffic

---

## Next Steps After Deployment

1. ✅ Test all functionality thoroughly
2. ✅ Set up monitoring (CloudWatch, error tracking)
3. ✅ Configure automated deployments
4. ✅ Set up backup/versioning in S3
5. ✅ Consider CloudFront WAF for additional security
6. ✅ Set up access logs for analytics

---

## Support

- [AWS S3 Static Website Hosting](https://docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteHosting.html)
- [CloudFront Documentation](https://docs.aws.amazon.com/cloudfront/)
- [Supabase Edge Functions](https://supabase.com/docs/guides/functions)
- [Stripe HTTPS Requirements](https://stripe.com/docs/security/guide#tls)

---

**You're all set!** 🚀

Follow the steps above in order, and your website with authentication and payments will be live on AWS.

