from odoo import models, fields, api,_
from collections import defaultdict
from odoo.tools import formatLang
from odoo.exceptions import UserError

class CustomerStatementLine(models.TransientModel):
    _name = 'customer.statement.line'
    _description = 'Customer Statement Line'

    statement_id = fields.Many2one('customer.statement.report', required=True, ondelete='cascade')
    invoice_id = fields.Many2one('account.move')
    date = fields.Date(related='invoice_id.invoice_date', store=True)
    due_date = fields.Date(related='invoice_id.invoice_date_due', store=True)
    invoice_number = fields.Char(related='invoice_id.name', store=True)
    reference = fields.Char(related='invoice_id.ref', store=True)
    contact = fields.Many2one(related='invoice_id.partner_id', store=True)
    total = fields.Monetary(related='invoice_id.amount_total', store=True)
    balance = fields.Monetary(related='invoice_id.amount_residual', store=True)
    currency_id = fields.Many2one(related='invoice_id.currency_id', store=True)
    status = fields.Selection(related='invoice_id.payment_state', store=True)
    company_id = fields.Many2one('res.company', compute='_compute_company', store=True, string="Company")
    is_selected = fields.Boolean(string="Select")

    @api.depends('invoice_id')
    def _compute_company(self):
        for rec in self:
            rec.company_id = rec.invoice_id.company_id


class CustomerStatementReport(models.TransientModel):
    _name = 'customer.statement.report'
    _description = 'Customer Statement Report Wizard'

    customer_id = fields.Many2one('res.partner', string="Customer")
    start_date = fields.Date()
    end_date = fields.Date()
    company_ids = fields.Many2many('res.company', string="Companies")
    status = fields.Selection([
        ('paid', 'Paid'),
        ('not_paid', 'Not Paid'),
        ('partial', 'Partially Paid'),
        ('all', 'All'),
    ], default='all')
    statement_lines = fields.One2many('customer.statement.line', 'statement_id', string="Statement Lines")
    company_lines_html = fields.Html(string="Statement By Company", compute="_compute_company_lines_html", sanitize=False)
    has_statement_lines = fields.Boolean(compute="_compute_has_statement_lines",default=False)

    def _compute_has_statement_lines(self):
        for record in self:
            print(len(record.statement_lines),"===================================================len(record.statement_lines)")
            record.has_statement_lines =False if len(record.statement_lines) == 0  else True

    def action_generate_statement(self):
        domain = [('move_type', 'in', ['out_invoice']), ('state', '=', 'posted')]

        if self.customer_id:
            domain.append(('partner_id', '=', self.customer_id.id))
        if self.start_date:
            domain.append(('invoice_date', '>=', self.start_date))
        if self.end_date:
            domain.append(('invoice_date', '<=', self.end_date))
        if self.status and self.status != 'all':
            domain.append(('payment_state', '=', self.status))
        if self.company_ids:
            domain.append(('company_id', 'in', self.company_ids.ids))

        invoices = self.env['account.move'].search(domain)

        self.statement_lines = [(5, 0, 0)]
        lines = []
        for inv in invoices:
            lines.append((0, 0, {
                'invoice_id': inv.id,
                'is_selected': False
            }))
        self.statement_lines = lines

    def _compute_company_lines_html(self):
        for rec in self:
            grouped = defaultdict(list)
            for line in rec.statement_lines:
                grouped[line.company_id.name].append(line)

            html = """
                <style>
                    h3 { color: #2C3E50; margin-top: 20px; }
                    table { width: 100%; font-size: 13px; border-collapse: collapse; margin-bottom: 20px; }
                    th, td { border: 1px solid #ccc; padding: 6px; text-align: left; }
                    thead { background-color: #f2f2f2; }
                    input[type="checkbox"] { transform: scale(1.2); }
                </style>
                <div class="customer_statement_html_wrapper">
            """
            for idx, (company, lines) in enumerate(grouped.items()):
                company_class = f"company_select_{idx}"
                html += f"<h3>{company}</h3>"
                html += f"""
                    <table class='table'>
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Due Date</th>
                                <th>Invoice</th>
                                <th>Reference</th>
                                <th>Contact</th>
                                <th>Total</th>
                                <th>Balance</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                for line in lines:
                    checked = 'checked' if line.is_selected else ''
                    html += f"""
                        <tr>
                            <td>{line.date or ''}</td>
                            <td>{line.due_date or ''}</td>
                            <td>{line.invoice_number or ''}</td>
                            <td>{line.reference or ''}</td>
                            <td>{line.contact.name if line.contact else ''}</td>
                            <td>{formatLang(self.env, line.total, currency_obj=line.currency_id)}</td>
                            <td>{formatLang(self.env, line.balance, currency_obj=line.currency_id)}</td>
                            <td>{line.status or ''}</td>
                        </tr>
                    """
                html += "</tbody></table>"

            html += "</div>"

            rec.company_lines_html = html or "<p>No data available.</p>"

    def action_print_statement_pdf(self):
        self.ensure_one()
        if not self.statement_lines:
           raise UserError(_("No customer statement generated. Please generate the customer statement first."))
        return self.env.ref('dynamic_invoice_sale_report.customer_statement_pdf_report_action').report_action(self)

class ReportCustomerStatement(models.AbstractModel):
    _name = 'report.dynamic_invoice_sale_report.customer_statement_report'
    _description = 'Customer Statement Report'

    def _get_report_values(self, docids, data=None):
        statement = self.env['customer.statement.report'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'customer.statement.report',
            'doc': statement,
            'active_company': self.env.company, 
            'formatLang': lambda value, **kw: formatLang(self.env, value, **kw),
        }