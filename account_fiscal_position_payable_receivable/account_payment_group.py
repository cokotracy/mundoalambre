from odoo import _, api, models, fields
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError

class AccountPaymentGroup(models.Model):
    _inherit = "account.payment.group"
    x_studio_es_canal_2 = fields.Boolean()

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
            index = 1
            for rec in self:
                if index == 1:    
                    rec.to_pay_move_line_ids = rec.env['account.move.line'].search(rec._get_to_pay_move_lines_domain())  
            index += 1 

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

    @api.depends(
        'payment_ids.tax_withholding_id',
        'payment_ids.amount',
    )
    def _compute_withholdings_amount(self):
        for rec in self:
            rec.withholdings_amount = sum(
                rec.payment_ids.filtered(
                    lambda x: x.tax_withholding_id).mapped('amount'))

    def compute_withholdings(self):
        if  self.x_studio_es_canal_2 == True:
            raise ValidationError('No se puede calcular retenciones en Canal 2')
        
        index = 1
        for rec in self.to_pay_move_line_ids:
            if index == 1:
                if rec.journal_id.x_studio_es_canal_2 == True:
                    raise ValidationError('No se puede calcular retenciones en Canal 2')
        index += 1 
        
        for rec in self:
            if rec.partner_type != 'supplier':
                continue
                # limpiamos el type por si se paga desde factura ya que el en ese
                # caso viene in_invoice o out_invoice y en search de tax filtrar
                # por impuestos de venta y compra (y no los nuestros de pagos
                # y cobros)
                self.env['account.tax'].with_context(type=None).search([
                    ('type_tax_use', '=', rec.partner_type),
                    ('company_id', '=', rec.company_id.id),
                ]).create_payment_withholdings(rec)

    def confirm(self):
        res = super(AccountPaymentGroup, self).confirm()
        for rec in self:
            if rec.company_id.automatic_withholdings:
                rec.compute_withholdings()
        return res

    def _get_withholdable_amounts(
            self, withholding_amount_type, withholding_advances):
        """ Method to help on getting withholding amounts from account.tax
        """
        self.ensure_one()
        # Por compatibilidad con public_budget aceptamos
        # pagos en otros estados no validados donde el matched y
        # unmatched no se computaron, por eso agragamos la condición
        if self.state == 'posted':
            untaxed_field = 'matched_amount_untaxed'
            total_field = 'matched_amount'
        else:
            untaxed_field = 'selected_debt_untaxed'
            total_field = 'selected_debt'

        if withholding_amount_type == 'untaxed_amount':
            withholdable_invoiced_amount = self[untaxed_field]
        else:
            withholdable_invoiced_amount = self[total_field]

        withholdable_advanced_amount = 0.0
        # if the unreconciled_amount is negative, then the user wants to make
        # a partial payment. To get the right untaxed amount we need to know
        # which invoice is going to be paid, we only allow partial payment
        # on last invoice.
        # If the payment is posted the withholdable_invoiced_amount is
        # the matched amount
        if self.withholdable_advanced_amount < 0.0 and \
                self.to_pay_move_line_ids and self.state != 'posted':
            withholdable_advanced_amount = 0.0

            sign = self.partner_type == 'supplier' and -1.0 or 1.0
            sorted_to_pay_lines = sorted(
                self.to_pay_move_line_ids,
                key=lambda a: a.date_maturity or a.date)

            # last line to be reconciled
            partial_line = sorted_to_pay_lines[-1]
            if sign * partial_line.amount_residual < \
                    sign * self.withholdable_advanced_amount:
                raise ValidationError(_(
                    'Seleccionó deuda por %s pero aparentente desea pagar '
                    ' %s. En la deuda seleccionada hay algunos comprobantes de'
                    ' mas que no van a poder ser pagados (%s). Deberá quitar '
                    ' dichos comprobantes de la deuda seleccionada para poder '
                    'hacer el correcto cálculo de las retenciones.' % (
                        self.selected_debt,
                        self.to_pay_amount,
                        partial_line.move_id.display_name,
                        )))

            if withholding_amount_type == 'untaxed_amount' and \
                    partial_line.move_id:
                invoice_factor = partial_line.move_id._get_tax_factor()
            else:
                invoice_factor = 1.0

            # si el adelanto es negativo estamos pagando parcialmente una
            # factura y ocultamos el campo sin impuesto ya que lo sacamos por
            # el proporcional descontando de el iva a lo que se esta pagando
            withholdable_invoiced_amount -= (
                sign * self.unreconciled_amount * invoice_factor)
        elif withholding_advances:
            # si el pago esta publicado obtenemos los valores de los importes
            # conciliados (porque el pago pudo prepararse como adelanto
            # pero luego haberse conciliado y en ese caso lo estariamos sumando
            # dos veces si lo usamos como base de otros pagos). Si estan los
            # campos withholdable_advanced_amount y unreconciled_amount le
            # sacamos el proporcional correspondiente
            if self.state == 'posted':
                if self.unreconciled_amount and \
                   self.withholdable_advanced_amount:
                    withholdable_advanced_amount = self.unmatched_amount * (
                        self.withholdable_advanced_amount /
                        self.unreconciled_amount)
                else:
                    withholdable_advanced_amount = self.unmatched_amount
            else:
                withholdable_advanced_amount = \
                    self.withholdable_advanced_amount
        return (withholdable_advanced_amount, withholdable_invoiced_amount)
