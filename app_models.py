# app_models.py

# Import UserMixin from Flask-Login for standard user model properties
from flask_login import UserMixin
# Import password hashing utilities from Werkzeug
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin):
    """
    Represents a user in the application.
    Inherits from UserMixin to provide default implementations for Flask-Login
    (is_authenticated, is_active, is_anonymous, get_id).
    """
    def __init__(self, id, username, password_hash):
        """
        Initializes a User object. Usually called after fetching data from the DB.

        Args:
            id: The unique identifier for the user (typically from the database).
            username: The user's chosen username.
            password_hash: The securely hashed password for the user (already hashed).
        """
        self.id = id
        self.username = username
        self.password_hash = password_hash
        # Add other user attributes here if needed (e.g., email, registration_date)

    def set_password(self, password):
        """
        Generates a secure hash for the given plain-text password and stores it
        on this User instance's password_hash attribute.
        Call this *before* saving a new user or updating a password.

        Args:
            password: The plain-text password to hash.
        """
        # Uses Werkzeug's generate_password_hash for strong hashing with salt.
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """
        Checks if the provided plain-text password matches the stored hash.
        Uses Werkzeug's check_password_hash for secure comparison.

        Args:
            password: The plain-text password submitted by the user during login.

        Returns:
            True if the password matches the stored hash, False otherwise.
        """
        # Compares the provided password against the stored hash securely.
        return check_password_hash(self.password_hash, password)

    # Flask-Login requires the get_id method.
    # UserMixin provides a default implementation that returns self.id.
    # You usually don't need to override it unless your ID column is named differently.
    # def get_id(self):
    #     return str(self.id) # Ensure it returns a string if needed

    # You might add other methods here later, e.g., methods to fetch
    # or update user progress data from the 'user_progress' table.

    def __repr__(self):
        """
        Provides a developer-friendly string representation of the User object,
        useful for debugging.
        """
        return f'<User {self.username} (ID: {self.id})>'

# Note: Functions to load/save users from/to the database (like the commented-out
# example in the previous version) should typically reside in your main app.py
# or a dedicated data access layer, not directly within the model file itself.
# This keeps the model focused on representing the data structure.

