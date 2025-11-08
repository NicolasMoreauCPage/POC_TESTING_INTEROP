# Helpers communs pour les tests UI Playwright
import time, pytest, httpx

def wait_for_ready(url: str, max_retries: int = 30, delay: float = 0.5):
    for i in range(max_retries):
        try:
            response = httpx.get(url, follow_redirects=True, timeout=5.0)
            if response.status_code < 400:
                return True
        except Exception:
            pass
        if i < max_retries - 1:
            time.sleep(delay)
    return False

def safe_navigate(page, url: str, timeout_ms: int = 10000):
    max_retries = 3
    for i in range(max_retries):
        try:
            response = page.goto(url, timeout=timeout_ms)
            if response and response.ok:
                return True
        except Exception as e:
            if i == max_retries - 1:
                pytest.fail(f"Failed to navigate to {url}: {str(e)}")
            time.sleep(1)
    return False
