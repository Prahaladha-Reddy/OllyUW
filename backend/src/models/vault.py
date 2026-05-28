from __future__ import annotations
from datetime import datetime
from enum import Enum
from pydantic import BaseModel

class VaultItemType(str, Enum):
    COOKIE = "cookie"
    CREDENTIAL = "credential"
    API_KEY = "api_key"
    BOOKMARK = "bookmark"
    LOCAL_STORAGE = "local_storage"

class VaultItemRecord(BaseModel):
    id: str
    user_id: str
    item_type: VaultItemType
    key: str
    encrypted_data: str
    created_at: datetime
    updated_at: datetime

class CreateVaultItemRequest(BaseModel):
    item_type: VaultItemType
    key: str
    encrypted_data: str

class VaultItemResponse(BaseModel):
    item: VaultItemRecord

class VaultItemListResponse(BaseModel):
    items: list[VaultItemRecord]
