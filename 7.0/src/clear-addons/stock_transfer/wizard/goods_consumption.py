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

from openerp.osv import fields, orm
from openerp.tools.translate import _

class stock_consumption(orm.TransientModel):
    
    _name = 'stock.consumption'
    _description = 'Stock Consumption Wizard'
    
    def _get_dst_selection(self, cr, uid, context=None):
        
        loc_obj = self.pool.get('stock.location')
        parent_location_id = self._get_consumption_location(cr, uid, context=context)
        loc_ids = loc_obj.search(cr, uid, [('location_id', '=', parent_location_id)],
                                 context=context)
        datas = loc_obj.read(cr, uid, loc_ids, ['name'], context=context)
        res = []
        for data in datas:
            res.append((data['id'], data.get('name', '')))
        
        return res
    
    _columns = {
        'src_warehouse_id': fields.many2one('stock.warehouse', 'Source Warehouse', required=True,),
        'dst_selection': fields.selection(_get_dst_selection, string='Destination', required=True),
        'reference': fields.char('Patient/Reference', size=256, required=True),
    }
    
    def _get_consumption_location(self, cr, uid, context=None):
        
        res = False
        res_model, res_id = self.pool.get('ir.model.data').get_object_reference(cr, uid,
                                                                                'stock_transfer',
                                                                                'stock_location_dept_root')
        data = self.pool.get('stock.location').read(cr, uid, res_id, ['name'], context=context)
        if data.get('id', False):
            res = data['id']
        
        return res
    
    def has_location_access(self, cr, uid, warehouse_id, context=None):
        
        res = False
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        warehouse = self.pool.get('stock.warehouse').browse(cr, uid, warehouse_id, context=context)
        location_ids = [warehouse.lot_stock_id.id, warehouse.lot_input_id.id, warehouse.lot_output_id.id]
        for location in user.stock_location_ids:
            if location.id in location_ids:
                res = True
                break
        return res
    
    def onchange_src_warehouse(self, cr, uid, ids, warehouse_id, context=None):
        
        res = {'value': {'src_warehouse_id': False}}
        if self.has_location_access(cr, uid, warehouse_id, context=context):
            res['value']['src_warehouse_id'] = warehouse_id
        return res
    
    def get_src_location_id(self, cr, uid, warehouse_id, context=None):
        
        res = False
        if not warehouse_id:
            return res
        
        wh = self.pool.get('stock.warehouse').browse(cr, uid, warehouse_id, context=context)
        res = wh.lot_stock_id.id
        
        return res
    
    def create_consumption(self, cr, uid, ids, context=None):
        
        data = self.read(cr, uid, ids[0], [], context=context)
        
        # Create stock consumption (stock.issue) record
        #
        src_location_id = self.get_src_location_id(cr, uid, data['src_warehouse_id'][0], context)
        dst_location_id = int(data['dst_selection'])
        dst_datas = self.pool.get('stock.location').read(cr, uid, [dst_location_id], ['name'], context=context)
        dst_name = _('Consumption')
        for dst_data in dst_datas:
            dst_name = dst_name +' '+ dst_data['name']
        vals = {
            'src_warehouse_id': data['src_warehouse_id'][0],
            'src_location_id': src_location_id,
            'dst_location_id': dst_location_id,
            'name': dst_name,
            'issue_type': 'cons',
            'reference': data['reference'],
        }
        issue_obj = self.pool.get('stock.issue')
        issue_id = issue_obj.create(cr, uid, vals, context=context)
        
        # Open the record
        res_model_form, res_form_id = self.pool.get('ir.model.data').get_object_reference(cr, uid,
                                                                                'stock_transfer',
                                                                                'view_final_issue_form')
        res_model_tree, res_tree_id = self.pool.get('ir.model.data').get_object_reference(cr, uid,
                                                                                'stock_transfer',
                                                                                'view_final_issue_tree')
        return {
            'view_type': 'form',
            'view_mode': 'form, tree',
            'res_model': 'stock.issue',
            #'domain': "[('id', 'in', %s)]" % [issue_id],
            'res_id': issue_id,
            'type': 'ir.actions.act_window',
            'view_id': False,
            'views': [(res_form_id, 'form'), (res_tree_id, 'tree')],
            'nodestroy': True,
            'target': 'inline',
            'context': context
        }
