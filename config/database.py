import certifi
from pymongo import MongoClient

uri = "mongodb+srv://hensim97:I6yrc4wEom8ree74@asimgym.hdubeoh.mongodb.net/?retryWrites=true&w=majority&appName=AsimGym"
client = MongoClient(uri,ssl_ca_certs=certifi.where())

db=client["AsimGym"]

userCollection=db["users"]


try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)