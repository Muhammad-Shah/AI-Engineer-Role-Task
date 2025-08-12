#!/usr/bin/env python3
"""
Quick test script for the Database Chatbot API
Run this after starting the API to verify all endpoints work correctly
"""

import requests
import json
import time
from typing import Dict, Any

API_BASE = "http://localhost:8000"

def test_root():
    """Test root endpoint"""
    print("Testing root endpoint...")
    response = requests.get(f"{API_BASE}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_database_connection():
    """Test database connection (using PostgreSQL from docker-compose)"""
    print("\nTesting database connection...")
    
    # Connect to PostgreSQL
    payload = {
        "host": "localhost",  # Use "postgres" if running inside Docker
        "port": 5432,
        "database": "sampledb",
        "username": "postgres", 
        "password": "postgres",
        "db_type": "postgresql"
    }
    
    response = requests.post(f"{API_BASE}/api/database/connect", json=payload)
    print(f"Connect Status: {response.status_code}")
    result = response.json()
    print(f"Connect Response: {json.dumps(result, indent=2)}")
    
    if result.get("status") == "connected":
        connection_id = result["connection_id"]
        
        # Validate connection
        validate_response = requests.get(f"{API_BASE}/api/database/validate/{connection_id}")
        print(f"Validate Status: {validate_response.status_code}")
        print(f"Validate Response: {json.dumps(validate_response.json(), indent=2)}")
        
        return connection_id
    
    return None

def test_chat_session():
    """Test chat session management"""
    print("\nTesting chat session management...")
    
    # Create session
    create_response = requests.post(f"{API_BASE}/api/chat/sessions")
    print(f"Create Session Status: {create_response.status_code}")
    session_data = create_response.json()
    print(f"Session Created: {json.dumps(session_data, indent=2)}")
    
    session_id = session_data.get("session_id")
    
    # List sessions
    list_response = requests.get(f"{API_BASE}/api/chat/sessions")
    print(f"List Sessions Status: {list_response.status_code}")
    print(f"Sessions: {json.dumps(list_response.json(), indent=2)}")
    
    return session_id

def test_chat_query(connection_id: str, session_id: str):
    """Test natural language queries"""
    print("\nTesting natural language queries...")
    
    queries = [
        "Show me all users",
        "How many users are there?",
        "List users in Engineering department",
        "Show orders from last month",
        "Count active users"
    ]
    
    for query in queries:
        print(f"\nTesting query: '{query}'")
        payload = {
            "connection_id": connection_id,
            "message": query,
            "session_id": session_id
        }
        
        try:
            response = requests.post(f"{API_BASE}/api/chat/query", json=payload, stream=True, timeout=30)
            print(f"Query Status: {response.status_code}")
            
            if response.status_code == 200:
                print("Streaming response:")
                for line in response.iter_lines():
                    if line:
                        event_data = json.loads(line)
                        print(f"  {json.dumps(event_data, indent=2)}")
                        if event_data.get("event") == "end":
                            break
            else:
                print(f"Error: {response.text}")
                
        except Exception as e:
            print(f"Query failed: {e}")
        
        time.sleep(1)  # Brief pause between queries

def test_mongodb_connection():
    """Test MongoDB connection"""
    print("\nTesting MongoDB connection...")
    
    payload = {
        "host": "localhost",  # Use "mongodb" if running inside Docker
        "port": 27017,
        "database": "sampledb",
        "username": "appuser",
        "password": "apppassword", 
        "db_type": "mongodb"
    }
    
    response = requests.post(f"{API_BASE}/api/database/connect", json=payload)
    print(f"MongoDB Connect Status: {response.status_code}")
    result = response.json()
    print(f"MongoDB Response: {json.dumps(result, indent=2)}")
    
    return result.get("connection_id") if result.get("status") == "connected" else None

def main():
    """Run all tests"""
    print("=" * 60)
    print("Database Chatbot API Test Suite")
    print("=" * 60)
    
    # Test basic connectivity
    if not test_root():
        print("❌ API is not running!")
        return
    
    print("✅ API is running")
    
    # Test PostgreSQL
    pg_connection_id = test_database_connection()
    if not pg_connection_id:
        print("❌ PostgreSQL connection failed!")
        print("Make sure PostgreSQL is running (docker-compose up)")
        return
    
    print("✅ PostgreSQL connection successful")
    
    # Test sessions
    session_id = test_chat_session()
    if not session_id:
        print("❌ Session creation failed!")
        return
        
    print("✅ Chat session management working")
    
    # Test queries (requires OPENAI_API_KEY)
    print("\n⚠️  Chat queries require OPENAI_API_KEY environment variable")
    print("Set your OpenAI API key to test LLM functionality")
    
    try:
        test_chat_query(pg_connection_id, session_id)
        print("✅ Query testing completed")
    except Exception as e:
        print(f"⚠️  Query testing failed (likely missing OPENAI_API_KEY): {e}")
    
    # Test MongoDB
    mongo_connection_id = test_mongodb_connection()
    if mongo_connection_id:
        print("✅ MongoDB connection successful")
    else:
        print("⚠️  MongoDB connection failed (check if MongoDB is running)")
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("✅ API Running")
    print("✅ PostgreSQL Connected") 
    print("✅ Session Management")
    print("⚠️  NL Queries (needs OPENAI_API_KEY)")
    print("⚠️  MongoDB (optional)")
    print("=" * 60)

if __name__ == "__main__":
    main()
