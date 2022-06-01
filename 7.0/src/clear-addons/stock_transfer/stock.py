#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Michael Telahun Makonnen <mmakonnen@gmail.com>.
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

import pytz
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from lxml import etree

from openerp import netsvc, SUPERUSER_ID
from openerp.addons.decimal_precision import decimal_precision as dp
from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools import float_compare
from openerp.tools.translate import _

class goods_issue(orm.Model):
    
    _name = 'stock.issue'
    _description = 'Stock Issue'
    
    _columns = {
        'name': fields.char('Document No.', size=256, readonly=True),
        'user_id': fields.many2one('res.users', 'Issued By', readonly=True),
        'date': fields.date('Date', required=True),
        'issue_type': fields.selection([('cons', 'Consumption'), ('trans', 'Transfer')],
                                       'Type', required=True),
        'picking_policy': fields.selection([('direct', 'Deliver each product when available'), ('one', 'Deliver all products at once')],
            'Issuing Policy', required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
            help="""Pick 'Deliver each product when available' if you allow partial delivery."""),
        'src_warehouse_id': fields.many2one('stock.warehouse', 'Source Warehouse',
                                            required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'src_location_id': fields.many2one('stock.location', 'Source Location', required=True, domain=[('usage','<>','view')], states={'confirmed':[('readonly',True)], 'approved':[('readonly',True)],'done':[('readonly',True)]} ),
        'dst_warehouse_id': fields.many2one('stock.warehouse', 'Destination Warehouse',
                                            required=False, readonly=True, states={'draft': [('readonly', False)]}),
        'dst_location_id': fields.many2one('stock.location', 'Destination Location', required=True, domain=[('usage','<>','view')], states={'confirmed':[('readonly',True)], 'approved':[('readonly',True)],'done':[('readonly',True)]} ),
        'transit_location_id': fields.many2one('stock.location', 'Transit Location', required=True, readonly=True, domain=[('usage','<>','view')], states={'draft':[('readonly',False)]}),
        'out_picking_ids': fields.one2many('stock.picking', 'out_issue_id', 'Delivery Picking List', readonly=True, help="This is the list of outgoing shipments that have been generated for this issue order."),
        'in_picking_ids': fields.one2many('stock.picking', 'in_issue_id', 'Reception Picking List', readonly=True, help="This is the list of incoming shipments that have been generated for this issue order."),
        'shipped': fields.boolean('Delivered', readonly=True, help="It indicates that the Goods Issue has been delivered."),
        'line_ids': fields.one2many('stock.issue.line', 'issue_id', 'Issue Lines'),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'reference': fields.char('Reference', size=256),
        'notes': fields.text('Notes'),
        'state': fields.selection([('cancel', 'Cancelled'),
                                   ('draft', 'Draft'),
                                   ('progress', 'In Progress'),
                                   ('shipping_except', 'Shipping Exception'),
                                   ('done', 'Done'),
                                  ], 'State', readonly=True),
    }

    def _get_default_company(self, cr, uid, context=None):
        return self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
    
    def _get_transit_location(self, cr, uid, context=None):
        
        res_model, res_id = self.pool.get('ir.model.data').get_object_reference(cr, uid,
                                                                                'stock_transfer',
                                                                                'stock_location_transit')
        
        return res_id
    
    _defaults = {
        'state': 'draft',
        'user_id': lambda obj, cr, uid, context: uid,
        'company_id': _get_default_company,
        'picking_policy': 'direct',
        'date': datetime.now().strftime(OE_DFORMAT),
        'transit_location_id': _get_transit_location,
        'issue_type': 'trans',
    }
    
    def onchange_src_warehouse(self, cr, uid, ids, warehouse_id, context=None):
        
        res = {'value': {'src_location_id': False}}
        if not warehouse_id:
            return res
        
        wh = self.pool.get('stock.warehouse').browse(cr, uid, warehouse_id, context=context)
        res['value']['src_location_id'] = wh.lot_stock_id.id
        
        return res
    
    def onchange_dst_warehouse(self, cr, uid, ids, warehouse_id, context=None):
        
        res = {'value': {'dst_location_id': False}}
        if not warehouse_id:
            return res
        
        wh = self.pool.get('stock.warehouse').browse(cr, uid, warehouse_id, context=context)
        res['value']['dst_location_id'] = wh.lot_input_id.id
        
        return res
    
    def create(self, cr, uid, vals, context=None):
        
        rid = super(goods_issue, self).create(cr, uid, vals, context)
        if rid:
            ref = self.pool.get('ir.sequence').next_by_code(cr, uid, 'stock_issue.ref', context=context)
            self.write(cr, uid, rid, {'name': ref}, context=context)
        return rid

    def unlink(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (long, int)):
            ids = [ids]
        
        for issue in self.browse(cr, uid, ids, context=context):
            raise orm.except_orm(_('Operation Denied'),
                                 _("Once saved, an order cannot be deleted.\nDocument No. %s" %(issue.name)))
        
        return

    def _get_partner(self, src_warehouse, dst_warehouse, out=False):
        
        partner_id = False
        if out:
            if dst_warehouse and dst_warehouse.partner_id.id:
                partner_id = dst_warehouse.partner_id.id
        else:
            if src_warehouse and src_warehouse.partner_id:
                partner_id = src_warehouse.partner_id.id
        
        return partner_id

    #
    # These functions copied from sale_stock module
    #
    
    def _prepare_order_line_move(self, cr, uid, issue, line, picking_id, date_planned, out=False, context=None):
        
        if out == True:
            location_id = issue.src_warehouse_id.lot_stock_id.id
            output_id = (issue.issue_type == 'cons') and issue.dst_location_id.id or issue.transit_location_id.id
            partner_id = self._get_partner(issue.src_warehouse_id, issue.dst_warehouse_id, out=out)
        else:
            location_id = issue.transit_location_id.id
            output_id = issue.dst_warehouse_id.lot_stock_id.id
            partner_id = self._get_partner(issue.src_warehouse_id, issue.dst_warehouse_id, out=out)

        return {
            'name': line.name,
            'picking_id': picking_id,
            'product_id': line.product_id.id,
            'date': date_planned,
            'date_expected': date_planned,
            'product_qty': line.product_uom_qty,
            'product_uom': line.product_uom.id,
            'product_uos_qty': line.product_uom_qty,
            'product_uos': line.product_uom.id,
            'product_packaging': False,
            'partner_id': partner_id,
            'location_id': location_id,
            'location_dest_id': output_id,
            'out_issue_line_id': (out == True) and line.id or False,
            'in_issue_line_id': (out == False) and line.id or False,
            'tracking_id': False,
            'state': 'draft',
            'company_id': issue.company_id.id,
            'price_unit': line.product_id.standard_price or 0.0
        }

    def _prepare_order_picking(self, cr, uid, issue, out=False, context=None):
        
        if issue.issue_type == 'cons':
            pick_name = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.out')
        else:
            pick_name = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.internal')
        
        pick_type = 'internal'
        if out and issue.issue_type == 'cons':
            pick_type = 'out'
        else: # internal transfer
            if out:
                pick_type = 'int_out'
            else:
                pick_type= 'int_in'
        
        partner_id = self._get_partner(issue.src_warehouse_id, issue.dst_warehouse_id, out=out)
        
        return {
            'name': pick_name,
            'origin': issue.name,
            'date': self.date_to_datetime(cr, uid, issue.date, context),
            'type': pick_type,
            'state': 'auto',
            'move_type': issue.picking_policy,
            'out_issue_id': (out == True) and issue.id or False,
            'in_issue_id': (out == False) and issue.id or False,
            'location_dest_id': (out == True) and issue.src_warehouse_id.lot_output_id.id or issue.dst_location_id.id,
            'location_id': (out == True) and issue.src_location_id.id or issue.src_warehouse_id.lot_output_id.id,
            'partner_id': partner_id,
            'note': issue.notes,
            'invoice_state': 'none',
            'company_id': issue.company_id.id,
        }

    def date_to_datetime(self, cr, uid, userdate, context=None):
        """ Convert date values expressed in user's timezone to
        server-side UTC timestamp, assuming a default arbitrary
        time of 12:00 AM - because a time is needed.
    
        :param str userdate: date string in in user time zone
        :return: UTC datetime string for server-side use
        """
        # TODO: move to fields.datetime in server after 7.0
        user_date = datetime.strptime(userdate, OE_DFORMAT)
        if context and context.get('tz'):
            tz_name = context['tz']
        else:
            tz_name = self.pool.get('res.users').read(cr, SUPERUSER_ID, uid, ['tz'])['tz']
        if tz_name:
            utc = pytz.timezone('UTC')
            context_tz = pytz.timezone(tz_name)
            user_datetime = user_date + relativedelta(hours=12.0)
            local_timestamp = context_tz.localize(user_datetime, is_dst=False)
            user_datetime = local_timestamp.astimezone(utc)
            return user_datetime.strftime(OE_DTFORMAT)
        return user_date.strftime(OE_DTFORMAT)

    def _get_date_planned(self, cr, uid, issue, line, start_date, context=None):
        start_date = self.date_to_datetime(cr, uid, start_date, context)
        date_planned = datetime.strptime(start_date, OE_DTFORMAT)
        return date_planned

    def _create_pickings_and_procurements(self, cr, uid, issue, issue_lines, out_picking_id=False, in_picking_id=False, context=None):
        """Create the required procurements to supply sales order lines, also connecting
        the procurements to appropriate stock moves in order to bring the goods to the
        sales order's requested location.

        If ``picking_id`` is provided, the stock moves will be added to it, otherwise
        a standard outgoing picking will be created to wrap the stock moves, as returned
        by :meth:`~._prepare_order_picking`.

        Modules that wish to customize the procurements or partition the stock moves over
        multiple stock pickings may override this method and call ``super()`` with
        different subsets of ``order_lines`` and/or preset ``picking_id`` values.

        :param browse_record order: sales order to which the order lines belong
        :param list(browse_record) order_lines: sales order line records to procure
        :param int picking_id: optional ID of a stock picking to which the created stock moves
                               will be added. A new picking will be created if ommitted.
        :return: True
        """
        move_obj = self.pool.get('stock.move')
        picking_obj = self.pool.get('stock.picking')

        for line in issue_lines:
            if line.state == 'done':
                continue

            date_planned = self._get_date_planned(cr, uid, issue, line, issue.date, context=context)

            if line.product_id:
                if line.product_id.type in ('product', 'consu'):
                    # Create outgoing picking and stock move
                    #
                    if not out_picking_id:
                        out_picking_id = picking_obj.create(cr, uid, self._prepare_order_picking(cr, uid, issue, out=True, context=context))
                    move_obj.create(cr, uid, self._prepare_order_line_move(cr, uid, issue, line, out_picking_id, date_planned, out=True, context=context))
                    
                    # Create incoming picking and stock move if this is not a consumption
                    #
                    if issue.issue_type == 'trans':
                        if not in_picking_id:
                            in_picking_id = picking_obj.create(cr, uid, self._prepare_order_picking(cr, uid, issue, out=False, context=context))
                        move_obj.create(cr, uid, self._prepare_order_line_move(cr, uid, issue, line, in_picking_id, date_planned, out=False, context=context))

        wf_service = netsvc.LocalService("workflow")
        if out_picking_id:
            wf_service.trg_validate(uid, 'stock.picking', out_picking_id, 'button_confirm', cr)
        if in_picking_id:
            wf_service.trg_validate(uid, 'stock.picking', in_picking_id, 'button_confirm', cr)

        # Check availability of stock
        picking_obj.action_assign(cr, uid, [out_picking_id], context)
        
        val = {}
        if issue.state == 'shipping_except':
            val['state'] = 'progress'
            val['shipped'] = False

        issue.write(val)
        return True

    def action_issue_create(self, cr, uid, ids, context=None):
        for issue in self.browse(cr, uid, ids, context=context):
            self._create_pickings_and_procurements(cr, uid, issue, issue.line_ids, context=context)
        
            # If stock consumption perform additional actions
            #
            pick_obj = self.pool.get('stock.picking')
            partial_pick_obj = self.pool.get('stock.partial.picking')
            partial_data = {
                'delivery_date' : issue.date
            }
            if issue.issue_type == 'cons' and len(issue.out_picking_ids) > 0:
                for picking in issue.out_picking_ids:
                    
                    # Add reference to picking
                    if not picking.giv_reference:
                        pick_obj.write(cr, uid, [picking.id], 
                                       {'giv_reference': issue.reference}, context=context)
                    
                    # Go ahead and do the picking as well
                    #
                    moves = [partial_pick_obj._partial_move_for(cr, uid, m) for m in picking.move_lines if m.state not in ('done','cancel')]
                    for mov in moves:
                        partial_data['move%s' % (mov['move_id'])] = {
                            'product_id': mov['product_id'],
                            'product_qty': mov['quantity'],
                            'product_uom': mov['product_uom'],
                            'prodlot_id': mov['prodlot_id'],
                        }
                    pick_obj.do_partial(cr, uid, [picking.id], partial_data, context=context)

        return True

    def test_shipping_exception(self, cr, uid, ids, context=None):
        
        return False
    
    def allow_cancel(self, cr, uid, ids, context=None):
        
        for issue in self.browse(cr, uid, ids, context=context):
            if issue.state in ['done', 'cancel']:
                return False
        return True
        
    def test_done(self, cr, uid, ids, context=None):
        
        for issue in self.browse(cr, uid, ids, context=context):
            for pick in issue.out_picking_ids:
                if pick.state not in ('done', 'cancel'):
                    return False
            for pick in issue.in_picking_ids:
                if pick.state not in ('done', 'cancel'):
                    return False
        
        return True
    
    def state_cancel(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        if context is None:
            context = {}
        for issue in self.browse(cr, uid, ids, context=context):
            for pick in issue.out_picking_ids:
                if pick.state not in ('draft', 'cancel'):
                    raise orm.except_orm(
                        _('Cannot cancel stock issue order!'),
                        _('You must first cancel all delivery order(s) attached to this stock issue order.'))
            for pick in issue.in_picking_ids:
                if pick.state not in ('draft', 'cancel'):
                    raise orm.except_orm(
                        _('Cannot cancel stock issue order!'),
                        _('You must first cancel all receiving order(s) attached to this stock issue order.'))
            for r in self.read(cr, uid, ids, ['out_picking_ids', 'in_picking_ids']):
                for pick in (r['out_picking_ids'] + r['in_picking_ids']):
                    wf_service.trg_validate(uid, 'stock.picking', pick, 'signal_cancel', cr)
        return self._state_common(cr, uid, ids, 'cancel', 'cancel', context=context)
    
    def _state_common(self, cr, uid, ids, state, line_state, context=None):
        
        line_ids = []
        for order in self.browse(cr, uid, ids, context=context):
            line_ids += [line.id for line in order.line_ids if line.state != 'cancel']
        
        if len(line_ids) > 0:
            self.pool.get('stock.issue.line').write(cr, uid, line_ids, {'state': line_state}, context=context)
        self.write(cr, uid, ids, {'state': state}, context=context)
        
        return True
    
    def state_in_progress(self, cr, uid, ids, context=None):
        
        if self.action_issue_create(cr, uid, ids, context=context) == True:
            return self._state_common(cr, uid, ids, 'progress', 'confirmed', context=context)
        return self.state_shipping_exception(cr, uid, ids, context=context)
    
    def state_shipping_exception(self, cr, uid, ids, context=None):
        
        return self._state_common(cr, uid, ids, 'except', 'exception', context=context)
    
    def state_done(self, cr, uid, ids, context=None):
        
        return self._state_common(cr, uid, ids, 'done', 'done', context=context)

class goods_issue_line(orm.Model):
    
    _name = 'stock.issue.line'
    _description = 'Stock Issue Line'
    
    _columns = {
        'name': fields.text('Description', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'issue_id': fields.many2one('stock.issue', 'Goods Issue'),
        'date_planned': fields.date('Scheduled Date', required=True, select=True),
        'product_uom_qty': fields.float('Quantity', digits_compute= dp.get_precision('Product Unit of Measure'), required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'product_uom': fields.many2one('product.uom', 'Unit of Measure ', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'product_id': fields.many2one('product.product', 'Product', change_default=True),
        'out_move_ids': fields.one2many('stock.move', 'out_issue_line_id', 'Inventory Moves', readonly=True, ondelete='set null'),
        'in_move_ids': fields.one2many('stock.move', 'in_issue_line_id', 'Inventory Moves', readonly=True, ondelete='set null'),
        'state': fields.selection([('cancel', 'Cancelled'),('draft', 'Draft'),('confirmed', 'Confirmed'),('exception', 'Exception'),('done', 'Done')], 'Status', required=True, readonly=True,
                help='* The \'Draft\' status is set when the related sales order in draft status. \
                    \n* The \'Confirmed\' status is set when the related sales order is confirmed. \
                    \n* The \'Exception\' status is set when the related sales order is set as exception. \
                    \n* The \'Done\' status is set when the sales order line has been picked. \
                    \n* The \'Cancelled\' status is set when a user cancel the sales order related.'),
    }
    
    _defaults = {
        'product_uom_qty': 1,
        'state': 'draft',
    }

    # Copied and modified from module sale_stock
    #
    def onchange_product(self, cr, uid, ids, product_id, qty=0, uom=False,
                         date_order=False, context=None):
        
        context = context or {}
        product_uom_obj = self.pool.get('product.uom')
        product_obj = self.pool.get('product.product')

        warning = {}
        result = {}
        warning_msgs = ''
        product = product_obj.browse(cr, uid, product_id, context=context)

        if not product_id:
            return {'value': {'product_uom_qty': qty},
                    'domain': {'product_uom': []}}
        result['name'] = product_obj.name_get(cr, uid, [product.id], context=context)[0][1]
        
        if not date_order:
            date_order = time.strftime(OE_DFORMAT)
        result['date_planned'] = date_order

        uom2 = False
        if uom:
            uom2 = product_uom_obj.browse(cr, uid, uom)
            if product.uom_id.category_id.id != uom2.category_id.id:
                uom = False

        domain = {}
        if not uom:
            result['product_uom'] = product.uom_id.id
            domain = {'product_uom':
                        [('category_id', '=', product.uom_id.category_id.id)]}

        #check if product is available, and if not: raise an error
        if not uom2:
            uom2 = product.uom_id

        compare_qty = float_compare(product.virtual_available * uom2.factor, qty * product.uom_id.factor, precision_rounding=product.uom_id.rounding)
        if (product.type=='product') and int(compare_qty) == -1 \
          and (product.procure_method=='make_to_stock'):
            warn_msg = _('You plan to issue %.2f %s but you only have %.2f %s available !\nThe real stock is %.2f %s. (without reservations)') % \
                    (qty, uom2 and uom2.name or product.uom_id.name,
                     max(0,product.virtual_available), product.uom_id.name,
                     max(0,product.qty_available), product.uom_id.name)
            warning_msgs += _("Not enough stock ! : ") + warn_msg + "\n\n"

        if warning_msgs:
            warning = {
                       'title': _('Configuration Error!'),
                       'message' : warning_msgs
                    }
        return {'value': result, 'domain': domain, 'warning': warning}

class stock_move(orm.Model):
    _inherit = 'stock.move'
    _columns = {
        'out_issue_line_id': fields.many2one('stock.issue.line', 'Stock Transfer Line (Delivery)',
                                             ondelete='set null', select=True, readonly=True),
        'in_issue_line_id': fields.many2one('stock.issue.line', 'Stock Transfer Line (Reception)',
                                            ondelete='set null', select=True, readonly=True),
    }

class stock_picking(orm.Model):
    _inherit = 'stock.picking'
    _columns = {
        'giv_reference': fields.char('Goods Issue Voucher', size=256),
        'out_issue_id': fields.many2one('stock.issue', 'Stock Transfer (Delivery)', ondelete='set null', select=True),
        'in_issue_id': fields.many2one('stock.issue', 'Stock Transfer (Reception)', ondelete='set null', select=True),
        'type': fields.selection([('out', 'Sending Goods'),
                                  ('in', 'Getting Goods'),
                                  ('internal', 'Internal'),
                                  ('int_in', 'Internal Reception'),
                                  ('int_out', 'Internal Delivery')],
                                 'Shipping Type', required=True, select=True, help="Shipping type specify, goods coming in or going out."),
    }

# Copied from addons/stock/stock.py
#
#----------------------------------------------------------
# "Empty" Classes that are used to vary from the original stock.picking  (that are dedicated to the internal pickings)
#   in order to offer a different usability with different views, labels, available reports/wizards...
#----------------------------------------------------------
class stock_picking_in(orm.Model):
    _name = "stock.picking.internal.in"
    _inherit = "stock.picking"
    _table = "stock_picking"
    _description = "Incoming Internal Stock Transfers"

    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        return self.pool.get('stock.picking').search(cr, user, args, offset, limit, order, context, count)

    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        return self.pool.get('stock.picking').read(cr, uid, ids, fields=fields, context=context, load=load)

    def check_access_rights(self, cr, uid, operation, raise_exception=True):
        #override in order to redirect the check of acces rights on the stock.picking object
        return self.pool.get('stock.picking').check_access_rights(cr, uid, operation, raise_exception=raise_exception)

    def check_access_rule(self, cr, uid, ids, operation, context=None):
        #override in order to redirect the check of acces rules on the stock.picking object
        return self.pool.get('stock.picking').check_access_rule(cr, uid, ids, operation, context=context)

    def _workflow_trigger(self, cr, uid, ids, trigger, context=None):
        #override in order to trigger the workflow of stock.picking at the end of create, write and unlink operation
        #instead of it's own workflow (which is not existing)
        return self.pool.get('stock.picking')._workflow_trigger(cr, uid, ids, trigger, context=context)

    def _workflow_signal(self, cr, uid, ids, signal, context=None):
        #override in order to fire the workflow signal on given stock.picking workflow instance
        #instead of it's own workflow (which is not existing)
        return self.pool.get('stock.picking')._workflow_signal(cr, uid, ids, signal, context=context)

    def message_post(self, *args, **kwargs):
        """Post the message on stock.picking to be able to see it in the form view when using the chatter"""
        return self.pool.get('stock.picking').message_post(*args, **kwargs)

    def message_subscribe(self, *args, **kwargs):
        """Send the subscribe action on stock.picking model as it uses _name in request"""
        return self.pool.get('stock.picking').message_subscribe(*args, **kwargs)

    def message_unsubscribe(self, *args, **kwargs):
        """Send the unsubscribe action on stock.picking model to match with subscribe"""
        return self.pool.get('stock.picking').message_unsubscribe(*args, **kwargs)

    def default_get(self, cr, uid, fields_list, context=None):
        # merge defaults from stock.picking with possible defaults defined on stock.picking.internal.in
        defaults = self.pool['stock.picking'].default_get(cr, uid, fields_list, context=context)
        in_defaults = super(stock_picking_in, self).default_get(cr, uid, fields_list, context=context)
        defaults.update(in_defaults)
        return defaults

    _columns = {
        'backorder_id': fields.many2one('stock.picking.internal.in', 'Back Order of', states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}, help="If this shipment was split, then this field links to the shipment which contains the already processed part.", select=True),
        'state': fields.selection(
            [('draft', 'Draft'),
            ('auto', 'Waiting Another Operation'),
            ('confirmed', 'Waiting Availability'),
            ('assigned', 'Ready to Receive'),
            ('done', 'Received'),
            ('cancel', 'Cancelled'),],
            'Status', readonly=True, select=True,
            help="""* Draft: not confirmed yet and will not be scheduled until confirmed\n
                 * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows)\n
                 * Waiting Availability: still waiting for the availability of products\n
                 * Ready to Receive: products reserved, simply waiting for confirmation.\n
                 * Received: has been processed, can't be modified or cancelled anymore\n
                 * Cancelled: has been cancelled, can't be confirmed anymore"""),
    }
    _defaults = {
        'type': 'int_in',
    }

class stock_picking_out(orm.Model):
    _name = "stock.picking.internal.out"
    _inherit = "stock.picking"
    _table = "stock_picking"
    _description = "Internal Stock Delivery"

    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        return self.pool.get('stock.picking').search(cr, user, args, offset, limit, order, context, count)

    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        return self.pool.get('stock.picking').read(cr, uid, ids, fields=fields, context=context, load=load)

    def check_access_rights(self, cr, uid, operation, raise_exception=True):
        #override in order to redirect the check of acces rights on the stock.picking object
        return self.pool.get('stock.picking').check_access_rights(cr, uid, operation, raise_exception=raise_exception)

    def check_access_rule(self, cr, uid, ids, operation, context=None):
        #override in order to redirect the check of acces rules on the stock.picking object
        return self.pool.get('stock.picking').check_access_rule(cr, uid, ids, operation, context=context)

    def _workflow_trigger(self, cr, uid, ids, trigger, context=None):
        #override in order to trigger the workflow of stock.picking at the end of create, write and unlink operation
        #instead of it's own workflow (which is not existing)
        return self.pool.get('stock.picking')._workflow_trigger(cr, uid, ids, trigger, context=context)

    def _workflow_signal(self, cr, uid, ids, signal, context=None):
        #override in order to fire the workflow signal on given stock.picking workflow instance
        #instead of it's own workflow (which is not existing)
        return self.pool.get('stock.picking')._workflow_signal(cr, uid, ids, signal, context=context)

    def message_post(self, *args, **kwargs):
        """Post the message on stock.picking to be able to see it in the form view when using the chatter"""
        return self.pool.get('stock.picking').message_post(*args, **kwargs)

    def message_subscribe(self, *args, **kwargs):
        """Send the subscribe action on stock.picking model as it uses _name in request"""
        return self.pool.get('stock.picking').message_subscribe(*args, **kwargs)

    def message_unsubscribe(self, *args, **kwargs):
        """Send the unsubscribe action on stock.picking model to match with subscribe"""
        return self.pool.get('stock.picking').message_unsubscribe(*args, **kwargs)

    def default_get(self, cr, uid, fields_list, context=None):
        # merge defaults from stock.picking with possible defaults defined on stock.picking.out
        defaults = self.pool['stock.picking'].default_get(cr, uid, fields_list, context=context)
        out_defaults = super(stock_picking_out, self).default_get(cr, uid, fields_list, context=context)
        defaults.update(out_defaults)
        return defaults

    _columns = {
        'backorder_id': fields.many2one('stock.picking.internal.out', 'Back Order of', states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}, help="If this shipment was split, then this field links to the shipment which contains the already processed part.", select=True),
        'state': fields.selection(
            [('draft', 'Draft'),
            ('auto', 'Waiting Another Operation'),
            ('confirmed', 'Waiting Availability'),
            ('assigned', 'Ready to Deliver'),
            ('done', 'Delivered'),
            ('cancel', 'Cancelled'),],
            'Status', readonly=True, select=True,
            help="""* Draft: not confirmed yet and will not be scheduled until confirmed\n
                 * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows)\n
                 * Waiting Availability: still waiting for the availability of products\n
                 * Ready to Deliver: products reserved, simply waiting for confirmation.\n
                 * Delivered: has been processed, can't be modified or cancelled anymore\n
                 * Cancelled: has been cancelled, can't be confirmed anymore"""),
    }
    _defaults = {
        'type': 'int_out',
    }

# Partial picking wizard
class stock_partial_picking(orm.TransientModel):
    _inherit = "stock.partial.picking"
    
    _columns = {
        'giv_reference': fields.char('Goods Issue Voucher', size=256),
    }

    def do_partial(self, cr, uid, ids, context=None):
        stock_picking = self.pool.get('stock.picking')
        stock_issue = self.pool.get('stock.issue')
        partial = self.browse(cr, uid, ids[0], context=context)
        
        # Write reference to picking
        stock_picking.write(cr, uid, [partial.picking_id.id],
                            {'giv_reference': partial.giv_reference}, context=context)
        
        # Write reference to stock issue
        if partial.picking_id.type in ('int_in', 'int_out'):
            issue = False
            if partial.picking_id.type == 'int_in':
                issue = partial.picking_id.in_issue_id
            elif partial.picking_id.type == 'int_out':
                issue = partial.picking_id.out_issue_id
            
            # Only write the reference if there isn't another reference number already
            if issue and not issue.reference:
                stock_issue.write(cr, uid, [issue.id],
                                  {'reference': partial.giv_reference}, context=context)
        
        return super(stock_partial_picking, self).do_partial(cr, uid, ids, context=context)

class stock_requisition(orm.Model):
    
    _name = 'stock.requisition'
    _description = 'Stock Requisition'
    
    _columns = {
        'name': fields.char('Document No.', size=256, readonly=True),
        'user_id': fields.many2one('res.users', 'Issued By', readonly=True),
        'date': fields.date('Date', required=True),
        'line_ids': fields.one2many('stock.requisition.line', 'req_id', 'Issue Lines'),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'notes': fields.text('Notes'),
        'state': fields.selection([('cancel', 'Cancelled'),
                                   ('draft', 'Draft'),
                                   ('approve', 'Approved'),
                                   ('done', 'Done'),
                                  ], 'State', readonly=True),
    }
    
    _defaults = {
        'state': 'draft',
    }
    
    def create(self, cr, uid, vals, context=None):
        
        rid = super(stock_requisition, self).create(cr, uid, vals, context)
        if rid:
            ref = self.pool.get('ir.sequence').next_by_code(cr, uid, 'stock_requisition.ref', context=context)
            self.write(cr, uid, rid, {'name': ref}, context=context)
        return rid

    def unlink(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (long, int)):
            ids = [ids]
        
        for req in self.browse(cr, uid, ids, context=context):
            raise orm.except_orm(_('Operation Denied'),
                                 _("Once saved, a requisition cannot be deleted.\nDocument No. %s" %(req.name)))
        
        return

class stock_requisition_line(orm.Model):
    
    _name = 'stock.requisition.line'
    _description = 'Stock Requisition Line'
    
    _columns = {
        'name': fields.text('Description', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'req_id': fields.many2one('stock.requisition', 'Stock Requisition'),
        'product_uom_qty': fields.float('Quantity', digits_compute= dp.get_precision('Product Unit of Measure'), required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'product_uom': fields.many2one('product.uom', 'Unit of Measure ', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'product_id': fields.many2one('product.product', 'Product', change_default=True),
    }
    
    _defaults = {
        'product_uom_qty': 1,
    }

    # Copied and modified from module sale_stock
    #
    def onchange_product(self, cr, uid, ids, product_id, qty=0, uom=False,
                         date_order=False, context=None):
        
        context = context or {}
        product_uom_obj = self.pool.get('product.uom')
        product_obj = self.pool.get('product.product')

        result = {}
        product = product_obj.browse(cr, uid, product_id, context=context)

        if not product_id:
            return {'value': {'product_uom_qty': qty},
                    'domain': {'product_uom': []}}
        result['name'] = product_obj.name_get(cr, uid, [product.id], context=context)[0][1]

        uom2 = False
        if uom:
            uom2 = product_uom_obj.browse(cr, uid, uom)
            if product.uom_id.category_id.id != uom2.category_id.id:
                uom = False

        domain = {}
        if not uom:
            result['product_uom'] = product.uom_id.id
            domain = {'product_uom':
                        [('category_id', '=', product.uom_id.category_id.id)]}

        return {'value': result, 'domain': domain}

class res_users(orm.Model):
    
    _inherit = 'res.users'

    _columns = {
        'stock_location_ids': fields.many2many('stock.location', 'res_users_stock_location_rel',
                                               'user_id', 'location_id', string="Stock Locations"),
    }
