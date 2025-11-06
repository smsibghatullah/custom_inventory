from odoo import models, fields, api

class CostAllocationParameter(models.Model):
    _name = 'cost.allocation.parameter'
    _description = 'Cost Allocation Parameters'

    # SOURCE COMPANY SECTION (Single Company)
    source_company_id = fields.Many2one(
        'res.company', 
        string='Company',
        required=True
    )
    source_debit_account_id = fields.Many2one(
        'account.account',
        string='Debit Account',
        required=True,
        domain="[('company_id', '=', source_company_id), ('account_type', '=', 'asset_receivable')]"
    )
    source_credit_account_id = fields.Many2one(
        'account.account', 
        string='Credit Account',
        required=True,
        domain="[('company_id', '=', source_company_id), ('account_type', 'in', ['expense', 'expense_depreciation', 'expense_direct_cost'])]"
    )
    source_journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        domain="[('company_id', '=', source_company_id), ('type', '=', 'general')]"
    )

    # DESTINATION COMPANIES SECTION (Multiple Companies)
    destination_company_ids = fields.One2many(
        'cost.allocation.destination', 
        'parameter_id',
    )

class CostAllocationDestination(models.Model):
    _name = 'cost.allocation.destination'
    _description = 'Cost Allocation Destination Companies'

    parameter_id = fields.Many2one('cost.allocation.parameter', string='Parameter')
    
    # DESTINATION COMPANY FIELDS
    destination_company_id = fields.Many2one(
        'res.company', 
        string='Company',
        required=True
    )
    destination_debit_account_id = fields.Many2one(
        'account.account',
        string='Debit Account',
        required=True,
        domain="[('company_id', '=', destination_company_id), ('account_type', 'in', ['expense', 'expense_depreciation', 'expense_direct_cost'])]"
    )
    destination_credit_account_id = fields.Many2one(
        'account.account', 
        string='Credit Account',
        required=True,
        domain="[('company_id', '=', destination_company_id), ('account_type', '=', 'liability_payable')]"
    )
    destination_journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        domain="[('company_id', '=', destination_company_id)]"
    )