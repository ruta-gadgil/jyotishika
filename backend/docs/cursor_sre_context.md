# Cursor SRE Context: Samved.ai Backend

> **Purpose**: This file is for AI assistants (Cursor) to understand
> the deployment and debugging context of this repository.
> Read this file when helping with production issues, deployments, or debugging.

## Quick Reference

| Item | Value |
|------|-------|
| **Domain** | api.samved.ai |
| **Stack** | AWS Lambda + API Gateway |
| **Region** | ap-south-1 (Mumbai) |
| **CloudFormation Stack** | samved-api |
| **DynamoDB Tables** | samved-sessions, samved-state-tokens |

## Cross-Repo Dependencies

- **Frontend repo**: `jyotishika-frontend`
- **Frontend URL**: https://app.samved.ai
- **CORS**: Must allow `https://app.samved.ai`
- **Cookies**: `domain=.samved.ai`, `SameSite=None`, `Secure=true`

## Debugging Commands

```bash
# View logs (find function name from CloudFormation stack)
aws logs tail /aws/lambda/samved-api-JyotishikaFunction-XXX --since 30m --region ap-south-1

# Check stack status
aws cloudformation describe-stacks --stack-name samved-api --region ap-south-1

# Test health endpoint
curl https://api.samved.ai/healthz

# Filter logs by request ID
aws logs filter-log-events \
  --log-group-name /aws/lambda/samved-api-JyotishikaFunction-XXX \
  --filter-pattern '"request_id": "abc123"' \
  --region ap-south-1
```

## Common Issues

1. **Cold start timeout**: Increase timeout in template.yaml (currently 60s)
2. **Session not persisting**: Check DynamoDB tables exist and Lambda has permissions
3. **CORS error**: Verify ALLOWED_ORIGINS includes https://app.samved.ai
4. **Cookie not working**: Check cookie settings (secure=True, samesite=None, domain=.samved.ai)

## Environment Variables

All environment variables are set via SAM template parameters:
- `DATABASE_URL` - Supabase PostgreSQL
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` - OAuth
- `SECRET_KEY` - Flask session encryption
- `ALLOWED_ORIGINS` - CORS origins
- `APP_BASE_URL` - https://api.samved.ai
- `FRONTEND_BASE_URL` - https://app.samved.ai
- `DYNAMODB_SESSIONS_TABLE` - samved-sessions
- `DYNAMODB_STATE_TABLE` - samved-state-tokens

## Deployment

Deployments happen automatically via GitHub Actions on push to `main` branch.
Manual deployment: `sam build && sam deploy --region ap-south-1`

---

*Last updated: 2026-01-25*
