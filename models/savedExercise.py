from typing import List
from pydantic import BaseModel

class CustomExcersice(BaseModel):
    name: str
    exercises: List[str]
    userEmail:str
