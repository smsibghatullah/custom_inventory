from odoo import models, fields, api

class TransactionCommentWizard(models.TransientModel):
    _name = 'transaction.comment.wizard'
    _description = 'Transaction Comment Wizard'

    transaction_id = fields.Many2one('akahu.transaction', string='Transaction', required=True)
    amount = fields.Monetary(string='Amount', readonly=True)
    comment = fields.Text(string='Comment', required=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    currency_id = fields.Many2one('res.currency', readonly=True)
    comment_line_ids = fields.One2many(
        'transaction.comment.line',
        compute='_compute_comment_lines',
        string='Previous Comments',
    )

    @api.depends('transaction_id')
    def _compute_comment_lines(self):
        for wizard in self:
            wizard.comment_line_ids = self.env['transaction.comment.line'].search([
                ('transaction_id', '=', wizard.transaction_id.id)
            ], order='create_date desc')

    def action_save_comment(self):
        for wizard in self:
            transaction = wizard.transaction_id

            self.env['transaction.comment.line'].create({
                'transaction_id': transaction.id,
                'comment': wizard.comment,
                'amount': wizard.amount,
                'attachment_ids': [(6, 0, wizard.attachment_ids.ids)],
                'currency_id': wizard.currency_id.id or transaction.env.company.currency_id.id,
            })

            body = f"New Comment Added: {wizard.comment}\nAmount: {wizard.amount}"
            transaction.message_post(
                body=body,
                attachment_ids=wizard.attachment_ids.ids,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )


        return {'type': 'ir.actions.act_window_close'}
