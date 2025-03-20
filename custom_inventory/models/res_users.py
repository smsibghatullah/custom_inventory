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
