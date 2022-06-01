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

from openerp.addons.decimal_precision import decimal_precision as dp
from openerp.osv import fields, osv

class bunching_summary_wizard(osv.TransientModel):
    
    _name = 'hr.bunching.shared.summary.wizard'
    
    _columns = {
        'start_date': fields.date('Start', required=True),
        'end_date': fields.date('End', required=True),
        'department_ids': fields.many2many('hr.department', 'bunch_shared_sum_by_dept_rel', 'department_id',
                                           'wizard_id', 'Departments'),
        'state': fields.selection([('all', 'All'), ('approve', 'Approved Only')], 'State'),
        'price': fields.float('Price/Bunch Over Target', digits_compute=dp.get_precision('Payroll'), required=True),
        'quota': fields.integer('Daily Target', required=True),
    }
    
    _defaults = {
        'state': 'approve',
        'price': 0.22,
        'quota': 240,
    }
    
    def print_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        datas = {'form': self.read(cr, uid, ids)[0],
                 'model': 'hr.department'}
        datas['ids'] = datas['form']['department_ids']
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'hr_bunching_shared_summary',
            'datas': datas,
        }
