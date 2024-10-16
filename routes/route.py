import json
import os
import random
import string

import httpx
import pandas as pd
from fastapi import APIRouter, HTTPException, requests
from fastapi.params import Query

from config.database import userCollection, usersAiCollection
from config.database import userConfigurationCollection
from config.database import customExercisesCollection
from config.database import usersExercisesLogCollection
from models.ExerciseRating import ExerciseRating
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
from trainersAi import predict_user_cluster
from firstRecommendation import process_list_and_csv


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
async def getVerificationCode(email: Email):
    try:
        logger.info('sup')
        semitoken = generate_random_token()
        print(semitoken)
        body = "here is your verification token " + semitoken
        sendEmail(email.email, "Email verification", body)
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
async def finishConfiguration(userDetails: UserData):
    user_dict = userDetails.dict()
    print(user_dict)
    # Insert the original user configuration into the database


    # Perform the first AI training using the original user_dict
    firstAiTraining, userCluster = userFirstAiTraining(user_dict)

    print(firstAiTraining)
    print(userCluster)
    user_dict['userCluster']=str(userCluster)
    userConfigurationCollection.insert_one(user_dict)
    # Ensure that the email is added to firstAiTraining
    firstAiTraining["email"] = user_dict.get("email")

    # Transform the exercise lists into the desired dictionary format for firstAiTraining
    for key, value in firstAiTraining.items():
        if isinstance(value, list) and key != 'email':
            firstAiTraining[key] = {exercise_name: {
                "reps": "0",
                "weight": "0",
                "sets": "0"
            } for exercise_name in value}

    # Check the modified firstAiTraining structure
    print("Modified firstAiTraining:", firstAiTraining)

    # Insert the modified firstAiTraining result into the database
    usersAiCollection.insert_one(firstAiTraining)

    return {"msg": "success"}


# @router.post("/api/user/userConfiguration")
# async def finishConfiguration(userDetails: UserData):
#     try:
#         user_dict = userDetails.dict()
#         print(user_dict)
#
#         # Transform the exercise data for each category
#         transformed_data = {}
#         for category, exercises in user_dict.items():
#             if category != "email":
#                 transformed_data[category] = {}
#                 for exercise in exercises:
#                     transformed_data[category][exercise] = {
#                         "reps": "0",
#                         "weight": "0",
#                         "sets": "0"
#                     }
#
#         # Create the document to be saved in the database
#         document = {
#             "email": user_dict.get("email"),
#             "exercises": transformed_data
#         }
#
#         # Insert into the user configuration collection
#         userConfigurationCollection.insert_one(document)
#
#         # Prepare and insert AI training data
#         firstAiTraining = userFirstAiTraining(document)
#         firstAiTraining["email"] = document["email"]
#         usersAiCollection.insert_one(firstAiTraining)
#
#         print(firstAiTraining)
#         print("Configuration saved successfully")
#
#         return {"msg": "success"}
#
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))




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


# @router.post("/api/user/getExerciseProgram")  # Corrected the typo in the endpoint
# async def getExerciseProgram(userExercise: UserExcersice):
#     try:
#         print(userExercise.excersicename)
#         user_exercises = customExercisesCollection.find({"userEmail": userExercise.email,"name":userExercise.excersicename})
#
#         exercise_details = []
#         for exercise_doc in user_exercises:
#             for exercise_name, exercise_info in exercise_doc['exercises'].items():
#                 exercise_details.append({
#                     "exercise_name": exercise_name,
#                     "reps": exercise_info.get("reps"),
#                     "sets": exercise_info.get("sets"),
#                     "weight": exercise_info.get("weight")
#                 })
#
#         print(exercise_details)
#         return {"exerciseProgram": exercise_details}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/user/getExerciseProgram")
async def getExerciseProgram(userExercise: UserExcersice):
    try:
        print(userExercise.excersicename)

        exercise_details = []

        if userExercise.excersicename == 'AI Exercise':
            # Search only by email in usersAiCollection
            user_exercises = usersAiCollection.find({"email": userExercise.email})

            # Iterate through the results to extract exercise information based on the structure
            for exercise_doc in user_exercises:
                # Iterate through each key in the document to find exercise information
                for category, exercises in exercise_doc.items():
                    # Skip non-exercise fields like '_id' and 'email'
                    if category not in ['_id', 'email']:
                        # Iterate through the exercises in this category
                        for exercise_name, exercise_info in exercises.items():
                            exercise_details.append({
                                "exercise_name": exercise_name,
                                "reps": exercise_info.get("reps", "N/A"),
                                "sets": exercise_info.get("sets", "N/A"),
                                "weight": exercise_info.get("weight", "N/A")
                            })

        else:
            # Search by email and exercise name in customExercisesCollection
            user_exercises = customExercisesCollection.find({"userEmail": userExercise.email,"name":userExercise.excersicename})

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
        cluster=userdetails["userCluster"]
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

            user_ai_data = usersAiCollection.find_one({"email": updateDetails.email})

            muscle_groups = [key for key in user_ai_data.keys() if key not in ["email", "_id"]]


            new_selected_muscles = updateDetails.selectedMuscles

            muscles_to_keep = [muscle for muscle in muscle_groups if muscle in new_selected_muscles]

            muscles_to_remove = [muscle for muscle in muscle_groups if muscle not in new_selected_muscles]

            if len(muscles_to_remove)>0:
                for muscle in muscles_to_remove:
                    usersAiCollection.update_one(
                        {"email": updateDetails.email},
                        {"$unset": {muscle: ""}}
                    )

            if len(muscles_to_keep)>0:
                new_selected_muscles = [muscle for muscle in new_selected_muscles if muscle not in muscles_to_keep]


            if len(new_selected_muscles)!=0:
                addAi(updateDetails.email, new_selected_muscles,cluster)


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
        return {"message": "Email does not exist"}
    hashed_password = pwd_context.hash(user.password)
    result = userCollection.update_one(
        {"email": user.email},
        {"$set": {"password": hashed_password}}
    )

    if result.modified_count == 1:
        return {"message": "Password updated successfully"}
    else:
        raise HTTPException(status_code=500, detail="Password update failed")


def userFirstAiTraining(userDict):
    userCluster=predict_user_cluster(userDict["age"],userDict["height"],userDict["weight"],userDict["gender"],userDict["fitnessLevel"])
    print(userCluster)
    #recomindationSystem(userDict['selectedMuscles'])
    userFirstAiProgram=process_list_and_csv(userDict['selectedMuscles'],str(userCluster))
    return userFirstAiProgram, userCluster










































def recomindationSystem(muscle_groups):
    exercises_df = pd.read_csv('clustered_exercises.csv')

    # Initialize the recommendations dictionary
    recommendations = {}

    # For each muscle group, find exercises
    for muscle in muscle_groups:
        # Filter exercises that target the given muscle group
        filtered_exercises = exercises_df[exercises_df['bodyPart'] == muscle]

        # Convert filtered dataframe to a list of dictionaries
        filtered_exercises = filtered_exercises.to_dict(orient='records')

        # Check the number of available exercises and add to recommendations accordingly
        if len(filtered_exercises) >= 3:
            # Get 3 random exercises if available
            selected_exercises = random.sample(filtered_exercises, 3)
        elif len(filtered_exercises) > 0:
            # Not enough exercises for three, add all available exercises
            selected_exercises = filtered_exercises
        else:
            # No exercises available for this muscle group
            selected_exercises = "No exercises available for this muscle group"

        # Include only necessary fields in the recommendations
        if isinstance(selected_exercises, list):
            recommendations[muscle] = [
                {
                    "name": exercise["name"],
                    "id": exercise["id"],
                    "cluster": exercise["cluster"],
                    "bodyPart": exercise["bodyPart"]
                } for exercise in selected_exercises
            ]
        else:
            recommendations[muscle] = selected_exercises

    # Print the recommendations before returning
    print(recommendations)

    return recommendations


@router.post("/api/user/updateAIExercises")
async def updateCustomExercise(updatedExercise: UpdatedExcersice):
    try:
        # Parse the payload into a dictionary
        payload_dict = json.loads(updatedExercise.payload)

        # Retrieve the user's document
        user_document = usersAiCollection.find_one({"email": updatedExercise.useremail})
        print(user_document)

        if not user_document:
            raise HTTPException(status_code=404, detail="User not found")

        # Extract keys representing exercise categories, excluding '_id' and 'email'
        exercise_categories_keys = [
            key for key in user_document if key not in ["_id", "email"]
        ]

        print(exercise_categories_keys)

        # Iterate through each exercise in the payload
        for exercise_name, details in payload_dict.items():
            # Check which category the exercise belongs to
            for category in exercise_categories_keys:
                if exercise_name in user_document[category]:
                    # Update the specific exercise in the correct category
                    usersAiCollection.update_one(
                        {"email": updatedExercise.useremail},
                        {"$set": {f"{category}.{exercise_name}": details}},
                    )
                    print(f"Updated {exercise_name} in {category} with {details}")
                    break  # Exit loop once the exercise is updated

        return {"message": "Exercises updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/user/exerciseRatings")
async def receive_exercise_ratings(rating: ExerciseRating):
    try:
        # Create the document to be inserted
        rating_data = {
            "useremail": rating.useremail,
            "exerciseName": rating.exerciseName,
            "ratings": rating.ratings,
            "choices": rating.choices  # Include choices field in the document
        }
        print(rating_data)



        user = userConfigurationCollection.find_one({"email": rating.useremail})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Retrieve the userCluster from the user document
        user_cluster = user.get("userCluster")
        if not user_cluster:
            raise HTTPException(status_code=404, detail="User cluster not found")



        rating=rating_data["ratings"]
        print(rating)
        print(user_cluster)
        updateClusters(user_cluster,rating)
        if any(value in [3, 4] for value in rating_data["ratings"].values()):
            process_exercise_ratings(rating_data['useremail'], rating_data['ratings'], rating_data["choices"])
        



        return {"message": "Exercise rating added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


#create a func that will check for each rating what to do
#if rating is 1 and 2 dont switch 3 and 4 is switch


def updateClusters(usercluster, ratings) :
    # Read the CSV file into a DataFrame
    df = pd.read_csv('clustered_exercises.csv')

    # Loop through each exercise in the ratings dictionary
    for exercise, rating in ratings.items():
        # Check if the exercise exists in the DataFrame
        if exercise in df['name'].values:
            # Get the current value in the cluster column for this exercise
            current_value = df.loc[df['name'] == exercise, usercluster].values[0]

            # Update the value based on the rating
            if rating == 1:
                updated_value = current_value + 2
            elif rating == 2:
                updated_value = current_value + 1
            elif rating == 3:
                # Only subtract 1 if the current value is not 0
                if current_value != 0:
                    updated_value = current_value - 1
                else:
                    updated_value = current_value  # No change if it's 0
            elif rating == 4:
                # Only subtract 2 if the current value is not 0
                if current_value != 0:
                    updated_value = current_value - 2
                else:
                    updated_value = current_value  # No change if it's 0
            else:
                continue  # If the rating is not 1, 2, 3, or 4, skip this exercise

            # Update the DataFrame with the new value
            df.loc[df['name'] == exercise, usercluster] = updated_value

    # Save the updated DataFrame back to the CSV file
    df.to_csv('clustered_exercises.csv', index=False)
    print("Cluster valuesss updated successfully.")


def process_exercise_ratings(useremail, ratings, choices):
    import pandas as pd  # Make sure to import pandas if not already imported

    # Create a result list to store exercises that match the criteria
    result = []
    cluster = {}  # Change from list to dict

    # Iterate through the ratings dictionary
    for exercise, rating in ratings.items():
        # Check if the rating is 3 and choice is 'Change', or if the rating is 4
        if (rating == 3 and exercise in choices and choices[exercise] == "Change") or rating == 4:
            result.append({
                "exercise": exercise,
                "rating": rating,
                "choice": choices.get(exercise, "No choice"),  # Default to 'No choice' if not found in choices
                "status": f"Rating {rating} and choice {choices.get(exercise, 'No choice')}"
            })

    print("Result:", result)


    #search the body part of each stuff in result




    df = pd.read_csv('clustered_exercises.csv')

    # Iterate through the result list and find the cluster number for each exercise
    for item in result:
        exercise_name = item['exercise']

        # Search for the exercise in the DataFrame and get the cluster number and body part
        cluster_number = df.loc[df['name'] == exercise_name, 'cluster'].values
        cluster_bodypart = df.loc[df['name'] == exercise_name, 'bodyPart'].values

        # If the exercise is found, add the cluster number to the cluster dict
        if len(cluster_number) > 0 and len(cluster_bodypart) > 0:
            body_part = str(cluster_bodypart[0])
            clust_num = int(cluster_number[0])

            # Initialize the list if the body part is not already in the cluster dict
            if body_part not in cluster:
                cluster[body_part] = []

            # Append the cluster number if it's not already in the list to avoid duplicates
            if clust_num not in cluster[body_part]:
                cluster[body_part].append(clust_num)

    print("Cluster:", cluster)

    user_document = userConfigurationCollection.find_one({"email": useremail})

    # Check if 'hatedCluster' already exists in the user's document
    if 'hatedCluster' in user_document:
        existing_hated_clusters = user_document['hatedCluster']

        # Merge new clusters with existing clusters
        for body_part, new_clusters in cluster.items():
            if body_part in existing_hated_clusters:
                # Append only new clusters, avoiding duplicates
                combined_clusters = list(set(existing_hated_clusters[body_part] + new_clusters))
                existing_hated_clusters[body_part] = combined_clusters
            else:
                # Add new body part if it doesn't already exist
                existing_hated_clusters[body_part] = new_clusters

        # Update the user's document with the merged hatedCluster field
        userConfigurationCollection.update_one(
            {"email": useremail},  # Filter by user email
            {"$set": {"hatedCluster": existing_hated_clusters}}  # Set the hatedCluster field
        )
    else:
        # If hatedCluster doesn't exist, set it with the new cluster dict
        userConfigurationCollection.update_one(
            {"email": useremail},  # Filter by user email
            {"$set": {"hatedCluster": cluster}}  # Set the hatedCluster field
        )

    changeAiExcersice(useremail, cluster, result)

    return result



def changeAiExcersice(useremail,cluster,deleteList):
    exercise_names = [item['exercise'] for item in deleteList]



    for body_part in cluster.keys():
        # Loop through each exercise name to delete from the current body part
        for exercise in exercise_names:
            # Update command to remove the specific exercise from the body part
            usersAiCollection.update_one(
                {"email": useremail},  # Filter by email
                {"$unset": {f"{body_part}.{exercise}": ""}}  # Unset the specific exercise from the body part
            )

    user = userConfigurationCollection.find_one({"email": useremail})

    hated_cluster = user['hatedCluster']

    newCluster={}

    df = pd.read_csv('clustered_exercises.csv')

    for body_part, exercises in cluster.items():
        # Count how many exercises are in the array
        newCluster[body_part] = len(exercises)

    print(newCluster)

    for body_part, count in newCluster.items():
        print(f"Body part: {body_part}")

        # Get the list of hated clusters for this body part
        hatedclusters = hated_cluster[body_part]

        # Filter exercises by body part and exclude exercises in the hated clusters
        valid_exercises = df[(df['bodyPart'] == body_part) & (~df['cluster'].isin(hatedclusters))]

        if not valid_exercises.empty:
            # Get only the names of the valid exercises
            exercise_names = valid_exercises['name'].tolist()

            # If the number of valid exercises is less than count, return as many as possible
            if len(exercise_names) > count:
                # Randomly select `count` number of exercise names
                selected_exercises = random.sample(exercise_names, count)

            else:
                # If fewer exercises than count, return all valid ones
                selected_exercises = exercise_names

            for exercise in selected_exercises:
                exercise_data = {
                    "reps": "0",
                    "weight": "0",
                    "sets": "0"
                }

                # Insert the new exercise into the corresponding body part in MongoDB
                usersAiCollection.update_one(
                    {"email": useremail},
                    {"$set": {f"{body_part}.{exercise}": exercise_data}}  # Add the new exercise under the body part
                )

            print(f"Selected exercise names for {body_part}: {selected_exercises}")
        else:
            print(f"No valid exercises available for {body_part} that aren't in hated clusters.")





def addAi(userEmail,bodyparts,cluster):
    df = pd.read_csv('clustered_exercises.csv')
    exercise_data = {
        "reps": "0",
        "weight": "0",
        "sets": "0"
    }
    user_doc = userConfigurationCollection.find_one({"email": userEmail}, {"hatedCluster"})

    hated_cluster = user_doc.get('hatedCluster', {})

    formatted_cluster = {}
    for muscle_group, ids in hated_cluster.items():
        formatted_cluster[muscle_group] = ids

    newEx=[]

    for bodypart in bodyparts:
        # Filter the dataframe by the body part
        bodypart_exercises = df[df['bodyPart'] == bodypart]

        # Sort the exercises by the provided cluster number
        sorted_exercises = bodypart_exercises.sort_values(by=str(cluster), ascending=False)

        # Select the top 3 exercises
        top_3_exercises = sorted_exercises.head(3)

        # Loop through the top 3 exercises
        for _, exercise in top_3_exercises.iterrows():
            exercise_cluster = exercise['cluster']
            exercise_name = exercise['name']

            # Check if this exercise's cluster is not in the hated cluster
            if exercise_cluster not in formatted_cluster.get(bodypart, []):
                newEx.append(exercise_name)

        for ex in newEx:
            usersAiCollection.update_one(
                {"email": userEmail},
                {"$set": {f"{bodypart}.{ex}": exercise_data}})
        newEx.clear()



