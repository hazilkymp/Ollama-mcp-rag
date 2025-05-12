#!/usr/bin/env python3
import sqlite3
import os
import asyncio
from sqlite3 import Row
from typing import List, Dict, Any, Optional
import json
import requests
import time
import sys
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions
from mcp import ClientSession, types

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
        print("Initializing database and loading into vector store...")
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
        schema_texts = [row['sql'] for row in cursor.fetchall() if row['sql']]
        if schema_texts:
            schema_collection.add(
                documents=schema_texts,
                ids=[f"schema_{i}" for i in range(len(schema_texts))],
                metadatas=[{"type": "schema"} for _ in schema_texts]
            )

        cursor.execute("SELECT * FROM students")
        students = cursor.fetchall()
        students_texts, students_ids, students_metadata = [], [], []
        for student in students:
            d = dict(student)
            t = f"Student ID: {d['student_id']}, Name: {d['name']}, Gender: {d['gender']}, Program: {d['program']}, Status: {d['status']}"
            students_texts.append(t)
            students_ids.append(f"student_{d['student_id']}")
            students_metadata.append({"type": "student", "id": d['student_id']})
        if students_texts:
            students_collection.add(documents=students_texts, ids=students_ids, metadatas=students_metadata)

        cursor.execute("SELECT * FROM rooms")
        rooms = cursor.fetchall()
        rooms_texts, rooms_ids, rooms_metadata = [], [], []
        for room in rooms:
            d = dict(room)
            t = f"Room ID: {d['room_id']}, Floor: {d['floor']}, Room Number: {d['room_number']}, Capacity: {d['capacity']}"
            rooms_texts.append(t)
            rooms_ids.append(f"room_{d['room_id']}")
            rooms_metadata.append({"type": "room", "id": d['room_id']})
        if rooms_texts:
            rooms_collection.add(documents=rooms_texts, ids=rooms_ids, metadatas=rooms_metadata)

        cursor.execute("""
            SELECT o.*, s.name as student_name, r.floor, r.room_number
            FROM occupancy o
            JOIN students s ON o.student_id = s.student_id
            JOIN rooms r ON o.room_id = r.room_id
        """)
        occupancies = cursor.fetchall()
        occupancy_texts, occupancy_ids, occupancy_metadata = [], [], []
        for o in occupancies:
            d = dict(o)
            status = f"checked out on {d['check_out_date']}" if d['check_out_date'] else "currently residing"
            t = f"Student {d['student_name']} (ID: {d['student_id']}) checked in to Room {d['room_number']} on Floor {d['floor']} on {d['check_in_date']} and is {status}."
            occupancy_texts.append(t)
            occupancy_ids.append(f"occupancy_{d['occupancy_id']}")
            occupancy_metadata.append({"type": "occupancy", "id": d['occupancy_id']})
        if occupancy_texts:
            occupancy_collection.add(documents=occupancy_texts, ids=occupancy_ids, metadatas=occupancy_metadata)

        cursor.execute("""
            SELECT m.*, r.floor, r.room_number
            FROM maintenance m
            JOIN rooms r ON m.room_id = r.room_id
        """)
        maintenance_requests = cursor.fetchall()
        maintenance_texts, maintenance_ids, maintenance_metadata = [], [], []
        for m in maintenance_requests:
            d = dict(m)
            status = f"resolved on {d['resolved_date']}" if d['resolved_date'] else f"status: {d['status']}"
            t = f"Maintenance request #{d['request_id']} for Room {d['room_number']} on Floor {d['floor']}: {d['issue_description']}. Reported on {d['reported_date']}, {status}."
            maintenance_texts.append(t)
            maintenance_ids.append(f"maintenance_{d['request_id']}")
            maintenance_metadata.append({"type": "maintenance", "id": d['request_id']})
        if maintenance_texts:
            maintenance_collection.add(documents=maintenance_texts, ids=maintenance_ids, metadatas=maintenance_metadata)

        conn.close()
        print("Database loaded into vector store successfully!")

    def query_ollama(self, prompt: str, context: Optional[str] = None) -> str:
        system_message = "You are a helpful assistant for a dormitory management system. Answer questions based on the provided context."
        if context:
            system_message += "\n\nContext information:\n" + context
        if len(self.conversation_history) >= self.max_history_length * 2:
            self.conversation_history = self.conversation_history[2:]
        self.conversation_history.append({"role": "user", "content": prompt})
        messages = [{"role": "system", "content": system_message}] + self.conversation_history
        payload = {"model": "llama3.2", "messages": messages, "stream": False}
        try:
            response = requests.post("http://localhost:11434/api/chat", json=payload)
            response.raise_for_status()
            result = response.json()
            reply = result.get("message", {}).get("content", "I couldn't generate a response.")
            self.conversation_history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            return f"Error querying Ollama: {str(e)}"

    def query_vector_store(self, query: str, k: int = 5) -> List[str]:
        results = []
        for collection in [students_collection, rooms_collection, occupancy_collection, maintenance_collection, schema_collection]:
            try:
                collection_results = collection.query(
                    query_texts=[query],
                    n_results=min(k, collection.count())
                )
                docs = collection_results.get("documents", [[]])[0]
                results.extend(docs)
            except Exception as e:
                print(f"Error querying collection: {e}")
        return results[:k]

    def run_cli(self):
        print("=== Dormitory RAG System ===")
        print("Type 'exit' or 'quit' to stop.")
        while True:
            user_input = input("\n>> ").strip()
            if user_input.lower() in ["exit", "quit"]:
                print("Exiting Dormitory RAG System.")
                break
            context_chunks = self.query_vector_store(user_input, k=5)
            combined_context = "\n".join(context_chunks)
            response = self.query_ollama(user_input, context=combined_context)
            print("\nResponse:\n", response)

if __name__ == "__main__":
    rag = DormitoryRAG()
    rag.initialize_database()
    rag.run_cli()
