"""
Authentication endpoint documentation.

Contains OpenAPI response examples and metadata for auth-related endpoints.
Used in FastAPI route definitions for Swagger/OpenAPI documentation.
"""

# GOOGLE LOGIN ENDPOINT DOCS
google_login_responses = {
    307: {
        "description": "Redirect to Google Sign-In",
        "headers": {
            "location": {
                "description": "URL to Google OAuth authorization page",
                "schema": {"type": "string"},
            }
        },
    },
}

google_login_custom_success = {
    "status_code": 307,
    "description": "Redirects user to Google OAuth sign-in page.",
}

# GOOGLE CALLBACK ENDPOINT DOCS
google_callback_responses = {
    200: {
        "description": "Authentication Successful",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "User Authenticated",
                        "value": {
                            "status": "success",
                            "message": "Authentication successful",
                            "status_code": 200,
                            "data": {
                                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                                "user": {
                                    "id": 1,
                                    "email": "user@example.com",
                                    "name": "John Doe",
                                    "wallet_number": "1234567890123",
                                },
                            },
                        },
                    }
                }
            }
        },
    },
    400: {
        "description": "Bad Request - Authentication Failed",
        "content": {
            "application/json": {
                "examples": {
                    "invalid_code": {
                        "summary": "Invalid or Expired Authorization Code",
                        "value": {
                            "status": "failure",
                            "message": "Authentication failed",
                            "status_code": 400,
                            "error_code": "GOOGLE_AUTH_ERROR",
                            "errors": {"detail": ["Invalid authorization code"]},
                        },
                    },
                    "token_exchange_failed": {
                        "summary": "Failed to Exchange Code for Token",
                        "value": {
                            "status": "failure",
                            "message": "Failed to obtain access token from Google",
                            "status_code": 400,
                            "error_code": "GOOGLE_AUTH_ERROR",
                            "errors": {},
                        },
                    },
                }
            }
        },
    },
    500: {
        "description": "Internal Server Error",
        "content": {
            "application/json": {
                "examples": {
                    "server_error": {
                        "summary": "Unexpected Error",
                        "value": {
                            "status": "failure",
                            "message": "Internal server error",
                            "status_code": 500,
                            "error_code": "INTERNAL_SERVER_ERROR",
                            "errors": {},
                        },
                    }
                }
            }
        },
    },
}

google_callback_custom_errors = ["400", "500"]
google_callback_custom_success = {
    "status_code": 200,
    "description": "User authenticated successfully with Google OAuth.",
}
