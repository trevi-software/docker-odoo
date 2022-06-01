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

from openerp.osv import fields, osv
from openerp.tools.translate import _

class hr_payslip(osv.Model):
    
    _name = 'hr.payslip'
    _inherit = 'hr.payslip'
    
    def get_worked_day_lines(self, cr, uid, contract_ids, date_from, date_to, context=None):
        
        res = super(hr_payslip, self).get_worked_day_lines(cr, uid, contract_ids, date_from, date_to,
                                                           context=context)
        if len(res) == 0:
            return res
        
        c_obj = self.pool.get('hr.contract')
        bns_obj = self.pool.get('hr.bonus')
        
        for contract in c_obj.browse(cr, uid, contract_ids, context=context):

            bns_pct = {
                 'name': _("Employee Performance Bonus"),
                 'sequence': 100,
                 'code': 'BNS_PCT',
                 'number_of_days': 0.0,     # Bonus Amount
                 'number_of_hours': 0.0,    # Bonus Amount
                 'rate': 1.0,               # Always 1
                 'contract_id': contract.id,
            }

            bns_fix = {
                 'name': _("Employee Performance Bonus"),
                 'sequence': 100,
                 'code': 'BNS_FIX',
                 'number_of_days': 0.0,     # Bonus Amount
                 'number_of_hours': 0.0,    # Bonus Amount
                 'rate': 1.0,               # Always 1
                 'contract_id': contract.id,
            }
            
            bns_ids = bns_obj.search(cr, uid, [('date_end', '>=', date_from),
                                               ('date_end', '<=', date_to),
                                               ('state', '=', 'approve')], context=context)
            for sheet in bns_obj.browse(cr, uid, bns_ids, context=context):
                for line in sheet.line_ids:
                    if line.employee_id.id == contract.employee_id.id:
                        if line.type == 'percent':
                            bns_pct['number_of_days'] = line.amount / 100.0
                            bns_pct['number_of_hours'] = bns_pct['number_of_days']
                        elif line.type == 'fix':
                            bns_fix['number_of_days'] = line.amount
                            bns_fix['number_of_hours'] = bns_fix['number_of_days']
                        break
        
            res += [bns_pct, bns_fix]
        return res
