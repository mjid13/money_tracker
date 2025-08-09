#!/usr/bin/env python3
"""
Gmail Sync and Transaction Parsing Test Script

This script tests Gmail email synchronization and transaction parsing
using the existing transactions.db database.

Usage:
    python test_gmail_sync.py [user_id] [--max-messages=10] [--dry-run]

Options:
    user_id: The user ID to test (optional - will use first OAuth user if not specified)
    --max-messages: Maximum number of messages to process (default: 10)
    --dry-run: Don't save transactions to database, just show what would be parsed
"""

import sys
import os
import argparse
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Import Flask app to get application context
from app import create_app
from app.models.database import Database
from app.models.oauth import OAuthUser, EmailAuthConfig
from app.models.models import Transaction, Account, Bank
from app.models.transaction import TransactionRepository
from app.services.google_oauth_service import GoogleOAuthService
from app.services.gmail_service import GmailService
from app.services.parser_service import TransactionParser

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GmailSyncTester:
    """Test class for Gmail synchronization and transaction parsing."""
    
    def __init__(self):
        # Create Flask app instance
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Initialize services within Flask context
        self.db = Database()
        self.oauth_service = GoogleOAuthService()
        self.gmail_service = GmailService()
        self.parser = TransactionParser()
        self.transaction_repo = TransactionRepository()
    
    def __del__(self):
        """Clean up Flask app context."""
        if hasattr(self, 'app_context'):
            try:
                self.app_context.pop()
            except:
                pass
        
    def get_test_user(self, user_id: Optional[int] = None) -> Optional[OAuthUser]:
        """Get a user for testing. If no user_id specified, use the first OAuth user."""
        db_session = self.db.get_session()
        try:
            if user_id:
                oauth_user = db_session.query(OAuthUser).filter_by(
                    user_id=user_id,
                    provider='google',
                    is_active=True
                ).first()
            else:
                oauth_user = db_session.query(OAuthUser).filter_by(
                    provider='google',
                    is_active=True
                ).first()
            
            if oauth_user:
                logger.info(f"Found OAuth user: {oauth_user.email} (ID: {oauth_user.user_id})")
                return oauth_user
            else:
                logger.error("No active Google OAuth users found")
                return None
                
        finally:
            self.db.close_session(db_session)
    
    def get_or_create_email_config(self, oauth_user: OAuthUser) -> Optional[EmailAuthConfig]:
        """Get or create email configuration for the OAuth user."""
        db_session = self.db.get_session()
        try:
            # Try to get existing config
            email_config = db_session.query(EmailAuthConfig).filter_by(
                oauth_user_id=oauth_user.id,
                enabled=True
            ).first()
            
            if not email_config:
                logger.info("Creating default email configuration...")
                # Create a default configuration
                email_config = EmailAuthConfig(
                    oauth_user_id=oauth_user.id,
                    provider='google',
                    enabled=True,
                    auto_sync=True,
                    sync_frequency_hours=24
                )
                # Default settings for bank emails
                email_config.labels_list = ['INBOX']
                email_config.sender_filter_list = [
                    'bankmuscat@bankmuscat.com',
                    'noreply@bankmuscat.com',
                    'alerts@bankmuscat.com'
                ]
                email_config.subject_filter_list = [
                    'transaction',
                    'alert', 
                    'debit',
                    'credit',
                    'payment',
                    'transfer'
                ]
                
                db_session.add(email_config)
                db_session.commit()
                logger.info("Created default email configuration")
            else:
                logger.info(f"Found existing email configuration: {email_config.id}")
            
            return email_config
            
        except Exception as e:
            logger.error(f"Error getting/creating email config: {e}")
            db_session.rollback()
            return None
        finally:
            self.db.close_session(db_session)
    
    def test_gmail_connection(self, oauth_user: OAuthUser):
        """Test Gmail API connection and show user profile."""
        logger.info("\\n" + "="*50)
        logger.info("Testing Gmail Connection")
        logger.info("="*50)
        
        # Test Gmail service connection
        gmail_service = self.gmail_service.get_gmail_service(oauth_user)
        if not gmail_service:
            logger.error("Failed to connect to Gmail API")
            return False
        
        # Get user profile
        profile = self.gmail_service.get_user_profile(oauth_user)
        if profile:
            logger.info(f"Gmail Profile:")
            logger.info(f"  Email: {profile['email']}")
            logger.info(f"  Total Messages: {profile['messages_total']:,}")
            logger.info(f"  Total Threads: {profile['threads_total']:,}")
        else:
            logger.error("Failed to get Gmail profile")
            return False
        
        # List Gmail labels
        labels = self.gmail_service.list_labels(oauth_user)
        logger.info(f"\\nGmail Labels ({len(labels)} total):")
        for label in labels[:10]:  # Show first 10 labels
            logger.info(f"  - {label['name']} ({label['message_count']} messages)")
        
        return True
    
    def search_and_analyze_emails(self, oauth_user: OAuthUser, email_config: EmailAuthConfig, max_messages: int = 10):
        """Search for bank emails and analyze them."""
        logger.info("\\n" + "="*50)
        logger.info(f"Searching for Bank Emails (max: {max_messages})")
        logger.info("="*50)
        
        # Search for messages
        messages = self.gmail_service.search_messages(oauth_user, email_config, max_messages)
        
        logger.info(f"Found {len(messages)} messages matching filters")
        
        if not messages:
            logger.warning("No messages found. Consider adjusting your email config filters:")
            logger.info(f"  Labels: {email_config.labels_list}")
            logger.info(f"  Sender filters: {email_config.sender_filter_list}")
            logger.info(f"  Subject filters: {email_config.subject_filter_list}")
            return []
        
        # Analyze each message
        analyzed_messages = []
        for i, message in enumerate(messages, 1):
            logger.info(f"\\n--- Message {i}/{len(messages)} ---")
            logger.info(f"Subject: {message['subject']}")
            logger.info(f"Sender: {message['sender']}")
            logger.info(f"Date: {message['date']}")
            logger.info(f"Snippet: {message['snippet'][:100]}...")
            
            analyzed_messages.append(message)
        
        return analyzed_messages
    
    def parse_transactions(self, messages: List[Dict], dry_run: bool = False) -> List[Dict]:
        """Parse transactions from email messages."""
        logger.info("\\n" + "="*50)
        logger.info("Parsing Transactions from Emails")
        logger.info("="*50)
        
        parsed_transactions = []
        
        for i, message in enumerate(messages, 1):
            logger.info(f"\\n--- Parsing Message {i}/{len(messages)} ---")
            logger.info(f"Subject: {message['subject']}")
            
            # Clean the email text
            clean_text = self.parser.clean_text(message['body_text'])
            logger.info(f"Cleaned text length: {len(clean_text)} chars")
            
            # Try to parse transaction
            try:
                transaction_data = self.parser.parse_email_text(clean_text, message['subject'])
                
                if transaction_data:
                    logger.info("✓ Transaction successfully parsed!")
                    logger.info(f"  Amount: {transaction_data.get('amount', 'N/A')}")
                    logger.info(f"  Type: {transaction_data.get('transaction_type', 'N/A')}")
                    logger.info(f"  Date: {transaction_data.get('transaction_date', 'N/A')}")
                    logger.info(f"  Description: {transaction_data.get('description', 'N/A')[:50]}...")
                    logger.info(f"  Counterparty: {transaction_data.get('counterparty', 'N/A')}")
                    logger.info(f"  Account: {transaction_data.get('account_number', 'N/A')}")
                    
                    parsed_transactions.append({
                        'email_data': message,
                        'transaction_data': transaction_data
                    })
                else:
                    logger.warning("⚠ No transaction data could be parsed from this email")
                    # Show first 200 chars of cleaned text for debugging
                    logger.info(f"Text preview: {clean_text[:200]}...")
                    
            except Exception as e:
                logger.error(f"✗ Error parsing transaction: {e}")
                logger.info(f"Text preview: {clean_text[:200]}...")
        
        logger.info(f"\\nParsing Summary: {len(parsed_transactions)}/{len(messages)} emails successfully parsed")
        return parsed_transactions
    
    def save_transactions(self, parsed_transactions: List[Dict], user_id: int):
        """Save parsed transactions to database."""
        logger.info("\\n" + "="*50)
        logger.info("Saving Transactions to Database")
        logger.info("="*50)
        
        db_session = self.db.get_session()
        saved_count = 0
        duplicate_count = 0
        error_count = 0
        
        try:
            for item in parsed_transactions:
                transaction_data = item['transaction_data']
                email_data = item['email_data']
                
                try:
                    # Check if transaction already exists (basic duplicate check)
                    existing = db_session.query(Transaction).filter_by(
                        user_id=user_id,
                        amount=transaction_data.get('amount'),
                        transaction_date=transaction_data.get('transaction_date'),
                        description=transaction_data.get('description', '')[:100]
                    ).first()
                    
                    if existing:
                        logger.info(f"  ⚠ Duplicate transaction skipped: {transaction_data.get('description', '')[:50]}...")
                        duplicate_count += 1
                        continue
                    
                    # Get or create account (simplified)
                    account_number = transaction_data.get('account_number', 'Unknown')
                    account = db_session.query(Account).filter_by(
                        user_id=user_id,
                        account_number=account_number
                    ).first()
                    
                    if not account:
                        # Create a basic account entry
                        account = Account(
                            user_id=user_id,
                            account_number=account_number,
                            bank_name="Bank Muscat",  # Default
                            account_type="Unknown"
                        )
                        db_session.add(account)
                        db_session.flush()
                        logger.info(f"  Created new account: {account_number}")
                    
                    # Create transaction
                    transaction = Transaction(
                        user_id=user_id,
                        account_id=account.id,
                        amount=transaction_data.get('amount', 0.0),
                        transaction_type=transaction_data.get('transaction_type', 'unknown'),
                        transaction_date=transaction_data.get('transaction_date', datetime.now()),
                        description=transaction_data.get('description', ''),
                        counterparty=transaction_data.get('counterparty', ''),
                        balance_after=transaction_data.get('balance_after'),
                        category_id=None,  # Will be categorized later
                        email_subject=email_data.get('subject', ''),
                        email_sender=email_data.get('sender', ''),
                        created_at=datetime.now()
                    )
                    
                    db_session.add(transaction)
                    saved_count += 1
                    logger.info(f"  ✓ Saved: {transaction_data.get('description', '')[:50]}...")
                    
                except Exception as e:
                    logger.error(f"  ✗ Error saving transaction: {e}")
                    error_count += 1
            
            db_session.commit()
            logger.info(f"\\nSave Summary:")
            logger.info(f"  ✓ Saved: {saved_count}")
            logger.info(f"  ⚠ Duplicates skipped: {duplicate_count}")
            logger.info(f"  ✗ Errors: {error_count}")
            
        except Exception as e:
            logger.error(f"Database error: {e}")
            db_session.rollback()
        finally:
            self.db.close_session(db_session)
    
    def show_existing_transactions(self, user_id: int, limit: int = 10):
        """Show existing transactions in database for comparison."""
        logger.info("\\n" + "="*50)
        logger.info(f"Existing Transactions in Database (last {limit})")
        logger.info("="*50)
        
        db_session = self.db.get_session()
        try:
            transactions = db_session.query(Transaction).filter_by(
                user_id=user_id
            ).order_by(Transaction.transaction_date.desc()).limit(limit).all()
            
            if transactions:
                for i, trans in enumerate(transactions, 1):
                    logger.info(f"{i}. {trans.transaction_date.strftime('%Y-%m-%d')} | "
                              f"{trans.transaction_type} | "
                              f"{trans.amount:,.2f} | "
                              f"{trans.description[:40]}...")
            else:
                logger.info("No existing transactions found")
                
        finally:
            self.db.close_session(db_session)
    
    def run_test(self, user_id: Optional[int] = None, max_messages: int = 10, dry_run: bool = False):
        """Run the complete Gmail sync and parsing test."""
        logger.info("Gmail Sync and Transaction Parsing Test")
        logger.info("="*60)
        logger.info(f"Parameters: user_id={user_id}, max_messages={max_messages}, dry_run={dry_run}")
        
        # Step 1: Get test user
        oauth_user = self.get_test_user(user_id)
        if not oauth_user:
            logger.error("Cannot proceed without a valid OAuth user")
            return False
        
        # Step 2: Get/create email configuration
        email_config = self.get_or_create_email_config(oauth_user)
        if not email_config:
            logger.error("Cannot proceed without email configuration")
            return False
        
        # Step 3: Test Gmail connection
        if not self.test_gmail_connection(oauth_user):
            logger.error("Gmail connection failed")
            return False
        
        # Step 4: Show existing transactions
        self.show_existing_transactions(oauth_user.user_id)
        
        # Step 5: Search and analyze emails
        messages = self.search_and_analyze_emails(oauth_user, email_config, max_messages)
        if not messages:
            logger.warning("No messages to process")
            return False
        
        # Step 6: Parse transactions
        parsed_transactions = self.parse_transactions(messages, dry_run)
        if not parsed_transactions:
            logger.warning("No transactions were successfully parsed")
            return False
        
        # Step 7: Save transactions (unless dry run)
        if not dry_run:
            self.save_transactions(parsed_transactions, oauth_user.user_id)
            self.show_existing_transactions(oauth_user.user_id, 20)  # Show more after saving
        else:
            logger.info("\\nDRY RUN: Transactions were not saved to database")
        
        logger.info("\\n" + "="*60)
        logger.info("Test completed successfully!")
        return True


def main():
    """Main function to run the test script."""
    parser = argparse.ArgumentParser(
        description='Test Gmail sync and transaction parsing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('user_id', nargs='?', type=int, 
                       help='User ID to test (optional - uses first OAuth user if not specified)')
    parser.add_argument('--max-messages', type=int, default=10,
                       help='Maximum number of messages to process (default: 10)')
    parser.add_argument('--dry-run', action='store_true',
                       help="Don't save transactions to database, just show what would be parsed")
    
    args = parser.parse_args()
    
    # Create tester and run
    tester = None
    try:
        tester = GmailSyncTester()
        
        success = tester.run_test(
            user_id=1,
            max_messages=args.max_messages,
            dry_run=args.dry_run
        )
        
        if success:
            print("\\n✓ Test completed successfully!")
            sys.exit(0)
        else:
            print("\\n✗ Test failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
    finally:
        # Ensure proper cleanup
        if tester:
            del tester


if __name__ == '__main__':
    main()