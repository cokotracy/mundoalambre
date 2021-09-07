    
# Copyright 2020 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import UserError
    
class AccountPayment(models.Model):
    _inherit = "account.payment"
 
    
    

    def get_journals_domain(self):
        domain = super(AccountPayment, self).get_journals_domain()
        #domain.append(('x_studio_es_canal_2', '=', False)) 
        if self.payment_group_company_id:
            domain.append(
                ('company_id', '=', self.payment_group_company_id.id))
        #con las prox lineas comentadas funciona ok
        if self.payment_group_id.to_pay_move_line_ids:
            index = 1
            for rec in self.payment_group_id.to_pay_move_line_ids:
                if index == 1:
                    if rec.journal_id.x_studio_es_canal_2 == True:
                        domain.append(('x_studio_es_canal_2', '=', True))    
                    else:
                            #if self.payment_group_id.to_pay_move_line_ids.journal_id.search([('x_studio_es_canal_2','=',False)], limit=1).x_studio_es_canal_2  == False:
                        domain.append(('x_studio_es_canal_2', '=', False))    
                    return domain
            index += 1
        else:
            if self.payment_group_id.x_studio_es_canal_2 == True: 
                domain.append(('x_studio_es_canal_2', '=', True))
            else:
                domain.append(('x_studio_es_canal_2', '=', False)) 
            return domain
        
        
    
    def _compute_journal_domain_and_types(self):
        journal_type = ['bank', 'cash']
        domain = [('x_studio_es_canal_2', '=', True)]
        if self.invoice_ids:
            domain.append(('company_id', '=', self.invoice_ids[0].company_id.id))
            if self.invoice_ids.journal_id.x_studio_es_canal_2 == True or self.x_studio_es_canal_2:
                domain.append(('x_studio_es_canal_2', '=', True))
        if self.currency_id.is_zero(self.amount) and self.has_invoices:
            # In case of payment with 0 amount, allow to select a journal of type 'general' like
            # 'Miscellaneous Operations' and set this journal by default.
            journal_type = ['general']
            self.payment_difference_handling = 'reconcile'
        else:
            if self.payment_type == 'inbound':
                domain.append(('at_least_one_inbound', '=', True))
            else:
                domain.append(('at_least_one_outbound', '=', True))
        return {'domain': domain, 'journal_types': set(journal_type)}