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

from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools.float_utils import float_compare
from openerp.tools.translate import _

class adj_seniority(orm.TransientModel):
    
    _name = 'wage.adjustment.seniority'
    _description = 'Wage Adjustment by Seniority'
    
    _columns = {
        'date': fields.date('Computation Date', required=True,
                            help=_('Date as of when the seniority should be calculated')),
        'min_month': fields.float('Min. Service Month', required=True,
                                  help="Minimum length of service is less than or equal to " \
                                       "this number"),
        'max_month': fields.float('Max. Service Month', required=True,
                                  help="Maximum length of service is less than this number. " \
                                       "If there is no upper limit use an absurdly high "     \
                                       "number like 1200 (100 years)."),
        'department_ids': fields.many2many('hr.department', 'wage_adjustment_seniority_dept_rel',
                                           'wizard_id', 'department_id', 'Departments',
                                           help="The employee's current department, not " \
                                                "the one at the time of the adjustment."),
        'ex_depts': fields.boolean('Exclude Departments',
                                   help="Check this if employees in the listed departments " \
                                        "should be *EXCLUDED* from the adjustment.The "      \
                                        "department refers to the current department, not "  \
                                        "the one at the time of the adjustment."),
        'ex_negative': fields.boolean('Exclude Reductions',
                                      help="Check this to automatically ignore adjustments " \
                                           "that would result in reducing an employee's "    \
                                           "salary")
    }
    
    _defaults = {
        'min_month': 0.0,
        'ex_negative': True,
    }

    def _calculate_adjustment(self, initial, adj_type, adj_amount):
        
        result = 0
        if adj_type == 'fixed':
            result = initial + adj_amount
        elif adj_type == 'percent':
            result = initial + (initial * adj_amount / 100)
        elif adj_type == 'final':
            result = adj_amount
        else:
            # manual
            result = initial
        
        return result
    
    def create_adjustments(self, cr, uid, ids, context=None):
        
        emp_pool = self.pool.get('hr.employee')
        adj_pool = self.pool.get('hr.contract.wage.increment')
        run_pool = self.pool.get('hr.contract.wage.increment.run')
        
        if context is None:
            context = {}
        
        wizard = self.browse(cr, uid, ids[0], context=context)
        
        run_id = context.get('active_id', False)
        if not run_id:
            raise orm.except_orm(_('Internal Error'), _('Unable to determine wage adjustment run ID'))
        
        run_data = run_pool.read(cr, uid, run_id, ['effective_date', 'type', 'adjustment_amount'],
                                 context=context)

        # Adjust domain according to selection in wizard        
        dept_domain = []
        if len(wizard.department_ids) > 0 and wizard.ex_depts:
            dept_domain += [('department_id', 'not in', [d.id for d in wizard.department_ids])]
        elif len(wizard.department_ids) > 0:
            dept_domain += [('department_id', 'in', [d.id for d in wizard.department_ids])]

        # Get employees
        dComp = datetime.strptime(wizard.date, OE_DFORMAT).date()
        ee_match_ids = []
        ee_ids = emp_pool.search(cr, uid, [('status', 'in', ['onboarding', 'active'])] + dept_domain,
                                 context=context)
        ee_data = emp_pool.get_months_service_to_date(cr, uid, ee_ids, dToday=dComp,
                                                      context=context)
        for eid, stats in ee_data.items():
            
            months = stats[0]
            if (float_compare(months, wizard.min_month, precision_digits=1) >= 0) \
               and (float_compare(months, wizard.max_month, precision_digits=1) < 0):
                ee_match_ids.append(eid)
        
        # Group by department and put in alphabetical order
        ee_match_ids = emp_pool.search(cr, uid, [('id', 'in', ee_match_ids)],
                                       order='department_id,name', context=context)
        
        for emp in emp_pool.browse(cr, uid, ee_match_ids, context=context):
            
            if not emp.contract_id:
                continue

            res = {
                'effective_date': run_data.get('effective_date', False),
                'contract_id': emp.contract_id.id,
                'wage': self._calculate_adjustment(emp.contract_id.wage, run_data['type'],
                                                   run_data['adjustment_amount']),
                'run_id': run_id,
            }
            
            # Skip if user wants to exclude reductions in wage
            if wizard.ex_negative and res['wage'] < emp.contract_id.wage:
                continue
            
            # Remove active_id from context because wage adjustment assumes it is
            # the employee_id.
            #
            if context.get('active_id', False):
                ctx2 = context.copy()
                ctx2['active_id'] = False
            else:
                ctx2 = context
            
            adj_pool.create(cr, uid, res, context=ctx2)
        
        return {'type': 'ir.actions.act_window_close'}
