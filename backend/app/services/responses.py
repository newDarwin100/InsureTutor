"""Bounded Responses API calls; no retries, tools, persistence or secret logging."""
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ModelError(RuntimeError):
    pass


class Responses:
    def __init__(self):
        self.model = os.getenv('LLM_MODEL', 'gpt-5.6-luna')

    def structured(self, instructions, payload, output_type):
        key = os.getenv('OPENAI_API_KEY', '').strip()
        if not key or key == 'your_openai_api_key_here':
            raise ModelError('Model credentials are unavailable')
        body = {'model': self.model, 'instructions': instructions,
                'input': json.dumps(payload, ensure_ascii=False), 'store': False,
                'reasoning': {'effort': 'none'}, 'max_output_tokens': 2400,
                'text': {'format': {'type': 'json_schema', 'name': output_type.__name__,
                                   'strict': True, 'schema': output_type.model_json_schema()}}}
        request = Request('https://api.openai.com/v1/responses', data=json.dumps(body).encode(),
                          headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})
        started = time.perf_counter()
        try:
            with urlopen(request, timeout=45) as response:
                result = json.load(response)
        except HTTPError as exc:
            raise ModelError(f'Model API returned HTTP {exc.code}') from None
        except (URLError, TimeoutError, ValueError, OSError):
            raise ModelError('Model request failed') from None
        if result.get('status') != 'completed':
            raise ModelError('Model response was incomplete')
        content = [c for item in result.get('output', []) for c in item.get('content', [])]
        if any(c.get('type') == 'refusal' for c in content):
            raise ModelError('Model declined the structured response')
        text = ''.join(c['text'] for c in content if c.get('type') == 'output_text')
        try:
            parsed = output_type.model_validate_json(text)
        except ValueError:
            raise ModelError('Model response did not match the required format') from None
        usage = result.get('usage', {})
        return parsed, {'ms': round((time.perf_counter()-started)*1000, 2),
                        'input_tokens': usage.get('input_tokens', 0),
                        'output_tokens': usage.get('output_tokens', 0)}
