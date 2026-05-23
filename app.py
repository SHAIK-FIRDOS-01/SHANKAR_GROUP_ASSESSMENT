from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from models import db, User, Task
from config import Config
from analytics import calculate_task_analytics
from flask_socketio import SocketIO, emit, join_room
from functools import wraps
import os

app = Flask(__name__)
app.config.from_object(Config)

# Initialize SQLAlchemy
db.init_app(app)

# Initialize WebSockets (Flask-SocketIO)
# Set cors_allowed_origins="*" for development
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Dynamic Database Configuration Logic ---
db_connected = False

def verify_db_connection():
    global db_connected
    if db_connected:
        return True
    try:
        uri = app.config.get('SQLALCHEMY_DATABASE_URI')
        if not uri or uri.startswith('sqlite:'):
            return False
        with app.app_context():
            db.session.execute(db.text('SELECT 1'))
        db_connected = True
        return True
    except Exception:
        db_connected = False
        return False

def write_to_env(db_url):
    env_path = os.path.join(app.root_path, '.env')
    lines = []
    updated = False
    
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('DATABASE_URL='):
                    lines.append(f"DATABASE_URL={db_url}\n")
                    updated = True
                else:
                    lines.append(line)
                    
    if not updated:
        lines.append(f"DATABASE_URL={db_url}\n")
        
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

# Decorator to secure routes
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required. Please log in.'}), 401
            return redirect(url_for('login_page'))
        
        # Verify user still exists in database (e.g. after a DB reset)
        user = User.query.get(session['user_id'])
        if not user:
            session.clear()
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'User not found. Please log in again.'}), 401
            return redirect(url_for('login_page'))
            
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def check_database_configuration():
    # Allow static resources, setup endpoint, and favicon to bypass checks
    if (request.endpoint in ['static', 'setup_db'] or 
        request.path.startswith('/static/') or 
        request.path == '/favicon.ico'):
        return
        
    if not verify_db_connection():
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'error': 'Database not configured. Please configure PostgreSQL at /setup-db.'}), 503
        return redirect(url_for('setup_db'))

@app.route('/setup-db', methods=['GET', 'POST'])
def setup_db():
    global db_connected
    if verify_db_connection():
        return redirect(url_for('index'))
        
    error = None
    host = 'localhost'
    port = '5432'
    dbname = 'task_db'
    user = 'postgres'
    password = ''
    
    if request.method == 'POST':
        host = request.form.get('host', 'localhost').strip()
        port = request.form.get('port', '5432').strip()
        dbname = request.form.get('dbname', 'task_db').strip()
        user = request.form.get('user', 'postgres').strip()
        password = request.form.get('password', '')
        
        # Reconstruct Database URL
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        
        try:
            db.session.remove()
            old_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
            
            # Attempt to automatically create target database if it doesn't exist
            import psycopg2
            from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
            from psycopg2 import sql
            try:
                conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
                conn.close()
            except psycopg2.OperationalError as oe:
                if "does not exist" in str(oe) or "3D000" in str(oe):
                    # Connect to default database 'postgres' to run CREATE DATABASE
                    conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname='postgres')
                    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                    cur = conn.cursor()
                    cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
                    cur.close()
                    conn.close()
                else:
                    raise oe
            
            app.config['SQLALCHEMY_DATABASE_URI'] = db_url
            
            # Dispose of the old default engine
            engines = db._app_engines[app]
            if None in engines:
                engines[None].dispose()
                
            # Manually recreate default engine
            options = {'url': db_url, 'echo': False, 'echo_pool': False}
            db._apply_driver_defaults(options, app)
            engines[None] = db._make_engine(None, options, app)
            
            with app.app_context():
                db.session.execute(db.text('SELECT 1'))
                db.create_all()
                
            db_connected = True
            write_to_env(db_url)
            return redirect(url_for('index'))
        except Exception as e:
            db_connected = False
            # Restore previous SQLite engine on connection failure
            app.config['SQLALCHEMY_DATABASE_URI'] = old_uri
            engines = db._app_engines[app]
            if None in engines:
                engines[None].dispose()
            options = {'url': old_uri, 'echo': False, 'echo_pool': False}
            db._apply_driver_defaults(options, app)
            engines[None] = db._make_engine(None, options, app)
            error = f"Database connection failed: {str(e)}"
            
    return render_template('setup_db.html', error=error, host=host, port=port, dbname=dbname, user=user, password=password)

# --- Page Routes ---

@app.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if not user:
            session.clear()
        else:
            return redirect(url_for('dashboard_page'))
    return redirect(url_for('login_page'))

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if not user:
            session.clear()
        else:
            return redirect(url_for('dashboard_page'))
    
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            error = 'Username and password are required'
        else:
            try:
                user = User.query.filter_by(username=username).first()
                if not user or not user.check_password(password):
                    error = 'Invalid username or password'
                else:
                    session['user_id'] = user.id
                    session['username'] = user.username
                    return redirect(url_for('dashboard_page'))
            except Exception as e:
                error = f'Database error: {str(e)}'
                
    return render_template('auth.html', error=error, active_tab='login')

@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if not user:
            session.clear()
        else:
            return redirect(url_for('dashboard_page'))
        
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            error = 'Username and password are required'
        elif len(username) < 3:
            error = 'Username must be at least 3 characters long'
        elif len(password) < 6:
            error = 'Password must be at least 6 characters long'
        else:
            try:
                existing_user = User.query.filter_by(username=username).first()
                if existing_user:
                    error = 'Username is already taken'
                else:
                    new_user = User(username=username)
                    new_user.set_password(password)
                    db.session.add(new_user)
                    db.session.commit()
                    
                    session['user_id'] = new_user.id
                    session['username'] = new_user.username
                    return redirect(url_for('dashboard_page'))
            except Exception as e:
                db.session.rollback()
                error = f'Database error: {str(e)}'
                
    return render_template('auth.html', error=error, active_tab='register')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/dashboard')
@login_required
def dashboard_page():
    user_id = session['user_id']
    try:
        tasks = Task.query.filter_by(user_id=user_id).order_by(Task.created_date.desc()).all()
        stats = calculate_task_analytics(tasks)
        return render_template('dashboard.html', username=session.get('username'), tasks=tasks, stats=stats)
    except Exception as e:
        print(f"Error loading dashboard: {e}")
        return render_template('dashboard.html', username=session.get('username'), tasks=[], stats={
            'total_tasks': 0,
            'completed_tasks': 0,
            'pending_tasks': 0,
            'completion_percentage': 0.0
        }, error=str(e))

# --- Server-Side Task Actions (Jinja2 Support) ---

@app.route('/tasks/add', methods=['POST'])
@login_required
def page_add_task():
    user_id = session['user_id']
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    priority = request.form.get('priority', 'Medium').capitalize()
    
    if not title:
        return redirect(url_for('dashboard_page'))
        
    if priority not in ['Low', 'Medium', 'High']:
        priority = 'Medium'
        
    try:
        new_task = Task(
            user_id=user_id,
            title=title,
            description=description,
            priority=priority,
            status='Pending'
        )
        db.session.add(new_task)
        db.session.commit()
        
        # Broadcast real-time WebSocket notification to task owner's room
        socketio.emit('task_update', {
            'action': 'created',
            'username': session['username'],
            'task': new_task.to_dict()
        }, to=f"user_{user_id}")
    except Exception as e:
        db.session.rollback()
        print(f"Error adding task: {e}")
        
    return redirect(url_for('dashboard_page'))

@app.route('/tasks/toggle/<int:task_id>', methods=['POST', 'GET'])
@login_required
def page_toggle_task(task_id):
    user_id = session['user_id']
    try:
        task = Task.query.filter_by(id=task_id, user_id=user_id).first()
        if task:
            task.status = 'Pending' if task.status == 'Completed' else 'Completed'
            db.session.commit()
            
            socketio.emit('task_update', {
                'action': 'updated',
                'username': session['username'],
                'task': task.to_dict()
            }, to=f"user_{user_id}")
    except Exception as e:
        db.session.rollback()
        print(f"Error toggling task: {e}")
        
    return redirect(url_for('dashboard_page'))

@app.route('/tasks/delete/<int:task_id>', methods=['POST', 'GET'])
@login_required
def page_delete_task(task_id):
    user_id = session['user_id']
    try:
        task = Task.query.filter_by(id=task_id, user_id=user_id).first()
        if task:
            task_data = task.to_dict()
            db.session.delete(task)
            db.session.commit()
            
            socketio.emit('task_update', {
                'action': 'deleted',
                'username': session['username'],
                'task': task_data
            }, to=f"user_{user_id}")
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting task: {e}")
        
    return redirect(url_for('dashboard_page'))

@app.route('/tasks/edit/<int:task_id>', methods=['POST'])
@login_required
def page_edit_task(task_id):
    user_id = session['user_id']
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    priority = request.form.get('priority', 'Medium').capitalize()
    status = request.form.get('status', 'Pending').capitalize()
    
    if not title:
        return redirect(url_for('dashboard_page'))
        
    try:
        task = Task.query.filter_by(id=task_id, user_id=user_id).first()
        if task:
            task.title = title
            task.description = description
            if priority in ['Low', 'Medium', 'High']:
                task.priority = priority
            if status in ['Pending', 'Completed']:
                task.status = status
            db.session.commit()
            
            socketio.emit('task_update', {
                'action': 'updated',
                'username': session['username'],
                'task': task.to_dict()
            }, to=f"user_{user_id}")
    except Exception as e:
        db.session.rollback()
        print(f"Error editing task: {e}")
        
    return redirect(url_for('dashboard_page'))

# --- Authentication APIs ---

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.get_json() or request.form
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
        
    if len(username) < 3:
        return jsonify({'error': 'Username must be at least 3 characters long'}), 400
        
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters long'}), 400
        
    try:
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return jsonify({'error': 'Username is already taken'}), 409
            
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        session['user_id'] = new_user.id
        session['username'] = new_user.username
        
        return jsonify({'message': 'Registration and login successful'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json() or request.form
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
        
    try:
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid username or password'}), 401
            
        session['user_id'] = user.id
        session['username'] = user.username
        
        return jsonify({'message': 'Login successful'}), 200
    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route('/api/auth/logout', methods=['POST', 'GET'])
def api_logout():
    session.clear()
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'message': 'Logged out successfully'}), 200
    return redirect(url_for('login_page'))

# --- Tasks REST API ---

@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks():
    user_id = session['user_id']
    try:
        tasks = Task.query.filter_by(user_id=user_id).order_by(Task.created_date.desc()).all()
        return jsonify([t.to_dict() for t in tasks]), 200
    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route('/api/tasks', methods=['POST'])
@login_required
def add_task():
    user_id = session['user_id']
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No input data provided'}), 400
        
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    priority = data.get('priority', 'Medium').capitalize()
    status = data.get('status', 'Pending').capitalize()
    
    if not title:
        return jsonify({'error': 'Task title is required'}), 400
        
    if priority not in ['Low', 'Medium', 'High']:
        priority = 'Medium'
        
    if status not in ['Pending', 'Completed']:
        status = 'Pending'
        
    try:
        new_task = Task(
            user_id=user_id,
            title=title,
            description=description,
            priority=priority,
            status=status
        )
        db.session.add(new_task)
        db.session.commit()
        
        task_data = new_task.to_dict()
        
        # Broadcast real-time WebSocket notification to task owner's room only
        socketio.emit('task_update', {
            'action': 'created',
            'username': session['username'],
            'task': task_data
        }, to=f"user_{user_id}")
        
        return jsonify(task_data), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    user_id = session['user_id']
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No input data provided'}), 400
        
    try:
        task = Task.query.filter_by(id=task_id, user_id=user_id).first()
        if not task:
            return jsonify({'error': 'Task not found'}), 404
            
        if 'title' in data:
            title = data['title'].strip()
            if not title:
                return jsonify({'error': 'Title cannot be empty'}), 400
            task.title = title
            
        if 'description' in data:
            task.description = data['description'].strip()
            
        if 'priority' in data:
            priority = data['priority'].capitalize()
            if priority in ['Low', 'Medium', 'High']:
                task.priority = priority
                
        if 'status' in data:
            status = data['status'].capitalize()
            if status in ['Pending', 'Completed']:
                task.status = status
                
        db.session.commit()
        task_data = task.to_dict()
        
        # Broadcast WebSocket notification to task owner's room only
        socketio.emit('task_update', {
            'action': 'updated',
            'username': session['username'],
            'task': task_data
        }, to=f"user_{user_id}")
        
        return jsonify(task_data), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    user_id = session['user_id']
    try:
        task = Task.query.filter_by(id=task_id, user_id=user_id).first()
        if not task:
            return jsonify({'error': 'Task not found'}), 404
            
        task_data = task.to_dict()
        db.session.delete(task)
        db.session.commit()
        
        # Broadcast WebSocket notification to task owner's room only
        socketio.emit('task_update', {
            'action': 'deleted',
            'username': session['username'],
            'task': task_data
        }, to=f"user_{user_id}")
        
        return jsonify({'message': 'Task deleted successfully', 'id': task_id}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

# --- Analytics API ---

@app.route('/api/analytics', methods=['GET'])
@login_required
def get_analytics():
    user_id = session['user_id']
    try:
        tasks = Task.query.filter_by(user_id=user_id).all()
        stats = calculate_task_analytics(tasks)
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': f'Database calculation error: {str(e)}'}), 500

# --- WebSocket Event Handlers ---

@socketio.on('connect')
def handle_connect():
    print(f"WebSocket client connected: {request.sid}")
    if 'user_id' in session:
        room = f"user_{session['user_id']}"
        join_room(room)
        print(f"Socket {request.sid} joined room {room}")
    emit('conn_ack', {'message': 'Connected to live tasks pipeline.'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f"WebSocket client disconnected: {request.sid}")

# --- DB Schema Setup & App Launch ---

# Automatically create tables if the database is accessible
with app.app_context():
    try:
        # Check if database is configured before trying to build all tables
        if app.config.get('SQLALCHEMY_DATABASE_URI') and not app.config.get('SQLALCHEMY_DATABASE_URI').startswith('sqlite:'):
            db.create_all()
            print("PostgreSQL tables verified/created successfully.")
        else:
            print("\n" + "="*80)
            print("DATABASE CONFIGURATION INFO:")
            print("No DATABASE_URL configured in environment or .env file.")
            print("Please visit http://localhost:5000/setup-db in your browser to configure.")
            print("="*80 + "\n")
    except Exception as e:
        print("\n" + "="*80)
        print("DATABASE ACCESS WARNING:")
        print(e)
        print("\nPostgreSQL database check failed.")
        print("Please visit http://localhost:5000/setup-db in your browser to configure your database.")
        print("="*80 + "\n")

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
