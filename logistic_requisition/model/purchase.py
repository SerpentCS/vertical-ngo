# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier, Jacques-Etienne Baudoux
#    Copyright 2013 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import orm, fields
from openerp import netsvc


class purchase_order(orm.Model):
    _inherit = 'purchase.order'

    def action_picking_create(self, cr, uid, ids, context=None):
        """ When the picking is created, we'll:

        Only for the sales order lines mto + drop shipping:
        Link the moves with the procurement of the sale order lines
        which generated the purchase and confirm the procurement.
        """
        assert len(ids) == 1, "Expected only 1 ID, got %r" % ids
        picking_id = super(purchase_order, self).action_picking_create(
            cr, uid, ids, context=context)
        if not picking_id:
            return picking_id
        wf_service = netsvc.LocalService("workflow")
        picking_obj = self.pool.get('stock.picking')
        picking = picking_obj.browse(cr, uid, picking_id, context=context)
        for move in picking.move_lines:
            purchase_line = move.purchase_line_id
            if not purchase_line:
                continue
            sale_line = purchase_line.sale_order_line_id
            if not sale_line:
                continue
            if not (sale_line.type == 'make_to_order'
                    and sale_line.sale_flow == 'direct_delivery'):
                continue
            procurement = sale_line.procurement_id
            if not procurement.move_id:
                # the procurement for the sales and purchase is the same!
                # So when the move will be done, the sales order and the
                # purchase order will be shipped at the same time
                procurement.write({'move_id': move.id})
                wf_service.trg_validate(uid, 'procurement.order',
                                        procurement.id, 'button_confirm', cr)
                if purchase_line is not None:
                    wf_service.trg_validate(uid, 'procurement.order',
                                            procurement.id, 'button_check', cr)

        return picking_id


class purchase_order_line(orm.Model):
    _inherit = 'purchase.order.line'

    _columns = {
        'lr_source_line_id': fields.many2one(  # one2one relation with selected_bid_line_id
            'logistic.requisition.source',
            'Logistic Requisition Source',
            readonly=True,
            ondelete='restrict'),
        'from_bid_line_id': fields.many2one(
            'purchase.order.line',
            'Generated from bid',
            readonly=True),
        'po_line_from_bid_ids': fields.one2many(
            'purchase.order.line',
            'from_bid_line_id',
            'Lines generated by the bid',
            readonly=True),
    }