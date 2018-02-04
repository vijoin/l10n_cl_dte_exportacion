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
        if self._es_exportacion() and self.commercial_partner_id.vat == value:
            value = "CL555555555"
        return super(Exportacion, self).format_vat(value, con_cero)

    @api.multi
    def crear_exportacion(self):
        self.exportacion = [(5,), (0,0,{
                    'pais_destino': self.commercial_partner_id.country_id.id,

                })]

    def _es_nc_exportacion(self):
        return self.sii_document_class_id.sii_code in [ 112 ]

    def _es_exportacion(self):
        if self.sii_document_class_id.sii_code in [ 110, 111, 112 ]:
            return True
        return False

    def _totales_normal(self, currency_id, MntExe, MntNeto, IVA, TasaIVA, ImptoReten, MntTotal=0):
        if not self._es_exportacion():
            return super(Exportacion, self)._totales_normal(currency_id, MntExe, MntNeto, IVA, TasaIVA, ImptoReten, MntTotal)
        if IVA:
            raise UserError("No debe haber Productos con IVA")
        Totales = collections.OrderedDict()
        if currency_id:
            Totales['TpoMoneda'] = currency_id.abreviatura
        Totales['MntExe'] = MntExe
        Totales['MntTotal'] = MntTotal
        #Totales['MontoNF']
        #Totales['TotalPeriodo']
        #Totales['SaldoAnterior']
        #Totales['VlrPagar']
        return Totales

    def _totales_otra_moneda(self, currency_id, MntExe, MntNeto, IVA, TasaIVA, ImptoReten, MntTotal=0):
        if not self._es_exportacion():
            return super(Exportacion, self)._totales_otra_moneda(currency_id, MntExe, MntNeto, IVA, TasaIVA, ImptoReten, MntTotal)
        Totales = collections.OrderedDict()
        Totales['TpoMoneda'] = self._acortar_str(self.company_id.currency_id.abreviatura, 15)
        Totales['TpoCambio'] = currency_id.rate
        if MntExe:
            if currency_id:
                MntExe = currency_id.compute(MntExe, self.company_id.currency_id)
            Totales['MntExeOtrMnda'] = MntExe
        if currency_id:
            MntTotal = currency_id.compute(MntTotal, self.company_id.currency_id)
        Totales['MntTotOtrMnda'] = MntTotal
        return Totales

    def _aplicar_gdr(self, MntExe):
        gdr = self.porcentaje_dr()
        MntExe *= gdr
        return self.currency_id.round( MntExe )

    def _totales(self, MntExe=0, no_product=False, taxInclude=False):
        MntExe, MntNeto, MntIVA, TasaIVA, ImptoReten, MntTotal = super(Exportacion, self)._totales(MntExe, no_product, taxInclude)
        if self._es_exportacion():
            MntExe = self._aplicar_gdr(MntExe)
        return MntExe, MntNeto, MntIVA, TasaIVA, ImptoReten, MntTotal

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
        if self.payment_term_id:
            Aduana['CodModVenta'] = self.payment_term_id.forma_pago_aduanas.code
            mnt_clau = self.payment_term_id.with_context(currency_id=self.currency_id.id).compute(self.amount_total, date_ref=self.date_invoice)[0]
            Aduana['TotClauVenta'] = round(mnt_clau[0][1], 2)
        elif not self._es_nc_exportacion():
            raise UserError("Debe Ingresar un Término de Pago")
        if self.incoterms_id:
            Aduana['CodClauVenta'] = self.incoterms_id.aduanas_code
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
        if expo.monto_flete:
            Aduana['MntFlete'] = expo.monto_flete
        if expo.monto_seguro:
            Aduana['MntSeguro'] = expo.monto_seguro
        if expo.pais_recepcion:
            Aduana['CodPaisRecep'] = expo.pais_recepcion.code
        if expo.pais_destino:
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
