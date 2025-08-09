"""
Auto-sync service for configuring email filters and syncing when accounts are added.
"""

import logging
from typing import Optional, Tuple, List
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError

from ..models.database import Database
from ..models.oauth import OAuthUserRepository, EmailAuthConfigRepository
from ..models.models import Bank, Account, OAuthUser, EmailAuthConfig
from .google_oauth_service import GoogleOAuthService
from .gmail_service import GmailService

logger = logging.getLogger(__name__)
email_config = EmailAuthConfigRepository()
oauth_repo = OAuthUserRepository()


class EmailSyncConfig:
    """Configuration class for EmailSync service."""
    
    def __init__(self, 
                 default_sync_frequency_hours: int = 6,
                 default_labels: List[str] = None,
                 common_subject_keywords: List[str] = None,
                 email_domain_variations: List[str] = None):
        self.default_sync_frequency_hours = default_sync_frequency_hours
        self.default_labels = default_labels or ['INBOX']
        self.common_subject_keywords = common_subject_keywords or [
            'transaction', 'debit', 'credit', 'payment', 'transfer', 
            'statement', 'balance', 'receipt'
        ]
        self.email_domain_variations = email_domain_variations or [
            'noreply', 'alerts', 'notifications', 'statements'
        ]


class EmailSync:
    """Service for automatically configuring email filters and syncing emails when accounts are added."""
    
    def __init__(self, config: Optional[EmailSyncConfig] = None):
        self.db = Database()
        self.oauth_service = GoogleOAuthService()
        self.gmail_service = GmailService()
        self.config = config or EmailSyncConfig()

    def create_sync(self, user_id: int, account: Account) -> Tuple[bool, str]:
        """
        Configure email filters based on the bank associated with the account.
        
        Args:
            user_id: User ID
            account: Account object that was just created
            
        Returns:
            Tuple of (success, message)
        """
        # Input validation
        if not isinstance(user_id, int) or user_id <= 0:
            logger.error(f"Invalid user_id: must be a positive integer")
            return False, "Invalid user_id: must be a positive integer"
        
        if not account:
            logger.error(f"Account object is required")
            return False, "Account object is required"
        
        if not hasattr(account, 'bank_id') or not hasattr(account, 'account_number'):
            logger.error(f"Invalid account object: missing required attributes")
            return False, "Invalid account object: missing required attributes"
        
        db_session = self.db.get_session()
        
        try:
            # Get the bank information
            if not account.bank_id:
                logger.error(f"Account has no associated bank for email configuration")
                return False, "Account has no associated bank for email configuration"
            
            bank = db_session.query(Bank).filter_by(id=account.bank_id).first()
            if not bank:
                logger.error(f"Bank not found for email configuration")
                return False, "Bank not found for email configuration"
            
            logger.info(f"Configuring email filters for account {account.account_number} with bank {bank.name}")
            

            oauth_user = db_session.query(OAuthUser).filter_by(
                user_id=user_id,
                provider='google',
                is_active=True
            ).first()
            
            if not oauth_user:
                logger.info(f"No OAuth user found for user {user_id}, skipping email configuration")
                return True, "No Gmail connection available for auto-sync"
            
            # Get or create email configuration
            email_config = db_session.query(EmailAuthConfig).filter_by(
                oauth_user_id=oauth_user.id
            ).first()
            
            if not email_config:
                # Create new email configuration
                # Normalize bank filters into lists
                bank_senders = []
                if bank.email_address:
                    # Support multiple senders separated by commas
                    bank_senders = [s.strip() for s in str(bank.email_address).split(',') if s.strip()]
                bank_subjects = []
                if bank.email_subjects:
                    bank_subjects = [s.strip() for s in str(bank.email_subjects).split(',') if s.strip()]

                email_config = EmailAuthConfig(
                    oauth_user_id=oauth_user.id,
                    enabled=True,
                    auto_sync=True,
                    sync_frequency_hours=self.config.default_sync_frequency_hours,
                )
                # Use property setters to ensure JSON storage format
                email_config.sender_filter_list = bank_senders
                email_config.subject_filter_list = bank_subjects

                db_session.add(email_config)
                db_session.flush()  # Get the ID
                logger.info(f"Created new email configuration for user {user_id}")

                db_session.commit()
                logger.info(f"Successfully configured email filters for account {account.account_number}")
                return True, "Email filters configured successfully"
            else:
                # Update existing configuration to include bank filters if missing
                updated = False
                bank_senders = []
                if bank.email_address:
                    bank_senders = [s.strip() for s in str(bank.email_address).split(',') if s.strip()]
                bank_subjects = []
                if bank.email_subjects:
                    bank_subjects = [s.strip() for s in str(bank.email_subjects).split(',') if s.strip()]

                # Merge and de-duplicate
                existing_senders = set(email_config.sender_filter_list)
                existing_subjects = set(email_config.subject_filter_list)
                new_senders = list(existing_senders.union(bank_senders))
                new_subjects = list(existing_subjects.union(bank_subjects))

                if new_senders != email_config.sender_filter_list:
                    email_config.sender_filter_list = new_senders
                    updated = True
                if new_subjects != email_config.subject_filter_list:
                    email_config.subject_filter_list = new_subjects
                    updated = True
                # Ensure enabled and auto_sync if previously disabled
                if not email_config.enabled:
                    email_config.enabled = True
                    updated = True
                if not email_config.auto_sync:
                    email_config.auto_sync = True
                    updated = True

                if updated:
                    db_session.commit()
                    logger.info(f"Updated existing email configuration for user {user_id}")
                    return True, "Email filters updated successfully"
                else:
                    logger.info(f"Existing email configuration already up to date for user {user_id}")
                    return True, "Email filters already configured"
                
        except SQLAlchemyError as e:
            logger.error(f"Database error configuring email filters: {e}")
            db_session.rollback()
            return False, f"Database error configuring email filters: {str(e)}"
        except ValueError as e:
            logger.error(f"Invalid data while configuring email filters: {e}")
            db_session.rollback()
            return False, f"Invalid data: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error configuring email filters: {e}")
            db_session.rollback()
            return False, f"Unexpected error configuring email filters: {str(e)}"
        finally:
            self.db.close_session(db_session)

    
    def trigger_initial_sync(self, user_id: int, account: Account) -> Tuple[bool, str, dict]:
        """
        Trigger an initial Gmail sync for the newly added account.
        
        Args:
            user_id: User ID
            account: Account object that was just created
            
        Returns:
            Tuple of (success, message, stats)
        """
        # Input validation
        if not isinstance(user_id, int) or user_id <= 0:
            return False, "Invalid user_id: must be a positive integer", {}
        
        if not account:
            return False, "Account object is required", {}
        
        if not hasattr(account, 'account_number'):
            return False, "Invalid account object: missing account_number", {}
        
        try:
            logger.info(f"Triggering initial Gmail sync for account {account.account_number}")
            
            # Use the Gmail service to sync messages
            success, message, stats = self.gmail_service.sync_gmail_messages(user_id, account.account_number)

            # Log outcome safely without assuming stats keys exist
            if success:
                logger.info(f"Initial sync completed for account {account.account_number}: {message}")
            else:
                logger.warning(f"Initial sync failed for account {account.account_number}: {message}")

            if isinstance(stats, dict) and stats:
                found = stats.get('messages_found')
                processed = stats.get('messages_processed')
                total_time = stats.get('total_time_taken')
                if found is not None and processed is not None:
                    logger.info(f"Found {found} emails, processed {processed}")
                if total_time is not None:
                    logger.info(f"Total time taken: {total_time} seconds")

            return success, message, stats
            
        except ValueError as e:
            logger.error(f"Invalid data while triggering initial sync: {e}")
            return False, f"Invalid data: {str(e)}", {}
        except Exception as e:
            logger.error(f"Unexpected error triggering initial sync: {e}")
            return False, f"Unexpected error triggering initial sync: {str(e)}", {}
    
    def process_new_account(self, user_id: int, account: Account) -> dict:
        """
        Complete process for handling a newly created account:
        1. Configure email filters based on bank data
        2. Trigger initial Gmail sync
        
        Args:
            user_id: User ID
            account: Account object that was just created
            
        Returns:
            Dictionary with results of both operations
        """
        # Input validation
        if not isinstance(user_id, int) or user_id <= 0:
            return {
                'filters_configured': False,
                'sync_triggered': False,
                'messages': ['Invalid user_id: must be a positive integer'],
                'sync_stats': {}
            }
        
        if not account:
            return {
                'filters_configured': False,
                'sync_triggered': False,
                'messages': ['Account object is required'],
                'sync_stats': {}
            }
        
        results = {
            'filters_configured': False,
            'sync_triggered': False,
            'messages': [],
            'sync_stats': {}
        }
        
        try:
            # Step 1: Configure email filters
            filter_success, filter_message = self.create_sync(user_id, account)
            results['filters_configured'] = filter_success
            results['messages'].append(f"Email filters: {filter_message}")
            
            if filter_success:
                logger.info(f"Email filters configured successfully for account {account.account_number}")
                # Step 2: Trigger initial sync (only if filters were configured successfully)
                sync_success, sync_message, sync_stats = self.trigger_initial_sync(user_id, account)
                results['sync_triggered'] = sync_success
                results['messages'].append(f"Initial sync: {sync_message}")
                results['sync_stats'] = sync_stats
                
                if sync_success and sync_stats.get('messages_found', 0) > 0:
                    results['messages'].append(f"Found {sync_stats['messages_found']} emails, processed {sync_stats['messages_processed']}")
            
        except Exception as e:
            logger.error(f"Error processing new account: {e}")
            results['messages'].append(f"Error: {str(e)}")
        
        return results
    
    def get_bank_email_preview(self, bank_id: int) -> dict:
        """
        Get a preview of what email filters would be configured for a bank.
        
        Args:
            bank_id: Bank ID
            
        Returns:
            Dictionary with preview information
        """
        # Input validation
        if not isinstance(bank_id, int) or bank_id <= 0:
            return {'error': 'Invalid bank_id: must be a positive integer'}
        
        db_session = self.db.get_session()
        
        try:
            bank = db_session.query(Bank).filter_by(id=bank_id).first()
            if not bank:
                return {'error': 'Bank not found'}
            

            # Normalize possible comma-separated values into unique lists
            bank_senders = []
            if bank.email_address:
                bank_senders = [s.strip() for s in str(bank.email_address).split(',') if s.strip()]
            bank_subjects = []
            if bank.email_subjects:
                bank_subjects = [s.strip() for s in str(bank.email_subjects).split(',') if s.strip()]

            sender_filters = sorted(set(bank_senders))
            subject_filters = sorted(set(bank_subjects))

            return {
                'bank_name': bank.name,
                'sender_filters': sender_filters,
                'subject_filters': subject_filters,
                'estimated_filters': len(sender_filters) + len(subject_filters)
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting bank email preview: {e}")
            return {'error': f'Database error: {str(e)}'}
        except ValueError as e:
            logger.error(f"Invalid data while getting bank email preview: {e}")
            return {'error': f'Invalid data: {str(e)}'}
        except Exception as e:
            logger.error(f"Unexpected error getting bank email preview: {e}")
            return {'error': f'Unexpected error: {str(e)}'}
        finally:
            self.db.close_session(db_session)