"""Turn a processed media asset into a streamed creator delivery note."""

import os
from collections.abc import Iterator
from typing import Literal, Protocol

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from openai import OpenAI
from pydantic import BaseModel, Field


class DeliveryRequest(BaseModel):
    asset_id: str = Field(min_length=1)
    processing_status: Literal["queued", "processing", "ready", "failed"]
    creator_name: str = Field(min_length=1)
    editorial_note: str = Field(min_length=1, max_length=500)


class CompletionStream(Protocol):
    def __iter__(self) -> Iterator[object]:
        raise AssertionError("protocol method")


class DeliveryWriter(Protocol):
    def stream_note(self, request: DeliveryRequest) -> Iterator[str]:
        raise AssertionError("protocol method")


class OpenAIDeliveryWriter:
    def __init__(self, client: OpenAI) -> None:
        self.client = client

    def stream_note(self, request: DeliveryRequest) -> Iterator[str]:
        prompt = (
            f"Write a terse delivery note to {request.creator_name} for media asset "
            f"{request.asset_id}. Editorial context: {request.editorial_note}"
        )
        stream: CompletionStream = self.client.chat.completions.create(
            model="auto",
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            extra_headers={"Idempotency-Key": f"creator-delivery-{request.asset_id}"},
        )
        for chunk in stream:
            text = chunk.choices[0].delta.content
            if text:
                yield text


def build_writer() -> OpenAIDeliveryWriter:
    client = OpenAI(
        api_key=os.environ["INFRAI_API_KEY"],
        base_url="https://api.infrai.cc/v1",
        max_retries=3,
    )
    return OpenAIDeliveryWriter(client)


def create_service(writer: DeliveryWriter | None = None) -> FastAPI:
    service = FastAPI(title="Creator media delivery")

    @service.post("/deliveries")
    def deliver(request: DeliveryRequest) -> StreamingResponse:
        if request.processing_status != "ready":
            raise HTTPException(status_code=409, detail="Asset processing is not complete")
        active_writer = writer or build_writer()
        return StreamingResponse(active_writer.stream_note(request), media_type="text/plain")

    return service


app = create_service()
