from pydantic import BaseModel

class UserExcersice(BaseModel):
    email: str
    excersicename:str