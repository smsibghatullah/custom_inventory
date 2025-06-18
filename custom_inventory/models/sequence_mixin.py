from odoo import models, api
from odoo.exceptions import ValidationError
from psycopg2 import DatabaseError
from odoo.tools import mute_logger


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _set_next_sequence(self):
        self.ensure_one()

        sequence_obj = self.env['ir.sequence'].search([
            ('code', '=', 'account.move'),
            ('company_id', '=', self.company_id.id),
        ], limit=1)

        if sequence_obj:
            next_seq = sequence_obj.next_by_id()
            if next_seq:
                self[self._sequence_field] = next_seq
                self._compute_split_sequence()
                self.flush_recordset(['sequence_prefix', 'sequence_number'])
                return

        # ✅ Final fallback using default logic
        last_sequence = self._get_last_sequence()
        new = not last_sequence
        if new:
            last_sequence = self._get_last_sequence(relaxed=True) or self._get_starting_sequence()

        format_string, format_values = self._get_sequence_format_param(last_sequence)
        sequence_number_reset = self._deduce_sequence_number_reset(last_sequence)

        if new:
            date_start, date_end = self._get_sequence_date_range(sequence_number_reset)
            format_values['seq'] = 0
            format_values['year'] = self._truncate_year_to_length(date_start.year, format_values['year_length'])
            format_values['year_end'] = self._truncate_year_to_length(date_end.year, format_values['year_end_length'])
            format_values['month'] = date_start.month

        self.flush_recordset()

        registry = self.env.registry
        triggers = registry._field_triggers[self._fields[self._sequence_field]]
        for inverse_field, triggered_fields in triggers.items():
            for triggered_field in triggered_fields:
                if not triggered_field.store or not triggered_field.compute:
                    continue
                for field in registry.field_inverses[inverse_field[0]] if inverse_field else [None]:
                    self.env.add_to_compute(triggered_field, self[field.name] if field else self)

        while True:
            format_values['seq'] += 1
            sequence = format_string.format(**format_values)
            try:
                with self.env.cr.savepoint(flush=False), mute_logger('odoo.sql_db'):
                    self[self._sequence_field] = sequence
                    self.flush_recordset([self._sequence_field])
                    break
            except DatabaseError as e:
                if e.pgcode not in ('23P01', '23505'):
                    raise e

        self._compute_split_sequence()
        self.flush_recordset(['sequence_prefix', 'sequence_number'])
