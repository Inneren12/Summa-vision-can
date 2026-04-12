from pydantic import BaseModel, EmailStr, Field


class LeadCaptureRequest(BaseModel):
    email: EmailStr
    asset_id: int = Field(gt=0)
    turnstile_token: str = Field(min_length=1)


class LeadCaptureResponse(BaseModel):
    message: str = "Check your email for the download link"
