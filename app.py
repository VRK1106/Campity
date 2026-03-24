from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_socketio import SocketIO, emit
from datetime import datetime, timedelta
import os
import redis
from werkzeug.utils import secure_filename
import heapq
import json
from dotenv import load_dotenv

load_dotenv()

# --- Configuration & Setup ---
app = Flask(__name__)

# Force cache clearing for dev
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Load config from Environment
# Load config from Environment
database_url = os.environ.get('DATABASE_URL', 'sqlite:///campity.db')
# Fix for local run where 'db' hostname from .env (Docker) is not resolvable
# Only fallback if we have a Docker URL AND we are NOT in a Docker container
in_docker = os.path.exists('/.dockerenv')
if '@db' in database_url and 'sqlite' not in database_url and not in_docker:
    print("Detected Docker URL with 'db' host but running locally (No /.dockerenv). Falling back to SQLite.", flush=True)
    database_url = 'sqlite:///campity.db'

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_key')
app.config['UPLOAD_FOLDER'] = 'uploads'

# Redis Connection
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
redis_client = None
try:
    # Try connecting to Redis (with a short timeout to fail fast if not present)
    redis_client = redis.from_url(redis_url, socket_timeout=1)
    redis_client.ping()
    print(f"Connected to Redis at {redis_url}", flush=True)
except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
    print("Redis not available. Running in local mode (No Redis).", flush=True)
    redis_client = None

# Extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# SocketIO setup
if redis_client:
    socketio = SocketIO(app, message_queue=redis_url)
else:
    # Fallback for local run without Redis
    socketio = SocketIO(app)

# Create upload folder
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    
    # Economy & Gamification
    credits = db.Column(db.Float, default=100.0) # Starting UBI
    xp = db.Column(db.Integer, default=0)
    reputation = db.Column(db.Float, default=5.0) # Start with 5.0 stars
    role = db.Column(db.String(50), default='Guest User') # Guest, Standard, Sudo, Root
    badges = db.Column(db.Text, default='[]') # JSON string of badges

    def get_badges(self):
        return json.loads(self.badges)

    def add_badge(self, badge_name):
        current_badges = self.get_badges()
        if badge_name not in current_badges:
            current_badges.append(badge_name)
            self.badges = json.dumps(current_badges)

class Quest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    
    # Economics
    reward = db.Column(db.Float, nullable=False)
    stake_amount = db.Column(db.Float, default=0.0) # Required stake from Solver
    
    # Status
    status = db.Column(db.String(50), default='OPEN') # OPEN, ACCEPTED, COMPLETED, DISPUTED, EXPIRED
    escrow_status = db.Column(db.String(50), default='HELD') # HELD, RELEASED, REFUNDED
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deadline = db.Column(db.DateTime, nullable=True)
    accepted_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    poster_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    solver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    file_path = db.Column(db.String(300))

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # None = System
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # None = System/Burn
    amount = db.Column(db.Float, nullable=False)
    tx_type = db.Column(db.String(50), nullable=False) # PAYMENT, STAKE, REWARD, PENALTY
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    quest_id = db.Column(db.Integer, db.ForeignKey('quest.id'), nullable=True)

# --- Helper Functions ---

def update_user_rank(user):
    # Update role based on XP
    if user.xp > 1000:
        user.role = 'Root Admin'
    elif user.xp > 500:
        user.role = 'Sudo User'
    elif user.xp > 100:
        user.role = 'Standard User'
    else:
        user.role = 'Guest User'
    db.session.commit()

# --- Routes ---

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('post_quest'))
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('User already exists.', 'danger')
            return redirect(url_for('login'))
            
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # New User Bonus (UBI)
        new_user = User(username=username, password=hashed_password, credits=100.0, xp=0)
        db.session.add(new_user)
        db.session.commit()
        
        # Initial Transaction Log (UBI)
        tx = Transaction(receiver_id=new_user.id, amount=100.0, tx_type='UBI_WELCOME')
        db.session.add(tx)
        db.session.commit()
        
        flash('Welcome to Campity! You received 100 Credits.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            session['username'] = user.username
            session['user_id'] = user.id
            
            # Daily Login Bonus Check (simplified)
            
            
            return redirect(url_for('dashboard'))
        else:
            flash('Login Failed. Check credentials.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    username = user.username
    
    # My Quests (Seeker)
    posted_quests = Quest.query.filter_by(poster_id=user.id).order_by(Quest.created_at.desc()).all()
    
    # My Missions (Solver) - Active
    active_missions = Quest.query.filter_by(solver_id=user.id).filter(Quest.status.in_(['ACCEPTED', 'COMPLETED'])).all()
    
    # Available Quests (Marketplace)
    # Filter: Not my quests, Status is OPEN
    available_quests = Quest.query.filter(Quest.poster_id != user.id, Quest.status == 'OPEN').order_by(Quest.created_at.desc()).all()
    
    return render_template('dashboard.html', 
                           username=username, 
                           user=user, 
                           posted_quests=posted_quests,
                           active_missions=active_missions,
                           available_quests=available_quests)

@app.route('/profile/<username>')
def profile(username):
    if 'username' not in session:
        return redirect(url_for('login'))
        
    user = User.query.filter_by(username=username).first_or_404()
    
    # Posted Quests
    posted_quests = Quest.query.filter_by(poster_id=user.id).order_by(Quest.created_at.desc()).all()
    
    # Accepted/Completed Quests (as Solver)
    tasks_accepted = Quest.query.filter_by(solver_id=user.id).all()
    
    return render_template('profile.html', 
                           user=user, 
                           username=username,
                           tasks_posted=posted_quests, 
                           tasks_accepted=tasks_accepted)

# --- Quest Management Routes ---

# --- Seeding ---
@app.route('/seed_coc')
def seed_coc():
    if Quest.query.count() > 0:
        flash("Village already populated!", "warning")
        return redirect(url_for('dashboard'))

    # Sample "Goblin Maps" (Easy Tasks)
    quests = [
        Quest(title="Payback (Goblin Map)", description="Deliver the package to the Dean's Office. Watch out for traps!", category="Logistics", reward=500, poster_id=1),
        Quest(title="Sherbet Towers", description="Fix the projector in Hall B. It's glitching!", category="Tech Support", reward=800, poster_id=1),
        Quest(title="Maginot Line", description="Help distribute flyers for the Tech Fest.", category="Labor", reward=300, poster_id=1),
        Quest(title="Bottoms Up", description="Urgent! Need lecture notes for Data Structures.", category="Academics", reward=1000, poster_id=1),
    ]

    for q in quests:
        db.session.add(q)
    
    db.session.commit()
    flash("Goblin Maps Discovered! (Sample Data Added)", "success")
    return redirect(url_for('dashboard'))

@app.route('/post_quest', methods=['GET', 'POST'])
def post_quest():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        reward = float(request.form['reward'])
        category = request.form['category']
        deadline_str = request.form['deadline'] # Format: YYYY-MM-DDTHH:MM
        
        # Validation: Check Emeralds
        if user.credits < reward:
            flash('Not enough Emeralds to post this bounty.', 'danger')
            return redirect(url_for('post_quest'))
            
        # Deduct Emeralds (Escrow)
        user.credits -= reward
        
        # Create Quest
        quest = Quest(
            title=title,
            description=description,
            reward=reward,
            category=category,
            poster_id=user.id,
            status='OPEN',
            escrow_status='HELD',
            deadline=datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M') if deadline_str else None
        )
        db.session.add(quest)
        db.session.commit() # Commit to get ID
        
        # Log Transaction
        tx = Transaction(
            sender_id=user.id,
            amount=reward,
            tx_type='ESCROW_DEPOSIT',
            quest_id=quest.id
        )
        db.session.add(tx)
        db.session.commit()
        
        # Real-time Notification for Credits (Self)
        socketio.emit('credits_updated', {'new_amount': user.credits}, room=f"user_{user.id}")
        
        flash('Ad Astra Abyssoque! Commission posted successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('post_quest.html')
    
    db.session.add(new_quest)
    db.session.commit()
    
    # Log Transaction
    tx = Transaction(
        sender_id=user.id,
        amount=reward,
        tx_type='ESCROW_DEPOSIT',
        quest_id=new_quest.id
    )
    db.session.add(tx)
    db.session.commit()
    
    # Real-time Notification
    socketio.emit('credits_updated', {'new_amount': user.credits}, room=f"user_{user.id}")
    
    flash('Ad Astra Abyssoque! Commission posted successfully.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/accept_quest/<int:quest_id>', methods=['POST'])
def accept_quest(quest_id):
    if 'username' not in session:
        return redirect(url_for('login'))
        
    quest = Quest.query.get_or_404(quest_id)
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    if quest.poster_id == user.id:
        flash("You cannot accept your own commission, Traveler!", "danger")
        return redirect(url_for('dashboard'))

    if quest.status != 'OPEN':
        flash('This commission has already been taken!', 'danger')
        return redirect(url_for('dashboard'))

    # Stake Logic (10% of reward)
    stake = max(10, int(quest.reward * 0.1))
    
    if user.credits < stake:
        flash(f'Insufficient Mora! You need {stake} Mora to accept this commission.', 'danger')
        return redirect(url_for('dashboard'))

    # Deduct Stake
    user.credits -= stake
    quest.status = 'ACCEPTED'
    quest.solver_id = user.id
    quest.stake_amount = stake
    
    db.session.commit()
    
    # Log Stake
    tx = Transaction(
        sender_id=user.id,
        amount=stake,
        tx_type='STAKE_LOCK',
        quest_id=quest.id
    )
    db.session.add(tx)
    db.session.commit()
    
    # Real-time Notify
    socketio.emit('quest_accepted', {'solver': user.username, 'quest_id': quest_id}, to=f"user_{quest.poster_id}")
    flash(f'Commission Accepted! {stake} Mora staked.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/complete_quest/<int:quest_id>', methods=['POST'])
def complete_quest(quest_id):
    if 'username' not in session:
        return redirect(url_for('login'))
        
    quest = Quest.query.get_or_404(quest_id)
    
    if quest.solver_id != session['user_id']:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('dashboard'))

    quest.status = 'COMPLETED'
    db.session.commit()
    
    socketio.emit('quest_completed', {'quest_id': quest_id}, to=f"user_{quest.poster_id}")
    flash('Commission Complete! Waiting for Guild Verification.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/verify_quest/<int:quest_id>', methods=['POST'])
def verify_quest(quest_id):
    if 'username' not in session:
        return redirect(url_for('login'))
        
    quest = Quest.query.get_or_404(quest_id)
    
    if quest.poster_id != session['user_id']:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('dashboard'))

    if quest.status != 'COMPLETED':
        flash('Commission is not ready for verification.', 'danger')
        return redirect(url_for('dashboard'))

    solver = User.query.get(quest.solver_id)
    
    # Payout: Reward + Returned Stake
    payout = quest.reward + quest.stake_amount
    solver.credits += payout
    
    # Add Clean XP (Adventure Rank)
    solver.xp += 50 
    solver.reputation += 1
    
    quest.status = 'VERIFIED'
    
    db.session.commit()
    
    # Real-time update for solver
    socketio.emit('credit_update', {'new_total': solver.credits}, to=f"user_{solver.id}")
    
    flash(f'Commission Verified! {payout} Mora transferred to {solver.username}.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/leaderboard')
def leaderboard():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    user = User.query.filter_by(username=session['username']).first()
    # Top 10 by XP
    top_users = User.query.order_by(User.xp.desc()).limit(10).all()
    return render_template('leaderboard.html', user=user, top_users=top_users)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Use debug=True for local dev to see errors
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
