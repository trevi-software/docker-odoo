#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyrigth (C) 2013 Michael Telahun Makonnen <mmakonnen@gmail.com>
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

from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DATEFORMAT
from report import report_sxw

from ethiopic_calendar.pycalcal import pycalcal as pcc
from ethiopic_calendar.ethiopic_calendar import ET_MONTHS_SELECTION_AM

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_employee_list': self.get_employee_list,
            'birthday': self.birthday,
            'et_hire_date': self.et_hire_date,
            'gender': self.gender,
            'get_no': self.get_no,
            'tin': self.tin,
            'company_tin': self.company_tin,
        })
        
        self.no = 0
        self.department_id = False
    
    def get_no(self, department_id):
        
        if not self.department_id:
            self.department_id = department_id
            self.no = 1
        else:
            self.no += 1
        
        return self.no
    
    def get_employee_list(self, department_id):
        
        imd_obj = self.pool.get('ir.model.data')
        ee_obj = self.pool.get('hr.employee')
        res_model, res_id = imd_obj.get_object_reference(self.cr, self.uid,
                                                         'base', 'et')
        ee_ids = ee_obj.search(self.cr, self.uid,
                               [('active', '=', True),
                                '|', ('department_id.id', '=', department_id),
                                     ('saved_department_id.id', '=', department_id),
                                ('country_id', '=', res_id)])
        ees = ee_obj.browse(self.cr, self.uid, ee_ids)
        return ees
    
    def birthday(self, ee):
        
        if not ee.etcal_dob_year:
            return ''
        return str(ee.etcal_dob_day) +'/'+ str(ee.etcal_dob_month) +'/'+ str(ee.etcal_dob_year)
    
    def et_hire_date(self, ee):
        
        hire = False
        earliest = False
        if ee.initial_employment_date:
            d = datetime.strptime(ee.initial_employment_date, OE_DATEFORMAT).date()
        else:
            for contract in ee.contract_ids:
                if not earliest or contract.date_start < earliest:
                    earliest = contract.date_start
            if earliest:
                d = datetime.strptime(earliest, OE_DATEFORMAT).date()
        
        if ee.initial_employment_date or earliest:
            hire = pcc.ethiopic_from_fixed(
                pcc.fixed_from_gregorian(
                        pcc.gregorian_date(d.year, d.month, d.day)))
        
        if not hire:
            return ''
        
        return str(hire[2]) +'/'+ str(hire[1]) +'/'+ str(hire[0])
    
    def gender(self, ee):
        
        if ee.gender == 'female':
            return u'ሴት'
        elif ee.gender == 'male':
            return u'ወንድ'
        return ''
    
    def tin(self, ee):
        
        if not ee.tin_no:
            return ''
        return str(ee.tin_no) + ' _'
    
    def company_tin(self, tin):
        
        if not tin:
            return ''
        return str(tin) + ' _'
