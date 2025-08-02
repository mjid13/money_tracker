import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models.database import Database
from app.models.transaction import TransactionRepository
from app.models.user import User
from app.models import Category, CategoryMapping, EmailConfiguration, Bank, Account, Transaction
from datetime import datetime
from flask import jsonify
from app.utils.decorators import login_required

# Create blueprint
account_bp = Blueprint('account', __name__)

# Initialize database and logger
db = Database()
logger = logging.getLogger(__name__)

@account_bp.route('/accounts')
@login_required
def accounts():
    """Display all accounts and their summaries."""
    user_id = session.get('user_id')
    db_session = db.get_session()
    try:
        # Get user's accounts
        accounts = TransactionRepository.get_user_accounts(db_session, user_id)

        summaries = []
        for account in accounts:
            summary = TransactionRepository.get_account_summary(db_session, user_id, account.account_number)
            if summary:
                summaries.append(summary)

        return render_template('accounts.html', summaries=summaries)
    except Exception as e:
        logger.error(f"Error getting account summaries: {str(e)}")
        flash(f'Error getting account summaries: {str(e)}', 'error')
        return redirect(url_for('dashboard'))
    finally:
        db.close_session(db_session)


@account_bp.route('/accounts/add', methods=['GET', 'POST'])
@login_required
def add_account():
    """Add a new bank account."""
    user_id = session.get('user_id')
    db_session = db.get_session()

    try:
        # Get all email configurations for this user
        email_configs = db_session.query(EmailConfiguration).filter(
            EmailConfiguration.user_id == user_id
        ).all()

        # Get all available banks
        banks = db_session.query(Bank).all()

        if request.method == 'POST':
            account_number = request.form.get('account_number')
            bank_id = request.form.get('bank_id')
            account_holder = request.form.get('account_holder')
            balance = request.form.get('balance', 0.0)
            currency = request.form.get('currency', 'OMR')
            email_config_id = request.form.get('email_config_id')

            if not account_number:
                flash('Account number is required', 'error')
                return render_template('add_account.html', email_configs=email_configs, banks=banks)

            # Get bank information
            bank_name = None
            if bank_id:
                try:
                    bank = db_session.query(Bank).filter_by(id=int(bank_id)).first()
                    if bank:
                        bank_name = bank.name
                        currency = bank.currency
                except ValueError:
                    flash('Invalid bank selected', 'error')
                    return render_template('add_account.html', email_configs=email_configs, banks=banks)

            if not bank_name:
                flash('Please select a valid bank', 'error')
                return render_template('add_account.html', email_configs=email_configs, banks=banks)

            # Validate balance
            try:
                balance_float = float(balance) if balance else 0.0
            except ValueError:
                flash('Balance must be a valid number', 'error')
                return render_template('add_account.html', email_configs=email_configs, banks=banks)

            # Create account data
            account_data = {
                'user_id': user_id,
                'account_number': account_number,
                'bank_id': int(bank_id) if bank_id else None,
                'bank_name': bank_name,
                'account_holder': account_holder,
                'balance': balance_float,
                'currency': currency
            }

            # Add email_config_id if provided
            if email_config_id:
                try:
                    account_data['email_config_id'] = int(email_config_id)
                except ValueError:
                    flash('Invalid email configuration selected', 'error')
                    return render_template('add_account.html', email_configs=email_configs, banks=banks)

            account = TransactionRepository.create_account(db_session, account_data)
            if account:
                flash('Account added successfully', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Error adding account', 'error')
                return render_template('add_account.html', email_configs=email_configs, banks=banks)

        return render_template('add_account.html', email_configs=email_configs, banks=banks)
    except Exception as e:
        logger.error(f"Error adding account: {str(e)}")
        flash('Error adding account. Please try again.', 'error')
        return render_template('add_account.html', email_configs=[], banks=[])
    finally:
        db.close_session(db_session)


@account_bp.route('/accounts/<int:account_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_account(account_id):
    """Edit a bank account."""
    user_id = session.get('user_id')
    db_session = db.get_session()

    try:
        account = db_session.query(Account).filter(
            Account.id == account_id,
            Account.user_id == user_id
        ).first()

        if not account:
            flash('Account not found or you do not have permission to edit it', 'error')
            return redirect(url_for('dashboard'))

        # Get all email configurations for this user
        email_configs = db_session.query(EmailConfiguration).filter(
            EmailConfiguration.user_id == user_id
        ).all()

        # Get all available banks
        banks = db_session.query(Bank).all()

        if request.method == 'POST':
            account.account_number = request.form.get('account_number')
            account_holder = request.form.get('account_holder')
            balance = request.form.get('balance', 0.0)

            # Handle bank selection
            bank_id = request.form.get('bank_id')
            if bank_id:
                try:
                    bank = db_session.query(Bank).filter_by(id=int(bank_id)).first()
                    if bank:
                        account.bank_id = int(bank_id)
                        account.bank_name = bank.name
                        account.currency = bank.currency
                    else:
                        flash('Selected bank not found', 'error')
                        return render_template('edit_account.html', account=account, email_configs=email_configs,
                                               banks=banks)
                except ValueError:
                    flash('Invalid bank selected', 'error')
                    return render_template('edit_account.html', account=account, email_configs=email_configs,
                                           banks=banks)
            else:
                flash('Please select a valid bank', 'error')
                return render_template('edit_account.html', account=account, email_configs=email_configs, banks=banks)

            # Update other fields
            account.account_holder = account_holder
            try:
                account.balance = float(balance)
            except ValueError:
                flash('Balance must be a valid number', 'error')
                return render_template('edit_account.html', account=account, email_configs=email_configs, banks=banks)

            # Update email_config_id
            email_config_id = request.form.get('email_config_id')
            if email_config_id:
                account.email_config_id = int(email_config_id)
            else:
                account.email_config_id = None

            db_session.commit()
            flash('Account updated successfully', 'success')
            return redirect(url_for('dashboard'))

        return render_template('edit_account.html', account=account, email_configs=email_configs, banks=banks)
    except Exception as e:
        logger.error(f"Error editing account: {str(e)}")
        flash(f'Error editing account: {str(e)}', 'error')
        return redirect(url_for('dashboard'))
    finally:
        db.close_session(db_session)


@account_bp.route('/accounts/<int:account_id>/update-balance', methods=['POST'])
@login_required
def update_balance(account_id):
    """Update account balance."""
    user_id = session.get('user_id')
    db_session = db.get_session()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    try:
        account = db_session.query(Account).filter(
            Account.id == account_id,
            Account.user_id == user_id
        ).first()

        if not account:
            if is_ajax:
                return jsonify(
                    {'success': False, 'message': 'Account not found or you do not have permission to update it'})
            flash('Account not found or you do not have permission to update it', 'error')
            return redirect(url_for('dashboard'))

        new_balance = request.form.get('new_balance')
        if not new_balance:
            if is_ajax:
                return jsonify({'success': False, 'message': 'No balance value provided'})
            flash('No balance value provided', 'error')
            return redirect(url_for('account_details', account_number=account.account_number))

        try:
            new_balance = float(new_balance)
            account.balance = new_balance
            account.updated_at = datetime.now()  # Update the timestamp
            db_session.commit()

            if is_ajax:
                return jsonify({
                    'success': True,
                    'message': 'Balance updated successfully',
                    'balance': account.balance,
                    'formatted_balance': '{:.3f}'.format(account.balance)
                })

            flash('Balance updated successfully', 'success')
        except ValueError:
            if is_ajax:
                return jsonify({'success': False, 'message': 'Invalid balance value provided'})
            flash('Invalid balance value provided', 'error')

        # For non-AJAX requests, redirect to the account details page
        return redirect(url_for('account_details', account_number=account.account_number))
    except Exception as e:
        logger.error(f"Error updating balance: {str(e)}")
        if is_ajax:
            return jsonify({'success': False, 'message': f'Error updating balance: {str(e)}'})
        flash(f'Error updating balance: {str(e)}', 'error')
        return redirect(url_for('dashboard'))
    finally:
        db.close_session(db_session)


@account_bp.route('/accounts/<int:account_id>/delete', methods=['POST'])
@login_required
def delete_account(account_id):
    """Delete a bank account."""
    user_id = session.get('user_id')
    db_session = db.get_session()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    try:
        account = db_session.query(Account).filter(
            Account.id == account_id,
            Account.user_id == user_id
        ).first()

        if not account:
            if is_ajax:
                return jsonify(
                    {'success': False, 'message': 'Account not found or you do not have permission to delete it'})
            flash('Account not found or you do not have permission to delete it', 'error')
            return redirect(url_for('dashboard'))

        # First delete all transactions associated with the account
        db_session.query(Transaction).filter(Transaction.account_id == account.id).delete()

        # Then delete the account
        db_session.delete(account)
        db_session.commit()

        if is_ajax:
            return jsonify({
                'success': True,
                'message': 'Account deleted successfully',
                'redirect': url_for('accounts')
            })

        flash('Account deleted successfully', 'success')
        return redirect(url_for('dashboard'))
    except Exception as e:
        logger.error(f"Error deleting account: {str(e)}")
        if is_ajax:
            return jsonify({'success': False, 'message': f'Error deleting account: {str(e)}'})
        flash(f'Error deleting account: {str(e)}', 'error')
        return redirect(url_for('dashboard'))
    finally:
        db.close_session(db_session)

@account_bp.route('/account/<account_number>')
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