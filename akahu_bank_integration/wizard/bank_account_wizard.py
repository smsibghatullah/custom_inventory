from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AccountSetupBankManualConfig(models.TransientModel):
    _inherit = 'account.setup.bank.manual.config'

    akahu_account_ref_id = fields.Many2one(
        'akahu.bank.account',
        string="Account"
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['partner_id'] = self.env.company.partner_id.id

            if vals.get('akahu_account_ref_id'):
                akahu_account = self.env['akahu.all.bank.account'].browse(vals['akahu_account_ref_id'])
                existing = self.env['account.journal'].search([
                    ('bank_acc_number', '=', akahu_account.name)
                ], limit=1)
                if existing:
                    raise ValidationError("This account number already exists in a journal: %s" % existing.name)
                vals['acc_number'] = akahu_account.name
                vals['new_journal_name'] = akahu_account.name

            if not vals.get('bank_id') and vals.get('bank_bic'):
                vals['bank_id'] = self.env['res.bank'].search([('bic', '=', vals['bank_bic'])], limit=1).id \
                                  or self.env['res.bank'].create({'name': vals['bank_bic'], 'bic': vals['bank_bic']}).id

        return super().create(vals_list)

  