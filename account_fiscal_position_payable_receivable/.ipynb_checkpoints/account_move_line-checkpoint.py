from odoo import models, fields, api, _
from odoo.exceptions import UserError, Warning


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_computed_price_unit(self):
        ''' Helper to get the default price unit based on the product by taking care of the taxes
        set on the product and the fiscal position.
        :return: The price unit.
        '''
        #raise Warning ("ejecuta")
        self.ensure_one()

        if not self.product_id:
            return 0.0

        company = self.move_id.company_id
        currency = self.move_id.currency_id
        company_currency = company.currency_id
        product_uom = self.product_id.uom_id
        fiscal_position = self.move_id.fiscal_position_id
        is_refund_document = self.move_id.type in ('out_refund', 'in_refund')
        move_date = self.move_id.date or fields.Date.context_today(self)
        product_price_unit=self.price_unit
        
        if self.move_id.is_sale_document(include_receipts=True) and self.price_unit==0:
            product_price_unit = self.product_id.lst_price
            product_taxes = self.product_id.taxes_id
        elif self.move_id.is_sale_document(include_receipts=True) and self.price_unit!=0:
            #product_price_unit=self.price_unit
            product_taxes = self.product_id.taxes_id
        elif self.move_id.is_purchase_document(include_receipts=True)and self.price_unit==0:
            product_price_unit = self.product_id.standard_price
            product_taxes = self.product_id.supplier_taxes_id
        elif self.move_id.is_purchase_document(include_receipts=True)and self.price_unit!=0:
            #product_price_unit = self.product_id.standard_price
            product_taxes = self.product_id.supplier_taxes_id
        
        else:
            return 0.0
        product_taxes = product_taxes.filtered(lambda tax: tax.company_id == company)

        # Apply unit of measure.
        if self.product_uom_id and self.product_uom_id != product_uom:
            product_price_unit = product_uom._compute_price(product_price_unit, self.product_uom_id)

        # Apply fiscal position.
        if product_taxes and fiscal_position:
            product_taxes_after_fp = fiscal_position.map_tax(product_taxes, partner=self.partner_id)
            #raise Warning (product_taxes_after_fp.name)
            if set(product_taxes.ids) != set(product_taxes_after_fp.ids):
                flattened_taxes_before_fp = product_taxes._origin.flatten_taxes_hierarchy()
                if any(tax.price_include for tax in flattened_taxes_before_fp):
                    taxes_res = flattened_taxes_before_fp.compute_all(
                        product_price_unit,
                        quantity=1.0,
                        currency=company_currency,
                        product=self.product_id,
                        partner=self.partner_id,
                        is_refund=is_refund_document,
                        handle_price_include=False,
                    )
                    product_price_unit = company_currency.round(taxes_res['total_excluded'])
                    for tax_res in taxes_res['taxes']:
                        tax = self.env['account.tax'].browse(tax_res['id'])
                        #raise Warning (tax_res['amount']) 
                flattened_taxes_after_fp = product_taxes_after_fp._origin.flatten_taxes_hierarchy()
                price_subtotal=product_price_unit
                if any(tax.price_include for tax in flattened_taxes_after_fp):
                    taxes_res = flattened_taxes_after_fp.compute_all(
                        product_price_unit,
                        quantity=1.0,
                        currency=company_currency,
                        product=self.product_id,
                        partner=self.partner_id,
                        is_refund=is_refund_document,
                        handle_price_include=True,

                    )
                    
                    for tax_res in taxes_res['taxes']:
                        tax = self.env['account.tax'].browse(tax_res['id'])
                        if tax.price_include:
                            product_price_unit += 0 #tax_res['amount']
                            #raise Warning (tax_res['amount'])
                    #for tax_res in taxes_res['taxes']:
                    #    tax = self.env['account.tax'].browse(tax_res['id'])
                    #    if  not tax.price_include:
                    #        product_price_unit += tax_res['amount']
                    #    else:
                    #        product_price_unit += tax_res['amount']
                            
        # Apply currency rate.
        if currency and currency != company_currency:
            product_price_unit = company_currency._convert(product_price_unit, currency, company, move_date)
        
        #self.move_id._recompute_dynamic_lines(recompute_tax_base_amount=True)
        self.move_id._recompute_dynamic_lines(recompute_all_taxes=False, recompute_tax_base_amount=True)
        return product_price_unit
        
