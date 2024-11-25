from flask import *
import pymysql
import bcrypt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import matplotlib.pyplot as plt
from pymysql.cursors import DictCursor  # Import the DictCursor class
import io
import os
from models import *
from werkzeug.utils import secure_filename
import base64
from config import Config
import datetime
import requests
from requests.auth import HTTPBasicAuth
from werkzeug.security import generate_password_hash  # For password hashing

import matplotlib
matplotlib.use('Agg') 

app = Flask(__name__)
app.config.from_object(Config)

# Secret key for session management (to enable flash messages)
# Instead of hardcoding, get it from the environment
app.secret_key = os.getenv('SECRET_KEY', 'default-secret-key-for-local-development')  # Default for local dev


@app.route('/admin/dashboard')
def dashboard():
    # Connect to the database
    connection = get_db_connection()
    # Initialize variables
    total_users = 0
    total_recipes = 0
    total_events = 0
    total_volunteers = 0
    recent_activities = []
    unread_notifications_count = 0  # Initialize unread message count

    try:
        with connection.cursor() as cursor:
            # Query for total users
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]

            # Query for total recipes
            cursor.execute("SELECT COUNT(*) FROM recipes")
            total_recipes = cursor.fetchone()[0]

            # Query for total events
            cursor.execute("SELECT COUNT(*) FROM events")
            total_events = cursor.fetchone()[0]

            # Query for total volunteers
            cursor.execute("SELECT COUNT(*) FROM volunteers")
            total_volunteers = cursor.fetchone()[0]

            # Query for the 5 most recent activities
            cursor.execute("SELECT activity, timestamp FROM activities ORDER BY timestamp DESC LIMIT 5")
            recent_activities = cursor.fetchall()

            # Query for the count of unread messages (those with is_read = 0)
            cursor.execute("SELECT COUNT(*) FROM contact_messages WHERE is_read = FALSE")
            unread_notifications_count = cursor.fetchone()[0]  # Fetch the count

    finally:
        connection.close()

    # Pie Chart Data (this can be dynamically generated from your database or any other source)
    event_data = {
        'Event A': 300,
        'Event B': 50,
        'Event C': 100,
    }

    # Prepare data for the pie chart
    labels = event_data.keys()
    sizes = event_data.values()
    colors = ['#ff6384', '#36a2eb', '#ffcd56']  # Custom colors

    # Create a figure and axis for plotting
    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
    ax.axis('equal')  # Ensures the pie chart is circular

    # Save the plot to a BytesIO object (this allows us to send the image as base64 to the template)
    img = io.BytesIO()
    plt.savefig(img, format='png')  # Save figure as PNG in memory
    img.seek(0)  # Move the pointer to the beginning of the image
    img_b64 = base64.b64encode(img.getvalue()).decode('utf-8')  # Encode image as base64 string

    # Close the plot after saving it to prevent memory issues
    plt.close(fig)

    # Pass the data to the template for rendering
    return render_template('admin/dashboard.html', 
                           total_users=total_users, 
                           total_recipes=total_recipes, 
                           total_events=total_events, 
                           total_volunteers=total_volunteers,
                           recent_activities=recent_activities, 
                           pie_chart_data=img_b64,
                           unread_notifications_count=unread_notifications_count)

@app.route('/admin/manage_users')
def manage_users():
    # Get users from the database
    connection = get_db_connection()
    cursor = connection.cursor()

    # Query to get all users
    cursor.execute("SELECT * FROM users")  # Modify based on your table schema
    users = cursor.fetchall()  

    # Close the database connection
    cursor.close()
    connection.close()

    # Render the template and pass the users data
    return render_template('admin/manage_users.html', users=users)

@app.route('/staffs', methods=['GET'])
def staffs():
    search_query = request.args.get('search', '')
    
    connection = get_db_connection()

    members = []
    try:
        with connection.cursor() as cursor:
            # Query to search members by name or position
            cursor.execute("""
                SELECT id, name, position, image, email 
                FROM members 
                WHERE status = 'active' 
                AND (name LIKE %s OR position LIKE %s)
                ORDER BY position
            """, (f'%{search_query}%', f'%{search_query}%'))
            members = cursor.fetchall()
    finally:
        connection.close()

    return render_template('staffs.html', members=members)


# Set the upload folder for images and allowed file extensions
app.config['UPLOAD_FOLDER'] = 'static/images/'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/admin/add_member', methods=['GET', 'POST'])
def add_member():
    if request.method == 'POST':
        # Get data from the form
        name = request.form['name']
        position = request.form['position']
        email = request.form.get('email', None)  
        status = request.form['status']

        # Handle image upload 
        image_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                # Secure the file name
                image_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
        
        # Insert data 
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                
                cursor.execute("""
                    INSERT INTO members (name, position, email, image, status)
                    VALUES (%s, %s, %s, %s, %s)
                """, (name, position, email, image_filename, status))
                connection.commit()  
            
            return render_template('admin/dashboard.html', success='Member added successfully!')

        except Exception as e:
            
            connection.rollback()
            return render_template('admin/add_member.html', error=f"Error: {e}")
        finally:
            connection.close()

    # Render the form for GET requests
    return render_template('admin/add_member.html')

@app.route('/view_notifications')
def view_notifications():
    # Fetch notifications from the database (this is just a placeholder)
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM contact_messages WHERE is_read = 0")  # Example query
        notifications = cursor.fetchall()

    return render_template('admin/view_notifications.html', notifications=notifications)


# Function to log activity
def log_activity(activity_description):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO activities (activity, timestamp) VALUES (%s, %s)", (activity_description, datetime.now()))
    conn.commit()  # Commit the transaction
    cursor.close()
    conn.close()

# Example route for user login
@app.route('/user_login', methods=['POST'])
def user_login():
    username = request.form['username']  # Get the username
    log_activity(f"User {username} logged in")
    return "Login successful!"

# Route to display recent activities
@app.route('/recent-activities')
def recent_activities_view():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT activity, timestamp FROM activities ORDER BY timestamp DESC LIMIT 5")
    recent_activities = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('recent_activities.html', recent_activities=recent_activities)



# SMTP Configuration (Your email server details)
SENDER_EMAIL = "your_email@example.com"  # Your email address
RECEIVER_EMAIL = "admin_email@example.com"  # Admin's email address
SMTP_SERVER = "smtp.example.com"  # SMTP server (e.g., Gmail)
SMTP_PORT = 587  # Usually 587 for TLS
SMTP_PASSWORD = "your_email_password"  # Your email password or app password

# Send notification to admin
def send_admin_notification(message_details):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL  # Your email address
    msg['To'] = RECEIVER_EMAIL  # Admin email
    msg['Subject'] = f"New Contact Form Submission: {message_details['subject']}"

    body = f"""
    New message from: {message_details['name']} ({message_details['email']})
    
    Message:
    {message_details['message']}
    """
    msg.attach(MIMEText(body, 'plain'))

    # Send the email using your SMTP configuration
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Start TLS encryption
        server.login(SENDER_EMAIL, SMTP_PASSWORD)  # Login to the SMTP server
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())  # Send the email
        server.quit()
        print("Email sent successfully to admin!")
    except Exception as e:
        print(f"Error sending email: {e}")

# Route to show the contact form and handle submission
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        subject = request.form['subject']
        message = request.form['message']

        # Save message to the database
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO contact_messages (name, email, subject, message) VALUES (%s, %s, %s, %s)",
                (name, email, subject, message)
            )
            connection.commit()

        # Send a notification to the admin
        send_admin_notification({
            'name': name,
            'email': email,
            'subject': subject,
            'message': message
        })

        flash('Your message has been sent successfully!', 'success')
        return redirect(url_for('contact'))

    return render_template('contact.html')



# Route to view a specific message
@app.route('/view_message/<int:message_id>')
def view_message(message_id):
    connection = get_db_connection()
    with connection.cursor() as cursor:
        # Mark the message as read
        cursor.execute("UPDATE contact_messages SET is_read = 1 WHERE id = %s", (message_id,))
        connection.commit()

        # Retrieve the message details to display
        cursor.execute("SELECT * FROM contact_messages WHERE id = %s", (message_id,))
        message = cursor.fetchone()

    return render_template('view_message.html', message=message)

@app.route('/mark_as_read/<int:notification_id>', methods=['POST'])
def mark_as_read(notification_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Update the notification to mark it as read
            cursor.execute("UPDATE contact_messages SET is_read = TRUE WHERE id = %s", (notification_id,))
            connection.commit()
        
        # Flash a success message
        flash('Notification marked as read.', 'success')
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
    finally:
        connection.close()
    
    return redirect(url_for('view_notifications'))


@app.route('/reply_to_notification/<int:notification_id>', methods=['POST'])
def reply_to_notification(notification_id):
    # Get the reply message from the form
    reply_message = request.form['reply_message']
    
    # Fetch the original message details from the database
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT email, name, subject,created_at FROM contact_messages WHERE id = %s", (notification_id,))
        notification = cursor.fetchone()

    if notification:
        user_email = notification['email']
        user_name = notification['name']
        subject = "Re: " + notification['subject']  # Optional: Prefix subject with "Re:"

        # Email settings (Make sure to replace with your email service details)
        sender_email = "owinoteddy1997@.com"
        sender_password = ""
        smtp_server = "smtp.gmail.com"
        smtp_port = 587

        # Compose the email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = user_email
        msg['Subject'] = subject

        body = f"Hello {user_name},\n\n{reply_message}\n\nBest regards,\nCommunity Harvest Admin"
        msg.attach(MIMEText(body, 'plain'))

        # Send the email using SMTP
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()  # Secure connection
                server.login(sender_email, sender_password)
                text = msg.as_string()
                server.sendmail(sender_email, user_email, text)
            flash('Reply sent successfully!', 'success')
        except Exception as e:
            flash(f'Failed to send reply: {e}', 'danger')

    return redirect(url_for('view_notifications'))

# Database connection function
def get_db_connection():
    connection = get_db_connection()
    return connection

# User-related functions
def create_user(username, first_name, last_name, email, password, phone_number, address):
    connection = get_db_connection()
    cursor = connection.cursor()
    hashed_password = generate_password_hash(password)  # Hash the password
    cursor.execute("""
        INSERT INTO users (username, first_name, last_name, email, password, phone_number, address)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (username, first_name, last_name, email, hashed_password, phone_number, address))
    connection.commit()
    cursor.close()
    connection.close()

def get_all_users():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    cursor.close()
    connection.close()
    return users



# Event-related functions
def create_event(title, date, location, description, organizer, max_participants, status):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO events (title, date, location, description, organizer, max_participants, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (title, date, location, description, organizer, max_participants, status))
    connection.commit()
    cursor.close()
    connection.close()
    print(f"Event '{title}' has been created successfully!")

def get_all_events():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM events")
    events = cursor.fetchall()
    cursor.close()
    connection.close()
    return events

# Recipe-related functions
def create_recipe(title, ingredients, instructions, prep_time, cook_time, serving_size, difficulty_level, cuisine_type):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO recipes (title, ingredients, instructions, prep_time, cook_time, serving_size, difficulty_level, cuisine_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (title, ingredients, instructions, prep_time, cook_time, serving_size, difficulty_level, cuisine_type))
    connection.commit()
    cursor.close()
    connection.close()
    print(f"Recipe '{title}' added successfully!")


def get_all_recipes():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM recipes")
    recipes = cursor.fetchall()
    cursor.close()
    connection.close()
    return recipes

# Volunteer-related functions
def create_volunteer(name, email, phone_number, skills, availability, volunteer_area):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO volunteers (name, email, phone_number, skills, availability, volunteer_area)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (name, email, phone_number, skills, availability, volunteer_area))
    connection.commit()
    cursor.close()
    connection.close()
    print(f"Volunteer {name} signed up successfully!")

def get_all_volunteers():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM volunteers")
    volunteers = cursor.fetchall()
    cursor.close()
    connection.close()
    return volunteers

# Routes
@app.route('/')
def index():
    users = get_all_users()
    events = get_all_events()
    recipes = get_all_recipes()
    volunteers = get_all_volunteers()
    return render_template('index.html', users=users, events=events, recipes=recipes, volunteers=volunteers)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Extract form data
        username = request.form['username']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']  # Get confirm password
        phone_number = request.form['phone_number']
        address = request.form['address']
        
        # Set default role to "user" for all registrations
        role = 'user'

        # Validate input fields
        if not username or not password or not email:
            flash('Please provide all required fields', 'danger')
            return redirect(url_for('register'))
        
        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return redirect(url_for('register'))

        # Hash the password using bcrypt
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Check if the email or username already exists
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s OR username = %s", (email, username))
        existing_user = cursor.fetchone()
        
        if existing_user:
            flash('Username or email already exists. Please try again with a different one.', 'danger')
            return redirect(url_for('register'))

        # Insert new user into the database
        try:
            cursor.execute("""
                INSERT INTO users (username, first_name, last_name, email, password, phone_number, address, role) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (username, first_name, last_name, email, hashed_pw, phone_number, address, role))
            connection.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))  
        except Exception as e:
            connection.rollback()  # Rollback transaction in case of error
            flash(f'An error occurred: {e}', 'danger')
            return redirect(url_for('register'))  # Redirect back to registration page on error
        finally:
            cursor.close()
            connection.close()

    # If GET request, render registration page
    return render_template('register.html')

@app.route('/recipe', methods=['GET', 'POST'])
def recipe():
    if request.method == 'POST':
        # Retrieve data from the form
        title = request.form['title']
        ingredients = request.form['ingredients']
        instructions = request.form['instructions']
        prep_time = request.form['prep_time']
        cook_time = request.form['cook_time']
        serving_size = request.form['serving_size']
        difficulty_level = request.form['difficulty_level']
        cuisine_type = request.form['cuisine_type']
        
        # Call the create_recipe function to insert data into the database
        create_recipe(title, ingredients, instructions, prep_time, cook_time, serving_size, difficulty_level, cuisine_type)

        # Flash a success message
        flash('Recipe added successfully!', 'success')
        
        # Redirect to the homepage or a success page
        return redirect(url_for('information'))

    # If the request method is GET (initial page load), render the form
    return render_template('recipe.html')  # The template for the recipe form


@app.route('/admin/manage_events', methods=['GET', 'POST'] )
def manage_events():
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute('SELECT * FROM events')
        events = cursor.fetchall()
    connection.close()
    return render_template('admin/manage_events.html', events=events)


@app.route('/admin/manage_recipes', methods=['GET', 'POST'])
def manage_recipes():
    # Connect to the database
    connection = get_db_connection()
    with connection.cursor() as cursor:
        # Query to fetch all recipes from the database
        cursor.execute('SELECT * FROM recipes')  # Assuming there's a 'recipes' table
        recipes = cursor.fetchall()  # Fetch all rows from the query
    
    connection.close()
    
    # Pass the recipes data to the template
    return render_template('admin/manage_recipes.html', recipes=recipes)



# Route to manage volunteers
@app.route('/admin/manage_volunteers', methods=['GET', 'POST'])
def manage_volunteers():
    # Connect to the database
    connection = get_db_connection()
    with connection.cursor() as cursor:
        # Fetch all volunteers
        cursor.execute("SELECT * FROM volunteers")
        volunteers = cursor.fetchall()  # Fetch all records from the volunteers table
    connection.close()

    # Render the HTML template and pass the volunteers data
    return render_template('admin/manage_volunteers.html', volunteers=volunteers)


# Route to manage donations
@app.route('/admin/manage_donations', methods=['GET', 'POST'])
def manage_donations():
    # Connect to the database
    connection = get_db_connection()
    with connection.cursor() as cursor:
        # Fetch all donations
        cursor.execute("SELECT id, name, phone, amount, donation_time FROM donations ORDER BY donation_time DESC")
        donations = cursor.fetchall()  # Fetch all records from the donations table
    connection.close()

    # Render the HTML template and pass the donations data
    return render_template('admin/donation_records.html', donations=donations)



@app.route('/volunteer', methods=['GET', 'POST'])
def volunteer():
    if request.method == 'POST':
        # Retrieve form data
        name = request.form['name']
        email = request.form['email']
        phone_number = request.form['phone_number']
        skills = request.form['skills']
        availability = request.form['availability']
        volunteer_area = request.form['volunteer_area']

        # Insert into the database
        create_volunteer(name, email, phone_number, skills, availability, volunteer_area)
        
        # Flash success message
        flash('Volunteer added successfully!', 'success')
        return redirect(url_for('information'))  # Redirect to manage volunteers page

    return render_template('volunteer.html')  # Render the add volunteer form

@app.route('/admin/delete_volunteer/<int:volunteer_id>', methods=['GET'])
def delete_volunteer(volunteer_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    # Delete query
    cursor.execute("DELETE FROM volunteers WHERE id = %s", (volunteer_id,))
    connection.commit()
    
    flash('Volunteer deleted successfully!', 'danger')
    cursor.close()
    connection.close()

    return redirect(url_for('manage_volunteers'))


@app.route('/admin/edit_volunteer/<int:volunteer_id>', methods=['GET', 'POST'])
def edit_volunteer(volunteer_id):
    connection = get_db_connection()

    cursor = connection.cursor()

    if request.method == 'POST':
        # Retrieve updated form data
        name = request.form['name']
        email = request.form['email']
        phone_number = request.form['phone_number']
        skills = request.form['skills']
        availability = request.form['availability']
        volunteer_area = request.form['volunteer_area']

        # Update query to modify volunteer data
        update_query = """
        UPDATE volunteers
        SET name=%s, email=%s, phone_number=%s, skills=%s, availability=%s, volunteer_area=%s
        WHERE id=%s
        """
        cursor.execute(update_query, (name, email, phone_number, skills, availability, volunteer_area, volunteer_id))
        connection.commit()
        flash('Volunteer updated successfully!', 'success')
        return redirect(url_for('manage_volunteers'))

    # Retrieve current volunteer data
    cursor.execute("SELECT * FROM volunteers WHERE id = %s", (volunteer_id,))
    volunteer = cursor.fetchone()

    # Close the connection
    cursor.close()
    connection.close()

    return render_template('admin/edit_volunteer.html', volunteer=volunteer)


@app.route('/admin/delete_event/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    # Delete event from the database
    cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))
    connection.commit()
    
    flash('Event deleted successfully!', 'danger')
    
    cursor.close()
    connection.close()

    return redirect(url_for('manage_events'))


@app.route('/admin/delete_user/<int:user_id>', methods=['GET'])
def delete_user(user_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    # Delete query
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    connection.commit()
    flash('User deleted successfully!', 'danger')
    cursor.close()
    connection.close()

    return redirect(url_for('manage_users'))

@app.route('/admin/delete_recipe/<int:recipe_id>', methods=['POST'])
def delete_recipe(recipe_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    # Delete recipe from the database
    cursor.execute("DELETE FROM recipes WHERE id = %s", (recipe_id,))
    connection.commit()
    
    flash('Recipe deleted successfully!', 'danger')
    
    cursor.close()
    connection.close()

    return redirect(url_for('manage_recipes'))


@app.route('/admin/event',  methods=['GET', 'POST'])
def event():
    if request.method == 'POST':
        # Extract form data
        title = request.form['title']
        date = request.form['date']
        location = request.form['location']
        description = request.form['description']
        organizer = request.form['organizer']
        max_participants = int(request.form['max_participants'])
        status = request.form['status']
        
        # Validate form input
        if not title or not date or not location:
            flash('Title, date, and location are required.', 'danger')
            return redirect(url_for('event'))  # Stay on the add event page
        
        # Create the event (for now, just print to console, replace with actual database save)
        create_event(title, date, location, description, organizer, max_participants, status)
        
        flash('Event added successfully!', 'success')
        return redirect(url_for('information'))  # Redirect to the home page or events list page
     # Display the event creation form

    return render_template('admin/event.html') 


@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        phone_number = request.form['phone_number']
        address = request.form['address']

        cursor.execute("""
        UPDATE users
        SET username=%s, email=%s, first_name=%s, last_name=%s, phone_number=%s, address=%s
        WHERE id=%s
        """, (username, email, first_name, last_name, phone_number, address, user_id))
        connection.commit()
        flash('User updated successfully!', 'success')
        cursor.close()
        connection.close()

        return redirect(url_for('manage_users'))

    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    cursor.close()
    connection.close()

    return render_template('admin/edit_user.html', user=user)


# @app.route('/volunteer')
# def volunteer():
#     return render_template('volunteer.html') 
@app.route('/admin/edit_recipe/<int:recipe_id>', methods=['GET', 'POST'])
def edit_recipe(recipe_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    # Handling the form submission (POST method)
    if request.method == 'POST':
        # Retrieving form data
        name = request.form['name']
        category = request.form['category']
        ingredients = request.form['ingredients']
        instructions = request.form['instructions']

        # Update the recipe in the database
        cursor.execute("""
            UPDATE recipes
            SET name = %s, category = %s, ingredients = %s, instructions = %s
            WHERE id = %s
        """, (name, category, ingredients, instructions, recipe_id))
        connection.commit()
        flash('Recipe updated successfully!', 'success')

        cursor.close()
        connection.close()

        return redirect(url_for('manage_recipes'))

    # Handling the GET request: fetching the current recipe details
    cursor.execute("SELECT * FROM recipes WHERE id = %s", (recipe_id,))
    recipe = cursor.fetchone()

    cursor.close()
    connection.close()

    # Rendering the edit form with the current recipe details
    return render_template('admin/edit_recipe.html', recipe=recipe)


@app.route('/admin/edit_event/<int:event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    # Handling the form submission (POST method)
    if request.method == 'POST':
        # Retrieving form data
        title = request.form['title']
        date = request.form['date']
        location = request.form['location']
        description = request.form['description']
        organizer = request.form['organizer']
        max_participants = request.form['max_participants']
        status = request.form['status']

        # Update the event in the database
        cursor.execute("""
            UPDATE events
            SET title = %s, date = %s, location = %s, description = %s, organizer = %s, 
                max_participants = %s, status = %s
            WHERE id = %s
        """, (title, date, location, description, organizer, max_participants, status, event_id))
        connection.commit()
        flash('Event updated successfully!', 'success')

        cursor.close()
        connection.close()

        return redirect(url_for('manage_events'))

    # Handling the GET request: fetching the current event details
    cursor.execute("SELECT * FROM events WHERE id = %s", (event_id,))
    event = cursor.fetchone()

    cursor.close()
    connection.close()

    # Rendering the edit form with the current event details
    return render_template('admin/edit_event.html', event=event)



@app.route('/admin/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        phone_number = request.form['phone_number']
        address = request.form['address']
        password = request.form['password']  # Hash the password in production

        # Insert the user into the database
        connection = get_db_connection()
    
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO users (username, email, first_name, last_name, phone_number, address, password)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (username, email, first_name, last_name, phone_number, address, password))
        connection.commit()
        cursor.close()
        connection.close()

        flash('User added successfully!', 'success')
        return redirect(url_for('manage_users'))

    return render_template('admin/add_user.html')



# Your MPesa credentials (sandbox example)
consumer_key = "YourConsumerKey"  # Replace with your actual consumer key
consumer_secret = "YourConsumerSecret"  # Replace with your actual consumer secret
shortcode = "174379"  # Your M-Pesa Shortcode (for Lipa Na M-Pesa)
lipa_na_mpesa_online_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"  # STK Push URL for sandbox
api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"  # OAuth URL

# Your M-Pesa passkey (replace with your actual passkey)
passkey = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'  # Use your actual passkey here

# Callback URL where Safaricom will send the payment result
callback_url = "https://yourdomain.com/payment_callback"  # Replace with your actual callback URL

# Function to get access token for MPesa
def get_access_token():
    response = requests.get(api_url, auth=HTTPBasicAuth(consumer_key, consumer_secret))
    response_data = response.json()
    access_token = response_data.get("access_token")
    return "Bearer " + access_token

# Function to initiate the MPesa payment request (STK Push)
def mpesa_payment(amount, phone):
    # Generate token
    access_token = get_access_token()

    # Prepare request payload
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    
    # Generate password (Base64 encoding of the shortcode + passkey + timestamp)
    data = shortcode + passkey + timestamp
    password = base64.b64encode(data.encode()).decode()

    # Payment request payload
    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,  # Donor's phone number (Kenya format)
        "PartyB": shortcode,  # Your business shortcode
        "PhoneNumber": phone,  # Donor's phone number (same as PartyA)
        "CallBackURL": callback_url,  # Your callback URL
        "AccountReference": "Donation",  # This can be customized
        "TransactionDesc": "Donation"  # This can be customized
    }

    # Headers for the request
    headers = {
        "Authorization": access_token,
        "Content-Type": "application/json"
    }

    # Make the request to the M-Pesa API for STK push
    response = requests.post(lipa_na_mpesa_online_url, json=payload, headers=headers)

    # Return the response from the M-Pesa API
    return response.json()

# Route to render the donation page
# @app.route('/donate', methods=['GET'])
# def donate_page():
#     return render_template('donation.html')  # Donation page with form for amount and phone number
@app.route('/training')
def training():
    return render_template('training.html')

# Route to render the donation page
@app.route('/about')
def about():
    return render_template('about.html')  


@app.route('/information')
def information():
    # Connect to the MySQL database
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            # Query to fetch events with status 'Upcoming'
            cursor.execute("SELECT id, title, date, location, description, organizer, max_participants, status FROM events WHERE status = 'Upcoming' ORDER BY date")
            events = cursor.fetchall()  # Fetch all upcoming events

        # Render the template and pass the events data to it
        return render_template('information.html', events=events)
    
    except pymysql.MySQLError as e:
        print(f"Error: {e}")
        return "Database connection error", 500
    
    finally:
        connection.close()  # Always close the connection after use

@app.route('/food')
def food():
    return render_template('food.html')

@app.route('/foods')
def foods():
    return render_template('foods.html')
# Route to handle donation (initiates MPesa payment)
@app.route('/donate', methods=['GET', 'POST'])
def donate():
    if request.method == 'GET':
        # This handles rendering the donation page
        return render_template('donation.html')  # Render the donation form/page

    elif request.method == 'POST':
        # This handles the donation processing when the form is submitted
        amount = request.form.get('amount')
        phone = request.form.get('phone')
        
        if not amount or not phone:
            return jsonify({'status': 'failure', 'message': 'Missing amount or phone number'}), 400

        # Initiate the MPesa payment process (STK Push)
        response = mpesa_payment(amount, phone)

        if response.get('ResponseCode') == '0':  # Success response from M-Pesa
            return jsonify({'status': 'success', 'message': 'Payment initiated successfully!'}), 200
        else:
            return jsonify({'status': 'failure', 'message': 'Failed to initiate payment.'}), 400


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get the form data (username/email and password)
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Please provide both username and password.', 'danger')
            return redirect(url_for('login'))  # Redirect to login page

        # Check if the user exists in the database
        connection = get_db_connection()
        cursor = connection.cursor(DictCursor)  # Use DictCursor for easier column access
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user:
            # Compare hashed password
            stored_password_hash = user['password']  # Assuming password is stored in 'password' field
            if bcrypt.checkpw(password.encode('utf-8'), stored_password_hash.encode('utf-8')):

                # Valid user, store user info in session
                session['user_id'] = user['id']  # Store the user ID in the session
                session['role'] = user['role']  # Store the role (admin/user) in the session
                
                flash('Login successful!', 'success')

                # Redirect based on the user's role
                if user['role'] == 'admin':
                    return redirect(url_for('dashboard'))  # Admin dashboard
                else:
                    return redirect(url_for('index'))  # User dashboard (for regular users)

            else:
                flash('Invalid username or password.', 'danger')
        else:
            flash('Invalid username or password.', 'danger')

        # Close connection
        cursor.close()
        connection.close()

        return redirect(url_for('login'))  # If login fails, redirect back to login page

    # If GET request, render login page
    return render_template('login.html')



@app.route('/admin/add_admin', methods=['GET', 'POST'])
def add_admin():


    if request.method == 'POST':
        # Collect the form data
        username = request.form.get('username')
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone_number = request.form.get('phone_number')
        address = request.form.get('address')
        password = request.form.get('password')

        # Check if all required fields are filled
        if not username or not email or not password or not first_name or not last_name:
            flash('Please fill out all required fields.', 'danger')
            return redirect(url_for('add_admin'))  # Redirect back to the form if required fields are missing

        # Hash the password
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        try:
            # Insert the new admin into the database
            connection = get_db_connection()
            cursor = connection.cursor()

            # Insert data into the 'users' table, setting the role as 'admin'
            cursor.execute("""
                INSERT INTO users (username, email, first_name, last_name, phone_number, address, password, role)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'admin')
            """, (username, email, first_name, last_name, phone_number, address, hashed_pw))

            # Commit the transaction (save changes to the database)
            connection.commit()

            # Success message
            flash(f'Admin user {username} added successfully!', 'success')
            return redirect(url_for('dashboard'))  # Redirect to the admin dashboard after successful admin creation

        except Exception as e:
            # If there is an error, rollback the transaction and display an error message
            connection.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')

        finally:
            cursor.close()
            connection.close()

    # If it's a GET request, render the Add Admin form
    return render_template('admin/add_admin.html')  # Render the form to add a new admin


@app.route('/payment_result')
def payment_result():
    status = request.args.get('status')
    message = request.args.get('message')
    return render_template('result.html', status=status, message=message)


@app.route('/logout')
def logout():
    # Remove user information from the session
    session.pop('user_id', None)  # Removes 'user_id' from the session
    session.pop('username', None)  # Removes 'username' from the session
    session.pop('role', None)      # Removes 'role' from the session

    # Flash message indicating the user has been logged out
    flash('You have been logged out successfully.', 'success')

    # Redirect the user to the login page
    return redirect(url_for('login'))


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))  # Get port from environment variable (or 5000 if not set)
    app.run(debug=True, host='0.0.0.0', port=port) 
