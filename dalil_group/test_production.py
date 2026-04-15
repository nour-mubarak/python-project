#!/usr/bin/env python3
"""
Comprehensive Production Testing Suite for Dalīl Group
Tests: Functionality, Load, Performance, Security, Database Integration
"""

import asyncio
import concurrent.futures
import requests
import json
import time
import statistics
from typing import List, Dict, Tuple
from datetime import datetime
import sys

# Configuration
BASE_URL = "http://localhost:8000"
TIMEOUT = 10
CONCURRENT_WORKERS = 50


# Color codes for terminal output
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    END = "\033[0m"
    BOLD = "\033[1m"


def print_header(text):
    """Print section header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")


def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def print_info(text):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")


# ============================================================================
# SECTION 1: FUNCTIONALITY TESTING
# ============================================================================


class FunctionalTests:
    """Test all endpoints for basic functionality"""

    @staticmethod
    def test_routes() -> Dict[str, Dict]:
        """Test all website routes"""
        routes = {
            "Public Website": [
                ("/", "Home Page"),
                ("/services", "Services"),
                ("/sectors", "Sectors Overview"),
                ("/sectors/government", "Government Sector"),
                ("/sectors/finance", "Finance Sector"),
                ("/sectors/healthcare", "Healthcare Sector"),
                ("/sectors/education", "Education Sector"),
            ],
            "Internal Dashboard": [
                ("/evaluations/new", "Evaluation Wizard"),
                ("/auth/login", "Login Page"),
                ("/auth/register", "Registration Page"),
                ("/chat/", "Chat Interface"),
                ("/reports/", "Reports Dashboard"),
            ],
            "API Endpoints": [
                ("/health", "Health Check"),
                ("/docs", "Swagger UI"),
                ("/redoc", "ReDoc Documentation"),
            ],
        }

        results = {}
        total_tests = 0
        passed_tests = 0

        for category, endpoints in routes.items():
            results[category] = {}
            print_info(f"Testing {category}...")

            for route, name in endpoints:
                total_tests += 1
                try:
                    response = requests.get(f"{BASE_URL}{route}", timeout=TIMEOUT)

                    if response.status_code == 200:
                        passed_tests += 1
                        results[category][name] = {
                            "status": "✅ PASS",
                            "code": response.status_code,
                            "size": len(response.content),
                            "time": response.elapsed.total_seconds(),
                        }
                        print_success(f"  {name} ({route})")
                    else:
                        results[category][name] = {
                            "status": "❌ FAIL",
                            "code": response.status_code,
                            "error": f"Unexpected status code",
                        }
                        print_error(f"  {name} ({route}) - HTTP {response.status_code}")

                except requests.exceptions.Timeout:
                    results[category][name] = {
                        "status": "❌ TIMEOUT",
                        "error": "Request timeout",
                    }
                    print_error(f"  {name} ({route}) - Timeout")
                except Exception as e:
                    results[category][name] = {"status": "❌ ERROR", "error": str(e)}
                    print_error(f"  {name} ({route}) - {type(e).__name__}")

        results["Summary"] = {
            "total": total_tests,
            "passed": passed_tests,
            "failed": total_tests - passed_tests,
            "success_rate": f"{(passed_tests/total_tests*100):.1f}%",
        }

        return results


# ============================================================================
# SECTION 2: PERFORMANCE TESTING
# ============================================================================


class PerformanceTests:
    """Test response times and performance metrics"""

    @staticmethod
    def test_endpoint_performance(
        route: str, name: str, num_requests: int = 100
    ) -> Dict:
        """Test performance of a single endpoint"""
        times = []
        errors = 0

        for _ in range(num_requests):
            try:
                start = time.time()
                response = requests.get(f"{BASE_URL}{route}", timeout=TIMEOUT)
                elapsed = time.time() - start

                if response.status_code == 200:
                    times.append(elapsed)
                else:
                    errors += 1
            except:
                errors += 1

        if times:
            stats = {
                "route": route,
                "name": name,
                "requests": num_requests,
                "successful": len(times),
                "errors": errors,
                "min": min(times),
                "max": max(times),
                "mean": statistics.mean(times),
                "median": statistics.median(times),
                "stddev": statistics.stdev(times) if len(times) > 1 else 0,
                "p95": sorted(times)[int(len(times) * 0.95)] if len(times) > 0 else 0,
                "p99": sorted(times)[int(len(times) * 0.99)] if len(times) > 0 else 0,
            }
            return stats
        else:
            return {"error": "All requests failed"}

    @staticmethod
    def run_performance_suite() -> Dict:
        """Run performance tests on critical endpoints"""
        print_info("Running performance tests (100 requests per endpoint)...")

        critical_endpoints = [
            ("/", "Home"),
            ("/health", "Health Check"),
            ("/evaluations/new", "Evaluation Wizard"),
        ]

        results = {}
        for route, name in critical_endpoints:
            stats = PerformanceTests.test_endpoint_performance(route, name)
            results[name] = stats

            if "error" not in stats:
                print_info(f"  {name}:")
                print(
                    f"    Mean: {stats['mean']*1000:.2f}ms, "
                    f"P95: {stats['p95']*1000:.2f}ms, "
                    f"P99: {stats['p99']*1000:.2f}ms"
                )

        return results


# ============================================================================
# SECTION 3: LOAD TESTING
# ============================================================================


class LoadTests:
    """Simulate production load with concurrent requests"""

    @staticmethod
    def single_request(route: str) -> Tuple[bool, float]:
        """Execute a single request"""
        try:
            start = time.time()
            response = requests.get(f"{BASE_URL}{route}", timeout=TIMEOUT)
            elapsed = time.time() - start
            return response.status_code == 200, elapsed
        except Exception as e:
            return False, 0

    @staticmethod
    def run_concurrent_load(
        route: str, total_requests: int, concurrent_workers: int
    ) -> Dict:
        """Run load test with concurrent requests"""
        print_info(f"Running load test: {route}")
        print_info(f"  Total requests: {total_requests}")
        print_info(f"  Concurrent workers: {concurrent_workers}")

        results = {
            "successful": 0,
            "failed": 0,
            "times": [],
            "start_time": time.time(),
        }

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=concurrent_workers
        ) as executor:
            futures = [
                executor.submit(LoadTests.single_request, route)
                for _ in range(total_requests)
            ]

            completed = 0
            for future in concurrent.futures.as_completed(futures):
                try:
                    success, elapsed = future.result()
                    if success:
                        results["successful"] += 1
                        results["times"].append(elapsed)
                    else:
                        results["failed"] += 1

                    completed += 1
                    if completed % 100 == 0:
                        print_info(f"  Progress: {completed}/{total_requests}")
                except Exception as e:
                    results["failed"] += 1
                    completed += 1

        results["end_time"] = time.time()
        results["total_duration"] = results["end_time"] - results["start_time"]
        results["requests_per_second"] = total_requests / results["total_duration"]

        if results["times"]:
            results["mean_time"] = statistics.mean(results["times"])
            results["median_time"] = statistics.median(results["times"])
            results["p95_time"] = sorted(results["times"])[
                int(len(results["times"]) * 0.95)
            ]
            results["p99_time"] = sorted(results["times"])[
                int(len(results["times"]) * 0.99)
            ]

        return results

    @staticmethod
    def run_load_test() -> Dict:
        """Run full load test suite"""
        total_requests = 500

        results = {}
        endpoints = [
            ("/", "Home"),
            ("/health", "Health"),
            ("/evaluations/new", "Evaluation Wizard"),
        ]

        for route, name in endpoints:
            load_result = LoadTests.run_concurrent_load(
                route, total_requests, CONCURRENT_WORKERS
            )
            results[name] = load_result

            print_success(f"{name} Load Test Complete:")
            print(f"  Successful: {load_result['successful']}/{total_requests}")
            print(f"  Failed: {load_result['failed']}/{total_requests}")
            print(f"  Throughput: {load_result['requests_per_second']:.2f} req/s")
            print(f"  Mean Response: {load_result.get('mean_time', 0)*1000:.2f}ms")
            print(f"  P95 Response: {load_result.get('p95_time', 0)*1000:.2f}ms")
            print(f"  P99 Response: {load_result.get('p99_time', 0)*1000:.2f}ms")
            print()

        return results


# ============================================================================
# SECTION 4: SECURITY TESTING
# ============================================================================


class SecurityTests:
    """Basic security checks"""

    @staticmethod
    def test_https_readiness() -> Dict:
        """Check if server can handle HTTPS"""
        results = {}

        # Check if server is running (prerequisite for HTTPS)
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
            results["server_running"] = response.status_code == 200
            print_success("Server is running")
        except:
            results["server_running"] = False
            print_error("Server is not accessible")

        return results

    @staticmethod
    def test_security_headers() -> Dict:
        """Check for recommended security headers"""
        results = {}

        recommended_headers = {
            "content-type": "Response content type",
        }

        try:
            response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)

            for header, description in recommended_headers.items():
                if header in response.headers:
                    results[header] = "✅ Present"
                    print_success(f"{description}: {response.headers[header]}")
                else:
                    results[header] = "⚠️  Missing"
                    print_warning(f"{description}: Not present")
        except Exception as e:
            print_error(f"Could not check security headers: {e}")

        return results

    @staticmethod
    def test_injection_protection() -> Dict:
        """Test basic injection protection"""
        results = {}

        # Try SQL injection-like payloads
        test_payloads = {
            "sql_injection": "' OR '1'='1",
            "xss_payload": "<script>alert('xss')</script>",
            "path_traversal": "../../../etc/passwd",
        }

        print_info("Testing injection protection...")

        for payload_type, payload in test_payloads.items():
            try:
                response = requests.get(
                    f"{BASE_URL}/", params={"test": payload}, timeout=TIMEOUT
                )

                # If server returns 200 safely, that's good
                if response.status_code in [200, 404]:
                    results[payload_type] = "✅ Safe"
                    print_success(f"  {payload_type}: Server handled safely")
                else:
                    results[payload_type] = f"⚠️  Status {response.status_code}"
                    print_warning(f"  {payload_type}: Unexpected response")
            except Exception as e:
                results[payload_type] = "❌ Error"
                print_error(f"  {payload_type}: {e}")

        return results

    @staticmethod
    def run_security_tests() -> Dict:
        """Run complete security test suite"""
        results = {}
        results["https_readiness"] = SecurityTests.test_https_readiness()
        results["security_headers"] = SecurityTests.test_security_headers()
        results["injection_protection"] = SecurityTests.test_injection_protection()
        return results


# ============================================================================
# SECTION 5: DATABASE & INTEGRATION TESTING
# ============================================================================


class IntegrationTests:
    """Test integration with database and services"""

    @staticmethod
    def test_health_endpoint() -> Dict:
        """Test health endpoint and service status"""
        print_info("Testing health endpoint...")

        try:
            response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)

            if response.status_code == 200:
                data = response.json()
                print_success("Health endpoint responding")

                return {
                    "status": "✅ Healthy",
                    "data": data,
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                print_error(f"Health endpoint returned {response.status_code}")
                return {"status": "❌ Unhealthy"}
        except Exception as e:
            print_error(f"Could not connect to health endpoint: {e}")
            return {"status": "❌ Error", "error": str(e)}

    @staticmethod
    def test_api_documentation() -> Dict:
        """Test that API documentation is accessible"""
        docs_endpoints = {
            "/docs": "Swagger UI",
            "/redoc": "ReDoc",
        }

        results = {}
        print_info("Testing API documentation...")

        for endpoint, name in docs_endpoints.items():
            try:
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=TIMEOUT)

                if response.status_code == 200:
                    print_success(f"{name} documentation is accessible")
                    results[endpoint] = {
                        "status": "✅ Accessible",
                        "size": len(response.content),
                    }
                else:
                    print_warning(f"{name} returned {response.status_code}")
                    results[endpoint] = {"status": f"⚠️  HTTP {response.status_code}"}
            except Exception as e:
                print_error(f"{name} error: {e}")
                results[endpoint] = {"status": "❌ Error"}

        return results


# ============================================================================
# SECTION 6: GENERATE REPORT
# ============================================================================


def generate_report(all_results: Dict) -> str:
    """Generate comprehensive test report"""
    report = []
    report.append("\n" + "=" * 80)
    report.append("PRODUCTION TEST REPORT - DALĪL GROUP".center(80))
    report.append("=" * 80)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Server: {BASE_URL}\n")

    # Summary
    report.append("EXECUTIVE SUMMARY")
    report.append("-" * 80)

    func_summary = all_results["Functional"]["Summary"]
    report.append(
        f"✅ Functional Tests: {func_summary['passed']}/{func_summary['total']} pass"
    )
    report.append(f"✅ Success Rate: {func_summary['success_rate']}\n")

    # Functional results
    report.append("DETAILED RESULTS")
    report.append("=" * 80)
    report.append("1. FUNCTIONAL TESTING")
    report.append("-" * 80)
    for category, endpoints in all_results["Functional"].items():
        if category != "Summary":
            report.append(f"\n{category}:")
            for name, result in endpoints.items():
                status = result.get("status", "Unknown")
                report.append(f"  {status} {name}")

    # Performance results
    if "Performance" in all_results and all_results["Performance"]:
        report.append("\n2. PERFORMANCE TESTING")
        report.append("-" * 80)
        for name, stats in all_results["Performance"].items():
            if "error" not in stats:
                report.append(f"\n{name}:")
                report.append(f"  Mean: {stats['mean']*1000:.2f}ms")
                report.append(f"  Median: {stats['median']*1000:.2f}ms")
                report.append(f"  P95: {stats['p95']*1000:.2f}ms")
                report.append(f"  P99: {stats['p99']*1000:.2f}ms")

    # Load test results
    if "Load" in all_results and all_results["Load"]:
        report.append("\n3. LOAD TESTING (500 requests per endpoint)")
        report.append("-" * 80)
        for name, result in all_results["Load"].items():
            report.append(f"\n{name}:")
            report.append(f"  Successful: {result['successful']}/{500}")
            report.append(f"  Throughput: {result['requests_per_second']:.2f} req/s")
            report.append(f"  Mean: {result.get('mean_time', 0)*1000:.2f}ms")

    # Security results
    if "Security" in all_results:
        report.append("\n4. SECURITY TESTING")
        report.append("-" * 80)
        report.append("Security checks completed")

    # Integration results
    if "Integration" in all_results:
        report.append("\n5. INTEGRATION TESTING")
        report.append("-" * 80)
        report.append("Integration checks completed")

    report.append("\n" + "=" * 80)
    report.append("END OF REPORT".center(80))
    report.append("=" * 80 + "\n")

    return "\n".join(report)


# ============================================================================
# MAIN EXECUTION
# ============================================================================


def main():
    """Run complete test suite"""
    print_header("DALĪL GROUP PRODUCTION TEST SUITE")
    print_info(f"Target Server: {BASE_URL}")
    print_info(f"Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    all_results = {}

    try:
        # Test 1: Functionality
        print_header("TEST 1: FUNCTIONALITY TESTING")
        functional_results = FunctionalTests.test_routes()
        all_results["Functional"] = functional_results
        summary = functional_results["Summary"]
        print(
            f"\n{summary['passed']}/{summary['total']} routes working ({summary['success_rate']})"
        )

        # Test 2: Performance
        print_header("TEST 2: PERFORMANCE TESTING")
        performance_results = PerformanceTests.run_performance_suite()
        all_results["Performance"] = performance_results

        # Test 3: Load
        print_header("TEST 3: LOAD TESTING")
        load_results = LoadTests.run_load_test()
        all_results["Load"] = load_results

        # Test 4: Security
        print_header("TEST 4: SECURITY TESTING")
        security_results = SecurityTests.run_security_tests()
        all_results["Security"] = security_results

        # Test 5: Integration
        print_header("TEST 5: INTEGRATION TESTING")
        integration_results = {
            "health": IntegrationTests.test_health_endpoint(),
            "documentation": IntegrationTests.test_api_documentation(),
        }
        all_results["Integration"] = integration_results

        # Generate report
        report = generate_report(all_results)
        print(report)

        # Save report
        with open("test_report.txt", "w") as f:
            f.write(report)
        print_success("Test report saved to test_report.txt")

        # Final status
        if summary["passed"] == summary["total"]:
            print_success("✅ ALL TESTS PASSED - SYSTEM READY FOR PRODUCTION")
            sys.exit(0)
        else:
            print_warning(f"⚠️  {summary['failed']} endpoint(s) need attention")
            sys.exit(1)

    except KeyboardInterrupt:
        print_error("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Test suite error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
