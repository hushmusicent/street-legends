# Test Credentials for Street Legends

## Test Account for Fitness/Mission Sync Testing
- Username: testfitness123
- Password: testpass123
- Player ID: b58ba7af-d3af-4524-b4d1-365cbafc7107
- Vehicle equipped: Beat-up Bike (durability tested)

## Testing Password Reset Flow
To test the password reset flow:
1. Create a new account with an email address
2. Use the "Forgot Password?" feature on the login screen
3. A reset code will be sent to the registered email

## API Endpoints
- POST /api/auth/forgot-password - Request password reset
  - Body: `{"email_or_username": "test@example.com"}`
- POST /api/auth/reset-password - Reset password with token
  - Body: `{"token": "RESET_CODE", "new_password": "newpassword"}`
- POST /api/auth/change-password/{player_id} - Change password (logged in)
  - Body: `{"current_password": "oldpass", "new_password": "newpass"}`

## Notes
- Email field is optional during registration but required for password reset
- Reset codes are 8 characters (shown in email as uppercase)
- Reset codes expire after 1 hour
