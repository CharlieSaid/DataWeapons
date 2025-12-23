# AWS S3 Migration Guide

Complete guide for migrating your website from local hosting to AWS S3 (with CloudFront CDN).

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [S3 Bucket Configuration](#s3-bucket-configuration)
3. [CloudFront Setup (Recommended)](#cloudfront-setup-recommended)
4. [CORS Configuration](#cors-configuration)
5. [Deployment Process](#deployment-process)
6. [Domain & SSL Setup](#domain--ssl-setup)
7. [Testing Checklist](#testing-checklist)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting, ensure you have:
- ✅ AWS account with appropriate permissions
- ✅ S3 bucket already created (you mentioned this is done)
- ✅ Domain name (optional, but recommended)
- ✅ All website files ready in `website_files/` directory

---

## S3 Bucket Configuration

### Step 1: Enable Static Website Hosting

1. **Go to S3 Console** → Select your bucket
2. **Properties tab** → Scroll to "Static website hosting"
3. **Click "Edit"** and configure:
   - **Static website hosting**: Enable
   - **Hosting type**: Host a static website
   - **Index document**: `index.html`
   - **Error document**: `index.html` (for SPA routing)
   - **Click "Save changes"**

### Step 2: Set Bucket Policy (Public Read Access)

1. **Permissions tab** → **Bucket policy**
2. **Click "Edit"** and add this policy (replace `YOUR-BUCKET-NAME`):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::YOUR-BUCKET-NAME/*"
        }
    ]
}
```

3. **Click "Save changes"**

### Step 3: Block Public Access Settings

1. **Permissions tab** → **Block public access (bucket settings)**
2. **Click "Edit"**
3. **Uncheck** "Block all public access" (or uncheck only "Block public access to buckets and objects granted through new public bucket or access point policies")
4. **Click "Save changes"** and confirm

### Step 4: Configure CORS (Important for Supabase/Stripe)

1. **Permissions tab** → **Cross-origin resource sharing (CORS)**
2. **Click "Edit"** and add:

```json
[
    {
        "AllowedHeaders": [
            "*"
        ],
        "AllowedMethods": [
            "GET",
            "HEAD"
        ],
        "AllowedOrigins": [
            "*"
        ],
        "ExposeHeaders": [],
        "MaxAgeSeconds": 3000
    }
]
```

3. **Click "Save changes"**

**Note**: This CORS config is for S3. Your Supabase Edge Functions already have CORS headers configured.

---

## CloudFront Setup (Recommended)

CloudFront provides:
- ✅ HTTPS/SSL (required for Stripe)
- ✅ Custom domain support
- ✅ Better performance (CDN)
- ✅ Lower latency
- ✅ DDoS protection

### Step 1: Create CloudFront Distribution

1. **Go to CloudFront Console** → **Create distribution**
2. **Origin settings**:
   - **Origin domain**: Select your S3 bucket (use the website endpoint, not the REST API endpoint)
     - Should look like: `your-bucket-name.s3-website-us-east-1.amazonaws.com`
     - Or: `your-bucket-name.s3-website.region.amazonaws.com`
   - **Origin path**: Leave empty
   - **Name**: Auto-filled
   - **Origin access**: Select "Public" (since bucket is public)

3. **Default cache behavior**:
   - **Viewer protocol policy**: Redirect HTTP to HTTPS (required for Stripe)
   - **Allowed HTTP methods**: GET, HEAD, OPTIONS
   - **Cache policy**: CachingOptimized (or CachingDisabled for development)
   - **Origin request policy**: CORS-CustomOrigin (if using custom origin)

4. **Distribution settings**:
   - **Price class**: Use all edge locations (or cheapest for testing)
   - **Alternate domain names (CNAMEs)**: Leave empty for now (add after domain setup)
   - **SSL certificate**: Default CloudFront certificate (or request custom one if you have a domain)
   - **Default root object**: `index.html`
   - **Custom error responses**: 
     - **HTTP error code**: 403
     - **Customize error response**: Yes
     - **Response page path**: `/index.html`
     - **HTTP response code**: 200
     - **Repeat for 404 errors**

5. **Click "Create distribution"**
6. **Wait 10-15 minutes** for distribution to deploy

### Step 2: Update Supabase CORS Settings

After CloudFront is deployed, update your Supabase project settings:

1. **Go to Supabase Dashboard** → Your project → **Settings** → **API**
2. **Add your CloudFront domain** to allowed origins:
   - Format: `https://your-cloudfront-id.cloudfront.net`
   - Or your custom domain: `https://yourdomain.com`

**Note**: Supabase Edge Functions already have `'Access-Control-Allow-Origin': '*'` in the code, so they should work from any origin. But it's good practice to restrict it.

---

## CORS Configuration

### Supabase Edge Functions

Your Edge Functions already have CORS configured with:
```typescript
const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}
```

**For production**, consider restricting the origin:
```typescript
const allowedOrigins = [
  'https://yourdomain.com',
  'https://www.yourdomain.com',
  'https://your-cloudfront-id.cloudfront.net'
]

const origin = req.headers.get('origin')
const corsHeaders = {
  'Access-Control-Allow-Origin': allowedOrigins.includes(origin) ? origin : allowedOrigins[0],
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Credentials': 'true',
}
```

---

## Deployment Process

### Step 1: Prepare Files for Deployment

1. **Ensure all files are ready** in `website_files/`:
   - `index.html`
   - `about.html`
   - `advanced.html`
   - `script.js`
   - `advanced.js`
   - `styles.css`
   - Any other assets

2. **Verify file paths** are relative (not absolute):
   - ✅ `href="styles.css"` (good)
   - ❌ `href="/styles.css"` (might work, but relative is better)
   - ❌ `href="C:/path/to/styles.css"` (won't work)

### Step 2: Upload Files to S3

**Option A: Using AWS Console (Manual)**

1. **Go to S3 Console** → Your bucket
2. **Click "Upload"**
3. **Add files** from `website_files/` directory
4. **Click "Upload"**

**Option B: Using AWS CLI (Recommended for automation)**

```bash
# Install AWS CLI if not already installed
# macOS: brew install awscli
# Then configure: aws configure

# Upload all files
cd /Users/charlie/Desktop/DataWeapons
aws s3 sync website_files/ s3://YOUR-BUCKET-NAME/ --delete

# The --delete flag removes files from S3 that don't exist locally
```

**Option C: Using AWS SDK (For CI/CD)**

You can add this to your GitHub Actions workflow later for automatic deployments.

### Step 3: Set Correct Content Types

Some files might need explicit content types:

```bash
# Set content type for HTML files
aws s3 cp website_files/index.html s3://YOUR-BUCKET-NAME/index.html \
  --content-type "text/html"

aws s3 cp website_files/*.html s3://YOUR-BUCKET-NAME/ \
  --content-type "text/html" --recursive

# Set content type for CSS
aws s3 cp website_files/*.css s3://YOUR-BUCKET-NAME/ \
  --content-type "text/css" --recursive

# Set content type for JavaScript
aws s3 cp website_files/*.js s3://YOUR-BUCKET-NAME/ \
  --content-type "application/javascript" --recursive
```

### Step 4: Invalidate CloudFront Cache (If Using CloudFront)

After uploading new files:

1. **Go to CloudFront Console** → Your distribution
2. **Invalidations tab** → **Create invalidation**
3. **Object paths**: `/*` (to invalidate everything)
4. **Click "Create invalidation"**
5. **Wait 2-5 minutes** for invalidation to complete

**Note**: CloudFront invalidations cost money after the first 1,000 per month. For frequent updates, consider using versioned file names or a different cache policy.

---

## Domain & SSL Setup

### Step 1: Get a Domain (If You Don't Have One)

- Use Route 53, Namecheap, GoDaddy, etc.
- Point your domain's nameservers to your registrar

### Step 2: Request SSL Certificate

1. **Go to AWS Certificate Manager (ACM)**
2. **Request a certificate**
3. **Domain name**: `yourdomain.com`
4. **Add additional names**: `www.yourdomain.com` (optional)
5. **Validation method**: DNS validation (recommended)
6. **Add CNAME records** to your DNS provider as instructed
7. **Wait for validation** (usually 5-30 minutes)

**Important**: Request the certificate in **us-east-1** region (required for CloudFront)

### Step 3: Update CloudFront Distribution

1. **Go to CloudFront Console** → Your distribution → **General tab** → **Edit**
2. **Alternate domain names (CNAMEs)**: Add `yourdomain.com` and `www.yourdomain.com`
3. **Custom SSL certificate**: Select your ACM certificate
4. **Click "Save changes"**

### Step 4: Update DNS Records

At your DNS provider, add:

**For root domain (`yourdomain.com`)**:
- **Type**: A
- **Name**: `@` or leave blank
- **Value**: Your CloudFront distribution domain (e.g., `d1234abcd5678.cloudfront.net`)
- **Alias**: Yes (if supported)

**For www subdomain (`www.yourdomain.com`)**:
- **Type**: CNAME
- **Name**: `www`
- **Value**: Your CloudFront distribution domain

**Note**: If using Route 53, use Alias records. For other providers, use CNAME (but CNAME for root domain might not be supported - use A record pointing to CloudFront IP).

### Step 5: Update Supabase/Stripe Settings

1. **Update Supabase allowed origins** with your domain
2. **Update Stripe webhook URL** (if using custom domain):
   - Go to Stripe Dashboard → Developers → Webhooks
   - Update webhook endpoint to: `https://yourdomain.com/.netlify/functions/stripe-webhook`
   - Actually, your webhook is on Supabase, so update it to: `https://uxdqrswbcgkkftvompwd.supabase.co/functions/v1/stripe-webhook`

---

## Testing Checklist

### Pre-Deployment Testing

- [ ] All files uploaded to S3
- [ ] S3 static website hosting enabled
- [ ] Bucket policy allows public read
- [ ] CORS configured correctly

### Post-Deployment Testing

- [ ] **Basic Access**:
  - [ ] Website loads at S3 website endpoint
  - [ ] Website loads at CloudFront URL
  - [ ] All pages accessible (index, about, advanced)

- [ ] **Supabase Integration**:
  - [ ] Supabase client initializes
  - [ ] Can query data from Supabase tables
  - [ ] Login functionality works
  - [ ] Sign up functionality works
  - [ ] Authentication state persists

- [ ] **Stripe Integration**:
  - [ ] Stripe.js loads correctly
  - [ ] Checkout session creation works
  - [ ] Redirect to Stripe Checkout works
  - [ ] Webhook receives events (check Stripe Dashboard)

- [ ] **Edge Functions**:
  - [ ] `create-checkout-session` function works
  - [ ] `delete-account` function works
  - [ ] CORS headers present in responses

- [ ] **HTTPS/SSL**:
  - [ ] Site loads over HTTPS
  - [ ] No mixed content warnings
  - [ ] SSL certificate valid

- [ ] **Performance**:
  - [ ] Page load times acceptable
  - [ ] Images/assets load correctly
  - [ ] No 404 errors in browser console

### Testing URLs

1. **S3 Website Endpoint**: `http://your-bucket-name.s3-website-region.amazonaws.com`
2. **CloudFront URL**: `https://your-cloudfront-id.cloudfront.net`
3. **Custom Domain**: `https://yourdomain.com`

---

## Troubleshooting

### Issue: 403 Forbidden Error

**Solution**:
- Check bucket policy allows public read
- Check Block Public Access settings
- Verify file permissions in S3

### Issue: CORS Errors in Browser Console

**Solution**:
- Verify S3 CORS configuration
- Check Supabase Edge Functions have CORS headers
- Ensure CloudFront is forwarding appropriate headers

### Issue: Supabase Connection Fails

**Solution**:
- Check Supabase URL and keys are correct in JavaScript files
- Verify Supabase project allows your CloudFront domain
- Check browser console for specific error messages

### Issue: Stripe Checkout Not Working

**Solution**:
- Ensure site is served over HTTPS (required by Stripe)
- Verify Stripe publishable key is correct
- Check browser console for errors
- Verify Edge Function `create-checkout-session` is deployed

### Issue: CloudFront Shows Old Content

**Solution**:
- Create CloudFront invalidation for `/*`
- Wait 2-5 minutes for invalidation to complete
- Clear browser cache

### Issue: Domain Not Resolving

**Solution**:
- Wait 24-48 hours for DNS propagation
- Verify DNS records are correct
- Use `dig yourdomain.com` or `nslookup yourdomain.com` to check

---

## Security Considerations

### Public Keys in JavaScript

Your Supabase anon key and Stripe publishable key are in your JavaScript files. **This is correct and safe**:
- ✅ Supabase anon key is meant to be public (protected by RLS policies)
- ✅ Stripe publishable key is meant to be public
- ❌ Never put service role keys or secret keys in client-side code

### Environment Variables

Since S3 is static hosting, you can't use server-side environment variables. Options:
1. **Build-time replacement**: Replace placeholders during deployment
2. **Configuration file**: Load config from a JSON file
3. **Current approach**: Hardcode public keys (acceptable for public keys only)

### Rate Limiting

Consider adding rate limiting:
- CloudFront has built-in DDoS protection
- Supabase has rate limits on API calls
- Consider adding CloudFront WAF for additional protection

---

## Cost Estimation

**S3 Storage**:
- First 50 GB: $0.023 per GB/month
- For a small website (~10 MB): ~$0.00023/month

**S3 Requests**:
- GET requests: $0.0004 per 1,000 requests
- Very cheap for low traffic

**CloudFront**:
- Data transfer out: $0.085 per GB (first 10 TB)
- Requests: $0.0075 per 10,000 HTTPS requests
- For 1,000 visitors/month viewing 1 MB each: ~$0.09/month

**Total estimated cost**: ~$1-5/month for low-medium traffic

---

## Next Steps After Migration

1. **Set up automated deployments** (GitHub Actions → S3 sync)
2. **Monitor CloudWatch** for errors
3. **Set up CloudFront access logs** for analytics
4. **Configure CloudFront WAF** for security
5. **Set up Route 53 health checks** (if using Route 53)
6. **Configure backup/versioning** in S3

---

## Quick Reference Commands

```bash
# Upload files to S3
aws s3 sync website_files/ s3://YOUR-BUCKET-NAME/ --delete

# Create CloudFront invalidation
aws cloudfront create-invalidation \
  --distribution-id YOUR-DISTRIBUTION-ID \
  --paths "/*"

# Check S3 bucket policy
aws s3api get-bucket-policy --bucket YOUR-BUCKET-NAME

# List CloudFront distributions
aws cloudfront list-distributions
```

---

## Support Resources

- [AWS S3 Static Website Hosting Docs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteHosting.html)
- [CloudFront Documentation](https://docs.aws.amazon.com/cloudfront/)
- [Supabase CORS Guide](https://supabase.com/docs/guides/api/api-cors)
- [Stripe HTTPS Requirements](https://stripe.com/docs/security/guide#tls)

---

**Good luck with your migration!** 🚀

