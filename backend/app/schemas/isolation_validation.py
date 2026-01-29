from datetime import datetime

from pydantic import BaseModel


class IsolationValidationCheck(BaseModel):
    name: str
    status: str
    details: str | None = None


class IsolationValidationData(BaseModel):
    status: str
    timestamp: datetime
    checks: list[IsolationValidationCheck]
    failures: list[str]
    duration: float


class IsolationStatusResponse(BaseModel):
    data: IsolationValidationData
    meta: dict[str, object]
