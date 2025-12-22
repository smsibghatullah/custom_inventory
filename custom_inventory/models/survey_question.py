from odoo import models, fields

class SurveyQuestion(models.Model):
    _inherit = 'survey.question'

    question_type = fields.Selection(selection_add=[
        ('digital_signature', 'Digital Signature'),
        ('static_content', 'Static Content') ,
        ('table', 'Table')
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

    description = fields.Text(
        string="Description / Helper Text"
    )

    auto_filled = fields.Boolean(
        string="Auto Filled",
    )

    question_id = fields.Many2one(
        "survey.question",
        string="Refrence Field",
        ondelete="set null"
    )

    table_row_ids = fields.One2many('survey.table.row', 'question_id', string="Table Rows")
    table_column_ids = fields.One2many('survey.table.column', 'question_id', string="Table Columns")
    static_content = fields.Html("Static Content")

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