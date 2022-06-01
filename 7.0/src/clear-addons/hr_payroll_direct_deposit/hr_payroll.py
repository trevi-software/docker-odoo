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

class hr_payroll_dd(orm.Model):
    
    _name = 'hr.payroll.directdeposit'
    _description = 'Payroll Direct Deposit'
    
    _columns = {
        'account_name': fields.char('Bank Account Number', size=128, required=True),
        'bank_name': fields.char('Bank Name', size=256, required=True),
        'effective_date': fields.date('Effective Date', required=True),
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True),
    }
    
    def name_get(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (long, int)):
            ids = [ids]
        
        res = dict.fromkeys(ids)
        name = ''
        for rec in self.browse(cr, uid, ids, context=context):
            name += rec.bank_name +':'+ rec.account_name
        
        return res
    
    def get_latest(self, cr, uid, dds, dToday, context=None):
        '''Return a record with an effective date before dToday but greater than all others'''
        
        if len(dds) == 0 or not dToday:
            return None
        
        res = None
        for line in dds:
            dLine = datetime.strptime(line.effective_date, OE_DFORMAT).date()
            if dLine <= dToday:
                if res == None:
                    res = line
                elif dLine > datetime.strptime(res.effective_date, OE_DFORMAT).date():
                    res = line
        
        return res

class hr_employee(orm.Model):
    
    _name = 'hr.employee'
    _inherit = 'hr.employee'
    
    _columns = {
        'use_direct_deposit': fields.boolean('Direct Deposit', required=False),
        'dd_ids': fields.one2many('hr.payroll.directdeposit', 'employee_id',
                                  'Direct Deposit'),
    }

    _defaults = {
        'use_direct_deposit': False,
    }
