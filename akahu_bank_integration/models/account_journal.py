from odoo import models, fields, api
import requests
import logging
from datetime import datetime
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = 'account.journal'

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

    def action_configure_bank_accounts(self):
        headers = {
            'Authorization': 'Bearer user_token_cm9y2t9w2000208l1c7ts2m2i',
            'X-Akahu-Id': 'app_token_cm9y2t9w2000108l1bdnc7mza'
        }

        response = requests.get('https://api.akahu.io/v1/accounts', headers=headers)
        matched_record_ids = []
        AkahuAccount = self.env['akahu.bank.account']

        if response.status_code == 200:
            accounts = response.json().get('items', [])

            for account_data in accounts:
                if account_data.get('name') != self.name:
                    continue  

                vals = {
                    'name': account_data.get('formatted_account'),
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

                match = AkahuAccount.search([('name', '=', self.name)], limit=1)
                if match:
                    match.write(vals)
                    matched_record_ids.append(match.id)
                else:
                    new_rec = AkahuAccount.create(vals)
                    matched_record_ids.append(new_rec.id)

        else:
            _logger.error("Failed to fetch Akahu accounts: %s", response.text)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Bank Accounts',
            'res_model': 'akahu.bank.account',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', matched_record_ids)],
            'target': 'current',
        }


    def action_configure_bank_accounts_transactions(self):
        AkahuAccount = self.env['akahu.bank.account']
        AkahuTransaction = self.env['akahu.transaction']
        TransactionLink = self.env['akahu.transaction.link']
        created_transaction = []

        headers = {
            'Authorization': 'Bearer user_token_cm9y2t9w2000208l1c7ts2m2i',
            'X-Akahu-Id': 'app_token_cm9y2t9w2000108l1bdnc7mza'
        }

        response = requests.get('https://api.akahu.io/v1/transactions', headers=headers)

        if response.status_code == 200:
            transactions = response.json()

            for trans_data in transactions.get('items', []):
                account_id = trans_data.get('_account')
                matched_account = AkahuAccount.search([('name', '=', self.name)], limit=1)

                if not matched_account or trans_data.get('_account') != matched_account.akahu_account_id:
                    continue 

                transaction_link = TransactionLink.search([('akahu_account_id', '=', matched_account.id)], limit=1)
                if not transaction_link:
                    transaction_link = TransactionLink.create({
                        'name': f'{matched_account.name}',
                        'akahu_account_id': matched_account.id,
                    })
                
                reference = trans_data.get('_id')
                transaction = AkahuTransaction.search([('reference', '=', reference),('akahu_account_id', '=', matched_account.akahu_account_id)], limit=1)
                print(matched_account.akahu_account_id,"ppppppppssssssssssssddddddddddfffffffffffggggggg",matched_account.name,transaction)

                if not transaction:
                    transaction_type = 'INCOME' if trans_data.get('type') == 'credit' else 'PAYMENT'

                    transaction = AkahuTransaction.create({
                        'name': trans_data.get('description'),
                        'amount': trans_data.get('amount'),
                        'amount_due': trans_data.get('amount'),  
                        'amount_paid': 0.0,
                        'date': self.parse_datetime_safe(trans_data.get('date')),
                        'created_at': self.parse_datetime_safe(trans_data.get('created_at')),
                        'updated_at': self.parse_datetime_safe(trans_data.get('updated_at')),
                        'balance': trans_data.get('balance'),
                        'type': transaction_type,
                        'reference': reference,
                        'hash': trans_data.get('hash'),
                        'akahu_account_id': matched_account.akahu_account_id,
                        'akahu_user_id': trans_data.get('_user'),
                        'akahu_connection_id': trans_data.get('_connection'),
                        'description': trans_data.get('description'),
                        'particulars': trans_data.get('meta', {}).get('particulars'),
                        'code': trans_data.get('meta', {}).get('code'),
                        'other_account': trans_data.get('meta', {}).get('other_account'),
                        'transaction_link_id':transaction_link.id
                    })

                transaction_link.write({
                        'invoice_ids': [(5, 0, 0)]
                    })  
                print(transaction.id,"vvvvvvvvvvvvvvvvvvvvvvvvvvxxxxcccccccccccccccccccc")  
                created_transaction.append(transaction_link.id)

                if transaction.id not in transaction_link.transaction_ids.ids:
                    transaction_link.write({
                        'transaction_ids': [(4, transaction.id)],
                        'all_transaction_ids': [(4, transaction.id)],
                    })

            if created_transaction == []:
                raise UserError(f"Account {self.name} has no transactions.")

            return {
                'type': 'ir.actions.act_window',
                'name': 'Transaction Link',
                'res_model': 'akahu.transaction.link',
                'view_mode': 'form',
                'res_id': transaction_link.id,  
                'target': 'current'
            }

        else:
            _logger.error('Failed to fetch transactions: %s', response.text)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Error',
                'res_model': 'ir.ui.view',
                'view_mode': 'form',
                'view_id': False,
                'target': 'new'
            }



class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    def action_configure_bank_accounts_transactions(self):
        AkahuAccount = self.env['akahu.bank.account']
        AkahuTransaction = self.env['akahu.transaction']
        TransactionLink = self.env['akahu.transaction.link']
        created_transaction = []

        headers = {
            'Authorization': 'Bearer user_token_cm9y2t9w2000208l1c7ts2m2i',
            'X-Akahu-Id': 'app_token_cm9y2t9w2000108l1bdnc7mza'
        }

        response = requests.get('https://api.akahu.io/v1/transactions', headers=headers)

        if response.status_code == 200:
            transactions = response.json()

            for trans_data in transactions.get('items', []):
                account_id = trans_data.get('_account')
                matched_account = AkahuAccount.search([('formatted_account', '=', self.acc_number)], limit=1)

                if not matched_account or trans_data.get('_account') != matched_account.akahu_account_id:
                    continue

                transaction_link = TransactionLink.search([('akahu_account_id', '=', matched_account.id)], limit=1)
                if not transaction_link:
                    transaction_link = TransactionLink.create({
                        'name': f'{matched_account.name}',
                        'akahu_account_id': matched_account.id,
                    })

                reference = trans_data.get('_id')
                transaction = AkahuTransaction.search([
                    ('reference', '=', reference),
                    ('akahu_account_id', '=', matched_account.akahu_account_id)
                ], limit=1)

                if not transaction:
                    transaction_type = 'INCOME' if trans_data.get('type') == 'credit' else 'PAYMENT'

                    transaction = AkahuTransaction.create({
                        'name': trans_data.get('description'),
                        'amount': trans_data.get('amount'),
                        'amount_due': trans_data.get('amount'),
                        'amount_paid': 0.0,
                        'date': self._parse_datetime_safe(trans_data.get('date')),
                        'created_at': self._parse_datetime_safe(trans_data.get('created_at')),
                        'updated_at': self._parse_datetime_safe(trans_data.get('updated_at')),
                        'balance': trans_data.get('balance'),
                        'type': transaction_type,
                        'reference': reference,
                        'hash': trans_data.get('hash'),
                        'akahu_account_id': matched_account.akahu_account_id,
                        'akahu_user_id': trans_data.get('_user'),
                        'akahu_connection_id': trans_data.get('_connection'),
                        'description': trans_data.get('description'),
                        'particulars': trans_data.get('meta', {}).get('particulars'),
                        'code': trans_data.get('meta', {}).get('code'),
                        'other_account': trans_data.get('meta', {}).get('other_account'),
                        'transaction_link_id': transaction_link.id
                    })

                transaction_link.write({
                    'invoice_ids': [(5, 0, 0)]
                })

                created_transaction.append(transaction_link.id)

                if transaction.id not in transaction_link.transaction_ids.ids:
                    transaction_link.write({
                        'transaction_ids': [(4, transaction.id)],
                        'all_transaction_ids': [(4, transaction.id)],
                    })

            if not created_transaction:
                raise UserError(f"Account {self.acc_number} has no transactions.")

            return {
                'type': 'ir.actions.act_window',
                'name': 'Transaction Link',
                'res_model': 'akahu.transaction.link',
                'view_mode': 'form',
                'res_id': transaction_link.id,
                'target': 'current'
            }

        else:
            _logger.error('Failed to fetch transactions: %s', response.text)
            raise UserError("Failed to fetch transactions from Akahu.")

    def _parse_datetime_safe(self, date_str):
        try:
            return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        except Exception:
            return False