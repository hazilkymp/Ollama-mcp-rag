# Building a RAG System for Dormitory Management with MCP and Ollama

I'll create a complete step-by-step guide for building a Retrieval Augmented Generation (RAG) system for dormitory management. This guide is designed to be beginner-friendly for Linux users and will use Ollama with Llama 3.2 as the LLM and all-MiniLM:L6-v2 for embeddings.

Let's start with the setup process:

## Step 1: Set Up the Environment

First, we need to install the necessary dependencies:

```bash
# Update your system
sudo apt update
sudo apt upgrade -y

# Install basic dependencies
sudo apt install -y python3-pip python3-venv git sqlite3

# Create a virtual environment
mkdir dorm_rag_system
cd dorm_rag_system
python3 -venv venv
source venv/bin/activate

# Install required Python packages
pip install mcp-api langchain sentence-transformers fastmcp chromadb pandas
```

## Step 2: Install Ollama

Ollama needs to be installed to run the Llama 3.2 model locally:

```bash
# Download and install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Verify Ollama installation
ollama --version

# Pull the Llama 3.2 model
ollama pull llama3.2

# Test the model
ollama run llama3.2 "Hello, how are you?"
```

## Step 3: Create the Dormitory Database

Let's create a SQLite database with the necessary tables and sample data for our dormitory management system:
```code
create_dorm_database.py
```

## Step 4: Set Up the MCP Server

Now, let's create an MCP server that will interact with our SQLite database:
```code
dorm_mcp_server.py
```

## Step 5: Create the RAG System

Now let's create our RAG system that will use all-MiniLM:L6-v2 for embeddings and connect to our MCP server:
```code
dorm_rag_system.py
```

Finally, let's create a simple launcher script to make it easier to start the system:
```code
run_rag_system.sh
```

## Step 6: Using the System

Let's create a usage guide to help you interact with the system:
### Dormitory Management RAG System - Usage Guide

This guide will help you use the Dormitory Management RAG system, which combines a SQLite database with a Retrieval Augmented Generation (RAG) system using Ollama and MCP.

#### a. Setup Instructions

1. Make sure all files are in the same directory:
   - `create_dorm_database.py` - Creates the SQLite database with sample data
   - `dorm_mcp_server.py` - MCP server for interacting with the database
   - `dorm_rag_system.py` - Main RAG system implementation
   - `run_rag_system.sh` - Convenience script to run the system

2. Make the run script executable:
   ```bash
   chmod +x run_rag_system.sh
   ```

3. Run the system:
   ```bash
   ./run_rag_system.sh
   ```

#### b. Example Queries

Here are some example queries you can try with the system:

##### 1. Student Information

- "Who are the students living in room 101 on floor 1?"
- "Find a student named Alex"
- "How many students are currently checked out?"
- "Show me all students enrolled in Computer Science"
- "Which student has been staying in the dorm the longest?"

##### 2. Room Information

- "Are there any available beds on floor 2?"
- "Show room availability in the dormitory"
- "Which rooms have maintenance issues?"
- "How many rooms are completely full?"
- "What's the occupancy rate of the dormitory?"

##### 3. Maintenance Information

- "List all pending maintenance requests"
- "What are the common maintenance issues in the dorm?"
- "How long does it take on average to resolve maintenance issues?"
- "Which floor has the most maintenance problems?"

##### 4. General Statistics

- "What's the gender distribution in the dormitory?"
- "Which program has the most students in the dorm?"
- "What percentage of beds are currently occupied?"
- "How many students have checked out in the past month?"

#### c. System Architecture

This RAG system combines several components:

1. **SQLite Database**: Stores dormitory data including students, rooms, occupancy, and maintenance records.

2. **MCP Server**: Provides tools and resources for accessing and querying the database.

3. **Vector Database (ChromaDB)**: Stores embeddings of database records for semantic search.

4. **Embedding Model (all-MiniLM:L6-v2)**: Creates vector embeddings from text.

5. **LLM (Llama 3.2 via Ollama)**: Generates natural language responses based on the retrieved context.

#### d. Troubleshooting

If you encounter issues:

1. **Ollama Connection Error**: Make sure Ollama is running with `ollama serve`.

2. **Missing Models**: You may need to manually pull the Llama 3.2 model with `ollama pull llama3.2`.

3. **Database Issues**: If the database seems corrupted, delete `dormitory.db` and restart to recreate it.

4. **MCP Server Connection**: If you see MCP connection errors, make sure port 3000 is available.

5. **Python Package Issues**: You may need to install additional packages with `pip install package-name`.

To exit the system, type "exit" or "quit" in the CLI, or press Ctrl+C.

## Complete Guide for Building a RAG System for Dormitory Management

Now that I've created all the necessary components, let me provide a step-by-step guide on how to set up and use this system on your Ubuntu 22.04 VM:

### Step 1: Prepare Your Environment

1. Update your system and install the prerequisites:
   ```bash
   sudo apt update
   sudo apt upgrade -y
   sudo apt install -y python3-pip python3-venv git sqlite3 curl
   ```

2. Create a project directory and navigate to it:
   ```bash
   mkdir dorm_rag_system
   cd dorm_rag_system
   ```

3. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. Install the required Python packages:
   ```bash
   pip install mcp-api langchain sentence-transformers fastmcp chromadb pandas requests
   ```

### Step 2: Install Ollama

1. Install Ollama using the installation script:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. Start the Ollama service:
   ```bash
   ollama serve
   ```

3. In a new terminal, download the Llama 3.2 model:
   ```bash
   ollama pull llama3.2
   ```

### Step 3: Set Up the Files

1. Create all the necessary files in your project directory:
   - `create_dorm_database.py`: For generating the SQLite database with sample dormitory data
   - `dorm_mcp_server.py`: For running the MCP server that interacts with the database
   - `dorm_rag_system.py`: The main RAG system that uses Ollama and MCP
   - `run_rag_system.sh`: A convenience script to run everything

2. Make the run script executable:
   ```bash
   chmod +x run_rag_system.sh
   ```

### Step 4: Generate the Database

1. Create the database with sample data:
   ```bash
   python3 create_dorm_database.py
   ```

   This will create a `dormitory.db` file with tables for students, rooms, occupancy, and maintenance requests.

### Step 5: Run the System

1. Start the RAG system using the convenience script:
   ```bash
   ./run_rag_system.sh
   ```

   The script will:
   - Activate the virtual environment
   - Check if Ollama is running
   - Ensure the Llama 3.2 model is available
   - Create the database if it doesn't exist
   - Start the RAG system with the interactive CLI

### Step 6: Interact with the System

Once the system is running, you can interact with it by typing natural language queries about the dormitory. For example:

- "Show me all available rooms on floor 2"
- "Find student John Smith"
- "How many maintenance requests are pending?"
- "What's the overall occupancy rate of the dormitory?"

The system will process your query by:
1. Finding relevant information in the vector database
2. Querying the MCP server if needed
3. Using Llama 3.2 to generate a natural language response

### Understanding the Components

- **Database (SQLite)**: Stores all dormitory data in a structured format
- **MCP Server**: Provides tools for querying the database and accessing resources
- **Vector Store (ChromaDB)**: Enables semantic search of the dormitory data
- **Embedding Model (all-MiniLM:L6-v2)**: Creates vector embeddings for semantic search
- **LLM (Llama 3.2)**: Generates natural language responses based on the retrieved context

### Tips for Better Usage

1. **Be specific in your queries**: The more specific your query, the better the system can retrieve relevant information.

2. **Ask follow-up questions**: The system maintains conversation history, so you can ask follow-up questions.

3. **Try different query types**: The system can handle questions about students, rooms, occupancy, and maintenance.

4. **Exit gracefully**: Type "exit" or "quit" to properly close the system.

This RAG system provides a natural language interface to your dormitory database, making it easy to access and understand the information without writing SQL queries manually. The combination of vector search, MCP tools, and LLM generation creates a powerful and flexible system that can handle a wide range of queries about your dormitory management system.
