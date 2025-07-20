def retry(func, max_attempts=3, *args, **kwargs):
    last_exc = None
    for attempt in range(max_attempts):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            print(f"[RETRY] Attempt {attempt+1} failed: {exc}")
    raise last_exc
