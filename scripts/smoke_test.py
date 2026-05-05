import json

import httpx


def main() -> None:
    url = "http://127.0.0.1:8001/health"
    response = httpx.get(url, timeout=5)
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    main()
