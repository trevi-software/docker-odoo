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

from datetime import datetime
from dateutil.relativedelta import relativedelta

from openerp.report import report_sxw
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT

class Parser(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_no': self._get_no,
            'week_start': self._get_week_start,
            'week_no': self._get_week_no,
            'mday': self._get_mday,
            'is_al': self._is_al,
            'is_ml': self._is_ml,
            'get_status': self._get_status,
        })
        
        self.no = 0
        self.department_id = 0
    
    def set_context(self, objects, data, ids, report_type=None):
        if data.get('form', False) and data['form'].get('week_start', False):
            self.week_start = data['form']['week_start']
        else:
            self.week_start = (datetime.now().date() + relativedelta(days= +(7 - datetime.now().date().weekday()))).strftime('%Y-%m-%d')
        
        if data.get('form', False) and data['form'].get('week_no'):
            self.week_no = data['form']['week_no']
        else:
            self.week_no = datetime.strptime(self.week_start, '%Y-%m-%d').isocalendar()[1]
        
        return super(Parser, self).set_context(objects, data, ids, report_type=report_type)
    
    def _get_week_start(self):
        dt = datetime.strptime(self.week_start, '%Y-%m-%d')
        return dt.strftime('%B %d, %Y')
    
    def _get_week_no(self):
        return self.week_no
    
    def _get_no(self, d_id):
        if d_id != self.department_id:
            self.department_id = d_id
            self.no = 0
        self.no += 1
        return self.no
    
    def _get_mday(self, wday):
        dt = datetime.strptime(self.week_start, '%Y-%m-%d')
        dt = dt + relativedelta(days= +wday)
        return dt.strftime('%d')

    def _get_lv(self, ee_id, wday):
        
        lv_obj = self.pool.get('hr.holidays')
        code = None
        
        dt = datetime.strptime(self.week_start + ' 12:00:00', OE_DTFORMAT)
        dt = dt + relativedelta(days= +wday)
        
        lv_ids = lv_obj.search(self.cr, self.uid, [('employee_id', '=', ee_id),
                                                   ('type', '=', 'remove'),
                                                   ('state', '=', 'validate'),
                                                   ('date_from', '<=', dt.strftime(OE_DTFORMAT)),
                                                   ('date_to', '>=', dt.strftime(OE_DTFORMAT))])
        if len(lv_ids) > 0:
            lv = lv_obj.browse(self.cr, self.uid, lv_ids[0])
            code = lv.holiday_status_id.code
        
        return code

    def _is_al(self, ee_id, wday):
        
        code = self._get_lv(ee_id, wday)
        if code != None and code == 'LVANNUAL':
            return True
        return False

    def _is_ml(self, ee_id, wday):
        
        code = self._get_lv(ee_id, wday)
        if code != None and code == 'LVMATERNITY':
            return True
        return False

    def _get_status(self, ee, wday):
        
        if self._is_al(ee.id, wday):
            return 'AL'
        elif self._is_ml(ee.id, wday):
            return 'ML'
        elif ee.rest_day == wday:
            return 'Off'
        return ''
