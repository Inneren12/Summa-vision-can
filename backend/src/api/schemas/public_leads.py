from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


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

    @field_validator(
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        mode="before",
    )
    @classmethod
    def _normalize_utm(cls, value: object) -> str | None:
        """Trim whitespace; treat empty / whitespace-only as ``None``.

        The public capture endpoint accepts these directly from URL
        params, where empty strings can leak through (e.g. a share URL
        copied with ``utm_source=&utm_content=ln_xyz``). Persisting
        whitespace would break group-level backfill semantics in the
        repository, since ``""`` is truthy enough to mark the lead as
        attributed even though it carries no useful campaign data.
        """
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class LeadCaptureResponse(BaseModel):
    message: str = "Check your email for the download link"
