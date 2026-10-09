"""Bounded Responses API calls; no retries, tools, persistence or secret logging."""
import json
import os
import time
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from app.services.answer_text import answer_text


class ModelError(RuntimeError):
    pass


def sse_events(response):
    """Read SSE data frames, including comments, CRLF and multiline data."""
    data = []
    for raw in response:
        line = raw.decode('utf-8').rstrip('\r\n')
        if not line:
            if data:
                value = '\n'.join(data)
                if value != '[DONE]':
                    yield json.loads(value)
                data = []
        elif line.startswith('data:'):
            data.append(line[5:].lstrip(' '))
    if data:
        yield json.loads('\n'.join(data))


class ClaimTextStream:
    """Expose only claim text from an incomplete structured JSON response, never raw JSON."""
    def __init__(self, emit, language=None):
        self.emit, self.buffer, self.seen = emit, '', {}
        self.language = language

    def feed(self, delta):
        self.buffer += delta
        if len(self.buffer) > 100000:
            raise ModelError('Stream exceeded the response budget')
        action = re.search(r'"action"\s*:\s*"(answered|source_conflict)"', self.buffer)
        if not action or '"claims"' not in self.buffer:
            return
        # Complete escapes only: a cut Unicode escape must wait for the next delta.
        for index, match in enumerate(re.finditer(r'(?<!\\)"text"\s*:\s*"((?:[^"\\]|\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))*)', self.buffer)):
            text = json.loads('"' + match.group(1) + '"')
            # A high surrogate at a chunk boundary is not displayable yet.
            if text and 0xD800 <= ord(text[-1]) <= 0xDBFF:
                text = text[:-1]
            # Phrase conversion can revise an earlier character once more context arrives.
            # A replacement updates that paragraph without discarding the other streamed text.
            text = answer_text(text, self.language, partial=True)
            previous = self.seen.get(index, '')
            if text != previous:
                if text.startswith(previous):
                    self.emit('delta', {'index': index, 'text': text[len(previous):]})
                else:
                    self.emit('delta', {'index': index, 'text': text, 'replace': True})
                self.seen[index] = text


class Responses:
    def __init__(self):
        self.model = os.getenv('LLM_MODEL', 'gpt-5.6-luna')

    def structured(self, instructions, payload, output_type):
        return self._structured(instructions, payload, output_type)

    def structured_stream(self, instructions, payload, output_type, emit):
        return self._structured(instructions, payload, output_type, emit)

    def _structured(self, instructions, payload, output_type, emit=None):
        key = os.getenv('OPENAI_API_KEY', '').strip()
        if not key or key == 'your_openai_api_key_here':
            raise ModelError('Model credentials are unavailable')
        body = {'model': self.model, 'instructions': instructions,
                'input': json.dumps(payload, ensure_ascii=False), 'store': False,
                'reasoning': {'effort': 'none'},
                'max_output_tokens': 512 if output_type.__name__ in ('Verification', 'ResolvedQuestion') else 1800,
                'text': {'format': {'type': 'json_schema', 'name': output_type.__name__,
                                   'strict': True, 'schema': output_type.model_json_schema()}}}
        if emit:
            body['stream'] = True
        request = Request('https://api.openai.com/v1/responses', data=json.dumps(body).encode(),
                          headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})
        started = time.perf_counter()
        first_delta_ms = None
        try:
            with urlopen(request, timeout=45) as response:
                if emit:
                    parser = ClaimTextStream(emit, payload.get('language'))
                    result = None
                    for event in sse_events(response):
                        kind = event.get('type')
                        if kind == 'response.output_text.delta':
                            if first_delta_ms is None:
                                first_delta_ms = round((time.perf_counter()-started)*1000, 2)
                            parser.feed(event['delta'])
                        elif kind == 'response.completed':
                            result = event['response']
                            break
                        elif kind in ('error', 'response.failed', 'response.incomplete', 'response.refusal.delta', 'response.refusal.done'):
                            raise ModelError('Model stream failed or declined')
                    if result is None:
                        raise ModelError('Model stream ended without completion')
                else:
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
        return parsed, {'ms': round((time.perf_counter()-started)*1000, 2), 'model_ttft_ms': first_delta_ms,
                        'input_tokens': usage.get('input_tokens', 0),
                        'output_tokens': usage.get('output_tokens', 0)}
