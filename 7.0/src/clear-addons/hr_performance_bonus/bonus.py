#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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

from openerp import netsvc
from openerp.addons.decimal_precision import decimal_precision as dp
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.translate import _

ITYPE_SELECTION = [
    ('fixed', 'Fixed Points'),
    ('daily', 'Daily Points'),
    ('fixed_amt', 'Fixed Amount'),
]

class bonus_demerit(osv.Model):
    
    _name = 'hr.bonus.sheet.demerit'
    _description = 'Bonus Sheet Demerit Records'
    
    _columns = {
        'bonus_sheet_id': fields.many2one('hr.bonus.sheet', 'Bonus Sheet'),
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True),
        'percentage': fields.float('Subtract Percentage'),
    }
    
    def onchange_sheet(self, cr, uid, ids, sheet_id, context=None):
        
        sheet = self.pool.get('hr.bonus.sheet').browse(cr, uid, sheet_id, context=context)
        ee_ids = self.get_employees_by_department(cr, uid, sheet.department_id.id,
                                                  sheet.date_start, sheet.date_end,
                                                  context=context)
        ee_ids += self.get_other_employees(cr, uid, ids, sheet_id,
                                           context=context)
        res = {'domain': {'employee_id': [('id', 'in', ee_ids)]}}
        return res
    
    def get_employees_by_department(self, cr, uid, dept_id, start, end, context=None):
        
        c_obj = self.pool.get('hr.contract')
        
        # Get all employees associated with this department. This
        # includes current and past employees.
        #
        e_ids = []
        c_ids = c_obj.search(cr, uid,
                             ['|', ('job_id.department_id', '=', dept_id),
                                   ('end_job_id.department_id', '=', dept_id),
                              ('date_start', '<=', end),
                              '|', ('date_end', '=', False),
                                   ('date_end', '>=', start)],
                             context=context)
        
        datas = c_obj.read(cr, uid, c_ids, ['employee_id'], context=context)
        for d in datas:
            if d['employee_id'][0] not in e_ids:
                e_ids.append(d['employee_id'][0])
        
        return e_ids

    def get_other_employees(self, cr, uid, ids, sheet_id, context=None):

        # Get employees listed under supervisors and Managers
        #
        sheet = self.pool.get('hr.bonus.sheet').browse(cr, uid, sheet_id,
                                                       context=context)
        ee_ids = []
        for supervisor in sheet.supervisor_ids:
            ee_ids.append(supervisor.id)
        for manager in sheet.manager_ids:
            ee_ids.append(manager.id)

        return ee_ids


class hr_bonus_sheet(osv.Model):
    
    _name = 'hr.bonus.sheet'
    _description = 'Departmental Bonus Sheet'
    
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    
    def _calc(self, cr, uid, ids, field_name, arg, context=None):
        
        res = dict.fromkeys(ids, False)
        for sheet in self.browse(cr, uid, ids, context=context):
            
            res[sheet.id] = {'lines_total': 0, 'lines_avg': 0}

            # Fixed Amount Evaluations
            if sheet.incentive_type == 'fixed' and sheet.eval_fixed_id:
                res[sheet.id]['lines_total'] = sheet.eval_fixed_id.total
                res[sheet.id]['lines_avg'] = sheet.eval_fixed_id.avg
            # Daily bonus
            elif sheet.incentive_type == 'daily' and sheet.eval_daily_ids:
                for line in sheet.eval_daily_ids:
                    res[sheet.id]['lines_total'] += line.points
                res[sheet.id]['lines_avg'] = res[sheet.id]['lines_total'] / float(len(sheet.eval_daily_ids))
            
        return res
    
    def _ids_from_eval(self, cr, uid, ids, myobj, context=None):
        
        res = []
        for _eval in myobj.browse(cr, uid, ids, context=context):
            if _eval.sheet_id.id not in res: res.append(_eval.sheet_id.id)
        return res
        
    def _ids_from_fixed_eval(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (long, int)):
            ids = [ids]
        
        o = self.pool.get('hr.bonus.sheet')
        return o._ids_from_eval(cr, uid, ids, self.pool.get('hr.bonus.evaluation.fixed'),
                                   context)
    
    def _ids_from_daily_eval(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (long, int)):
            ids = [ids]
        
        o = self.pool.get('hr.bonus.sheet')
        return o._ids_from_eval(cr, uid, ids, self.pool.get('hr.bonus.evaluation.daily'),
                                   context)
    
    _columns = {
        'date_start': fields.date('From', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'date_end': fields.date('To', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'criteria_collection_id': fields.many2one('hr.bonus.criteria.collection',
                                                  'Criteria Selection', required=False),
        'incentive_type': fields.selection(ITYPE_SELECTION, 'Incentive Type', required=True,
                                           readonly=True, states={'draft': [('readonly', False)]}),
        'bonus_amount': fields.float('Bonus Amount', digits_compute=dp.get_precision('Payroll'), required=True, readonly=True,
                                     states={'draft': [('readonly', False)]}),
        'assistant_bonus_multiplier': fields.float('Assistants Multiplier', digits_compute=dp.get_precision('Payroll'), required=True, readonly=True,
                                                   states={'draft': [('readonly', False)]}),
        'supervisor_bonus_multiplier': fields.float('Supervisors Multiplier', digits_compute=dp.get_precision('Payroll'), required=True, readonly=True,
                                                    states={'draft': [('readonly', False)]}),
        'manager_bonus_multiplier': fields.float('Managers Multiplier', digits_compute=dp.get_precision('Payroll'), required=True, readonly=True,
                                                 states={'draft': [('readonly', False)]}),
        'supervisor_ids': fields.many2many('hr.employee', 'hr_bonus_sheet_supervisors_rel',
                                           'sheet_id', 'employee_id', 'Supervisors'),
        'manager_ids': fields.many2many('hr.employee', 'hr_bonus_sheet_managers_rel',
                                           'sheet_id', 'employee_id', 'Managers'),
        'department_id': fields.many2one('hr.department', 'Department', required=True, readonly=True,
                                         states={'draft': [('readonly', False)]}),
        'recorder_id': fields.many2one('hr.employee', 'Prepared By', readonly=True,
                                       states={'draft': [('readonly', False)]}),
        'state': fields.selection([('draft', 'Draft'),
                                   ('approve', 'Approved'),
                                   ('cancel', 'Cancelled'),
                                  ],
                                  'State', readonly=True),
        'eval_fixed_id': fields.many2one('hr.bonus.evaluation.fixed', 'Fixed Evaluation'),
        'eval_daily_ids': fields.one2many('hr.bonus.evaluation.daily', 'sheet_id', 'Daily Evaluations'),
        'lines_total': fields.function(_calc, type='float', method=True, multi='total', string='Total',
                                     store={'hr.bonus.sheet': (lambda s, c, u, ids, ctx=None: ids, ['eval_fixed_id'], 10),
                                            'hr.bonus.evaluation.fixed': (_ids_from_fixed_eval, ['sheet_id', 'line_ids', 'total', 'avg'], 10),
                                            'hr.bonus.evaluation.daily': (_ids_from_daily_eval, ['sheet_id', 'date', 'points'], 10)}),
        'lines_avg': fields.function(_calc, type='float', method=True, multi='total', string='Average',
                                     store={'hr.bonus.sheet': (lambda s, c, u, ids, ctx=None: ids, ['eval_fixed_id'], 10),
                                            'hr.bonus.evaluation.fixed': (_ids_from_fixed_eval, ['sheet_id', 'line_ids', 'total', 'avg'], 10),
                                            'hr.bonus.evaluation.daily': (_ids_from_daily_eval, ['sheet_id', 'date', 'points'], 10)}),
        'demerit_ids': fields.one2many('hr.bonus.sheet.demerit', 'bonus_sheet_id', 'Demerits'),
    }
    
    def _get_default_bonus_amount(self, cr, uid, context=None):
        
        icp = self.pool['ir.config_parameter']
        bns_amount = float(icp.get_param(cr, uid, 'hr.bonus.sheet.fixed_bonus_amount', default=0.00))
        return bns_amount
    
    def _get_default_asst_multiplier(self, cr, uid, context=None):
        
        icp = self.pool['ir.config_parameter']
        bns_amount = float(icp.get_param(cr, uid, 'hr.bonus.sheet.assistant_multiplier', default=1.0))
        return bns_amount
    
    def _get_default_supervisor_multiplier(self, cr, uid, context=None):
        
        icp = self.pool['ir.config_parameter']
        bns_amount = float(icp.get_param(cr, uid, 'hr.bonus.sheet.supervisor_multiplier', default=1.0))
        return bns_amount
    
    def _get_default_manager_multiplier(self, cr, uid, context=None):
        
        icp = self.pool['ir.config_parameter']
        bns_amount = float(icp.get_param(cr, uid, 'hr.bonus.sheet.manager_multiplier', default=1.0))
        return bns_amount
    
    _defaults = {
        'state': 'draft',
        'bonus_amount': _get_default_bonus_amount,
        'assistant_bonus_multiplier': _get_default_asst_multiplier,
        'supervisor_bonus_multiplier': _get_default_supervisor_multiplier,
        'manager_bonus_multiplier': _get_default_manager_multiplier,
    }
    
    _order = 'date_start desc,department_id'

    def _check_date(self, cr, uid, ids):
        for sheet in self.browse(cr, uid, ids):
            sheet_ids = self.search(cr, uid, [('date_start', '<=', sheet.date_end),
                                              ('date_end', '>=', sheet.date_start),
                                              ('department_id', '=', sheet.department_id.id),
                                              ('id', '<>', sheet.id)])
            if len(sheet_ids) > 0:
                return False
        return True
    
    _constraints = [
        (_check_date,
         _('You cannot have more than one bonus sheet in a department per period.'),
         ['date_start','date_end']),
    ] 
    
    _track = {
        'state': {
            'hr_performance_bonus.mt_alert_approved': lambda self, cr,uid, obj, ctx=None: obj['state'] == 'approve',
        },
    }

    def name_get(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (long, int)):
            ids = [ids]
        
        res = []
        datas = self.read(cr, uid, ids, ['date_start', 'date_end', 'department_id'],
                          context=context)
        for data in datas:
            name = data.get('department_id', False) and data['department_id'][1] or ''
            name += ' ' + data['date_start'] + ' - ' + data['date_end']
            res.append((data['id'], name))
        
        return res
    
    def onchange_incentive_type(self, cr, uid, ids, incentive_type, context=None):
        
        res = {'value': {'bonus_amount': 0.00}}
        icp = self.pool['ir.config_parameter']
        if incentive_type == 'fixed':
            res['value']['bonus_amount'] = self._get_default_bonus_amount(cr, uid, context=context)
        elif incentive_type == 'daily':
            res['value']['bonus_amount'] = float(icp.get_param(cr, uid, 'hr.bonus.sheet.daily_bonus_amount', default=0.00))
        elif incentive_type == 'fixed_amt':
            res['value']['bonus_amount'] = float(icp.get_param(cr, uid, 'hr.bonus.sheet.fixed_amt_bonus_amount', default=0.00))
        
        return res
    
    def _needaction_domain_get(self, cr, uid, context=None):
        
        domain = []
        if self.pool.get('res.users').has_group(cr, uid, 'hr_performance_bonus.group_hr_bonus'):
            domain = [('state','=','draft')]
        
        if len(domain) == 0:
            return False
        
        return domain
    
    def action_delete_lines(self, cr, uid, ids, context=None):
        
        line_obj = self.pool.get('hr.bonus.evaluation.fixed')
        line_ids = line_obj.search(cr, uid, [('sheet_id', 'in', ids)], context=context)
        if len(line_ids) > 0:
            line_obj.unlink(cr, uid, line_ids, context=context)
        daily_obj = self.pool.get('hr.bonus.evaluation.daily')
        line_ids = daily_obj.search(cr, uid, [('sheet_id', 'in', ids)], context=context)
        if len(line_ids) > 0:
            daily_obj.unlink(cr, uid, line_ids, context=context)
        return True

    def set_to_draft(self, cr, uid, ids, context=None):
        
        self.write(cr, uid, ids, {
            'state': 'draft',
        })
        wf_service = netsvc.LocalService("workflow")
        for i in ids:
            wf_service.trg_delete(uid, 'hr.bonus.sheet', i, cr)
            wf_service.trg_create(uid, 'hr.bonus.sheet', i, cr)
        return True
    
    def bonus_criteria_ok(self, cr, uid, ids, context=None):
        
        for bonus in self.browse(cr, uid, ids, context=context):
            if bonus.incentive_type == 'fixed':
                if not bonus.eval_fixed_id or not bonus.eval_fixed_id.line_ids or len(bonus.eval_fixed_id.line_ids) == 0:
                    return False
            elif bonus.incentive_type == 'daily':
                if not bonus.eval_daily_ids or len(bonus.eval_daily_ids) == 0:
                    return False
            elif bonus.incentive_type == 'fixed_amount':
                # Allow 0 bonus amount
                pass
        
        return True

class hr_criteria(osv.Model):
    
    _name = 'hr.bonus.criteria'
    _description = 'Bonus Criteria'
    
    _columns = {
        'name': fields.char('Name', size=128, required=True),
    }

class hr_criteria_collection(osv.Model):
    
    _name = 'hr.bonus.criteria.collection'
    _description = 'Collection of Criterias'
    
    _columns = {
        'name': fields.char('Name', size=128, required=True),
        'criteria_ids': fields.many2many('hr.bonus.criteria', 'hr_criteria_collection_rel', 'collection_id',
                                         'criteria_id', 'Criteria Lines'),
    }

class hr_bonus_evaluation_fixed(osv.Model):
    
    _name = 'hr.bonus.evaluation.fixed'
    _description = 'Fixed Bonus Evaluation'
    
    def _calculate(self, cr, uid, ids, field_name, arg, context=None):
        
        res = dict.fromkeys(ids)
        for evaluation in self.browse(cr, uid, ids, context=context):
            res[evaluation.id] = {'total': 0, 'avg': 0}
            for line in evaluation.line_ids:
                res[evaluation.id]['total'] += line.points
                # Use 'avg' key to hold number of lines, then use it to average the sum of 'total'
                res[evaluation.id]['avg'] += 1
            
            if res[evaluation.id]['avg'] > 0:
                res[evaluation.id]['avg'] = res[evaluation.id]['total'] / res[evaluation.id]['avg']
        
        return res
    
    def _ids_from_line(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (long, int)):
            ids = [ids]
        
        res = []
        for line in self.pool.get('hr.bonus.evaluation.fixed.line').browse(cr, uid, ids, context=context):
            if line.evaluation_id.id not in res: res.append(line.evaluation_id.id)
        
        return res
    
    _columns = {
        'sheet_id': fields.many2one('hr.bonus.sheet', 'Bonus Sheet'),
        'line_ids': fields.one2many('hr.bonus.evaluation.fixed.line', 'evaluation_id', 'Evaluations'),
        'total': fields.function(_calculate, type='float', method=True, string='Total',
                                 multi='total', store=True),
        'avg': fields.function(_calculate, type='float', method=True, string='Average',
                               multi='total', store={
                                                'hr.bonus.evaluation.fixed.line': (_ids_from_line, ['evaluation_id', 'points'], 10),
                                              }),
    }

    def name_get(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (long, int)):
            ids = [ids]
        
        res = []
        for evaluation in self.browse(cr, uid, ids, context=context):
            name = ''
            if evaluation.sheet_id.criteria_collection_id:
                name += evaluation.sheet_id.criteria_collection_id.name
                name += ' '
            name += '(Total: %.2f, Avg: %.2f)' % (evaluation.total, evaluation.avg)
            res.append((evaluation.id, name))
        
        return res

class hr_bonus_evaluation_fixed_line(osv.Model):
    
    _name = 'hr.bonus.evaluation.fixed.line'
    _description = 'Fixed Bonus Evaluation Line'
    
    _columns = {
        'evaluation_id': fields.many2one('hr.bonus.evaluation.fixed', 'Evaluation Line'),
        'criteria_id': fields.many2one('hr.bonus.criteria', 'Criteria', readonly=True),
        'points': fields.float('Points', digits_compute=dp.get_precision('Payroll'), required=True),
    }
    
    _defaults = {
        'points': 0.0,
    }

class hr_bonus_evaluation_daily(osv.Model):
    
    _name = 'hr.bonus.evaluation.daily'
    _description = 'Fixed Bonus Evaluation for Grading'
    
    def _calculate(self, cr, uid, ids, field_name, arg, context=None):
        
        res = dict.fromkeys(ids)
        for evaluation in self.browse(cr, uid, ids, context=context):
            res[evaluation.id] = {'total': 0, 'avg': 0}
            for line in evaluation.line_ids:
                res[evaluation.id]['total'] += line.points
                # Use 'avg' key to hold number of lines, then use it to average the sum of 'total'
                res[evaluation.id]['avg'] += 1
            
            if res[evaluation.id]['avg'] > 0:
                res[evaluation.id]['avg'] = res[evaluation.id]['total'] / res[evaluation.id]['avg']
        
        return res
    
    def _ids_from_line(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (long, int)):
            ids = [ids]
        
        res = []
        for line in self.pool.get('hr.bonus.evaluation.daily.line').browse(cr, uid, ids, context=context):
            if line.evaluation_id.id not in res: res.append(line.evaluation_id.id)
        
        return res
    
    _columns = {
        'sheet_id': fields.many2one('hr.bonus.sheet', 'Bonus Sheet'),
        'date': fields.date('Date', required=True),
        'points': fields.float('Bonus', digits_compute=dp.get_precision('Payroll'), required=True),
    }

    def name_get(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (long, int)):
            ids = [ids]
        
        res = []
        for evaluation in self.browse(cr, uid, ids, context=context):
            name = ''
            if evaluation.sheet_id.department_id:
                name += evaluation.sheet_id.department_id.complete_name
                name += ' '
            name += evaluation.sheet_id.date_end
            res.append((evaluation.id, name))
        
        return res
