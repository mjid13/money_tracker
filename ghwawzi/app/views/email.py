import logging
import os
from asyncio import Lock

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from app.models.database import Database
from app.models.transaction import TransactionRepository
from app.models.user import User
from app.models import Category, CategoryMapping, EmailConfiguration, Bank, Account, Transaction
from datetime import datetime, time
from flask import jsonify
from app.utils.decorators import login_required
from app.services.email_service import EmailService
from app.services.parser_service import TransactionParser
from werkzeug.utils import secure_filename

# Create blueprint
email_bp = Blueprint('email', __name__)

# Initialize database and logger
db = Database()
logger = logging.getLogger(__name__)
parser = TransactionParser()

# Task manager for tracking email fetching tasks
email_tasks = {}
email_tasks_lock = Lock()


@email_bp.route('/email-configs', methods=['GET'])
@login_required
def email_configs():
    """List all email configurations."""
    user_id = session.get('user_id')
    db_session = db.get_session()

    try:
        # Get all email configurations for this user
        email_configs = db_session.query(EmailConfiguration).filter(
            EmailConfiguration.user_id == user_id
        ).all()

        return render_template('email_configs.html', email_configs=email_configs)
    except Exception as e:
        logger.error(f"Error listing email configurations: {str(e)}")
        flash(f'Error listing email configurations: {str(e)}', 'error')
        return redirect(url_for('dashboard'))
    finally:
        db.close_session(db_session)


@email_bp.route('/email-config/add', methods=['GET', 'POST'])
@login_required
def add_email_config():
    """Add a new email configuration."""
    user_id = session.get('user_id')
    db_session = db.get_session()

    try:
        # Get all available banks
        banks = db_session.query(Bank).all()

        if request.method == 'POST':
            email_username = request.form.get('email_username')

            # Extract provider from email
            provider_name = EmailService.extract_provider_from_email(email_username)

            # Get provider configuration if available
            provider_config = None
            if provider_name:
                provider_config = EmailService.get_provider_config(db_session, provider_name)

                # Get the provider record to set the relationship
                from money_tracker.models.models import EmailServiceProvider
                provider = db_session.query(EmailServiceProvider).filter_by(
                    provider_name=provider_name
                ).first()

            # Get bank information
            bank_ids = request.form.getlist('bank_ids[]')
            selected_banks = []

            # For backward compatibility, keep track of the first bank
            first_bank = None

            if bank_ids:
                for bank_id in bank_ids:
                    try:
                        bank = db_session.query(Bank).filter_by(id=int(bank_id)).first()
                        if bank:
                            selected_banks.append(bank)
                            if first_bank is None:
                                first_bank = bank
                    except ValueError:
                        logger.warning(f"Invalid bank ID: {bank_id}")

                if not selected_banks:
                    flash('No valid banks selected', 'error')
                    return render_template('add_email_config.html', banks=banks)

            # Prepare configuration data
            config_data = {
                'user_id': user_id,
                'name': request.form.get('name', 'Default'),
                'email_username': email_username,
                'email_password': request.form.get('email_password'),
                'bank_email_addresses': request.form.get('bank_email_addresses', ''),
                'bank_email_subjects': request.form.get('bank_email_subjects', '')
            }

            # Add bank_id of the first selected bank for backward compatibility
            if first_bank:
                config_data['bank_id'] = first_bank.id

            # If provider configuration is available, use it
            if provider_config and provider:
                config_data['email_host'] = provider_config['host']
                config_data['email_port'] = provider_config['port']
                config_data['email_use_ssl'] = provider_config['use_ssl']
                config_data['service_provider_id'] = provider.id
                logger.info(f"Using configuration for provider: {provider_name}")
            else:
                # Fall back to manual configuration if provider not recognized
                config_data['email_host'] = request.form.get('email_host')
                config_data['email_port'] = int(request.form.get('email_port', 993))
                config_data['email_use_ssl'] = 'email_use_ssl' in request.form
                logger.info(f"Using manual configuration (provider not recognized or not found)")

            # Create the email configuration
            email_config = TransactionRepository.create_email_config(db_session, config_data)
            if email_config:
                # Create the many-to-many relationships with selected banks
                if selected_banks:
                    from money_tracker.models.models import EmailConfigBank
                    for bank in selected_banks:
                        # Check if the relationship already exists
                        existing = db_session.query(EmailConfigBank).filter_by(
                            email_config_id=email_config.id,
                            bank_id=bank.id
                        ).first()

                        if not existing:
                            # Create a new relationship
                            email_config_bank = EmailConfigBank(
                                email_config_id=email_config.id,
                                bank_id=bank.id
                            )
                            db_session.add(email_config_bank)

                    # Commit the changes
                    db_session.commit()

                flash('Email configuration added successfully', 'success')
                return redirect(url_for('email_configs'))
            else:
                flash('Error adding email configuration', 'error')
                return render_template('add_email_config.html', banks=banks)

        # For GET requests, render the form
        return render_template('add_email_config.html', banks=banks)
    except Exception as e:
        logger.error(f"Error adding email configuration: {str(e)}")
        flash(f'Error adding email configuration: {str(e)}', 'error')
        return redirect(url_for('email_configs'))
    finally:
        db.close_session(db_session)


@email_bp.route('/email-config/<int:config_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_email_config(config_id):
    """Edit an existing email configuration."""
    user_id = session.get('user_id')
    db_session = db.get_session()

    try:
        # Get the email configuration
        email_config = db_session.query(EmailConfiguration).filter(
            EmailConfiguration.id == config_id,
            EmailConfiguration.user_id == user_id
        ).first()

        if not email_config:
            flash('Email configuration not found or you do not have permission to edit it', 'error')
            return redirect(url_for('email_configs'))

        # Get all available banks
        banks = db_session.query(Bank).all()

        # Get all banks associated with this email configuration
        from money_tracker.models.models import EmailConfigBank
        associated_bank_ids = [rel.bank_id for rel in db_session.query(EmailConfigBank).filter_by(
            email_config_id=email_config.id
        ).all()]

        if request.method == 'POST':
            email_username = request.form.get('email_username')

            # Extract provider from email
            provider_name = EmailService.extract_provider_from_email(email_username)

            # Get provider configuration if available
            provider_config = None
            if provider_name:
                provider_config = EmailService.get_provider_config(db_session, provider_name)

                # Get the provider record to set the relationship
                from money_tracker.models.models import EmailServiceProvider
                provider = db_session.query(EmailServiceProvider).filter_by(
                    provider_name=provider_name
                ).first()

            # Get bank information
            bank_ids = request.form.getlist('bank_ids[]')
            selected_banks = []

            # For backward compatibility, keep track of the first bank
            first_bank = None

            if bank_ids:
                for bank_id in bank_ids:
                    try:
                        bank = db_session.query(Bank).filter_by(id=int(bank_id)).first()
                        if bank:
                            selected_banks.append(bank)
                            if first_bank is None:
                                first_bank = bank
                    except ValueError:
                        logger.warning(f"Invalid bank ID: {bank_id}")

                if not selected_banks:
                    flash('No valid banks selected', 'error')
                    return render_template('edit_email_config.html', email_config=email_config, banks=banks)

                # Update bank_id for backward compatibility
                email_config.bank_id = first_bank.id
            else:
                email_config.bank_id = None

            # Update basic fields
            email_config.name = request.form.get('name', 'Default')
            email_config.email_username = email_username

            # Only update password if provided
            new_password = request.form.get('email_password')
            if new_password:
                email_config.email_password = new_password

            email_config.bank_email_addresses = request.form.get('bank_email_addresses', '')
            email_config.bank_email_subjects = request.form.get('bank_email_subjects', '')

            # If provider configuration is available, use it
            if provider_config and provider:
                email_config.email_host = provider_config['host']
                email_config.email_port = provider_config['port']
                email_config.email_use_ssl = provider_config['use_ssl']
                email_config.service_provider_id = provider.id
                logger.info(f"Using configuration for provider: {provider_name}")
            else:
                # Fall back to manual configuration if provider not recognized
                email_config.email_host = request.form.get('email_host')
                email_config.email_port = int(request.form.get('email_port', 993))
                email_config.email_use_ssl = 'email_use_ssl' in request.form
                email_config.service_provider_id = None
                logger.info(f"Using manual configuration (provider not recognized or not found)")

            # Update the many-to-many relationships with selected banks
            if selected_banks:
                from money_tracker.models.models import EmailConfigBank

                # Get existing relationships
                existing_relationships = db_session.query(EmailConfigBank).filter_by(
                    email_config_id=email_config.id
                ).all()

                # Create a set of existing bank IDs for easy lookup
                existing_bank_ids = {rel.bank_id for rel in existing_relationships}

                # Create a set of selected bank IDs
                selected_bank_ids = {bank.id for bank in selected_banks}

                # Remove relationships that are no longer needed
                for rel in existing_relationships:
                    if rel.bank_id not in selected_bank_ids:
                        db_session.delete(rel)

                # Add new relationships
                for bank in selected_banks:
                    if bank.id not in existing_bank_ids:
                        email_config_bank = EmailConfigBank(
                            email_config_id=email_config.id,
                            bank_id=bank.id
                        )
                        db_session.add(email_config_bank)

            # Commit all changes
            db_session.commit()
            flash('Email configuration updated successfully', 'success')
            return redirect(url_for('email_configs'))

        return render_template('edit_email_config.html', email_config=email_config, banks=banks,
                               associated_bank_ids=associated_bank_ids)
    except Exception as e:
        logger.error(f"Error editing email configuration: {str(e)}")
        flash(f'Error editing email configuration: {str(e)}', 'error')
        return redirect(url_for('email_configs'))
    finally:
        db.close_session(db_session)


@email_bp.route('/email-config/<int:config_id>/delete', methods=['POST'])
@login_required
def delete_email_config(config_id):
    """Delete an email configuration."""
    user_id = session.get('user_id')
    db_session = db.get_session()

    try:
        # Get the email configuration
        email_config = db_session.query(EmailConfiguration).filter(
            EmailConfiguration.id == config_id,
            EmailConfiguration.user_id == user_id
        ).first()

        if not email_config:
            flash('Email configuration not found or you do not have permission to delete it', 'error')
            return redirect(url_for('email_configs'))

        # Check if any accounts are using this configuration
        accounts = db_session.query(Account).filter(
            Account.email_config_id == config_id
        ).first()

        if accounts:
            flash('Cannot delete email configuration that is being used by accounts', 'error')
            return redirect(url_for('email_configs'))

        db_session.delete(email_config)
        db_session.commit()
        flash('Email configuration deleted successfully', 'success')
        return redirect(url_for('email_configs'))
    except Exception as e:
        logger.error(f"Error deleting email configuration: {str(e)}")
        flash(f'Error deleting email configuration: {str(e)}', 'error')
        return redirect(url_for('email_configs'))
    finally:
        db.close_session(db_session)


@email_bp.route('/parse', methods=['POST'])
@login_required
def parse_email():
    """Parse email data from various sources."""
    user_id = session.get('user_id')
    email_data = {}
    source = request.form.get('source')
    account_number = request.form.get('account_number')

    if not account_number:
        flash('Please select an account', 'error')
        return redirect(url_for('dashboard'))

    if source == 'email':
        # Parse the email data
        transaction_data = parser.parse_email(email_data)

        if not transaction_data:
            flash('Failed to parse email content. Make sure it contains valid transaction data.', 'error')
            return redirect(url_for('dashboard'))

        # Check if the account is different
        if account_number[-4:] not in transaction_data.get('account_number'):
            flash(
                f'Transaction account number {transaction_data.get("account_number")} does not match selected account {account_number}',
                'error')
            return redirect(url_for('dashboard'))

        # Add user_id and account_number to transaction data
        transaction_data['user_id'] = user_id
        transaction_data['account_number'] = account_number
        transaction_data['email_data'] = email_data

        # Store the transaction data in session for display
        session['transaction_data'] = transaction_data

        # Optionally save to database if requested
        save_to_db = 'save_to_db' in request.form
        preserve_balance = 'preserve_balance' in request.form

        if save_to_db:
            db_session = db.get_session()
            try:
                # Add preserve_balance flag to transaction data
                transaction_data['preserve_balance'] = preserve_balance
                transaction = TransactionRepository.create_transaction(db_session, transaction_data)
                if transaction:
                    flash('Transaction saved to database', 'success')
                else:
                    flash('Failed to save transaction to database', 'error')
            except Exception as e:
                logger.error(f"Error saving transaction to database: {str(e)}")
                flash(f'Error saving to database: {str(e)}', 'error')
            finally:
                db.close_session(db_session)

        return redirect(url_for('results'))


    elif source == 'upload':
        # Handle uploaded email file
        if 'email_file' not in request.files:
            flash('No file part', 'error')
            return redirect(url_for('dashboard'))

        file = request.files['email_file']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(url_for('dashboard'))

        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    email_content = f.read()

                email_data = {
                    'id': f'upload_{datetime.now().strftime("%Y%m%d%H%M%S")}',
                    'subject': filename,
                    'from': request.form.get('from', 'upload@example.com'),
                    'date': datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z'),
                    'body': email_content
                }

                # Clean up the uploaded file
                os.remove(filepath)
            except Exception as e:
                logger.error(f"Error reading uploaded file: {str(e)}")
                flash(f'Error reading file: {str(e)}', 'error')
                return redirect(url_for('dashboard'))

    else:
        flash('Invalid source', 'error')
        return redirect(url_for('dashboard'))


@email_bp.route('/email/task/<task_id>/status')
@login_required
def email_task_status(task_id):
    """API endpoint for checking email task status."""
    with email_tasks_lock:
        if task_id not in email_tasks:
            return jsonify({'error': 'Task not found'}), 404

        task = email_tasks[task_id].copy()  # Create a copy to avoid holding the lock

    # Calculate elapsed time
    elapsed_time = time.time() - task['start_time']

    # Prepare response data
    response = {
        'status': task['status'],
        'progress': task['progress'],
        'elapsed_seconds': elapsed_time,
        'message': task.get('message', '')
    }

    # Add estimated time if available
    if 'estimated_seconds' in task:
        response['estimated_seconds'] = task['estimated_seconds']

    # Add completion data if task is completed
    if task['status'] == 'completed':
        response['parsed_count'] = task.get('parsed_count', 0)
        response['saved_count'] = task.get('saved_count', 0)

        # If there's a transaction, redirect to results
        if 'first_transaction' in task:
            # Store the transaction in session for the results page
            session['transaction_data'] = task['first_transaction']
            response['redirect_url'] = url_for('results')

    return jsonify(response)

@email_bp.route('/api/test_email_connection/<int:config_id>')
@login_required
def test_email_connection(config_id):
    """Test the email connection for a specific configuration."""
    user_id = session.get('user_id')
    db_session = db.get_session()

    try:
        # Get the email configuration
        email_config = db_session.query(EmailConfiguration).filter(
            EmailConfiguration.id == config_id,
            EmailConfiguration.user_id == user_id
        ).first()

        if not email_config:
            return jsonify({
                'success': False,
                'message': 'Email configuration not found'
            }), 404

        # Create email service from the configuration
        email_service = EmailService(
            host=email_config.email_host,
            port=email_config.email_port,
            username=email_config.email_username,
            password=email_config.email_password,
            use_ssl=email_config.email_use_ssl,
            bank_email_addresses=[],
            bank_email_subjects=[]
        )

        # Test connection
        if email_service.connect():
            email_service.disconnect()
            # Update last tested timestamp
            email_config.last_tested = datetime.now()
            db_session.commit()
            return jsonify({
                'success': True,
                'message': 'Successfully connected to email server'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to connect to email server'
            })

    except Exception as e:
        logger.error(f"Error testing email connection: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
    finally:
        db.close_session(db_session)
