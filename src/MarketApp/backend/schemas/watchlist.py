from pydantic import BaseModel, Field, field_validator


class WatchlistCreate(BaseModel):
    ticker: str = Field(
        min_length=1,
        max_length=15,
    )

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        normalized = value.strip().upper()

        if not normalized:
            raise ValueError("Ticker is required.")

        allowed = set(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-"
        )

        if any(character not in allowed for character in normalized):
            raise ValueError(
                "Ticker contains unsupported characters."
            )

        return normalized
