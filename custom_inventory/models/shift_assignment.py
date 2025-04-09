from odoo import models, fields, api

class ShiftRole(models.Model):
    _name = 'shift.assignment.main'
    _description = 'Shift Assignment'

    name = fields.Char(string="Name", required=True)
    date = fields.Date(string="Date", default=fields.Date.context_today)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done')
    ], string="Status", default='draft')
    main_shift_assignment_id = fields.One2many('shift.assignment', 'main_shift_assignment_id', string="Shift Assigments")
   

    def action_waiting_for_checkin(self):
        """Mark shift assignment as verified"""
        self.state = 'in_progress'
        for shift in self.main_shift_assignment_id:
            shift.write({'state': 'waiting_for_checkin'})
            print(shift.state,"ppppppppppppppppppppppppppppppppppppppppdddddddddddddddddddddddddddddddddddddddd")

    def check_and_update_state(self):
        """Check if all Shift Assignments are done, then update Main Shift Assignment state"""
        for record in self:
            if record.state != 'done' and record.main_shift_assignment_id and all(shift.state == 'done' for shift in record.main_shift_assignment_id):
                record.state = 'done'


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
    survey_id = fields.Many2many('survey.survey', string='Survey Form')

    team_checkin_required = fields.Boolean(string="Team Check-in Required")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_for_checkin', 'Waiting For Check-in'),
        ('done', 'Done')
    ], string="Status", default='draft')
    main_shift_assignment_id = fields.Many2one('shift.assignment.main', string='Shift Assignment', required=True)
    attendance_ids = fields.One2many('shift.attendance', 'shift_id', string="Attendance Records")

    def write(self, vals):
        """Check if all shift assignments are done when state changes"""
        result = super(ShiftAssignment, self).write(vals)
        if 'state' in vals and vals['state'] == 'done':
            self.mapped('main_shift_assignment_id').check_and_update_state()
        return result

    @api.model
    def write(self, vals):
        if 'state' in vals and vals['state'] == 'done':
            for record in self:
                for attendance in record.attendance_ids:
                    if attendance.check_in and not attendance.check_out:
                        attendance.check_out = fields.Datetime.now()
        return super(ShiftAssignment, self).write(vals)



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

  