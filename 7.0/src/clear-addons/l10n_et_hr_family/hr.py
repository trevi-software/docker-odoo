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
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT

from ethiopic_calendar.ethiopic_calendar import ET_DAYOFMONTH_SELECTION
from ethiopic_calendar.ethiopic_calendar import ET_MONTHS_SELECTION
from ethiopic_calendar.pycalcal import pycalcal as pcc

class hr_employee(osv.Model):
    
    _inherit = 'hr.employee'
    
    _columns = {
        'fam_spouse_ethiopic_name': fields.char('Ethiopic Name', size=512),
        'fam_spouse_use_etdob': fields.boolean('Use Ethiopic Birthday'),
        'fam_spouse_etcal_dob_month': fields.selection(ET_MONTHS_SELECTION, 'Month'),
        'fam_spouse_etcal_dob_day': fields.selection(ET_DAYOFMONTH_SELECTION, 'Day'),
        'fam_spouse_etcal_dob_year': fields.char('Year', size=4),
        'fam_father_ethiopic_name': fields.char('Ethiopic Name', size=512),
        'fam_father_use_etdob': fields.boolean('Use Ethiopic Birthday'),
        'fam_father_etcal_dob_month': fields.selection(ET_MONTHS_SELECTION, 'Month'),
        'fam_father_etcal_dob_day': fields.selection(ET_DAYOFMONTH_SELECTION, 'Day'),
        'fam_father_etcal_dob_year': fields.char('Year', size=4),
        'fam_mother_ethiopic_name': fields.char('Ethiopic Name', size=512),
        'fam_mother_use_etdob': fields.boolean('Use Ethiopic Birthday'),
        'fam_mother_etcal_dob_month': fields.selection(ET_MONTHS_SELECTION, 'Month'),
        'fam_mother_etcal_dob_day': fields.selection(ET_DAYOFMONTH_SELECTION, 'Day'),
        'fam_mother_etcal_dob_year': fields.char('Year', size=4),
    }
    
    _defaults = {
        'fam_spouse_use_etdob': True,
        'fam_father_use_etdob': True,
        'fam_mother_use_etdob': True,
    }
    
    def _onchange_etdob(self, cr, uid, ids, y, m, d, field_name, context=None):
        
        res = {'value': {field_name: False}}
        if d and m and y:
            dob = pcc.gregorian_from_fixed(
                        pcc.fixed_from_ethiopic(
                                pcc.ethiopic_date(int(y), int(m), int(d))))
            res['value'][field_name] = date(year=dob[0], month=dob[1], day=dob[2]).strftime(OE_DFORMAT)
        return res
    
    def onchange_spouse_etdob(self, cr, uid, ids, y, m, d, context=None):
        
        return self._onchange_etdob(cr, uid, ids, y, m, d, 'fam_spouse_dob', context)
    
    def onchange_father_etdob(self, cr, uid, ids, y, m, d, context=None):
        
        return self._onchange_etdob(cr, uid, ids, y, m, d, 'fam_father_dob', context)
    
    def onchange_mother_etdob(self, cr, uid, ids, y, m, d, context=None):
        
        return self._onchange_etdob(cr, uid, ids, y, m, d, 'fam_mother_dob', context)
    
    # May modify parameter: vals
    #
    def _update_dob_create_vals(self, cr, uid, vals, keys, context=None):
        
        # Only on creation: if Ethiopian birthday but not European, convert Ethio -> European.
        # Otherwise, if there's a European birthday but not Ethiopian, convert European -> Ethio.
        #
        if vals.get(keys['etyear'], False) and vals.get(keys['etmonth'], False) and vals.get(keys['etday'], False) and not vals.get(keys['dob'], False):
            dob = pcc.gregorian_from_fixed(
                        pcc.fixed_from_ethiopic(
                                pcc.ethiopic_date(int(vals[keys['etyear']]), int(vals[keys['etmonth']]),
                                                  int(vals[keys['etday']]))))
            vals[keys['dob']] = date(year=dob[0], month=dob[1], day=dob[2]).strftime(OE_DFORMAT)
        elif vals.get(keys['dob'], False) and not vals.get(keys['etyear']):
            dBirth = datetime.strptime(vals[keys['dob']], OE_DFORMAT).date()
            et_dob = pcc.ethiopic_from_fixed(
                            pcc.fixed_from_gregorian(
                                    pcc.gregorian_date(dBirth.year, dBirth.month, dBirth.day)))
            et_vals = {
                keys['etyear']: str(et_dob[0]),
                keys['etmonth']: str(et_dob[1]),
                keys['etday']: str(et_dob[2]),
            }
            vals.update(et_vals)
        
        return
    
    def create(self, cr, uid, vals, context=None):
        
        spouse_keys = {
            'dob': 'fam_spouse_dob',
            'etyear': 'fam_spouse_etcal_dob_year',
            'etmonth': 'fam_spouse_etcal_dob_month',
            'etday': 'fam_spouse_etcal_dob_day',
        }
        father_keys = {
            'dob': 'fam_father_dob',
            'etyear': 'fam_father_etcal_dob_year',
            'etmonth': 'fam_father_etcal_dob_month',
            'etday': 'fam_father_etcal_dob_day',
        }
        mother_keys = {
            'dob': 'fam_father_dob',
            'etyear': 'fam_father_etcal_dob_year',
            'etmonth': 'fam_father_etcal_dob_month',
            'etday': 'fam_father_etcal_dob_day',
        }
        self._update_dob_create_vals(cr, uid, vals, spouse_keys, context=context)
        self._update_dob_create_vals(cr, uid, vals, father_keys, context=context)
        self._update_dob_create_vals(cr, uid, vals, mother_keys, context=context)
        
        return super(hr_employee, self).create(cr, uid, vals, context=context)
    
    # May update some DoB fields in database
    #
    def _write_dob_vals(self, cr, uid, ids, vals, keys, context=None):
        
        y = vals.get(keys['etyear'], False)
        m = vals.get(keys['etmonth'], False)
        d = vals.get(keys['etday'], False)
        
        if y or m or d:
            for i in ids:
                data = {keys['dob']: ''}
                rdata = self.read(cr, uid, i, [keys['etyear'], keys['etmonth'], keys['etday']],
                                  context=context)
                if not y:
                    y = rdata[keys['etyear']]
                if not m:
                    m = rdata[keys['etmonth']]
                if not d:
                    d = rdata[keys['etday']]
                dob = pcc.gregorian_from_fixed(
                            pcc.fixed_from_ethiopic(
                                    pcc.ethiopic_date(int(y), int(m), int(d))))
                data[keys['dob']] = date(year=dob[0], month=dob[1], day=dob[2]).strftime(OE_DFORMAT)
                
                super(hr_employee, self).write(cr, uid, i, data, context=context)
        
        return
    
    def write(self, cr, uid, ids, vals, context=None):
        
        res =  super(hr_employee, self).write(cr, uid, ids, vals, context=context)
        
        spouse_keys = {
            'dob': 'fam_spouse_dob',
            'etyear': 'fam_spouse_etcal_dob_year',
            'etmonth': 'fam_spouse_etcal_dob_month',
            'etday': 'fam_spouse_etcal_dob_day',
        }
        father_keys = {
            'dob': 'fam_father_dob',
            'etyear': 'fam_father_etcal_dob_year',
            'etmonth': 'fam_father_etcal_dob_month',
            'etday': 'fam_father_etcal_dob_day',
        }
        mother_keys = {
            'dob': 'fam_father_dob',
            'etyear': 'fam_father_etcal_dob_year',
            'etmonth': 'fam_father_etcal_dob_month',
            'etday': 'fam_father_etcal_dob_day',
        }
        self._write_dob_vals(cr, uid, ids, vals, spouse_keys, context=context)
        self._write_dob_vals(cr, uid, ids, vals, father_keys, context=context)
        self._write_dob_vals(cr, uid, ids, vals, mother_keys, context=context)
        
        return res

class hr_children(osv.Model):
    
    _inherit = 'hr.employee.children'
    
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
        
        res = {'value': {'dob': False}}
        if d and m and y:
            dob = pcc.gregorian_from_fixed(
                        pcc.fixed_from_ethiopic(
                                pcc.ethiopic_date(int(y), int(m), int(d))))
            res['value']['dob'] = date(year=dob[0], month=dob[1], day=dob[2]).strftime(OE_DFORMAT)
        return res
    
    def create(self, cr, uid, vals, context=None):
        
        # Only on creation: if Ethiopian birthday but not European, convert Ethio -> European.
        # Otherwise, if there's a European birthday but not Ethiopian, convert European -> Ethio.
        #
        if vals.get('etcal_dob_year', False) and vals.get('etcal_dob_month', False) and vals.get('etcal_dob_day', False) and not vals.get('dob', False):
            dob = pcc.gregorian_from_fixed(
                        pcc.fixed_from_ethiopic(
                                pcc.ethiopic_date(int(vals['etcal_dob_year']), int(vals['etcal_dob_month']),
                                                  int(vals['etcal_dob_day']))))
            vals['dob'] = date(year=dob[0], month=dob[1], day=dob[2]).strftime(OE_DFORMAT)
        elif vals.get('dob', False) and not vals.get('etcal_dob_year'):
            dBirth = datetime.strptime(vals['dob'], OE_DFORMAT).date()
            et_dob = pcc.ethiopic_from_fixed(
                            pcc.fixed_from_gregorian(
                                    pcc.gregorian_date(dBirth.year, dBirth.month, dBirth.day)))
            et_vals = {
                'etcal_dob_year': str(et_dob[0]),
                'etcal_dob_month': str(et_dob[1]),
                'etcal_dob_day': str(et_dob[2]),
            }
            vals.update(et_vals)
        
        return super(hr_children, self).create(cr, uid, vals, context=context)
    
    def write(self, cr, uid, ids, vals, context=None):
        
        res =  super(hr_children, self).write(cr, uid, ids, vals, context=context)
        
        y = vals.get('etcal_dob_year', False)
        m = vals.get('etcal_dob_month', False)
        d = vals.get('etcal_dob_day', False)
        
        if y or m or d:
            for i in ids:
                data = {'dob': ''}
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
                data['dob'] = date(year=dob[0], month=dob[1], day=dob[2]).strftime(OE_DFORMAT)
                
                super(hr_children, self).write(cr, uid, i, data, context=context)
        
        return res
