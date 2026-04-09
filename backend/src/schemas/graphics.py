from pydantic import BaseModel

class GenerationResult(BaseModel):
    publication_id: int
    cdn_url_lowres: str
    s3_key_highres: str
    version: int
