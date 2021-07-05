# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountInvoiceLine(models.Model):
	_inherit = 'account.move.line'

	secondary_uom_id = fields.Many2one('uom.uom', compute='_quantity_secondary_compute', string="Secondary UOM", store=True)
	secondary_quantity = fields.Float('Secondary Qty', compute='_quantity_secondary_compute', digits='Product Unit of Measure', store=True)

	@api.depends('product_id', 'quantity', 'product_uom_id')
	def _quantity_secondary_compute(self):
		for order in self:
			if order.product_id.is_secondary_uom:
				uom_quantity = order.product_id.uom_id._compute_quantity(order.quantity, order.product_id.secondary_uom_id, rounding_method='HALF-UP')  * order.product_id.weight
				order.update({'secondary_uom_id' : order.product_id.secondary_uom_id})
				order.update({'secondary_quantity' : uom_quantity})
			else:
				order.update({'secondary_uom_id' : False})
				order.update({'secondary_quantity' : 0.0})