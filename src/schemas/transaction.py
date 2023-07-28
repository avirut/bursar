from sqlmodel import Field, SQLModel
from datetime import datetime

class Transaction(SQLModel, table=True):
    id: str = Field(default=None, primary_key=True)
    ts: datetime = Field(default=None)