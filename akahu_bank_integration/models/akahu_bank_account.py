from odoo import models, fields, api
import requests
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class AkahuBankAccount(models.Model):
    _name = 'akahu.bank.account'
    _description = 'Akahu Bank Account'

    name = fields.Char(string="Account Name")
    akahu_account_id = fields.Char(string="Akahu Account ID")
    formatted_account = fields.Char(string="Formatted Account")
    balance_currency = fields.Char(string="Currency")
    balance_current = fields.Float(string="Current Balance")
    balance_available = fields.Float(string="Available Balance")
    balance_overdrawn = fields.Boolean(string="Overdrawn")
    status = fields.Char(string="Status")
    type = fields.Char(string="Account Type")
    holder_name = fields.Char(string="Holder")
    refreshed_balance = fields.Datetime(string="Balance Refreshed At")
    refreshed_meta = fields.Datetime(string="Meta Refreshed At")
    refreshed_transactions = fields.Datetime(string="Transactions Refreshed At")
    refreshed_party = fields.Datetime(string="Party Refreshed At")
    authorisation_id = fields.Char(string="Authorisation ID")
    credentials_id = fields.Char(string="Credentials ID")
    connection_id = fields.Char(string="Connection ID")
    connection_name = fields.Char(string="Connection Name")
    connection_logo = fields.Char(string="Connection Logo")
    attributes = fields.Char(string="Attributes (CSV)")
    last_refresh = fields.Datetime(string="Last Refreshed At")

    @staticmethod
    def parse_datetime_safe(value):
        """Parse ISO datetime string safely, return None if value is None or malformed."""
        if value:
            try:
                return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ')
            except ValueError:
                try:
                    return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')
                except ValueError:
                    _logger.warning("Invalid datetime format: %s", value)
        return None

    def sync_bank_accounts(self):
            """Sync only the current record with the matching API account, then refresh view."""
            headers = {
                'Authorization': 'Bearer user_token_cm9y2t9w2000208l1c7ts2m2i',
                'X-Akahu-Id': 'app_token_cm9y2t9w2000108l1bdnc7mza'
            }

            response = requests.get('https://api.akahu.io/v1/accounts', headers=headers)
            if response.status_code == 200:
                accounts = response.json().get('items', [])
                for account_data in accounts:
                    if account_data.get('name') != self.name:
                        continue  

                    vals = {
                        'akahu_account_id': account_data.get('_id'),
                        'formatted_account': account_data.get('formatted_account'),
                        'type': account_data.get('type'),
                        'status': account_data.get('status'),
                        'balance_currency': account_data['balance'].get('currency'),
                        'balance_current': account_data['balance'].get('current'),
                        'balance_available': account_data['balance'].get('available'),
                        'balance_overdrawn': account_data['balance'].get('overdrawn'),
                        'holder_name': account_data['meta'].get('holder'),
                        'authorisation_id': account_data.get('_authorisation'),
                        'credentials_id': account_data.get('_credentials'),
                        'connection_id': account_data['connection'].get('_id'),
                        'connection_name': account_data['connection'].get('name'),
                        'connection_logo': account_data['connection'].get('logo'),
                        'attributes': ','.join(account_data.get('attributes', [])),
                        'refreshed_balance': self.parse_datetime_safe(account_data['refreshed'].get('balance')),
                        'refreshed_meta': self.parse_datetime_safe(account_data['refreshed'].get('meta')),
                        'refreshed_transactions': self.parse_datetime_safe(account_data['refreshed'].get('transactions')),
                        'refreshed_party': self.parse_datetime_safe(account_data['refreshed'].get('party')),
                        'last_refresh':datetime.now()
                    }

                    self.write(vals)
                    break 
            else:
                _logger.error("Failed to fetch Akahu bank accounts: %s", response.text)

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'akahu.bank.account',
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'current',
            }

class AkahuAllBankAccount(models.Model):
    _name = 'akahu.all.bank.account'
    _description = 'Akahu Bank Account'

    name = fields.Char(string="Account Name")
    akahu_account_id = fields.Char(string="Akahu Account ID")
    formatted_account = fields.Char(string="Formatted Account")
    balance_currency = fields.Char(string="Currency")
    balance_current = fields.Float(string="Current Balance")
    balance_available = fields.Float(string="Available Balance")
    balance_overdrawn = fields.Boolean(string="Overdrawn")
    status = fields.Char(string="Status")
    type = fields.Char(string="Account Type")
    holder_name = fields.Char(string="Holder")
    refreshed_balance = fields.Datetime(string="Balance Refreshed At")
    refreshed_meta = fields.Datetime(string="Meta Refreshed At")
    refreshed_transactions = fields.Datetime(string="Transactions Refreshed At")
    refreshed_party = fields.Datetime(string="Party Refreshed At")
    authorisation_id = fields.Char(string="Authorisation ID")
    credentials_id = fields.Char(string="Credentials ID")
    connection_id = fields.Char(string="Connection ID")
    connection_name = fields.Char(string="Connection Name")
    connection_logo = fields.Char(string="Connection Logo")
    attributes = fields.Char(string="Attributes (CSV)")
    last_refresh = fields.Datetime(string="Last Refreshed At")

    @staticmethod
    def parse_datetime_safe(value):
        """Parse ISO datetime string safely, return None if value is None or malformed."""
        if value:
            try:
                return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ')
            except ValueError:
                try:
                    return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')
                except ValueError:
                    _logger.warning("Invalid datetime format: %s", value)
        return None

    def cron_sync_all_accounts(self):
        headers = {
            'Authorization': 'Bearer user_token_cm9y2t9w2000208l1c7ts2m2i',
            'X-Akahu-Id': 'app_token_cm9y2t9w2000108l1bdnc7mza'
        }

        response = requests.get('https://api.akahu.io/v1/accounts', headers=headers)
        if response.status_code == 200:
            accounts = response.json().get('items', [])
            for account_data in accounts:
                akahu_account_id = account_data.get('_id')
                
                existing = self.env['akahu.all.bank.account'].search([
                    ('akahu_account_id', '=', akahu_account_id)
                ], limit=1)

                vals = {
                    'name': account_data.get('formatted_account'),
                    'akahu_account_id': akahu_account_id,
                    'formatted_account': account_data.get('formatted_account'),
                    'type': account_data.get('type'),
                    'status': account_data.get('status'),
                    'balance_currency': account_data['balance'].get('currency'),
                    'balance_current': account_data['balance'].get('current'),
                    'balance_available': account_data['balance'].get('available'),
                    'balance_overdrawn': account_data['balance'].get('overdrawn'),
                    'holder_name': account_data['meta'].get('holder'),
                    'authorisation_id': account_data.get('_authorisation'),
                    'credentials_id': account_data.get('_credentials'),
                    'connection_id': account_data['connection'].get('_id'),
                    'connection_name': account_data['connection'].get('name'),
                    'connection_logo': account_data['connection'].get('logo'),
                    'attributes': ','.join(account_data.get('attributes', [])),
                    'refreshed_balance': self.parse_datetime_safe(account_data['refreshed'].get('balance')),
                    'refreshed_meta': self.parse_datetime_safe(account_data['refreshed'].get('meta')),
                    'refreshed_transactions': self.parse_datetime_safe(account_data['refreshed'].get('transactions')),
                    'refreshed_party': self.parse_datetime_safe(account_data['refreshed'].get('party')),
                    'last_refresh': datetime.now()
                }

                if existing:
                    existing.write(vals) 
                else:
                    self.create(vals)     
        else:
            _logger.error("Failed to fetch Akahu bank accounts: %s", response.text)
