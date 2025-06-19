from odoo import http
from odoo.http import request

class CustomerStatementController(http.Controller):

    @http.route('/customer_statement/update_line_selection', type='json', auth='user')
    def update_line_selection(self, line_id, is_selected):
        line = request.env['customer.statement.line'].sudo().browse(int(line_id))
        if line.exists():
            line.write({'is_selected': is_selected})
        return {'success': True}
