#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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

class hr_weekly_attendance(orm.Model):
    
    _inherit = 'hr.attendance.weekly'
    
    def get_ids_from_period(self, cr, uid, dept_ids, dStart, dEnd, context=None):
        
        dStartApprox = dStart
        while dStartApprox.weekday() != 0:
            dStartApprox += timedelta(days= -1)
        
        ids = self.search(cr, uid, [('department_id', 'in', dept_ids),
                                    ('week_start', '>=', dStartApprox.strftime(OE_DFORMAT)),
                                    ('week_start', '<=', dEnd.strftime(OE_DFORMAT))],
                          context=context)
        return ids

class payroll_period(orm.Model):
    
    _inherit = 'hr.payroll.period'
    
    def lock_period(self, cr, uid, periods, employee_ids, context=None):
        
        return super(payroll_period, self).lock_period(cr, uid, periods, employee_ids,
                                                       context=context)

class period_wizard(orm.TransientModel):
    
    _inherit = 'hr.payroll.period.end.1'

    def create_payslip_runs(self, cr, uid, period_id, previous_register_id, register_values, dept_ids, contract_ids,
                            date_start, date_end, annual_pay_periods, context=None):
        
        return super(period_wizard, self).create_payslip_runs(cr, uid, period_id, previous_register_id, register_values, dept_ids, contract_ids,
                                                              date_start, date_end, annual_pay_periods, context=context)
