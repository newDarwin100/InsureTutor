"""Small OpenAI API connectivity check; run with python3 scripts/smoke_test.py."""

import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"


def read_api_key() -> str:
    if not ENV_FILE.exists():
        raise SystemExit("Missing .env file. Copy .env.example and add your API key.")

    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        name, separator, value = line.partition("=")
        if separator and name.strip() == "OPENAI_API_KEY":
            key = value.strip().strip('"\'')
            if key:
                return key
    raise SystemExit("OPENAI_API_KEY is empty in .env.")


def main() -> None:
    key = read_api_key()
    payload = json.dumps(
        {
            "model": "gpt-5.6-luna",
            "input": "请只回复：连接成功",
            "reasoning": {"effort": "none"},
            "max_output_tokens": 40,
            "store": False,
        }
    ).encode("utf-8")
    request = Request(
        "https://api.openai.com/v1/responses",
        data=payload,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
    except HTTPError as error:
        raise SystemExit(f"API request failed with HTTP {error.code}.") from None
    except URLError:
        raise SystemExit("Could not reach the OpenAI API.") from None

    answer = "".join(
        part.get("text", "")
        for item in result.get("output", [])
        for part in item.get("content", [])
        if part.get("type") == "output_text"
    )
    if not answer:
        raise SystemExit("API responded, but returned no text.")
    print(f"API OK — model: {result.get('model', 'unknown')}")
    print(f"Reply: {answer}")


if __name__ == "__main__":
    main()
