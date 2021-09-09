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
            self.fiscal_position_change()
            
        return {"domain": {"fiscal_position_id": domain}}   


    def _recompute_payment_terms_lines(self):
        ''' Compute the dynamic payment term lines of the journal entry.'''
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
                        if self.fiscal_position_id:
                            if payment_terms_lines:
                                                    # Retrieve account from previous payment terms lines in order to allow the user to set a custom one.
                                return payment_terms_lines[0].account_id
                            elif self.partner_id:
                                                    # Retrieve account from partner.
                                if self.is_sale_document(include_receipts=True):
                                    return self.fiscal_position_id.receivable_account_id
                                else:
                                    return self.fiscal_position_id.payable_account_id
                            else:
                                                    # Search new account.
                                domain = [
                                    ('company_id', '=', self.company_id.id),
                                    ('internal_type', '=', 'receivable' if self.type in ('out_invoice', 'out_refund', 'out_receipt') else 'payable'),
                                ]
                                return self.env['account.account'].search(domain, limit=1)
                        else:
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

        if new_terms_lines:
            self.invoice_payment_ref = new_terms_lines[-1].name or ''
            self.invoice_date_due = new_terms_lines[-1].date_maturity
            

            
    def _get_computed_price_unit(self):
        ''' Helper to get the default price unit based on the product by taking care of the taxes
        set on the product and the fiscal position.
        :return: The price unit.
        '''
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

        if self.move_id.is_sale_document(include_receipts=True):
            product_price_unit = self.product_id.lst_price
            product_taxes = self.product_id.taxes_id
        elif self.move_id.is_purchase_document(include_receipts=True):
            product_price_unit = self.product_id.standard_price
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
                    )
                    product_price_unit = company_currency.round(taxes_res['total_excluded'])

                flattened_taxes_after_fp = product_taxes_after_fp._origin.flatten_taxes_hierarchy()
                if any(tax.price_include for tax in flattened_taxes_after_fp):
                    taxes_res = flattened_taxes_after_fp.compute_all(
                        product_price_unit,
                        quantity=1.0,
                        currency=company_currency,
                        product=self.product_id,
                        partner=self.partner_id,
                        is_refund=is_refund_document,
                        handle_price_include=False,
                    )
                    for tax_res in taxes_res['taxes']:
                        tax = self.env['account.tax'].browse(tax_res['id'])
                        if not tax.price_include:
                            product_price_unit -= tax_res['amount']

        # Apply currency rate.
        if currency and currency != company_currency:
            product_price_unit = company_currency._convert(product_price_unit, currency, company, move_date)

        return product_price_unit

            