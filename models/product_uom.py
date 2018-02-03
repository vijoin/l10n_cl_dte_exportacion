# -*- coding: utf-8 -*-
from openerp import fields, models, api, _

class AduanasUnidadesMedida(models.Model):
    _inherit = 'product.uom'

    code = fields.Char(
            string="Código Aduanas",
        )
