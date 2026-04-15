# Production Testing Toolkit - Quick Reference

## 📋 What's Included

Your Dalīl Group project now includes **4 comprehensive testing tools**:

| Tool | Purpose | Time | When to Use |
|------|---------|------|------------|
| `quick_test.py` | Smoke test | 5 min | After code changes |
| `test_production.py` | Full test suite | 20 min | Before production |
| `stress_test.py` | Load simulation | 12 min | Production readiness |
| `PRODUCTION_TESTING_GUIDE.md` | Reference guide | - | Troubleshooting |

---

## 🚀 Getting Started (First Time Setup)

### 1. Start Your Development Server
```bash
cd /home/nour/python-project/dalil_group
source ../.venv/bin/activate
uvicorn web.main:app --reload --port 8000
```

**Keep this terminal window open.** Open a new terminal for testing.

### 2. Run Quick Test (Recommended First)
```bash
cd /home/nour/python-project/dalil_group
python3 quick_test.py
```

**Expected output:**
```
✅ Home - 200 (45ms)
✅ Health Check - 200 (12ms)
✅ API Docs - 200 (23ms)
...
✅ QUICK TEST PASSED - 8 routes working
```

---

## 🧪 Testing Workflows

### Workflow 1: After Code Changes
```bash
python3 quick_test.py
```
- Takes 5 minutes
- Tests all critical routes
- Warns about slow endpoints
- Good for rapid validation

### Workflow 2: Pre-Production Validation
```bash
python3 test_production.py
```
- Takes 20 minutes
- Tests: Functionality, Performance, Load, Security, Integration
- Generates detailed report (`test_report.txt`)
- Comprehensive quality check

### Workflow 3: Production Load Testing
```bash
python3 stress_test.py
```
- Takes 12 minutes (ramp-up 1 min + sustained 10 min + ramp-down 1 min)
- Simulates 100 concurrent users
- Measures throughput and response times
- Tests system limits under load

### Workflow 4: Continuous Monitoring
```bash
# Test in a loop (every 5 minutes)
while true; do
    python3 quick_test.py
    sleep 300
done
```

---

## 📊 Understanding the Reports

### Quick Test Output
```
✅ Home                  - 200 (45ms)      ← Route is working, response time in parentheses
⚠️  Reports             - 200 (1250ms SLOW) ← Working but slow, consider optimization
❌ Unknown Route        - HTTP 404         ← Route not found
```

### Full Test Suite Output
The `test_production.py` generates `test_report.txt` with sections:
1. **Functionality** - Which routes work
2. **Performance** - Response time statistics
3. **Load Test** - How many req/s the system handles
4. **Security** - Security header checks
5. **Integration** - Health endpoint status

### Stress Test Output
```
Phase 1: Ramp Up (0-60 seconds)
  100% - 100 workers, 5234 requests, 98.5% success

Phase 2: Sustained Load (60-660 seconds)
  100% - 100 workers, 87452 requests, 0 errors, 145.7 req/s

Phase 3: Ramp Down (660-720 seconds)
  All workers stopped

Results:
  Throughput: 145.7 req/s
  P99 Latency: 234ms
  Success Rate: 98.7%
```

---

## ✅ Success Criteria

### Quick Test - All routes should return 200 OK
❌ If any route returns error → Fix the issue  
⚠️  If any route is slow (> 1000ms) → Monitor it  
✅ If all routes return 200 OK → Pass

### Full Test Suite - Target Success Rate
```
✅ 100% of routes working
✅ Average response < 500ms
✅ P95 response < 1000ms
✅ No security issues
```

### Stress Test - Production Load
```
✅ Throughput: > 100 req/s
✅ Success Rate: > 95%
✅ P99 Latency: < 1000ms
✅ CPU Usage: < 80%
```

---

## 🔍 Troubleshooting

### "Connection refused" Error
```
Problem: Server not running
Solution: 
  1. Open new terminal
  2. cd /home/nour/python-project/dalil_group
  3. uvicorn web.main:app --port 8000
```

### "Route returns 500 error"
```
Problem: Application crashed on that route
Solution:
  1. Check server terminal for error messages
  2. Run: curl -v http://localhost:8000/route
  3. Check logs: tail -f logs/app.log (if configured)
```

### "High response times (> 1000ms)"
```
Problem: Server is slow
Solution:
  1. Check CPU usage: top
  2. Check memory: free -h
  3. Check database: Is it connected?
  4. Try restarting server
```

### "Many timeouts in stress test"
```
Problem: Server can't handle load
Solution:
  1. Optimize code (profile with cProfile)
  2. Add caching (Redis is configured)
  3. Reduce concurrent workers in stress_test.py
  4. Check database connection pooling
```

---

## 💡 Best Practices

### Before Every Deployment
- [ ] Run `quick_test.py` - verify nothing broke
- [ ] Run `test_production.py` - full validation
- [ ] Check `test_report.txt` for any warnings
- [ ] Run `stress_test.py` - verify load capacity

### During Development
- Run `quick_test.py` after every major change
- Monitor response times
- Look for "SLOW" warnings
- Fix critical issues immediately

### Production Monitoring
- Set up automated testing (GitHub Actions)
- Run tests on a schedule (daily/weekly)
- Alert on test failures
- Track metrics over time

---

## 🔧 Advanced: Custom Testing

### Test a Specific Route
```python
import requests
response = requests.get('http://localhost:8000/evaluations/new')
print(f"Status: {response.status_code}")
print(f"Size: {len(response.content)} bytes")
print(f"Headers: {dict(response.headers)}")
```

### Load Test a Specific Endpoint
```bash
python3 << 'EOF'
import concurrent.futures
import requests
import time

def test():
    return requests.get('http://localhost:8000/health', timeout=5)

start = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
    results = list(ex.map(lambda _: test(), range(500)))
    success = sum(1 for r in results if r.status_code == 200)
    duration = time.time() - start
    
print(f"Success: {success}/500")
print(f"Throughput: {500/duration:.1f} req/s")
EOF
```

### Monitor Real-Time Performance
```bash
# Watch response times as they happen
while true; do
    time curl -s http://localhost:8000/ > /dev/null
    sleep 1
done
```

---

## 📈 Metrics to Track

### Response Times
- **Target**: P99 < 1000ms (99th percentile)
- **Excellent**: P99 < 200ms
- **Good**: P99 < 500ms
- **Acceptable**: P99 < 1000ms
- **Poor**: P99 > 1000ms

### Throughput
- **Target**: > 100 req/s for medium load
- **Excellent**: > 1000 req/s
- **Good**: > 500 req/s
- **Acceptable**: > 100 req/s
- **Poor**: < 100 req/s

### Error Rate
- **Target**: < 0.1%
- **Excellent**: 0%
- **Good**: < 0.5%
- **Acceptable**: < 1%
- **Poor**: > 1%

---

## 📚 Related Documentation

For more details, see:
- [PRODUCTION_TESTING_GUIDE.md](PRODUCTION_TESTING_GUIDE.md) - Complete testing guide
- [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) - Deployment instructions  
- [README_PRODUCTION.md](README_PRODUCTION.md) - Production setup
- [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - Pre-deployment checklist

---

## 🎯 Next Steps

1. **Run Quick Test**: `python3 quick_test.py`
2. **Fix Any Issues**: Check troubleshooting section
3. **Run Full Test**: `python3 test_production.py`
4. **Run Stress Test**: `python3 stress_test.py`
5. **Review Results**: Open `test_report.txt`
6. **Deploy**: Follow [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)

---

**Last Updated**: 2025  
**Version**: 1.0
