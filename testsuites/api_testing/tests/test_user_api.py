"""
================================================================================
User API Test Suite
================================================================================

Comprehensive tests for User Management API endpoints.

Test Categories:
    - CRUD Operations: Create, Read, Update, Delete
    - Business Rules: Validation, permissions, constraints
    - Error Handling: Invalid inputs, edge cases

Author: Automation Team
License: MIT
================================================================================
"""

from __future__ import annotations

from typing import Any, Dict

import allure
import pytest

from ..framework import HttpClient


@allure.epic("User Management API")
@allure.feature("User CRUD Operations")
class TestUserAPI:
    """
    User API endpoint tests.
    
    Covers:
        - User creation and validation
        - User retrieval (single and list)
        - User updates (full and partial)
        - User deletion and soft-delete
    """

    @pytest.mark.P0
    @pytest.mark.smoke
    @allure.story("Create User")
    @allure.title("Create user with valid data - Success")
    def test_create_user_success(
        self,
        http_client: HttpClient,
        test_user_data: Dict[str, Any],
        cleanup_users: list,
    ):
        """
        Verify user creation with valid data succeeds.
        
        Steps:
            1. Send POST request with valid user data
            2. Verify 201 status code
            3. Verify response contains user_id
            4. Verify user can be retrieved
        """
        with allure.step("Create new user"):
            response = http_client.post(
                "/api/v1/users",
                json=test_user_data
            )
        
        with allure.step("Verify success response"):
            assert response.status_code == 201, (
                f"Expected 201, got {response.status_code}"
            )
            
            data = response.json()
            assert "user_id" in data, "Response should contain user_id"
            
            user_id = data["user_id"]
            cleanup_users.append(user_id)
        
        with allure.step("Verify user exists in database"):
            get_response = http_client.get(f"/api/v1/users/{user_id}")
            assert get_response.status_code == 200
            
            user = get_response.json()
            assert user["username"] == test_user_data["username"]
            assert user["email"] == test_user_data["email"]

    @pytest.mark.P0
    @allure.story("Create User")
    @allure.title("Create user with duplicate email - Conflict")
    def test_create_user_duplicate_email(
        self,
        http_client: HttpClient,
        test_user_data: Dict[str, Any],
        cleanup_users: list,
    ):
        """
        Verify duplicate email returns 409 Conflict.
        
        Steps:
            1. Create first user
            2. Attempt to create second user with same email
            3. Verify 409 status code
        """
        with allure.step("Create first user"):
            response = http_client.post(
                "/api/v1/users",
                json=test_user_data
            )
            assert response.status_code == 201
            cleanup_users.append(response.json()["user_id"])
        
        with allure.step("Attempt to create duplicate"):
            # Modify username but keep same email
            duplicate_data = test_user_data.copy()
            duplicate_data["username"] = f"different_{test_user_data['username']}"
            
            response = http_client.post(
                "/api/v1/users",
                json=duplicate_data
            )
        
        with allure.step("Verify conflict response"):
            assert response.status_code == 409, (
                f"Expected 409 Conflict, got {response.status_code}"
            )

    @pytest.mark.P1
    @allure.story("Get User")
    @allure.title("Get existing user by ID - Success")
    def test_get_user_by_id(
        self,
        http_client: HttpClient,
        test_user_data: Dict[str, Any],
        cleanup_users: list,
    ):
        """
        Verify user retrieval by ID returns correct data.
        """
        # Setup: Create user
        create_response = http_client.post(
            "/api/v1/users",
            json=test_user_data
        )
        user_id = create_response.json()["user_id"]
        cleanup_users.append(user_id)
        
        with allure.step("Retrieve user by ID"):
            response = http_client.get(f"/api/v1/users/{user_id}")
        
        with allure.step("Verify response data"):
            assert response.status_code == 200
            
            user = response.json()
            assert user["user_id"] == user_id
            assert user["username"] == test_user_data["username"]
            assert user["email"] == test_user_data["email"]
            assert "created_at" in user

    @pytest.mark.P1
    @allure.story("Get User")
    @allure.title("Get non-existent user - Not Found")
    def test_get_user_not_found(self, http_client: HttpClient):
        """
        Verify request for non-existent user returns 404.
        """
        with allure.step("Request non-existent user"):
            response = http_client.get("/api/v1/users/non_existent_id_12345")
        
        with allure.step("Verify 404 response"):
            assert response.status_code == 404

    @pytest.mark.P1
    @allure.story("Update User")
    @allure.title("Update user display name - Success")
    def test_update_user_display_name(
        self,
        http_client: HttpClient,
        test_user_data: Dict[str, Any],
        cleanup_users: list,
    ):
        """
        Verify user display name can be updated.
        """
        # Setup: Create user
        create_response = http_client.post(
            "/api/v1/users",
            json=test_user_data
        )
        user_id = create_response.json()["user_id"]
        cleanup_users.append(user_id)
        
        new_display_name = "Updated Display Name"
        
        with allure.step("Update display name"):
            response = http_client.patch(
                f"/api/v1/users/{user_id}",
                json={"display_name": new_display_name}
            )
        
        with allure.step("Verify update success"):
            assert response.status_code == 200
            
            updated_user = response.json()
            assert updated_user["display_name"] == new_display_name
        
        with allure.step("Verify persistence"):
            get_response = http_client.get(f"/api/v1/users/{user_id}")
            assert get_response.json()["display_name"] == new_display_name

    @pytest.mark.P1
    @allure.story("Delete User")
    @allure.title("Delete existing user - Success")
    def test_delete_user(
        self,
        http_client: HttpClient,
        test_user_data: Dict[str, Any],
    ):
        """
        Verify user deletion succeeds and user is no longer accessible.
        """
        # Setup: Create user
        create_response = http_client.post(
            "/api/v1/users",
            json=test_user_data
        )
        user_id = create_response.json()["user_id"]
        
        with allure.step("Delete user"):
            response = http_client.delete(f"/api/v1/users/{user_id}")
        
        with allure.step("Verify deletion success"):
            assert response.status_code in (200, 204)
        
        with allure.step("Verify user no longer exists"):
            get_response = http_client.get(f"/api/v1/users/{user_id}")
            assert get_response.status_code == 404

    @pytest.mark.P2
    @allure.story("List Users")
    @allure.title("List users with pagination - Success")
    def test_list_users_pagination(
        self,
        http_client: HttpClient,
        unique_id: str,
        cleanup_users: list,
    ):
        """
        Verify user list pagination works correctly.
        """
        # Setup: Create multiple users
        created_count = 5
        for i in range(created_count):
            user_data = {
                "username": f"user_{unique_id}_{i}",
                "email": f"{unique_id}_{i}@test.example.com",
                "display_name": f"Test User {i}",
            }
            response = http_client.post("/api/v1/users", json=user_data)
            if response.status_code == 201:
                cleanup_users.append(response.json()["user_id"])
        
        with allure.step("Request first page"):
            response = http_client.get(
                "/api/v1/users",
                params={"page_size": 2, "page": 1}
            )
        
        with allure.step("Verify pagination response"):
            assert response.status_code == 200
            
            data = response.json()
            assert "users" in data
            assert len(data["users"]) <= 2  # Respects page_size


@allure.epic("User Management API")
@allure.feature("User Validation")
class TestUserValidation:
    """
    User input validation tests.
    
    Covers parameter validation and business rule enforcement.
    """

    @pytest.mark.P1
    @pytest.mark.mutation
    @allure.story("Input Validation")
    @allure.title("Create user with invalid email - Bad Request")
    def test_create_user_invalid_email(
        self,
        http_client: HttpClient,
        test_user_data: Dict[str, Any],
    ):
        """
        Verify invalid email format is rejected.
        """
        test_user_data["email"] = "invalid-email-format"
        
        with allure.step("Attempt creation with invalid email"):
            response = http_client.post(
                "/api/v1/users",
                json=test_user_data
            )
        
        with allure.step("Verify rejection"):
            assert response.status_code == 400

    @pytest.mark.P1
    @pytest.mark.mutation
    @allure.story("Input Validation")
    @allure.title("Create user with missing required field - Bad Request")
    def test_create_user_missing_username(
        self,
        http_client: HttpClient,
        test_user_data: Dict[str, Any],
    ):
        """
        Verify missing required field is rejected.
        """
        del test_user_data["username"]
        
        with allure.step("Attempt creation without username"):
            response = http_client.post(
                "/api/v1/users",
                json=test_user_data
            )
        
        with allure.step("Verify rejection"):
            assert response.status_code == 400
            
            error = response.json()
            assert "username" in str(error).lower() or "required" in str(error).lower()

