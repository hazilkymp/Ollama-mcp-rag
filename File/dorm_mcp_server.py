import sqlite3
from sklearn.linear_model import LinearRegression
import numpy as np
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import List, Dict, Any, AsyncIterator

from mcp.server.fastmcp import FastMCP, Context

# Database connection helper
@dataclass
class DatabaseConnection:
    db_path: str = "dormitory.db"
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        try:
            cur.execute(query)
            rows = [dict(r) for r in cur.fetchall()]
        except sqlite3.Error as e:
            rows = [{"error": str(e)}]
        finally:
            conn.close()
        return rows

# Lifespan for MCP server
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[DatabaseConnection]:
    print("Starting MCP server for Dormitory Management System...")
    db = DatabaseConnection()
    try:
        yield db
    finally:
        print("Shutting down MCP server...")

mcp = FastMCP("Dormitory Management System", lifespan=app_lifespan)

# Resources
@mcp.resource("schema://dormitory")
def get_schema(ctx: Context) -> str:
    db = ctx.request_context.lifespan_context
    items = db.execute_query("SELECT sql FROM sqlite_master WHERE type='table'")
    return "\n\n".join(it["sql"] for it in items if it.get("sql"))

@mcp.resource("data://students")
def get_students(ctx: Context) -> str:
    db = ctx.request_context.lifespan_context
    rows = db.execute_query("SELECT * FROM students")
    return "\n".join(f"ID: {r['student_id']}, Name: {r['name']}, Status: {r['status']}" for r in rows)

@mcp.resource("data://rooms")
def get_rooms(ctx: Context) -> str:
    db = ctx.request_context.lifespan_context
    rows = db.execute_query("SELECT * FROM rooms")
    return "\n".join(
        f"Room: {r['room_number']} (Floor {r['floor']}), Capacity: {r['capacity']}"
        for r in rows
    )

@mcp.resource("data://occupancy")
def get_occupancy(ctx: Context) -> str:
    db = ctx.request_context.lifespan_context
    rows = db.execute_query("""
        SELECT r.floor, r.room_number,
               COUNT(o.student_id) AS occupied,
               r.capacity
        FROM rooms r
        LEFT JOIN occupancy o
          ON r.room_id = o.room_id AND o.check_out_date IS NULL
        GROUP BY r.room_id
        ORDER BY r.floor, r.room_number
    """)
    return "\n".join(
        f"Room {r['room_number']} (Floor {r['floor']}): "
        f"{r['occupied']}/{r['capacity']} occupied"
        for r in rows
    )

@mcp.resource("data://maintenance")
def get_maintenance(ctx: Context) -> str:
    db = ctx.request_context.lifespan_context
    rows = db.execute_query("""
        SELECT m.request_id, r.floor, r.room_number,
               m.issue_description, m.status, m.reported_date
        FROM maintenance m
        JOIN rooms r ON m.room_id = r.room_id
        ORDER BY m.reported_date DESC
    """)
    return "\n".join(
        f"ID: {m['request_id']}, Room: {m['room_number']} (Floor {m['floor']}), "
        f"Issue: {m['issue_description']}, Status: {m['status']}"
        for m in rows
    )

# Tools
@mcp.tool()
def query_database(ctx: Context, sql_query: str) -> str:
    forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE"]
    if any(k in sql_query.upper() for k in forbidden):
        return "Error: Only SELECT queries are allowed."
    if not sql_query.strip().upper().startswith("SELECT"):
        return "Error: Only SELECT queries are allowed."
    db = ctx.request_context.lifespan_context
    rows = db.execute_query(sql_query)
    if not rows:
        return "No results."
    if "error" in rows[0]:
        return f"Error: {rows[0]['error']}"
    # Format as table
    keys = rows[0].keys()
    header = " | ".join(keys)
    sep = "-" * len(header)
    lines = [header, sep]
    for r in rows:
        lines.append(" | ".join(str(r[k]) for k in keys))
    return "\n".join(lines)

@mcp.tool()
def find_student(ctx: Context, search_term: str) -> str:
    db = ctx.request_context.lifespan_context
    rows = db.execute_query(f"""
        SELECT s.*, r.floor, r.room_number
        FROM students s
        LEFT JOIN occupancy o 
          ON s.student_id = o.student_id AND o.check_out_date IS NULL
        LEFT JOIN rooms r ON o.room_id = r.room_id
        WHERE s.student_id LIKE '%{search_term}%' 
           OR s.name LIKE '%{search_term}%'
    """)
    if not rows:
        return f"No students found matching '{search_term}'."
    out = []
    for s in rows:
        room = (
            f"Room {s['room_number']} (Floor {s['floor']})"
            if s.get('room_number') else "Not assigned"
        )
        out.append(
            f"ID: {s['student_id']}\n"
            f"Name: {s['name']}\n"
            f"Program: {s['program']}\n"
            f"Status: {s['status']}\n"
            f"Room: {room}\n"
        )
    return "\n".join(out)

@mcp.tool()
def room_occupants(ctx: Context, floor: int, room_number: str) -> str:
    db = ctx.request_context.lifespan_context
    rows = db.execute_query(f"""
        SELECT s.student_id, s.name, s.program, o.check_in_date
        FROM students s
        JOIN occupancy o ON s.student_id = o.student_id
        JOIN rooms r ON o.room_id = r.room_id
        WHERE r.floor = {floor} 
          AND r.room_number = '{room_number}'
          AND o.check_out_date IS NULL
    """)
    if not rows:
        return f"No current occupants found for Room {room_number} on Floor {floor}."
    lines = [f"Occupants of Room {room_number} (Floor {floor}):", "-"*40]
    for o in rows:
        lines.append(
            f"ID: {o['student_id']}\n"
            f"Name: {o['name']}\n"
            f"Program: {o['program']}\n"
            f"Check-in: {o['check_in_date']}\n"
        )
    return "\n".join(lines)

@mcp.tool()
def check_availability(ctx: Context) -> str:
    db = ctx.request_context.lifespan_context
    rows = db.execute_query("""
        SELECT r.floor, r.room_number, r.capacity,
               (SELECT COUNT(*) FROM occupancy o 
                 WHERE o.room_id = r.room_id 
                   AND o.check_out_date IS NULL) AS occupied,
               r.capacity - 
               (SELECT COUNT(*) FROM occupancy o 
                 WHERE o.room_id = r.room_id 
                   AND o.check_out_date IS NULL) AS available
        FROM rooms r
        ORDER BY r.floor, r.room_number
    """)
    lines = ["Room Availability:"]
    for f in range(1, 4):
        lines.append(f"\nFloor {f}:")
        lines.append("-"*40)
        for r in rows:
            if r['floor'] == f:
                status = "FULL" if r['available'] == 0 else f"{r['available']} beds available"
                lines.append(
                    f"Room {r['room_number']}: "
                    f"{r['occupied']}/{r['capacity']} occupied - {status}"
                )
    return "\n".join(lines)

@mcp.tool()
def predict_occupancy(ctx: Context, months_ahead: int) -> str:
    db = ctx.request_context.lifespan_context
    rows = db.execute_query("""
        SELECT strftime('%Y-%m', check_in_date) AS ym, COUNT(*) AS num
        FROM occupancy
        WHERE check_out_date IS NULL 
           OR check_out_date > date('now','-1 year')
        GROUP BY ym ORDER BY ym
    """)
    if not rows or len(rows) < 2:
        return "Not enough historical data."
    y = np.array([r['num'] for r in rows])
    X = np.arange(len(y)).reshape(-1, 1)
    model = LinearRegression().fit(X, y)
    future_X = np.arange(len(y), len(y)+months_ahead).reshape(-1, 1)
    preds = model.predict(future_X).astype(int)
    return "\n".join(f"Month +{i+1}: {p} residents" for i, p in enumerate(preds))

@mcp.tool()
def update_room_capacity(ctx: Context, room_id: int, new_capacity: int) -> str:
    if new_capacity < 1:
        return "Capacity must be ≥ 1."
    conn = sqlite3.connect("dormitory.db")
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE rooms SET capacity = ? WHERE room_id = ?",
            (new_capacity, room_id)
        )
        if cur.rowcount == 0:
            return f"No room with ID {room_id} found."
        conn.commit()
        return f"Room {room_id} capacity set to {new_capacity}."
    except Exception as e:
        return f"Update error: {e}"
    finally:
        conn.close()

@mcp.prompt()
def help_prompt() -> str:
    return """
    You are a helpful assistant for a dormitory management system. You can:

    1. Answer questions about students, rooms, and occupancy
    2. Check room availability
    3. Find information about specific students
    4. View maintenance requests
    5. Predict future occupancy (tool: predict_occupancy)
    6. Update room capacity (tool: update_room_capacity)

    Use the available tools and resources to provide accurate information.
    """

# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("dorm_mcp_server:mcp", host="0.0.0.0", port=3000)
