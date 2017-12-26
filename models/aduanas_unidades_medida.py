# -*- coding: utf-8 -*-
from openerp import fields, models, api, _

class AduanasUnidadesMedida(models.Model):
    _name = 'aduanas.unidades_medida'

    name = fields.Char(
            string="Código Aduanas",
        )
    codigo_arancelario = fields.Char(
            string= 'Código Arancelario',
        )
    descripcion = fields.Char(
            string="Descripción",
        )
    sigla = fields.Char(
            string="Sigla a indicar en la declaración",
        )
