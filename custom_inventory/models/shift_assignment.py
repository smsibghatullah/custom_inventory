from odoo import models, fields, api

class ShiftAssignment(models.Model):
    _name = 'shift.assignment'
    _description = 'Shift Assignment for Project Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    project_id = fields.Many2one('project.project', string='Project')
    task_id = fields.Many2one(
        'project.task', 
        string='Task', 
        domain="[('project_id', '=', project_id)]"
    )
    supervisor_ids = fields.Many2many(
        'hr.employee', 
        'shift_assignment_supervisor_rel',  
        'shift_id', 
        'employee_id', 
        string='Supervisors', 
    )
    employee_ids = fields.Many2many(
        'hr.employee', 
        'shift_assignment_employee_rel',  
        'shift_id', 
        'employee_id', 
        string='Employees', 
    )
    survey_id = fields.Many2one('survey.survey', string='Survey Form')

    team_checkin_required = fields.Boolean(string="Team Check-in Required")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_for_checkin', 'Waiting for Check-in'),
        ('done', 'Done')
    ], string="Status", default='draft')
    attendance_ids = fields.One2many('shift.attendance', 'shift_id', string="Attendance Records")

    def action_waiting_for_checkin(self):
        """Mark shift assignment as verified"""
        self.state = 'waiting_for_checkin'

class ShiftAttendance(models.Model):
    _name = 'shift.attendance'
    _description = 'Shift Attendance'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    shift_id = fields.Many2one('shift.assignment', string='Shift Assignment', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    check_in = fields.Datetime(string='Check-in Time')
    check_out = fields.Datetime(string='Check-out Time')
    duration = fields.Float(string='Worked Hours', compute='_compute_duration', store=True)

    @api.depends('check_in', 'check_out')
    def _compute_duration(self):
        for record in self:
            if record.check_in and record.check_out:
                duration = (record.check_out - record.check_in).total_seconds() / 3600.0
                record.duration = round(duration, 2)
                task = record.shift_id.task_id if record.shift_id.task_id else False
            
                if task and hasattr(task, 'timesheet_ids') and task.timesheet_ids:
                    print(task.id, "pppppppppppppppppppp")

                    self.env['account.analytic.line'].create({
                        'date': record.check_in.date(),
                        'employee_id': record.employee_id.id,
                        'name': task.name,
                        'unit_amount': record.duration,
                        'task_id': task.id,
                    })
            else:
                record.duration = 0.0

  