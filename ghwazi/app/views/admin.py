"""
Admin views for the Flask application.
"""

import logging

from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)

from .models import Category, CategoryMapping, EmailConfiguration
from .models.database import Database
from .models.transaction import TransactionRepository
from .models.user import User
from .utils.decorators import login_required

# Create blueprint
admin_bp = Blueprint("admin", __name__)

# Initialize database and logger
db = Database()
logger = logging.getLogger(__name__)
