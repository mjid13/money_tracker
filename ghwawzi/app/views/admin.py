"""
Admin views for the Flask application.
"""
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models.database import Database
from app.models.transaction import TransactionRepository
from app.models.user import User
from app.models import Category, CategoryMapping, EmailConfiguration
from app.utils.decorators import login_required

# Create blueprint
admin_bp = Blueprint('admin', __name__)

# Initialize database and logger
db = Database()
logger = logging.getLogger(__name__)



@admin_bp.route('/email-configs')
@login_required
def email_configs():
    """Display email configurations."""
    user_id = session.get('user_id')
    db_session = db.get_session()

    try:
        configs = db_session.query(EmailConfiguration).filter(
            EmailConfiguration.user_id == user_id
        ).all()
        return render_template('admin/email_configs.html', configs=configs)

    except Exception as e:
        logger.error(f"Error loading email configs: {str(e)}")
        flash('Error loading email configurations', 'error')
        return render_template('admin/email_configs.html', configs=[])
    finally:
        db.close_session(db_session)


@admin_bp.route('/email-configs/add', methods=['GET', 'POST'])
@login_required
def add_email_config():
    """Add a new email configuration."""
    if request.method == 'POST':
        user_id = session.get('user_id')
        
        # Get form data
        email = request.form.get('email')
        password = request.form.get('password')
        imap_server = request.form.get('imap_server')
        imap_port = request.form.get('imap_port', 993)
        
        if not all([email, password, imap_server]):
            flash('All fields are required', 'error')
            return render_template('admin/add_email_config.html')

        db_session = db.get_session()
        try:
            config = EmailConfiguration(
                email=email,
                password=password,  # Should be encrypted in production
                imap_server=imap_server,
                imap_port=int(imap_port),
                user_id=user_id
            )
            db_session.add(config)
            db_session.commit()
            
            flash('Email configuration added successfully', 'success')
            return redirect(url_for('admin.email_configs'))

        except Exception as e:
            logger.error(f"Error adding email config: {str(e)}")
            flash('Error adding email configuration', 'error')
            return render_template('admin/add_email_config.html')
        finally:
            db.close_session(db_session)

    return render_template('admin/add_email_config.html')