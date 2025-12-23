#!/bin/bash

# AWS S3 Deployment Script
# This script uploads your website files to S3 and optionally invalidates CloudFront cache

set -e  # Exit on error

# Configuration - UPDATE THESE VALUES
BUCKET_NAME="your-bucket-name"
CLOUDFRONT_DISTRIBUTION_ID=""  # Leave empty if not using CloudFront
REGION="us-east-1"  # Change to your bucket's region

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting deployment to S3...${NC}"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed. Please install it first.${NC}"
    echo "   macOS: brew install awscli"
    echo "   Then run: aws configure"
    exit 1
fi

# Check if bucket name is set
if [ "$BUCKET_NAME" == "your-bucket-name" ]; then
    echo -e "${RED}❌ Please update BUCKET_NAME in this script${NC}"
    exit 1
fi

# Check if website_files directory exists
if [ ! -d "website_files" ]; then
    echo -e "${RED}❌ website_files directory not found${NC}"
    exit 1
fi

echo -e "${YELLOW}📦 Uploading files to S3 bucket: ${BUCKET_NAME}${NC}"

# Upload files with proper content types
aws s3 sync website_files/ s3://${BUCKET_NAME}/ \
    --delete \
    --exclude "*.csv" \
    --exclude "website_data/*" \
    --cache-control "max-age=31536000" \
    --region ${REGION}

# Set content types explicitly
echo -e "${YELLOW}📝 Setting content types...${NC}"

# HTML files
aws s3 cp website_files/ s3://${BUCKET_NAME}/ \
    --recursive \
    --exclude "*" \
    --include "*.html" \
    --content-type "text/html" \
    --metadata-directive REPLACE \
    --region ${REGION} 2>/dev/null || true

# CSS files
aws s3 cp website_files/ s3://${BUCKET_NAME}/ \
    --recursive \
    --exclude "*" \
    --include "*.css" \
    --content-type "text/css" \
    --metadata-directive REPLACE \
    --region ${REGION} 2>/dev/null || true

# JavaScript files
aws s3 cp website_files/ s3://${BUCKET_NAME}/ \
    --recursive \
    --exclude "*" \
    --include "*.js" \
    --content-type "application/javascript" \
    --metadata-directive REPLACE \
    --region ${REGION} 2>/dev/null || true

echo -e "${GREEN}✅ Files uploaded successfully!${NC}"

# Invalidate CloudFront cache if distribution ID is provided
if [ ! -z "$CLOUDFRONT_DISTRIBUTION_ID" ]; then
    echo -e "${YELLOW}🔄 Creating CloudFront invalidation...${NC}"
    INVALIDATION_ID=$(aws cloudfront create-invalidation \
        --distribution-id ${CLOUDFRONT_DISTRIBUTION_ID} \
        --paths "/*" \
        --query 'Invalidation.Id' \
        --output text)
    
    echo -e "${GREEN}✅ CloudFront invalidation created: ${INVALIDATION_ID}${NC}"
    echo -e "${YELLOW}⏳ Waiting for invalidation to complete (this may take a few minutes)...${NC}"
    
    aws cloudfront wait invalidation-completed \
        --distribution-id ${CLOUDFRONT_DISTRIBUTION_ID} \
        --id ${INVALIDATION_ID} || echo -e "${YELLOW}⚠️  Invalidation is processing in the background${NC}"
fi

echo -e "${GREEN}🎉 Deployment complete!${NC}"
echo ""
echo "Your website should be available at:"
echo "  S3: http://${BUCKET_NAME}.s3-website-${REGION}.amazonaws.com"
if [ ! -z "$CLOUDFRONT_DISTRIBUTION_ID" ]; then
    CLOUDFRONT_URL=$(aws cloudfront get-distribution \
        --id ${CLOUDFRONT_DISTRIBUTION_ID} \
        --query 'Distribution.DomainName' \
        --output text)
    echo "  CloudFront: https://${CLOUDFRONT_URL}"
fi

