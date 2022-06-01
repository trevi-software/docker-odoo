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

from datetime import datetime, timedelta

from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT

class rx_type(osv.Model):
    
    _name = 'hr.patient.history.rx'
    
    _columns = {
        'name': fields.char('Name', size=128, required=True),
        'desc': fields.text('Description'),
    }

class hr_patient_history(osv.Model):
    
    _name = 'hr.patient.history'
    _description = 'Patient History'
    
    def _get_history(self, cr, uid, ids, field_name, arg, context=None):
        
        res = dict.fromkeys(ids, [])
        datas = self.read(cr, uid, ids, ['employee_id'], context=context)
        for d in datas:
            cr.execute('SELECT id FROM hr_patient_history WHERE employee_id=%s', (d['employee_id'][0],))
            rs = cr.dictfetchall()
            [res[d['id']].append(r['id']) for r in rs if r['id'] != d['id']]
        
        return res
    
    _columns = {
        'name': fields.char('Name', required=True),
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True),
        'employee_no': fields.related('employee_id', 'employee_no', type='char',
                                      string='Employee ID', readonly=True, store=True),
        'f_employee_no': fields.related('employee_id', 'f_employee_no', type='char',
                                        string='Employee ID', readonly=True, store=True),
        'department_id': fields.related('employee_id', 'department_id', type='many2one',
                                        obj='hr.department', string='Department',
                                        store=True, readonly=True),
        'date': fields.date('Date', required=True),
        'age': fields.integer('Age'),
        'gender': fields.selection([('f', 'Female'), ('m', 'Male')], 'Sex', required=True),
        'cc': fields.text('Chief Complaint', groups='patient_history.group_hr_nurse'),
        'vs': fields.text('Vital Signs', groups='patient_history.group_hr_nurse'),
        'dx': fields.text('Diagnosis', groups='patient_history.group_hr_nurse'),
        'rx_type_id': fields.many2one('hr.patient.history.rx', 'Rx Type'),
        'rx': fields.text('Rx Note', groups='patient_history.group_hr_nurse'),
        'patient_history_ids': fields.function(_get_history, type='one2many', method=True,
                                               relation='hr.patient.history'),
        'active': fields.boolean('Active'),
    }
    
    _order = 'name, date'
    
    _defaults = {
        'date': lambda *a: datetime.now().strftime(OE_DFORMAT),
        'active': True,
    }
    
    def onchange_employee(self, cr, uid, ids, employee_id, context=None):
        
        res = {'value': {
                         'name': False,
                         'age': False,
                         'gender': False,
                        }
              }
        
        if employee_id:
            ee = self.pool.get('hr.employee').browse(cr, uid, employee_id, context=context)
            
            if ee.birthday:
                dToday = datetime.now().date()
                dBday = datetime.strptime(ee.birthday, OE_DFORMAT).date()
                res['value']['age'] = (dToday - dBday).days / 365
            
            if ee.gender:
                res['value']['gender'] = ee.gender == 'female' and 'f' or 'm'
            
            res['value']['name'] = ee.name
        
        return res
