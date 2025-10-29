import psycopg2
import hashlib

DB_CONFIG = {
    'dbname': 'campus_events_db',
    'user': 'postgres', 
    'password': 'arsalan1357',
    'host': 'localhost',
    'port': '5432'
}

def setup_complete_database():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:

        
        # Insert users
        print("Inserting users...")
        cursor.execute("""
            INSERT INTO users (name, email, password, role, college_name, student_id, department) 
            VALUES 
            ('Admin User', 'admin@campus.edu', %s, 'organizer', NULL, NULL, NULL),
            ('John Pillai Student', 'student@pillai.edu', %s, 'pillai_student', 'Pillai College', 'PIL2025001', 'Computer Engineering'),
            ('Other College Student', 'student@other.edu', %s, 'other_student', 'Other University', 'OTH2025001', 'Information Technology'),
            ('Non Student Guest', 'guest@gmail.com', %s, 'non_student', NULL, NULL, NULL)
        """, [
            hashlib.md5('password'.encode()).hexdigest(),
            hashlib.md5('password'.encode()).hexdigest(), 
            hashlib.md5('password'.encode()).hexdigest(),
            hashlib.md5('password'.encode()).hexdigest()
        ])
        
        # Insert events
        print("Inserting 10 events...")
        cursor.execute("""
            INSERT INTO events (title, description, date, end_time, registration_deadline, location, capacity, registered, category, audience, organizer_id) 
            VALUES 
            ('Web Development Workshop', 'Learn HTML, CSS, and JavaScript basics.', '2025-10-15 15:00:00', '2025-10-15 17:00:00', '2025-10-14 23:59:59', 'Tech Building, Room 302', 60, 45, 'Workshop', 'all', 1),
            ('AI & Machine Learning Talk', 'Explore the future of artificial intelligence.', '2025-10-18 14:00:00', '2025-10-18 16:00:00', '2025-10-17 23:59:59', 'Science Center, Auditorium', 100, 78, 'Technical', 'pillai_students', 1),
            ('Career Guidance Session', 'Get insights about career opportunities in tech.', '2025-11-01 16:00:00', '2025-11-01 18:00:00', '2025-10-31 23:59:59', 'Career Center, Room 101', 50, 25, 'Talk', 'college_students', 1),
            ('Sports Festival 2025', 'Annual college sports competition.', '2025-11-10 09:00:00', '2025-11-10 17:00:00', '2025-11-08 23:59:59', 'College Ground', 200, 150, 'Sports', 'all', 1),
            ('Cultural Night', 'An evening of music, dance, and cultural performances.', '2025-11-14 18:00:00', '2025-11-14 22:00:00', '2025-11-13 23:59:59', 'Main Auditorium', 300, 275, 'Social', 'all', 1),
            ('Python Programming Bootcamp', 'Intensive Python programming workshop.', '2025-11-20 10:00:00', '2025-11-20 16:00:00', '2025-11-18 23:59:59', 'Computer Lab 3', 40, 32, 'Technical', 'college_students', 1),
            ('Entrepreneurship Summit', 'Learn from successful entrepreneurs.', '2025-11-25 14:00:00', '2025-11-25 18:00:00', '2025-11-23 23:59:59', 'Business School Auditorium', 120, 85, 'Talk', 'all', 1),
            ('Robotics Workshop', 'Hands-on workshop on building robots.', '2025-12-05 13:00:00', '2025-12-05 17:00:00', '2025-12-03 23:59:59', 'Engineering Block, Room 205', 30, 28, 'Workshop', 'pillai_students', 1),
            ('Photography Club Meetup', 'Monthly photography club meeting.', '2025-12-08 15:00:00', '2025-12-08 18:00:00', '2025-12-07 23:59:59', 'Art Department', 25, 18, 'Social', 'all', 1),
            ('Data Science Career Talk', 'Career opportunities in data science.', '2025-12-12 16:00:00', '2025-12-12 18:00:00', '2025-12-10 23:59:59', 'Science Block, Room 101', 80, 65, 'Talk', 'college_students', 1)
        """)
        
        conn.commit()
        print("✅ Database setup complete! 4 users + 10 events inserted.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    setup_complete_database()