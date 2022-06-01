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

from datetime import datetime, timedelta

from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools.translate import _

class hr_weekly_ot(orm.Model):
    
    _inherit = 'hr.attendance.weekly.ot'
    
    _columns = {
        'demerit': fields.integer('Demerits 1'),
        'demerit2': fields.integer('Demerits 2'),
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
        ot_obj = self.pool.get('hr.attendance.weekly.ot')
        
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

            bns_demerit = {
                 'name': _("Demerits"),
                 'sequence': 100,
                 'code': 'DEMERIT',
                 'number_of_days': 0.0,
                 'number_of_hours': 0.0,
                 'rate': 0.0,
                 'contract_id': contract.id,
            }
            
            dTmpCStart = datetime.strptime(c_start, OE_DFORMAT).date()
            while dTmpCStart.weekday() != 0:
                dTmpCStart = dTmpCStart + timedelta(days= -1)
            tmp_c_start = dTmpCStart.strftime(OE_DFORMAT)
            dem_ids = []
            watt_ids = watt_obj.search(cr, uid, [('week_start', '>=', tmp_c_start),
                                                 ('week_start', '<=', c_end)],
                                       context=context)

            if len(watt_ids) > 0:
                dem_ids = ot_obj.search(cr, uid, [('weekly_id', 'in', watt_ids),
                                                  ('employee_id', '=', contract.employee_id.id)],
                                        context=context)
            for ot in ot_obj.browse(cr, uid, dem_ids, context=context):
                # If the weekly attendance starts in this period use the first demerit.
                # Otherwise, use the second demerit because this period starts in the middle
                # of the current weekly attendance.
                #
                dWeeklyStart = datetime.strptime(ot.weekly_id.week_start, OE_DFORMAT).date()
                if dWeeklyStart >= dFrom:
                    bns_demerit['number_of_hours'] += ot.demerit
                    bns_demerit['number_of_days'] += ot.demerit
                else:
                    bns_demerit['number_of_hours'] += ot.demerit2
                    bns_demerit['number_of_days'] += ot.demerit2
        
            res += [bns_demerit]
        return res
