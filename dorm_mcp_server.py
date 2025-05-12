import sqlite3
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import List, Dict, Any, AsyncIterator
from mcp.server.fastmcp import FastMCP, Context

# Create a class to represent our database connection
@dataclass
class DatabaseConnection:
    db_path: str = "dormitory.db"
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a SQLite query and return results as a list of dictionaries"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(query)
            results = [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            results = [{"error": str(e)}]
        finally:
            conn.close()
        
        return results

# Set up lifespan context manager
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[DatabaseConnection]:
    """Manage application lifecycle with database connection"""
    print("Starting MCP server for Dormitory Management System...")
    db = DatabaseConnection()
    try:
        yield db
    finally:
        print("Shutting down MCP server...")

# Initialize FastMCP server
mcp = FastMCP("Dormitory Management System", lifespan=app_lifespan)

# Define resources
@mcp.resource("schema://dormitory")
def get_schema(ctx: Context) -> str:
    """Provide the dormitory database schema as a resource"""
    db = ctx.request_context.lifespan_context
    schema = db.execute_query("SELECT sql FROM sqlite_master WHERE type='table'")
    return "\n\n".join(item["sql"] for item in schema if item.get("sql"))

@mcp.resource("data://students")
def get_students(ctx: Context) -> str:
    """List all students in the dormitory system"""
    db = ctx.request_context.lifespan_context
    students = db.execute_query("SELECT * FROM students")
    return "\n".join(f"ID: {s['student_id']}, Name: {s['name']}, Status: {s['status']}" for s in students)

@mcp.resource("data://rooms")
def get_rooms(ctx: Context) -> str:
    """List all rooms in the dormitory"""
    db = ctx.request_context.lifespan_context
    rooms = db.execute_query("SELECT * FROM rooms")
    return "\n".join(f"Room: {r['room_number']} (Floor {r['floor']}), Capacity: {r['capacity']}" for r in rooms)

@mcp.resource("data://occupancy")
def get_occupancy(ctx: Context) -> str:
    """Get current dormitory occupancy information"""
    db = ctx.request_context.lifespan_context
    occupancy = db.execute_query("""
        SELECT r.floor, r.room_number, COUNT(o.student_id) as occupied, r.capacity
        FROM rooms r
        LEFT JOIN occupancy o ON r.room_id = o.room_id AND o.check_out_date IS NULL
        GROUP BY r.room_id
        ORDER BY r.floor, r.room_number
    """)
    return "\n".join(
        f"Room {r['room_number']} (Floor {r['floor']}): {r['occupied']}/{r['capacity']} occupied" 
        for r in occupancy
    )

@mcp.resource("data://maintenance")
def get_maintenance(ctx: Context) -> str:
    """Get maintenance request information"""
    db = ctx.request_context.lifespan_context
    maintenance = db.execute_query("""
        SELECT m.request_id, r.floor, r.room_number, m.issue_description, m.status, m.reported_date
        FROM maintenance m
        JOIN rooms r ON m.room_id = r.room_id
        ORDER BY m.reported_date DESC
    """)
    return "\n".join(
        f"ID: {m['request_id']}, Room: {m['room_number']} (Floor {m['floor']}), " +
        f"Issue: {m['issue_description']}, Status: {m['status']}"
        for m in maintenance
    )

# Define tools for querying the database
@mcp.tool()
def query_database(ctx: Context, sql_query: str) -> str:
    """Execute SQL queries on the dormitory database"""
    # Basic SQL injection prevention
    forbidden_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE"]
    if any(keyword in sql_query.upper() for keyword in forbidden_keywords):
        return f"Error: Query contains forbidden keywords. Only SELECT queries are allowed."
    
    if not sql_query.strip().upper().startswith("SELECT"):
        return f"Error: Only SELECT queries are allowed for security reasons."
    
    db = ctx.request_context.lifespan_context
    try:
        results = db.execute_query(sql_query)
        if not results:
            return "No results found."
        
        # Format results as a readable table
        if "error" in results[0]:
            return f"Error executing query: {results[0]['error']}"
        
        keys = results[0].keys()
        rows = []
        
        # Header
        header = " | ".join(keys)
        separator = "-" * len(header)
        rows.append(header)
        rows.append(separator)
        
        # Data rows
        for row in results:
            rows.append(" | ".join(str(row[key]) for key in keys))
        
        return "\n".join(rows)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def find_student(ctx: Context, search_term: str) -> str:
    """Find a student by name or ID"""
    db = ctx.request_context.lifespan_context
    results = db.execute_query(f"""
        SELECT s.*, r.floor, r.room_number
        FROM students s
        LEFT JOIN occupancy o ON s.student_id = o.student_id AND o.check_out_date IS NULL
        LEFT JOIN rooms r ON o.room_id = r.room_id
        WHERE s.student_id LIKE '%{search_term}%' OR s.name LIKE '%{search_term}%'
    """)
    
    if not results:
        return f"No students found matching '{search_term}'."
    
    formatted_results = []
    for student in results:
        room_info = f"Room {student['room_number']} (Floor {student['floor']})" if student.get('room_number') else "Not assigned"
        formatted_results.append(
            f"ID: {student['student_id']}\n"
            f"Name: {student['name']}\n"
            f"Program: {student['program']}\n"
            f"Status: {student['status']}\n"
            f"Room: {room_info}\n"
        )
    
    return "\n".join(formatted_results)

@mcp.tool()
def room_occupants(ctx: Context, floor: int, room_number: str) -> str:
    """List all current occupants of a specific room"""
    db = ctx.request_context.lifespan_context
    occupants = db.execute_query(f"""
        SELECT s.student_id, s.name, s.program, o.check_in_date
        FROM students s
        JOIN occupancy o ON s.student_id = o.student_id
        JOIN rooms r ON o.room_id = r.room_id
        WHERE r.floor = {floor} AND r.room_number = '{room_number}'
        AND o.check_out_date IS NULL
    """)
    
    if not occupants:
        return f"No current occupants found for Room {room_number} on Floor {floor}."
    
    formatted_occupants = [
        f"Room {room_number} (Floor {floor}) Occupants:",
        "-" * 40
    ]
    
    for occupant in occupants:
        formatted_occupants.append(
            f"ID: {occupant['student_id']}\n"
            f"Name: {occupant['name']}\n"
            f"Program: {occupant['program']}\n"
            f"Check-in Date: {occupant['check_in_date']}\n"
        )
    
    return "\n".join(formatted_occupants)

@mcp.tool()
def check_availability(ctx: Context) -> str:
    """Check room availability in the dormitory"""
    db = ctx.request_context.lifespan_context
    availability = db.execute_query("""
        SELECT r.floor, r.room_number, r.capacity, 
               (SELECT COUNT(*) FROM occupancy o 
                WHERE o.room_id = r.room_id AND o.check_out_date IS NULL) as occupied,
               r.capacity - (SELECT COUNT(*) FROM occupancy o 
                            WHERE o.room_id = r.room_id AND o.check_out_date IS NULL) as available
        FROM rooms r
        ORDER BY r.floor, r.room_number
    """)
    
    formatted_results = ["Room Availability:"]
    
    for floor in range(1, 4):  # 3 floors
        floor_rooms = [r for r in availability if r['floor'] == floor]
        formatted_results.append(f"\nFloor {floor}:")
        formatted_results.append("-" * 40)
        
        for room in floor_rooms:
            status = "FULL" if room['available'] == 0 else f"{room['available']} beds available"
            formatted_results.append(f"Room {room['room_number']}: {room['occupied']}/{room['capacity']} occupied - {status}")
    
    return "\n".join(formatted_results)

# Add a simple prompt to help the LLM understand how to interact with the system
@mcp.prompt()
def help_prompt() -> str:
    return """
    You are a helpful assistant for a dormitory management system. You can:
    
    1. Answer questions about students, rooms, and occupancy
    2. Check room availability
    3. Find information about specific students
    4. View maintenance requests
    
    Use the available tools and resources to provide accurate information.
    """

# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("dorm_mcp_server:mcp", host="0.0.0.0", port=3000)
