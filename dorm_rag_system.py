import sqlite3
import os
import asyncio
from sqlite3 import Row
from typing import List, Dict, Any, Optional
import json
import requests
import time
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions
from mcp import ClientSession, HttpServerParameters, types
from mcp.client.http import http_client

# Initialize embedding model
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# Set up ChromaDB
chroma_client = chromadb.Client()
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

# Create or get collections for different document types
students_collection = chroma_client.get_or_create_collection(
    name="students_data",
    embedding_function=embedding_function
)

rooms_collection = chroma_client.get_or_create_collection(
    name="rooms_data",
    embedding_function=embedding_function
)

occupancy_collection = chroma_client.get_or_create_collection(
    name="occupancy_data",
    embedding_function=embedding_function
)

maintenance_collection = chroma_client.get_or_create_collection(
    name="maintenance_data",
    embedding_function=embedding_function
)

schema_collection = chroma_client.get_or_create_collection(
    name="schema_data",
    embedding_function=embedding_function
)

class DormitoryRAG:
    def __init__(self, db_path: str = "dormitory.db", mcp_port: int = 3000):
        self.db_path = db_path
        self.mcp_port = mcp_port
        self.ollama_url = "http://localhost:11434/api/generate"
        self.context_window_size = 4096
        self.mcp_session = None
        self.conversation_history = []
        self.max_history_length = 10
        
    def initialize_database(self) -> None:
        """Connect to the database and load data into ChromaDB collections"""
        print("Initializing database and loading into vector store...")
        
        # Connect to SQLite
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get schema
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
        schema_texts = [row['sql'] for row in cursor.fetchall() if row['sql']]
        
        # Index schema
        if schema_texts:
            schema_collection.add(
                documents=schema_texts,
                ids=[f"schema_{i}" for i in range(len(schema_texts))],
                metadatas=[{"type": "schema"} for _ in schema_texts]
            )
        
        # Get students data
        cursor.execute("SELECT * FROM students")
        students = cursor.fetchall()
        
        # Format students data for embedding
        students_texts = []
        students_ids = []
        students_metadata = []
        
        for student in students:
            student_dict = dict(student)
            student_text = f"Student ID: {student_dict['student_id']}, Name: {student_dict['name']}, " \
                          f"Gender: {student_dict['gender']}, Program: {student_dict['program']}, " \
                          f"Status: {student_dict['status']}"
            students_texts.append(student_text)
            students_ids.append(f"student_{student_dict['student_id']}")
            students_metadata.append({"type": "student", "id": student_dict['student_id']})
        
        # Index students
        if students_texts:
            students_collection.add(
                documents=students_texts,
                ids=students_ids,
                metadatas=students_metadata
            )
        
        # Get rooms data
        cursor.execute("SELECT * FROM rooms")
        rooms = cursor.fetchall()
        
        # Format rooms data for embedding
        rooms_texts = []
        rooms_ids = []
        rooms_metadata = []
        
        for room in rooms:
            room_dict = dict(room)
            room_text = f"Room ID: {room_dict['room_id']}, Floor: {room_dict['floor']}, " \
                       f"Room Number: {room_dict['room_number']}, Capacity: {room_dict['capacity']}"
            rooms_texts.append(room_text)
            rooms_ids.append(f"room_{room_dict['room_id']}")
            rooms_metadata.append({"type": "room", "id": room_dict['room_id']})
        
        # Index rooms
        if rooms_texts:
            rooms_collection.add(
                documents=rooms_texts,
                ids=rooms_ids,
                metadatas=rooms_metadata
            )
        
        # Get occupancy data with joins
        cursor.execute("""
            SELECT o.*, s.name as student_name, r.floor, r.room_number
            FROM occupancy o
            JOIN students s ON o.student_id = s.student_id
            JOIN rooms r ON o.room_id = r.room_id
        """)
        occupancies = cursor.fetchall()
        
        # Format occupancy data for embedding
        occupancy_texts = []
        occupancy_ids = []
        occupancy_metadata = []
        
        for occupancy in occupancies:
            occ_dict = dict(occupancy)
            checkout_status = f"checked out on {occ_dict['check_out_date']}" if occ_dict['check_out_date'] else "currently residing"
            occ_text = f"Student {occ_dict['student_name']} (ID: {occ_dict['student_id']}) " \
                      f"checked in to Room {occ_dict['room_number']} on Floor {occ_dict['floor']} " \
                      f"on {occ_dict['check_in_date']} and is {checkout_status}."
            occupancy_texts.append(occ_text)
            occupancy_ids.append(f"occupancy_{occ_dict['occupancy_id']}")
            occupancy_metadata.append({"type": "occupancy", "id": occ_dict['occupancy_id']})
        
        # Index occupancy
        if occupancy_texts:
            occupancy_collection.add(
                documents=occupancy_texts,
                ids=occupancy_ids,
                metadatas=occupancy_metadata
            )
        
        # Get maintenance data with joins
        cursor.execute("""
            SELECT m.*, r.floor, r.room_number
            FROM maintenance m
            JOIN rooms r ON m.room_id = r.room_id
        """)
        maintenance_requests = cursor.fetchall()
        
        # Format maintenance data for embedding
        maintenance_texts = []
        maintenance_ids = []
        maintenance_metadata = []
        
        for request in maintenance_requests:
            req_dict = dict(request)
            resolution_status = f"resolved on {req_dict['resolved_date']}" if req_dict['resolved_date'] else f"status: {req_dict['status']}"
            req_text = f"Maintenance request #{req_dict['request_id']} for Room {req_dict['room_number']} " \
                      f"on Floor {req_dict['floor']}: {req_dict['issue_description']}. " \
                      f"Reported on {req_dict['reported_date']}, {resolution_status}."
            maintenance_texts.append(req_text)
            maintenance_ids.append(f"maintenance_{req_dict['request_id']}")
            maintenance_metadata.append({"type": "maintenance", "id": req_dict['request_id']})
        
        # Index maintenance
        if maintenance_texts:
            maintenance_collection.add(
                documents=maintenance_texts,
                ids=maintenance_ids,
                metadatas=maintenance_metadata
            )
        
        conn.close()
        print("Database loaded into vector store successfully!")
    
    def query_ollama(self, prompt: str, context: Optional[str] = None) -> str:
        """Query the Ollama API with the provided prompt and context"""
        system_message = "You are a helpful assistant for a dormitory management system. Answer questions based on the provided context."
        
        if context:
            system_message += "\n\nContext information:\n" + context
        
        # Keep track of conversation history
        if len(self.conversation_history) >= self.max_history_length * 2:
            # Remove oldest message pair (user + assistant) to maintain reasonable context
            self.conversation_history = self.conversation_history[2:]
        
        # Add current user message to history
        self.conversation_history.append({"role": "user", "content": prompt})
        
        # Construct full messages array with system message and history
        messages = [{"role": "system", "content": system_message}] + self.conversation_history
        
        payload = {
            "model": "llama3.2",
            "messages": messages,
            "stream": False
        }
        
        try:
            response = requests.post("http://localhost:11434/api/chat", json=payload)
            response.raise_for_status()
            result = response.json()
            
            # Extract the assistant's message
            assistant_message = result.get("message", {}).get("content", "I couldn't generate a response.")
            
            # Add assistant response to history
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            
            return assistant_message
        except Exception as e:
            error_message = f"Error querying Ollama: {str(e)}"
            print(error_message)
            return error_message
    
    async def start_mcp_server(self):
        """Start the MCP server in a subprocess"""
        import subprocess
        import sys
        
        print("Starting MCP server...")
        # Start the MCP server in a separate process
        server_process = subprocess.Popen(
            [sys.executable, "dorm_mcp_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for the server to start up
        print("Waiting for MCP server to start...")
        time.sleep(5)
        
        return server_process
    
    def query_vector_store(self, query: str, k: int = 5) -> List[str]:
        """Query all collections and return the most relevant documents"""
        results = []
        
        # Query each collection
        for collection in [students_collection, rooms_collection, occupancy_collection, 
                          maintenance_collection, schema_collection]:
            collection_results = collection.query(
                query_texts=[query],
                n_results=min(k, collection.count())
