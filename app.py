from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response
from fpdf import FPDF
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
import io
import os

DATABASE_URL = os.environ.get('DATABASE_URL')  # This gets the URL from Render's environment variable
conn = psycopg2.connect(DATABASE_URL, sslmode='require')

app = Flask(__name__)
app.secret_key = 'c3d4f4e8e3c1b89d33c15bbcd2e827vf'  # Set a secret key for session management

# Database connection
def get_db_connection():
    print("Opening new DB connection")
    conn = psycopg2.connect(
        host="localhost",
        database="testdb1",
        user="postgres",
        password="Vedant@123"
    )
    return conn


class PDF(FPDF):
    def header(self):
        self.set_font("Arial", size=12)
        self.cell(0, 10, "Text to PDF Conversion", ln=True, align="C")

# Register route
@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            # Insert user data into the database
            cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", 
                        (username, email, hashed_password))
            conn.commit()
            flash("Registration successful! Please log in.")
            return redirect(url_for('login'))
        except Exception as e:
            conn.rollback()
            flash(f"Error: {e}")
        finally:
            cur.close()
            conn.close()
        
    return render_template("register.html")

# Login route
@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        
        if user and check_password_hash(user[3], password):  # user[3] is the password
            session['user_id'] = user[0]  # Store user ID in the session
            flash("Login successful!")
            return redirect(url_for('index'))  # Redirect to home page after login
        else:
            flash("Invalid credentials, please try again.")
        
        cur.close()
        conn.close()
    
    return render_template("login.html")

# Home page (protected route)
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get the username of the logged-in user
    username = None
    try:
        conn = get_db_connection()  # Open the connection
        
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE id = %s", (session['user_id'],))
        user = cur.fetchone()
        
        if user:
            username = user[0]  # Assign the fetched username
        else:
            username = "Unknown User"
        
        cur.close()  # Close the cursor after the query
    except Exception as e:
        print(f"Error: {e}")
        username = "Error retrieving username"
    finally:
        # Ensure that the connection is closed after the query is completed
        if conn:
            conn.close()
    
    return render_template("index.html", username=username)

# Convert to PDF route (protected)
@app.route('/convert', methods=["POST"])
def convert_to_pdf():
    if 'user_id' not in session:
        print("No user logged in!")  # Debugging message
        return redirect(url_for('login'))

    # Get form inputs
    text = request.form.get("text", "")
    font_style = request.form.get("font_style", "Arial")
    font_size = int(request.form.get("font_size", 12))
    font_color = request.form.get("font_color", "#000000")

    # Replace unsupported characters
    text = text.replace("’", "'").replace("“", '"').replace("”", '"')

    # Convert hex color to RGB
    font_color_rgb = tuple(int(font_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))

    # Create PDF
    pdf = PDF()
    pdf.add_page()
    pdf.set_text_color(*font_color_rgb)
    pdf.set_font(font_style, size=font_size)
    pdf.multi_cell(0, 10, text)

    # Output PDF for download
    pdf_output = pdf.output(dest="S").encode("latin1")

    username = None

    try:
        # Open a new connection for saving PDF file data to the database
        conn = get_db_connection()  # Open a new connection
        cur = conn.cursor()

        # Check if user_id is correctly set in the session
        user_id = session.get('user_id')
        print(f"User ID (from session): {user_id}")  # Debugging message

        # Check if user_id is None
        if user_id is None:
            print("User ID is None! Cannot insert PDF.")  # Debugging message
            flash("You need to log in first.")
            return redirect(url_for('login'))
        
        cur.execute("SELECT username FROM users WHERE id = %s", (session['user_id'],))
        user = cur.fetchone()
        
        if user:
            username = user[0]  # Assign the fetched username
        else:
            username = "Unknown User"

        # Insert PDF file data into the database
        cur.execute("INSERT INTO pdf_files (file_name, file_data, user_id, username) VALUES (%s, %s, %s, %s)", 
                    ("text_to_pdf.pdf", pdf_output, user_id, username))

        # Commit the transaction
        conn.commit()
        print("PDF file saved to database successfully.")  # Debugging message

        # Close the cursor and connection
        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error: {e}")  # Debugging message
        flash("Error saving PDF file to database.")

    # Send the PDF file to the user as a response
    response = make_response(pdf_output)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=text_to_pdf.pdf"
    return response

if __name__ == '__main__':
    app.run(debug=True)
