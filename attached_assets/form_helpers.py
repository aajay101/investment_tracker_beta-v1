"""
Helper functions for handling form validation in the application.
"""
from flask import flash

def format_form_errors(form, errors_dict):
    """
    Format and flash form validation errors in a consistent way.
    
    Args:
        form: The form containing the errors
        errors_dict: Dictionary of field errors from form.errors
    """
    for field, errors in errors_dict.items():
        # Safely determine field label without dynamic attribute access
        field_label = get_field_label(field)
        
        # Flash each error with the appropriate field label
        for error in errors:
            flash(f"{field_label}: {error}", "danger")

def get_field_label(field_name):
    """
    Get a user-friendly label for a form field without relying on dynamic attribute access.
    
    Args:
        field_name: The name of the form field
        
    Returns:
        str: A user-friendly label for the field
    """
    field_labels = {
        # User form fields
        'username': 'Username',
        'email': 'Email',
        'password': 'Password',
        'confirm_password': 'Confirm Password',
        
        # Portfolio form fields
        'symbol': 'Stock Symbol',
        'quantity': 'Quantity',
        'buy_price': 'Buy Price',
        'exchange': 'Exchange',
        
        # Watchlist form fields
        'notes': 'Notes',
        
        # Report form fields
        'report_type': 'Report Type'
    }
    
    # Return the mapped label or capitalize the field name if no mapping exists
    if field_name in field_labels:
        return field_labels[field_name]
    else:
        # Safe handling of None
        return "Field" if field_name is None else field_name.capitalize()