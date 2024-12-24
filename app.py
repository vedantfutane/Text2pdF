from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response
from fpdf import FPDF
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import os
import psycopg2

# Flask app setup
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'c3d4f4e8e3c1b89d33c15bbcd2e827vf')  # Secure the secret key
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL','postgresql://text2pdf_database_user:g2D7U2aB2yRAi99PoxqALJxaGmYAt3wk@dpg-ctl3fk5umphs73d6v680-a.oregon-postgres.render.com/text2pdf_database')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database and migration
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Define the database models
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class PDFFile(db.Model):
    __tablename__ = 'pdf_files'
    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(100), nullable=False)
    file_data = db.Column(db.LargeBinary, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    username = db.Column(db.String(50), nullable=False)

# Define the PDF generator class
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

        # Check if the username or email already exists
        existing_user_by_username = User.query.filter_by(username=username).first()
        existing_user_by_email = User.query.filter_by(email=email).first()

        if existing_user_by_username:
            flash("Username already exists. Please choose a different one.", "danger")
            return redirect(url_for('register'))

        if existing_user_by_email:
            flash("Email already exists. Please use a different one.", "danger")
            return redirect(url_for('register'))

        try:
            # Add new user to the database
            new_user = User(username=username, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {e}", "danger")
    
    return render_template("register.html")


# Login route
@app.route('/login', methods=["GET", "POST"])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id  # Store user ID in the session
            flash("Login successful!", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid credentials. Please try again.", "danger")
    
    return render_template('login.html')



# Home route
@app.route('/')
def index():
    # Check if the user is logged in
    if 'user_id' not in session:
        flash("Please log in to access this page.", "warning")
        return redirect(url_for('login'))
    
    # Retrieve the username of the logged-in user
    user = User.query.get(session['user_id'])
    if user:
        return render_template('index.html', username=user.username)
    else:
        flash("User not found. Please log in again.", "danger")
        return redirect(url_for('login'))

# Define the PDF generator class
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", size=12)
        self.cell(0, 10, "Text2PDF Conversion", ln=True, align="C")

# Convert to PDF route
@app.route('/convert', methods=["POST"])
def convert_to_pdf():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    text = request.form.get("text", "")
    font_style = request.form.get("font_style", "Arial")
    font_size = int(request.form.get("font_size", 12))
    font_color = request.form.get("font_color", "#000000")

    # Check for selected styles
    bold = 'bold' in request.form
    italic = 'italic' in request.form
    underline = 'underline' in request.form

    # Replace quotes
    text = text.replace("’", "'").replace("“", '"').replace("”", '"')
    font_color_rgb = tuple(int(font_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))

    # Create the PDF
    pdf = PDF()
    pdf.add_page()
    pdf.set_text_color(*font_color_rgb)
    pdf.set_font(font_style, size=font_size)

    # Apply styles based on user input
    styles = ''
    if bold:
        styles += 'B'
    if italic:
        styles += 'I'
    if underline:
        styles += 'U'

    pdf.set_font(font_style, style=styles)

    # Write the styled text to the PDF
    pdf.multi_cell(0, 10, text)

    # Save PDF to database (optional step)
    pdf_output = pdf.output(dest="S").encode("latin1")
    user = User.query.get(session['user_id'])

    try:
        # Create a new PDFFile record
        new_pdf = PDFFile(
            file_name="text_to_pdf.pdf",
            file_data=pdf_output,
            user_id=user.id,
            username=user.username
        )
        db.session.add(new_pdf)
        db.session.commit()  # Save to the database

    except Exception as e:
        db.session.rollback()
        flash(f"Error saving PDF file: {e}", "danger")
    
    # Return the PDF file to the user
    response = make_response(pdf_output)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=text_to_pdf.pdf"
    return response


# Logout route
@app.route('/logout')
def logout():
    session.clear()
    print("Session after clearing:", session)  # Debug log
    return redirect(url_for('login'))



if __name__ == '__main__':
    app.run(debug=True)
