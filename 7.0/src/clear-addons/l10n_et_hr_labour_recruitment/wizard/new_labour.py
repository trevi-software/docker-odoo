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

from datetime import datetime, date, timedelta

from openerp.addons.decimal_precision import decimal_precision as dp
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools.translate import _

from ethiopic_calendar.ethiopic_calendar import ET_MONTHS_SELECTION, ET_DAYOFMONTH_SELECTION
from ethiopic_calendar.pycalcal import pycalcal as pcc

OE_DATEFORMAT = OE_DFORMAT

class benefits(osv.TransientModel):
    
    _name = 'hr.recruitment.labour.benefits'
    _description = 'New Hire Benefits'
    
    _columns = {
        'new_labour_id': fields.many2one('hr.recruitment.labour.new', 'Wizard'),
        'benefit_id': fields.many2one('hr.benefit', 'Benefit', required=True),
        'effective_date': fields.date('Effective Date', required=True),
        'end_date': fields.date('Effective Date'),
        'adv_override': fields.boolean('Override Advantage'),
        'prm_override': fields.boolean('Override Premium'),
        'adv_amount': fields.float('Advantage Amount', digits_compute=dp.get_precision('Account')),
        'prm_amount': fields.float('Premium Amount', digits_compute=dp.get_precision('Account')),
        'prm_total': fields.float('Premium Total', digits_compute=dp.get_precision('Account')),
    }
    
    _defaults = {
        'effective_date': datetime.now().strftime(OE_DFORMAT),
    }

class new_labour(osv.TransientModel):
    
    _name = 'hr.recruitment.labour.new'
    _description = 'Daily Labour Recruitment Form'
    
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
        'employee_ids': fields.many2many('hr.employee', 'new_employee_rel', 'employee_id', 'wiz_id',
                                         string="Employees"),
        'new_benefit_ids': fields.one2many('hr.recruitment.labour.benefits', 'new_labour_id',
                                           'New Benefits'),
        'state': fields.selection([('personal', 'Personal'),
                                   ('contract', 'Contract'),
                                   ('benefits', 'Benefits'),
                                   ('review', 'Review')], "State",
                                  readonly=True),
        'company_id': fields.many2one('res.company', 'Company', required=True),

        # Personal Details
        #
        'name': fields.char('Name', size=128),
        'ethiopic_name': fields.char('Ethiopic Name', size=512),
        'birth_date': fields.date('Birth Date'),
        'use_ethiopic_dob': fields.boolean('Use Ethiopic Birthday'),
        'etcal_dob_month': fields.selection(ET_MONTHS_SELECTION, 'Month'),
        'etcal_dob_day': fields.selection(ET_DAYOFMONTH_SELECTION, 'Day'),
        'etcal_dob_year': fields.selection(_get_year, 'Year'),
        'gender': fields.selection([('f', 'Female'),('m', 'Male')], 'Gender'),
        'id_no': fields.char('Official ID', size=32),
        'house_no': fields.char('House No.', size=8),
        'kebele': fields.char('Kebele', size=8),
        'woreda': fields.char('Subcity/Woreda', size=32),
        'city': fields.char('City', size=32),
        'state_id': fields.many2one('res.country.state', 'State'),
        'country_id': fields.many2one('res.country', 'Country'),
        'telephone': fields.char('Telephone', size=19),
        'mobile': fields.char('Mobile', size=19),
        'education': fields.selection((
                                       ('none', 'No Education'),
                                       ('primary', 'Primary School'),
                                       ('secondary', 'Secondary School'),
                                       ('diploma', 'Diploma'),
                                       ('degree1', 'First Degree'),
                                       ('masters', 'Masters Degree'),
                                       ('phd', 'PhD'),
                                      ), 'Education'),
        
        # Contract Details
        #
        'job_id': fields.many2one('hr.job', 'Applied Job'),
        'department_id': fields.many2one('hr.department', 'Department'),
        'struct_id': fields.many2one('hr.payroll.structure', 'Salary Structure'),
        'pps_id': fields.many2one('hr.payroll.period.schedule', 'Payroll Period Schedule'),
        'policy_group_id': fields.many2one('hr.policy.group', 'Policy Group'),
        'wage': fields.float('Wage', digits=(16,2), help="Basic Salary of the employee"),
        'schedule_template_id': fields.many2one('hr.schedule.template','Working Schedule Template'),
        'date_start': fields.date('Start Date'),
        'date_end': fields.date('End Date'),
        'trial_date_start': fields.date('Trial Start Date'),
        'trial_date_end': fields.date('Trial End Date'),
    }
    
    def _get_country(self, cr, uid, context=None):
        
        company_id = self.pool.get('res.company')._company_default_get(cr, uid, 'hr.applicant', context=context)
        data = self.pool.get('res.company').read(cr, uid, company_id, context=context)
        return data.get('country_id', False) and data['country_id'][0] or False
    
    _defaults = {
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'hr.employee', context=c),
        'country_id': _get_country,
        'use_ethiopic_dob': True,
        'education': 'none',
        'state': 'personal',
        'date_start': datetime.now().strftime(OE_DFORMAT),
        'wage': lambda s,cr,uid,ctx: s.pool.get('hr.contract')._get_wage(cr, uid, ctx),
        'struct_id': lambda s,cr,uid,ctx: s.pool.get('hr.contract')._get_struct(cr, uid, ctx),
        'trial_date_start': lambda s,cr,uid,ctx: s.pool.get('hr.contract')._get_trial_date_start(cr, uid, ctx),
        'trial_date_end': lambda s,cr,uid,ctx: s.pool.get('hr.contract')._get_trial_date_end(cr, uid, ctx),
        'schedule_template_id': lambda s,cr,uid,ctx: s.pool.get('hr.contract')._get_sched_template(cr, uid, ctx),
        'pps_id': lambda s,cr,uid,ctx: s.pool.get('hr.contract')._get_pay_sched(cr, uid, ctx),
        'policy_group_id': lambda s,cr,uid,ctx: s.pool.get('hr.contract')._get_policy_group(cr, uid, ctx),
    }
    
    def onchange_company(self, cr, uid, ids, company_id, context=None):
        
        res = {'domain': {
                    'job_id': [('company_id', '=', company_id)],
                    'department_id': [('company_id', '=', company_id)],
               }
        }
        return res
    
    def onchange_job(self, cr, uid, ids, job_id, context=None):
        
        c_obj = self.pool.get('hr.contract')
        res = {'value': {
                    'department_id': False,
                    'wage': False,
                    'struct_id': False,
                    'policy_group_id': False,
               }
        }
        if job_id:
            job_obj = self.pool.get('hr.job')
            res['value']['department_id'] = job_obj.browse(cr, uid, job_id, context=context).department_id.id
            res['value']['wage'] = c_obj._get_wage(cr, uid, context=context, job_id=job_id)
            res['value']['struct_id'] = c_obj._get_struct(cr, uid, context=context)
            res['value']['policy_group_id'] = c_obj._get_policy_group(cr, uid, context=context)
        return res
    
    def onchange_date(self, cr, uid, ids, date_start, context=None):
        
        res = { 'value': {'trial_date_start': False, 'trial_date_end': False} }
        if date_start:
            res['value']['trial_date_start'] = date_start
            trial_res = self.onchange_trial(cr, uid, ids, date_start, context=context)
            res['value']['trial_date_end'] = trial_res['value']['trial_date_end']
        return res
    
    def onchange_trial(self, cr, uid, ids, trial_date_start, context=None):
        
        c_obj = self.pool.get('hr.contract')
        dStart = datetime.strptime(trial_date_start, OE_DFORMAT)
        str_end = c_obj._get_trial_date_end_from_start(cr, uid, dStart, context=context)
        return { 'value': {'trial_date_end': str_end} }
    
    def onchange_etdob(self, cr, uid, ids, y, m, d, context=None):
        
        res = {'value': {'birth_date': False}}
        if d and m and y:
            dob = pcc.gregorian_from_fixed(
                        pcc.fixed_from_ethiopic(
                                pcc.ethiopic_date(int(y), int(m), int(d))))
            res['value']['birth_date'] = date(year=dob[0], month=dob[1], day=dob[2]).strftime(OE_DATEFORMAT)
        return res

    def onchange_country(self, cr, uid, ids, country_id, context=None):
        
        res = {'domain': {'state_id': False}}
        if country_id:
            res['domain']['state_id'] = [('country_id', '=', country_id)]
        
        return res
    
    def create_applicant(self, cr, uid, ids, context=None):
        
        if context == None:
            context = {}
        
        appl_obj = self.pool.get('hr.applicant')
        data = self.read(cr, uid, ids[0], context=context)
        if not data.get('name', False) or not data.get('birth_date', False) or not data.get('gender', False):
            raise osv.except_osv(_('Mandatory Fields Missing'), _('Make sure that at least the Name, Birth Date and Gender fields have been filled in.'))
        
        hno = data.get('house_no', False) and 'House No: ' + data['house_no'] or ''
        kebele = data.get('kebele', False) and 'Kebele: ' + data['kebele'] or ''
        woreda = data.get('woreda', False) and 'Subcity/Woreda: ' + data['woreda'] or ''
        partner_vals = {
            'name': data['name'],
            'phone': data['telephone'],
            'mobile': data['mobile'],
            'street': woreda + ' ' + kebele + ' ' + hno,
            'city': data['city'],
            'country_id': data['country_id'][0],
            'state_id': data.get('state_id', False) and data['state_id'][0] or False,
            'company_id': data['company_id'][0],
            'employee': True,
            'customer': False,
        }
        partner_id = self.pool.get('res.partner').create(cr, uid, partner_vals, context=context)
        applicant_vals = {
            'name': data['name'],
            'ethiopic_name': data['ethiopic_name'],
            'partner_id': partner_id,
            'partner_phone': data['telephone'],
            'partner_mobile': data['mobile'],
            'job_id': data['job_id'][0],
            'department_id': data['department_id'][0],
            'gender': data['gender'],
            'use_ethiopic_dob': data['use_ethiopic_dob'],
            'etcal_dob_year': data['use_ethiopic_dob'] and data['etcal_dob_year'] or False,
            'etcal_dob_month': data['use_ethiopic_dob'] and data['etcal_dob_month'] or False,
            'etcal_dob_day': data['use_ethiopic_dob'] and data['etcal_dob_day'] or False,
            'birth_date': data['birth_date'],
            'education': data['education'],
            'company_id': data['company_id'][0],
        }
        appl_id = appl_obj.create(cr, uid, applicant_vals, context=context)
        
        # Create employee
        res_appl = appl_obj.case_close_with_emp(cr, uid, [appl_id], context=context)
        
        # Create contract
        #
        c_vals = {
            'employee_id': res_appl['res_id'],
            'job_id': data['job_id'][0],
            'department_id': data['department_id'][0],
            'wage': data['wage'],
            'struct_id': data['struct_id'][0],
            'policy_group_id': data['policy_group_id'][0],
            'date_start': data['date_start'],
            'date_end': data['date_end'],
            'trial_date_start': data['trial_date_start'],
            'trial_date_end': data['trial_date_end'],
            'schedule_template_id': data['schedule_template_id'][0],
            'pps_id': data['pps_id'][0],
        }
        self.pool.get('hr.contract').create(cr, uid, c_vals, context=context)
        
        # Enroll in benefits
        #
        newb_obj = self.pool.get('hr.recruitment.labour.benefits')
        bpol_obj = self.pool.get('hr.benefit.policy')
        for newb in newb_obj.browse(cr, uid, data['new_benefit_ids'], context=context):
            newb_vals = {
                'employee_id': res_appl['res_id'],
                'benefit_id': newb.benefit_id.id,
                'benefit_code': newb.benefit_id.code,
                'start_date': newb.effective_date,
                'end_date': newb.end_date,
                'advantage_override': newb.adv_override,
                'premium_override': newb.prm_override,
                'advantage_amount': newb.adv_amount,
                'premium_amount': newb.prm_amount,
                'premium_total': newb.prm_total,
            }
            bpol_obj.create(cr, uid, newb_vals, context=context)

        # Add employee ID to list of hired employees
        if context.get('new_employee_ids', False):
            context['new_employee_ids'].append(res_appl['res_id'])
        else:
            context.update({'new_employee_ids': [res_appl['res_id']]})
        
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.recruitment.labour.new',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }
    
    def cancel_wizard(self, cr, uid, ids, context=None):
        
        if context == None:
            context = {}
        
        res_model, res_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'hr', 'open_view_employee_list_my')
        act_window_obj = self.pool.get('ir.actions.act_window')
        dict_act_window = act_window_obj.read(cr, uid, res_id, [])
        dict_act_window['view_mode'] = 'kanban,tree,form'
        dict_act_window['domain'] = [('id', 'in', context.get('new_employee_ids', False))]
        context.pop('new_employee_ids', False)
        return dict_act_window

    def state_contract(self, cr, uid, ids, context=None):
        
        self.write(cr, uid, ids, {'state': 'contract'}, context=context)
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.recruitment.labour.new',
            'res_id': ids[0],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context,
        }

    def state_benefits(self, cr, uid, ids, context=None):
        
        self.write(cr, uid, ids, {'state': 'benefits'}, context=context)
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.recruitment.labour.new',
            'res_id': ids[0],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context,
        }

    def state_review(self, cr, uid, ids, context=None):
        
        self.write(cr, uid, ids, {'state': 'review'}, context=context)
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.recruitment.labour.new',
            'res_id': ids[0],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context,
        }
