# Rate Limiting & Security Configuration (Alpha MVP)

**Date:** 2026-01-28  
**Approach:** Simple, maintainable, monitor-first

---

## ✅ What's In Place

### 1. API Gateway Throttling
**Location:** `template.yaml` → `HttpApiGateway` resource

```yaml
DefaultRouteSettings:
  ThrottlingBurstLimit: 50      # Max concurrent requests
  ThrottlingRateLimit: 100      # Steady-state: 100 requests/second
```

**Purpose:**
- Protects Lambda from overwhelming traffic spikes
- Prevents single abusive client from consuming all capacity
- Returns `429 Too Many Requests` when exceeded

**Alpha Rationale:**
- 100 rps = 360,000 requests/hour = plenty for early users
- Can increase later based on real traffic patterns
- Zero additional cost

### 2. Application-Level Protection
**Location:** `app/routes.py` - All routes require authentication

**Security Features:**
- `/chart`, `/dasha`, `/profiles/*`, `/notes/*` → **Authentication required**
- `/healthz`, `/license`, `/robots.txt` → Public (monitoring & compliance)
- OAuth session validation via DynamoDB
- CORS restricted to `https://app.samved.ai`

**Purpose:**
- Authenticated endpoints prevent anonymous abuse
- Each user has a known identity (Google OAuth)
- Can implement per-user rate limits later if needed

### 3. Bot Discouragement
**Location:** `app/__init__.py` → `/robots.txt` endpoint

```
User-agent: *
Disallow: /
```

**Purpose:**
- Tells well-behaved crawlers to stay away during alpha
- Reduces noise in logs from automated scanners
- Zero cost, simple to maintain

---

## 🔍 What We're NOT Doing (And Why)

### No WAF (AWS Web Application Firewall)
**Rationale:**
- **Cost:** $5/month base + $1/million requests = unnecessary for alpha
- **Complexity:** 4 additional rule types to monitor & tune
- **Premature:** Don't know traffic patterns yet
- **Overkill:** API Gateway throttling is sufficient for alpha abuse protection

**When to Add:**
- Post-launch if seeing coordinated attacks
- If traffic exceeds 1M requests/month
- If monitoring shows suspicious patterns

### No Geo-Blocking
**Rationale:**
- Blocks legitimate users on VPNs, traveling, or using proxies
- Hard to debug ("Why can't I access from my hotel in Dubai?")
- Not necessary when all endpoints require authentication
- Can add monitoring later if needed

### No Per-IP Rate Limiting
**Rationale:**
- API Gateway throttling applies globally
- NAT gateways & corporate proxies share IPs (false positives)
- Authentication provides better user-level control
- Can add later if seeing single-IP abuse

---

## 📊 Monitoring Recommendations

### CloudWatch Alarms to Create

1. **API Gateway Metrics (Immediate Priority)**
   ```
   - Count > 50,000/hour         → Unusual traffic spike
   - 4XXError > 100/5min          → Client errors (auth, validation)
   - 5XXError > 10/5min           → Backend errors (Lambda, DB)
   - Latency p99 > 5000ms         → Performance degradation
   ```

2. **Lambda Metrics (Immediate Priority)**
   ```
   - Errors > 10/5min             → Application crashes
   - Throttles > 0                → Lambda concurrency limit hit
   - Duration p99 > 50000ms       → Timeout risk (60s limit)
   ```

3. **DynamoDB Metrics (Monitor)**
   ```
   - UserErrors > 10/5min         → Schema/capacity issues
   - ThrottledRequests > 0        → Need to increase capacity
   ```

### Logs to Watch

```bash
# API Gateway access logs (if enabled)
aws logs tail /aws/apigateway/samved-api --follow --region ap-south-1

# Lambda function logs
aws logs tail /aws/lambda/samved-api-JyotishikaFunction-XXX --follow --region ap-south-1

# Filter for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/samved-api-JyotishikaFunction-XXX \
  --filter-pattern '"ERROR"' \
  --region ap-south-1
```

---

## 🚀 Deployment Impact

### What Changed
- ✅ Added explicit `HttpApiGateway` with throttling (100 rps / 50 burst)
- ✅ Added `/robots.txt` endpoint to Flask app
- ❌ **No new AWS resources** (just configuration on existing API Gateway)
- ❌ **No cost increase** (throttling is free)

### What Stayed the Same
- Same Lambda function
- Same DynamoDB tables
- Same authentication flow
- Same API endpoints
- Same Docker container

### Breaking Changes
- **API Gateway URL will change** (new explicit API vs implicit)
- **Mitigation:** You use custom domain `api.samved.ai` via DNS, so frontend is unaffected
- **Action Required:** Update any hardcoded API URLs in monitoring/scripts

---

## 🔧 Future Enhancements (When Needed)

### Short-term (Post-Launch, First 1000 Users)
1. Enable API Gateway access logs → S3 for traffic analysis
2. Create CloudWatch dashboard with key metrics
3. Set up SNS alerts for error spikes

### Medium-term (When Traffic Grows)
1. Add AWS WAF with:
   - Rate-based rule (2000 req/5min per IP)
   - Count mode only (monitor, don't block)
   - Review logs weekly, tune thresholds
2. Consider per-user rate limits in application code
3. Add caching layer (CloudFront or ElastiCache) for expensive calculations

### Long-term (Production Scale)
1. Multi-region failover
2. DDoS mitigation service (AWS Shield Advanced)
3. API Gateway usage plans with API keys for partners
4. Application-level circuit breakers

---

## 📝 SRE Decision Log

**Decision:** Use simple throttling + monitoring instead of WAF  
**Rationale:** Alpha MVP with authenticated users, don't know traffic patterns yet  
**Risk:** May need to add WAF quickly if see abuse  
**Mitigation:** CloudWatch alarms alert us immediately to unusual traffic  

**Decision:** No geo-blocking  
**Rationale:** Too risky to block legitimate users (VPNs, travel, proxies)  
**Alternative:** If needed, add geo-monitoring (Count mode) first, then enforce  

**Decision:** Keep throttling conservative (100 rps)  
**Rationale:** 10x higher than expected alpha traffic, easy to increase  
**Monitoring:** Watch for 429 errors from legitimate users  

---

**Last Updated:** 2026-01-28  
**Next Review:** After first 500 real users or 30 days post-launch
