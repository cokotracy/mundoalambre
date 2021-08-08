##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _


class AccountJournal(models.Model):

    _inherit = 'account.journal'
    x_studio_canal_2 = fields.Boolean()