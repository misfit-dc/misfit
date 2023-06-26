from dotenv import load_dotenv
import os
load_dotenv()

token = os.environ["token"]
mongos = os.environ["mongos"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
spam = os.environ["SPAM_CHANNEL"]  
modappch = os.environ["MOD_APPLICATION_CHANNEL"]