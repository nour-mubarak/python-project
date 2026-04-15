#!/usr/bin/env python3
"""
Quick Production Test - Rapid validation (5 minutes)
Tests: All routes, health check, response times
"""

import requests
import time
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000"
TIMEOUT = 10


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    END = "\033[0m"
    BOLD = "\033[1m"


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}\n")


def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def test_routes():
    """Test all critical routes"""
    print_header("QUICK ROUTE TEST")

    routes = [
        ("/", "Home"),
        ("/health", "Health Check"),
        ("/docs", "API Docs"),
        ("/services", "Services"),
        ("/sectors", "Sectors"),
        ("/evaluations/new", "Evaluation Wizard"),
        ("/auth/login", "Login"),
        ("/chat/", "Chat"),
    ]

    passed = 0
    failed = 0
    slow = 0

    for route, name in routes:
        try:
            start = time.time()
            response = requests.get(f"{BASE_URL}{route}", timeout=TIMEOUT)
            elapsed = time.time() - start

            if response.status_code == 200:
                if elapsed > 1.0:
                    print_warning(
                        f"{name:20s} - {response.status_code} ({elapsed*1000:.0f}ms SLOW)"
                    )
                    slow += 1
                else:
                    print_success(
                        f"{name:20s} - {response.status_code} ({elapsed*1000:.0f}ms)"
                    )
                passed += 1
            else:
                print_error(f"{name:20s} - HTTP {response.status_code}")
                failed += 1
        except requests.exceptions.Timeout:
            print_error(f"{name:20s} - TIMEOUT")
            failed += 1
        except Exception as e:
            print_error(f"{name:20s} - {type(e).__name__}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed, {slow} slow")
    return passed, failed, slow


def test_health():
    """Test health endpoint details"""
    print_header("HEALTH CHECK")

    try:
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)

        if response.status_code == 200:
            print_success("Health endpoint responding")
            try:
                data = response.json()
                for key, value in data.items():
                    if isinstance(value, bool):
                        status = "✅" if value else "❌"
                        print(f"  {status} {key}: {value}")
                    else:
                        print(f"  ℹ️  {key}: {value}")
            except:
                print(f"  Response: {response.text[:200]}")
        else:
            print_error(f"Health check returned {response.status_code}")
    except Exception as e:
        print_error(f"Could not reach health endpoint: {e}")


def test_performance():
    """Quick performance check"""
    print_header("PERFORMANCE CHECK")

    route = "/"
    times = []

    print("Testing 20 requests...")
    for i in range(20):
        try:
            start = time.time()
            response = requests.get(f"{BASE_URL}{route}", timeout=TIMEOUT)
            elapsed = time.time() - start

            if response.status_code == 200:
                times.append(elapsed * 1000)
                print(f"  {i+1:2d}. {elapsed*1000:6.1f}ms", end="")
                print(" ✅" if elapsed < 0.5 else " ⚠️")
        except:
            pass

    if times:
        avg = sum(times) / len(times)
        min_t = min(times)
        max_t = max(times)

        print(f"\nAverage: {avg:.1f}ms")
        print(f"Min: {min_t:.1f}ms, Max: {max_t:.1f}ms")

        if avg < 200:
            print_success("Performance is excellent")
        elif avg < 500:
            print_success("Performance is good")
        else:
            print_warning("Performance could be optimized")


def main():
    print_header("DALĪL GROUP - QUICK TEST")
    print(f"Server: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%H:%M:%S')}\n")

    # Check if server is running
    try:
        requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    except Exception as e:
        print_error(f"Server is not accessible: {e}")
        print("Please start the server with:")
        print("  cd /home/nour/python-project/dalil_group")
        print("  uvicorn web.main:app --port 8000")
        sys.exit(1)

    # Run tests
    passed, failed, slow = test_routes()
    test_health()
    test_performance()

    # Summary
    print_header("SUMMARY")

    if failed == 0 and passed > 0:
        print_success(f"✅ QUICK TEST PASSED - {passed} routes working")
        if slow > 0:
            print_warning(f"  ({slow} routes are slow - monitor performance)")
        sys.exit(0)
    else:
        print_error(f"⚠️  {failed} route(s) failed - see details above")
        sys.exit(1)


if __name__ == "__main__":
    main()
