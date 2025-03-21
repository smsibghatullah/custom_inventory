

from odoo import models, fields, api,_
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = "crm.lead"


    brand_id = fields.Many2one(
        'brand.master',
        string='Brand',
         domain="[('company_id', '=', company_id)]",
        help='Select the brand associated with this sale order'
    )

    category_ids = fields.Many2many(
        'sku.type.master',
        'crm_category_rel',
        'product_id',
        'category_id',
        string='Categories',
        domain="[('brand_id', '=', brand_id),('id', 'in', available_category_ids)]",
        help='Select the Categories associated with the selected brand'
    )
    sku_ids = fields.Many2many('product.template', string="SKU")

    available_tag_ids = fields.Many2many(
        'crm.tag',
        compute="_compute_available_tags",
    )
    available_category_ids = fields.Many2many(
        'sku.type.master',
        compute="_compute_available_categories",
    )
    bci_project = fields.Char(string='BCI Project', required=True)
    @api.depends("tag_ids")
    def _compute_available_tags(self):
        for record in self:
            record.available_tag_ids = self.env.user.tag_ids
            print(record.available_tag_ids,"ppppppppppppppppppppppppmubeenpssssssssssssssssssssssssss")
    @api.depends("category_ids")
    def _compute_available_categories(self):
        for record in self:
            record.available_category_ids = self.env.user.category_ids
            print(record.available_tag_ids,"ppppppppppppppppppppppppmubeenpssssssssssssssssssssssssss")



    def _prepare_opportunity_quotation_context(self):
        """ Prepares the context for a new quotation (sale.order) by sharing the values of common fields """
        self.ensure_one()
        context = super(CrmLead, self)._prepare_opportunity_quotation_context()

        context.update({
            'default_brand_id': self.brand_id.id,
            'default_category_ids': [(6, 0, self.category_ids.ids)],
        })
        print("aaaaaaaaaaaaaaaaaaa",self.category_ids.ids)
        print(context)

        return context


