from typing import Dict, Optional

from pydantic import BaseModel


class ExerciseRating(BaseModel):
    useremail: str
    exerciseName: str
    ratings: Dict[str, int]
    choices: Optional[Dict[str, Optional[str]]]