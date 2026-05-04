import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from models import db, User, Ticket, Message
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey_ticket_system_2026'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

# Decorator for login required
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Decorator for admin required
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---
@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    user = User.query.filter_by(email=email).first()
    
    if user and check_password_hash(user.password, password):
        session['user_id'] = user.id
        session['role'] = user.role
        flash('Logged in successfully.', 'success')
        if user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid email or password.', 'error')
        return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register():
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role', 'user') # Standardly this would be locked down, but allowed for demo

    if User.query.filter_by(email=email).first():
        flash('Email address already exists', 'error')
        return redirect(url_for('index'))

    new_user = User(
        name=name,
        email=email,
        password=generate_password_hash(password, method='pbkdf2:sha256'),
        role=role
    )
    db.session.add(new_user)
    db.session.commit()
    
    flash('Registration successful. Please login.', 'success')
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index'))

# Dashboard Routes
@app.route('/dashboard')
@login_required
def dashboard():
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    tickets = Ticket.query.filter_by(user_id=session['user_id']).order_by(Ticket.created_at.desc()).all()
    stats = {
        'open': Ticket.query.filter_by(user_id=session['user_id'], status='Open').count(),
        'in_progress': Ticket.query.filter_by(user_id=session['user_id'], status='In Progress').count(),
        'resolved': Ticket.query.filter_by(user_id=session['user_id'], status='Resolved').count()
    }
    return render_template('dashboard.html', tickets=tickets, stats=stats)

@app.route('/admin_dashboard')
@login_required
@admin_required
def admin_dashboard():
    search = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    
    query = Ticket.query
    if search:
        query = query.filter(db.or_(Ticket.title.ilike(f'%{search}%'), Ticket.id.like(f'%{search}%')))
    if status_filter:
        query = query.filter_by(status=status_filter)
        
    tickets = query.order_by(Ticket.created_at.desc()).all()
    
    stats = {
        'total': Ticket.query.count(),
        'open': Ticket.query.filter_by(status='Open').count(),
        'in_progress': Ticket.query.filter_by(status='In Progress').count(),
        'resolved': Ticket.query.filter_by(status='Resolved').count()
    }
    return render_template('admin_dashboard.html', tickets=tickets, stats=stats)

# Ticket Routes
@app.route('/ticket/create', methods=['GET', 'POST'])
@login_required
def create_ticket():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        priority = request.form.get('priority')
        
        new_ticket = Ticket(
            title=title,
            description=description,
            category=category,
            priority=priority,
            user_id=session['user_id']
        )
        db.session.add(new_ticket)
        db.session.commit()
        
        flash('Ticket created successfully.', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('create_ticket.html')

@app.route('/ticket/<int:ticket_id>')
@login_required
def ticket_detail(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    # Check access
    if session.get('role') != 'admin' and ticket.user_id != session['user_id']:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
        
    messages = Message.query.filter_by(ticket_id=ticket.id).order_by(Message.timestamp.asc()).all()
    return render_template('ticket_detail.html', ticket=ticket, messages=messages)

@app.route('/ticket/<int:ticket_id>/reply', methods=['POST'])
@login_required
def reply_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    
    if session.get('role') != 'admin' and ticket.user_id != session['user_id']:
        flash('Unauthorized action.', 'error')
        return redirect(url_for('dashboard'))
        
    message_text = request.form.get('message')
    if message_text:
        new_message = Message(
            message=message_text,
            ticket_id=ticket.id,
            sender_id=session['user_id']
        )
        db.session.add(new_message)
        
        # If admin replies and status is Open, automatically set to In Progress
        if session.get('role') == 'admin' and ticket.status == 'Open':
            ticket.status = 'In Progress'
            
        db.session.commit()
    
    return redirect(url_for('ticket_detail', ticket_id=ticket.id))

@app.route('/ticket/<int:ticket_id>/update_status', methods=['POST'])
@login_required
@admin_required
def update_ticket_status(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    new_status = request.form.get('status')
    if new_status in ['Open', 'In Progress', 'Resolved', 'Closed']:
        ticket.status = new_status
        db.session.commit()
        flash('Ticket status updated.', 'success')
        
    return redirect(url_for('ticket_detail', ticket_id=ticket.id))

@app.route('/chatbot', methods=['POST'])
@login_required
def chatbot():
    # Only allow non-admins (customers) to use the bot
    if session.get('role') == 'admin':
        return jsonify({'reply': 'Chatbot is meant for customers.'}), 403
        
    user_msg = request.json.get('message', '').lower()
    
    # Very basic FAQ logic
    if 'password' in user_msg or 'reset' in user_msg:
        reply = "To reset your password, please go to the settings page or click 'Forgot Password' on the login screen."
    elif 'billing' in user_msg or 'refund' in user_msg:
        reply = "For billing inquiries or refunds, please create a ticket under the 'Billing & Subscriptions' category."
    elif 'hello' in user_msg or 'hi' in user_msg:
        reply = "Hello! I'm the ResolveX Bot. How can I help you today? Ask me about billing, passwords, or creating tickets."
    elif 'ticket' in user_msg or 'create' in user_msg or 'new' in user_msg:
        reply = "You can create a new ticket by clicking the 'New Ticket' button in your dashboard navigation."
    elif 'status' in user_msg or 'progress' in user_msg:
        reply = "You can check the status of your existing tickets right on your Customer Dashboard."
    else:
        reply = "I'm a simple bot and I couldn't quite understand that. Please create a Support Ticket so our human agents can assist you."
        
    return jsonify({'reply': reply})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
