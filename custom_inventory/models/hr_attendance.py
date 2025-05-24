
import pytz

from collections import defaultdict
from datetime import datetime, timedelta
from operator import itemgetter
from pytz import timezone

from odoo import models, fields, api, exceptions, _
from odoo.addons.resource.models.utils import Intervals
from odoo.tools import format_datetime
from odoo.osv.expression import AND, OR
from odoo.tools.float_utils import float_is_zero,float_round
from odoo.exceptions import AccessError
from odoo.tools import format_duration

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

    @api.depends('check_in', 'check_out', 'break_time')
    def _compute_worked_hours(self):
        for attendance in self:
            if attendance.check_out and attendance.check_in and attendance.employee_id:
                calendar = attendance._get_employee_calendar()
                resource = attendance.employee_id.resource_id
                tz = timezone(calendar.tz)
                check_in_tz = attendance.check_in.astimezone(tz)
                check_out_tz = attendance.check_out.astimezone(tz)
                lunch_intervals = attendance.employee_id._employee_attendance_intervals(check_in_tz, check_out_tz, lunch=True)
                attendance_intervals = Intervals([(check_in_tz, check_out_tz, attendance)]) - lunch_intervals
                delta = sum((i[1] - i[0]).total_seconds() for i in attendance_intervals)

                worked_hours = delta / 3600.0

                if attendance.break_time:
                    break_minutes = int(attendance.break_time)
                    worked_hours -= break_minutes / 60.0

                attendance.worked_hours = float_round(worked_hours, precision_digits=2)
            else:
                attendance.worked_hours = False
