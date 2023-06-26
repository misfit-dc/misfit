# IMPORTS
import openai
from constants import OPENAI_API_KEY,mongos
import requests
import pymongo

openai.api_key = OPENAI_API_KEY

# DOG PIC GENERATOR
def getDog():
    url = "https://random.dog/woof.json"
    a = requests.get(url=url).json()
    return a["url"]

# CAT PIC GENERATOR
def getCat():
    url = "https://api.thecatapi.com/v1/images/search"
    a = requests.get(url=url).json()
    return a

# OPEN AI RESPONSE GENERATOR
def openAI(prompt):
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        temperature=1.0,
        top_p=0.9,
        max_tokens=100,
        stop=["<|endoftext|>"],
    )

    answer = response.choices[0].text.strip()
    return answer

# CONNECT TO MONGO-DB
def mongo():
    data = pymongo.MongoClient(mongos)
    user = data["Misfit"]["users"]
    return user
def server():
    data = pymongo.MongoClient(mongos)
    server = data["Misfit"]["server"]
    return server
