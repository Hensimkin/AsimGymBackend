from pydantic import BaseModel
from typing import List
class UserData(BaseModel):
    email: str
    age: str
    fitnessLevel: str
    gender: str
    goal: str
    height: str
    selectedMuscles: List[str]
    weight: str
