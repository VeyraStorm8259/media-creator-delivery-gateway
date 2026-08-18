"""Run one local request against the creator delivery service."""

from fastapi.testclient import TestClient

from creator_delivery import DeliveryRequest, create_service


class PreviewWriter:
    def stream_note(self, request: DeliveryRequest):
        yield f"{request.creator_name}, asset {request.asset_id} is ready. "
        yield "Use the approved vertical cut."


response = TestClient(create_service(PreviewWriter())).post(
    "/deliveries",
    json={
        "asset_id": "asset-204",
        "processing_status": "ready",
        "creator_name": "Mina",
        "editorial_note": "Use the vertical cut with captions.",
    },
)
print(response.text)
