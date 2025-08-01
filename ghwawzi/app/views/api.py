"""
API views for the Flask application.
"""
import logging
import json
from datetime import time
from threading import Lock

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response, Blueprint
from app.models import Database, TransactionRepository, Transaction, Account, Category
from app.utils.decorators import login_required

# Create blueprint
api_bp = Blueprint('api', __name__)

# Initialize database and logger
db = Database()
logger = logging.getLogger(__name__)

# Task manager for tracking email fetching tasks
email_tasks = {}
email_tasks_lock = Lock()


@api_bp.route('/transaction/<int:transaction_id>', methods=['DELETE'])
@login_required
def delete_transaction(transaction_id):
    """Delete a transaction."""
    user_id = session.get('user_id')
    db_session = db.get_session()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    try:
        # Get transaction and verify it belongs to the user
        transaction = db_session.query(Transaction).join(Account).filter(
            Transaction.id == transaction_id,
            Account.user_id == user_id
        ).first()

        if not transaction:
            if is_ajax:
                return jsonify({'success': False, 'message': 'Transaction not found or you do not have permission to delete it'})
            flash('Transaction not found or you do not have permission to delete it', 'error')
            return redirect(url_for('accounts'))

        account_number = transaction.account.account_number

        result = TransactionRepository.delete_transaction(db_session, transaction_id)
        if result:
            if is_ajax:
                return jsonify({
                    'success': True,
                    'message': 'Transaction deleted successfully',
                    'transaction_id': transaction_id
                })
            flash('Transaction deleted successfully', 'success')
        else:
            if is_ajax:
                return jsonify({'success': False, 'message': 'Error deleting transaction'})
            flash('Error deleting transaction', 'error')

        return redirect(url_for('account_details', account_number=account_number))
    except Exception as e:
        logger.error(f"Error deleting transaction: {str(e)}")
        if is_ajax:
            return jsonify({'success': False, 'message': f'Error deleting transaction: {str(e)}'})
        flash(f'Error deleting transaction: {str(e)}', 'error')
        return redirect(url_for('accounts'))
    finally:
        db.close_session(db_session)


@api_bp.route('/transaction/<int:transaction_id>/category', methods=['PUT'])
@login_required
def update_transaction_category(transaction_id):
    """Update the category of a transaction."""
    user_id = session.get('user_id')
    db_session = db.get_session()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    try:
        # Get transaction and verify it belongs to the user
        transaction = db_session.query(Transaction).join(Account).filter(
            Transaction.id == transaction_id,
            Account.user_id == user_id
        ).first()

        if not transaction:
            if is_ajax:
                return jsonify(
                    {'success': False, 'message': 'Transaction not found or you do not have permission to edit it'})
            flash('Transaction not found or you do not have permission to edit it', 'error')
            return redirect(url_for('accounts'))

        # Get the category ID from the request
        category_id = request.form.get('category_id')
        if not category_id:
            if is_ajax:
                return jsonify({'success': False, 'message': 'Category ID is required'})
            flash('Category ID is required', 'error')
            return redirect(url_for('account_details', account_number=transaction.account.account_number))

        # Update the transaction category
        transaction_data = {
            'category_id': category_id
        }
        updated_transaction = TransactionRepository.update_transaction(
            db_session, transaction_id, transaction_data
        )

        if updated_transaction:
            # Get the category name for the response
            category = db_session.query(Category).filter(Category.id == category_id).first()
            category_name = category.name if category else 'Uncategorized'

            if is_ajax:
                return jsonify({
                    'success': True,
                    'message': 'Category updated successfully',
                    'category_name': category_name
                })
            flash('Category updated successfully', 'success')
            return redirect(url_for('account_details', account_number=transaction.account.account_number))
        else:
            if is_ajax:
                return jsonify({'success': False, 'message': 'Error updating category'})
            flash('Error updating category', 'error')
            return redirect(url_for('account_details', account_number=transaction.account.account_number))
    except Exception as e:
        logger.error(f"Error updating transaction category: {str(e)}")
        if is_ajax:
            return jsonify({'success': False, 'message': f'Error updating transaction category: {str(e)}'})
        flash(f'Error updating transaction category: {str(e)}', 'error')
        return redirect(url_for('accounts'))
    finally:
        db.close_session(db_session)


@api_bp.route('/email/task/<task_id>/status')
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

@api_bp.route('/get_chart_data')
@login_required
def get_chart_data():
    """Get chart data filtered by account and date range."""
    user_id = session.get('user_id')
    account_number = request.args.get('account_number', 'all')
    date_range = request.args.get('date_range', 'overall')

    db_session = db.get_session()

    try:
        # Prepare data for charts
        chart_data = {}

        # Import necessary modules for data aggregation
        from sqlalchemy import func, case, extract
        from datetime import datetime, timedelta
        from money_tracker.models.models import Transaction, Category, TransactionType

        # Calculate date range based on selection
        end_date = datetime.now()
        start_date = None

        if date_range == '2w':  # Last 2 weeks
            start_date = end_date - timedelta(days=14)
        elif date_range == '1m':  # Last month
            start_date = end_date - timedelta(days=30)
        elif date_range == '3m':  # Last 3 months
            start_date = end_date - timedelta(days=90)
        elif date_range == '6m':  # Last 6 months
            start_date = end_date - timedelta(days=180)
        elif date_range == '12m':  # Last 12 months
            start_date = end_date - timedelta(days=365)
        elif date_range == '24m':  # Last 24 months
            start_date = end_date - timedelta(days=730)
        # For 'overall', start_date remains None

        # Base query for transactions
        base_query = db_session.query(Transaction).join(Account)

        # Filter by user_id
        base_query = base_query.filter(Account.user_id == user_id)

        # Filter by account_number if specified
        if account_number != 'all':
            base_query = base_query.filter(Account.account_number == account_number)

        # 1. Income vs. Expense Comparison Chart
        income_expense_query = db_session.query(
            func.sum(case((Transaction.transaction_type == TransactionType.INCOME, Transaction.amount), else_=0)).label(
                'total_income'),
            func.sum(
                case((Transaction.transaction_type == TransactionType.EXPENSE, Transaction.amount), else_=0)).label(
                'total_expense')
        ).join(Account)

        # Filter by user_id
        income_expense_query = income_expense_query.filter(Account.user_id == user_id)

        # Filter by account_number if specified
        if account_number != 'all':
            income_expense_query = income_expense_query.filter(Account.account_number == account_number)

        income_expense_data = income_expense_query.first()

        chart_data['income_expense'] = {
            'labels': ['Income', 'Expense'],
            'datasets': [{
                'data': [
                    float(income_expense_data.total_income or 0),
                    float(income_expense_data.total_expense or 0)
                ],
                'backgroundColor': ['#4CAF50', '#F44336']
            }]
        }

        # 2. Category Distribution Pie Chart
        # Get expense transactions with categories
        category_query = db_session.query(
            Category.name,
            Category.color,
            func.sum(Transaction.amount).label('total_amount')
        ).join(
            Transaction, Transaction.category_id == Category.id
        ).join(
            Account, Transaction.account_id == Account.id
        ).filter(
            Account.user_id == user_id,
            Transaction.transaction_type == TransactionType.EXPENSE
        )

        # Filter by account_number if specified
        if account_number != 'all':
            category_query = category_query.filter(Account.account_number == account_number)

        category_data = category_query.group_by(
            Category.name,
            Category.color
        ).order_by(
            func.sum(Transaction.amount).desc()
        ).limit(10).all()

        # Format data for pie chart
        category_labels = [cat.name for cat in category_data]
        category_values = [float(cat.total_amount) for cat in category_data]

        # Use category colors from database, or fallback to defaults
        default_colors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
            '#FF9F40', '#8AC249', '#EA5545', '#F46A9B', '#EF9B20'
        ]
        category_colors = []
        for i, cat in enumerate(category_data):
            if cat.color:
                category_colors.append(cat.color)
            else:
                # Use default color if category doesn't have one
                category_colors.append(default_colors[i % len(default_colors)])

        chart_data['category_distribution'] = {
            'labels': category_labels,
            'datasets': [{
                'data': category_values,
                'backgroundColor': category_colors[:len(category_labels)]
            }]
        }

        # 3. Monthly Transaction Trend Line Chart
        # Get data for the last 6 months
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)  # Approximately 6 months

        # Query monthly aggregates
        monthly_query = db_session.query(
            extract('year', Transaction.value_date).label('year'),
            extract('month', Transaction.value_date).label('month'),
            func.sum(case((Transaction.transaction_type == TransactionType.INCOME, Transaction.amount), else_=0)).label(
                'income'),
            func.sum(
                case((Transaction.transaction_type == TransactionType.EXPENSE, Transaction.amount), else_=0)).label(
                'expense')
        ).join(
            Account, Transaction.account_id == Account.id
        ).filter(
            Account.user_id == user_id,
            Transaction.value_date.between(start_date, end_date)
        )

        # Filter by account_number if specified
        if account_number != 'all':
            monthly_query = monthly_query.filter(Account.account_number == account_number)

        monthly_data = monthly_query.group_by(
            extract('year', Transaction.value_date),
            extract('month', Transaction.value_date)
        ).order_by(
            extract('year', Transaction.value_date),
            extract('month', Transaction.value_date)
        ).all()

        # Format data for line chart
        months = []
        income_values = []
        expense_values = []

        for data in monthly_data:
            month_name = datetime(int(data.year), int(data.month), 1).strftime('%b %Y')
            months.append(month_name)
            income_values.append(float(data.income or 0))
            expense_values.append(float(data.expense or 0))

        chart_data['monthly_trend'] = {
            'labels': months,
            'datasets': [
                {
                    'label': 'Income',
                    'data': income_values,
                    'borderColor': '#4CAF50',
                    'backgroundColor': 'rgba(76, 175, 80, 0.1)',
                    'fill': True
                },
                {
                    'label': 'Expense',
                    'data': expense_values,
                    'borderColor': '#F44336',
                    'backgroundColor': 'rgba(244, 67, 54, 0.1)',
                    'fill': True
                }
            ]
        }

        # 4. Account Balance Comparison Chart
        # For account balance chart, we'll only show the selected account if one is specified
        # Otherwise, show all accounts
        account_query = db_session.query(Account).filter(Account.user_id == user_id)

        if account_number != 'all':
            account_query = account_query.filter(Account.account_number == account_number)

        accounts_for_chart = account_query.all()

        account_data = []
        for account in accounts_for_chart:
            account_data.append({
                'account_number': account.account_number,
                'bank_name': account.bank_name,
                'balance': float(account.balance),
                'currency': account.currency
            })

        # Sort accounts by balance (descending)
        account_data.sort(key=lambda x: x['balance'], reverse=True)

        # Format data for bar chart
        account_labels = [f"{acc['bank_name']} ({acc['account_number'][-4:]})" for acc in account_data]
        account_balances = [acc['balance'] for acc in account_data]
        account_currencies = [acc['currency'] for acc in account_data]

        chart_data['account_balance'] = {
            'labels': account_labels,
            'datasets': [{
                'label': 'Balance',
                'data': account_balances,
                'backgroundColor': '#2196F3',
                'borderColor': '#1976D2',
                'borderWidth': 1
            }],
            'currencies': account_currencies
        }

        return jsonify(chart_data)
    except Exception as e:
        logger.error(f"Error getting chart data: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close_session(db_session)
