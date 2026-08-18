from fastapi.testclient import TestClient

from creator_delivery import DeliveryRequest, create_service


class RecordingWriter:
    def __init__(self) -> None:
        self.requests: list[DeliveryRequest] = []

    def stream_note(self, request: DeliveryRequest):
        self.requests.append(request)
        yield "Cut approved. "
        yield "Ready for your channel."


def test_ready_asset_streams_a_creator_delivery_note() -> None:
    writer = RecordingWriter()
    client = TestClient(create_service(writer))

    response = client.post(
        "/deliveries",
        json={
            "asset_id": "asset-204",
            "processing_status": "ready",
            "creator_name": "Mina",
            "editorial_note": "Use the vertical cut with captions.",
        },
    )

    assert response.status_code == 200
    assert response.text == "Cut approved. Ready for your channel."
    assert [item.asset_id for item in writer.requests] == ["asset-204"]


def test_processing_asset_is_not_sent_for_delivery() -> None:
    writer = RecordingWriter()
    client = TestClient(create_service(writer))

    response = client.post(
        "/deliveries",
        json={
            "asset_id": "asset-205",
            "processing_status": "processing",
            "creator_name": "Mina",
            "editorial_note": "Use the vertical cut with captions.",
        },
    )

    assert response.status_code == 409
    assert writer.requests == []
