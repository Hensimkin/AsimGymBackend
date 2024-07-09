import os
import random
import string

from fastapi import APIRouter, HTTPException, requests
from fastapi.params import Query
import httpx
from config.database import userCollection
from models.users import User
from models.userLogin import UserLogin
from models.emails import Email
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from uuid import uuid4
import aiohttp
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from fastapi import Body
logging.basicConfig(level=logging.INFO)# printing
logger = logging.getLogger(__name__)# printing
from typing import List
from models.Exercise import Exercise
from models.ExercisesResponse import ExercisesResponse


SECRET_KEY = "784255b18b16ad873a7048bd745428647b3697ea3c0250e7089a69fc9ed7a268"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 50400


router = APIRouter()

YOUR_CLIENT_ID = "955645307335-dq3jk2dpiuu1jvemhn31tgjm87uhmfc5.apps.googleusercontent.com"
YOUR_CLIENT_SECRET = "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"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
EMAIL_SERVICE_URL = 'http://127.0.0.1:8000/send_email'
@router.post("/api/user/create")
async def create_user(user: User): #create user
    try:
        user2 = userCollection.find_one({"email": user.email})
        if user2:
            return{"message":"User already exists"}
        else:

            # verification_token = str(uuid4())


            #hashing password
            hashed_password = pwd_context.hash(user.password)
            user_data = user.dict()
            # user_data["verification_token"] = verification_token
            user_data["verified"] = False #verified means that the user hasnt been verifed his email
            user_data["password"] = hashed_password
            inserted_user = userCollection.insert_one(user_data)
            semitoken=generate_random_token() #for user verification
            body="here is your verification token "+semitoken
            sendEmail(user.email, "Email verification", body)

            # await send_verification_email(user.email, verification_token)

            #generating token
            #user = userCollection.find_one({"email": user.email})
            #user_name = inserted_user.get("name")
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token_payload = {
                "sub": user.email,
                "exp": datetime.utcnow() + access_token_expires
            }
            access_token = jwt.encode(access_token_payload, SECRET_KEY, algorithm=ALGORITHM)
            return {"message": "User created successfully","token":access_token,"username":user.name,"useremail":user.email,"semitoken":semitoken}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")


@router.post("/api/user/login")
async def login_user(user_login: UserLogin):
    try:
        # Check if user exists and password matches
        user = userCollection.find_one({"email": user_login.email})
        if user:
            # Generate JWT token

            if pwd_context.verify(user_login.password, user.get("password")):
                # Password matches, generate JWT token
                user_name = user.get("name")
                access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                access_token_payload = {
                    "sub": user_login.email,
                    "exp": datetime.utcnow() + access_token_expires
                }
                access_token = jwt.encode(access_token_payload, SECRET_KEY, algorithm=ALGORITHM)
                return {"access_token": access_token, "user_name": user_name}
            else:
                return {"message":"incorrect password"}
        else:
            return {"message":"incorrect user"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log in: {str(e)}")



def sendEmail(receiver_email, subject, body): #email sender for requests
    smtp_server = "smtp.gmail.com"
    port = 587  # For starttls
    sender_email = "asimgym39@gmail.com"  # Enter your address
    password = "dchz uhsa mpwo egyz"  # Enter your password

    # Create a multipart message and set headers
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject

    # Add body to email
    message.attach(MIMEText(body, "plain"))

    # Try to log in to server and send email
    try:
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()  # Secure the connection
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())
        print("Email sent successfully")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        server.quit()


def generate_random_token():
    # Define the characters to choose from
    characters = string.ascii_letters + string.digits

    # Generate a random token of length 4
    token = ''.join(random.choice(characters) for _ in range(4))

    return token



@router.post("/api/user/checkverify")
async def login_user(userEmail: Email):
    try:
        # Check if user exists and password matches
        emailcheck = userCollection.find_one({"email": userEmail.email})
        if emailcheck:
            verification = emailcheck.get("verified")  # Replace "fieldName" with the actual field name you want to access
            if verification==True:
                return {"msg": "true"}
            else:
                return {"msg": "false"}
        else:
            return {"msg": "false"}
    except Exception as e:
        print(f"Error: {e}")

@router.post("/api/user/verify")
async def verify_user(userEmail: Email):
    try:
        # Find the user by email
        print("hello")
        user = userCollection.find_one({"email": userEmail.email})

        if user:
            # Update the 'verified' field to True
            userCollection.update_one({"_id": user["_id"]}, {"$set": {"verified": True}})
            return {"msg": "true"}
        else:
            return {"msg": "false"}
    except Exception as e:
        print(f"Error: {e}")


@router.post("/api/user/resendMail")
async def getVerificationCode(userEmail: Email):
    try:
        logger.info('sup')
        semitoken = generate_random_token()
        print(semitoken)
        body = "here is your verification token " + semitoken
        sendEmail(userEmail.email, "Email verification", body)
        return {"semitoken": semitoken}
    except Exception as e:
        print(f"Error: {e}")


@router.get("/api/user/getToken") #function that creates a token for logging for a user
async def getToken(email: str = Query(...)):
    print(email)
    # return{"sup":'sup'}
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token_payload = {
        "sub": email,
        "exp": datetime.utcnow() + access_token_expires
    }
    access_token = jwt.encode(access_token_payload, SECRET_KEY, algorithm=ALGORITHM)
    print(access_token)
    return {"accesstoken":access_token}


# @router.get("/api/user/getExcersices")
# async def getExcersices():
#     url = "https://exercisedb.p.rapidapi.com/exercises"
#     querystring = {"limit": "1400", "offset": "0"}
#     headers = {
#         "x-rapidapi-key": "0f349ea414msh974e63aa91e4b27p19340ajsn7c454a65aeb1",
#         "x-rapidapi-host": "exercisedb.p.rapidapi.com"
#     }
#     response = requests.get(url, headers=headers, params=querystring)
#     if response.status_code == 200:
#         exercises = response.json()
#         exercise_data = [
#             {
#                 "name": exercise["name"],
#                 "bodyPart":exercise["bodyPart"],
#                 "target":exercise["target"],
#                 "secondaryMuscles": exercise["secondaryMuscles"],
#                 "instructions": exercise["instructions"],
#                 "gifUrl": exercise["gifUrl"],
#                 "equipment": exercise["equipment"]
#             }
#             for exercise in exercises
#         ]
#         return {"exercises": exercise_data}
#     else:
#         print("Error:", response.status_code)


@router.get("/api/user/getExercises")
async def get_exercises():
    url = "https://exercisedb.p.rapidapi.com/exercises"
    querystring = {"limit": "1400", "offset": "0"}
    headers = {
        "x-rapidapi-key": "0f349ea414msh974e63aa91e4b27p19340ajsn7c454a65aeb1",
        "x-rapidapi-host": "exercisedb.p.rapidapi.com"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=querystring)
        if response.status_code == 200:
            exercises = response.json()
            return {"exercises": exercises}
        else:
            raise HTTPException(status_code=response.status_code, detail="Error fetching data from exercise API")
