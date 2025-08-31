#!/usr/bin/env python3
"""
Examples of how to use the rate limiter programmatically
"""

from todo.services.rate_limiter_service import rate_limiter_service


def example_basic_usage():
    """Basic example of checking rate limits"""
    print("=== Basic Rate Limiting Example ===")
    
    # Check if an IP is rate limited
    ip_address = "192.168.1.100"
    is_limited, data = rate_limiter_service.is_rate_limited(ip_address)
    
    if is_limited:
        print(f"IP {ip_address} is RATE LIMITED!")
        print(f"Current count: {data['current_count']}")
        print(f"Max allowed: {data['max_requests']}")
        print(f"Remaining: {data['remaining_requests']}")
    else:
        print(f"IP {ip_address} is NOT rate limited")
        print(f"Current count: {data['current_count']}")
        print(f"Remaining requests: {data['remaining_requests']}")
    
    print()


def example_get_rate_limit_info():
    """Example of getting rate limit information"""
    print("=== Rate Limit Information Example ===")
    
    ip_address = "10.0.0.50"
    info = rate_limiter_service.get_rate_limit_info(ip_address)
    
    print(f"Rate limit info for {ip_address}:")
    print(f"  Current count: {info['current_count']}")
    print(f"  Window weight: {info['window_weight']}")
    print(f"  Window size: {info['window_size_minutes']} minutes")
    print(f"  Requests per second: {info['requests_per_second']}")
    print(f"  Sliding scale factor: {info['sliding_scale_factor']}")
    print()


def example_update_rules():
    """Example of updating rate limiting rules"""
    print("=== Rule Update Example ===")
    
    # Update the default rule to be more restrictive
    success = rate_limiter_service.update_rule(
        "default",
        requests_per_second=60,  # Reduce from 120 to 60
        sliding_scale_factor=0.7  # Reduce from 0.8 to 0.7
    )
    
    if success:
        print("Successfully updated default rule")
        print("New settings:")
        print("  Requests per second: 60 (was 120)")
        print("  Sliding scale factor: 0.7 (was 0.8)")
    else:
        print("Failed to update rule")
    
    print()


def example_create_custom_rule():
    """Example of creating a custom rate limiting rule"""
    print("=== Custom Rule Creation Example ===")
    
    # Create a strict rule for sensitive endpoints
    success = rate_limiter_service.update_rule(
        "strict",
        window_size_minutes=1,      # 1-minute windows
        num_windows=5,              # 5 windows total
        requests_per_second=10,     # Only 10 requests per second
        sliding_scale_factor=0.5    # Very restrictive
    )
    
    if success:
        print("Successfully created 'strict' rule")
        print("Rule settings:")
        print("  Window size: 1 minute")
        print("  Number of windows: 5")
        print("  Total time span: 5 minutes")
        print("  Requests per second: 10")
        print("  Effective max requests: 300 (10 * 1 * 60 * 5 * 0.5)")
    else:
        print("Failed to create custom rule")
    
    print()


def example_multiple_identifiers():
    """Example of rate limiting multiple identifiers"""
    print("=== Multiple Identifiers Example ===")
    
    # Test rate limiting for different IP addresses
    test_ips = [
        "192.168.1.100",
        "10.0.0.50", 
        "172.16.0.25"
    ]
    
    for ip in test_ips:
        is_limited, data = rate_limiter_service.is_rate_limited(ip)
        status = "LIMITED" if is_limited else "OK"
        print(f"IP {ip}: {status} - Count: {data['current_count']}/{data['max_requests']}")
    
    print()


def example_rule_management():
    """Example of managing multiple rules"""
    print("=== Rule Management Example ===")
    
    # Create different rules for different use cases
    rules = {
        "public": {
            "window_size_minutes": 5,
            "num_windows": 3,
            "requests_per_second": 100,
            "sliding_scale_factor": 0.8
        },
        "authenticated": {
            "window_size_minutes": 5,
            "num_windows": 3,
            "requests_per_second": 200,
            "sliding_scale_factor": 0.9
        },
        "admin": {
            "window_size_minutes": 5,
            "num_windows": 3,
            "requests_per_second": 500,
            "sliding_scale_factor": 1.0
        }
    }
    
    for rule_name, rule_config in rules.items():
        success = rate_limiter_service.update_rule(rule_name, **rule_config)
        if success:
            print(f"Created rule '{rule_name}' with {rule_config['requests_per_second']} req/sec")
        else:
            print(f"Failed to create rule '{rule_name}'")
    
    print()


def example_error_handling():
    """Example of error handling in rate limiting"""
    print("=== Error Handling Example ===")
    
    try:
        # This might fail if MongoDB is not available
        ip_address = "127.0.0.1"
        is_limited, data = rate_limiter_service.is_rate_limited(ip_address)
        
        if 'error' in data:
            print(f"Rate limiting error: {data['error']}")
            print("Allowing request to proceed...")
        else:
            print(f"Rate limiting successful: {is_limited}")
            
    except Exception as e:
        print(f"Unexpected error in rate limiting: {e}")
        print("Allowing request to proceed...")
    
    print()


if __name__ == "__main__":
    print("Rate Limiter Usage Examples")
    print("=" * 50)
    print()
    
    # Run examples
    example_basic_usage()
    example_get_rate_limit_info()
    example_update_rules()
    example_create_custom_rule()
    example_multiple_identifiers()
    example_rule_management()
    example_error_handling()
    
    print("Examples completed!")
    print("\nNote: These examples assume the rate limiter service is properly configured")
    print("and MongoDB is accessible. Some operations may fail in test environments.")
