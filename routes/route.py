import json
import os
import random
import string

from fastapi import APIRouter, HTTPException, requests
from fastapi.params import Query
import httpx
from config.database import userCollection
from config.database import userConfigurationCollection
from config.database import customExercisesCollection
from config.database import usersExercisesLogCollection
from models.users import User
from models.userLogin import UserLogin
from models.emails import Email
from models.line import UpdatedExcersice
from models.userConfiguration import UserData
from models.savedExercise import CustomExcersice
from models.userExcersice import UserExcersice
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

from typing import List, Dict, Any


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
            user_data["started"]=False #if the user configured himself such as weight , height ....
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


@router.post("/api/user/login") #login
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
                return {"message":"true","access_token": access_token, "user_name": user_name}
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


def generate_random_token(): #generate random token for user
    # Define the characters to choose from
    characters = string.ascii_letters + string.digits

    # Generate a random token of length 4
    token = ''.join(random.choice(characters) for _ in range(4))

    return token



@router.post("/api/user/checkverify") #checks if the email is verified
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

@router.post("/api/user/verify") #verifiy user
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


@router.post("/api/user/resendMail") #resends email
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



@router.get("/api/user/getUserName")
async def get_userName(userEmail: Email):
    try:
        username = userCollection.find_one({"email": userEmail})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")



@router.post("/api/user/checkstart") #check if the user finished his settings about himself returns true or false
async def login_user(userEmail: Email):
    try:
        # Check if user exists and password matches
        emailcheck = userCollection.find_one({"email": userEmail.email})
        if emailcheck:
            start = emailcheck.get("started")  # Replace "fieldName" with the actual field name you want to access
            if start==True:
                return {"msg": "true"}
            else:
                return {"msg": "false"}
        else:
            return {"msg": "false"}
    except Exception as e:
        print(f"Error: {e}")

@router.post("/api/user/userConfiguration")
async def finishConfiguration(userDetails:UserData):
    user_dict = userDetails.dict()
    userConfigurationCollection.insert_one(user_dict)
    return {"msg": "success"}



@router.post("/api/user/verifyConfiguration") #verifiy user_configuration
async def verify_user_Configuration(userEmail: Email):
    try:
        user = userCollection.find_one({"email": userEmail.email})

        if user:
            # Update the 'verified' field to True
            userCollection.update_one({"_id": user["_id"]}, {"$set": {"started": True}})
            return {"msg": "success"}
        else:
            return {"msg": "failed"}
    except Exception as e:
        print(f"Error: {e}")


@router.post("/api/user/saveExercises") #creating custom excercise with 0 0 0
async def createCustomExcersice(newExcersice:CustomExcersice):
    try:
        existing_exercise = customExercisesCollection.find_one({
            "name": newExcersice.name,
            "userEmail": newExcersice.userEmail
        })

        print(existing_exercise)

        if existing_exercise:
            return {"message": "ChangeName"}

        # Transform the input data into the desired format
        exercises_data = {}
        for exercise in newExcersice.exercises:
            exercises_data[exercise] = {
                "reps": 0,
                "sets": 0,
                "weight": 0
            }
        document=dict()
        document["name"]=newExcersice.name
        document["userEmail"]=newExcersice.userEmail
        document["exercises"]=exercises_data

        customExercisesCollection.insert_one(document)

        return {"message": "Exercise saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/user/updateExercises") #updating the excersice
async def updateCustomExcersice(updatedExcercise:UpdatedExcersice):
    try:
        # custom = customExercisesCollection.find_one({"userEmail": updatedExcercise.useremail, "name": updatedExcercise.excersicename})
        # print(updatedExcercise.payload)

        payload_dict = json.loads(updatedExcercise.payload)

        for exercise_name, details in payload_dict.items():
            customExercisesCollection.update_one(
                {"userEmail": updatedExcercise.useremail, "name": updatedExcercise.excersicename},
                {"$set": {f"exercises.{exercise_name}": details}},
                upsert=True
            )
        print(updatedExcercise.excersicename)
        return {"message": "Exercises updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/user/getExcersicesNames") #getting excersices name
async def getExcerciesNames(email:Email):
    try:
        user_exercises = customExercisesCollection.find({"userEmail": email.email})

        exercise_names = []
        for exercise_doc in user_exercises:
            exercise_names.append(exercise_doc.get('name'))
            # for exercise_name in exercise_doc['exercises']:
            #     exercise_names.append(exercise_name)

        print(exercise_names)
        return{"exercisenames":exercise_names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/user/getExerciseProgram")  # Corrected the typo in the endpoint
async def getExerciseProgram(userExercise: UserExcersice):
    try:
        print(userExercise.excersicename)
        user_exercises = customExercisesCollection.find({"userEmail": userExercise.email,"name":userExercise.excersicename})

        exercise_details = []
        for exercise_doc in user_exercises:
            for exercise_name, exercise_info in exercise_doc['exercises'].items():
                exercise_details.append({
                    "exercise_name": exercise_name,
                    "reps": exercise_info.get("reps"),
                    "sets": exercise_info.get("sets"),
                    "weight": exercise_info.get("weight")
                })

        print(exercise_details)
        return {"exerciseProgram": exercise_details}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/user/updateProfile")
async def updateProfile(updateDetails: UserData):
    try:
        userdetails = userConfigurationCollection.find_one({"email": updateDetails.email})
        if userdetails:
            # Creating the update dictionary excluding email
            update_data = {
                "age": updateDetails.age,
                "fitnessLevel": updateDetails.fitnessLevel,
                "gender": updateDetails.gender,
                "goal": updateDetails.goal,
                "height": updateDetails.height,
                "selectedMuscles": updateDetails.selectedMuscles,
                "weight": updateDetails.weight
            }

            userConfigurationCollection.update_one(
                {"email": updateDetails.email},
                {"$set": update_data}
            )
            return {"message": "Profile updated successfully"}
        else:
            return {"message": "User not found"}
    except Exception as e:
        return {"message": f"An error occurred: {str(e)}"}



@router.get("/api/user/getProfile")
async def getProfile(email: str = Query(..., alias='email')):
    try:
        userdetails = userConfigurationCollection.find_one({"email": email})
        if userdetails:
            # Remove the ObjectId from the result to make it serializable
            userdetails['_id'] = str(userdetails['_id'])
            return {"userdetails": userdetails}
        else:
            return {"message": "User not found"}
    except Exception as e:
        return {"message": f"An error occurred: {str(e)}"}


@router.post("/api/user/postExerciseLog")
async def post_exercise_log(exercise_log_str: str = Body(...)):
    try:
        # Parse the incoming string into a dictionary
        exercise_log_dict = json.loads(exercise_log_str)



        # Transform the exercises array into an object
        exercises_transformed = {}
        for exercise in exercise_log_dict["exercises"]:
            exercise_name = exercise.pop("name")
            exercises_transformed[exercise_name] = exercise

        # Replace the exercises list with the transformed object
        exercise_log_dict["exercises"] = exercises_transformed


        # Insert the exercise log into the database
        usersExercisesLogCollection.insert_one(exercise_log_dict)

        # Return a success message with the inserted ID
        return {"status": "success", "message": "Data saved successfully."}

    except Exception as e:
        # Handle any error that occurs
        raise HTTPException(status_code=500, detail=str(e))



def serialize_log(log: Dict[str, Any]) -> Dict[str, Any]:
    # Remove the _id field and return the rest of the log
    log.pop('_id', None)  # Remove _id if it exists
    return log
@router.post("/api/user/getExerciseLog")
async def get_exercise_log(email: Email):
    logs = list(usersExercisesLogCollection.find({"userEmail": email.email}))
    serialized_logs = [serialize_log(log) for log in logs]

    return {"logs": serialized_logs}


@router.post("/api/user/forgotPassword")
async def forgotPassword(user:UserLogin):
    db_user = userCollection.find_one({"email": user.email})
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    hashed_password = pwd_context.hash(user.password)
    result = userCollection.update_one(
        {"email": user.email},
        {"$set": {"password": hashed_password}}
    )

    if result.modified_count == 1:
        return {"message": "Password updated successfully"}
    else:
        raise HTTPException(status_code=500, detail="Password update failed")