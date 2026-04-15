# Production Testing Guide for Dalīl Group

## Quick Start

### 1. **Start the Development Server**
```bash
cd /home/nour/python-project/dalil_group
uvicorn web.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. **Run the Complete Test Suite** (15-20 minutes)
```bash
python3 test_production.py
```

This runs:
- ✅ **Functionality Tests** - Verifies all 12 routes return 200 OK
- ✅ **Performance Tests** - Response time analysis (100 requests/endpoint)
- ✅ **Load Tests** - Concurrent requests (500 requests/endpoint)
- ✅ **Security Tests** - Basic security checks
- ✅ **Integration Tests** - Health & documentation endpoints

---

## Testing Strategies by Use Case

### Strategy 1: Quick Smoke Test (5 minutes)
For rapid validation after code changes:

```bash
python3 quick_test.py
```

Tests:
- All 12 routes return 200 OK
- Health endpoint accessible
- No critical errors

---

### Strategy 2: Pre-Production Testing (1 hour)
Complete validation before deploying:

```bash
# Run full test suite
python3 test_production.py

# Run API validation
python3 -c "
import requests
routes = ['/health', '/docs', '/evaluations/new', '/']
for r in routes:
    resp = requests.get(f'http://localhost:8000{r}')
    print(f'{r}: {resp.status_code}')
"
```

---

### Strategy 3: Load Simulation Testing (30 minutes)
Verify system can handle production traffic:

```python
# Test with 100-1000 concurrent users
python3 << 'EOF'
import concurrent.futures
import requests
import time

def test_endpoint(n):
    try:
        requests.get('http://localhost:8000/', timeout=5)
        return True
    except:
        return False

# Simulate 100 concurrent users
with concurrent.futures.ThreadPoolExecutor(max_workers=100) as ex:
    futures = [ex.submit(test_endpoint, i) for i in range(1000)]
    success = sum(1 for f in futures if f.result())
    print(f"Success rate: {success}/1000 ({success/10}%)")
EOF
```

---

### Strategy 4: Security Validation
Check HTTPS readiness and security headers:

```bash
# Before production, ensure:
# 1. HTTPS certificate is installed
# 2. Security headers are configured
# 3. Rate limiting is enabled

python3 << 'EOF'
import requests

# Test security headers
resp = requests.get('http://localhost:8000/')
headers = resp.headers

print("Security Headers:")
print(f"  Content-Type: {headers.get('Content-Type', 'Missing')}")
print(f"  Content-Length: {headers.get('Content-Length', 'Missing')}")

# Check for needed production headers
needed = [
    'Strict-Transport-Security',
    'X-Content-Type-Options',
    'X-Frame-Options',
]

for header in needed:
    print(f"  {header}: {'✅' if header in headers else '⚠️'}")
EOF
```

---

### Strategy 5: Database Performance Testing
Test with production-like data volumes:

```bash
# Test evaluation endpoint with database
python3 << 'EOF'
import requests
import json
from concurrent.futures import ThreadPoolExecutor

def create_evaluation():
    try:
        response = requests.post(
            'http://localhost:8000/evaluations/create',
            json={
                'client_name': 'Test Client',
                'prompt_pack': 'government',
            },
            timeout=10
        )
        return response.status_code == 200 or response.status_code == 201
    except:
        return False

# Try creating 50 concurrent evals
with ThreadPoolExecutor(max_workers=10) as ex:
    results = list(ex.map(lambda _: create_evaluation(), range(50)))
    print(f"Concurrent Creates: {sum(results)}/50 succeeded")
EOF
```

---

## Interpreting Results

### Response Time Standards
```
Excellent:   < 100ms
Good:        100-500ms
Acceptable:  500-1000ms
Slow:        > 1000ms
```

### Success Rate Standards
```
Excellent:   > 99%
Good:        95-99%
Acceptable:  90-95%
Poor:        < 90%
```

### Load Test Interpreation
```
Your target:  100-1000 requests/sec

Results:
- If > 1000 req/s:    ✅ Excellent
- If 500-1000 req/s:  ✅ Good
- If 100-500 req/s:   ⚠️  Acceptable
- If < 100 req/s:     ❌ Needs optimization
```

---

## Common Issues & Solutions

### Issue 1: "Connection refused"
```
Problem: Server not running
Solution: 
  cd /home/nour/python-project/dalil_group
  uvicorn web.main:app --reload --port 8000
```

### Issue 2: "Timeout" errors in tests
```
Problem: Server is slow or overloaded
Solution:
  - Check CPU/memory usage: top
  - Increase timeout in tests
  - Reduce concurrent workers
  - Check database performance
```

### Issue 3: High response times
```
Problem: Slow endpoints
Solution:
  - Profile with: python3 -m cProfile cli_eval.py run --help
  - Check database queries: Enable query logging
  - Cache results: Redis is configured
  - Optimize code: ProfileSQL queries
```

### Issue 4: 500 errors on specific routes
```
Problem: Application error
Solution:
  - Check logs: tail -f logs/*.log
  - Test endpoint: curl -i http://localhost:8000/route
  - Check dependencies: pip install -r requirements.txt
  - Validate config: Check .env variables
```

---

## Pre-Deployment Checklist

### Before Going to Production

- [ ] All 12 routes return 200 OK (Functional Test)
- [ ] Response times < 500ms average (Performance Test)
- [ ] Load test: > 500 req/s with < 1000 concurrent
- [ ] Health endpoint responds correctly
- [ ] Database migrations run successfully
- [ ] Environment variables configured
- [ ] HTTPS certificate obtained
- [ ] Nginx reverse proxy configured
- [ ] Systemd service files created
- [ ] Backup strategy implemented
- [ ] Monitoring alerts configured
- [ ] Rate limiting enabled
- [ ] Authentication working
- [ ] Error logging configured

---

## Running Tests in CI/CD

### Example GitHub Actions Workflow:
```yaml
name: Production Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.10
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Start server
        run: |
          uvicorn web.main:app --port 8000 &
          sleep 5
      
      - name: Run tests
        run: python3 test_production.py
      
      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v2
        with:
          name: test-report
          path: test_report.txt
```

---

## Monitoring Production

### Key Metrics to Monitor
```
✅ Uptime: Should be > 99.9%
✅ Response Time: P95 < 500ms
✅ Error Rate: < 0.1%
✅ CPU Usage: < 80%
✅ Memory Usage: < 85%
✅ Database Connections: < 90% pool
✅ Cache Hit Rate: > 70%
```

### Alerting Rules
```
- If response time P95 > 1000ms → Alert
- If error rate > 1% → Critical
- If CPU > 85% → Alert
- If Memory > 90% → Critical
- If downtime > 5 min → Critical
```

---

## Support & Troubleshooting

### Getting More Detailed Information

1. **View server logs:**
   ```bash
   tail -f /var/log/dalil_group/app.log
   ```

2. **Check resource usage:**
   ```bash
   top -p $(pgrep -f uvicorn)
   ```

3. **Monitor network:**
   ```bash
   netstat -tulpn | grep 8000
   ```

4. **Test specific endpoint:**
   ```bash
   curl -w "\n%{http_code}\n" http://localhost:8000/health
   ```

5. **Get detailed request info:**
   ```bash
   curl -v http://localhost:8000/
   ```

---

## Next Steps

After successful testing:

1. **Configure Nginx reverse proxy** - See PRODUCTION_DEPLOYMENT.md
2. **Set up SSL/TLS** - Use Let's Encrypt
3. **Configure systemd service** - Auto-start and monitoring
4. **Set up backups** - Database backups every 6 hours
5. **Configure monitoring** - Prometheus + Grafana
6. **Load test at scale** - Test with 5000+ concurrent users

For detailed production deployment steps, see:
- [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)
- [README_PRODUCTION.md](README_PRODUCTION.md)
- [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
