from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    

    tag_ids = fields.Many2many(
        'crm.tag',
        'res_users_crm_tag_rel',
        'user_id',
        'tag_id',
        string='Tags',
        help='Select the Tags associated with this user',
        domain="[('company_id', 'in', company_ids)]",
    )

    category_ids = fields.One2many(
        'sku.type.master',  
        'user_id', 
        string='Categories',
        help='Select the Categories associated with this company',
        domain="[('company_id', 'in', company_ids)]",
    )

    @api.onchange('company_ids')
    def _onchange_company_ids(self):
        """Remove only the tags and categories that do not match the selected companies."""
        if self.company_ids:
            company_ids = self.company_ids.ids

            valid_tags = self.env['crm.tag'].search([('company_id', 'in', company_ids)]).ids
            valid_categories = self.env['sku.type.master'].search([('company_id', 'in', company_ids)]).ids

            self.tag_ids = [(6, 0, list(set(self.tag_ids.ids) & set(valid_tags)))]

            self.category_ids = [(6, 0, list(set(self.category_ids.ids) & set(valid_categories)))]
               
