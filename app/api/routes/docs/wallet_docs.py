"""
Wallet operation endpoint documentation.

Contains OpenAPI response examples and metadata for wallet-related endpoints.
Used in FastAPI route definitions for Swagger/OpenAPI documentation.
"""

# DEPOSIT FUNDS ENDPOINT DOCS
deposit_funds_responses = {
    200: {
        "description": "Deposit Initialized Successfully",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "Paystack Payment URL Generated",
                        "value": {
                            "status": "success",
                            "message": "Deposit initialized successfully",
                            "status_code": 200,
                            "data": {
                                "reference": "DEP_1234567890_abc123",
                                "authorization_url": "https://checkout.paystack.com/0iaufh75282...",
                                "amount": "5000.00",
                            },
                        },
                    }
                }
            }
        },
    },
    400: {
        "description": "Bad Request - Invalid Amount or Service Error",
        "content": {
            "application/json": {
                "examples": {
                    "paystack_error": {
                        "summary": "Paystack API Error",
                        "value": {
                            "status": "failure",
                            "message": "Failed to initialize deposit",
                            "status_code": 400,
                            "error_code": "PAYSTACK_ERROR",
                            "errors": {"detail": ["Paystack service unavailable"]},
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
    403: {
        "description": "Forbidden - Missing Permission",
        "content": {
            "application/json": {
                "examples": {
                    "insufficient_permission": {
                        "summary": "API Key Missing 'deposit' Permission",
                        "value": {
                            "status": "failure",
                            "message": "Insufficient permissions for this operation",
                            "status_code": 403,
                            "error_code": "INSUFFICIENT_PERMISSION",
                            "errors": {},
                        },
                    }
                }
            }
        },
    },
    404: {
        "description": "Not Found - Wallet Not Found",
        "content": {
            "application/json": {
                "examples": {
                    "wallet_not_found": {
                        "summary": "Wallet Not Found",
                        "value": {
                            "status": "failure",
                            "message": "Wallet not found",
                            "status_code": 404,
                            "error_code": "WALLET_NOT_FOUND",
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
                        "summary": "Invalid Amount",
                        "value": {
                            "status": "failure",
                            "message": "Validation failed",
                            "status_code": 422,
                            "error_code": "VALIDATION_ERROR",
                            "errors": {
                                "amount": ["Amount must be greater than 0"],
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

deposit_funds_custom_errors = ["400", "401", "403", "404", "422", "500"]
deposit_funds_custom_success = {
    "status_code": 200,
    "description": "Deposit initialized. User completes payment on Paystack.",
}

# PAYSTACK WEBHOOK ENDPOINT DOCS
paystack_webhook_responses = {
    200: {
        "description": "Webhook Processed Successfully",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "Webhook Accepted",
                        "value": {
                            "status": "success",
                            "message": "Webhook processed successfully",
                            "status_code": 200,
                            "data": {},
                        },
                    }
                }
            }
        },
    },
    400: {
        "description": "Bad Request - Invalid Signature",
        "content": {
            "application/json": {
                "examples": {
                    "invalid_signature": {
                        "summary": "Webhook Signature Verification Failed",
                        "value": {
                            "status": "failure",
                            "message": "Invalid webhook signature",
                            "status_code": 400,
                            "error_code": "INVALID_SIGNATURE",
                            "errors": {},
                        },
                    }
                }
            }
        },
    },
}

paystack_webhook_custom_errors = ["400"]
paystack_webhook_custom_success = {
    "status_code": 200,
    "description": "Webhook processed (deposits are credited via webhook only).",
}

# GET DEPOSIT STATUS ENDPOINT DOCS
check_deposit_status_responses = {
    200: {
        "description": "Deposit Status Retrieved Successfully",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "Deposit Status",
                        "value": {
                            "status": "success",
                            "message": "Transaction status retrieved",
                            "status_code": 200,
                            "data": {
                                "reference": "DEP_1234567890_abc123",
                                "status": "success",
                                "amount": "5000.00",
                                "created_at": "2025-01-09T12:00:00Z",
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
    403: {
        "description": "Forbidden - Missing Permission",
        "content": {
            "application/json": {
                "examples": {
                    "insufficient_permission": {
                        "summary": "API Key Missing 'read' Permission",
                        "value": {
                            "status": "failure",
                            "message": "Insufficient permissions for this operation",
                            "status_code": 403,
                            "error_code": "INSUFFICIENT_PERMISSION",
                            "errors": {},
                        },
                    }
                }
            }
        },
    },
    404: {
        "description": "Not Found - Transaction Not Found",
        "content": {
            "application/json": {
                "examples": {
                    "transaction_not_found": {
                        "summary": "Transaction Not Found",
                        "value": {
                            "status": "failure",
                            "message": "Transaction not found",
                            "status_code": 404,
                            "error_code": "TRANSACTION_NOT_FOUND",
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

check_deposit_status_custom_errors = ["401", "403", "404", "500"]
check_deposit_status_custom_success = {
    "status_code": 200,
    "description": "Deposit status retrieved (for manual verification only).",
}

# GET WALLET BALANCE ENDPOINT DOCS
get_wallet_balance_responses = {
    200: {
        "description": "Wallet Balance Retrieved Successfully",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "Wallet Balance",
                        "value": {
                            "status": "success",
                            "message": "Wallet balance retrieved",
                            "status_code": 200,
                            "data": {
                                "balance": "15000.00",
                                "wallet_number": "1234567890123",
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
    403: {
        "description": "Forbidden - Missing Permission",
        "content": {
            "application/json": {
                "examples": {
                    "insufficient_permission": {
                        "summary": "API Key Missing 'read' Permission",
                        "value": {
                            "status": "failure",
                            "message": "Insufficient permissions for this operation",
                            "status_code": 403,
                            "error_code": "INSUFFICIENT_PERMISSION",
                            "errors": {},
                        },
                    }
                }
            }
        },
    },
    404: {
        "description": "Not Found - Wallet Not Found",
        "content": {
            "application/json": {
                "examples": {
                    "wallet_not_found": {
                        "summary": "Wallet Not Found",
                        "value": {
                            "status": "failure",
                            "message": "Wallet not found",
                            "status_code": 404,
                            "error_code": "WALLET_NOT_FOUND",
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

get_wallet_balance_custom_errors = ["401", "403", "404", "500"]
get_wallet_balance_custom_success = {
    "status_code": 200,
    "description": "Current wallet balance and wallet number retrieved.",
}

# TRANSFER FUNDS ENDPOINT DOCS
transfer_funds_responses = {
    200: {
        "description": "Transfer Completed Successfully",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "Transfer Successful",
                        "value": {
                            "status": "success",
                            "message": "Transfer completed successfully",
                            "status_code": 200,
                            "data": {
                                "status": "success",
                                "message": "Transfer completed successfully",
                                "reference": "TRF_1234567890_xyz",
                                "amount": "3000.00",
                                "recipient_wallet": "9876543210123",
                            },
                        },
                    }
                }
            }
        },
    },
    400: {
        "description": "Bad Request - Invalid Transfer",
        "content": {
            "application/json": {
                "examples": {
                    "insufficient_balance": {
                        "summary": "Insufficient Balance",
                        "value": {
                            "status": "failure",
                            "message": "Insufficient balance for transfer",
                            "status_code": 400,
                            "error_code": "TRANSFER_ERROR",
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
    403: {
        "description": "Forbidden - Missing Permission",
        "content": {
            "application/json": {
                "examples": {
                    "insufficient_permission": {
                        "summary": "API Key Missing 'transfer' Permission",
                        "value": {
                            "status": "failure",
                            "message": "Insufficient permissions for this operation",
                            "status_code": 403,
                            "error_code": "INSUFFICIENT_PERMISSION",
                            "errors": {},
                        },
                    }
                }
            }
        },
    },
    404: {
        "description": "Not Found - Wallet Not Found",
        "content": {
            "application/json": {
                "examples": {
                    "wallet_not_found": {
                        "summary": "Wallet Not Found",
                        "value": {
                            "status": "failure",
                            "message": "Wallet not found",
                            "status_code": 404,
                            "error_code": "WALLET_NOT_FOUND",
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
                        "summary": "Invalid Transfer Details",
                        "value": {
                            "status": "failure",
                            "message": "Validation failed",
                            "status_code": 422,
                            "error_code": "VALIDATION_ERROR",
                            "errors": {
                                "wallet_number": ["Field required"],
                                "amount": ["Amount must be greater than 0"],
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

transfer_funds_custom_errors = ["400", "401", "403", "404", "422", "500"]
transfer_funds_custom_success = {
    "status_code": 200,
    "description": "Transfer completed successfully (atomic operation).",
}

# GET TRANSACTION HISTORY ENDPOINT DOCS
get_transaction_history_responses = {
    200: {
        "description": "Transaction History Retrieved Successfully",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "Transaction History",
                        "value": {
                            "status": "success",
                            "message": "Transaction history retrieved",
                            "status_code": 200,
                            "data": {
                                "transactions": [
                                    {
                                        "id": 1,
                                        "type": "deposit",
                                        "amount": "5000.00",
                                        "status": "success",
                                        "reference": "DEP_123",
                                        "extra_data": {},
                                        "created_at": "2025-01-09T12:00:00Z",
                                    },
                                    {
                                        "id": 2,
                                        "type": "transfer_out",
                                        "amount": "1000.00",
                                        "status": "success",
                                        "reference": "TRF_456",
                                        "extra_data": {},
                                        "created_at": "2025-01-08T15:30:00Z",
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
    403: {
        "description": "Forbidden - Missing Permission",
        "content": {
            "application/json": {
                "examples": {
                    "insufficient_permission": {
                        "summary": "API Key Missing 'read' Permission",
                        "value": {
                            "status": "failure",
                            "message": "Insufficient permissions for this operation",
                            "status_code": 403,
                            "error_code": "INSUFFICIENT_PERMISSION",
                            "errors": {},
                        },
                    }
                }
            }
        },
    },
    404: {
        "description": "Not Found - Wallet Not Found",
        "content": {
            "application/json": {
                "examples": {
                    "wallet_not_found": {
                        "summary": "Wallet Not Found",
                        "value": {
                            "status": "failure",
                            "message": "Wallet not found",
                            "status_code": 404,
                            "error_code": "WALLET_NOT_FOUND",
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

get_transaction_history_custom_errors = ["401", "403", "404", "500"]
get_transaction_history_custom_success = {
    "status_code": 200,
    "description": "Transaction history retrieved (limited to 50 most recent).",
}

# RECOVER TRANSFER ENDPOINT DOCS
recover_transfer_responses = {
    200: {
        "description": "Transfer Recovery Completed",
        "content": {
            "application/json": {
                "examples": {
                    "recovery_performed": {
                        "summary": "Transfer Recovered Successfully",
                        "value": {
                            "status": "success",
                            "message": "Transfer recovered successfully",
                            "status_code": 200,
                            "data": {
                                "recovered": True,
                                "reference": "TRF_123_abc",
                            },
                        },
                    },
                    "no_recovery_needed": {
                        "summary": "No Recovery Needed",
                        "value": {
                            "status": "success",
                            "message": "Transfer was already completed successfully",
                            "status_code": 200,
                            "data": {
                                "recovered": False,
                                "reference": "TRF_123_abc",
                            },
                        },
                    }
                }
            }
        },
    },
    400: {
        "description": "Bad Request - Invalid Reference or Recovery Failed",
        "content": {
            "application/json": {
                "examples": {
                    "invalid_reference": {
                        "summary": "Transfer Reference Not Found",
                        "value": {
                            "status": "failure",
                            "message": "Transfer reference not found or not in recoverable state",
                            "status_code": 400,
                            "error_code": "INVALID_REFERENCE",
                            "errors": {},
                        },
                    },
                    "recovery_failed": {
                        "summary": "Recovery Operation Failed",
                        "value": {
                            "status": "failure",
                            "message": "Recovery failed: database error",
                            "status_code": 400,
                            "error_code": "RECOVERY_ERROR",
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
    403: {
        "description": "Forbidden - Missing Permission",
        "content": {
            "application/json": {
                "examples": {
                    "insufficient_permission": {
                        "summary": "API Key Missing 'transfer' Permission",
                        "value": {
                            "status": "failure",
                            "message": "Insufficient permissions for this operation",
                            "status_code": 403,
                            "error_code": "INSUFFICIENT_PERMISSION",
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

recover_transfer_custom_errors = ["400", "401", "403", "500"]
recover_transfer_custom_success = {
    "status_code": 200,
    "description": "Transfer recovery attempted. Check 'recovered' field for result.",
}
