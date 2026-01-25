# Deployment Prerequisites

Run these commands before deploying:

## 1. Generate SECRET_KEY

```bash
openssl rand -hex 32
```

Save this output - you'll need it for GitHub Secrets and SAM deployment.

## 2. Install Tools

```bash
# macOS
brew install awscli
brew install aws-sam-cli

# Verify
aws --version
sam --version
docker --version  # Ensure Docker Desktop is running
```

## 3. Configure AWS CLI

```bash
aws configure
# AWS Access Key ID: [your-key]
# AWS Secret Access Key: [your-secret]
# Default region name: ap-south-1
# Default output format: json
```

## 4. Create DynamoDB Tables

```bash
# Sessions table
aws dynamodb create-table \
  --table-name samved-sessions \
  --attribute-definitions AttributeName=session_id,AttributeType=S \
  --key-schema AttributeName=session_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ap-south-1

# State tokens table
aws dynamodb create-table \
  --table-name samved-state-tokens \
  --attribute-definitions AttributeName=state,AttributeType=S \
  --key-schema AttributeName=state,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --ttl-specification Enabled=true,AttributeName=expires_at \
  --region ap-south-1
```

## Next Steps

After completing these prerequisites, proceed with Phase 2: Backend Code Changes.
