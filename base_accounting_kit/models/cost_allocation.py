from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError


import logging
_logger = logging.getLogger(__name__)
class CostAllocationParameter(models.Model):
    _name = 'cost.allocation.parameter'
    _description = 'Cost Allocation Parameters'

    company_id = fields.Many2one(
        'res.company', 
        string='Record Company', 
        default=lambda self: self.env.company
    )

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

    destination_company_ids = fields.One2many(
        'cost.allocation.destination', 
        'parameter_id',
        string='Destination Companies'
    )

class CostAllocationDestination(models.Model):
    _name = 'cost.allocation.destination'
    _description = 'Cost Allocation Destination Companies'

    parameter_id = fields.Many2one('cost.allocation.parameter', string='Parameter')

    parent_source_company_id = fields.Many2one(
        'res.company',
        string='Source Company Reference',
        related='parameter_id.source_company_id',
        store=False,
        readonly=True
    )
    
    destination_company_id = fields.Many2one(
        'res.company', 
        string='Company',
        required=True,
    )
    destination_debit_account_id = fields.Many2one(
        'account.account',
        string='Debit Account',
        required=True,
        domain="[('company_id', '=', destination_company_id)]"
    )
    destination_credit_account_id = fields.Many2one(
        'account.account', 
        string='Credit Account',
        required=True,
        domain="[('company_id', '=', destination_company_id)]"
    )
    destination_journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        domain="[('company_id', '=', destination_company_id)]"
    )

    @api.onchange('destination_company_id')
    def _onchange_destination_company(self):
        self.destination_debit_account_id = False
        self.destination_credit_account_id = False  
        self.destination_journal_id = False


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_open_cost_allocation(self):
        if self.move_type != "in_invoice":
            raise ValidationError(
                _("This action is only used for bills")
            )
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cost Allocation',
            'res_model': 'cost.allocation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_source_bill_id': self.id}
        }
    

class CostAllocationWizard(models.TransientModel):
    _name = 'cost.allocation.wizard'
    _description = 'Cost Allocation Wizard'

    source_bill_id = fields.Many2one('account.move', string='Source Bill')
    source_company_id = fields.Many2one('res.company', string='Source Company', compute='_compute_source_company', store=True)
    gross_amount = fields.Float(string='Total Amount', readonly=True)
    source_company_amount = fields.Float(string='Amount allocated to Source Company', compute='_compute_source_amount', readonly=True)
    allocation_date = fields.Date(string='Allocation Date', default=fields.Date.today)
    
    allocation_line_ids = fields.One2many(
        'cost.allocation.wizard.line', 
        'wizard_id', 
        string='Allocation Lines'
    )

    @api.depends('source_bill_id')
    def _compute_source_company(self):
        for wizard in self:
            wizard.source_company_id = wizard.source_bill_id.company_id

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if self._context.get('default_source_bill_id'):
            bill = self.env['account.move'].browse(self._context['default_source_bill_id'])
            res['gross_amount'] = bill.amount_total
        return res

    @api.depends('gross_amount', 'allocation_line_ids.amount')
    def _compute_source_amount(self):
        for wizard in self:
            total_allocated = sum(wizard.allocation_line_ids.mapped('amount'))
            wizard.source_company_amount = wizard.gross_amount - total_allocated
            _logger.info("=== wizard.source_company_amount %s", wizard.source_company_amount)    

    def action_post_allocation(self):
        _logger.info("=== CALLING POST ALLOCATIO N")
        
        self._compute_source_amount()

        total_destination_amount = sum(self.allocation_line_ids.mapped('amount'))
        _logger.info("=== total_destination_amount %s", total_destination_amount)
        source_company_allocated_amount = self.gross_amount - total_destination_amount
        _logger.info("=== source_company_allocated_amount %s", source_company_allocated_amount)
        source_mapping = self.env['cost.allocation.parameter'].search([
            ('source_company_id', '=', self.source_company_id.id)
        ], limit=1)
        
        if not source_mapping:
            raise UserError(f"No cost allocation mapping found for {self.source_company_id.name}")

        source_move_vals = {
            'date': self.allocation_date,
            'journal_id': source_mapping.source_journal_id.id,
            'company_id': self.source_company_id.id,
            'ref': f'Cost Allocation: {self.source_bill_id.name}',
            'line_ids': [
                (0, 0, {
                    'account_id': source_mapping.source_debit_account_id.id,
                    'debit': source_company_allocated_amount,  # CHANGED: Use source_company_amount directly
                    'credit': 0,
                    'name': f'Cost Allocation from {self.source_bill_id.name}',
                }),
                (0, 0, {
                    'account_id': source_mapping.source_credit_account_id.id,
                    'debit': 0,
                    'credit': source_company_allocated_amount,  # CHANGED: Use source_company_amount directly
                    'name': f'Cost Allocation from {self.source_bill_id.name}',
                }),
            ]
        }


        source_move = self.env['account.move'].create(source_move_vals)
        source_move.action_post()

        for line in self.allocation_line_ids:
            if line.amount > 0:
                dest_mapping = self.env['cost.allocation.parameter'].search([
                    ('destination_company_ids.destination_company_id', '=', line.destination_company_id.id)
                ], limit=1)
                
                if not dest_mapping:
                    raise UserError(f"No cost allocation mapping found for destination company {line.destination_company_id.name}")
                
                dest_company_line = dest_mapping.destination_company_ids.filtered(
                    lambda x: x.destination_company_id == line.destination_company_id
                )
                
                if not dest_company_line:
                    raise UserError(f"No journal configured for destination company {line.destination_company_id.name}")
                
                dest_move_vals = {
                    'date': self.allocation_date,
                    'journal_id': dest_company_line.destination_journal_id.id,
                    'company_id': line.destination_company_id.id,
                    'ref': f'Cost Allocation: {self.source_bill_id.name}',
                    'line_ids': [
                        (0, 0, {
                            'account_id': line.dest_debit_account_id.id,
                            'debit': line.amount,
                            'credit': 0,
                            'name': f'Cost Allocation from {self.source_bill_id.name}',
                        }),
                        (0, 0, {
                            'account_id': dest_company_line.destination_credit_account_id.id,
                            'debit': 0,
                            'credit': line.amount,
                            'name': f'Cost Allocation from {self.source_bill_id.name}',
                        }),
                    ]
                }
                dest_move = self.env['account.move'].with_company(line.destination_company_id.id).sudo().create(dest_move_vals)
                dest_move.action_post()
                _logger.info("=== Destination Journal Created: %s", dest_move.name)

        return {'type': 'ir.actions.act_window_close'}
    

class CostAllocationWizardLine(models.TransientModel):
    _name = 'cost.allocation.wizard.line'
    _description = 'Cost Allocation Wizard Lines'

    wizard_id = fields.Many2one('cost.allocation.wizard', string='Wizard')
    destination_company_id = fields.Many2one('res.company', string='Destination Company', required=True, domain="[('id', 'in', available_company_ids)]")
    dest_debit_account_id = fields.Many2one(
        'account.account', 
        string='Payable Account',
        domain="[('id', 'in', available_debit_account_ids)]"
    )
    percentage = fields.Float(string='Percentage', required=True)
    amount = fields.Float(string='Amount', compute='_compute_amount', readonly=True, store=False)
    
    dest_journal_id = fields.Many2one('account.journal', string='Journal', readonly=True)

    available_company_ids = fields.Many2many(
        'res.company', 
        compute='_compute_available_companies'
    )
    available_debit_account_ids = fields.Many2many('account.account', compute='_compute_available_accounts')

    @api.depends('percentage', 'wizard_id.gross_amount')
    def _compute_amount(self):
        for line in self:
            if line.wizard_id and line.wizard_id.gross_amount and line.percentage:
                line.amount = (line.wizard_id.gross_amount * line.percentage) / 100
            else:
                line.amount = 0.0

    @api.depends('wizard_id.source_company_id')
    def _compute_available_companies(self):
        for line in self:
            if line.wizard_id.source_company_id:
                mapping = self.env['cost.allocation.parameter'].search([
                    ('source_company_id', '=', line.wizard_id.source_company_id.id)
                ], limit=1)
                
                if mapping:
                    destination_companies = mapping.destination_company_ids.mapped('destination_company_id')
                    line.available_company_ids = destination_companies
                else:
                    line.available_company_ids = False
            else:
                line.available_company_ids = False

    @api.depends('destination_company_id')
    def _compute_available_accounts(self):
        for line in self:
            if line.destination_company_id and line.wizard_id.source_company_id:
                mapping = self.env['cost.allocation.parameter'].search([
                    ('source_company_id', '=', line.wizard_id.source_company_id.id)
                ], limit=1)
                
                if mapping:
                    filtered_records = mapping.destination_company_ids.filtered(
                        lambda x: x.destination_company_id.id == line.destination_company_id.id
                    )                    
                    debit_accounts = filtered_records.mapped('destination_debit_account_id')
                    
                    line.available_debit_account_ids = debit_accounts
                else:
                    line.available_debit_account_ids = False
            else:
                line.available_debit_account_ids = False

    @api.onchange('dest_debit_account_id')
    def _onchange_dest_debit_account(self):
        if self.dest_debit_account_id and self.destination_company_id and self.wizard_id.source_company_id:
            mapping = self.env['cost.allocation.parameter'].search([
                ('source_company_id', '=', self.wizard_id.source_company_id.id)
            ], limit=1)
            if mapping:
                dest_record = mapping.destination_company_ids.filtered(
                    lambda x: x.destination_company_id.id == self.destination_company_id.id 
                    and x.destination_debit_account_id.id == self.dest_debit_account_id.id
                )
                if dest_record:
                    self.dest_journal_id = dest_record.destination_journal_id

    @api.onchange('percentage', 'wizard_id.gross_amount')
    def _onchange_percentage(self):
        if self.wizard_id.gross_amount and self.percentage:
            self.amount = (self.percentage / 100) * self.wizard_id.gross_amount

