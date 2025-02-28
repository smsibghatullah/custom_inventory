from odoo import models, fields, api

class ShiftAssignment(models.Model):
    _name = 'shift.assignment'
    _description = 'Shift Assignment for Project Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    project_id = fields.Many2one('project.project', string='Project', tracking=True)
    task_id = fields.Many2one(
        'project.task', 
        string='Task', 
        tracking=True,
        domain="[('project_id', '=', project_id)]"
    )
    supervisor_ids = fields.Many2many(
        'hr.employee', 
        'shift_assignment_supervisor_rel',  
        'shift_id', 
        'employee_id', 
        string='Supervisors', 
        tracking=True
    )
    employee_ids = fields.Many2many(
        'hr.employee', 
        'shift_assignment_employee_rel',  
        'shift_id', 
        'employee_id', 
        string='Employees', 
        tracking=True
    )
    survey_id = fields.Many2one('survey.survey', string='Survey Form', tracking=True)

    team_checkin_required = fields.Boolean(string="Team Check-in Required", tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_for_checkin', 'Waiting for Check-in'),
        ('done', 'Done')
    ], string="Status", default='draft', tracking=True)
    attendance_ids = fields.One2many('shift.attendance', 'shift_id', string="Attendance Records")

    def action_waiting_for_checkin(self):
        """Mark shift assignment as verified"""
        self.state = 'waiting_for_checkin'

class ShiftAttendance(models.Model):
    _name = 'shift.attendance'
    _description = 'Shift Attendance'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    shift_id = fields.Many2one('shift.assignment', string='Shift Assignment', required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    check_in = fields.Datetime(string='Check-in Time', tracking=True)
    check_out = fields.Datetime(string='Check-out Time', tracking=True)
    duration = fields.Float(string='Worked Hours', compute='_compute_duration', store=True, tracking=True)

    @api.depends('check_in', 'check_out')
    def _compute_duration(self):
        for record in self:
            if record.check_in and record.check_out:
                duration = (record.check_out - record.check_in).total_seconds() / 3600.0
                record.duration = round(duration, 2)
            else:
                record.duration = 0.0
