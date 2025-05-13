#!/bin/bash

# This script runs the Dormitory Management RAG System

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Dormitory Management RAG System ===${NC}"

# 1) Ensure Python 3 & venv
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed. Please install Python 3 and try again.${NC}"
    exit 1
fi
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Setting up environment...${NC}"
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install mcp-api langchain sentence-transformers fastmcp chromadb pandas requests scikit-learn

# 2) Ollama configuration
#    Before running, you can override these:
#      export OLLAMA_URL="http://10.0.2.2:11434"
#      export MODEL="llama3.1"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
MODEL="${MODEL:-llama3.1}"

# Only bootstrap local Ollama if pointing at localhost
if [[ "$OLLAMA_URL" == http://localhost* ]]; then
  # Install Ollama CLI if needed
  if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}Installing Ollama CLI...${NC}"
    curl -fsSL https://ollama.com/install.sh | sh
  fi
  # Start local Ollama if not already
  if ! curl -s "$OLLAMA_URL/api/version" &> /dev/null; then
    echo -e "${YELLOW}Starting local Ollama service...${NC}"
    ollama serve &
    sleep 5
  fi
  # Pull model if missing
  if ! ollama list | grep -q "$MODEL"; then
    echo -e "${YELLOW}Pulling model $MODEL locally...${NC}"
    ollama pull "$MODEL"
  fi
else
  echo -e "${YELLOW}Using remote Ollama at $OLLAMA_URL, skipping local pull${NC}"
fi

# 3) Database setup
if [ ! -f "dormitory.db" ]; then
  echo -e "${YELLOW}Creating dormitory database...${NC}"
  python3 create_dorm_database.py
fi

# 4) Run the RAG system
echo -e "${GREEN}Starting Dormitory Management RAG System...${NC}"
export OLLAMA_URL
export MODEL
python3 dorm_rag_system.py

deactivate
