"""
Main views for the Flask application.
"""
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import Database, TransactionRepository, User, Account, EmailConfiguration
from app.utils.decorators import login_required

# Create blueprint
main_bp = Blueprint('main', __name__)

# Initialize database and logger
db = Database()
logger = logging.getLogger(__name__)


@main_bp.route('/')
def index():
    """Home page with landing content."""
    return render_template('index.html', year=datetime.now().year)


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
        return render_template('dashboard.html', 
                             accounts=accounts, 
                             email_configs=email_configs)

    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        flash('Error loading dashboard', 'error')
        return render_template('dashboard.html', accounts=[], email_configs=[])
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


@main_bp.route('/accounts')
@login_required
def accounts():
    """Display user's accounts."""
    user_id = session.get('user_id')
    db_session = db.get_session()

    try:
        accounts = TransactionRepository.get_user_accounts(db_session, user_id)
        return render_template('accounts.html', accounts=accounts)

    except Exception as e:
        logger.error(f"Error loading accounts: {str(e)}")
        flash('Error loading accounts', 'error')
        return render_template('accounts.html', accounts=[])
    finally:
        db.close_session(db_session)


@main_bp.route('/account/<account_number>')
@login_required
def account_details(account_number):
    """Display account details and transactions."""
    user_id = session.get('user_id')
    db_session = db.get_session()

    try:
        # Get account and verify ownership
        account = db_session.query(Account).filter(
            Account.account_number == account_number,
            Account.user_id == user_id
        ).first()

        if not account:
            flash('Account not found or you do not have permission to view it', 'error')
            return redirect(url_for('main.accounts'))

        # Get transactions for this account
        transactions = TransactionRepository.get_account_transactions(
            db_session, account.id, limit=100
        )

        return render_template('account_details.html', 
                             account=account, 
                             transactions=transactions)

    except Exception as e:
        logger.error(f"Error loading account details: {str(e)}")
        flash('Error loading account details', 'error')
        return redirect(url_for('main.accounts'))
    finally:
        db.close_session(db_session)