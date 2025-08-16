from pydantic import BaseModel


class InfoResponse(BaseModel):
    info: str
