"""
Main views for the Flask application.
"""
import logging
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from app.models.database import Database
from app.models.transaction import TransactionRepository
from app.models.user import User
from app.models.models import Account, EmailConfiguration
from app.utils.decorators import login_required
from app.services.counterparty_service import CounterpartyService
# Create blueprint
main_bp = Blueprint('main', __name__)

# Initialize database and logger
db = Database()
logger = logging.getLogger(__name__)
counterparty_service = CounterpartyService()

@main_bp.route('/')
def index():
    """Home page with landing content."""
    return render_template('main/index.html', year=datetime.now().year)


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard."""
    user_id = session.get('user_id')
    db_session = db.get_session()

    try:
        # Get user's accounts
        accounts = TransactionRepository.get_user_accounts(db_session, user_id)

        # Get user's email configurations
        email_configs = db_session.query(EmailConfiguration).filter(
            EmailConfiguration.user_id == user_id
        ).all()

        # Simplified dashboard for now - can be enhanced with charts later
        return render_template('main/dashboard.html',
                             accounts=accounts, 
                             email_configs=email_configs)

    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        flash('Error loading dashboard', 'error')
        return render_template('main/dashboard.html', accounts=[], email_configs=[])
    finally:
        db.close_session(db_session)


@main_bp.route('/profile')
@login_required
def profile():
    """User profile page."""
    user_id = session.get('user_id')
    db_session = db.get_session()

    try:
        user = db_session.query(User).filter(User.id == user_id).first()
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('main.dashboard'))

        return render_template('profile.html', user=user)

    except Exception as e:
        logger.error(f"Error loading profile: {str(e)}")
        flash('Error loading profile', 'error')
        return redirect(url_for('main.dashboard'))
    finally:
        db.close_session(db_session)


@main_bp.route('/counterparties')
@login_required
def counterparties():
    """List all unique counterparties."""
    user_id = session.get('user_id')
    account_number = request.args.get('account_number', 'all')
    db_session = db.get_session()

    try:
        # Get user's accounts
        accounts = TransactionRepository.get_user_accounts(db_session, user_id)

        # Get all unique counterparties for this user, filtered by account if specified
        counterparties = counterparty_service.get_unique_counterparties(user_id, account_number)

        # Get all categories for this user (for the categorization form)
        categories = counterparty_service.get_categories(user_id)

        return render_template('counterparties.html',
                               counterparties=counterparties,
                               categories=categories,
                               accounts=accounts,
                               selected_account=account_number)
    except Exception as e:
        logger.error(f"Error loading counterparties: {str(e)}")
        flash('Error loading counterparties. Please try again.', 'error')
        return redirect(url_for('dashboard'))
    finally:
        db.close_session(db_session)

@main_bp.route('/results')
@login_required
def results():
    """Display the parsed transaction data."""
    transaction_data = session.get('transaction_data')
    if not transaction_data:
        flash('No transaction data available', 'error')
        return redirect(url_for('dashboard'))

    return render_template('results.html', transaction=transaction_data)
