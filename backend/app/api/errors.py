from fastapi import HTTPException


def not_found(detail: str, *, instance: str | None = None) -> HTTPException:
    payload = {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": detail,
    }
    if instance:
        payload["instance"] = instance
    return HTTPException(status_code=404, detail=payload)
