from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import ReportController

class CustomReportController(ReportController):

    @http.route(['/report/download'], type='http', auth="user")
    def report_download(self, data, token):
        import json
        import werkzeug

        request_content = json.loads(data)
        url, report_type = request_content[0], request_content[1]

        if report_type in ['qweb-pdf', 'qweb-text']:
            reportname = url.split('/report/pdf/')[1].split('?')[0]
            docids = reportname.split('/')[-1]
            model = reportname.split('/')[0]

            record = request.env[model].browse(int(docids))
            filename = ''

            # Customize file name based on model
            if model == 'sale.order':
                filename = record.name
            elif model == 'account.invoice':
                filename = record.number or 'invoice'
            elif model == 'purchase.order':
                filename = record.name
            else:
                filename = model.replace('.', '_') + '_' + str(record.id)

            filename = filename.replace('/', '_') + '.pdf'

            response = super(CustomReportController, self).report_download(data, token)
            response.headers['Content-Disposition'] = 'attachment; filename=%s' % filename
            return response
