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

    sku_category_ids = fields.Many2many(
        'sku.type.master',
        'res_users_sku_category_rel',
        'user_id',
        'sku_type_id',
        string='Categories',
        help='Select the SKU Categories associated with this user',
        domain="[('company_id', 'in', company_ids)]",
    )


    @api.onchange('company_ids')
    def _onchange_company_ids(self):
        """Remove only tags and categories related to removed companies."""
        previous_companies = self._origin.company_ids.ids if self._origin else []
        current_companies = self.company_ids.ids
        removed_companies = list(set(previous_companies) - set(current_companies))
        print("Removed Companies:", removed_companies)

        if removed_companies:
            removed_tags = self.env['crm.tag'].search([('company_id', 'in', removed_companies)]).ids
            removed_categories = self.env['sku.type.master'].search([('company_id', 'in', removed_companies)]).ids
            self.tag_ids = [(3, tag_id) for tag_id in removed_tags if tag_id in self.tag_ids.ids]
            self.sku_category_ids = [(2, category.id) for category in self.sku_category_ids if
                                 category.company_id.id in removed_companies]


class ResPartner(models.Model):
    _inherit = 'res.partner'

    brand_ids = fields.Many2many(
        'brand.master',
        'res_partner_brand_rel_we',
        string='Brands',
        domain="[('company_id', '=', current_company_id)]",
        help='Select the Brands'
    )

    current_company_id = fields.Many2one(
        'res.company',
        compute='_compute_current_company',
        store=False
    )

    @api.depends('company_id')
    def _compute_current_company(self):
        for record in self:
            record.current_company_id = self.env.company

 


               

 


               
