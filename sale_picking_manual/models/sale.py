# -*- coding: utf-8 -*-

from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _action_launch_stock_rule(self):
        create_delivery = self._context.get('create_delivery')
        if create_delivery:
            res = super(SaleOrderLine,self)._action_launch_stock_rule()
            return res
        return True