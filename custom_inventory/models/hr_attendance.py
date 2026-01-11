from odoo import models, fields, api
from odoo.addons.resource.models.utils import Intervals
from odoo.tools.float_utils import float_round
from pytz import timezone
from odoo.http import content_disposition
import csv
import io
from datetime import datetime
import base64

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    break_time = fields.Selection(
        selection=[
            ('15', '15 Minutes'),
            ('30', '30 Minutes'),
            ('45', '45 Minutes'),
            ('60', '60 Minutes'),
        ],
        string='Break Duration'
    )

    date_time = fields.Datetime(
        string='Date',
        help='The date on which the break was taken.'
    )

    status = fields.Selection(
        selection=[
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
        ],
        string='Status',
        default='submitted'
    )

    work_name = fields.Char(
        string="Work Name",
        default="Standard Work",
        readonly=False
    )

    unit = fields.Char(
        string="Units",
        default="Hours",
        readonly=False
    )

    approved_hours = fields.Float(string='Approved Hours')
    comment = fields.Text(string="Comments")
    notes = fields.Text(string="Notes")

    def _break_to_float(self, break_time):
        mapping = {
            '15': 0.25,
            '30': 0.5,
            '45': 0.75,
            '60': 1.0,
        }
        return mapping.get(break_time, 0.0)

    def action_export_attendance_csv(self):
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        # CSV Header
        writer.writerow([
            'Employee',
            'Work Name',
            'Date',
            'Employee Email',
            'Notes',
            'Start Time',
            'End Time',
            'Duration',
            'Break Duration',
            'Units'
        ])

        for att in self:
            check_in = fields.Datetime.from_string(att.check_in) if att.check_in else False
            check_out = fields.Datetime.from_string(att.check_out) if att.check_out else False

            writer.writerow([
                att.employee_id.name or '',
                att.work_name or 'Standard Work',
                check_in.strftime('%d/%m/%Y') if check_in else '',
                att.employee_id.work_email or '',
                att.notes or '',
                check_in.strftime('%H:%M') if check_in else '',
                check_out.strftime('%H:%M') if check_out else '',
                round(att.worked_hours or 0, 2),
                self._break_to_float(att.break_time),
                att.unit or 'Hours'
            ])

        csv_content = buffer.getvalue()
        buffer.close()

        csv_base64 = base64.b64encode(csv_content.encode('utf-8'))
        filename = f"attendance_export_{fields.Date.today()}.csv"

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': csv_base64,
            'mimetype': 'text/csv',
        })

        # ✅ DIRECT DOWNLOAD ACTION
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    @api.onchange('check_in', 'check_out', 'break_time')
    def _compute_worked_hours(self):
        for attendance in self:
            if attendance.check_out and attendance.check_in and attendance.employee_id:
                calendar = attendance._get_employee_calendar()
                tz = timezone(calendar.tz)
                check_in_tz = attendance.check_in.astimezone(tz)
                check_out_tz = attendance.check_out.astimezone(tz)
                lunch_intervals = attendance.employee_id._employee_attendance_intervals(
                    check_in_tz, check_out_tz, lunch=True)
                attendance_intervals = Intervals([(check_in_tz, check_out_tz, attendance)]) - lunch_intervals
                delta = sum((i[1] - i[0]).total_seconds() for i in attendance_intervals)

                worked_hours = delta / 3600.0

                if attendance.break_time:
                    worked_hours -= int(attendance.break_time) / 60.0

                worked_hours = float_round(worked_hours, precision_digits=2)
                attendance.worked_hours = worked_hours

                if attendance.status == 'submitted':
                    attendance.approved_hours = worked_hours
            else:
                attendance.worked_hours = False

    def action_approve_attendance_bulk(self):
        for rec in self.filtered(lambda r: r.status == 'submitted'):
            rec.status = 'approved'
            rec.approved_hours = rec.worked_hours

    def action_approve_attendance(self):
        for rec in self:
            if rec.status == 'submitted':
                rec.status = 'approved'
                rec.approved_hours = rec.worked_hours
