from pydantic import BaseModel, ConfigDict

class ASRelationshipResponse(BaseModel):
    asn_a: int
    asn_b: int
    rel_type: str
    source: str

    model_config = ConfigDict(from_attributes=True)

class PaginatedTopology(BaseModel):
    items: list[ASRelationshipResponse]
    total: int
    page: int
    size: int
