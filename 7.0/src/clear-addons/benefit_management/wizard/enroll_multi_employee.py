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

from datetime import datetime, timedelta

from openerp import netsvc
from openerp.addons.decimal_precision import decimal_precision as dp
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools.translate import _

class enroll_employee(osv.TransientModel):
    
    _name = 'hr.benefit.enroll.multi.employee'
    _description = 'Employee Benefit Enrollment Form'
    
    _columns = {
        'benefit_id': fields.many2one('hr.benefit', 'Benefit', required=True),
        'employee_ids': fields.many2many('hr.employee', 'hr_employee_benefit_rel',
                                         'employee_id', 'benefit_id', string='Employee'),
        'start_date': fields.date('Enrollment Date', required=True),
        'end_date': fields.date('Termination Date'),
        'advantage_override': fields.boolean('Override Advantage'),
        'premium_override': fields.boolean('Override Premium'),
        'advantage_amount': fields.float('Advantage Amount', digits_compute=dp.get_precision('Account')),
        'premium_amount': fields.float('Premium Amount', digits_compute=dp.get_precision('Account')),
        'premium_total': fields.float('Premium Total', digits_compute=dp.get_precision('Account')),
        'premium_installments': fields.integer("No. of Installments"),
    }
    
    def _get_benefit(self, cr, uid, context=None):
        
        if context == None:
            context = {}
        return context.get('active_id', False)
    
    _defaults = {
        'benefit_id': _get_benefit,
        'start_date': datetime.today().strftime(OE_DFORMAT),
    }
    
    def onchange_premium_total(self, cr, uid, ids, start_date, premium_amount, premium_total, context=None):
        
        return self.pool.get('hr.benefit.policy').onchange_premium_total(cr, uid, [], start_date,
                                                                         premium_amount, premium_total,
                                                                         context=context)
    
    def do_multi_enroll(self, cr, uid, ids, context=None):
        
        policy_obj = self.pool.get('hr.benefit.policy')
        data = self.read(cr, uid, ids[0], [], context=context)
        benefit_id = data.get('benefit_id', False) and data['benefit_id'][0] or False
        employee_ids = data.get('employee_ids', False)
        start = data.get('start_date', False)
        end = data.get('end_date', False)
        
        if not benefit_id or not employee_ids:
            return {'type': 'ir.actions.act_window_close'}

        wkf = netsvc.LocalService('workflow')
        for employee_id in employee_ids:
            
            vals = {
                'benefit_id': benefit_id,
                'employee_id': employee_id,
                'start_date': start,
                'end_date': end,
                'advantage_override': data.get('advantage_override', False),
                'premium_override': data.get('premium_override', False),
                'advantage_amount': data.get('advantage_amount', False),
                'premium_amount': data.get('premium_amount', False),
                'premium_total': data.get('premium_total', False),
            }
            pol_id = policy_obj.create(cr, uid, vals, context=context)
            wkf.trg_validate(uid, 'hr.benefit.policy', pol_id, 'signal_open', cr)
        
        return {'type': 'ir.actions.act_window_close'}
