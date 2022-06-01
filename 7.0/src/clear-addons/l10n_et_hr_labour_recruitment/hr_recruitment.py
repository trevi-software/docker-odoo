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

from openerp import netsvc
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DATEFORMAT
from openerp.tools.translate import _

from ethiopic_calendar.ethiopic_calendar import ET_MONTHS_SELECTION, ET_DAYOFMONTH_SELECTION
from ethiopic_calendar.pycalcal import pycalcal as pcc

class hr_applicant(osv.Model):
    
    _name = 'hr.applicant'
    _inherit = 'hr.applicant'
    
    def _get_year(self, cr, uid, context=None):
        
        res = []
        
        # Assuming employees are at least 16 years old
        year = datetime.now().year
        year -= 16
        
        # Convert to Ethiopic calendar
        pccDate = pcc.ethiopic_from_fixed(
                    pcc.fixed_from_gregorian(
                            pcc.gregorian_date(year, 1, 1)))
        year = pccDate[0]
        
        i = year
        while i > (year - 59):
            res.append((str(i), str(i)))
            i -= 1
        
        return res
    
    _columns = {
        'ethiopic_name': fields.char('Ethiopic Name', size=512),
        'gender': fields.selection([('f', 'Female'),('m', 'Male')], 'Gender'),
        'birth_date': fields.date('Birth Date'),
        'use_ethiopic_dob': fields.boolean('Use Ethiopic Birthday'),
        'etcal_dob_month': fields.selection(ET_MONTHS_SELECTION, 'Month'),
        'etcal_dob_day': fields.selection(ET_DAYOFMONTH_SELECTION, 'Day'),
        'etcal_dob_year': fields.selection(_get_year, 'Year'),
        'education': fields.selection((
                                       ('none', 'No Education'),
                                       ('primary', 'Primary School'),
                                       ('secondary', 'Secondary School'),
                                       ('diploma', 'Diploma'),
                                       ('degree1', 'First Degree'),
                                       ('masters', 'Masters Degree'),
                                       ('phd', 'PhD'),
                                      ), 'Education'),
    }
    
    def onchange_etdob(self, cr, uid, ids, y, m, d, context=None):
        
        res = {'value': {'birth_date': False}}
        if d and m and y:
            dob = pcc.gregorian_from_fixed(
                        pcc.fixed_from_ethiopic(
                                pcc.ethiopic_date(int(y), int(m), int(d))))
            res['value']['birth_date'] = date(year=dob[0], month=dob[1], day=dob[2]).strftime(OE_DATEFORMAT)
        return res
    
    def case_close_with_emp(self, cr, uid, ids, context=None):
        
        ee_obj = self.pool.get('hr.employee')
        
        res = super(hr_applicant, self).case_close_with_emp(cr, uid, ids, context=context)
        
        for applicant in self.browse(cr, uid, ids, context=context):
            vals = {
                'ethiopic_name': applicant.ethiopic_name,
                'gender': applicant.gender == 'f' and 'female' or 'male',
                'use_ethiopic_dob': applicant.use_ethiopic_dob,
                'etcal_dob_year': applicant.etcal_dob_year,
                'etcal_dob_month': applicant.etcal_dob_month,
                'etcal_dob_day': applicant.etcal_dob_day,
                'birthday': applicant.birth_date,
                'education': applicant.education,
            }
            ee_obj.write(cr, uid, [applicant.emp_id.id], vals, context=context)
        
        return res

class hr_contract(osv.Model):
    
    _inherit = 'hr.contract'
    
    # This function is called by the workflow activity functions of "trial" and "open" state
    # Overload it so that any benefit policies are also activated.
    #
    def state_common(self, cr, uid, ids, context=None):
        
        res = super(hr_contract, self).state_common(cr, uid, ids, context=context)
        
        wkf = netsvc.LocalService('workflow')
        for contract in self.browse(cr, uid, ids, context=context):
            for policy in contract.employee_id.benefit_policy_ids:
                wkf.trg_validate(uid, 'hr.benefit.policy', policy.id, 'signal_open', cr)
        
        return res

class hr_employee(osv.Model):
    
    _inherit = 'hr.employee'
    
    def state_inactive(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        res = super(hr_employee, self).state_inactive(cr, uid, ids, context=context)
        
        wkf = netsvc.LocalService('workflow')
        bpol_obj = self.pool.get('hr.benefit.policy')
        for ee in self.browse(cr, uid, ids, context=context):
            
            inactive_date = False
            for term in ee.inactive_ids:
                if not inactive_date or term.name > inactive_date:
                    inactive_name = term.name
            
            for policy in ee.benefit_policy_ids:
                if policy.state not in ['done']:
                    bpol_obj.write(cr, uid, policy.id, {'end_date': inactive_name}, context=context)
                    wkf.trg_validate(uid, 'hr.benefit.policy', policy.id, 'signal_done', cr)
        
        return res
