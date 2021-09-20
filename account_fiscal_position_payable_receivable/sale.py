from datetime import datetime, timedelta
from functools import partial
from itertools import groupby

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError, Warning
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare

from werkzeug.urls import url_encode


class SaleOrder(models.Model):
    _inherit = "sale.order"

   # @api.model
    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        # ensure a correct context for the _get_default_journal method and company-dependent fields
        self = self.with_context(default_company_id=self.company_id.id, force_company=self.company_id.id)
        domain_journal = [('type', '=', 'sale'),('x_studio_es_canal_2', '=',True)]
        if self.fiscal_position_id.x_studio_es_canal_2 == True:
            journal = self.env['account.journal'].search(domain_journal, limit=1)
            #journal = self.env['account.move'].with_context(default_type='out_invoice')._get_default_journal()
        else:
            journal = self.env['account.move'].with_context(default_type='out_invoice')._get_default_journal()
        
        
        if not journal:
            raise UserError(_('Please define an accounting sales journal for the company %s (%s).') % (self.company_id.name, self.company_id.id))

        invoice_vals = {
            'ref': self.client_order_ref or '',
            'type': 'out_invoice',
            'narration': self.note,
            'currency_id': self.pricelist_id.currency_id.id,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'user_id': self.user_id.id,
            'invoice_user_id': self.user_id.id,
            'team_id': self.team_id.id,
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'invoice_partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
            'fiscal_position_id': self.fiscal_position_id.id or self.partner_invoice_id.property_account_position_id.id,
            'journal_id': journal.id,  # company comes from the journal
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_payment_ref': self.reference,
            'transaction_ids': [(6, 0, self.transaction_ids.ids)],
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
        }
        return invoice_vals
    
    
##agregado zolvant Actualizacion de precios al cambiar la lista de precios. 

    @api.onchange('pricelist_id')
    def change_price(self):
        #raise Warning ("pasa por aca")
        if not self.pricelist_id:
            return
        vals = {}
        for line in self.order_line:
            vals.update(name=line.get_sale_order_line_multiline_description_sale(line.product_id))

            line._compute_tax_id()

            if line.order_id.pricelist_id and line.order_id.partner_id:
                vals['price_unit'] = line.env['account.tax']._fix_tax_included_price_company(line._get_display_price(line.product_id), line.product_id.taxes_id, line.tax_id, line.company_id)
            line.update(vals)
