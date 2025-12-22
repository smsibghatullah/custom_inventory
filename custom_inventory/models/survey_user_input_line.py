from odoo import models, fields,_

class SurveyUserInputLine(models.Model):
    _inherit = 'survey.user_input.line'

    digital_signature = fields.Binary("Digital Signature")
    static_content = fields.Html("Static Content") 
    answer_type = fields.Selection(selection_add=[
        ('digital_signature', 'Digital Signature'),
        ('static_content', 'Static Content') 
    ])

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
            elif line.answer_type == 'suggestion':
                if line.matrix_row_id:
                    line.display_name = f'{line.suggested_answer_id.value}: {line.matrix_row_id.value}'
                else:
                    line.display_name = line.suggested_answer_id.value

            if not line.display_name:
                line.display_name = _('Skipped')


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

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

    
