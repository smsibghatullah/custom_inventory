from odoo import models, fields, api
from datetime import timedelta
from odoo.exceptions import UserError,ValidationError


class ShiftRole(models.Model):
    _name = 'shift.assignment.main'
    _description = 'Shift Assignment'

    name = fields.Char(string="Name", required=True)
    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done')
    ], string="Status", default='draft')
    main_shift_assignment_id = fields.One2many('shift.assignment', 'main_shift_assignment_id', string="Shift Assigments")
    survey_status_ids = fields.One2many(
        'shift.assignment.survey.status',
        'shift_main_id',
        string="Survey Statuses",
    )
    survey_assigned_form_ids = fields.One2many(
        'shift.assignment.assigned.forms',
        'shift_main_id',
    )

    @api.constrains('date_from', 'date_to')
    def _check_date_order(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from < rec.date_to:
                raise ValidationError("⚠️ Date From must be greather than Date To.")


    def action_generate_shifts(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'shift.generate.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_main_shift_id': self.id,
            }
        }


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

    date = fields.Date(string="Date")
    project_id = fields.Many2one('project.project', string='Project')
    task_id = fields.Many2one(
        'project.task', 
        string='Task', 
        domain="[('project_id', '=', project_id)]"
    )
    supervisor_ids = fields.Many2many(
        'res.users', 
        'shift_assignment_supervisor_user_rel',  
        'shift_id', 
        'employee_id', 
        string='Supervisors', 
    )
    employee_ids = fields.Many2many(
        'res.users', 
        'shift_assignment_employee_user_rel',  
        'shift_id', 
        'employee_id', 
        string='Employees', 
    )
    survey_id = fields.Many2many('survey.survey', string='Survey Forms')
    team_checkin_required = fields.Boolean(string="Team Check-in Required")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_for_checkin', 'Waiting For Check-in'),
        ('done', 'Done')
    ], string="Status", default='draft')
    main_shift_assignment_id = fields.Many2one('shift.assignment.main', string='Shift Assignment', required=True)
    attendance_ids = fields.One2many('shift.attendance', 'shift_id', string="Attendance Records")
    survey_status_ids = fields.One2many(
        'shift.assignment.survey.status',
        'shift_id',
        string="Survey Statuses",
    )

    @api.model
    def create(self, vals):
        record = super(ShiftAssignment, self).create(vals)

        status_data = []
        all_surveys = [
            # ('project', record.project_survey_ids),
            # ('task', record.task_survey_ids)
        ]
        all_employees = record.employee_ids | record.supervisor_ids
        for survey_type, surveys in all_surveys:
            for emp in all_employees:
                for survey in surveys:
                    status_entry = {
                        'employee_id': emp.id,
                        'survey_id': survey.id,
                        'status': 'not_filled',  
                        'survey_type': survey_type,
                        'shift_id': record.id,
                        'shift_main_id': record.main_shift_assignment_id.id,
                    }

                    if survey_type == 'project':
                        status_entry['project_id'] = record.project_id.id
                    elif survey_type == 'task':
                        status_entry['task_id'] = record.task_id.id

                    status_data.append(status_entry)

        if status_data:
            self.env['shift.assignment.survey.status'].create(status_data)

        return record



    @api.model
    def write(self, vals):
        result = super(ShiftAssignment, self).write(vals)

        for record in self:
            all_surveys = [
                # ('project', record.project_survey_ids),
                # ('task', record.task_survey_ids)
            ]
            all_employees = record.employee_ids | record.supervisor_ids
            for survey_type, surveys in all_surveys:
                for emp in all_employees:
                    for survey in surveys:
                        existing_status = self.env['shift.assignment.survey.status'].search([
                            ('employee_id', '=', emp.id),
                            ('survey_id', '=', survey.id),
                            ('survey_type', '=', survey_type),
                            ('shift_id', '=', record.id),
                        ], limit=1)

                        if existing_status:
                            existing_status.write({
                                # 'status': existing_status.status or 'not_filled',
                                'shift_main_id': record.main_shift_assignment_id.id,
                            })
                        else:
                            self.env['shift.assignment.survey.status'].create({
                                'employee_id': emp.id,
                                'survey_id': survey.id,
                                'status': 'not_filled',
                                'survey_type': survey_type,
                                'shift_id': record.id,
                                'shift_main_id': record.main_shift_assignment_id.id,
                                'task_id':record.task_id.id  if survey_type == 'task' else [],
                                'project_id':record.project_id.id  if survey_type == 'project' else []
                            })


            if vals.get('state') == 'done' or record.state == 'done':
                for attendance in record.attendance_ids:
                    if attendance.check_in and not attendance.check_out:
                        attendance.check_out = fields.Datetime.now()

                if record.task_id and record.project_id:
                    done_stage = self.env['project.task.type'].search([
                        ('name', '=', 'Done'),
                        ('project_ids', 'in', record.project_id.id)
                    ], limit=1)
                    if done_stage:
                        record.task_id.stage_id = done_stage.id
                    record.task_id.state = '1_done'

        self.mapped('main_shift_assignment_id').check_and_update_state()
        return result


class ShiftSurveyAssignedForms(models.Model):
    _name = 'shift.assignment.assigned.forms'
    _description = 'Survey Assigned Form'

    survey_id = fields.Many2one('survey.survey', string="Survey")
    shift_main_id = fields.Many2one('shift.assignment.main', string="Shift main Assignment")
    survey_type = fields.Selection([
        ('project', 'Project Survey'),
        ('task', 'Task Survey')
    ], string="Survey Type")

    project_id = fields.Many2one(
        'project.project', 
        string='Project',
        domain="[('id','in',available_project_ids)]"
    )
    task_id = fields.Many2one(
        'project.task', 
        string='Task',
        domain="[('id','in',available_task_ids)]"
    )

    frequency = fields.Selection([
        ('one_time_recurring', 'One Time Recurring'),
        ('multiple_time_recurring', 'Multiple Time Recurring')
    ], string="Frequency")

    available_project_ids = fields.Many2many(
        'project.project',
        compute='_compute_available_projects',
        store=False
    )
    available_task_ids = fields.Many2many(
        'project.task',
        compute='_compute_available_tasks',
        store=False
    )


    @api.depends('shift_main_id')
    def _compute_available_projects(self):
        for rec in self:
            if rec.shift_main_id:
                rec.available_project_ids = rec.shift_main_id.main_shift_assignment_id.mapped('project_id')
            else:
                rec.available_project_ids = self.env['project.project']

    @api.depends('project_id', 'shift_main_id')
    def _compute_available_tasks(self):
        for rec in self:
            if rec.shift_main_id:
                rec.available_task_ids = rec.shift_main_id.main_shift_assignment_id.mapped('task_id')
            else:
                rec.available_task_ids = self.env['project.task']


  

class ShiftAttendance(models.Model):
    _name = 'shift.attendance'
    _description = 'Shift Attendance'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    shift_id = fields.Many2one('shift.assignment', string='Shift Assignment', required=True)
    employee_id = fields.Many2one('res.users', string='Employee', required=True)
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
                print(task.id, "pppppppp=================================================pppppppppppp")
                if task and hasattr(task, 'timesheet_ids'):
                    print(task.id, "pppppppp=================================================pppppppppppp")

                    self.env['account.analytic.line'].create({
                        'date': record.check_in.date(),
                        'employee_id': record.employee_id.id,
                        'name': task.name,
                        'unit_amount': record.duration,
                        'task_id': task.id,
                    })
            else:
                record.duration = 0.0

class ShiftSurveyStatus(models.Model):
    _name = 'shift.assignment.survey.status'
    _description = 'Survey Status for Employee (Shift-Based)'

    employee_id = fields.Many2one('res.users', string="Employee")
    survey_id = fields.Many2one('survey.survey', string="Survey")
    status = fields.Selection([
        ('not_filled', 'Not Filled'),
        ('partial', 'Partially Filled'),
        ('filled', 'Filled')
    ], string="Survey Status")
    shift_id = fields.Many2one('shift.assignment', string="Shift Assignment")
    shift_main_id = fields.Many2one('shift.assignment.main', string="Shift main Assignment")
    survey_type = fields.Selection([
        ('project', 'Project Survey'),
        ('task', 'Task Survey')
    ], string="Survey Type")
    project_id = fields.Many2one('project.project', string='Project')
    task_id = fields.Many2one(
        'project.task', 
        string='Task', 
    )


class ShiftGenerateWizard(models.TransientModel):
    _name = 'shift.generate.wizard'
    _description = 'Wizard to Generate Shifts'

    project_id = fields.Many2one('project.project', string="Project", required=True)
    task_id = fields.Many2one(
        'project.task', 
        string='Task', 
        domain="[('project_id', '=', project_id)]",
        required=True
    )
    supervisor_ids = fields.Many2many(
        'res.users', 
        'shift_generate_supervisor_rel',
        'wizard_id',
        'user_id',
        string="Supervisors",
        required=True
    )
    employee_ids = fields.Many2many(
        'res.users', 
        'shift_generate_employee_rel',
        'wizard_id',
        'user_id',
        string="Employees",
        required=True
    )
    main_shift_id = fields.Many2one('shift.assignment.main', string="Main Shift Assignment")

    def action_generate(self):
        """Generate Shift Assignments for all dates in main_shift_id"""
        self.ensure_one()
        main = self.main_shift_id
        if not main:
            return

        start_date = min(main.date_from, main.date_to)
        end_date = max(main.date_from, main.date_to)

        current_date = start_date
        while current_date <= end_date:
            vals = {
                'date': current_date,
                'project_id': self.project_id.id,
                'task_id': self.task_id.id,
                'supervisor_ids': [(6, 0, self.supervisor_ids.ids)],
                'employee_ids': [(6, 0, self.employee_ids.ids)],
                'main_shift_assignment_id': main.id,
            }
            rec = self.env['shift.assignment'].create(vals)
            print(f"Created Shift on {current_date} -> {rec.id}")
            current_date += timedelta(days=1)

        return {'type': 'ir.actions.act_window_close'}




class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    project_id = fields.Many2one('project.project', string="Project")
    task_id = fields.Many2one(
        'project.task', 
        string="Task", 
    )

class Project(models.Model):
    _inherit = "project.project"

    survey_count = fields.Integer(string="Surveys", compute="_compute_survey_count")

    def _compute_survey_count(self):
        for project in self:
            project.survey_count = self.env['survey.user_input'].search_count([
                ('project_id', '=', project.id)
            ]) or 0

    def action_view_project_surveys(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Surveys',
            'res_model': 'survey.user_input',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

class Task(models.Model):
    _inherit = "project.task"

    survey_count = fields.Integer(string="Surveys", compute="_compute_survey_count")

    def _compute_survey_count(self):
        for task in self:
            task.survey_count = self.env['survey.user_input'].search_count([
                ('task_id', '=', task.id)
            ])

    def action_view_task_surveys(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Surveys',
            'res_model': 'survey.user_input',
            'view_mode': 'tree,form',
            'domain': [('task_id', '=', self.id)],
            'context': {'default_task_id': self.id},
        }


  