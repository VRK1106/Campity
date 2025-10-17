from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import heapq
import paypalrestsdk

# Initialize Flask App and extensions
Campity = Flask(__name__)
bcrypt = Bcrypt(Campity)

# App Configuration
Campity.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///campity.db'
Campity.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
Campity.config['SECRET_KEY'] = 'your_super_secret_key'
Campity.config['UPLOAD_FOLDER'] = 'uploads'

# --- PayPal Configuration ---
paypalrestsdk.configure({
    "mode": "sandbox",
    "client_id": "YOUR_PAYPAL_CLIENT_ID",
    "client_secret": "YOUR_PAYPAL_SECRET_KEY"
})
# --- PayPal Configuration ---

db = SQLAlchemy(Campity)

# Create the uploads folder if it doesn't exist
if not os.path.exists(Campity.config['UPLOAD_FOLDER']):
    os.makedirs(Campity.config['UPLOAD_FOLDER'])

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    rating = db.Column(db.Float, default=0.0)

class Task(db.Model):
    task_id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(150), nullable=False)
    task_description = db.Column(db.String(300), nullable=False)
    task_status = db.Column(db.String(50), nullable=False, default='pending')
    reward = db.Column(db.Float, nullable=False)
    reward_type = db.Column(db.String(50), nullable=False)
    deadline = db.Column(db.String(50), nullable=False)
    file_path = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.Column(db.String(50), nullable=False, default='general')
    
    poster_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    accepter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

class Rating(db.Model):
    rating_id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.task_id'), nullable=False)
    poster_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    accepter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with Campity.app_context():
    db.create_all()

# Function to prioritize tasks using a priority queue
def prioritize_tasks(tasks):
    priority_queue = []
    for task in tasks:
        # Define a custom priority score based on category and reward
        priority = task.reward
        if task.category == 'medical':
            priority += 1000
        
        heapq.heappush(priority_queue, (-priority, task))
    
    sorted_tasks = [heapq.heappop(priority_queue)[1] for _ in range(len(priority_queue))]
    return sorted_tasks

@Campity.route('/')
def home():
    return render_template('home.html')

@Campity.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            print("Login Successful")
            return redirect(url_for('dashboard', username=username))
        flash('Invalid username or password. Please try again.')
    return render_template('login.html')

@Campity.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('User already exists. Please log in.')
            return redirect(url_for('login'))
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, password=hashed_password, rating=0.0)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@Campity.route('/dashboard/<username>')
def dashboard(username):
    user = User.query.filter_by(username=username).first_or_404()
    tasks_accepted = Task.query.filter(Task.accepter_id == user.id, Task.task_status != 'completed').all()
    tasks_posted = Task.query.filter(Task.poster_id == user.id, Task.task_status != 'completed').all()
    
    # Fetch available tasks and prioritize them
    available_tasks_from_db = Task.query.filter_by(accepter_id=None).filter(Task.poster_id != user.id).all()
    tasks_available = prioritize_tasks(available_tasks_from_db)
    
    return render_template('dashboard.html', 
                           username=username, 
                           tasks_accepted=tasks_accepted, 
                           tasks_posted=tasks_posted,
                           tasks_available=tasks_available)

@Campity.route('/dashboard/<username>/profile')
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    tasks_accepted_list = Task.query.filter_by(accepter_id=user.id).all()
    tasks_posted_list = Task.query.filter_by(poster_id=user.id).all()
    return render_template('profile.html', 
                           username=username, 
                           user=user, 
                           tasks_accepted_list=tasks_accepted_list, 
                           tasks_posted_list=tasks_posted_list)

@Campity.route('/dashboard/<username>/tasks_available')
def tasks_available(username):
    user = User.query.filter_by(username=username).first_or_404()
    # Fetch available tasks and prioritize them
    available_tasks_from_db = Task.query.filter_by(accepter_id=None).filter(Task.poster_id != user.id).all()
    tasks = prioritize_tasks(available_tasks_from_db)
    
    return render_template('tasks_available.html', 
                           username=username, 
                           tasks=tasks)

@Campity.route('/dashboard/<username>/accept_task/<int:task_id>', methods=['POST'])
def accept_new_task(username, task_id):
    user = User.query.filter_by(username=username).first_or_404()
    task = Task.query.get_or_404(task_id)
    
    if task.accepter_id is not None:
        flash('This task has already been accepted.')
        return redirect(url_for('dashboard', username=username))
    
    task.accepter_id = user.id
    task.task_status = 'accepted'
    db.session.commit()
    
    flash('Task accepted successfully!')
    return redirect(url_for('dashboard', username=username))

@Campity.route('/dashboard/<username>/post_task', methods=['GET', 'POST'])
def post_task(username):
    user = User.query.filter_by(username=username).first_or_404()
    if request.method == 'POST':
        task_name = request.form['task_name']
        task_description = request.form['task_description']
        reward_type = request.form['reward_type']
        deadline = request.form['deadline']
        category = request.form['category']
        
        # Handle conditional reward inputs
        if reward_type == 'cash':
            reward_amount = float(request.form.get('reward_amount', 0.0))
        else: # for 'favor'
            reward_amount = 0.0

        file_path = None
        if 'task_file' in request.files:
            file = request.files['task_file']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                # Corrected: Only save the filename, not the full path
                file.save(os.path.join(Campity.config['UPLOAD_FOLDER'], filename))
                file_path = filename # Store just the filename in the database

        new_task = Task(
            task_name=task_name,
            task_description=task_description,
            reward=reward_amount,
            reward_type=reward_type,
            deadline=deadline,
            poster_id=user.id,
            file_path=file_path,
            category=category
        )
        db.session.add(new_task)
        db.session.commit()
        
        flash('Task posted successfully!')
        return redirect(url_for('dashboard', username=username))
    
    return render_template('post_task.html', username=username)

@Campity.route('/uploads/<path:filename>')
def download_file(filename):
    return send_from_directory(Campity.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# FIX: Renamed route function to view_accepted_task to avoid name conflict with task_accepted
@Campity.route('/dashboard/<username>/my_accepted_tasks/<int:task_id>', methods=['GET', 'POST'])
def view_accepted_task(username, task_id):
    user = User.query.filter_by(username=username).first_or_404()
    task = Task.query.get_or_404(task_id)

    if task.accepter_id != user.id:
        flash('You are not authorized to view this task.')
        return redirect(url_for('dashboard', username=username))
    
    if request.method == 'POST':
        new_status = request.form['task_status']
        task.task_status = new_status
        if new_status == 'completed':
            task.task_status = 'awaiting_rating'
        db.session.commit()
        flash('Task status updated successfully!')
        return redirect(url_for('dashboard', username=username))
    
    return render_template('my_accepted_tasks.html', username=username, task=task)

@Campity.route('/dashboard/<username>/rate_task/<int:task_id>', methods=['GET', 'POST'])
def rate_task(username, task_id):
    poster = User.query.filter_by(username=username).first_or_404()
    task = Task.query.get_or_404(task_id)

    if task.task_status != 'awaiting_rating' or task.poster_id != poster.id:
        flash('This task is not ready to be rated.')
        return redirect(url_for('dashboard', username=username))

    if request.method == 'POST':
        rating_score = int(request.form['rating'])
        comment = request.form['comment']

        accepter = User.query.get_or_404(task.accepter_id)

        new_rating = Rating(
            task_id=task.task_id,
            poster_id=poster.id,
            accepter_id=accepter.id,
            score=rating_score,
            comment=comment
        )
        db.session.add(new_rating)

        all_ratings = Rating.query.filter_by(accepter_id=accepter.id).all()
        total_score = sum(r.score for r in all_ratings)
        accepter.rating = total_score / len(all_ratings)

        task.task_status = 'completed'
        db.session.commit()
        
        flash('Rating submitted successfully! Task is now complete.')
        return redirect(url_for('dashboard', username=username))
    
    return render_template('rate_task.html', username=username, task=task)

@Campity.route('/logout')
def logout():
    return redirect(url_for('login'))

if __name__ == '__main__':
    Campity.run(debug=True, host='0.0.0.0', port=5000)
