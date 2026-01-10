from odoo import models, fields,_,api
import textwrap
import re

class SurveyUserInputLine(models.Model):
    _inherit = 'survey.user_input.line'

    digital_signature = fields.Binary("Digital Signature")
    static_content = fields.Html("Static Content") 
    answer_type = fields.Selection(selection_add=[
        ('digital_signature', 'Digital Signature'),
        ('static_content', 'Static Content') ,
        ('risk', 'Risk'),
        ('table', 'Table'),
    ])
    hazard_ids = fields.Many2many(
        'survey.potential_hazard',
        relation='survey_input_assessment_hazard_rel', 
        string="Risk Assessment"
    )
    table_ids = fields.Many2many('survey.table', relation='survey_input_assessment_table_rel', string="Table")
    heading_id = fields.Many2one(
        'survey.heading',
        string="Heading",
        related='question_id.heading_id',
        store=True,
        readonly=True
    )

    group_id = fields.Many2one(
        'survey.group',
        string="Group",
        related='question_id.group_id',
        store=True,
        readonly=True
    )

    subtitle = fields.Char(
        string="Subtitle",
        related='question_id.subtitle',
        store=True,
        readonly=True
    )

    description = fields.Char(
        string="Description / Helper Text",
        related='question_id.description',
        store=True,
        readonly=True
    )

    def _compute_display_name(self):
        for line in self:
            if line.answer_type == 'char_box':
                line.display_name = line.value_char_box
            elif line.answer_type == 'text_box' and line.value_text_box:
                line.display_name = textwrap.shorten(line.value_text_box, width=50, placeholder=" [...]")
            elif line.answer_type == 'numerical_box':
                line.display_name = line.value_numerical_box
            elif line.answer_type == 'date':
                line.display_name = fields.Date.to_string(line.value_date)
            elif line.answer_type == 'datetime':
                line.display_name = fields.Datetime.to_string(line.value_datetime)
            elif line.answer_type == 'digital_signature':
                line.display_name = 'Digital Signature'  
            elif line.answer_type == 'static_content':
                line.display_name = 'Static Content' 
            elif line.answer_type == 'risk':
                line.display_name = 'Risk' 
            elif line.answer_type == 'table':
                line.display_name = 'Table'             
            elif line.answer_type == 'suggestion':
                if line.matrix_row_id:
                    line.display_name = f'{line.suggested_answer_id.value}: {line.matrix_row_id.value}'
                else:
                    line.display_name = line.suggested_answer_id.value

            if not line.display_name:
                line.display_name = _('Skipped')


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    def action_download_employment_certificate(self):
        self.ensure_one()
        return self.env.ref('custom_inventory.action_report_employment_certificate').report_action(self)

    def _save_lines(self, question, answer, comment=None, overwrite_existing=True):
        """ Save answers to questions, depending on question type.

        :param bool overwrite_existing: if an answer already exists for question and user_input_id
        it will be overwritten (or deleted for 'choice' questions) in order to maintain data consistency.
        :raises UserError: if line exists and overwrite_existing is False
        """
        old_answers = self.env['survey.user_input.line'].search([
            ('user_input_id', '=', self.id),
            ('question_id', '=', question.id)
        ])
        if old_answers and not overwrite_existing:
            raise UserError(_("This answer cannot be overwritten."))

        if question.question_type in ['char_box', 'text_box', 'numerical_box', 'date', 'datetime']:
            self._save_line_simple_answer(question, old_answers, answer)
            if question.save_as_email and answer:
                self.write({'email': answer})
            if question.save_as_nickname and answer:
                self.write({'nickname': answer})

        elif question.question_type in ['simple_choice', 'multiple_choice']:
            self._save_line_choice(question, old_answers, answer, comment)
        elif question.question_type == 'matrix':
            self._save_line_matrix(question, old_answers, answer, comment)
        elif question.question_type == 'digital_signature':
            self._save_line_digital_signature(question, old_answers, answer)
        elif question.question_type == 'static_content':
            self._save_line_static_content(question, old_answers, answer)    
        else:
            raise AttributeError(question.question_type + ": This type of question has no saving function")


    def _save_line_static_content(self, question, old_answers, answer):
        """
        Save static content lines for survey questions.
        :param question: survey.question record
        :param old_answers: existing survey.user_input.line records
        :param answer: HTML content / string
        """
        vals = {
            'user_input_id': self.id,
            'question_id': question.id,
            'answer_type': 'static_content',
            'skipped': False,
            'static_content': answer,
            'display_name': "Static Content"
        }

        if not answer:
            vals.update({
                'static_content': False,
                'skipped': True,
            })

        if old_answers:
            old_answers.write(vals)
            return old_answers
        else:
            return self.env['survey.user_input.line'].create(vals)
        

    def _save_line_digital_signature(self, question, old_answers, answer):
        vals = {
            'user_input_id': self.id,
            'question_id': question.id,
            'answer_type': 'digital_signature',
            'skipped': False,
            'digital_signature': answer,
            'display_name' : "Digital Signature"
        }
        print(vals,"==============================vals============================")

        if not answer:
            vals.update({
                'digital_signature': False,
                'skipped': True,
            })

        if old_answers:
            old_answers.write(vals)
            return old_answers
        else:
            return self.env['survey.user_input.line'].create(vals)

    

class ReportEmploymentCertificate(models.AbstractModel):
    _name = 'report.custom_inventory.report_employment_certificate'
    _description = 'Employment Certificate Report'

    def _clean_html_unicode(self, text):
        if not text:
            return ""
        unicode_controls = [
            u'\u202a', u'\u202b', u'\u202c',
            u'\u202d', u'\u202e',
            u'\u200e', u'\u200f'
        ]
        for ch in unicode_controls:
            text = text.replace(ch, '')
        return text

    @api.model
    def _get_report_values(self, docids, data=None):

        user_inputs = self.env['survey.user_input'].browse(docids)

        grouped_data = {}
        risk_register = []   # ✅ master risk table at end

        for user_input in user_inputs:

            # all questions answered in this survey
            questions = user_input.user_input_line_ids.mapped('question_id')

            for question in questions:

                group = question.group_id
                heading = question.heading_id

                group_id = group.id if group else 0
                heading_id = heading.id if heading else 0

                # ---------------- GROUP ----------------
                if group_id not in grouped_data:
                    grouped_data[group_id] = {
                        'group_id': group_id,
                        'group_name': group.name if group else '',
                        'sequence': group.sequence if group else 0,
                        'headings': {}
                    }

                # ---------------- HEADING ----------------
                if heading_id not in grouped_data[group_id]['headings']:
                    grouped_data[group_id]['headings'][heading_id] = {
                        'heading_id': heading_id,
                        'heading_name': heading.name if heading else '',
                        'sequence': heading.sequence if heading else 0,
                        'questions': []
                    }

                # ❌ avoid duplicate question (multiple user_input_line exist)
                already_added = any(
                    q['question_id'] == question.id
                    for q in grouped_data[group_id]['headings'][heading_id]['questions']
                )
                if already_added:
                    continue

                # ---------------- QUESTION LINES ----------------
                question_lines = user_input.user_input_line_ids.filtered(
                    lambda l: l.question_id.id == question.id
                )

                # ---------------- ANSWERS ----------------
                answers = {
                    'char_box': '',
                    'text_box': '',
                    'numerical_box': '',
                    'date': '',
                    'datetime': '',
                    'digital_signature': False,
                    'static_content': '',

                    'simple_choice_options': [],
                    'multiple_choice_options': [],

                    'matrix_columns': [],
                    'matrix_rows': [],

                    'table_columns': [],
                    'table_rows': [],

                    'risk': [],
                }

                # ---------- SIMPLE CHOICE ----------
                if question.question_type == 'simple_choice':
                    selected_line = question_lines[:1]
                    selected_answer = selected_line.suggested_answer_id if selected_line else False

                    for opt in question.suggested_answer_ids:
                        answers['simple_choice_options'].append({
                            'answer_id': opt.id,
                            'label': opt.value,
                            'selected': bool(selected_answer and opt.id == selected_answer.id)
                        })

                # ---------- MULTIPLE CHOICE ----------
                elif question.question_type == 'multiple_choice':
                    selected_answer_ids = set(question_lines.mapped('suggested_answer_id').ids)

                    for opt in question.suggested_answer_ids:
                        answers['multiple_choice_options'].append({
                            'answer_id': opt.id,
                            'label': opt.value,
                            'selected': opt.id in selected_answer_ids
                        })

                # ---------- TABLE ----------
                elif question.question_type == 'table':
                    table_columns = {}
                    table_rows = {}

                    for tl in question.table_ids:
                        if tl.column_no not in table_columns:
                            table_columns[tl.column_no] = {
                                'column_no': tl.column_no,
                                'column_name': tl.column_name
                            }

                        if tl.row_no not in table_rows:
                            table_rows[tl.row_no] = {
                                'row_no': tl.row_no,
                                'cells': {}
                            }

                        table_rows[tl.row_no]['cells'][tl.column_no] = tl.value

                    answers['table_columns'] = sorted(
                        table_columns.values(),
                        key=lambda c: c['column_no']
                    )
                    answers['table_rows'] = sorted(
                        table_rows.values(),
                        key=lambda r: r['row_no']
                    )

                # ---------- MATRIX ----------
                elif question.question_type == 'matrix':

                    for col in question.suggested_answer_ids:
                        answers['matrix_columns'].append({
                            'id': col.id,
                            'label': col.value,
                        })

                    row_map = {}
                    for row in question.matrix_row_ids:
                        row_map[row.id] = {
                            'id': row.id,
                            'label': row.value,
                            'selected_cols': set()
                        }

                    for ln in question_lines:
                        if ln.matrix_row_id and ln.suggested_answer_id:
                            row_map[ln.matrix_row_id.id]['selected_cols'].add(
                                ln.suggested_answer_id.id
                            )

                    for row in row_map.values():
                        answers['matrix_rows'].append({
                            'id': row['id'],
                            'label': row['label'],
                            'columns': [
                                {
                                    'column_id': col['id'],
                                    'selected': col['id'] in row['selected_cols']
                                }
                                for col in answers['matrix_columns']
                            ]
                        })

                # ---------- RISK ----------
                elif question.question_type == 'risk':

                    key = (question.title or '', question.subtitle or '')

                    risk_block = next(
                        (r for r in risk_register
                         if r['activity'] == key[0] and r['subtitle'] == key[1]),
                        None
                    )

                    if not risk_block:
                        risk_block = {
                            'activity': key[0],
                            'subtitle': key[1],
                            'hazards': []
                        }
                        risk_register.append(risk_block)

                    for hazard in question.potential_hazard_ids:
                        row = {
                            'hazard': hazard.name or '',
                            'consequence': (
                                f"{hazard.hazard_consequence_id.rating} - "
                                f"{hazard.hazard_consequence_id.name}"
                                if hazard.hazard_consequence_id else ''
                            ),
                            'likelihood': (
                                f"{hazard.likelihood_id.rating} - "
                                f"{hazard.likelihood_id.name}"
                                if hazard.likelihood_id else ''
                            ),
                            'initial_score': hazard.initial_risk_score,
                            'initial_level': hazard.initial_risk_level,
                            'controls': hazard.control_ids.mapped('name'),
                            'post_score': hazard.post_control_risk_score,
                            'post_level': hazard.post_control_risk_level,
                        }

                        risk_block['hazards'].append(row)
                        answers['risk'].append(row)

                # ---------- OTHER TYPES ----------
                for ln in question_lines:
                    answers['char_box'] = ln.value_char_box or answers['char_box']
                    answers['text_box'] = ln.value_text_box or answers['text_box']
                    answers['numerical_box'] = ln.value_numerical_box or answers['numerical_box']
                    answers['date'] = ln.value_date or answers['date']
                    answers['datetime'] = ln.value_datetime or answers['datetime']
                    answers['digital_signature'] = ln.digital_signature or answers['digital_signature']
                    answers['static_content'] = (
                        self._clean_html_unicode(ln.static_content)
                        or answers['static_content']
                    )

                # ---------------- STORE QUESTION ----------------
                grouped_data[group_id]['headings'][heading_id]['questions'].append({
                    'question_id': question.id,
                    'question_title': question.title,
                    'question_type': question.question_type,
                    'sequence': question.sequence,
                    'subtitle': question.subtitle,
                    'description': question.description,
                    'answers': answers,
                })

        # ================= SORT EVERYTHING =================

        grouped_list = []

        for grp in sorted(grouped_data.values(), key=lambda g: g['sequence']):

            headings_list = []

            for head in sorted(grp['headings'].values(), key=lambda h: h['sequence']):

                head['questions'] = sorted(
                    head['questions'],
                    key=lambda q: q['sequence']
                )

                headings_list.append(head)

            grp['headings'] = headings_list
            grouped_list.append(grp)

        return {
            'doc_ids': docids,
            'doc_model': 'survey.user_input',
            'docs': user_inputs,
            'grouped_data': grouped_list,
            'risk_register': risk_register,
        }