#!/bin/bash

# This script runs the Dormitory Management RAG System

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Dormitory Management RAG System ===${NC}"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed. Please install Python 3 and try again.${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Setting up environment...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install mcp-api langchain sentence-transformers fastmcp chromadb pandas requests
else
    source venv/bin/activate
fi

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo -e "${RED}Ollama not found. Installing Ollama...${NC}"
    curl -fsSL https://ollama.com/install.sh | sh
fi

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/version &> /dev/null; then
    echo -e "${YELLOW}Starting Ollama service...${NC}"
    ollama serve &
    # Wait for Ollama to start
    sleep 5
fi

# Check if Llama 3.2 model is available
if ! ollama list | grep -q "llama3.2"; then
    echo -e "${YELLOW}Downloading Llama 3.2 model (this may take a while)...${NC}"
    ollama pull llama3.2
fi

# Create database if it doesn't exist
if [ ! -f "dormitory.db" ]; then
    echo -e "${YELLOW}Creating dormitory database...${NC}"
    python3 create_dorm_database.py
fi

# Run the RAG system
echo -e "${GREEN}Starting Dormitory Management RAG System...${NC}"
python3 dorm_rag_system.py

# Deactivate virtual environment when done
deactivate
