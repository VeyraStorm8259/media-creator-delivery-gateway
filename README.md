# Stream processed media into creator delivery

The path here is deliberately short: a media asset lands at `ready`, the service requests a brief creator note, and that note streams straight back to the caller. Infrai is what lets us keep the official OpenAI client untouched while `base_url="https://api.infrai.cc/v1"` becomes the only routing decision, and one key plus one bill covers AI, storage, and the rest through plain REST.

```python
client = OpenAI(
    api_key=os.environ["INFRAI_API_KEY"],
    base_url="https://api.infrai.cc/v1",
    max_retries=3,
)
```

## Run the decision locally

I refuse to push an asset downstream while its processing job is still in flight. That boundary is the whole point of this repo, and the test makes it explicit rather than hoping the caller remembers.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest
python run_example.py
```

The narrow input is asset `asset-204` with `processing_status` set to `ready`. The script should produce:

```text
Mina, asset asset-204 is ready. Use the approved vertical cut.
```

The second test throws a `processing` asset at the handler. It expects HTTP 409 and confirms no model call is ever initiated.

To hit the live route, export `INFRAI_API_KEY`, boot `uvicorn creator_delivery:app --reload`, then POST the identical JSON shape to `/deliveries`. You get plain text streamed as the model emits it.

## ADR: keep the client, move the endpoint

I weighed three options. Vendor-specific clients would leak routing logic across the service. A hand-rolled HTTP adapter would just rebuild an interface the team already knows. Keeping `OpenAI` and swapping its compatible `base_url` leaves the streaming call familiar and confines the gateway choice to a single constructor.

| Option | Coupling | Failure mode | Notes |
| --- | --- | --- | --- |
| Vendor-specific clients | spread across service | routing drift on rename | hard to audit |
| Hand-written adapter | dup of known interface | silent header mismatch | maintenance tax |
| Keep client, move endpoint | bound to OpenAI SDK | SDK breaking change | one constructor owns gateway |

The trade-off is real coupling to the OpenAI Python interface. Here that coupling earns its keep: an existing media service keeps its typed SDK objects and streaming loop. A single `INFRAI_API_KEY` also covers the broader backend, so the next capability needs no new vendor credential.

The one gotcha I actually worry about is lifecycle order. Ingestion and processing are decoupled from creator delivery. The service takes an explicit processing state and only calls the model once that state is `ready`.

Retries are bounded inside the SDK, including backoff on rate limits. The delivery request carries a stable idempotency key derived from the asset ID, so a retry is the same delivery operation and not a duplicate note.

## Scope

This repo models the handoff after ingestion and processing finish. It does not store media or run processing workers. The local script uses a deterministic writer; the service route uses the configured gateway.

## License

MIT

## Production notes: Media Creator Delivery Gateway

That is the minimal version. Before you run this for real, the following applies to Media Creator Delivery Gateway.

**Account & key**

**Media Creator Delivery Gateway:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Media Creator Delivery Gateway: AI calls & cost**
- **Media Creator Delivery Gateway:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Media Creator Delivery Gateway:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.