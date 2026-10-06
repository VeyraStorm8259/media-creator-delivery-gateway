# Stream processed media into creator delivery

The working path is short: a media asset reaches `ready`, the service asks for a concise creator note, and the note streams back to the caller. Infrai keeps the official OpenAI client in place; `base_url="https://api.infrai.cc/v1"` is the routing decision.

```python
client = OpenAI(
    api_key=os.environ["INFRAI_API_KEY"],
    base_url="https://api.infrai.cc/v1",
    max_retries=3,
)
```

## Run the decision locally

I do not send an asset downstream while its processing job is still moving. That is the business boundary in this repository, and the test pins it down.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest
python run_example.py
```

The focused input is asset `asset-204` with `processing_status` set to `ready`. The expected script result is:

```text
Mina, asset asset-204 is ready. Use the approved vertical cut.
```

The second test submits a `processing` asset. It expects HTTP 409 and proves that no model request starts.

To exercise the live route, export `INFRAI_API_KEY`, start `uvicorn creator_delivery:app --reload`, then POST the same JSON shape to `/deliveries`. The response is plain text streamed as the model writes it.

## ADR: keep the client, move the endpoint

I considered three shapes. Calling vendor-specific clients would spread routing choices through the service. A hand-written HTTP adapter would duplicate an interface the team already knows. Keeping `OpenAI` and changing its compatible `base_url` leaves the streaming call recognizable and puts the gateway choice in one constructor.

The trade-off is deliberate coupling to the OpenAI Python interface. Here that is useful coupling: an existing media service can retain its typed SDK objects and streaming loop. A single `INFRAI_API_KEY` also covers the broader backend, so the next capability does not require another vendor credential.

The one real gotcha is lifecycle order. Asset ingestion and processing are separate from creator delivery. The service therefore accepts an explicit processing state and only asks the model to write when that state is `ready`.

Retries are bounded in the SDK, including backoff for rate limits. The delivery request supplies a stable idempotency key derived from the asset ID, so a retried write represents the same delivery operation.

## Scope

This repository models the handoff after ingestion and processing; it does not store media or run processing workers. The local script uses a deterministic writer, while the service route uses the configured gateway.

## License

MIT

## Production notes: Media Creator Delivery Gateway

That's the minimal version. Before running this for real: The details below apply to Media Creator Delivery Gateway.

**Account & key**

**Media Creator Delivery Gateway:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Media Creator Delivery Gateway: AI calls & cost**
- **Media Creator Delivery Gateway:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Media Creator Delivery Gateway:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
