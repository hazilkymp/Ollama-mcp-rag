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
programs = ["Computer Science", "Engineering", "Business", "Medicine", "Arts",
            "Biology", "Physics", "Chemistry", "Mathematics", "Psychology"]
genders = ["Male", "Female"]
statuses = ["Active", "Checked Out"]

first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Quinn",
               "Jamie", "Avery", "Skyler", "Aiden", "Emma", "Olivia", "Noah",
               "Liam", "Sophia", "Isabella", "Mia", "Charlotte", "Amelia",
               "Harper", "Evelyn", "Abigail", "Emily", "Michael", "Ethan",
               "Daniel", "Matthew", "James", "Benjamin", "Elijah", "Lucas",
               "Mason", "Logan", "Alexander", "William", "Jacob", "Samuel",
               "Henry", "David"]
last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
              "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez",
              "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor",
              "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
              "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis",
              "Robinson", "Walker", "Young", "Allen", "King", "Wright",
              "Scott", "Torres", "Nguyen", "Hill", "Flores"]

students = []
for i in range(1, 41):
    student_id = f"STU{2023000 + i}"
    name = f"{random.choice(first_names)} {random.choice(last_names)}"
    gender = random.choice(genders)
    program = random.choice(programs)
    contact_number = f"+1-555-{random.randint(1000, 9999)}"
    emergency_contact = f"+1-555-{random.randint(1000, 9999)}"
    status = "Checked Out" if i <= 12 else "Active"
    students.append((student_id, name, gender, program,
                     contact_number, emergency_contact, status))

for student in students:
    cursor.execute('''
    INSERT OR IGNORE INTO students
      (student_id, name, gender, program, contact_number,
       emergency_contact, status)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', student)

# Generate occupancy data
cursor.execute("SELECT room_id FROM rooms")
room_ids = [row[0] for row in cursor.fetchall()]

cursor.execute("SELECT student_id, status FROM students")
student_data = cursor.fetchall()

current_date = datetime.now()
occupancy_records = []
room_occupancy = {rid: 0 for rid in room_ids}

for student_id, status in student_data:
    available = [rid for rid, cnt in room_occupancy.items() if cnt < 4]
    if not available:
        break
    rid = random.choice(available)
    room_occupancy[rid] += 1
    days_ago = random.randint(30, 180)
    check_in = (current_date - timedelta(days=days_ago)).strftime('%Y-%m-%d')
    check_out = None
    if status == "Checked Out":
        after = random.randint(30, days_ago)
        check_out = (current_date - timedelta(days=days_ago - after)).strftime('%Y-%m-%d')
    occupancy_records.append((student_id, rid, check_in, check_out))

for rec in occupancy_records:
    cursor.execute('''
    INSERT INTO occupancy
      (student_id, room_id, check_in_date, check_out_date)
    VALUES (?, ?, ?, ?)
    ''', rec)

# Generate maintenance requests
issues = ["Broken light fixture", "Leaking faucet", "Clogged toilet",
          "Faulty air conditioner", "Damaged furniture", "Pest control needed",
          "Window won't close", "Door lock issue", "Ceiling fan not working",
          "Electrical outlet not working", "Heating issue", "Water damage"]
statuses = ["Pending", "In Progress", "Resolved"]
maintenance_requests = []

for i in range(15):
    rid = random.choice(room_ids)
    issue = random.choice(issues)
    days_ago = random.randint(1, 60)
    reported = (current_date - timedelta(days=days_ago)).strftime('%Y-%m-%d')
    stat = random.choice(statuses)
    resolved = None
    if stat == "Resolved":
        after = random.randint(1, min(days_ago, 14))
        resolved = (current_date - timedelta(days=days_ago - after)).strftime('%Y-%m-%d')
    maintenance_requests.append((rid, issue, reported, stat, resolved))

for req in maintenance_requests:
    cursor.execute('''
    INSERT INTO maintenance
      (room_id, issue_description, reported_date, status, resolved_date)
    VALUES (?, ?, ?, ?, ?)
    ''', req)

conn.commit()
print("Database created successfully with sample data.")
conn.close()
