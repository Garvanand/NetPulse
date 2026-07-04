from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, IPvAnyNetwork

class BGPEventResponse(BaseModel):
    id: UUID
    time: datetime
    collector: str
    event_type: str
    prefix: str | None = None
    peer_asn: int | None = None
    origin_asn: int | None = None
    as_path: list[int] | None = None

    model_config = ConfigDict(from_attributes=True)

class PaginatedBGPEvents(BaseModel):
    items: list[BGPEventResponse]
    total: int
    page: int
    size: int
