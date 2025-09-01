#!/usr/bin/env python3
"""
Utility script to test the rate limiter functionality
Run this script to simulate multiple requests and test rate limiting
"""

import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed


def make_request(url, request_id):
    """Make a single HTTP request and return the result"""
    try:
        start_time = time.time()
        response = requests.get(url, timeout=10)
        end_time = time.time()

        result = {
            "request_id": request_id,
            "status_code": response.status_code,
            "response_time": end_time - start_time,
            "headers": dict(response.headers),
            "rate_limited": response.status_code == 429,
        }

        if response.status_code == 429:
            try:
                result["error_data"] = response.json()
            except Exception:
                result["error_data"] = response.text

        return result

    except Exception as e:
        return {"request_id": request_id, "error": str(e), "rate_limited": False}


def test_rate_limiting(url, num_requests=150, concurrent_requests=10, delay_between_batches=1):
    """
    Test rate limiting by making multiple concurrent requests

    Args:
        url: The URL to test
        num_requests: Total number of requests to make
        concurrent_requests: Number of concurrent requests per batch
        delay_between_batches: Delay between batches in seconds
    """
    print(f"Testing rate limiting for: {url}")
    print(f"Total requests: {num_requests}")
    print(f"Concurrent requests per batch: {concurrent_requests}")
    print(f"Delay between batches: {delay_between_batches}s")
    print("=" * 60)

    all_results = []
    successful_requests = 0
    rate_limited_requests = 0
    failed_requests = 0

    # Make requests in batches
    for batch_num in range(0, num_requests, concurrent_requests):
        batch_start = batch_num + 1
        batch_end = min(batch_num + concurrent_requests, num_requests)

        print(f"\nBatch {batch_num // concurrent_requests + 1}: Requests {batch_start}-{batch_end}")

        # Make concurrent requests for this batch
        with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = [executor.submit(make_request, url, i) for i in range(batch_start, batch_end + 1)]

            batch_results = []
            for future in as_completed(futures):
                result = future.result()
                batch_results.append(result)
                all_results.append(result)

                if result.get("rate_limited"):
                    rate_limited_requests += 1
                    print(f"  Request {result['request_id']}: RATE LIMITED (429)")
                elif "error" in result:
                    failed_requests += 1
                    print(f"  Request {result['request_id']}: FAILED - {result['error']}")
                else:
                    successful_requests += 1
                    print(f"  Request {result['request_id']}: SUCCESS ({result['status_code']})")

        # Add delay between batches
        if batch_num + concurrent_requests < num_requests:
            print(f"  Waiting {delay_between_batches}s before next batch...")
            time.sleep(delay_between_batches)

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total requests: {num_requests}")
    print(f"Successful requests: {successful_requests}")
    print(f"Rate limited requests: {rate_limited_requests}")
    print(f"Failed requests: {failed_requests}")
    print(f"Success rate: {(successful_requests/num_requests)*100:.1f}%")
    print(f"Rate limit hit rate: {(rate_limited_requests/num_requests)*100:.1f}%")

    # Show rate limit headers from successful requests
    successful_results = [r for r in all_results if not r.get("rate_limited") and "error" not in r]
    if successful_results:
        print("\nRate limit headers from successful requests:")
        for key in ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]:
            values = [r["headers"].get(key, "N/A") for r in successful_results[:3]]  # Show first 3
            print(f"  {key}: {values}")

    # Show error details for rate limited requests
    if rate_limited_requests > 0:
        print("\nRate limit error details:")
        rate_limited_results = [r for r in all_results if r.get("rate_limited")]
        for result in rate_limited_results[:3]:  # Show first 3
            if "error_data" in result:
                print(f"  Request {result['request_id']}: {result['error_data']}")

    return all_results


def test_specific_scenarios(url):
    """Test specific rate limiting scenarios"""
    print("\n" + "=" * 60)
    print("TESTING SPECIFIC SCENARIOS")
    print("=" * 60)

    # Test 1: Single request to see headers
    print("\n1. Single request test:")
    result = make_request(url, "single")
    if "error" not in result:
        print(f"   Status: {result['status_code']}")
        for key in ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]:
            print(f"   {key}: {result['headers'].get(key, 'N/A')}")

    # Test 2: Burst of requests
    print("\n2. Burst test (50 concurrent requests):")
    test_rate_limiting(url, num_requests=50, concurrent_requests=50, delay_between_batches=0)

    # Test 3: Sustained load
    print("\n3. Sustained load test (200 requests over time):")
    test_rate_limiting(url, num_requests=200, concurrent_requests=20, delay_between_batches=2)


if __name__ == "__main__":
    # Configuration
    TEST_URL = "http://localhost:8000/api/tasks/"  # Adjust this URL as needed

    print("Rate Limiter Test Utility")
    print("Make sure your Django server is running before starting the test")
    print(f"Testing URL: {TEST_URL}")

    try:
        # Test basic connectivity
        print("\nTesting basic connectivity...")
        response = requests.get(TEST_URL, timeout=5)
        print(f"Server response: {response.status_code}")

        if response.status_code in [200, 401, 403]:  # Acceptable responses
            # Run tests
            test_specific_scenarios(TEST_URL)
        else:
            print(f"Unexpected response: {response.status_code}")
            print("Please check if the server is running and the URL is correct")

    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the server")
        print("Please make sure your Django server is running")
    except Exception as e:
        print(f"ERROR: {e}")
