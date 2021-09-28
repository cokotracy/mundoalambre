from odoo import models, fields, api, _
from odoo.exceptions import UserError, Warning

class AccountMove(models.Model):
    _inherit = "account.move"

###agregado zolvant
    @api.onchange("journal_id")
    def _onchange_fiscal_position_allowed_journal(self):
        
        self.ensure_one()
        self.fiscal_position_id=''
        if self.journal_id.x_studio_es_canal_2 == True:
            
            domain = []
            domain.append(
                ("x_studio_es_canal_2", "=", True)
            )
            self.fiscal_position_id=self.env['account.fiscal.position'].search(domain, limit=1)
            self.fiscal_position_change()
        else:
            domain = []
            domain.append(
                ("x_studio_es_canal_2", "=", False)
            )
            new_fiscal_position_id = self.env['account.fiscal.position'].with_context(force_company=self.company_id.id).get_fiscal_position(
            self.partner_id.id, delivery_id=self.partner_id)
            self.fiscal_position_id = self.env['account.fiscal.position'].browse(new_fiscal_position_id)
            #zolvant
            #self.fiscal_position_id=self.env['account.fiscal.position'].search(domain, limit=1)
            
            self.fiscal_position_change()
            
        return {"domain": {"fiscal_position_id": domain}}   


    def _recompute_payment_terms_lines(self):
        ''' Compute the dynamic payment term lines of the journal entry.'''
        #raise Warning ("Se actualizara el calculo impositivo segun la posicion fiscal")
        self.ensure_one()
        in_draft_mode = self != self._origin
        today = fields.Date.context_today(self)
        self = self.with_context(force_company=self.journal_id.company_id.id)
        def _get_payment_terms_computation_date(self):
            ''' Get the date from invoice that will be used to compute the payment terms.
            :param self:    The current account.move record.
            :return:        A datetime.date object.
            '''
            if self.invoice_payment_term_id:
                return self.invoice_date or today
            else:
                return self.invoice_date_due or self.invoice_date or today




        def _get_payment_terms_account(self, payment_terms_lines):
                        
                        ''' Get the account from invoice that will be set as receivable / payable account.
                        :param self:                    The current account.move record.
                        :param payment_terms_lines:     The current payment terms lines.
                        :return:                        An account.account record.
                        '''
                        #si raise Warning ("Se actualizara el calculo impositivo segun la posicion fiscal")
                        if self.fiscal_position_id:
                            #si raise Warning ("Se actualizara el calculo impositivo segun la posicion fiscal")
                            #zolvant
                            #if payment_terms_lines:
                                #raise Warning ("Se actualizara el calculo impositivo segun la posicion fiscal")                     # Retrieve account from previous payment terms lines in order to allow the user to set a custom one.
                             #   return payment_terms_lines[0].account_id
                            if self.partner_id:
                                                    # Retrieve account from partner.
                                #si raise Warning ("Se actualizara el calculo impositivo segun la posicion fiscal")
                                if self.is_sale_document(include_receipts=True):
                                    #siraise Warning (self.fiscal_position_id.receivable_account_id.name)
                                    return self.fiscal_position_id.receivable_account_id
                                    
                                else:
                                    return self.fiscal_position_id.payable_account_id
                            #raise Warning ("Se actualizara el calculo impositivo segun la posicion fiscal")
                            else:
                                                    # Search new account.
                                domain = [
                                    ('company_id', '=', self.company_id.id),
                                    ('internal_type', '=', 'receivable' if self.type in ('out_invoice', 'out_refund', 'out_receipt') else 'payable'),
                                ]
                                return self.env['account.account'].search(domain, limit=1)
                        else:
                            #raise Warning ("Se actualizara el calculo impositivo segun la posicion fiscal")
                            if payment_terms_lines:
                                                    # Retrieve account from previous payment terms lines in order to allow the user to set a custom one.
                                return payment_terms_lines[0].account_id
                            elif self.partner_id:
                                                    # Retrieve account from partner.
                                if self.is_sale_document(include_receipts=True):
                                    return self.partner_id.commercial_partner_id.property_account_receivable_id
                                else:
                                    return self.partner_id.commercial_partner_id.property_account_payable_id
                            else:
                                                    # Search new account.
                                domain = [
                                        ('company_id', '=', self.company_id.id),
                                        ('internal_type', '=', 'receivable' if self.type in ('out_invoice', 'out_refund', 'out_receipt') else 'payable'),
                                ]
                                return self.env['account.account'].search(domain, limit=1)
        
        def _compute_payment_terms(self, date, total_balance, total_amount_currency):
            ''' Compute the payment terms.
            :param self:                    The current account.move record.
            :param date:                    The date computed by '_get_payment_terms_computation_date'.
            :param total_balance:           The invoice's total in company's currency.
            :param total_amount_currency:   The invoice's total in invoice's currency.
            :return:                        A list <to_pay_company_currency, to_pay_invoice_currency, due_date>.
            '''
            if self.invoice_payment_term_id:
                to_compute = self.invoice_payment_term_id.compute(total_balance, date_ref=date, currency=self.company_id.currency_id)
                if self.currency_id != self.company_id.currency_id:
                    # Multi-currencies.
                    to_compute_currency = self.invoice_payment_term_id.compute(total_amount_currency, date_ref=date, currency=self.currency_id)
                    return [(b[0], b[1], ac[1]) for b, ac in zip(to_compute, to_compute_currency)]
                else:
                    # Single-currency.
                    return [(b[0], b[1], 0.0) for b in to_compute]
            else:
                return [(fields.Date.to_string(date), total_balance, total_amount_currency)]

        def _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute):
            ''' Process the result of the '_compute_payment_terms' method and creates/updates corresponding invoice lines.
            :param self:                    The current account.move record.
            :param existing_terms_lines:    The current payment terms lines.
            :param account:                 The account.account record returned by '_get_payment_terms_account'.
            :param to_compute:              The list returned by '_compute_payment_terms'.
            '''
            # As we try to update existing lines, sort them by due date.
            existing_terms_lines = existing_terms_lines.sorted(lambda line: line.date_maturity or today)
            existing_terms_lines_index = 0

            # Recompute amls: update existing line or create new one for each payment term.
            new_terms_lines = self.env['account.move.line']
            
            
            for date_maturity, balance, amount_currency in to_compute:
                currency = self.journal_id.company_id.currency_id
                if currency and currency.is_zero(balance) and len(to_compute) > 1:
                    continue

                if existing_terms_lines_index < len(existing_terms_lines):
                    # Update existing line.
                    
                    candidate = existing_terms_lines[existing_terms_lines_index]
                    existing_terms_lines_index += 1
                    candidate.update({
                        'date_maturity': date_maturity,
                        #zolvant
                        'account_id': account.id,
                        #zvt
                        'amount_currency': -amount_currency,
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                    })
                    
                else:
                    # Create new line.
                    create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
                    candidate = create_method({
                        'name': self.invoice_payment_ref or '',
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                        'quantity': 1.0,
                        'amount_currency': -amount_currency,
                        'date_maturity': date_maturity,
                        'move_id': self.id,
                        'currency_id': self.currency_id.id if self.currency_id != self.company_id.currency_id else False,
                        'account_id': account.id,
                        'partner_id': self.commercial_partner_id.id,
                        'exclude_from_invoice_tab': True,
                    })
                    
                new_terms_lines += candidate
                if in_draft_mode:
                    candidate._onchange_amount_currency()
                    candidate._onchange_balance()
            return new_terms_lines

        existing_terms_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        others_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
        company_currency_id = (self.company_id or self.env.company).currency_id
        total_balance = sum(others_lines.mapped(lambda l: company_currency_id.round(l.balance)))
        total_amount_currency = sum(others_lines.mapped('amount_currency'))

        if not others_lines:
            self.line_ids -= existing_terms_lines
            return

        computation_date = _get_payment_terms_computation_date(self)
        account = _get_payment_terms_account(self, existing_terms_lines)



        to_compute = _compute_payment_terms(self, computation_date, total_balance, total_amount_currency)
        new_terms_lines = _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute)


        # Remove old terms lines that are no longer needed.
        self.line_ids -= existing_terms_lines - new_terms_lines
        #
        if new_terms_lines:

            self.invoice_payment_ref = new_terms_lines[-1].name or ''
            self.invoice_date_due = new_terms_lines[-1].date_maturity


#####################################
###UPDATE

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        fiscal_position = self.fiscal_position_id
        res = super()._onchange_partner_id()
        if fiscal_position != self.fiscal_position_id:
            self.fiscal_position_change()
        return res

    @api.onchange("fiscal_position_id")
    def fiscal_position_change(self):
        #raise Warning ("Ejecuta fpos")
        """Updates taxes and accounts on all invoice lines"""
        self.ensure_one()
        res = {}
        lines_without_product = []
        fp = self.fiscal_position_id
        inv_type = self.type
        invoice_lines = self.invoice_line_ids.filtered(lambda l: not l.display_type)
        for line in invoice_lines:
            if line.product_id:
                account = line._get_computed_account()
                product = line.with_context(force_company=self.company_id.id).product_id
                if inv_type in ("out_invoice", "out_refund"):
                    # M2M fields don't have an option 'company_dependent=True'
                    # so we need per-company post-filtering
                    taxes = product.taxes_id.filtered(
                        lambda tax: tax.company_id == self.company_id
                    )
                else:
                    taxes = product.supplier_taxes_id.filtered(
                        lambda tax: tax.company_id == self.company_id
                    )
                taxes = taxes or account.tax_ids.filtered(
                    lambda tax: tax.company_id == self.company_id
                )
                if fp:
                    taxes = fp.map_tax(taxes)
                line.recompute_tax_line = True
                line.tax_ids = [(6, 0, taxes.ids)]
                
                line.account_id = account.id
                #
                #line.name = line._get_computed_name()
                #line.account_id = line._get_computed_account()
                #raise Warning ("por aca dentro del if1")
                #line.price_unit = line._get_computed_price_unit()
                #raise Warning (line.price_unit)
                taxes = line._get_computed_taxes()
                if taxes and line.move_id.fiscal_position_id:
                    taxes = line.move_id.fiscal_position_id.map_tax(taxes, partner=line.partner_id)
                line.tax_ids = taxes
                line.price_unit = line._get_computed_price_unit()
                line.product_uom_id = line._get_computed_uom()
                line._onchange_price_subtotal()
                
            else:
                lines_without_product.append(line.name)
        #raise Warning ("Ejecuta")
        
        #raise Warning ("Ejecuta")
        
        self._recompute_dynamic_lines( recompute_tax_base_amount=True, recompute_all_taxes=True) #
        #recompute_all_taxes=True,
        self._recompute_payment_terms_lines()
        
        #if lines_without_product:
         #   res["warning"] = {"title": _("Warning")}
          #  if len(lines_without_product) == len(invoice_lines):
           #     res["warning"]["message"] = _(
            #        "The invoice lines were not updated to the new "
             #       "Fiscal Position because they don't have products. "
              #      "You should update the Account and the Taxes of each "
               #     "invoice line manually."
               # )
            ##   res["warning"]["message"] = _(
              #      "The following invoice lines were not updated "
               #     "to the new Fiscal Position because they don't have a "
                #    "Product: - %s You should update the Account and the "
                 #   "Taxes of these invoice lines manually."
                #) % ("- ".join(lines_without_product))
        #return res

    
    