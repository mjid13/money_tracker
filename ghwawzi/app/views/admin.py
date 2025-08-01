"""
Admin views for the Flask application.
"""
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import Database, TransactionRepository, Category, CategoryMapping, EmailConfiguration
from app.utils.decorators import login_required

# Create blueprint
admin_bp = Blueprint('admin', __name__)

# Initialize database and logger
db = Database()
logger = logging.getLogger(__name__)


@admin_bp.route('/categories')
@login_required
def categories():
    """Display categories management page."""
    user_id = session.get('user_id')
    db_session = db.get_session()

    try:
        categories = db_session.query(Category).filter(
            Category.user_id == user_id
        ).all()
        return render_template('admin/categories.html', categories=categories)

    except Exception as e:
        logger.error(f"Error loading categories: {str(e)}")
        flash('Error loading categories', 'error')
        return render_template('admin/categories.html', categories=[])
    finally:
        db.close_session(db_session)


@admin_bp.route('/categories/add', methods=['GET', 'POST'])
@login_required
def add_category():
    """Add a new category."""
    if request.method == 'POST':
        user_id = session.get('user_id')
        name = request.form.get('name')
        color = request.form.get('color')
        
        if not name:
            flash('Category name is required', 'error')
            return render_template('admin/add_category.html')

        db_session = db.get_session()
        try:
            category = Category(
                name=name,
                color=color,
                user_id=user_id
            )
            db_session.add(category)
            db_session.commit()
            
            flash('Category added successfully', 'success')
            return redirect(url_for('admin.categories'))

        except Exception as e:
            logger.error(f"Error adding category: {str(e)}")
            flash('Error adding category', 'error')
            return render_template('admin/add_category.html')
        finally:
            db.close_session(db_session)

    return render_template('admin/add_category.html')


@admin_bp.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    """Edit a category."""
    user_id = session.get('user_id')
    db_session = db.get_session()

    try:
        category = db_session.query(Category).filter(
            Category.id == category_id,
            Category.user_id == user_id
        ).first()

        if not category:
            flash('Category not found', 'error')
            return redirect(url_for('admin.categories'))

        if request.method == 'POST':
            category.name = request.form.get('name')
            category.color = request.form.get('color')
            db_session.commit()
            
            flash('Category updated successfully', 'success')
            return redirect(url_for('admin.categories'))

        return render_template('admin/edit_category.html', category=category)

    except Exception as e:
        logger.error(f"Error editing category: {str(e)}")
        flash('Error editing category', 'error')
        return redirect(url_for('admin.categories'))
    finally:
        db.close_session(db_session)


@admin_bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_category(category_id):
    """Delete a category."""
    user_id = session.get('user_id')
    db_session = db.get_session()

    try:
        category = db_session.query(Category).filter(
            Category.id == category_id,
            Category.user_id == user_id
        ).first()

        if not category:
            flash('Category not found', 'error')
            return redirect(url_for('admin.categories'))

        db_session.delete(category)
        db_session.commit()
        
        flash('Category deleted successfully', 'success')
        return redirect(url_for('admin.categories'))

    except Exception as e:
        logger.error(f"Error deleting category: {str(e)}")
        flash('Error deleting category', 'error')
        return redirect(url_for('admin.categories'))
    finally:
        db.close_session(db_session)


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