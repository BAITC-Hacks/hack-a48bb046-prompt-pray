from pydantic import BaseModel, ConfigDict, Field


class GenerateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    prompt: str = Field(min_length=1, max_length=32000)
    instructions: str | None = Field(default=None, min_length=1, max_length=8000)
    max_output_tokens: int | None = Field(default=None, ge=16, le=32768)


class TokenUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int


class GenerateResponse(BaseModel):
    id: str
    model: str
    content: str
    usage: TokenUsage | None = None
