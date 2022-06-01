#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2013 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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

from openerp.osv import fields, osv

class restday(osv.TransientModel):
    
    _name = 'hr.restday.wizard'
    _description = 'Rest Day Change Wizard'
    
    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True),
        'contract_id': fields.related('employee_id', 'contract_id', type='many2one',
                                      relation='hr.contract', string='Contract', readonly=True),
        'st_current_id': fields.many2one('hr.schedule.template','Current Template', readonly=True),
        'st_new_id': fields.many2one('hr.schedule.template','New Template', required=True),
    }
    
    def onchange_employee(self, cr, uid, ids, ee_id, context=None):
        
        res = {'value': {'st_current_id': False}}
        ee = self.pool.get('hr.employee').browse(cr, uid, ee_id, context=None)
        res['value']['st_current_id'] = ee.contract_id.schedule_template_id.id
        
        return res
    
    def change_restday(self, cr, uid, ids, context=None):
        
        data = self.read(cr, uid, ids[0], [], context=context)
        self.pool.get('hr.contract').write(cr, uid, data['contract_id'][0],
                                           {'schedule_template_id': data['st_new_id'][0]},
                                           context=context)
        return {
            'name': 'Change Rest Day',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.restday.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }
