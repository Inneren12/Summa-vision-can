from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LeadCaptureRequest(BaseModel):
    email: EmailStr
    asset_id: int = Field(gt=0)
    turnstile_token: str = Field(min_length=1)
    # Phase 2.3: optional UTM attribution; populated when the visitor
    # arrived via a publish-kit share URL (utm_content = lineage_key).
    utm_source: str | None = Field(default=None, max_length=100)
    utm_medium: str | None = Field(default=None, max_length=100)
    utm_campaign: str | None = Field(default=None, max_length=200)
    utm_content: str | None = Field(default=None, max_length=200)

    model_config = ConfigDict(extra="forbid")


class LeadCaptureResponse(BaseModel):
    message: str = "Check your email for the download link"
