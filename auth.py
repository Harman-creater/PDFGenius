from flask import Flask, request, jsonify
import sqlite3
import uuid
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from smtplib import SMTP
from email.mime.text import MIMEText


app = Flask(__name__)

# Initialize the database
def init_db():
    """Initialize the database and create the users table if it doesn't exist."""
    try:
        conn = sqlite3.connect("auth.db")
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                reset_token TEXT
            )
        ''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database initialization error: {e}")
    finally:
        conn.close()

# Call the init_db function to set up the database
init_db()

# Email configuration
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USERNAME = 'your_email@gmail.com'
SMTP_PASSWORD = 'your_email_password'

def send_email(to_email, subject, body):
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SMTP_USERNAME
        msg['To'] = to_email

        with SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, to_email, msg.as_string())
    except Exception as e:
        print(f"Failed to send email: {e}")

# Route for forgot password
@app.route('/forgot_password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({"error": "Email is required"}), 400

    try:
        conn = sqlite3.connect("auth.db")
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "Email not registered"}), 404

        # Generate reset token
        reset_token = str(uuid.uuid4())
        cursor.execute("UPDATE users SET reset_token = ? WHERE email = ?", (reset_token, email))
        conn.commit()

        # Send reset token via email
        reset_link = f"http://127.0.0.1:5000/reset_password?token={reset_token}"
        send_email(email, "Password Reset Request", f"Click the link to reset your password: {reset_link}")

        return jsonify({"message": "Password reset email sent"}), 200
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        conn.close()

# Route to reset password
@app.route('/reset_password', methods=['POST'])
def reset_password():
    data = request.get_json()
    reset_token = data.get('reset_token')
    new_password = data.get('new_password')

    if not reset_token or not new_password:
        return jsonify({"error": "Reset token and new password are required"}), 400

    try:
        conn = sqlite3.connect("auth.db")
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE reset_token = ?", (reset_token,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "Invalid reset token"}), 400

        hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
        cursor.execute("UPDATE users SET password = ?, reset_token = NULL WHERE reset_token = ?", (hashed_password, reset_token))
        conn.commit()

        return jsonify({"message": "Password reset successful"}), 200
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        conn.close()

# Route for user signup
@app.route('/signup', methods=['POST'])
def signup():
    """Endpoint for user signup."""
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    # Validate input fields
    if not username or not email or not password:
        return jsonify({"error": "All fields are required"}), 400

    # Hash the password for secure storage
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256') 

    try:
        conn = sqlite3.connect("auth.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)", 
            (username, email, hashed_password)
        )
        conn.commit()
        return jsonify({"message": "User registered successfully"}), 201
    except sqlite3.IntegrityError as e:
        error_message = "Username or email already exists" if "UNIQUE" in str(e) else "Database error"
        return jsonify({"error": error_message}), 400
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        conn.close()

# Route for user login
@app.route('/login', methods=['POST'])
def login():
    """Endpoint for user login."""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # Validate input fields
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    try:
        conn = sqlite3.connect("auth.db")
        cursor = conn.cursor()

        # Assuming the "users" table has columns like: id, username, email, password_hash
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        # Check if user exists and password matches
        if user and check_password_hash(user[3], password):  # Password is in the 4th column (index 3)
            return jsonify({"message": "Login successful", "username": user[1]}), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401

    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    finally:
        conn.close()

@app.route('/view_users', methods=['GET'])
def view_users():
    try:
        conn = sqlite3.connect('auth.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")  # Modify as necessary
        rows = cursor.fetchall()
        conn.close()

        # Return the rows as a JSON response
        return jsonify(rows)
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    
# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)