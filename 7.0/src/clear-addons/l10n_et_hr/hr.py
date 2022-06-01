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

from datetime import datetime, date

from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

from openerp.addons.ethiopic_calendar.ethiopic_calendar import ET_MONTHS_SELECTION
from openerp.addons.ethiopic_calendar.ethiopic_calendar import ET_DAYOFMONTH_SELECTION
from openerp.addons.ethiopic_calendar.pycalcal import pycalcal as pcc

class hr_employee(osv.Model):
    
    _name = 'hr.employee'
    _inherit = 'hr.employee'
    
    _columns = {
        'ethiopic_name': fields.char('Ethiopic Name', size=512),
        'use_ethiopic_dob': fields.boolean('Use Ethiopic Birthday'),
        'etcal_dob_month': fields.selection(ET_MONTHS_SELECTION, 'Month'),
        'etcal_dob_day': fields.selection(ET_DAYOFMONTH_SELECTION, 'Day'),
        'etcal_dob_year': fields.char('Year', size=4),
    }
    
    _defaults = {
        'use_ethiopic_dob': True,
    }
    
    def onchange_etdob(self, cr, uid, ids, y, m, d, context=None):
        
        res = {'value': {'birthday': False}}
        if d and m and y:
            dob = pcc.gregorian_from_fixed(
                        pcc.fixed_from_ethiopic(
                                pcc.ethiopic_date(int(y), int(m), int(d))))
            res['value']['birthday'] = date(year=dob[0], month=dob[1], day=dob[2]).strftime(DEFAULT_SERVER_DATE_FORMAT)
        return res
    
    def create(self, cr, uid, vals, context=None):
        
        # Only on creation: if Ethiopian birthday but not European, convert Ethio -> European.
        # Otherwise, if there's a European birthday but not Ethiopian, convert European -> Ethio.
        #
        if vals.get('etcal_dob_year', False) and vals.get('etcal_dob_month', False) and vals.get('etcal_dob_day', False) and not vals.get('birthday', False):
            dob = pcc.gregorian_from_fixed(
                        pcc.fixed_from_ethiopic(
                                pcc.ethiopic_date(int(vals['etcal_dob_year']), int(vals['etcal_dob_month']),
                                                  int(vals['etcal_dob_day']))))
            vals['birthday'] = date(year=dob[0], month=dob[1], day=dob[2]).strftime(DEFAULT_SERVER_DATE_FORMAT)
        elif vals.get('birthday', False) and not vals.get('etcal_dob_year'):
            dBirth = datetime.strptime(vals['birthday'], DEFAULT_SERVER_DATE_FORMAT).date()
            et_dob = pcc.ethiopic_from_fixed(
                            pcc.fixed_from_gregorian(
                                    pcc.gregorian_date(dBirth.year, dBirth.month, dBirth.day)))
            et_vals = {
                'etcal_dob_year': str(et_dob[0]),
                'etcal_dob_month': str(et_dob[1]),
                'etcal_dob_day': str(et_dob[2]),
            }
            vals.update(et_vals)
        
        return super(hr_employee, self).create(cr, uid, vals, context=context)
    
    def write(self, cr, uid, ids, vals, context=None):
        
        res =  super(hr_employee, self).write(cr, uid, ids, vals, context=context)
        
        y = vals.get('etcal_dob_year', False)
        m = vals.get('etcal_dob_month', False)
        d = vals.get('etcal_dob_day', False)
        
        if y or m or d:
            for i in ids:
                data = {'birthday': ''}
                rdata = self.read(cr, uid, i, ['etcal_dob_year', 'etcal_dob_month', 'etcal_dob_day'],
                                  context=context)
                if not y:
                    y = rdata['etcal_dob_year']
                if not m:
                    m = rdata['etcal_dob_month']
                if not d:
                    d = rdata['etcal_dob_day']
                dob = pcc.gregorian_from_fixed(
                            pcc.fixed_from_ethiopic(
                                    pcc.ethiopic_date(int(y), int(m), int(d))))
                data['birthday'] = date(year=dob[0], month=dob[1], day=dob[2]).strftime(DEFAULT_SERVER_DATE_FORMAT)
                
                super(hr_employee, self).write(cr, uid, i, data, context=context)
        
        return res

class hr_department(osv.Model):
    
    _name = 'hr.department'
    _inherit = 'hr.department'
    
    def ethiopic_name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not ids:
            return []
        reads = self.read(cr, uid, ids, ['ethiopic_name','parent_id'], context=context)
        res = []
        for record in reads:
            ethiopic_name = record['ethiopic_name']
            if ethiopic_name and record['parent_id']:
                readen = self.read(cr, uid, record['parent_id'][0], ['ethiopic_name'], context=context)
                ethiopic_name = readen.get('ethiopic_name', False) and readen['ethiopic_name'] or '' + ' / ' + ethiopic_name
            res.append((record['id'], ethiopic_name))
        return res

    def _dept_ethiopic_name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.ethiopic_name_get(cr, uid, ids, context=context)
        return dict(res)

    _columns = {
        'ethiopic_name': fields.char('Ethiopic Name', size=512),
        'complete_ethiopic_name': fields.function(_dept_ethiopic_name_get_fnc, type="char", string='Name'),
    }

class hr_job(osv.Model):
    
    _name = 'hr.job'
    _inherit = 'hr.job'
    
    _columns = {
        'ethiopic_name': fields.char('Ethiopic Name', size=512),
    }
