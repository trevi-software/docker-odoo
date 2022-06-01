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

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_hno': self.get_hno,
            'get_tno': self.get_tno,
            'get_start': self.get_start,
            'get_end': self.get_end,
            'get_hires': self.get_hires,
            'get_terminations': self.get_terminations,
            'get_total_terminations': self.get_sumt,
            'get_total_hires': self.get_sumh,
            'get_total_hires_salary': self.get_sumhsalary,
            'get_total_terminations_salary': self.get_sumtsalary,
            'get_undefined_hires': self.get_undefined_hires,
        })
        
        self.start_date = False
        self.end_date = False
        self.hno = 0
        self.tno = 0
        self.hdepartment_id = False
        self.tdepartment_id = False
        self.sumh = 0
        self.sumt = 0
        self.hsalary = 0.0
        self.tsalary = 0.0
        self.hired_ee_list = None
    
    def set_context(self, objects, data, ids, report_type=None):
        if data.get('form', False) and data['form'].get('start_date', False):
            self.start_date = data['form']['start_date']
        if data.get('form', False) and data['form'].get('end_date', False):
            self.end_date = data['form']['end_date']
        
        return super(Parser, self).set_context(objects, data, ids, report_type=report_type)
    
    def get_start(self):
        return datetime.strptime(self.start_date, OE_DATEFORMAT).strftime('%B %d, %Y')
    
    def get_end(self):
        return datetime.strptime(self.end_date, OE_DATEFORMAT).strftime('%B %d, %Y')
    
    def get_hno(self, department_id):
        
        if not self.hdepartment_id or self.hdepartment_id != department_id:
            self.hdepartment_id = department_id
            self.hno = 1
        else:
            self.hno += 1
        
        return self.hno
    
    def get_tno(self, department_id):
        
        if not self.tdepartment_id or self.tdepartment_id != department_id:
            self.tdepartment_id = department_id
            self.tno = 1
        else:
            self.tno += 1
        
        return self.tno

    def get_undefined_hires(self, docount=False):
    
        res = []
        seen_list = self.hired_ee_list
        if seen_list is None:
            seen_list = []
        dStart = datetime.strptime(self.start_date, OE_DATEFORMAT).date()
        dEnd = datetime.strptime(self.end_date, OE_DATEFORMAT).date()
        ee_obj = self.pool.get('hr.employee')
        ee_ids = ee_obj.search(self.cr, self.uid,
                               [('status', 'in', ['pending_inactive', 'inactive']),
                                ('id', 'not in', seen_list)])
        for ee in ee_obj.browse(self.cr, self.uid, ee_ids):
            # if there are no contracts assume this is not a new employee
            if len(ee.contract_ids) == 0:
                continue
            data = ee_obj.get_initial_employment_date(self.cr, self.uid, [ee.id])
            d = data[ee.id]
            if d >= dStart and d <= dEnd:
                c = ee_obj._get_contracts_list(ee)
                res.append({'name': ee.name,
                            'f_employee_no': ee.f_employee_no,
                            'hire_date': c[0].date_start,
                            'salary': c[0].wage,
                            'dept': ee.department_id and ee.department_id.name or ''})
                if docount:
                    self.sumh += 1
                    self.hsalary += c[0].wage
                if self.hired_ee_list is None:
                    self.hired_ee_list = [ee.id]
                else:
                    self.hired_ee_list.append(ee.id)
        return res

    def get_hires(self, department_id, docount=False):
        
        res = []
        dStart = datetime.strptime(self.start_date, OE_DATEFORMAT).date()
        dEnd = datetime.strptime(self.end_date, OE_DATEFORMAT).date()
        department = self.pool.get('hr.department').browse(self.cr, self.uid, department_id)
        ee_obj = self.pool.get('hr.employee')
        ee_ids = ee_obj.search(self.cr, self.uid,
                               [('saved_department_id', '=', department_id)])
        for ee in department.member_ids:
            if ee.id not in ee_ids:
                ee_ids.append(ee.id)

        for ee in ee_obj.browse(self.cr, self.uid, ee_ids):
            # if there are no contracts assume this is not a new employee
            if len(ee.contract_ids) == 0:
                continue
            data = ee_obj.get_initial_employment_date(self.cr, self.uid, [ee.id])
            d = data[ee.id]
            if d >= dStart and d <= dEnd:
                c = ee_obj._get_contracts_list(ee)
                res.append({'name': ee.name,
                            'f_employee_no': ee.f_employee_no,
                            'hire_date': c[0].date_start,
                            'salary': c[0].wage})
                if docount:
                    self.sumh += 1
                    self.hsalary += c[0].wage
                if self.hired_ee_list is None:
                    self.hired_ee_list = [ee.id]
                else:
                    self.hired_ee_list.append(ee.id)
        return res
    
    def get_terminations(self, department_id, docount=False):
        
        res = []
        seen_ids = []
        wages = 0.0
        ee_obj = self.pool.get('hr.employee')
        term_obj = self.pool.get('hr.employee.termination')
        term_ids = term_obj.search(self.cr, self.uid, [('name', '>=', self.start_date),
                                                       ('name', '<=', self.end_date),])
        for term in term_obj.browse(self.cr, self.uid, term_ids):
            if term.employee_id.department_id:
                dept_id =  term.employee_id.department_id.id
            elif term.employee_id.saved_department_id:
                dept_id = term.employee_id.saved_department_id.id
            else:
                dept_id = False
            if term.employee_id.id not in seen_ids and dept_id == department_id:
                c = ee_obj._get_contracts_list(term.employee_id)
                res.append({'name': term.employee_id.name,
                            'f_employee_no': term.employee_id.f_employee_no,
                            'termination_date': term.name,
                            'salary': c[-1].wage})
                seen_ids.append(term.employee_id.id)
                wages += c[-1].wage
        if docount:
            self.sumt += len(res)
            self.tsalary += wages

        return res
    
    def get_sumh(self):
        return self.sumh
    
    def get_sumt(self):
        return self.sumt
    
    def get_sumhsalary(self):
        return self.hsalary
    
    def get_sumtsalary(self):
        return self.tsalary
