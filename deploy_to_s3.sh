#!/bin/bash
set -e

BUCKET_NAME="data-weapons-public"
REGION="us-east-1"

[ "$BUCKET_NAME" = "your-bucket-name" ] && { echo "Set BUCKET_NAME"; exit 1; }
command -v aws &>/dev/null || { echo "AWS CLI required"; exit 1; }
[ -d "website_files" ] || { echo "website_files not found"; exit 1; }

aws s3 sync website_files/ s3://${BUCKET_NAME}/ --region ${REGION}
