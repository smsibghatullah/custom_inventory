from odoo import models, fields,api

class SurveyQuestion(models.Model):
    _inherit = 'survey.question'

    question_type = fields.Selection(selection_add=[
        ('digital_signature', 'Digital Signature'),
        ('static_content', 'Static Content') ,
        ('table', 'Table'),
        ('risk', 'Risk')
    ])

    heading_id = fields.Many2one(
        "survey.heading",
        string="Heading",
        ondelete="set null"
    )

    group_id = fields.Many2one(
        "survey.group",
        string="Group",
        ondelete="set null"
    )

    subtitle = fields.Char(
        string="Subtitle"
    )

    description = fields.Char(
        string="Description / Helper Text"
    )

    auto_filled = fields.Boolean(
        string="Auto Filled",
    )

    pre_filled = fields.Boolean(
        string="Pre Filled",
    )

    question_id = fields.Many2one(
        "survey.question",
        string="Refrence Field",
        ondelete="set null"
    )

    table_row_ids = fields.One2many('survey.table.row', 'question_id', string="Table Rows")
    table_column_ids = fields.One2many('survey.table.column', 'question_id', string="Table Columns")
    static_content = fields.Html("Static Content")

    prefill_text = fields.Text(string='Prefill Text')
    prefill_char = fields.Char(string='Prefill Char')
    prefill_number = fields.Float(string='Prefill Number')
    prefill_date = fields.Date(string='Prefill Date')
    prefill_datetime = fields.Datetime(string='Prefill Datetime')
    prefill_signature = fields.Binary(string='Prefill Signature')

    potential_hazard_ids = fields.Many2many(
        'survey.potential_hazard',relation='survey_assessment_hazard_rel', string="Potential Hazards / Risks"
    )
   


class SurveyPotentialHazard(models.Model):
    _name = "survey.potential_hazard"
    _description = "Potential Hazard or Risk"
    _order = "sequence, id"

    name = fields.Char(string="Potential Hazard / Risk", required=True)
    question_id = fields.Many2one('survey.question', string="Question", ondelete='cascade')
    user_input_line_id = fields.Many2one(
        'survey.user_input.line',
        ondelete='cascade'
    )
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(default=True)  

    hazard_consequence_id = fields.Many2one(
        'survey.hazard_consequence', string="Hazard Consequences"
    )
    likelihood_id = fields.Many2one(
        'survey.likelihood', string="Likelihood Ratings"
    )
    post_control_hazard_consequence_id = fields.Many2one(
        'survey.post_control_hazard_consequence', string="Post-Control Hazard Consequences"
    )
    post_control_likelihood_id = fields.Many2one(
        'survey.post_control_likelihood', string="Post-Control Likelihood Ratings"
    )

    control_ids = fields.Many2many(
        'survey.controls', 
        'survey_question_controls_rel', 
        'potential_hazard_id', 
        'control_id', 
        string="Control Measures"
    )

    initial_risk_score = fields.Integer(
        string="Initial Risk Score",
        compute="_compute_initial_risk",
        store=True
    )

    initial_risk_level = fields.Selection(
        [('low', 'LOW'), ('medium', 'MEDIUM'), ('high', 'HIGH')],
        string="Initial Risk Level",
        compute="_compute_initial_risk",
        store=True
    )

    # ================= POST CONTROL RISK =================
    post_control_risk_score = fields.Integer(
        string="Post Control Risk Score",
        compute="_compute_post_control_risk",
        store=True
    )

    post_control_risk_level = fields.Selection(
        [('low', 'LOW'), ('medium', 'MEDIUM'), ('high', 'HIGH')],
        string="Post Control Risk Level",
        compute="_compute_post_control_risk",
        store=True
    )

    # ============== COMPUTE METHODS ==================

    @api.depends('hazard_consequence_id.rating', 'likelihood_id.rating')
    def _compute_initial_risk(self):
        for rec in self:
            score = 0
            if rec.hazard_consequence_id and rec.likelihood_id:
                score = rec.hazard_consequence_id.rating * rec.likelihood_id.rating

            rec.initial_risk_score = score
            rec.initial_risk_level = rec._get_risk_level(score)

    @api.depends('post_control_hazard_consequence_id.rating', 'post_control_likelihood_id.rating')
    def _compute_post_control_risk(self):
        for rec in self:
            score = 0
            if rec.post_control_hazard_consequence_id and rec.post_control_likelihood_id:
                score = (
                    rec.post_control_hazard_consequence_id.rating *
                    rec.post_control_likelihood_id.rating
                )

            rec.post_control_risk_score = score
            rec.post_control_risk_level = rec._get_risk_level(score)

    # ============== RISK LEVEL LOGIC ==================
    def _get_risk_level(self, score):
        if score <= 5:
            return 'low'
        elif score <= 12:
            return 'medium'
        else:
            return 'high'

class SurveyHazardConsequence(models.Model):
    _name = "survey.hazard_consequence"
    _description = "Hazard Consequence Rating"
    _order = "sequence, id"

    name = fields.Char(string="Consequence", required=True) 
    rating = fields.Integer(string="Rating", required=True)  
    potential_hazard_id = fields.Many2one("survey.potential_hazard", string="Potential Hazard", ondelete="cascade")
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(default=True)
   

class SurveyLikelihood(models.Model):
    _name = "survey.likelihood"
    _description = "Likelihood / Possibility Rating"
    _order = "sequence, id"

    name = fields.Char(string="Likelihood", required=True)  
    rating = fields.Integer(string="Rating", required=True) 
    potential_hazard_id = fields.Many2one("survey.potential_hazard", string="Potential Hazard", ondelete="cascade")
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(default=True)

class SurveyControls(models.Model):
    _name = "survey.controls"
    _description = "Controls to be Implemented for Risks & Hazards"
    _order = "sequence, id"

    name = fields.Text(string="Control Measures", required=True)
    potential_hazard_id = fields.Many2one("survey.potential_hazard", string="Potential Hazard", ondelete="cascade")
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(default=True)

class SurveyPostControlHazardConsequence(models.Model):
    _name = "survey.post_control_hazard_consequence"
    _description = "Hazard Consequence Rating"
    _order = "sequence, id"

    name = fields.Char(string="Consequence", required=True) 
    potential_hazard_id = fields.Many2one("survey.potential_hazard", string="Potential Hazard", ondelete="cascade")
    rating = fields.Integer(string="Rating", required=True)  
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(default=True)

class SurveyPostControlLikelihood(models.Model):
    _name = "survey.post_control_likelihood"
    _description = "Likelihood / Possibility Rating"
    _order = "sequence, id"

    name = fields.Char(string="Likelihood", required=True)  
    potential_hazard_id = fields.Many2one("survey.potential_hazard", string="Potential Hazard", ondelete="cascade")
    rating = fields.Integer(string="Rating", required=True) 
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(default=True)    

class SurveyTableRow(models.Model):
    _name = 'survey.table.row'
    _description = 'Survey Table Row'

    question_id = fields.Many2one('survey.question', string="Question", ondelete='cascade')
    name = fields.Char(string="Row Title")
    sequence = fields.Integer(string="Sequence", default=10)


class SurveyTableColumn(models.Model):
    _name = 'survey.table.column'
    _description = 'Survey Table Column'

    question_id = fields.Many2one('survey.question', string="Question", ondelete='cascade')
    name = fields.Char(string="Column Title")
    input_type = fields.Selection([
        ('text', 'Text'),
        ('numeric', 'Numeric'),
        ('dropdown', 'Dropdown')
    ], string="Input Type", default='text')
    sequence = fields.Integer(string="Sequence", default=10)
    dropdown_options = fields.Text(string="Dropdown Options (comma separated)")


class SurveyHeading(models.Model):
    _name = "survey.heading"
    _description = "Survey Question Heading"
    _order = "sequence, id"

    name = fields.Char(string="Heading Title", required=True)
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(default=True)

class SurveyGroup(models.Model):
    _name = "survey.group"
    _description = "Survey Question Group"
    _order = "sequence, id"

    name = fields.Char(string="Name", required=True)
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(default=True)