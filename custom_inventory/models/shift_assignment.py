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
    survey_status_ids = fields.One2many(
        'shift.assignment.survey.status',
        'shift_main_id',
        string="Survey Statuses",
    )
   

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

    name = fields.Char(string="Name", required=True, copy=False, readonly=True, default='New')
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
    project_survey_ids = fields.Many2many(
        'survey.survey',
        'shift_assignment_project_survey_rel',
        'shift_id',
        'survey_id',
        string='Project Survey Form(s)'
    )
    task_survey_ids = fields.Many2many(
        'survey.survey',
        'shift_assignment_task_survey_rel',
        'shift_id',
        'survey_id',
        string='Task Survey Form(s)'
    )
    project_survey_required = fields.Boolean(string="Project Survey Mandatory")
    task_survey_required = fields.Boolean(string="Task Survey Mandatory")


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
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('shift.assignment') or 'New'
        record = super(ShiftAssignment, self).create(vals)

        status_data = []
        all_surveys = [
            ('project', record.project_survey_ids),
            ('task', record.task_survey_ids)
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
                ('project', record.project_survey_ids),
                ('task', record.task_survey_ids)
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



  