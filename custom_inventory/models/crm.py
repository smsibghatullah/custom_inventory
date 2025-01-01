

from odoo import models, fields, api,_
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = "crm.lead"


    brand_id = fields.Many2one(
        'brand.master',
        string='Brand',
        help='Select the brand associated with this sale order'
    )

    sku_ids = fields.Many2many(
        'sku.type.master',
        'crm_sku_rel',
        'product_id',
        'sku_id',
        string='Categories',
        domain="[('brand_id', '=', brand_id)]",
        help='Select the Categories associated with the selected brand'
    )


    def _prepare_opportunity_quotation_context(self):
        """ Prepares the context for a new quotation (sale.order) by sharing the values of common fields """
        self.ensure_one()
        context = super(CrmLead, self)._prepare_opportunity_quotation_context()

        context.update({
            'default_brand_id': self.brand_id.id,
            'default_sku_ids': [(6, 0, self.sku_ids.ids)],
        })
        print("aaaaaaaaaaaaaaaaaaa")
        print(context)

        return context


