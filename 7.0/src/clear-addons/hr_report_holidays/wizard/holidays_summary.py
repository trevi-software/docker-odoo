#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2013-2015 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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

class hr_turnover_wizard(osv.TransientModel):
    
    _name = 'hr.holidays.summary'
    _description = 'Holidays Summary Report Wizard'
    
    _columns = {
        'department_ids': fields.many2many('hr.department', 'hr_holidays_summary_wizard_rel', 'wizard_id',
                                           'department_id', 'Departments'),
        'date_end': fields.date('Ending Date', required=True),
    }
    
    def print_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        datas = {'form': self.read(cr, uid, ids)[0],
                 'model': 'hr.department'}
        datas['ids'] = datas['form']['department_ids']
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'hr_holidays_summary',
            'datas': datas,
        }
