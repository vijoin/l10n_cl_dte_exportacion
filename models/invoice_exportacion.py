# -*- coding: utf-8 -*-
from openerp import fields, models, api, _

class Exportacion(models.Model):
    _name = "account.invoice.exportacion"

    pais_destino = fields.Many2one(
            'aduanas.paises',
            string='País de Destino',
        )
    puerto_embarque = fields.Many2one(
            'aduanas.puertos',
            string='Puerto Embarque',
        )
    puerto_destino = fields.Many2one(
            'aduanas.puertos',
            string='Puerto de Destino',
        )
    total_bultos = fields.Float(
            string="Total Bultos",
        )
    tipo_bulto = fields.Many2one(
            'aduanas.tipos_bulto',
            string='Tipo de Bulto',
        )
    total_items = fields.Float(
            string="Total Items",
        )
    cantidad_bultos = fields.Float(
            string="Cantidad de Bultos",
        )
    via = fields.Many2one(
            'aduanas.tipos_transporte',
            string='Vía',
        )
    carrier_id = fields.Many2one(
            'delivery.carrier',
            string="Transporte",
        )
    tara = fields.Float(
            string="Tara",
        )
    uom_tara = fields.Many2one(
            'aduanas.unidades_medida',
            string='Unidad Medida Tara',
        )
    peso_bruto = fields.Float(
            string="Peso Bruto",
        )
    uom_peso_bruto = fields.Many2one(
            'aduanas.unidades_medida',
            string='Unidad Medida Peso Bruto',
        )
    peso_neto = fields.Float(
            string="Peso Neto",
        )
    uom_peso_neto = fields.Many2one(
            'aduanas.unidades_medida',
            string='Unidad Medida Peso Neto',
        )
    monto_flete = fields.Monetary(
            string="Monto Flete",
        )
    monto_seguro = fields.Monetary(
            string="Monto Seguro",
        )
    pais_recepcion = fields.Many2one(
            'aduanas.paises',
            string='País de Recepción',
        )
    chofer_id = fields.Many2one(
            'res.partner',
            string="Chofer"
        )
    invoice_id = fields.Many2one(
            'account.invoice',
            string="Factura",
            ondelete="cascade",
        )
    currency_id = fields.Many2one(
            'res.currency',
            related='invoice_id',
            string='Moneda'
        )

    @api.onchange('carrier_id')
    def set_chofer(self):
        if not self.chofer_id:
            self.chofer_id = self.carrier_id.partner_id

    @api.onchange('pais_destino')
    def set_recepcion(self):
        if not self.pais_recepcion:
            self.pais_recepcion = self.pais_destino
