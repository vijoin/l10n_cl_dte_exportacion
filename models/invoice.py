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
        self.exportacion = [(5),(0,0,{'invoice_id':self.id})]

    def _es_exportacion(self):
        if self.sii_document_class_id.sii_code in [ 110, 111, 112 ]:
            return True
        return False

    def _aduana(self):
        Aduana = collections.OrderedDict()
        #if not in 3,4,5
        Aduana['CodModVenta'] = self.payment_terms_id.forma_pago_aduanas.code
        Aduana['CodClauVenta'] = self.incoterms_id.code
        Aduana['TotClauVenta'] = self.payment_terms_id
        Aduana['CodViaTransp'] = self.via.code
        Aduana['NombreTransp'] = self.chofer_id.name
        Aduana['RUTCiaTransp'] = self.format_vat(self.carrier_id.partner_id.vat)
        Aduana['NomCiaTransp'] = self.carrier_id.name
        #Aduana['IdAdicTransp'] = self.indicador_adicional
        Aduana['CodPtoEmbarque'] = self.puerto_embarque.code
        Aduana['IdAdicPtoEmb'] = self.ind_puerto_embarque
        Aduana['CodPtoDesemb'] = self.puerto_desembarque.code
        Aduana['IdAdicPtoDesemb'] = self.ind_puerto_desembarque
        Aduana['Tara'] = self.tara
        Aduana['CodUnidMedTara'] = self.uom_tara.name
        Aduana['PesoBruto'] = self.peso_bruto
        Aduana['CodUnidPesoBruto'] = self.uom_peso_bruto.name
        Aduana['PesoNeto'] = self.peso_neto
        Aduana['CodUnidPesoNeto'] = self.uom_peso_neto.name
        Aduana['TotItems'] = self.total_items
        Aduana['TotBultos'] = self.total_bultos
        Aduana['TipoBultos'] = self.tipo_bulto.name
        Aduana['CodTpoBultos'] = self.tipo_bulto.code
        Aduana['CantBultos'] = self.cantidad_bultos
        #Aduana['Marcas'] =
        #Solo si es contenedor
        #Aduana['IdContainer'] =
        #Aduana['Sello'] =
        #Aduana['EmisorSello'] =
        Aduana['MntFlete'] = self.monto_flete
        Aduana['MntSeguro'] = self.monto_seguro
        Aduana['CodPaisRecep'] = self.pais_recepcion.name
        Aduana['CodPaisDestin'] = self.pais_destino.code
        return Aduana

    def _transporte(self):
        Transporte = collections.OrderedDict()
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

    def _otra_moneda(self):
        OtraMoneda = collections.OrderedDict()
        OtraMoneda['TpoMoneda'] = self.currency_id
        OtraMoneda['TpoCambio'] = self.currency_id.cambio
        OtraMoneda['MntNetoOtrMnda'] = self.currency_id
        OtraMoneda['MntExeOtrMnda'] = self.currency_id
        #OtraMoneda['MntFaeCarneOtrMnda'] =
        #OtraMoneda['MntMargComOtrMnda'] =
        OtraMoneda['IVAOtrMnda'] = self.currency_id
        #OtraMoneda[''] = otros impuestos otra moneda
        OtraMoneda['MntTotOtrMnda'] = self.currency_id
        return OtraMoneda

    def _encabezado(self, MntExe=0, no_product=False, taxInclude=False):
        res = super(Exportacion, self)._encabezado(MntExe, no_product, taxInclude)
        if not self._es_exportacion():
            return res
        result = collections.OrderedDict()
        for key, value in res.iteritems():
            result[key] = value
            if key == 'Receptor':
                result['Transporte'] = self._transporte()
            if key == 'Totales':
                result['OtraMoneda'] = self._otra_moneda()
        return result

    def _totales(self, MntExe=0, no_product=False, taxInclude=False):
        res = super(Exportacion, self)._totales(MntExe, no_product, taxInclude)
        if not self._es_exportacion():
            return res
        result = collections.OrderedDict()
        result['TpoMoneda'] = self.compnay_id.currency_id.sii_code
        for key, value in res.iteritems():
            #if forma pago 21 mnttotal = 0
            result[key] = value
        return result

    def _tpo_dte(self):
        if self._es_exportacion():
            return 'Exportaciones'
        return super(Exportacion, self)._tpo_dte()
