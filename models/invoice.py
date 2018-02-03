# -*- coding: utf-8 -*-
from openerp import fields, models, api, _

from openerp.exceptions import UserError
from datetime import datetime, timedelta, date
import os
import logging
from lxml import etree
from lxml.etree import Element, SubElement
from openerp import SUPERUSER_ID

import pytz
import collections

_logger = logging.getLogger(__name__)

try:
    import xmltodict
except ImportError:
    _logger.warning('Cannot import xmltodict library')

try:
    import dicttoxml
except ImportError:
    _logger.warning('Cannot import dicttoxml library')

try:
    import base64
except ImportError:
    _logger.warning('Cannot import base64 library')

class Exportacion(models.Model):
    _inherit = "account.invoice"

    exportacion = fields.One2many(
        string="Exportación",
        comodel_name="account.invoice.exportacion",
        inverse_name="invoice_id",
        context={"form_view_ref": "l10n_cl_exportacion.exportacion_view_form"},
        help="Explain your field.",
        readonly=True,
        states={'draft': [('readonly', False)]},
    )

    def format_vat(self, value, con_cero=False):
        if self._es_exportacion() and not value or value=='' or value == 0:
            value = "CL555555555"
        return super(Exportacion, self).format_vat(value, con_cero)

    @api.multi
    def crear_exportacion(self):
        self.exportacion = [(5,), (0,0,{
                    'pais_destino': self.commercial_partner_id.country_id.id,

                })]

    def _es_exportacion(self):
        if self.sii_document_class_id.sii_code in [ 110, 111, 112 ]:
            return True
        return False

    def _bultos(self, bultos):
        Bultos = []
        for b in bultos:
            Bulto = dict()
            Bulto['TipoBultos'] = collections.OrderedDict()
            Bulto['TipoBultos']['CodTpoBultos'] = bultos.tipo_bulto.code
            Bulto['TipoBultos']['CantBultos'] = bultos.cantidad_bultos
            Bultos.append(Bulto)
        return Bultos

    def _aduana(self):
        expo = self.exportacion
        Aduana = collections.OrderedDict()
        #if not in 3,4,5
        Aduana['CodModVenta'] = self.payment_term_id.forma_pago_aduanas.code
        if self.incoterms_id:
            Aduana['CodClauVenta'] = self.incoterms_id.aduanas_code
        mnt_clau = 0
        Aduana['TotClauVenta'] = round(self.payment_term_id.compute(self.amount_total), 2)
        if expo.via:
            Aduana['CodViaTransp'] = expo.via.code
        if expo.chofer_id:
            Aduana['NombreTransp'] = expo.chofer_id.name
        if expo.carrier_id:
            Aduana['RUTCiaTransp'] = self.format_vat(expo.carrier_id.partner_id.vat)
        if expo.carrier_id:
            Aduana['NomCiaTransp'] = expo.carrier_id.name
        #Aduana['IdAdicTransp'] = self.indicador_adicional
        if expo.puerto_embarque:
            Aduana['CodPtoEmbarque'] = expo.puerto_embarque.code
        #Aduana['IdAdicPtoEmb'] = expo.ind_puerto_embarque
        if expo.puerto_desembarque:
            Aduana['CodPtoDesemb'] = expo.puerto_desembarque.code
        #Aduana['IdAdicPtoDesemb'] = expo.ind_puerto_desembarque
        if expo.tara:
            Aduana['Tara'] = expo.tara
            Aduana['CodUnidMedTara'] = expo.uom_tara.code
        if expo.peso_bruto:
            Aduana['PesoBruto'] = round(expo.peso_bruto, 2)
            Aduana['CodUnidPesoBruto'] = expo.uom_peso_bruto.code
        if expo.peso_neto:
            Aduana['PesoNeto'] = round(expo.peso_neto, 2)
            Aduana['CodUnidPesoNeto'] = expo.uom_peso_neto.code
        if expo.total_items:
            Aduana['TotItems'] = expo.total_items
        if expo.total_bultos:
            Aduana['TotBultos'] = expo.total_bultos
            Aduana['item'] = self._bultos(expo.bultos)
        #Aduana['Marcas'] =
        #Solo si es contenedor
        #Aduana['IdContainer'] =
        #Aduana['Sello'] =
        #Aduana['EmisorSello'] =
        Aduana['MntFlete'] = expo.monto_flete
        Aduana['MntSeguro'] = expo.monto_seguro
        Aduana['CodPaisRecep'] = expo.pais_recepcion.name
        Aduana['CodPaisDestin'] = expo.pais_destino.code
        return Aduana

    def _transporte(self):
        Transporte = collections.OrderedDict()
        expo = self.exportacion
        if expo.carrier_id:
            if self.patente:
                Transporte['Patente'] = self.patente[:8]
            elif self.vehicle:
                Transporte['Patente'] = self.vehicle.matricula or ''
            if self.transport_type in ['2','3'] and self.chofer:
                if not self.chofer.vat:
                    raise UserError("Debe llenar los datos del chofer")
                if self.transport_type == '2':
                    Transporte['RUTTrans'] = self.format_vat(self.company_id.vat)
                else:
                    if not self.carrier_id.partner_id.vat:
                        raise UserError("Debe especificar el RUT del transportista, en su ficha de partner")
                    Transporte['RUTTrans'] = self.format_vat(self.carrier_id.partner_id.vat)
                if self.chofer:
                    Transporte['Chofer'] = collections.OrderedDict()
                    Transporte['Chofer']['RUTChofer'] = self.format_vat(self.chofer.vat)
                    Transporte['Chofer']['NombreChofer'] = self.chofer.name[:30]
        partner_id = self.partner_id or self.company_id.partner_id
        Transporte['DirDest'] = (partner_id.street or '')+ ' '+ (partner_id.street2 or '')
        Transporte['CmnaDest'] = partner_id.state_id.name or ''
        Transporte['CiudadDest'] = partner_id.city or ''
        Transporte['Aduana'] = self._aduana()
        return Transporte

    def _encabezado(self, MntExe=0, no_product=False, taxInclude=False):
        res = super(Exportacion, self)._encabezado(MntExe, no_product, taxInclude)
        if not self._es_exportacion():
            return res
        result = collections.OrderedDict()
        for key, value in res.iteritems():
            result[key] = value
            if key == 'Receptor':
                result['Transporte'] = self._transporte()
        return result

    def _tpo_dte(self):
        if self._es_exportacion():
            return 'Exportaciones'
        return super(Exportacion, self)._tpo_dte()
