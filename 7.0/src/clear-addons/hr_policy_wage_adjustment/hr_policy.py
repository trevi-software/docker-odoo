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

import math
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

import openerp.addons.decimal_precision as dp

from openerp import netsvc
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DATEFORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DATETIMEFORMAT
from openerp.tools.float_utils import float_compare
from openerp.tools.translate import _

class hr_adj_job(osv.Model):
    
    _name = 'hr.policy.line.wageadj.job'
    _description = 'Wage Adjustment Policy Line Job Run'
    
    _columns = {
        'name': fields.date('Date', required=True, readonly=True),
        'exec': fields.datetime('Execution Date/Time', required=True, readonly=True),
        'policy_line_id': fields.many2one('hr.policy.line.wageadj', 'Adjustment Policy Line',
                                          required=True, readonly=True),
        'run_ids': fields.many2many('hr.contract.wage.increment.run', 'hr_policy_wageadj_job_run_rel',
                                    'job_id', 'run_id', 'Batch Adjustments',
                                    readonly=True),
        'no_runs': fields.boolean('No Wage Adjustments Created'),
    }

class wage_increment_run(osv.Model):
    
    _inherit = 'hr.contract.wage.increment.run'
    
    _columns = {
        'wageadj_policy_line_id': fields.many2one('hr.policy.line.wageadj', 'Adjustment Policy Line'),
        'wageadj_policy_job_id': fields.many2one('hr.policy.line.wageadj.job', 'Job'),
    }

class hr_policy(osv.Model):
    
    _name = 'hr.policy.wageadj'
    _description = 'Wage Adjustment Policy'
    
    _columns = {
        'name': fields.char('Name', size=128, required=True),
        'date': fields.date('Effective Date', required=True),
        'line_ids': fields.one2many('hr.policy.line.wageadj', 'policy_id', 'Policy Lines'),
    }
    
    # Return records with latest date first
    _order = 'date desc'
    
    def get_latest_policy(self, cr, uid, policy_group, dToday, context=None):
        '''Return an adjustment policy with an effective date before dToday but greater than all the others'''
        
        if not policy_group or not policy_group.wageadj_policy_ids or not dToday:
            return None
        
        res = None
        for policy in policy_group.wageadj_policy_ids:
            dPolicy = datetime.strptime(policy.date, OE_DATEFORMAT).date()
            if dPolicy <= dToday:
                if res == None:
                    res = policy
                elif dPolicy > datetime.strptime(res.date, OE_DATEFORMAT).date():
                    res = policy
        
        return res
    
    def _calculate_and_adjust(self, cr, uid, line, contract, job_id, run_id, date_str,
                              dToday=None, context=None):
        

        def _calculate(initial, adj_type, adj_amount):
            
            result = 0
            if adj_type == 'fixed':
                result = initial + adj_amount
            elif adj_type == 'percent':
                result = initial + (initial * adj_amount / 100.0)
            elif adj_type == 'final':
                result = adj_amount
            else:
                # manual
                result = initial
            return result
        
        adj_obj = self.pool.get('hr.contract.wage.increment')
        month_last_day = {
            1: 31,
            2: 28,
            3: 31,
            4: 30,
            5: 31,
            6: 30,
            7: 31,
            8: 31,
            9: 30,
            10: 31,
            11: 30,
            12: 31,
        }
        
        if line.type != 'calendar':
            return
        
        delta = month_last_day[dToday.month] - 1
        dEndMonth = dToday + relativedelta(days=delta)
        srvc_months, dHire = self.pool.get('hr.employee').get_months_service_to_date(cr, uid,
                                                                                     [contract.employee_id.id],
                                                                                     dToday=dEndMonth,
                                                                                     context=context)[contract.employee_id.id]
        if line.max_milestone != 0 and math.ceil(srvc_months) > line.max_milestone:
            return
        
        if dToday == None:
            dToday = date.today()
        
        employed_days = 0
        if line.minimum_employed_days:
            dCount = dHire
            while dCount < dToday:
                employed_days += 1
                dCount += timedelta(days= +1)
            if line.minimum_employed_days > employed_days:
                return

        # Get minimum milestone
        min_tpl = False
        for tpl in line.template_ids:
            if not min_tpl or tpl.milestone < min_tpl.milestone:
                min_tpl = tpl
        if min_tpl and float_compare(srvc_months, min_tpl.milestone, precision_digits=2) in [-1, 0]:
            return
        
        # Get relevant milestone and the one immediately after it
        milestone_amount = 0
        next_adj_template = False
        adj_template = False
        for template in line.template_ids:
            _cmp = float_compare(template.milestone, srvc_months, precision_digits=2)
            if not adj_template and _cmp in [-1, 0]:
                adj_template = template
            elif adj_template and (template.milestone > adj_template.milestone and template.milestone <= math.ceil(float(srvc_months))):
                adj_template = template
        for template in line.template_ids:
            if not next_adj_template or (template.milestone < next_adj_template.milestone and template.milestone > adj_template.milestone):
                next_adj_template = template
        if next_adj_template.milestone <= adj_template.milestone:
            next_adj_template = False
        if adj_template and adj_template.milestone <= math.ceil(float(srvc_months)):
            milestone_amount = _calculate(contract.wage, adj_template.type, adj_template.amount)
        
        if line.frequency_on_hire_date:
            freq_week_day = dHire.weekday()
            freq_month_day = dHire.day
            freq_annual_month = dHire.month
            freq_annual_day = dHire.day
        else:
            freq_week_day = line.frequency_week_day
            freq_month_day = line.frequency_month_day
            freq_annual_month = line.frequency_annual_month
            freq_annual_day = line.frequency_annual_day
        
        if line.calculation_frequency == 'weekly':
            if dToday.weekday() != freq_week_day:
                return
            freq_amount = milestone_amount / (next_adj_template and float(next_adj_template.milestone - adj_template.milestone) * 4.0 or 52.0)
        elif line.calculation_frequency == 'monthly':
            # When deciding to skip an employee account for actual month lengths. If
            # the frequency date is 31 and this month only has 30 days, go ahead and
            # do it on the last day of the month (i.e. the 30th). For
            # February, on non-leap years execute accruals for the 29th on the 28th.
            #
            if dToday.day == month_last_day[dToday.month] and freq_month_day > dToday.day:
                if dToday.month != 2:
                    freq_month_day = dToday.day
                elif dToday.month == 2 and dToday.day == 28 and (dToday + timedelta(days= +1)).day != 29:
                    freq_month_day = dToday.day
            
            if dToday.day != freq_month_day:
                return
            
            freq_amount = milestone_amount / float(next_adj_template.milestone - adj_template.milestone)
        else: # annual frequency
            # Only done once per month so don't do it if we already have a record for this month
            dLast = self._get_last_run_date(cr, uid, line.id, nomatch_id=job_id, context=context)
            if dLast != None and dLast.month == dToday.month and dLast.year == dToday.year:
                return
            
            if adj_template and float_compare(adj_template.milestone, 12.0, precision_digits=2) in [0, 1]  and dToday.month != freq_annual_month:
                return
            
            freq_amount = milestone_amount
        
        if line.max_adjustment > -0.01 and line.max_adjustment < 0.01:
            amount = freq_amount
        else:
            amount = min(freq_amount, line.max_adjustment)
        
        # Create Adjustments
        #
        vals = {
            'employee_id': contract.employee_id.id,
            'contract_id': contract.id,
            'effective_date': self._get_effective_date(cr, uid, contract.id, dToday, context=context),
            'wage': amount,
            'run_id': run_id,
        }
        adj_id = adj_obj.create(cr, uid, vals, context=context)
        adj = adj_obj.browse(cr, uid, adj_id, context=context)
        if float_compare(adj.wage, adj.current_wage, precision_digits=2) in [-1, 0]:
            adj_obj.unlink(cr, uid, [adj_id], context=context)
    
    def _get_last_calculation_id(self, cr, uid, domain, context=None):
        '''For a given domain, get the id for the last date on which a job was executed.'''
        
        job_obj = self.pool.get('hr.policy.line.wageadj.job')
        
        job_ids = job_obj.search(cr, uid, domain, order='name desc', limit=1, context=context)
        if len(job_ids) == 0:
            return None
        
        return job_ids[0]
    
    def _get_last_calculation_date(self, cr, uid, accrual_id, nomatch_id=None, context=None):
        '''Get the last date for which a job was executed, regardless of adjustment runs'''
        
        job_obj = self.pool.get('hr.policy.line.wageadj.job')
        
        domain = [('policy_line_id', '=', accrual_id)]
        if nomatch_id != None:
            domain += [('id', '!=', nomatch_id)]
        
        job_id = self._get_last_calculation_id(cr, uid, domain, context)
        if job_id == None:
            return None
        
        data = job_obj.read(cr, uid, job_id, ['name'], context=context)
        return datetime.strptime(data['name'], OE_DATEFORMAT).date()
    
    def _get_last_run_date(self, cr, uid, accrual_id, nomatch_id=None, context=None):
        '''Get the last date for which a job was executed and an adjustment run was made.'''
        
        job_obj = self.pool.get('hr.policy.line.wageadj.job')
        
        domain = [('policy_line_id', '=', accrual_id), ('no_runs', '=', False)]
        if nomatch_id != None:
            domain += [('id', '!=', nomatch_id)]
        
        job_id = self._get_last_calculation_id(cr, uid, domain, context)
        if job_id == None:
            return None
        
        data = job_obj.read(cr, uid, job_id, ['name'], context=context)
        return datetime.strptime(data['name'], OE_DATEFORMAT).date()
    
    def _in_prev_month(self, d1, d2):
        '''Return True if d2 is a date in the immediately preceding month.'''
        
        if d1 < d2 and d1.month != d2.month and (d1 + relativedelta(months= -1)).month == d2.month:
            return True
        return False
    
    def _get_effective_date(self, cr, uid, contract_id, dToday, context=None):
        
        if not contract_id: return False
        
        contract = self.pool.get('hr.contract').browse(cr, uid, contract_id, context=context)
        if contract.pps_id:
            first_day = 1
            if contract.pps_id.type == 'monthly':
                first_day = contract.pps_id.mo_firstday
            dThisMonth = datetime.strptime(dToday.strftime('%Y-%m-' + first_day), OE_DATEFORMAT).date()
            dNextMonth = datetime.strptime((dToday + relativedelta(months= +1)).strftime('%Y-%m-' + first_day), OE_DATEFORMAT).date()
            if dThisMonth < dToday:
                return dNextMonth.strftime(OE_DATEFORMAT)
            else:
                return dThisMonth.strftime(OE_DATEFORMAT)
        
        return False

    def _create_run(self, cr, uid, line, job_id, dToday, context=None):
        
        # Create a batch adjustment for the policy line
        run_vals = {
            'name': line.name +' '+ dToday.strftime('%Y/%m'),
            'effective_date': dToday.strftime(OE_DATEFORMAT),
            'type': 'manual',
            'adjustment_amount': 0,
            'wageadj_policy_line_id': line.id,
            'wageadj_policy_job_id': job_id,
        }
        run_id = self.pool.get('hr.contract.wage.increment.run').create(cr, uid, run_vals,
                                                                        context=context)
        
        # Add this batch adjustment to both the job and the policy line
        #
        self.pool.get('hr.policy.line.wageadj.job').write(cr, uid, job_id, 
                                                          {'run_ids': [(4, run_id)]},
                                                          context=context)
        self.pool.get('hr.policy.line.wageadj').write(cr, uid, line.id, {'run_ids': [(4, run_id)]},
                                                      context=context)
        
        return run_id
    
    def try_calculate_adjustments(self, cr, uid, context=None):
        
        pg_obj = self.pool.get('hr.policy.group')
        run_obj = self.pool.get('hr.contract.wage.increment.run')
        job_obj = self.pool.get('hr.policy.line.wageadj.job')
        dToday = datetime.now().date()
        
        pg_ids = pg_obj.search(cr, uid, [], context=context)
        for pg in pg_obj.browse(cr, uid, pg_ids, context=context):
            wageadj_policy = self.get_latest_policy(cr, uid, pg, dToday, context=context)
            if wageadj_policy == None:
                continue
            
            # Get the last time that a job was run for each line in
            # the policy. If there was no 'last time' assume this is the first
            # time the job is being run and start it running from today.
            #
            line_jobs = {}
            for line in wageadj_policy.line_ids:
                d = self._get_last_calculation_date(cr, uid, line.id, context=context)
                if d == None:
                    line_jobs[line.id] = [dToday]
                else:
                    line_jobs[line.id] = []
                    while d < (dToday + timedelta(days= -1)):
                        d += timedelta(days=1)
                        line_jobs[line.id].append(d)
            
            
            # For each line in this policy do a run for each day (beginning
            # from the last date for which it was run) until today for each contract attached
            # to the policy group.
            #
            for line in wageadj_policy.line_ids:
                category_ids = []
                if line.category_ids and len(line.category_ids) > 0:
                    category_ids = [c.id for c in line.category_ids]
                
                for dJob in line_jobs[line.id]:
                    # Create a Job for this run
                    job_vals = {
                        'name': dJob.strftime(OE_DATEFORMAT),
                        'exec': datetime.now().strftime(OE_DATETIMEFORMAT),
                        'policy_line_id': line.id,
                    }
                    job_id = job_obj.create(cr, uid, job_vals, context=context)

                    run_id = self._create_run(cr, uid, line, job_id, dJob, context=context)
                    
                    employee_list = []
                    for contract in pg.contract_ids:
                        if contract.employee_id.id in employee_list or contract.state in ['draft', 'done']:
                            continue
                        if contract.date_end and datetime.strptime(contract.date_end, OE_DATEFORMAT).date() < dJob:
                            continue
                        if line.wage_limit > 0.01 and contract.wage > line.wage_limit:
                            continue
                        
                        # If an employee category is specified proceed only if the employee
                        # is in that category. Look at both employee categories and categories
                        # attached to the job position associated with the job position.
                        if len(category_ids) > 0:
                            _in_category = False
                            ee_categ = []
                            if contract.job_id and contract.job_id.category_ids:
                                for c in contract.job_id.category_ids:
                                    if c.id not in ee_categ:
                                        ee_categ.append(c.id)
                            if contract.employee_id and contract.employee_id.category_ids:
                                for c in contract.employee_id.category_ids:
                                    if c.id not in ee_categ:
                                        ee_categ.append(c.id)
                            for cid in ee_categ:
                                if cid in category_ids:
                                    _in_category = True
                            if not _in_category:
                                continue
                        
                        # If job is in excluded list don't process
                        if line.exjob_ids:
                            exjob_ids = [j.id for j in line.exjob_ids]
                            if contract.job_id.id in exjob_ids:
                                continue
                        
                        # If the included jobs list is NOT EMPTY, then process only
                        # those jobs exclusively. If it IS EMPTY, then assume anything
                        # not in the excluded list should be included.
                        #
                        _job_is_included = False
                        if line.incjob_ids and len(line.incjob_ids) > 0:
                            incjob_ids = [j.id for j in line.incjob_ids]
                            if contract.job_id.id in incjob_ids:
                                _job_is_included = True
                        else:
                            _job_is_included = True
                        if not _job_is_included:
                            continue
                        
                        date_str = self._get_effective_date(cr, uid, contract.id, dJob, context=context)
                        self._calculate_and_adjust(cr, uid, line, contract, job_id, run_id,
                                                   date_str, dToday=dJob, context=context)

                        # An employee may have multiple valid contracts. Don't double-count.
                        employee_list.append(contract.employee_id.id)

                    # If no adjustments were created delete the batch run and mark the job
                    rdata = run_obj.read(cr, uid, run_id, ['increment_ids'], context=context)
                    if len(rdata['increment_ids']) == 0:
                        run_obj.unlink(cr, uid, run_id, context=context)
                        job_obj.write(cr, uid, job_id, {'no_runs': True}, context=context)
        
        return True

class hr_wageadj_template(osv.Model):
    
    _name = 'hr.wageadj.template'
    _description = 'Wage Adjustment Policy Template'
    
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'milestone': fields.integer('Milestone', required=True),
        'type': fields.selection([
                                  ('fixed', 'Fixed Amount'),
                                  ('percent', 'Percentage'),
                                  ('final', 'Final Amount'),
                                  ('manual', 'Manual'),
                                 ], 'Type', required=True),
        'amount': fields.float('Amount', digits_compute=dp.get_precision('Payroll'), required=True),
        'policy_line_id': fields.many2one('hr.policy.line.wageadj', 'Adjustment Policy'),
    }
    
    _order = 'milestone'
    
class hr_policy_line(osv.Model):
    
    _name = 'hr.policy.line.wageadj'
    _description = 'Wage Adjustment Policy Line'
    
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'code': fields.char('Code', size=16, required=True),
        'category_ids': fields.many2many('hr.employee.category', 'wageadj_policy_category_rel', 'policy_id',
                                         'category_id', 'Employee Categories'),
        'exjob_ids': fields.many2many('hr.job', 'employee_exjob_rel', 'emp_id', 'job_id',
                                    'Excluded Job Positions'),
        'incjob_ids': fields.many2many('hr.job', 'employee_incjob_rel', 'emp_id', 'job_id',
                                    'Included Job Positions',
                                    help="Applies only to these job positions"),
        'wage_limit': fields.float('Wage Limit', digits_compute=dp.get_precision('Payroll'), required=True,
                                   help="Limit adjustments only to current wages less than or equal to this amount"),
        'policy_id': fields.many2one('hr.policy.wageadj', 'Adjustment Policy'),
        'type': fields.selection([('standard', 'Standard'), ('calendar', 'Calendar')], 'Type',
                                 required=True),
        'calculation_frequency': fields.selection([('weekly', 'Weekly'),
                                                   ('monthly', 'Monthly'),
                                                   ('annual', 'Annual'),
                                                  ],
                                                  'Calculation Frequency', required=True),
        'frequency_on_hire_date': fields.boolean('Frequency Based on Hire Date'),
        'frequency_week_day': fields.selection([('0', 'Monday'),
                                                ('1', 'Tuesday'),
                                                ('2', 'Wednesday'),
                                                ('3', 'Thursday'),
                                                ('4', 'Friday'),
                                                ('5', 'Saturday'),
                                                ('6', 'Sunday'),
                                               ],
                                             'Week Day'),
        'frequency_month_day': fields.selection([
             ('1', '1'),('2', '2'),('3', '3'),('4', '4'),('5', '5'),('6', '6'),('7', '7'),
             ('8', '8'),('9', '9'),('10', '10'),('11', '11'),('12', '12'),('13', '13'),('14', '14'),
             ('15', '15'),('16', '16'),('17', '17'),('18', '18'),('19', '19'),('20', '20'),('21', '21'),
             ('22', '22'),('23', '23'),('24', '24'),('25', '25'),('26', '26'),('27', '27'),('28', '28'),
             ('29', '29'),('30', '30'),('31', '31'),
            ],
            'Day of Month'),
        'frequency_annual_month': fields.selection([('1', 'January'), ('2', 'February'),
                                                    ('3', 'March'), ('4', 'April'),
                                                    ('5', 'May'), ('6', 'June'),
                                                    ('7', 'July'), ('8', 'August'),
                                                    ('9', 'September'), ('10', 'October'),
                                                    ('11', 'November'), ('12', 'December'),
                                                   ],
                                                   'Month'),
        'frequency_annual_day': fields.selection([
             ('1', '1'),('2', '2'),('3', '3'),('4', '4'),('5', '5'),('6', '6'),('7', '7'),
             ('8', '8'),('9', '9'),('10', '10'),('11', '11'),('12', '12'),('13', '13'),('14', '14'),
             ('15', '15'),('16', '16'),('17', '17'),('18', '18'),('19', '19'),('20', '20'),('21', '21'),
             ('22', '22'),('23', '23'),('24', '24'),('25', '25'),('26', '26'),('27', '27'),('28', '28'),
             ('29', '29'),('30', '30'),('31', '31'),
            ],
            'Day of Month'),
        'minimum_employed_days': fields.integer('Minimum Employed Days'),
        'template_ids': fields.one2many('hr.wageadj.template', 'policy_line_id',
                                        string='Adjustment Templates'),
        'run_ids': fields.many2many('hr.contract.wage.increment.run',
                                    'hr_policy_line_wageadj_hr_increment_run_rel',
                                    'policy_line', 'run_id', string='Adjustment Batch',
                                    readonly=True),
        'max_adjustment': fields.float('Adjustment Limit',
                                       digits_compute=dp.get_precision('Payroll'), required=True),
        'max_milestone': fields.integer('Last Milestone', required=True,
                                        help="No more adjustments will be made after the "     \
                                             "employee has been employed for this number of "  \
                                             "months. If zero, the adjustments will continue " \
                                             "indefinitely."),
        'job_ids': fields.one2many('hr.policy.line.wageadj.job', 'policy_line_id', 'Jobs',
                                   readonly=True),
    }
    
    _defaults = {
        'type': 'calendar',
        'minimum_employed_days': 0,
        'max_adjustment': 0,
        'max_milestone': 0,
        'wage_limit': 0,
    }

class policy_group(osv.Model):
    
    _name = 'hr.policy.group'
    _inherit = 'hr.policy.group'
    
    _columns = {
        'wageadj_policy_ids': fields.many2many('hr.policy.wageadj', 'hr_policy_group_wageadj_rel',
                                                'group_id', 'wageadj_id', 'Wage Adjustment Policy'),
    }
