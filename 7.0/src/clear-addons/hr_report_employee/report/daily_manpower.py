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

import logging
from datetime import datetime, timedelta
from pytz import timezone, utc

from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DATEFORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DATETIMEFORMAT
from report import report_sxw

_l = logging.getLogger(__name__)

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_no': self.get_no,
            'get_start': self.get_start,
            'get_end': self.get_end,
            'get_employee_qty': self.get_employee_qty,
            'get_hires': self.get_hires,
            'get_terminations': self.get_terminations,
            'get_in_xfers': self.get_in_transfers,
            'get_out_xfers': self.get_out_transfers,
            'get_al': self.get_al,
            'get_sl': self.get_sl,
            'get_ml': self.get_ml,
            'get_ol': self.get_ol,
            'get_sumh': self.get_sumh,
            'get_sumt': self.get_sumt,
            'get_sum_start': self.get_sum_start,
            'get_sum_end': self.get_sum_end,
            'get_sum_xfer_in': self.get_sum_xfer_in,
            'get_sum_xfer_out': self.get_sum_xfer_out,
            'get_sum_al': self.get_sum_al,
            'get_sum_sl': self.get_sum_sl,
            'get_sum_ml': self.get_sum_ml,
            'get_sum_ol': self.get_sum_ol,
        })
        
        self.LVCODES = ['LVBEREAVEMENT', 'LVWEDDING', 'LVMMEDICAL', 'LVPTO', 'LVCIVIC', 'LVSICK',
                        'LVSICK50', 'LVSICK00', 'LVMATERNITY', 'LVANNUAL', 'LVTRAIN', 'LVUTO']

        self.start_date = False
        self.end_date = False
        self.no = 0
        self.sum_start_ee = 0
        self.sum_end_ee = 0
        self.sumh = 0
        self.sumt = 0
        self.sum_xfer_in = 0
        self.sum_xfer_out = 0
        self._al = 0
        self._sl = 0
        self._ml = 0
        self._ol = 0
    
    def set_context(self, objects, data, ids, report_type=None):
        if data.get('form', False):
            if data['form'].get('start_date', False):
                self.start_date = data['form']['start_date']
            if data['form'].get('end_date', False):
                self.end_date = data['form']['end_date']
        
        return super(Parser, self).set_context(objects, data, ids, report_type=report_type)
    
    def get_start(self):
        return datetime.strptime(self.start_date, OE_DATEFORMAT).strftime('%B %d, %Y')
    
    def get_end(self):
        return datetime.strptime(self.end_date, OE_DATEFORMAT).strftime('%B %d, %Y')
    
    def get_no(self):
        
        self.no += 1
        return self.no
    
    def get_start_employee_ids(self, dept, s_date):
        
        c_obj = self.pool.get('hr.contract')
        
        c_ids = c_obj.search(self.cr, self.uid, [('date_start', '<=', s_date),
                                                 '|', ('date_end', '=', False),
                                                      ('date_end', '>', s_date),
                                                 '|', ('job_id.department_id', '=', dept.id),
                                                      ('end_job_id.department_id', '=', dept.id)])
        ee_ids = []
        if len(c_ids) > 0:
            c_datas = c_obj.read(self.cr, self.uid, c_ids, ['employee_id'])
            ee_ids += [c['employee_id'][0] for c in c_datas if c['employee_id'][0] not in ee_ids]
        
        # Some people may have a transfer,wage adjustment, etc, that cause the both
        # the first and second contract to *NOT* meet the above criteria, so we
        # make sure there isn't another contract that ends on the start date, but starts less
        # than 1 month from end date (to not catch re-activated employees).
        #
        d = datetime.strptime(s_date, OE_DATEFORMAT).date()
        d = d + timedelta(days= +31)
        c_ids = c_obj.search(self.cr, self.uid, [('date_end', '=', s_date),
                                                 '|', ('job_id.department_id', '=', dept.id),
                                                      ('end_job_id.department_id', '=', dept.id)])
        ee2_ids = []
        ee3_ids = []
        if len(c_ids) > 0:
            c_datas = c_obj.read(self.cr, self.uid, c_ids, ['employee_id'])
            ee2_ids += [c['employee_id'][0] for c in c_datas if c['employee_id'][0] not in ee2_ids]
            ee_obj = self.pool.get('hr.employee')
            for ee in ee_obj.browse(self.cr, self.uid, ee2_ids):
                for c in ee.contract_ids:
                    if c.date_start > s_date and c.date_start < d.strftime(OE_DATEFORMAT) and ee.id not in ee_ids:
                        ee3_ids.append(ee.id)
                        break
        ee_ids += ee3_ids
        
        return ee_ids
    
    def get_end_employee_ids(self, dept, s_date):
        
        c_obj = self.pool.get('hr.contract')
        
        c_ids = c_obj.search(self.cr, self.uid, [('date_start', '<', s_date),
                                                 '|', ('date_end', '=', False),
                                                      ('date_end', '>=', s_date),
                                                 '|', ('job_id.department_id', '=', dept.id),
                                                      ('end_job_id.department_id', '=', dept.id)])
        ee_ids = []
        if len(c_ids) > 0:
            c_datas = c_obj.read(self.cr, self.uid, c_ids, ['employee_id'])
            ee_ids += [c['employee_id'][0] for c in c_datas if c['employee_id'][0] not in ee_ids]
        
        # Some people may have a transfer,wage adjustment, etc, that cause the both
        # the first and second contract to *NOT* meet the above criteria, so we
        # make sure there isn't another contract after the end date, but starts less
        # than 1 month from end date (to not catch re-activated employees).
        #
        d = datetime.strptime(s_date, OE_DATEFORMAT).date()
        d = d + timedelta(days= +31)
        c_ids = c_obj.search(self.cr, self.uid, [('date_end', '<', s_date),
                                                 ('date_end', '>=', self.start_date),
                                                 '|', ('job_id.department_id', '=', dept.id),
                                                      ('end_job_id.department_id', '=', dept.id)])
        ee2_ids = []
        ee3_ids = []
        if len(c_ids) > 0:
            c_datas = c_obj.read(self.cr, self.uid, c_ids, ['employee_id'])
            ee2_ids += [c['employee_id'][0] for c in c_datas if c['employee_id'][0] not in ee2_ids]
            ee_obj = self.pool.get('hr.employee')
            for ee in ee_obj.browse(self.cr, self.uid, ee2_ids):
                for c in ee.contract_ids:
                    if c.date_start == s_date and ee.id not in ee_ids:
                        ee3_ids.append(ee.id)
                        break
        ee_ids += ee3_ids
        _l.warning('end ee_ids: %s', ee_ids)
        _l.warning('end ee2_ids: %s', ee2_ids)
        _l.warning('end ee3_ids: %s', ee3_ids)
        return ee_ids
    
    def get_employee_qty(self, dept, is_start=True):
        
        # If starting, get the number of employees as of
        # the previous day
        if is_start:
            dt = datetime.strptime(self.start_date, OE_DATEFORMAT)
            dt = dt + timedelta(days= -1)
            _l.warning('get_employee start dt: %s', dt)
            no = len(self.get_start_employee_ids(dept, dt.strftime(OE_DATEFORMAT)))
            self.sum_start_ee += no
        else:
            dt = datetime.strptime(self.end_date, OE_DATEFORMAT)
            dt = dt + timedelta(days= +1)
            _l.warning('get_employee end dt: %s', dt)
            no = len(self.get_end_employee_ids(dept, dt.strftime(OE_DATEFORMAT)))
            self.sum_end_ee += no
        
        return no
    
    def get_hires(self, dept):
        
        c_obj = self.pool.get('hr.contract')
        c_ids = c_obj.search(self.cr, self.uid, [('date_start', '>=', self.start_date),
                                                 ('date_start', '<=', self.end_date),
                                                 '|', ('job_id.department_id', '=', dept.id),
                                                      ('end_job_id.department_id', '=', dept.id)])
        ee_ids = []
        if len(c_ids) > 0:
            c_datas = c_obj.read(self.cr, self.uid, c_ids, ['employee_id'])
            ee_ids += [c['employee_id'][0] for c in c_datas if c['employee_id'][0] not in ee_ids]
            
            # Check to see this isn't a transfer or wage incr. or something
            ee_obj = self.pool.get('hr.employee')
            for ee in ee_obj.browse(self.cr, self.uid, ee_ids):
                for c in ee.contract_ids:
                    if c.date_start < self.start_date:
                        ee_ids.remove(ee.id)
                        break

        res = len(ee_ids)  
        self.sumh += res      
        return res and res or '-'
    
    def get_terminated_ee_ids(self, dept):
        
        res = 0
        seen_ids = []
        term_obj = self.pool.get('hr.employee.termination')
        term_ids = term_obj.search(self.cr, self.uid, [('name', '>=', self.start_date),
                                                       ('name', '<=', self.end_date),
                                                       ('state', 'not in', ['cancel'])])
        for term in term_obj.browse(self.cr, self.uid, term_ids):
            if term.employee_id.department_id:
                dept_id =  term.employee_id.department_id.id
            elif term.employee_id.saved_department_id:
                dept_id = term.employee_id.saved_department_id.id
            else:
                dept_id = False
            if term.employee_id.id not in seen_ids and dept_id == dept.id:
                res += 1
                seen_ids.append(term.employee_id.id)
        
        return (res, seen_ids)
    
    def get_terminations(self, dept):
        
        res, ee_ids = self.get_terminated_ee_ids(dept)
        self.sumt += res
        return res and res or '-'
    
    def get_transfers(self, dept, xfer_out=False):
        
        leaf = 'dst_department_id'
        if xfer_out:
            leaf = 'src_department_id'
        xfer_obj = self.pool.get('hr.department.transfer')
        xfer_ids = xfer_obj.search(self.cr, self.uid, [(leaf, '=', dept.id),
                                                       ('state', 'not in', ['draft', 'cancel']),
                                                       ('date', '>=', self.start_date),
                                                       ('date', '<=', self.end_date)])
        
        return len(xfer_ids)
    
    def get_in_transfers(self, dept):
        
        xfer_in = self.get_transfers(dept)
        self.sum_xfer_in += xfer_in
        return xfer_in and xfer_in or '-'
    
    def get_out_transfers(self, dept):
        
        xfer_out = self.get_transfers(dept, xfer_out=True)
        self.sum_xfer_out += xfer_out
        return xfer_out and xfer_out or '-'

    def _get_leave_ids(self, department, codes):
        
        if isinstance(codes, str):
            codes = [codes]
        
        department_id = department.id
        leave_obj = self.pool.get('hr.holidays')
        user = self.pool.get('res.users').browse(self.cr, self.uid, self.uid)
        if user and user.tz:
            local_tz = timezone(user.tz)
        else:
            local_tz = timezone('Africa/Addis_Ababa')
        dtStart = datetime.strptime(self.start_date + ' 00:00:00', OE_DATETIMEFORMAT)
        utcdtStart = (local_tz.localize(dtStart, is_dst=False)).astimezone(utc)
        dtNextStart = datetime.strptime(self.end_date + ' 00:00:00', OE_DATETIMEFORMAT)
        dtNextStart = dtNextStart + timedelta(days= +1)
        utcdtNextStart = (local_tz.localize(dtNextStart, is_dst=False)).astimezone(utc)
        leave_ids = leave_obj.search(self.cr, self.uid, [('holiday_status_id.code', 'in', codes),
                                                         ('date_from', '<', utcdtNextStart.strftime(OE_DATETIMEFORMAT)),
                                                         ('date_to', '>=', utcdtStart.strftime(OE_DATETIMEFORMAT)),
                                                         ('type', '=', 'remove'),
                                                         ('state', 'in', ['validate', 'validate1']),
                                                         '|', ('employee_id.department_id.id', '=', department_id),
                                                              ('employee_id.saved_department_id.id', '=', department_id)
                                                        ])
        return leave_ids
    
    def get_leave(self, department_id, codes):
        
        leave_ids = self._get_leave_ids(department_id, codes)
        res = len(leave_ids)
        return res
    
    def get_employees_on_leave(self, department_id, codes):
        
        leave_ids = self._get_leave_ids(department_id, codes)
        
        employee_ids = []
        data = self.pool.get('hr.holidays').read(self.cr, self.uid, leave_ids, ['employee_id'])
        for d in data:
            if d.get('employee_id', False) and d['employee_id'][0] not in employee_ids:
                employee_ids.append(d['employee_id'][0])
        
        return employee_ids
    
    def get_al(self, department_id):
        
        res = self.get_leave(department_id, 'LVANNUAL')
        self._al += res
        return (res and res or '-')
    
    def get_sl(self, department_id):
        
        res = self.get_leave(department_id, ['LVSICK', 'LVSICK50', 'LVSICK00'])
        self._sl += res
        return (res and res or '-')
    
    def get_ml(self, department_id):
        
        res = self.get_leave(department_id, 'LVMATERNITY')
        self._ml += res
        return (res and res or '-')
    
    def get_ol(self, department_id):
        
        codes = ['LVBEREAVEMENT', 'LVWEDDING', 'LVMMEDICAL', 'LVPTO', 'LVCIVIC']
        res = self.get_leave(department_id, codes)
        self._ol += res

        return (res and res or '-')
        
    def get_sumh(self):
        return self.sumh
    
    def get_sumt(self):
        return self.sumt
    
    def get_sum_start(self):
        return self.sum_start_ee
    
    def get_sum_end(self):
        return self.sum_end_ee
    
    def get_sum_xfer_in(self):
        return self.sum_xfer_in
    
    def get_sum_xfer_out(self):
        return self.sum_xfer_out
    
    def get_sum_al(self):
        return self._al and self._al or '-'
    
    def get_sum_sl(self):
        return self._sl and self._sl or '-'
    
    def get_sum_ml(self):
        return self._ml and self._ml or '-'
    
    def get_sum_ol(self):
        return self._ol and self._ol or '-'
