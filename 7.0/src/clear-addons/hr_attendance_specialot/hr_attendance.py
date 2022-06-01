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

from datetime import datetime

from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools.translate import _

class hr_special_ot(orm.Model):
    
    _name = 'hr.attendance.weekly.specialot'
    _description = 'Weekly Attendance Special OT'
    
    _columns = {
        'weekly_id': fields.many2one('hr.attendance.weekly', 'Weekly Attendance', required=True),
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True),
        'hours': fields.float('Hours', ),
    }
    
    def _get_weekly(self, cr, uid, context=None):
        
        if context == None:
            context = {}
        
        return context.get('weekly_id', False)
    
    _defaults = {
        'weekly_id': _get_weekly,
    }

class hr_attendance_weekly(orm.Model):
    
    _inherit = 'hr.attendance.weekly'
    
    _columns = {
        'specialot_ids': fields.one2many('hr.attendance.weekly.specialot', 'weekly_id', 'Special OT'),
    }

class hr_payslip(orm.Model):
    
    _name = 'hr.payslip'
    _inherit = 'hr.payslip'
    
    def get_worked_day_lines(self, cr, uid, contract_ids, date_from, date_to, context=None):
        
        res = super(hr_payslip, self).get_worked_day_lines(cr, uid, contract_ids, date_from, date_to,
                                                           context=context)
        if len(res) == 0:
            return res
        
        c_obj = self.pool.get('hr.contract')
        watt_obj = self.pool.get('hr.attendance.weekly')
        spot_obj = self.pool.get('hr.attendance.weekly.specialot')
        
        dFrom = datetime.strptime(date_from, OE_DFORMAT).date()
        dTo = datetime.strptime(date_to, OE_DFORMAT).date()

        for contract in c_obj.browse(cr, uid, contract_ids, context=context):

            # Set the proper time frame
            #
            c_start = date_from
            c_end = date_to
            if contract.date_start:
                dc_start = datetime.strptime(contract.date_start, OE_DFORMAT).date()
                if dc_start > dFrom:
                    c_start = dc_start.strftime(OE_DFORMAT)
            if contract.date_end:
                dc_end = datetime.strptime(contract.date_end, OE_DFORMAT).date()
                if dc_end < dTo:
                    c_end = dc_end.strftime(OE_DFORMAT)

            bns_ot = {
                 'name': _("Special OT"),
                 'sequence': 100,
                 'code': 'SPOT',
                 'number_of_days': 0.0,
                 'number_of_hours': 0.0,
                 'rate': 0.0,
                 'contract_id': contract.id,
            }
            
            spot_ids = []
            watt_ids = watt_obj.search(cr, uid, [('week_start', '>=', c_start),
                                                 ('week_start', '<=', c_end)],
                                       context=context)

            # Collect Special OT data
            #
            if len(watt_ids) > 0:
                spot_ids = spot_obj.search(cr, uid, [('weekly_id', 'in', watt_ids),
                                                     ('employee_id', '=', contract.employee_id.id)],
                                           context=context)
            if len(spot_ids) > 0:
                spot_data = spot_obj.read(cr, uid, spot_ids, [('hours')], context=context)
                for data in spot_data:
                    bns_ot['number_of_hours'] += data['hours']
                    bns_ot['number_of_days'] += data['hours']
        
            res += [bns_ot]
        
        return res
