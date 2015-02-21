# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp.osv import fields

from openerp.tools.translate import _


class purchase_order(osv.Model):

    _inherit = 'purchase.order'
    _columns = {
        'partner_facility_id': fields.many2one('res.partner',
                                               "Supplier's Facility"),
    }

    def onchange_partner_id(self, cr, uid, ids, partner_id,
                            partner_facility_id):
        res = super(purchase_order, self).onchange_partner_id(cr, uid, ids,
                                                              partner_id)

        res.setdefault ('domain', {})

        if partner_id:
            res['domain']['partner_facility_id'] = [
                ('parent_id', '!=', False),
                ('parent_id', '=', partner_id),
            ]
        else:
            res['domain']['partner_facility_id'] = [
                ('parent_id', '!=', False),
            ]

        if not partner_id or not partner_facility_id:
            return res

        partner_facility = self.pool.get('res.partner').browse(
            cr, uid, partner_facility_id)
        if partner_facility.parent_id.id != partner_id:
            res['value']['partner_facility_id'] = None

        return res

    def onchange_partner_facility_id(self, cr, uid, ids, partner_facility_id,
                                     context=None):
        value = {}

        if partner_facility_id:
            partner_facility = self.pool.get('res.partner').browse(
                cr, uid, partner_facility_id)
            value['partner_id'] = partner_facility.parent_id.id

        return {'value': value}
