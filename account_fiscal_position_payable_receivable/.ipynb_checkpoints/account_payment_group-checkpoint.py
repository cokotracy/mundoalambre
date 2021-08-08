from odoo import _, api, models, fields
from odoo.exceptions import UserError
    
class AccountPaymentGroup(models.Model):
    _inherit = "account.payment.group"
    x_studio_canal_2 = fields.Boolean()

    def _compute_canal(self):
            index = 1
            for record in self.to_pay_move_line_ids:
                if index == 1:
                    if record.journal_id.x_studio_es_canal_2 == True:
                        record.x_studio_es_canal_2 = True
                    else:
                        record.x_studio_es_canal_2 = False 
            index += 1 
    @api.onchange('x_studio_es_canal_2')
    def _inverse_to_pay_amount(self):
        if self.pop_up == False:
            for rec in self:
                rec.to_pay_move_line_ids = rec.env['account.move.line'].search(rec._get_to_pay_move_lines_domain())  


    def _get_to_pay_move_lines_domain(self):
        self.ensure_one()
        if self.x_studio_es_canal_2 == True:
            return [
                ('partner_id.commercial_partner_id', '=',
                    self.commercial_partner_id.id),
                ('account_id.internal_type', '=',
                    self.account_internal_type),
                ('account_id.reconcile', '=', True),
                ('reconciled', '=', False),
                ('full_reconcile_id', '=', False),
                ('company_id', '=', self.company_id.id),
                ('move_id.state', '=', 'posted'), 
                ('journal_id.x_studio_es_canal_2', '=', True)

                # '|',
                # ('amount_residual', '!=', False),
                # ('amount_residual_currency', '!=', False),
            ]
        else:
            return [
                ('partner_id.commercial_partner_id', '=',
                    self.commercial_partner_id.id),
                ('account_id.internal_type', '=',
                    self.account_internal_type),
                ('account_id.reconcile', '=', True),
                ('reconciled', '=', False),
                ('full_reconcile_id', '=', False),
                ('company_id', '=', self.company_id.id),
                ('move_id.state', '=', 'posted'), 
                ('journal_id.x_studio_es_canal_2', '=', False)

                # '|',
                # ('amount_residual', '!=', False),
                # ('amount_residual_currency', '!=', False),
            ]
