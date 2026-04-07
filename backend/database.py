import os
import razorpay
from pymongo import MongoClient
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

# 1. MongoDB Connection
# This connects to  'payment_db' and sets up two collections
try:
    client = MongoClient(os.getenv("MONGO_URI"))
    db = client["payment_db"]
    users_collection = db["users"]
    payments_collection = db["payments"]
    print("Successfully connected to MongoDB")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")

# 2. Razorpay Client Initialization
# Using the keys provided in .env
razorpay_client = razorpay.Client(
    auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
)
