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
        ('verified', 'Verified')
    ], string="Status", default='draft', tracking=True)

    @api.onchange('team_checkin_required')
    def _onchange_team_checkin_required(self):
        """If check-in required, move to waiting state"""
        if self.team_checkin_required:
            self.state = 'waiting_for_checkin'
        else:
            self.state = 'draft'

    def action_verify_checkin(self):
        """Mark shift assignment as verified"""
        self.state = 'verified'
