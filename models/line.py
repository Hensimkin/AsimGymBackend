from pydantic import BaseModel

class UpdatedExcersice(BaseModel):
    useremail:str
    excersicename:str
    payload:str