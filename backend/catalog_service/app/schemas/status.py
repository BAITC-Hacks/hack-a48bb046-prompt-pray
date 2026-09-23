from typing import Literal

from pydantic import BaseModel


class ServiceStatus(BaseModel):
    status: Literal["ready"]
