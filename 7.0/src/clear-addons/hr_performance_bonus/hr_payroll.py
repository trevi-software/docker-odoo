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

from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools.float_utils import float_compare
from openerp.tools.translate import _

class hr_payslip(osv.Model):

    _name = 'hr.payslip'
    _inherit = 'hr.payslip'

    def get_worked_day_lines(self, cr, uid, contract_ids, date_from, date_to, context=None):

        res = super(hr_payslip, self).get_worked_day_lines(cr, uid, contract_ids, date_from, date_to,
                                                           context=context)
        if len(res) == 0:
            return res

        c_obj = self.pool.get('hr.contract')
        bns_obj = self.pool.get('hr.bonus.sheet')
        att_obj = self.pool.get('hr.attendance')

        dFrom = datetime.strptime(date_from, OE_DFORMAT).date()
        dTo = datetime.strptime(date_to, OE_DFORMAT).date()

        # If more than one contract, use the last one
        #
        _allways_false = False
        _cooked_contracts = []
        _cooked_contracts = contract_ids

        # Get departments of all contracts, and last contract
	#
        dept_ids = []
        last_contract = False
        last_contract_start = False
        for contract in c_obj.browse(cr, uid, _cooked_contracts, context=context):
            if contract.state in ['pending_done', 'done']:
                if contract.job_id:
                    dept_ids.append(contract.job_id.department_id.id)
                if contract.end_job_id.department_id:
                    dept_ids.append(contract.end_job_id.department_id.id)
            else:
                dept_ids.append(contract.job_id.department_id.id)
            if not last_contract or contract.date_start > last_contract.date_start:
            	last_contract = contract

        for contract in c_obj.browse(cr, uid, _cooked_contracts, context=context):

            # Set the proper time frame
            #
            c_start = date_from
            c_end = date_to
            if contract.date_start:
                dc_start = datetime.strptime(contract.date_start, OE_DFORMAT).date()
                if dc_start > dFrom:
                    c_start = dc_start.strftime(OE_DFORMAT)
            if contract.date_end:
                dc_end = datetime.strptime(contract.date_end, OE_DFORMAT).date()
                if dc_end < dTo:
                    c_end = dc_end.strftime(OE_DFORMAT)

            bns = {
                 'name': _("Performance Bonus"),
                 'sequence': 100,
                 'code': 'BNS1',
                 'number_of_days': 0.0,     # Bonus points
                 'number_of_hours': 0.0,    # % of take home amount because of demerit
                 'rate': 0.0,               # Bonus amount
                 'contract_id': contract.id,
            }

            bns_ids = bns_obj.search(cr, uid,
                                     [('department_id', '=', dept_ids[-1]),
                                      '&', ('date_start', '<=', date_to),
                                           ('date_end', '>=', date_from),
                                     ])

            # Check if this employee is in any performance bonus records.
            # Even though the employee's department (i.e supervisors) may
            # not have a record he or she may be attached to another
            # department that is.
            #
            _c = c_obj.browse(cr, uid, contract_ids[0], context=context)
            supervisor_bns_ids = bns_obj.search(cr, uid,
                                     ['&', ('date_start', '<=', date_to),
                                           ('date_end', '>=', date_from),
                                      ('supervisor_ids', 'in', [_c.employee_id.id]),
                                     ], context=context)
            manager_bns_ids = bns_obj.search(cr, uid,
                                     ['&', ('date_start', '<=', date_to),
                                           ('date_end', '>=', date_from),
                                      ('manager_ids', 'in', [_c.employee_id.id]),
                                     ], context=context)

            bns_ids += [i for i in supervisor_bns_ids if i not in bns_ids]
            bns_ids += [i for i in manager_bns_ids if i not in bns_ids]

            avgs = []
            amounts = []
            incentive_type = False
            for sheet in bns_obj.browse(cr, uid, bns_ids, context=context):
                multiplier = self.get_multiplier(last_contract, sheet)
                incentive_type = sheet.incentive_type
                demerit_percent = self.get_demerit_percent(cr, uid,
                                                           contract.employee_id.id,
                                                           sheet, context=context)
                amount_percent = (float_compare(0.0, demerit_percent, precision_digits=2) == 0) and 1 or (1.0 - demerit_percent)
                if incentive_type == 'fixed':
                    avgs.append(sheet.lines_avg)
                    amounts.append(sheet.bonus_amount * multiplier)
                elif incentive_type == 'daily':
                    dStart = datetime.strptime(c_start, OE_DFORMAT).date()
                    dEnd = datetime.strptime(c_end, OE_DFORMAT).date()
                    dSheetStart = datetime.strptime(sheet.date_start, OE_DFORMAT).date()
                    dSheetEnd = datetime.strptime(sheet.date_end, OE_DFORMAT).date()
                    if dSheetStart > dStart:
                        dStart = dSheetStart
                    if dSheetEnd > dEnd:
                        dEnd = dSheetEnd
                    punches_list = att_obj.punches_list_init(cr, uid, contract.employee_id.id,
                                                             contract.pps_id, dStart, dEnd, context=context)
                    for line in sheet.eval_daily_ids:
                        dLine = datetime.strptime(line.date, OE_DFORMAT).date()

                        # Compute this employee's hours during that day
                        worked_hours = att_obj.total_hours_on_day(cr, uid, contract, dLine,
                                                                  punches_list=punches_list, context=context)
                        if worked_hours > 0 and dLine >= dStart and dLine <= dEnd:
                            amounts.append(line.points * multiplier)

            if contract.id == last_contract.id:
                if incentive_type == 'fixed_amt':
                    avgs.append(sheet.bonus_amount)
                elif incentive_type == 'fixed':
                    bns['number_of_days'] = sum(avgs) / len(avgs)
                    bns['number_of_hours'] = amount_percent
                    bns['rate'] = sum(amounts) / len(amounts)
                elif incentive_type == 'daily':
                    bns['number_of_days'] = 1
                    bns['number_of_hours'] = amount_percent
                    bns['rate'] = sum(amounts) / float(len(bns_ids))

            res += [bns]
        return res

    def get_demerit_percent(self, cr, uid, ee_id, sheet, context=None):

        res = 0
        for demerit in sheet.demerit_ids:
            if demerit.employee_id.id != ee_id:
                continue
            res = abs(demerit.percentage / 100.0)
            break
        return res

    def get_multiplier(self, contract, sheet):

        res = 1.0
        if self.job_category_like(contract, 'Assistant'):
            res = sheet.assistant_bonus_multiplier
        if self.employee_is_in_list(contract.employee_id.id, sheet.supervisor_ids):
            res = sheet.supervisor_bonus_multiplier
        elif self.employee_is_in_list(contract.employee_id.id, sheet.manager_ids):
            res = sheet.manager_bonus_multiplier

        return res

    def job_category_like(self, contract, cat_string):

        job = False
        if contract.job_id:
            job = contract.job_id
        elif contract.end_job_id:
            job = contract.end_job_id

        if job:
            for cat in job.category_ids:
                if cat_string in cat.name:
                    return True

        return False

    def employee_is_in_list(self, ee_id, employee_list):

        for employee in employee_list:
            if ee_id == employee.id:
                return True

        return False
