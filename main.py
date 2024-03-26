from typing import Union

import uvicorn

from routes.route import router as user_router

from fastapi import FastAPI


app = FastAPI()

app.include_router(user_router)



if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)