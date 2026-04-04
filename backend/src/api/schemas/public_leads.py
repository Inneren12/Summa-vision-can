from pydantic import BaseModel, EmailStr, Field


class LeadCaptureRequest(BaseModel):
    email: EmailStr
    asset_id: int = Field(gt=0)


class LeadCaptureResponse(BaseModel):
    download_url: str
    message: str = "Check your email for the download link."
