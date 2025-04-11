from odoo import models, fields, api
import base64
import qrcode
from io import BytesIO

class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    field_access_ids = fields.One2many(
        'maintenance.equipment.access', 'equipment_id', string="."
    )

    qr_code_equip = fields.Binary("QR Code", compute="_generate_qr_code")

    def _generate_qr_code(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if qrcode and base64:
                equipment_url = f"{base_url}/equipment/public/{rec.id}"
                
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=3,
                    border=4,
                )
                qr.add_data(equipment_url)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                temp = BytesIO()
                img.save(temp, format="PNG")
                qr_image = base64.b64encode(temp.getvalue())
                rec.qr_code_equip = qr_image



class MaintenanceEquipmentAccess(models.Model):
    _name = 'maintenance.equipment.access'
    _description = "Equipment Field Access"

    equipment_id = fields.Many2one('maintenance.equipment', string="Equipment")
    field_name = fields.Selection(
        selection=lambda self: self._get_equipment_fields(),
        string="Field",
        required=True
    )
    is_public = fields.Boolean(string="Public")
    is_private = fields.Boolean(string="Private")

    @api.model
    def _get_equipment_fields(self):
        """Dynamically fetch all fields from maintenance.equipment."""
        model_fields = self.env['ir.model.fields'].search([
            ('model', '=', 'maintenance.equipment'),
            ('name', 'not in', ['id', 'create_uid', 'create_date', 'write_uid', 'write_date'])
        ])
        return [(field.name, field.field_description) for field in model_fields]


    @api.onchange('is_private')
    def _check_access_private_type(self):
        for record in self:
            if record.is_private:
                record.is_public = False

    @api.onchange('is_public')
    def _check_access_public_type(self):
        for record in self:
            if record.is_public:
                record.is_private = False