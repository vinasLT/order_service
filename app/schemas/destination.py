from pydantic import BaseModel


class DestinationOut(BaseModel):
    destination_id: int
    destination_name: str
