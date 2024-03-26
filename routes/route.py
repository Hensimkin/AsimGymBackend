from fastapi import APIRouter, HTTPException, requests
from config.database import userCollection
from models.users import User

router = APIRouter()

YOUR_CLIENT_ID = "955645307335-dq3jk2dpiuu1jvemhn31tgjm87uhmfc5.apps.googleusercontent.com"
YOUR_CLIENT_SECRET = "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"

@router.post("/api/user/create")
async def create_user(user: User):
    try:
        # Insert user data into MongoDB
        inserted_user = userCollection.insert_one(user.dict())
        # Return inserted user's ID
        return {"message": "User created successfully", "user_id": str(inserted_user.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")


def sign_up(code: str):
    url = f"https://oauth2.googleapis.com/token"
    params = {
        "code": code,
        "client_id": YOUR_CLIENT_ID,
        "client_secret": YOUR_CLIENT_SECRET,
        "redirect_uri": "http://localhost:3001/google",
        "grant_type": "authorization_code"
    }

    response = requests.post(url, json=params)
    data = response.json()
    print("data:", data)

    id_token = data.get("id_token")

    # Verify the id token
    verify_response = requests.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}")
    verify_data = verify_response.json()
    print("verifyData:", verify_data)

    # Get user data from the verify data
    name = verify_data.get("name")
    email = verify_data.get("email")
    picture = verify_data.get("picture")

    return email, name, picture

@router.get("/google")
def handle_google_login(code: str):
    if not code:
        raise HTTPException(status_code=400, detail="Invalid code")

    email, name, picture = sign_up(code)
    redirect_url = f'exp://?email={email}&name={name}&picture={picture}'
    return {"script": f'<script>window.location.replace("{redirect_url}")</script>'}
