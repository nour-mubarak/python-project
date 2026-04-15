#!/usr/bin/env python3
"""
Stress Test - Simulate production load (30 minutes)
Tests: High concurrency, sustained load, error handling
"""

import asyncio
import httpx
import time
import statistics
from datetime import datetime, timedelta
import sys

BASE_URL = "http://localhost:8000"
TIMEOUT = 30


class StressTestConfig:
    """Configuration for stress testing"""

    RAMP_UP_TIME = 60  # Seconds to reach full load
    SUSTAINED_TIME = 600  # 10 minutes of sustained load
    RAMP_DOWN_TIME = 60  # Seconds to reduce load

    # Load levels
    INITIAL_WORKERS = 10
    MAX_WORKERS = 100  # Target: 100 concurrent users

    # Test endpoints
    ENDPOINTS = [
        "/",
        "/health",
        "/evaluations/new",
        "/services",
    ]


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    END = "\033[0m"
    BOLD = "\033[1m"


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")


def print_progress(text):
    print(f"{Colors.BLUE}➤ {text}{Colors.END}")


def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


class StressTestStats:
    """Track statistics during stress test"""

    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.response_times = []
        self.errors_by_type = {}
        self.start_time = None
        self.end_time = None

    def add_request(self, success: bool, response_time: float, error: str = None):
        self.total_requests += 1
        if success:
            self.successful_requests += 1
            self.response_times.append(response_time)
        else:
            self.failed_requests += 1
            if error:
                self.errors_by_type[error] = self.errors_by_type.get(error, 0) + 1

    def print_summary(self):
        duration = (self.end_time - self.start_time).total_seconds()

        print(f"\nTotal Requests: {self.total_requests}")
        print(
            f"Successful: {self.successful_requests} ({self.successful_requests/self.total_requests*100:.1f}%)"
        )
        print(
            f"Failed: {self.failed_requests} ({self.failed_requests/self.total_requests*100:.1f}%)"
        )
        print(f"Duration: {duration:.1f}s")
        print(f"Throughput: {self.total_requests/duration:.1f} req/s")

        if self.response_times:
            print(f"\nResponse Times:")
            print(f"  Min: {min(self.response_times)*1000:.1f}ms")
            print(f"  Max: {max(self.response_times)*1000:.1f}ms")
            print(f"  Mean: {statistics.mean(self.response_times)*1000:.1f}ms")
            print(f"  Median: {statistics.median(self.response_times)*1000:.1f}ms")
            print(f"  StdDev: {statistics.stdev(self.response_times)*1000:.1f}ms")

            p95 = sorted(self.response_times)[int(len(self.response_times) * 0.95)]
            p99 = sorted(self.response_times)[int(len(self.response_times) * 0.99)]
            print(f"  P95: {p95*1000:.1f}ms")
            print(f"  P99: {p99*1000:.1f}ms")

        if self.errors_by_type:
            print(f"\nErrors:")
            for error_type, count in self.errors_by_type.items():
                print(f"  {error_type}: {count}")


async def make_request(client: httpx.AsyncClient, endpoint: str) -> tuple:
    """Make a single HTTP request"""
    try:
        start = time.time()
        response = await client.get(f"{BASE_URL}{endpoint}", timeout=TIMEOUT)
        elapsed = time.time() - start

        if response.status_code == 200:
            return True, elapsed, None
        else:
            return False, elapsed, f"HTTP {response.status_code}"

    except asyncio.TimeoutError:
        return False, TIMEOUT, "Timeout"
    except Exception as e:
        return False, 0, type(e).__name__


async def worker(client: httpx.AsyncClient, endpoint: str, stats: StressTestStats):
    """Worker that continuously makes requests"""
    while True:
        success, response_time, error = await make_request(client, endpoint)
        stats.add_request(success, response_time, error)


async def run_stress_test():
    """Run complete stress test"""
    print_header("STRESS TEST - PRODUCTION LOAD SIMULATION")

    config = StressTestConfig()
    stats = StressTestStats()
    stats.start_time = datetime.now()

    print(f"Configuration:")
    print(f"  Max Workers: {config.MAX_WORKERS}")
    print(f"  Ramp-up: {config.RAMP_UP_TIME}s")
    print(f"  Sustained: {config.SUSTAINED_TIME}s")
    print(f"  Endpoints: {', '.join(config.ENDPOINTS)}\n")

    async with httpx.AsyncClient() as client:
        tasks = []
        current_workers = config.INITIAL_WORKERS

        # Phase 1: Ramp up
        print_header("PHASE 1: RAMP UP (0-60 seconds)")
        start_phase1 = time.time()

        # Create initial workers
        for endpoint in config.ENDPOINTS:
            for _ in range(config.INITIAL_WORKERS):
                task = asyncio.create_task(worker(client, endpoint, stats))
                tasks.append(task)

        # Gradually increase load
        while time.time() - start_phase1 < config.RAMP_UP_TIME:
            elapsed = time.time() - start_phase1

            # Calculate target workers for this point
            target = int(
                config.INITIAL_WORKERS
                + (config.MAX_WORKERS - config.INITIAL_WORKERS)
                * (elapsed / config.RAMP_UP_TIME)
            )

            # Add new workers if needed
            while current_workers < target:
                endpoint = config.ENDPOINTS[current_workers % len(config.ENDPOINTS)]
                task = asyncio.create_task(worker(client, endpoint, stats))
                tasks.append(task)
                current_workers += 1

            # Print progress
            pct = int(elapsed / config.RAMP_UP_TIME * 100)
            print(
                f"\r  {pct:3d}% - {current_workers} workers, "
                f"{stats.total_requests} requests, "
                f"{stats.successful_requests/max(1, stats.total_requests)*100:.1f}% success",
                end="",
                flush=True,
            )

            await asyncio.sleep(1)

        print()  # Newline after progress

        # Phase 2: Sustained load
        print_header("PHASE 2: SUSTAINED LOAD (60-660 seconds)")
        start_phase2 = time.time()

        while time.time() - start_phase2 < config.SUSTAINED_TIME:
            elapsed = time.time() - start_phase2
            pct = int(elapsed / config.SUSTAINED_TIME * 100)

            print(
                f"\r  {pct:3d}% - {current_workers} workers, "
                f"{stats.total_requests} requests, "
                f"{stats.failed_requests} errors, "
                f"{stats.total_requests/(elapsed+1):.1f} req/s",
                end="",
                flush=True,
            )

            await asyncio.sleep(5)

        print()  # Newline after progress

        # Phase 3: Ramp down
        print_header("PHASE 3: RAMP DOWN (660-720 seconds)")

        # Cancel all tasks
        for task in tasks:
            task.cancel()

        # Wait for cancellation
        await asyncio.gather(*tasks, return_exceptions=True)

        print_success("All workers stopped")

    # Record end time and print results
    stats.end_time = datetime.now()

    print_header("TEST RESULTS")
    stats.print_summary()

    # Recommendations
    print_header("RECOMMENDATIONS")

    success_rate = stats.successful_requests / max(1, stats.total_requests) * 100

    if success_rate >= 99:
        print_success("✅ System is performing excellently under load")
    elif success_rate >= 95:
        print_success("✅ System is performing well under load")
    elif success_rate >= 90:
        print_warning("⚠️  System is acceptable but consider optimization")
    else:
        print_error("❌ System needs optimization for production")

    if stats.response_times:
        p99 = sorted(stats.response_times)[int(len(stats.response_times) * 0.99)] * 1000

        if p99 < 500:
            print_success(f"✅ P99 latency is excellent: {p99:.1f}ms")
        elif p99 < 1000:
            print_success(f"✅ P99 latency is good: {p99:.1f}ms")
        else:
            print_warning(
                f"⚠️  P99 latency is high: {p99:.1f}ms - consider optimization"
            )

    throughput = (
        stats.total_requests / (stats.end_time - stats.start_time).total_seconds()
    )
    print(f"\nSystemThroughput: {throughput:.1f} req/s")

    if throughput >= 500:
        print_success("✅ System can handle medium production load")
    elif throughput >= 100:
        print_warning("⚠️  System can handle light production load")
    else:
        print_error("❌ System is under-powered for production")


def main():
    try:
        asyncio.run(run_stress_test())
    except KeyboardInterrupt:
        print_error("\nStress test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}")
    main()
    print(f"Completed: {datetime.now().strftime('%H:%M:%S')}")
