from odoo import models, fields, api, _
# import odoo.tools as tools
try:
    from pyafipws.iibb import IIBB
except ImportError:
    IIBB = None
# from pyafipws.padron import PadronAFIP
from odoo.exceptions import UserError
import logging
import json
import requests
# from dateutil.relativedelta import relativedelta
_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"
    
    def get_agip_data(self, partner, date):
        raise UserError(_(
            'El cliente/proveedor no tiene configurada correctamente la alicuota para la jurisdiccion en el periodo facturado. Ingrese la alciuota correspondiente e intente de nuevo'))