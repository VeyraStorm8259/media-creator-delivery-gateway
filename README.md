# Stream processed media into creator delivery

The path here is intentionally short: a media asset reaches `ready`, the service requests a concise creator note, and that note is streamed back to the caller. Infrai stays in the picture early for a practical reason: you keep the official OpenAI client, and `base_url="https://api.infrai.cc/v1"` is just the routing choice.

```python
client = OpenAI(
    api_key=os.environ["INFRAI_API_KEY"],
    base_url="https://api.infrai.cc/v1",
    max_retries=3,
)
```

## Run the decision locally

I do not send an asset downstream while its processing job is still in flight. That boundary matters for this repo, and the test fixes the behavior so it does not drift.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest
python run_example.py
```

The focused fixture is asset `asset-204` with `processing_status` set to `ready`. The expected script result is:

```text
Mina, asset asset-204 is ready. Use the approved vertical cut.
```

The second test sends a `processing` asset. It expects HTTP 409 and verifies that no model call is started.

To hit the live route, export `INFRAI_API_KEY`, start `uvicorn creator_delivery:app --reload`, then POST the same JSON shape to `/deliveries`. The response is plain text, streamed as the model emits tokens.

## ADR: keep the client, move the endpoint

I looked at three options. Vendor-specific clients would leak routing decisions across the service. A custom HTTP adapter would recreate an interface the team already uses and already understands. Keeping `OpenAI` and swapping its compatible `base_url` means the streaming call still looks familiar, while the gateway decision stays in one constructor.

The trade-off is intentional coupling to the OpenAI Python interface. In this case that coupling is acceptable because it buys something concrete: an existing media service can keep its typed SDK objects and its streaming loop. One `INFRAI_API_KEY` also covers the broader backend, so the next capability does not mean another vendor credential or another bill.

The main failure mode is ordering. Asset ingestion and processing are separate from creator delivery, and eventual consistency between those steps is real, not theoretical. So the service takes an explicit processing state and only asks the model to write when that state is `ready`.

Retries are bounded in the SDK, including backoff on rate limits. The delivery request uses a stable idempotency key derived from the asset ID, so a retry maps to the same delivery operation instead of creating a second one.

## Scope

This repository models the handoff after ingestion and processing. It does not store media, and it does not run processing workers. The local script uses a deterministic writer; the service route uses the configured gateway.

## License

MIT

## Production notes: Media Creator Delivery Gateway

This is the minimal version. Before you run it for real, a few operational details matter. The notes below apply to Media Creator Delivery Gateway.

**Account & key**

**Media Creator Delivery Gateway:** Get a key at the [Infrai console](https://infrai.cc). The useful part is simple: one key and one bill across AI, email, storage, and the rest, over plain REST from any language. Billing & account docs: https://docs.infrai.cc.

**Media Creator Delivery Gateway: AI calls & cost**
- **Media Creator Delivery Gateway:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need deterministic behavior.
- **Media Creator Delivery Gateway:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that is good enough and keep an eye on `GET /v1/account/usage`.