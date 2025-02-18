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

from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DATEFORMAT
from openerp.tools.translate import _

class hr_job(osv.Model):
    
    _name = 'hr.job'
    _inherit = 'hr.job'
    
    _columns = {
        'max_employees': fields.integer('Maximum Number of Employees'),
        'max_employees_fuzz': fields.integer('Expected Turnover',
                                             help="Recruitment module will allow you to \
                                                  create this number of additional applicants and \
                                                  contracts above the maximum value. Use this \
                                                  number as a buffer to have additional \
                                                  employees on hand to cover employee turnover."),
    }
    
    # Do not write negative values for no. of recruitment
    def write(self, cr, uid, ids, vals, context=None):
        
        value = vals.get('no_of_recruitment', False)
        if value and value < 0:
            vals['no_of_recruitment'] = 0
        
        return super(hr_job, self).write(cr, uid, ids, vals, context=context)

class hr_applicant(osv.Model):
    
    _name = 'hr.applicant'
    _inherit = 'hr.applicant'
    
    def create(self, cr, uid, vals, context=None):
        
        if vals.get('job_id', False):
            data = self.pool.get('hr.job').read(cr, uid, vals['job_id'],
                                                ['max_employees', 'no_of_employee', 'state',
                                                 'max_employees_fuzz'],
                                                context=context)
            if data.get('state', False):
                if data['state'] != 'recruit' and int(data['no_of_employee']) >= (int(data['max_employees']) + data['max_employees_fuzz']):
                    raise osv.except_osv(_('Job not open for recruitment!'),
                                         _('You may not register applicants for jobs that are not recruiting.'))
        
        return super(hr_applicant, self).create(cr, uid, vals, context=context)

    # Replicate this function here so that we can handle creation of employee
    # in multi-company setup by using the force_company context attribute.
    #
    def case_close_with_emp(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        hr_employee = self.pool.get('hr.employee')
        model_data = self.pool.get('ir.model.data')
        act_window = self.pool.get('ir.actions.act_window')
        emp_id = False
        for applicant in self.browse(cr, uid, ids, context=context):
            address_id = False
            if applicant.partner_id:
                address_id = self.pool.get('res.partner').address_get(cr,uid,[applicant.partner_id.id],['contact'])['contact']
            if applicant.job_id:
                applicant.job_id.write({'no_of_recruitment': applicant.job_id.no_of_recruitment - 1})
                
                # THE SOLE REASON FOR REPLICATING THIS METHOD
                #
                emp_vals = {'name': applicant.partner_name or applicant.name,
                     'job_id': applicant.job_id.id,
                     'address_home_id': address_id,
                     'department_id': applicant.department_id.id,
                }
                ctx_copy = context.copy()
                if applicant.company_id:
                    emp_vals.update({'company_id': applicant.company_id.id})
                    ctx_copy.update({'force_company': applicant.company_id.id})
                emp_id = hr_employee.create(cr, uid, emp_vals, context=ctx_copy)
                
                self.write(cr, uid, [applicant.id], {'emp_id': emp_id}, context=context)
                self.case_close(cr, uid, [applicant.id], context)
            else:
                raise osv.except_osv(_('Warning!'), _('You must define Applied Job for this applicant.'))

        action_model, action_id = model_data.get_object_reference(cr, uid, 'hr', 'open_view_employee_list')
        dict_act_window = act_window.read(cr, uid, action_id, [])
        if emp_id:
            dict_act_window['res_id'] = emp_id
        dict_act_window['view_mode'] = 'form,tree'
        return dict_act_window

class hr_contract(osv.Model):
    
    _name = 'hr.contract'
    _inherit = 'hr.contract'
    
    def _get_job_from_applicant(self, cr, uid, context=None):
        """If the applicant went through recruitment get the job id from there."""
        
        res = False
        if context != None:
            ee_ids = context.get('search_default_employee_id', False)
            if ee_ids and len(ee_ids) > 0:
                # If this is the first contract try to obtain job position from application
                if len(self.search(cr, uid, [('employee_id','in',ee_ids)], context=context)) > 0:
                    return res
                applicant_obj = self.pool.get('hr.applicant')
                applicant_ids = applicant_obj.search(cr, uid, [('emp_id','=',ee_ids[0])], context=context)
                if len(applicant_ids) > 0:
                    data = applicant_obj.read(cr, uid, applicant_ids[0], ['job_id'], context=context)
                    res = data['job_id'][0]
        
        return res
    
    _defaults = {
        'job_id': _get_job_from_applicant,
    }
    
    def create(self, cr, uid, vals, context=None):
        
        # If the contract is for an employee with a pre-existing contract for
        # the same job, then bypass checks.
        employee_id = vals.get('employee_id', False)
        if employee_id:
            contract_ids = self.search(cr, uid, [
                                                 ('employee_id', '=', employee_id),
                                                 ('state', 'not in', ['draft', 'done']),
                                                ],
                                       context=context)
            for contract in self.browse(cr, uid, contract_ids, context=context):
                if vals.get('job_id', False) == contract.job_id.id:
                    return super(hr_contract, self).create(cr, uid, vals, context=context)
        
        # 1. Verify job is in recruitment
        if vals.get('job_id', False):
            job = self.pool.get('hr.job').browse(cr, uid, vals['job_id'], context=context)
            if job.state != 'recruit' or (job.max_employees and job.no_of_employee >= job.max_employees + job.max_employees_fuzz):
                raise osv.except_osv(_('The Job "%s" is not in recruitment!') %(job.name),
                                     _('You may not create contracts for jobs that are not in recruitment state.'))
        
        # 2. Verify that the number of open contracts < total expected employees
        if vals.get('job_id', False):
            contract_ids = self.search(cr, uid, [
                                                 ('job_id','=',vals['job_id']),
                                                 ('state','not in',['done', 'pending_done']),
                                                ],
                                       context=context)
            
            job = self.pool.get('hr.job').browse(cr, uid, vals['job_id'], context=context)
            if job.max_employees and len(contract_ids) >= max(job.expected_employees, job.max_employees + job.max_employees_fuzz):
                raise osv.except_osv(_('Maximum Number of Employees Exceeded!'),
                                     _('The maximum number of employees for "%s" has been exceeded.') %(job.name))
        
        return super(hr_contract, self).create(cr, uid, vals, context=context)

class hr_recruitment_request(osv.Model):
    
    _name = 'hr.recruitment.request'
    _description = 'Request for recruitment of additional personnel'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    
    _columns = {
        'name': fields.char('Description', size=64),
        'user_id': fields.many2one('res.users', 'Requesting User', required=True),
        'department_id': fields.many2one('hr.department', 'Department'),
        'job_id': fields.many2one('hr.job', 'Job', required=True),
        'number': fields.integer('Number to Recruit'),
        'current_number': fields.related('job_id', 'no_of_employee', type='integer', string="Current Number of Employees", readonly=True),
        'max_number': fields.related('job_id', 'max_employees', type='integer', string="Maximum Number of Employees", readonly=True),
        'reason': fields.text('Reason for Request'),
        'state': fields.selection([('draft', 'Draft'),
                                   ('confirm', 'Confirmed'),
                                   ('exception', 'Exception'),
                                   ('recruitment', 'In Recruitment'),
                                   ('decline', 'Declined'),
                                   ('done', 'Done'),
                                   ('cancel', 'Cancelled'),
                                  ],
                                  'State', readonly=True),
    }
    
    _order = 'department_id, job_id'
    
    _defaults = {
        'number': 1,
        'user_id': lambda self, cr, uid, context=None: uid,
    }
    
    _track = {
        'state': {
            'hr_labour_recruitment.mt_alert_request_confirmed': lambda self, cr,uid, obj, ctx=None: obj['state'] == 'confirm',
            'hr_labour_recruitment.mt_alert_request_exception': lambda self, cr,uid, obj, ctx=None: obj['state'] == 'exception',
            'hr_labour_recruitment.mt_alert_request_approved': lambda self, cr,uid, obj, ctx=None: obj['state'] == 'recruitment',
            'hr_labour_recruitment.mt_alert_request_declined': lambda self, cr,uid, obj, ctx=None: obj['state'] == 'decline',
        },
    }
    
    def onchange_job(self, cr, uid, ids, job_id, context=None):
        
        res = {'value': {'deparment_id': False, 'name': False}}
        if job_id:
            data = self.pool.get('hr.job').read(cr, uid, job_id, ['name', 'department_id'], context=context)
            if data.get('department_id', False):
                res['value']['department_id'] = data['department_id'][0]
            res['value']['name'] = 'Personnel Request: ' + str(data['name'])
        
        return res
    
    def _needaction_domain_get(self, cr, uid, context=None):
        
        users_obj = self.pool.get('res.users')
        
        domain = []
        has_prev_domain = False
        if users_obj.has_group(cr, uid, 'base.group_hr_manager'):
            domain = [('state','=','recruitment')]
            has_prev_domain = True
        if users_obj.has_group(cr, uid, 'hr_security.group_hr_director'):
            if has_prev_domain:
                domain = ['|'] + domain
            domain = domain + [('state','in',['confirm', 'exception'])]
        
        if len(domain) == 0:
            return False
        
        return domain
    
    def condition_exception(self, cr, uid, ids, context=None):
        
        for req in self.browse(cr, uid, ids, context=context):
            if req.number + req.job_id.expected_employees > req.job_id.max_employees:
                return True
        
        return False
    
    def _state(self, cr, uid, ids, state, context=None):
        
        job_obj = self.pool.get('hr.job')
        
        for req in self.browse(cr, uid, ids, context=context):
            
            if state == 'recruitment':
                job_obj.write(cr, uid, req.job_id.id, {'no_of_recruitment': req.number}, context=context)
                job_obj.job_recruitement(cr, uid, [req.job_id.id])
            elif state in ['done', 'cancel']:
                job_obj.job_open(cr, uid, [req.job_id.id])
            
            self.write(cr, uid, req.id, {'state': state}, context=context)
        
        return True
    
    def _state_subscribe_users(self, cr, uid, ids, state, context=None):
        
        imd_obj = self.pool.get('ir.model.data')
        model, group1_id = imd_obj.get_object_reference(cr, uid, 'base', 'group_hr_manager')
        model, group2_id = imd_obj.get_object_reference(cr, uid, 'hr_security', 'group_hr_director')
        data = self.pool.get('res.groups').read(cr, uid, [group1_id, group2_id], ['users'], context=context)
        user_ids = list(set(data[0]['users'] + data[1]['users']))
        self.message_subscribe_users(cr, uid, ids, user_ids=user_ids, context=context)
        
        return self._state(cr, uid, ids, state, context=context)
    
    def state_confirm(self, cr, uid, ids, context=None):
        
        return self._state_subscribe_users(cr, uid, ids, 'confirm', context=context)
    
    def state_exception(self, cr, uid, ids, context=None):
        
        return self._state_subscribe_users(cr, uid, ids, 'exception', context=context)
    
    def state_recruitment(self, cr, uid, ids, context=None):
        
        return self._state_subscribe_users(cr, uid, ids, 'recruitment', context=context)
    
    def state_done(self, cr, uid, ids, context=None):
        
        return self._state(cr, uid, ids, 'done', context=context)
    
    def state_cancel(self, cr, uid, ids, context=None):
        
        return self._state(cr, uid, ids, 'cancel', context=context)
