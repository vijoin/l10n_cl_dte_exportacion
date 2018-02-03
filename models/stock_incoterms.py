# -*- coding: utf-8 -*-
from openerp import fields, models, api, _

class Incoterms(models.Model):
    _inherit = "stock.incoterms"

    aduanas_code = fields.Integer(
            string="Código de aduanas"
        )
