# Import required libraries and modules
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from database import users_collection, payments_collection, razorpay_client
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
    set_access_cookies,
    unset_jwt_cookies,
)
from datetime import datetime, timedelta
import os
import re

# Initialize Flask application
app = Flask(__name__)
@app.route("/")
def home():
    return "Backend is running 🚀"

# ---------------- APPLICATION CONFIGURATION ---------------- #
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "super-secret-key")

app.config["JWT_SECRET_KEY"] = "jwt-super-secret"

app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=2)

# ---------------- COOKIE SECURITY SETTINGS ---------------- #
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]

app.config["JWT_COOKIE_SECURE"] = False

app.config["JWT_ACCESS_COOKIE_NAME"] = "access_token"

app.config["JWT_COOKIE_CSRF_PROTECT"] = False

jwt = JWTManager(app)

# ---------------- CORS CONFIGURATION ---------------- #

# Allow frontend application running on port 5500 to access backend APIs
CORS(
    app,
    resources={r"/api/*": {"origins": "http://127.0.0.1:5500"}},
    supports_credentials=True,
)

# Regular expression used to validate email format
email_regex = r"^\S+@\S+\.\S+$"


# ---------------- AUTHENTICATION ROUTES ---------------- #


# -------- Register User --------
@app.route("/api/register", methods=["POST"])
def register():
    try:
        # Extract data from JSON request
        data = request.json
        name, email, password = (
            data.get("name"),
            data.get("email"),
            data.get("password"),
        )

        # Validate required fields
        if not name or not email or not password:
            return jsonify({"message": "All fields required"}), 400

        # Validate email format using regex
        if not re.match(email_regex, email):
            return jsonify({"message": "Invalid email"}), 400

        # Check if user already exists
        if users_collection.find_one({"email": email}):
            return jsonify({"message": "User already exists"}), 400

        # Hash password before storing in database
        hashed_password = generate_password_hash(password)

        # Create new user document
        new_user = {
            "name": name,
            "email": email,
            "password": hashed_password,
            "created_at": datetime.utcnow(),
        }

        # Insert user into MongoDB collection
        users_collection.insert_one(new_user)

        return jsonify({"message": "User registered successfully"}), 201

    except Exception as e:
        return jsonify({"message": "Server error"}), 500


# -------- Login User --------
@app.route("/api/login", methods=["POST"])
def login():
    try:
        data = request.json

        # Find user using email
        user = users_collection.find_one({"email": data.get("email")})

        # Validate password using hashed password comparison
        if user and check_password_hash(user["password"], data.get("password")):

            # Generate JWT access token containing user ID
            access_token = create_access_token(identity=str(user["_id"]))

            # Prepare response
            response = jsonify({"message": "Login successful", "name": user["name"]})

            # Store JWT token inside HTTP-only cookie
            set_access_cookies(response, access_token)

            return response, 200

        return jsonify({"message": "User is Not Register"}), 401

    except Exception as e:
        return jsonify({"message": "Server error"}), 500


# -------- Logout User --------
@app.route("/api/logout", methods=["POST"])
def logout():

    response = jsonify({"message": "Logout successful"})

    # Remove JWT cookies from browser
    unset_jwt_cookies(response)

    return response, 200


# ---------------- PROFILE ROUTES ---------------- #


# -------- Get Logged-in User Profile --------
@app.route("/api/profile", methods=["GET"])
@jwt_required()  # Protect route using JWT authentication
def get_profile():

    # Extract user ID from JWT token
    user_id = get_jwt_identity()

    # Fetch user from MongoDB using ObjectId
    user = users_collection.find_one({"_id": ObjectId(user_id)})

    if user:
        return jsonify({"name": user["name"], "email": user["email"]}), 200

    return jsonify({"message": "User not found"}), 404


# -------- Update Profile --------
@app.route("/api/profile/update", methods=["PUT"])
@jwt_required()
def update_profile():

    # Get logged-in user ID
    user_id = get_jwt_identity()

    # Extract request data
    data = request.json

    # Dictionary that stores fields to update
    update_data = {}

    # Update name if provided
    if data.get("name"):
        update_data["name"] = data.get("name")

    # Update email if provided
    if data.get("email"):
        new_email = data.get("email")

        # Validate email format
        if not re.match(email_regex, new_email):
            return jsonify({"message": "Invalid email format"}), 400

        # Check if email already exists for another user
        existing_user = users_collection.find_one({"email": new_email})

        if existing_user and str(existing_user["_id"]) != user_id:
            return jsonify({"message": "Email already in use by another user"}), 400

        update_data["email"] = new_email

    # Prevent update if no data provided
    if not update_data:
        return jsonify({"message": "Nothing to update"}), 400

    # Update user document in MongoDB
    users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})

    return jsonify({"message": "Profile updated successfully"}), 200


# ---------------- PAYMENT ROUTES ---------------- #


# -------- Create Razorpay Order --------
@app.route("/api/create-order", methods=["POST"])
@jwt_required()
def create_order():
    try:
        # Get logged-in user ID
        user_id = get_jwt_identity()

        # Get amount from request
        amount = int(request.json.get("amount"))

        order_params = {"amount": amount * 100, "currency": "INR", "payment_capture": 1}

        # Create order using Razorpay API
        order = razorpay_client.order.create(data=order_params)

        # Store payment order in MongoDB
        payments_collection.insert_one(
            {
                "user_id": user_id,
                "order_id": order["id"],
                "amount": amount,
                "status": "Created",
                "timestamp": datetime.utcnow(),
            }
        )

        return jsonify(order), 200

    except Exception as e:
        return jsonify({"message": "Order creation failed"}), 400


# -------- Verify Razorpay Payment --------
@app.route("/api/verify-payment", methods=["POST"])
@jwt_required()
def verify_payment():

    # Extract Razorpay payment details
    data = request.json
    order_id = data.get("razorpay_order_id")
    payment_id = data.get("razorpay_payment_id")
    signature = data.get("razorpay_signature")

    try:
        # Handle case where payment was cancelled or failed
        if not signature or not payment_id:
            raise Exception("Payment cancelled or failed")

        params_dict = {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        }

        # Verify Razorpay payment signature
        razorpay_client.utility.verify_payment_signature(params_dict)

        # Update payment status to success
        payments_collection.update_one(
            {"order_id": order_id},
            {"$set": {"status": "Success", "payment_id": payment_id}},
        )

        return jsonify({"message": "Payment successful"}), 200

    except Exception as e:
        # Update payment status to failed if verification fails
        payments_collection.update_one(
            {"order_id": order_id}, {"$set": {"status": "Failed"}}
        )

        return jsonify({"message": "Payment failed or verification error"}), 400


# -------- Fetch Payment History --------
@app.route("/api/payment-history", methods=["GET"])
@jwt_required()
def payment_history():

    # Get logged-in user ID
    user_id = get_jwt_identity()

    # Retrieve payment records sorted by latest timestamp
    history = list(payments_collection.find({"user_id": user_id}).sort("timestamp", -1))

    # Convert MongoDB ObjectId and format timestamp
    for record in history:
        record["_id"] = str(record["_id"])

        # Convert UTC time to IST
        ist_time = record["timestamp"] + timedelta(hours=5, minutes=30)

        record["timestamp"] = ist_time.strftime("%Y-%m-%d %H:%M:%S")

    return jsonify(history), 200


# ---------------- RUN APPLICATION ---------------- #

if __name__ == "__main__":
    # Start Flask development server
    app.run(debug=True, port=5000)
