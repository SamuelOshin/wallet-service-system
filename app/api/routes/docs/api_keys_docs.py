"""
API Key endpoint documentation.

Contains OpenAPI response examples and metadata for API key management endpoints.
Used in FastAPI route definitions for Swagger/OpenAPI documentation.
"""

# CREATE API KEY ENDPOINT DOCS
create_api_key_responses = {
    201: {
        "description": "API Key Created Successfully",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "API Key Generated",
                        "value": {
                            "status": "success",
                            "message": "API key created successfully",
                            "status_code": 201,
                            "data": {
                                "api_key": "sk_live_abc123xyz789...",
                                "name": "trading-bot",
                                "permissions": ["read", "deposit"],
                                "expires_at": "2025-02-09T12:00:00Z",
                                "created_at": "2025-01-09T12:00:00Z",
                            },
                        },
                    }
                }
            }
        },
    },
    400: {
        "description": "Bad Request - Invalid Request or Max Keys Reached",
        "content": {
            "application/json": {
                "examples": {
                    "max_keys_reached": {
                        "summary": "Maximum API Keys Limit Exceeded",
                        "value": {
                            "status": "failure",
                            "message": "Maximum number of API keys (5) reached",
                            "status_code": 400,
                            "error_code": "API_KEY_LIMIT_EXCEEDED",
                            "errors": {},
                        },
                    },
                    "invalid_expiry": {
                        "summary": "Invalid Expiry Format",
                        "value": {
                            "status": "failure",
                            "message": "Invalid expiry format. Use: 1D, 1W, 1M, 3M, 6M, 1Y",
                            "status_code": 400,
                            "error_code": "API_KEY_CREATION_ERROR",
                            "errors": {},
                        },
                    },
                }
            }
        },
    },
    401: {
        "description": "Unauthorized - Authentication Required",
        "content": {
            "application/json": {
                "examples": {
                    "unauthorized": {
                        "summary": "User Not Authenticated",
                        "value": {
                            "status": "failure",
                            "message": "Invalid token or expired token",
                            "status_code": 401,
                            "error_code": "INVALID_TOKEN",
                            "errors": {},
                        },
                    }
                }
            }
        },
    },
    422: {
        "description": "Unprocessable Entity - Validation Failed",
        "content": {
            "application/json": {
                "examples": {
                    "validation_error": {
                        "summary": "Request Validation Failed",
                        "value": {
                            "status": "failure",
                            "message": "Validation failed",
                            "status_code": 422,
                            "error_code": "VALIDATION_ERROR",
                            "errors": {
                                "name": ["Field required"],
                                "permissions": ["Field required"],
                            },
                        },
                    }
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

create_api_key_custom_errors = ["400", "401", "422", "500"]
create_api_key_custom_success = {
    "status_code": 201,
    "description": "API key created successfully. Store it securely; it won't be shown again.",
}

# ROLLOVER API KEY ENDPOINT DOCS
rollover_api_key_responses = {
    201: {
        "description": "API Key Rolled Over Successfully",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "API Key Rolled Over",
                        "value": {
                            "status": "success",
                            "message": "API key rolled over successfully",
                            "status_code": 201,
                            "data": {
                                "api_key": "sk_live_xyz789abc123...",
                                "name": "trading-bot",
                                "permissions": ["read", "deposit"],
                                "expires_at": "2025-03-09T12:00:00Z",
                                "created_at": "2025-01-09T13:00:00Z",
                            },
                        },
                    }
                }
            }
        },
    },
    400: {
        "description": "Bad Request - Invalid Key ID or Key Not Expired",
        "content": {
            "application/json": {
                "examples": {
                    "key_not_expired": {
                        "summary": "Key Not Expired Yet",
                        "value": {
                            "status": "failure",
                            "message": "API key is not expired or revoked",
                            "status_code": 400,
                            "error_code": "API_KEY_ROLLOVER_ERROR",
                            "errors": {},
                        },
                    }
                }
            }
        },
    },
    401: {
        "description": "Unauthorized - Authentication Required",
        "content": {
            "application/json": {
                "examples": {
                    "unauthorized": {
                        "summary": "User Not Authenticated",
                        "value": {
                            "status": "failure",
                            "message": "Invalid token or expired token",
                            "status_code": 401,
                            "error_code": "INVALID_TOKEN",
                            "errors": {},
                        },
                    }
                }
            }
        },
    },
    422: {
        "description": "Unprocessable Entity - Validation Failed",
        "content": {
            "application/json": {
                "examples": {
                    "validation_error": {
                        "summary": "Request Validation Failed",
                        "value": {
                            "status": "failure",
                            "message": "Validation failed",
                            "status_code": 422,
                            "error_code": "VALIDATION_ERROR",
                            "errors": {
                                "expired_key_id": ["Field required"],
                                "expiry": ["Field required"],
                            },
                        },
                    }
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

rollover_api_key_custom_errors = ["400", "401", "422", "500"]
rollover_api_key_custom_success = {
    "status_code": 201,
    "description": "API key rolled over with same permissions.",
}

# LIST API KEYS ENDPOINT DOCS
list_api_keys_responses = {
    200: {
        "description": "API Keys Retrieved Successfully",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "API Keys List",
                        "value": {
                            "status": "success",
                            "message": "API keys retrieved successfully",
                            "status_code": 200,
                            "data": {
                                "keys": [
                                    {
                                        "id": 1,
                                        "name": "trading-bot",
                                        "permissions": ["read", "deposit"],
                                        "expires_at": "2025-02-09T12:00:00Z",
                                        "is_revoked": False,
                                        "created_at": "2025-01-09T12:00:00Z",
                                    },
                                    {
                                        "id": 2,
                                        "name": "api-gateway",
                                        "permissions": ["read", "transfer"],
                                        "expires_at": "2025-03-09T12:00:00Z",
                                        "is_revoked": False,
                                        "created_at": "2025-01-08T10:00:00Z",
                                    },
                                ],
                                "total": 2,
                            },
                        },
                    }
                }
            }
        },
    },
    401: {
        "description": "Unauthorized - Authentication Required",
        "content": {
            "application/json": {
                "examples": {
                    "unauthorized": {
                        "summary": "User Not Authenticated",
                        "value": {
                            "status": "failure",
                            "message": "Invalid token or expired token",
                            "status_code": 401,
                            "error_code": "INVALID_TOKEN",
                            "errors": {},
                        },
                    }
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

list_api_keys_custom_errors = ["401", "500"]
list_api_keys_custom_success = {
    "status_code": 200,
    "description": "List of API keys retrieved (does not show actual key values).",
}

# REVOKE API KEY ENDPOINT DOCS
revoke_api_key_responses = {
    200: {
        "description": "API Key Revoked Successfully",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "API Key Revoked",
                        "value": {
                            "status": "success",
                            "message": "API key revoked successfully",
                            "status_code": 200,
                            "data": {},
                        },
                    }
                }
            }
        },
    },
    401: {
        "description": "Unauthorized - Authentication Required",
        "content": {
            "application/json": {
                "examples": {
                    "unauthorized": {
                        "summary": "User Not Authenticated",
                        "value": {
                            "status": "failure",
                            "message": "Invalid token or expired token",
                            "status_code": 401,
                            "error_code": "INVALID_TOKEN",
                            "errors": {},
                        },
                    }
                }
            }
        },
    },
    404: {
        "description": "Not Found - API Key Not Found",
        "content": {
            "application/json": {
                "examples": {
                    "not_found": {
                        "summary": "API Key Not Found",
                        "value": {
                            "status": "failure",
                            "message": "API key not found or unauthorized",
                            "status_code": 404,
                            "error_code": "API_KEY_NOT_FOUND",
                            "errors": {},
                        },
                    }
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

revoke_api_key_custom_errors = ["401", "404", "500"]
revoke_api_key_custom_success = {
    "status_code": 200,
    "description": "API key revoked successfully. Cannot be used for future requests.",
}
