from pydantic import BaseModel


class ChunkContent(BaseModel):
    content: str
