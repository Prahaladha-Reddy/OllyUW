from __future__ import annotations

import unstructured_client
from unstructured_client.models import operations, shared

from src.config import get_settings

_client: unstructured_client.UnstructuredClient | None = None


def _get_client() -> unstructured_client.UnstructuredClient:
    global _client
    if _client is not None:
        return _client

    settings = get_settings()
    if not settings.unstructured_api_key:
        raise RuntimeError(
            "UNSTRUCTURED_API_KEY is not configured — set it in .env once you have the key."
        )

    _client = unstructured_client.UnstructuredClient(
        api_key_auth=settings.unstructured_api_key
    )
    return _client


async def partition(content: bytes, filename: str) -> list[dict]:
    """Partition a document via the Unstructured API. Returns a list of element dicts."""
    client = _get_client()
    req = operations.PartitionRequest(
        partition_parameters=shared.PartitionParameters(
            files=shared.Files(content=content, file_name=filename),
            strategy=shared.Strategy.AUTO,
        ),
    )
    res = await client.general.partition_async(request=req)
    return res.elements or []
