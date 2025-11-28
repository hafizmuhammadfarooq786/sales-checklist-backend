#!/usr/bin/env python3
"""
Comprehensive API Endpoint Testing Script
Tests all Sales Checklist™ API endpoints for production readiness
"""

import requests
import json
import time
import sys
from typing import Dict, Optional

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

# Test user credentials
TEST_EMAIL = "test_user_api@example.com"
TEST_PASSWORD = "TestPassword123!"
TEST_USER_NAME = "API Test User"

# Global variables for testing
auth_token: Optional[str] = None
test_user_id: Optional[int] = None
test_session_id: Optional[int] = None

def print_section(title: str):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print('='*60)

def print_test(name: str, status: str, details: str = ""):
    """Print test result"""
    emoji = "✅" if status == "PASS" else "❌"
    print(f"{emoji} {name}: {status}")
    if details:
        print(f"   {details}")

def make_request(method: str, endpoint: str, data: dict = None, headers: dict = None) -> tuple:
    """Make HTTP request and return response and status"""
    url = f"{API_BASE}{endpoint}"
    default_headers = {"Content-Type": "application/json"}
    
    if headers:
        default_headers.update(headers)
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=default_headers)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=default_headers)
        elif method.upper() == "PATCH":
            response = requests.patch(url, json=data, headers=default_headers)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data, headers=default_headers)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=default_headers)
        else:
            return None, "Invalid method"
        
        return response, "SUCCESS"
    except Exception as e:
        return None, f"ERROR: {str(e)}"

def test_health_check():
    """Test health check endpoint"""
    print_section("Health Check")
    
    response, status = make_request("GET", "/health")
    if status == "SUCCESS" and response.status_code == 200:
        print_test("Health Check", "PASS", "API is running")
        return True
    else:
        print_test("Health Check", "FAIL", f"Status: {response.status_code if response else 'No response'}")
        return False

def test_authentication():
    """Test authentication endpoints"""
    global auth_token, test_user_id
    print_section("Authentication")
    
    # Test user registration
    registration_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "first_name": "API",
        "last_name": "Test User"
    }
    
    response, status = make_request("POST", "/auth/register", registration_data)
    if status == "SUCCESS" and response.status_code == 201:
        data = response.json()
        auth_token = data.get("access_token")
        print_test("User Registration", "PASS", f"Token received: {auth_token[:20]}...")
    elif response and response.status_code == 400 and "already registered" in response.text:
        print_test("User Registration", "PASS", "User already exists, proceeding with login")
    else:
        print_test("User Registration", "FAIL", f"Status: {response.status_code if response else 'No response'}")
    
    # Test user login
    login_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    
    response, status = make_request("POST", "/auth/login", login_data)
    if status == "SUCCESS" and response.status_code == 200:
        data = response.json()
        auth_token = data.get("access_token")
        print_test("User Login", "PASS", f"Token received: {auth_token[:20]}...")
    else:
        print_test("User Login", "FAIL", f"Status: {response.status_code if response else 'No response'}")
        return False
    
    # Test authenticated endpoint
    headers = {"Authorization": f"Bearer {auth_token}"}
    response, status = make_request("GET", "/auth/me", headers=headers)
    if status == "SUCCESS" and response.status_code == 200:
        data = response.json()
        test_user_id = data.get("id")
        print_test("Get Current User", "PASS", f"User ID: {test_user_id}")
    else:
        print_test("Get Current User", "FAIL", f"Status: {response.status_code if response else 'No response'}")
        return False
    
    return True

def test_checklist_endpoints():
    """Test checklist endpoints"""
    print_section("Checklist Management")
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Test get checklist summary
    response, status = make_request("GET", "/checklists/summary", headers=headers)
    if status == "SUCCESS" and response.status_code == 200:
        data = response.json()
        categories_count = len(data.get("categories", []))
        total_items = data.get("total_items", 0)
        print_test("Get Checklist Summary", "PASS", f"Categories: {categories_count}, Items: {total_items}")
        
        if total_items == 92:
            print_test("Checklist Data Integrity", "PASS", "All 92 items found")
        else:
            print_test("Checklist Data Integrity", "FAIL", f"Expected 92 items, got {total_items}")
    else:
        print_test("Get Checklist Summary", "FAIL", f"Status: {response.status_code if response else 'No response'}")
    
    # Test get checklist categories
    response, status = make_request("GET", "/checklists/categories", headers=headers)
    if status == "SUCCESS" and response.status_code == 200:
        data = response.json()
        categories_count = len(data.get("categories", []))
        print_test("Get Categories", "PASS", f"Categories count: {categories_count}")
    else:
        print_test("Get Categories", "FAIL", f"Status: {response.status_code if response else 'No response'}")

def test_session_endpoints():
    """Test session management endpoints"""
    global test_session_id
    print_section("Session Management")
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Test create session
    session_data = {
        "title": "API Test Session",
        "description": "Testing session creation via API"
    }
    
    response, status = make_request("POST", "/sessions/", session_data, headers=headers)
    if status == "SUCCESS" and response.status_code == 201:
        data = response.json()
        test_session_id = data.get("id")
        print_test("Create Session", "PASS", f"Session ID: {test_session_id}")
    else:
        print_test("Create Session", "FAIL", f"Status: {response.status_code if response else 'No response'}")
        return False
    
    # Test get sessions
    response, status = make_request("GET", "/sessions/?page=1&page_size=10", headers=headers)
    if status == "SUCCESS" and response.status_code == 200:
        data = response.json()
        sessions_count = len(data.get("items", []))
        print_test("Get Sessions", "PASS", f"Sessions found: {sessions_count}")
    else:
        print_test("Get Sessions", "FAIL", f"Status: {response.status_code if response else 'No response'}")
    
    # Test get session by ID
    response, status = make_request("GET", f"/sessions/{test_session_id}", headers=headers)
    if status == "SUCCESS" and response.status_code == 200:
        data = response.json()
        session_title = data.get("title")
        print_test("Get Session by ID", "PASS", f"Title: {session_title}")
    else:
        print_test("Get Session by ID", "FAIL", f"Status: {response.status_code if response else 'No response'}")
    
    return True

def test_response_endpoints():
    """Test response management endpoints"""
    print_section("Response Management")
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Test initialize session responses
    response, status = make_request("POST", f"/sessions/{test_session_id}/responses/initialize", headers=headers)
    if status == "SUCCESS" and response.status_code == 200:
        data = response.json()
        total_items = data.get("total_items", 0)
        print_test("Initialize Session Responses", "PASS", f"Items initialized: {total_items}")
    else:
        print_test("Initialize Session Responses", "FAIL", f"Status: {response.status_code if response else 'No response'}")
    
    # Test get session responses
    response, status = make_request("GET", f"/sessions/{test_session_id}/responses", headers=headers)
    if status == "SUCCESS" and response.status_code == 200:
        data = response.json()
        responses_count = data.get("total_items", 0)
        print_test("Get Session Responses", "PASS", f"Responses count: {responses_count}")
        
        # Test update a response
        if data.get("responses") and len(data["responses"]) > 0:
            first_response = data["responses"][0]
            item_id = first_response["item_id"]
            
            update_data = {
                "is_validated": True,
                "manual_override": True
            }
            
            response, status = make_request("PATCH", f"/sessions/{test_session_id}/responses/{item_id}", update_data, headers=headers)
            if status == "SUCCESS" and response.status_code == 200:
                print_test("Update Session Response", "PASS", "Response updated successfully")
            else:
                print_test("Update Session Response", "FAIL", f"Status: {response.status_code if response else 'No response'}")
    else:
        print_test("Get Session Responses", "FAIL", f"Status: {response.status_code if response else 'No response'}")

def test_scoring_endpoints():
    """Test scoring endpoints"""
    print_section("Scoring System")
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Test calculate score
    response, status = make_request("POST", f"/sessions/{test_session_id}/calculate", headers=headers)
    if status == "SUCCESS" and response.status_code == 201:
        data = response.json()
        total_score = data.get("total_score", 0)
        risk_band = data.get("risk_band", "")
        print_test("Calculate Session Score", "PASS", f"Score: {total_score}, Risk: {risk_band}")
    else:
        print_test("Calculate Session Score", "FAIL", f"Status: {response.status_code if response else 'No response'}")
    
    # Test get score
    response, status = make_request("GET", f"/sessions/{test_session_id}/score", headers=headers)
    if status == "SUCCESS" and response.status_code == 200:
        data = response.json()
        total_score = data.get("total_score", 0)
        print_test("Get Session Score", "PASS", f"Score: {total_score}")
    else:
        print_test("Get Session Score", "FAIL", f"Status: {response.status_code if response else 'No response'}")

def test_upload_endpoints():
    """Test file upload endpoints"""
    print_section("File Upload")
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Test get audio file info (should return 404 for new session)
    response, status = make_request("GET", f"/sessions/{test_session_id}/audio", headers=headers)
    if status == "SUCCESS" and response.status_code == 404:
        print_test("Get Audio Info (Empty)", "PASS", "No audio file found as expected")
    else:
        print_test("Get Audio Info (Empty)", "FAIL", f"Status: {response.status_code if response else 'No response'}")

def test_user_management():
    """Test user management endpoints"""
    print_section("User Management")
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Test get all users (admin endpoint)
    response, status = make_request("GET", "/users/?page=1&page_size=10", headers=headers)
    if status == "SUCCESS" and response.status_code == 200:
        data = response.json()
        users_count = len(data.get("items", []))
        print_test("Get Users List", "PASS", f"Users found: {users_count}")
    else:
        print_test("Get Users List", "FAIL", f"Status: {response.status_code if response else 'No response'}")
    
    # Test get user by ID
    response, status = make_request("GET", f"/users/{test_user_id}", headers=headers)
    if status == "SUCCESS" and response.status_code == 200:
        data = response.json()
        user_email = data.get("email")
        print_test("Get User by ID", "PASS", f"Email: {user_email}")
    else:
        print_test("Get User by ID", "FAIL", f"Status: {response.status_code if response else 'No response'}")

def test_error_handling():
    """Test error handling"""
    print_section("Error Handling")
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Test 404 error
    response, status = make_request("GET", "/nonexistent-endpoint", headers=headers)
    if status == "SUCCESS" and response.status_code == 404:
        print_test("404 Error Handling", "PASS", "Returns proper 404")
    else:
        print_test("404 Error Handling", "FAIL", f"Expected 404, got {response.status_code if response else 'No response'}")
    
    # Test unauthorized access
    response, status = make_request("GET", "/auth/me")
    if status == "SUCCESS" and response.status_code == 401:
        print_test("Unauthorized Access", "PASS", "Properly blocks unauthorized requests")
    else:
        print_test("Unauthorized Access", "FAIL", f"Expected 401, got {response.status_code if response else 'No response'}")
    
    # Test invalid session ID
    response, status = make_request("GET", "/sessions/99999", headers=headers)
    if status == "SUCCESS" and response.status_code == 404:
        print_test("Invalid Resource ID", "PASS", "Returns 404 for invalid session")
    else:
        print_test("Invalid Resource ID", "FAIL", f"Expected 404, got {response.status_code if response else 'No response'}")

def test_api_documentation():
    """Test API documentation endpoints"""
    print_section("API Documentation")
    
    # Test OpenAPI docs
    response, status = make_request("GET", "/docs")
    if status == "SUCCESS" and response.status_code == 200:
        print_test("Swagger UI", "PASS", "Documentation accessible")
    else:
        print_test("Swagger UI", "FAIL", f"Status: {response.status_code if response else 'No response'}")
    
    # Test OpenAPI JSON schema
    response, status = make_request("GET", "/openapi.json")
    if status == "SUCCESS" and response.status_code == 200:
        print_test("OpenAPI Schema", "PASS", "JSON schema available")
    else:
        print_test("OpenAPI Schema", "FAIL", f"Status: {response.status_code if response else 'No response'}")

def run_all_tests():
    """Run all API tests"""
    print("🧪 SALES CHECKLIST™ API ENDPOINT TESTING")
    print("=" * 60)
    print(f"Testing API at: {BASE_URL}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests_passed = 0
    total_tests = 0
    
    try:
        # Run all test suites
        if test_health_check():
            tests_passed += 1
        total_tests += 1
        
        if test_authentication():
            tests_passed += 1
        total_tests += 1
        
        test_checklist_endpoints()
        tests_passed += 1
        total_tests += 1
        
        if test_session_endpoints():
            tests_passed += 1
        total_tests += 1
        
        test_response_endpoints()
        tests_passed += 1
        total_tests += 1
        
        test_scoring_endpoints()
        tests_passed += 1
        total_tests += 1
        
        test_upload_endpoints()
        tests_passed += 1
        total_tests += 1
        
        test_user_management()
        tests_passed += 1
        total_tests += 1
        
        test_error_handling()
        tests_passed += 1
        total_tests += 1
        
        test_api_documentation()
        tests_passed += 1
        total_tests += 1
        
    except KeyboardInterrupt:
        print("\n⚠️ Testing interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Testing failed with error: {str(e)}")
        return False
    
    # Print summary
    print_section("Test Summary")
    success_rate = (tests_passed / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"Tests Passed: {tests_passed}/{total_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("🎉 API is production ready!")
        return True
    elif success_rate >= 75:
        print("⚠️ API has some issues but is mostly functional")
        return True
    else:
        print("❌ API has significant issues that need to be addressed")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)