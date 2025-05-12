import sqlite3
import random
from datetime import datetime, timedelta
import pandas as pd

# Create a connection to the SQLite database
conn = sqlite3.connect('dormitory.db')
cursor = conn.cursor()

# Create tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS rooms (
    room_id INTEGER PRIMARY KEY,
    floor INTEGER NOT NULL,
    room_number TEXT NOT NULL,
    capacity INTEGER DEFAULT 4,
    UNIQUE(floor, room_number)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS students (
    student_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    gender TEXT NOT NULL,
    program TEXT NOT NULL,
    contact_number TEXT,
    emergency_contact TEXT,
    status TEXT NOT NULL
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS occupancy (
    occupancy_id INTEGER PRIMARY KEY,
    student_id TEXT NOT NULL,
    room_id INTEGER NOT NULL,
    check_in_date DATE NOT NULL,
    check_out_date DATE,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (room_id) REFERENCES rooms(room_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS maintenance (
    request_id INTEGER PRIMARY KEY,
    room_id INTEGER NOT NULL,
    issue_description TEXT NOT NULL,
    reported_date DATE NOT NULL,
    status TEXT NOT NULL,
    resolved_date DATE,
    FOREIGN KEY (room_id) REFERENCES rooms(room_id)
)
''')

# Generate room data (3 floors, 5 rooms per floor)
rooms = []
for floor in range(1, 4):
    for room_num in range(1, 6):
        room_number = f"{floor}0{room_num}"
        rooms.append((floor, room_number, 4))

# Insert room data
for floor, room_number, capacity in rooms:
    cursor.execute('''
    INSERT OR IGNORE INTO rooms (floor, room_number, capacity)
    VALUES (?, ?, ?)
    ''', (floor, room_number, capacity))

# Generate student data
programs = ["Computer Science", "Engineering", "Business", "Medicine", "Arts", "Biology", "Physics", "Chemistry", "Mathematics", "Psychology"]
genders = ["Male", "Female"]
statuses = ["Active", "Checked Out"]

# Sample first and last names
first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Quinn", "Jamie", "Avery", "Skyler", 
               "Aiden", "Emma", "Olivia", "Noah", "Liam", "Sophia", "Isabella", "Mia", "Charlotte", "Amelia",
               "Harper", "Evelyn", "Abigail", "Emily", "Michael", "Ethan", "Daniel", "Matthew", "James", "Benjamin",
               "Elijah", "Lucas", "Mason", "Logan", "Alexander", "William", "Jacob", "Samuel", "Henry", "David"]

last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
              "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
              "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
              "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores"]

# Generate 40 students
students = []
for i in range(1, 41):
    student_id = f"STU{2023000 + i}"
    name = f"{random.choice(first_names)} {random.choice(last_names)}"
    gender = random.choice(genders)
    program = random.choice(programs)
    contact_number = f"+1-555-{random.randint(1000, 9999)}"
    emergency_contact = f"+1-555-{random.randint(1000, 9999)}"
    
    # Make 30% of students "Checked Out"
    status = "Checked Out" if i <= 12 else "Active"
    
    students.append((student_id, name, gender, program, contact_number, emergency_contact, status))

# Insert student data
for student in students:
    cursor.execute('''
    INSERT OR IGNORE INTO students (student_id, name, gender, program, contact_number, emergency_contact, status)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', student)

# Generate occupancy data
# Get room IDs
cursor.execute("SELECT room_id FROM rooms")
room_ids = [row[0] for row in cursor.fetchall()]

# Get student IDs
cursor.execute("SELECT student_id, status FROM students")
student_data = cursor.fetchall()

# Current date for reference
current_date = datetime.now()

# Generate occupancy records
occupancy_records = []
room_occupancy = {room_id: 0 for room_id in room_ids}

for student_id, status in student_data:
    # Randomly select a room that's not full
    available_rooms = [room_id for room_id, count in room_occupancy.items() if count < 4]
    if not available_rooms:
        break
    
    room_id = random.choice(available_rooms)
    room_occupancy[room_id] += 1
    
    # Random check-in date (1-6 months ago)
    days_ago = random.randint(30, 180)
    check_in_date = (current_date - timedelta(days=days_ago)).strftime('%Y-%m-%d')
    
    # Check-out date if status is "Checked Out"
    check_out_date = None
    if status == "Checked Out":
        days_after_checkin = random.randint(30, days_ago)
        check_out_date = (current_date - timedelta(days=days_ago-days_after_checkin)).strftime('%Y-%m-%d')
    
    occupancy_records.append((student_id, room_id, check_in_date, check_out_date))

# Insert occupancy data
for student_id, room_id, check_in_date, check_out_date in occupancy_records:
    cursor.execute('''
    INSERT INTO occupancy (student_id, room_id, check_in_date, check_out_date)
    VALUES (?, ?, ?, ?)
    ''', (student_id, room_id, check_in_date, check_out_date))

# Generate maintenance requests
maintenance_issues = [
    "Broken light fixture", "Leaking faucet", "Clogged toilet", "Faulty air conditioner",
    "Damaged furniture", "Pest control needed", "Window won't close", "Door lock issue",
    "Ceiling fan not working", "Electrical outlet not working", "Heating issue", "Water damage"
]

maintenance_statuses = ["Pending", "In Progress", "Resolved"]

maintenance_requests = []
for i in range(15):  # Generate 15 maintenance requests
    room_id = random.choice(room_ids)
    issue = random.choice(maintenance_issues)
    
    # Random reported date (between 1-60 days ago)
    days_ago = random.randint(1, 60)
    reported_date = (current_date - timedelta(days=days_ago)).strftime('%Y-%m-%d')
    
    status = random.choice(maintenance_statuses)
    
    # Resolved date if status is "Resolved"
    resolved_date = None
    if status == "Resolved":
        days_after_report = random.randint(1, min(days_ago, 14))  # Resolved within 14 days
        resolved_date = (current_date - timedelta(days=days_ago-days_after_report)).strftime('%Y-%m-%d')
    
    maintenance_requests.append((room_id, issue, reported_date, status, resolved_date))

# Insert maintenance data
for room_id, issue, reported_date, status, resolved_date in maintenance_requests:
    cursor.execute('''
    INSERT INTO maintenance (room_id, issue_description, reported_date, status, resolved_date)
    VALUES (?, ?, ?, ?, ?)
    ''', (room_id, issue, reported_date, status, resolved_date))

# Commit changes and close connection
conn.commit()
print("Database created successfully with sample data.")

# Now let's display some basic statistics about the database
print("\nDatabase Summary:")

# Count rooms
cursor.execute("SELECT COUNT(*) FROM rooms")
print(f"Total Rooms: {cursor.fetchone()[0]}")

# Count students
cursor.execute("SELECT COUNT(*) FROM students")
print(f"Total Students: {cursor.fetchone()[0]}")

# Count active students
cursor.execute("SELECT COUNT(*) FROM students WHERE status = 'Active'")
print(f"Active Students: {cursor.fetchone()[0]}")

# Count checked out students
cursor.execute("SELECT COUNT(*) FROM students WHERE status = 'Checked Out'")
print(f"Checked Out Students: {cursor.fetchone()[0]}")

# Count maintenance requests
cursor.execute("SELECT COUNT(*) FROM maintenance")
print(f"Maintenance Requests: {cursor.fetchone()[0]}")

# Show sample data from each table
print("\nSample Data:")

print("\nRooms:")
df_rooms = pd.read_sql_query("SELECT * FROM rooms LIMIT 5", conn)
print(df_rooms)

print("\nStudents:")
df_students = pd.read_sql_query("SELECT * FROM students LIMIT 5", conn)
print(df_students)

print("\nOccupancy:")
df_occupancy = pd.read_sql_query("SELECT * FROM occupancy LIMIT 5", conn)
print(df_occupancy)

print("\nMaintenance:")
df_maintenance = pd.read_sql_query("SELECT * FROM maintenance LIMIT 5", conn)
print(df_maintenance)

conn.close()
