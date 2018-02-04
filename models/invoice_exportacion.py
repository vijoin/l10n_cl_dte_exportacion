# -*- coding: utf-8 -*-
from openerp import fields, models, api, _

class Exportacion(models.Model):
    _name = "account.invoice.exportacion"

    @api.depends('bultos')
    @api.onchange('bultos')
    def total_bultos(self):
        for r in self:
            tot_bultos = 0
            for b in r.bultos:
                tot_bultos += b.cantidad_bultos
            r.total_bultos = tot_bultos

    @api.depends('invoice_id.global_descuentos_recargos')
    @api.onchange('invoice_id.global_descuentos_recargos')
    def _get_tot_from_recargos(self):
        for r in self:
            mnt_seguro = 0
            mnt_flete = 0
            for gdr in r.invoice_id.global_descuentos_recargos:
                if gdr.aplicacion == 'flete':
                    mnt_flete += gdr.valor
                elif gdr.aplicacion == 'seguro':
                    mnt_seguro += gdr.valor
            r.monto_flete = mnt_flete
            r.monto_seguro = mnt_seguro

    pais_destino = fields.Many2one(
            'aduanas.paises',
            string='País de Destino',
        )
    puerto_embarque = fields.Many2one(
            'aduanas.puertos',
            string='Puerto Embarque',
        )
    puerto_desembarque = fields.Many2one(
            'aduanas.puertos',
            string='Puerto de Desembarque',
        )
    total_items = fields.Integer(
            string="Total Items",
        )
    total_bultos = fields.Integer(
            string="Total Bultos",
            compute='total_bultos',
            store=True,
        )
    bultos = fields.One2many(
        string="Bultos",
        comodel_name="account.invoice.exportacion.bultos",
        inverse_name="exportacion_id",
    )
    via = fields.Many2one(
            'aduanas.tipos_transporte',
            string='Vía',
        )
    carrier_id = fields.Many2one(
            'delivery.carrier',
            string="Transporte",
        )
    tara = fields.Integer(
            string="Tara",
        )
    uom_tara = fields.Many2one(
            'product.uom',
            string='Unidad Medida Tara',
        )
    peso_bruto = fields.Float(
            string="Peso Bruto",
        )
    uom_peso_bruto = fields.Many2one(
            'product.uom',
            string='Unidad Medida Peso Bruto',
        )
    peso_neto = fields.Float(
            string="Peso Neto",
        )
    uom_peso_neto = fields.Many2one(
            'product.uom',
            string='Unidad Medida Peso Neto',
        )
    monto_flete = fields.Monetary(
            string="Monto Flete",
            compute='_get_tot_from_recargos',
        )
    monto_seguro = fields.Monetary(
            string="Monto Seguro",
            compute='_get_tot_from_recargos',
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
            related='invoice_id.currency_id',
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

class Bultos(models.Model):
    _name = 'account.invoice.exportacion.bultos'

    tipo_bulto = fields.Many2one(
            'aduanas.tipos_bulto',
            string='Tipo de Bulto',
        )
    cantidad_bultos = fields.Integer(
            string="Cantidad de Bultos",
        )
    exportacion_id = fields.Many2one(
            'account.invoice.exportacion',
        )
