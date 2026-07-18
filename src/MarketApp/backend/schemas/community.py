from pydantic import BaseModel, Field

class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    title: str = Field(min_length=3, max_length=120)
    body: str = Field(min_length=10, max_length=1500)
    publish_consent: bool = False
    publish_name: bool = False
    display_name: str | None = Field(default=None, max_length=80)

class FeatureRequestCreate(BaseModel):
    title: str = Field(min_length=3, max_length=140)
    description: str = Field(min_length=10, max_length=1200)
