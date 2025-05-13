#!/usr/bin/env python3
import os
import sys
import sqlite3
import requests
from typing import List, Optional

from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions
from mcp import ClientSession

# Initialize embedding model
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# Set up ChromaDB and collections
chroma_client = chromadb.Client()
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
students_collection = chroma_client.get_or_create_collection(
    name="students_data", embedding_function=embedding_function
)
rooms_collection = chroma_client.get_or_create_collection(
    name="rooms_data", embedding_function=embedding_function
)
occupancy_collection = chroma_client.get_or_create_collection(
    name="occupancy_data", embedding_function=embedding_function
)
maintenance_collection = chroma_client.get_or_create_collection(
    name="maintenance_data", embedding_function=embedding_function
)
schema_collection = chroma_client.get_or_create_collection(
    name="schema_data", embedding_function=embedding_function
)

class DormitoryRAG:
    def __init__(
        self,
        db_path: str = "dormitory.db",
        mcp_host: str = "localhost",
        mcp_port: int = 3000
    ):
        self.db_path = db_path
        self.mcp_host = mcp_host
        self.mcp_port = mcp_port

        # Ollama chat endpoint (via env var or default)
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434") + "/api/chat"
        self.model = os.getenv("MODEL", "llama3.1")

        # Simple MCP client via positional args
        try:
            self.mcp_session = ClientSession(self.mcp_host, self.mcp_port)
        except Exception as e:
            print(f"Failed to initialize MCP session: {e}")
            sys.exit(1)

        self.conversation_history: List[dict] = []
        self.max_history_length = 10

    def initialize_database(self) -> None:
        print("Initializing database and loading into vector store...")
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Load schema
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
        schema_texts = [row['sql'] for row in cursor.fetchall() if row['sql']]
        if schema_texts:
            schema_collection.add(
                documents=schema_texts,
                ids=[f"schema_{i}" for i in range(len(schema_texts))],
                metadatas=[{"type": "schema"} for _ in schema_texts]
            )

        # Load students
        cursor.execute("SELECT * FROM students")
        students = cursor.fetchall()
        if students:
            docs, ids, metas = [], [], []
            for s in students:
                d = dict(s)
                text = (
                    f"Student ID: {d['student_id']}, Name: {d['name']}, "
                    f"Gender: {d['gender']}, Program: {d['program']}, Status: {d['status']}"
                )
                docs.append(text)
                ids.append(f"student_{d['student_id']}")
                metas.append({"type": "student", "id": d['student_id']})
            students_collection.add(documents=docs, ids=ids, metadatas=metas)

        # Load rooms
        cursor.execute("SELECT * FROM rooms")
        rooms = cursor.fetchall()
        if rooms:
            docs, ids, metas = [], [], []
            for r in rooms:
                d = dict(r)
                text = (
                    f"Room ID: {d['room_id']}, Floor: {d['floor']}, "
                    f"Room Number: {d['room_number']}, Capacity: {d['capacity']}"
                )
                docs.append(text)
                ids.append(f"room_{d['room_id']}")
                metas.append({"type": "room", "id": d['room_id']})
            rooms_collection.add(documents=docs, ids=ids, metadatas=metas)

        # Load occupancy
        cursor.execute("""
            SELECT o.*, s.name AS student_name, r.floor, r.room_number
            FROM occupancy o
            JOIN students s ON o.student_id = s.student_id
            JOIN rooms r ON o.room_id = r.room_id
        """)
        occs = cursor.fetchall()
        if occs:
            docs, ids, metas = [], [], []
            for o in occs:
                d = dict(o)
                status = (
                    f"checked out on {d['check_out_date']}"
                    if d['check_out_date']
                    else "currently residing"
                )
                text = (
                    f"Student {d['student_name']} (ID: {d['student_id']}) "
                    f"checked in to Room {d['room_number']} on Floor {d['floor']} "
                    f"on {d['check_in_date']} and is {status}."
                )
                docs.append(text)
                ids.append(f"occupancy_{d['occupancy_id']}")
                metas.append({"type": "occupancy", "id": d['occupancy_id']})
            occupancy_collection.add(documents=docs, ids=ids, metadatas=metas)

        # Load maintenance
        cursor.execute("""
            SELECT m.*, r.floor, r.room_number
            FROM maintenance m
            JOIN rooms r ON m.room_id = r.room_id
        """)
        mains = cursor.fetchall()
        if mains:
            docs, ids, metas = [], [], []
            for m in mains:
                d = dict(m)
                status = (
                    f"resolved on {d['resolved_date']}"
                    if d['resolved_date']
                    else f"status: {d['status']}"
                )
                text = (
                    f"Maintenance request #{d['request_id']} for Room {d['room_number']} "
                    f"on Floor {d['floor']}: {d['issue_description']}. "
                    f"Reported on {d['reported_date']}, {status}."
                )
                docs.append(text)
                ids.append(f"maintenance_{d['request_id']}")
                metas.append({"type": "maintenance", "id": d['request_id']})
            maintenance_collection.add(documents=docs, ids=ids, metadatas=metas)

        conn.close()
        print("Database loaded into vector store successfully!")

    def query_ollama(self, prompt: str, context: Optional[str] = None) -> str:
        system_msg = "You are a helpful assistant for a dormitory management system."
        if context:
            system_msg += "\n\nContext information:\n" + context

        if len(self.conversation_history) >= self.max_history_length * 2:
            self.conversation_history = self.conversation_history[2:]
        self.conversation_history.append({"role": "user", "content": prompt})
        messages = [{"role": "system", "content": system_msg}] + self.conversation_history

        payload = {"model": self.model, "messages": messages, "stream": False}
        try:
            resp = requests.post(self.ollama_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            reply = data.get("message", {}).get("content", "No response.")
            self.conversation_history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            return f"Error querying Ollama: {e}"

    def query_vector_store(self, query: str, k: int = 5) -> List[str]:
        results: List[str] = []
        for col in [
            students_collection,
            rooms_collection,
            occupancy_collection,
            maintenance_collection,
            schema_collection,
        ]:
            try:
                res = col.query(query_texts=[query], n_results=min(k, col.count()))
                docs = res.get("documents", [[]])[0]
                results.extend(docs)
            except Exception:
                pass
        return results[:k]

    def run_cli(self):
        print("=== Dormitory RAG System ===")
        print("Type 'exit' or 'quit' to stop.")
        while True:
            user_input = input("\n>> ").strip()
            if not user_input or user_input.lower() in ("exit", "quit"):
                print("Exiting Dormitory RAG System.")
                break

            # 1) Try MCP tool call
            try:
                tool_output = self.mcp_session.call(user_input)
                if tool_output is not None:
                    print(tool_output)
                    continue
            except Exception as e:
                print(f"[Tool error: {e}] Falling back to LLM...\n")

            # 2) Fallback: RAG + LLM
            context = "\n".join(self.query_vector_store(user_input, k=5))
            response = self.query_ollama(user_input, context=context)
            print("\nResponse:\n", response)

if __name__ == "__main__":
    rag = DormitoryRAG()
    rag.initialize_database()
    rag.run_cli()
