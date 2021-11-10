# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug import urls

from odoo import api, models
from odoo.exceptions import UserError, Warning


class SalePaymentLink(models.TransientModel):
    _inherit = "payment.link.wizard"
    _description = "Generate Sales Payment Link"

    def _generate_link(self):
        """ Override of the base method to add the order_id in the link. """
        for payment_link in self:
            # only add order_id for SOs,
            # otherwise the controller might try to link it with an unrelated record
            # NOTE: company_id is not necessary here, we have it in order_id
            # however, should parsing of the id fail in the controller, let's include
            # it anyway
            if payment_link.res_model == 'sale.order':
                domain = [("company_id.id", "=", self.company_id.id)]
                #raise Warning (self.company_id.name)
                url=self.env['res.config.settings'].search(domain, limit=1)
                #raise Warning (url.website_domain)
                record = self.env[payment_link.res_model].browse(payment_link.res_id)          
                if url.website_domain:
                    url_company=url.website_domain
                else:
                    url_company=record.get_base_url()
                                                                 
                payment_link.link = ('%s/website_payment/pay?reference=%s&amount=%s&currency_id=%s'
                                    '&partner_id=%s&order_id=%s&company_id=%s&access_token=%s') % (
                                        
                                        #record.get_base_url(),
                                        #url.website_domain, 
                                        url_company,
                                        urls.url_quote_plus(payment_link.description),
                                        payment_link.amount,
                                        payment_link.currency_id.id,
                                        payment_link.partner_id.id,
                                        payment_link.res_id,
                                        payment_link.company_id.id,
                                        payment_link.access_token
                                    )
            else:
                super(SalePaymentLink, payment_link)._generate_link()