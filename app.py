from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from datetime import datetime
import hashlib
import os
import base64
from werkzeug.utils import secure_filename
from flask import send_from_directory
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
CORS(app)

# Database configuration 
DB_CONFIG = {
    'dbname': 'campus_events_db',
    'user': 'postgres',
    'password': 'arsalan1357',  
    'host': 'localhost',
    'port': '5432'
}

def get_db_connection():
    """Create and return a database connection"""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    return conn

# File upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==================== API ROUTES ====================

@app.route('/')
def home():
    return "Backend is running! 🚀 Connected to PostgreSQL"

@app.route('/api/events', methods=['GET'])
def get_events():
    """Get all events from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT * FROM events ORDER BY date
        """)
        events = cursor.fetchall()
        
        # Convert to list of dictionaries
        events_list = []
        for event in events:
            event_dict = dict(event)
            events_list.append(event_dict)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'events': events_list,
            'total': len(events_list)
        })
        
    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Failed to fetch events'}), 500

@app.route('/api/events/search', methods=['GET'])
def search_events():
    """Search events by name or date"""
    query = request.args.get('q', '').lower().strip()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if not query:
            cursor.execute("SELECT * FROM events ORDER BY date")
        else:
            cursor.execute("""
                SELECT * FROM events 
                WHERE LOWER(title) LIKE %s OR LOWER(category) LIKE %s
                ORDER BY date
            """, (f'%{query}%', f'%{query}%'))
        
        events = cursor.fetchall()
        events_list = [dict(event) for event in events]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'events': events_list,
            'total': len(events_list),
            'query': query
        })
        
    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Search failed'}), 500

@app.route('/api/signup', methods=['POST'])
def signup():
    """User registration"""
    data = request.get_json()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user already exists
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (data['email'],))
        if cursor.fetchone():
            return jsonify({'error': 'User already exists'}), 400
        

        # Check if student ID already exists (for students only)
        if data['role'] in ['pillai_student', 'other_student']:
            cursor.execute("SELECT user_id FROM users WHERE student_id = %s", (data['studentId'],))
            if cursor.fetchone():
                return jsonify({'error': 'Student ID already registered'}), 400
        
        # Validate required fields based on role
        if data['role'] == 'pillai_student':
            if not data.get('studentId') or data['studentId'].strip() == '':
                return jsonify({'error': 'Student ID is required for Pillai students'}), 400
        
        if data['role'] == 'other_student':
            if not data.get('collegeName') or data['collegeName'].strip() == '':
                return jsonify({'error': 'College name is required for other college students'}), 400
            if not data.get('studentId') or data['studentId'].strip() == '':
                return jsonify({'error': 'Student ID is required for other college students'}), 400
        
        # Insert new user
        cursor.execute("""
            INSERT INTO users (name, email, password, role, college_name, student_id, department)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING user_id
        """, (
            data['name'],
            data['email'],
            hashlib.md5(data['password'].encode()).hexdigest(),
            data['role'],
            data.get('collegeName', ''),
            data.get('studentId', ''),
            data.get('department', '')
        ))
        
        user_id = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'User created successfully!', 'user_id': user_id})
        
    except Exception as e:
        print(f"Signup error: {e}")
        return jsonify({'error': 'Failed to create user'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """User login"""
    data = request.get_json()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT user_id, name, email, role, college_name, student_id, department 
            FROM users 
            WHERE email = %s AND password = %s
        """, (data['email'], hashlib.md5(data['password'].encode()).hexdigest()))
        
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            return jsonify({
                'message': 'Login successful!',
                'user': dict(user)
            })
        
        return jsonify({'error': 'Invalid credentials'}), 401
        
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/events/create', methods=['POST'])
def create_event():
    """Create new event"""
    data = request.get_json()
    print("📝 Received event data:", data)  # Debug log
    
    try:
        # Validate required fields
        required_fields = ['title', 'description', 'date', 'location', 'capacity', 'category', 'audience', 'organizer_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate capacity
        if data['capacity'] > 5000:
            return jsonify({'error': 'Event capacity cannot exceed 5000'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert new event
        cursor.execute("""
            INSERT INTO events (title, description, date, end_time, registration_deadline, 
                              location, capacity, registered, category, audience, organizer_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING event_id
        """, (
            data['title'],
            data['description'],
            data['date'],
            data.get('end_time', data['date']),  # Use date as fallback for end_time
            data.get('registration_deadline', data['date']),  # Use date as fallback
            data['location'],
            data['capacity'],
            0,  # Start with 0 registered
            data['category'],
            data['audience'],
            data['organizer_id']
        ))
        
        event_id = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        return jsonify({
            'message': 'Event created successfully!', 
            'event_id': event_id
        })
        
    except Exception as e:
        print(f"❌ Create event error: {e}")
        return jsonify({'error': f'Failed to create event: {str(e)}'}), 500

@app.route('/api/register', methods=['POST'])
def register_event():
    """Register for event"""
    data = request.get_json()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get event details
        cursor.execute("SELECT * FROM events WHERE event_id = %s", (data['eventId'],))
        event = cursor.fetchone()
        if not event:
            return jsonify({'error': 'Event not found'}), 404
        
        event = dict(event)
        
        # Check registration deadline
        registration_deadline = event['registration_deadline']
        if datetime.now() > registration_deadline:
            return jsonify({'error': 'Registration for this event has closed'}), 400
        
        # Check if user is already registered
        cursor.execute("""
            SELECT registration_id FROM registrations 
            WHERE event_id = %s AND user_id = %s
        """, (data['eventId'], data['userId']))
        if cursor.fetchone():
            return jsonify({'error': 'You are already registered for this event'}), 400
        
        # Check if user is on waitlist
        cursor.execute("""
            SELECT waitlist_id FROM waitlists 
            WHERE event_id = %s AND user_id = %s
        """, (data['eventId'], data['userId']))
        if cursor.fetchone():
            return jsonify({'error': 'You are already on the waitlist for this event'}), 400
        
        # Get user details
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (data['userId'],))
        user = cursor.fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user = dict(user)
        
        # Check if user is organizer
        if user['role'] == 'organizer':
            return jsonify({'error': 'Organizers cannot register for events'}), 403
        
        # Check audience restrictions
        user_role = user['role']
        event_audience = event['audience']
        
        can_register = False
        if event_audience == 'all':
            can_register = user_role != 'organizer'
        elif event_audience == 'pillai_students':
            can_register = user_role == 'pillai_student'
        elif event_audience == 'college_students':
            can_register = user_role == 'pillai_student' or user_role == 'other_student'
        elif event_audience == 'non_students':
            can_register = user_role == 'non_student'
        
        if not can_register:
            return jsonify({'error': 'You are not eligible to register for this event'}), 403
        
        # Check capacity
        if event['registered'] < event['capacity']:
            # Register user
            cursor.execute("""
                INSERT INTO registrations (event_id, user_id, name, email, college_name, student_id, department)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                data['eventId'],
                data['userId'],
                data['name'],
                data['email'],
                data.get('collegeName', ''),
                data.get('studentId', ''),
                data.get('department', '')
            ))
            
            # Update registered count
            cursor.execute("""
                UPDATE events SET registered = registered + 1 WHERE event_id = %s
            """, (data['eventId'],))
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'message': f"Successfully registered for {event['title']}!",
                'status': 'confirmed'
            })
        else:
            # Add to waitlist
            cursor.execute("""
                SELECT COUNT(*) as count FROM waitlists WHERE event_id = %s
            """, (data['eventId'],))
            position = cursor.fetchone()['count'] + 1
            
            cursor.execute("""
                INSERT INTO waitlists (event_id, user_id, name, email, college_name, student_id, department, position)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data['eventId'],
                data['userId'],
                data['name'],
                data['email'],
                data.get('collegeName', ''),
                data.get('studentId', ''),
                data.get('department', ''),
                position
            ))
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'message': 'Event is full! Added to waitlist.',
                'status': 'waitlisted',
                'position': position
            })
            
    except Exception as e:
        print(f"Registration error: {e}")
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/unregister', methods=['POST'])
def unregister_event():
    """Unregister from event"""
    data = request.get_json()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Remove registration
        cursor.execute("""
            DELETE FROM registrations 
            WHERE event_id = %s AND user_id = %s
            RETURNING registration_id
        """, (data['eventId'], data['userId']))
        
        if not cursor.fetchone():
            return jsonify({'error': 'Registration not found'}), 404
        
        # Update event count
        cursor.execute("""
            UPDATE events SET registered = registered - 1 WHERE event_id = %s
        """, (data['eventId'],))
        
        # Check waitlist
        cursor.execute("""
            SELECT * FROM waitlists 
            WHERE event_id = %s 
            ORDER BY position 
            LIMIT 1
        """, (data['eventId'],))
        next_waitlist = cursor.fetchone()
        
        if next_waitlist:
            # Register first waitlisted person
            cursor.execute("""
                INSERT INTO registrations (event_id, user_id, name, email, college_name, student_id, department)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                data['eventId'],
                next_waitlist['user_id'],
                next_waitlist['name'],
                next_waitlist['email'],
                next_waitlist['college_name'],
                next_waitlist['student_id'],
                next_waitlist['department']
            ))
            
            # Remove from waitlist
            cursor.execute("""
                DELETE FROM waitlists WHERE waitlist_id = %s
            """, (next_waitlist['waitlist_id'],))
            
            # Update event count again
            cursor.execute("""
                UPDATE events SET registered = registered + 1 WHERE event_id = %s
            """, (data['eventId'],))
            
            # Update remaining waitlist positions
            cursor.execute("""
                UPDATE waitlists SET position = position - 1 
                WHERE event_id = %s AND position > %s
            """, (data['eventId'], next_waitlist['position']))
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'message': 'Successfully unregistered.',
                'waitlist_promoted': True
            })
        
        cursor.close()
        conn.close()
        return jsonify({'message': 'Successfully unregistered from event'})
        
    except Exception as e:
        print(f"Unregister error: {e}")
        return jsonify({'error': 'Unregistration failed'}), 500

@app.route('/api/user/registrations/<int:user_id>', methods=['GET'])
def get_user_registrations(user_id):
    """Get events registered by a specific user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT * FROM registrations WHERE user_id = %s
        """, (user_id,))
        registrations = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'registrations': [dict(reg) for reg in registrations]})
        
    except Exception as e:
        print(f"Get registrations error: {e}")
        return jsonify({'error': 'Failed to get registrations'}), 500

@app.route('/api/user/waitlists/<int:user_id>', methods=['GET'])
def get_user_waitlists(user_id):
    """Get events waitlisted by a specific user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT * FROM waitlists WHERE user_id = %s
        """, (user_id,))
        waitlists = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'waitlists': [dict(wait) for wait in waitlists]})
        
    except Exception as e:
        print(f"Get waitlists error: {e}")
        return jsonify({'error': 'Failed to get waitlists'}), 500

@app.route('/api/user/events/<int:user_id>', methods=['GET'])
def get_user_events(user_id):
    """Get events created by a specific organizer"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT * FROM events WHERE organizer_id = %s ORDER BY date
        """, (user_id,))
        events = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'events': [dict(event) for event in events]})
        
    except Exception as e:
        print(f"Get user events error: {e}")
        return jsonify({'error': 'Failed to get user events'}), 500

@app.route('/api/events/update/<int:event_id>', methods=['PUT'])
def update_event(event_id):
    """Update event details"""
    data = request.get_json()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if event exists and user is organizer
        cursor.execute("SELECT organizer_id FROM events WHERE event_id = %s", (event_id,))
        event = cursor.fetchone()
        
        if not event:
            return jsonify({'error': 'Event not found'}), 404
        
        if event['organizer_id'] != data.get('userId'):
            return jsonify({'error': 'Unauthorized to edit this event'}), 403
        
        # Update event
        cursor.execute("""
            UPDATE events 
            SET title = %s, description = %s, date = %s, end_time = %s, 
                registration_deadline = %s, location = %s, capacity = %s, audience = %s
            WHERE event_id = %s
        """, (
            data['title'],
            data['description'],
            data['date'],
            data['end_time'],
            data['registration_deadline'],
            data['location'],
            data['capacity'],
            data['audience'],
            event_id
        ))
        
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Event updated successfully!'})
        
    except Exception as e:
        print(f"Update event error: {e}")
        return jsonify({'error': 'Failed to update event'}), 500

@app.route('/api/events/delete/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    """Delete an event"""
    data = request.get_json()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if event exists and user is organizer
        cursor.execute("SELECT organizer_id FROM events WHERE event_id = %s", (event_id,))
        event = cursor.fetchone()
        
        if not event:
            return jsonify({'error': 'Event not found'}), 404
        
        if event['organizer_id'] != data.get('userId'):
            return jsonify({'error': 'Unauthorized to delete this event'}), 403
        
        # Delete registrations and waitlists first
        cursor.execute("DELETE FROM registrations WHERE event_id = %s", (event_id,))
        cursor.execute("DELETE FROM waitlists WHERE event_id = %s", (event_id,))
        
        # Delete event
        cursor.execute("DELETE FROM events WHERE event_id = %s", (event_id,))
        
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Event deleted successfully!'})
        
    except Exception as e:
        print(f"Delete event error: {e}")
        return jsonify({'error': 'Failed to delete event'}), 500

@app.route('/api/waitlist/join', methods=['POST'])
def join_waitlist():
    """Join event waitlist"""
    data = request.get_json()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if already on waitlist
        cursor.execute("""
            SELECT waitlist_id FROM waitlists 
            WHERE event_id = %s AND user_id = %s
        """, (data['eventId'], data['userId']))
        
        if cursor.fetchone():
            return jsonify({'error': 'You are already on the waitlist for this event'}), 400
        
        # Get waitlist position
        cursor.execute("""
            SELECT COUNT(*) as count FROM waitlists WHERE event_id = %s
        """, (data['eventId'],))
        position = cursor.fetchone()['count'] + 1
        
        # Add to waitlist
        cursor.execute("""
            INSERT INTO waitlists (event_id, user_id, name, email, college_name, student_id, department, position)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data['eventId'],
            data['userId'],
            data['name'],
            data['email'],
            data.get('collegeName', ''),
            data.get('studentId', ''),
            data.get('department', ''),
            position
        ))
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'message': f'Added to waitlist at position {position}',
            'position': position
        })
        
    except Exception as e:
        print(f"Join waitlist error: {e}")
        return jsonify({'error': 'Failed to join waitlist'}), 500

@app.route('/api/waitlist/leave', methods=['POST'])
def leave_waitlist():
    """Leave event waitlist"""
    data = request.get_json()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get current position
        cursor.execute("""
            SELECT position FROM waitlists 
            WHERE event_id = %s AND user_id = %s
        """, (data['eventId'], data['userId']))
        
        result = cursor.fetchone()
        if not result:
            return jsonify({'error': 'Not found on waitlist'}), 404
        
        current_position = result['position']
        
        # Remove from waitlist
        cursor.execute("""
            DELETE FROM waitlists 
            WHERE event_id = %s AND user_id = %s
        """, (data['eventId'], data['userId']))
        
        # Update positions for others
        cursor.execute("""
            UPDATE waitlists SET position = position - 1 
            WHERE event_id = %s AND position > %s
        """, (data['eventId'], current_position))
        
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Successfully left the waitlist'})
        
    except Exception as e:
        print(f"Leave waitlist error: {e}")
        return jsonify({'error': 'Failed to leave waitlist'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Backend with PostgreSQL is working!'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)