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
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OEDATE_FORMAT
from openerp.tools.translate import _

BNCHCODE='BUNCH2'

class hr_payslip(osv.Model):
    
    _name = 'hr.payslip'
    _inherit = 'hr.payslip'
    
    def get_worked_day_lines(self, cr, uid, contract_ids, date_from, date_to, context=None):
        
        res = super(hr_payslip, self).get_worked_day_lines(cr, uid, contract_ids, date_from, date_to,
                                                           context=context)
        
        
        dFrom = datetime.strptime(date_from, OEDATE_FORMAT).date()
        dTo = datetime.strptime(date_to, OEDATE_FORMAT).date()
        
        for contract in self.pool.get('hr.contract').browse(cr, uid, contract_ids, context=context):
            
            # Set the proper time frame
            #
            c_start = date_from
            c_end = date_to
            if contract.date_start:
                dc_start = datetime.strptime(contract.date_start, OEDATE_FORMAT).date()
                if dc_start > dFrom:
                    c_start = dc_start.strftime(OEDATE_FORMAT)
            if contract.date_end:
                dc_end = datetime.strptime(contract.date_end, OEDATE_FORMAT).date()
                if dc_end < dTo:
                    c_end = dc_end.strftime(OEDATE_FORMAT)
            
            bunch = {
                 'name': _("Avg. Extra bunches graded"),
                 'sequence': 150,
                 'code': BNCHCODE,
                 'number_of_days': 0.0,     # bunch money amount
                 'number_of_hours': 0.0,    # ot hours that are less than bunch payment
                 'contract_id': contract.id,
            }
            
            # Get all departments that have a bunching sheet within
            # the period.
            #
            bs_obj = self.pool.get('hr.bunching.sheet')
            sheet_ids = bs_obj.search(cr, uid,
                                      [('state', '=', 'approve'),
                                       '&', ('name', '>=', c_start),
                                            ('name', '<=', c_end),
                                      ], context=context)
            dept_ids = []
            for bs in bs_obj.browse(cr, uid, sheet_ids, context=context):
                if bs.department_id.id not in dept_ids:
                    dept_ids.append(bs.department_id.id)
            
            # If the contract is not in any of these departments do nothing
            my_department_id = False
            if contract.job_id:
                if contract.job_id.department_id.id not in dept_ids:
                    res += [bunch]
                    continue
                else:
                    my_department_id = contract.job_id.department_id.id
            elif contract.end_job_id:
                if contract.end_job_id.department_id not in dept_ids:
                    res += [bunch]
                    continue
                else:
                    my_department_id = contract.end_job_id.department_id.id
            
            # Get the number of employees with a contract in the department during the period.
            # Compute which days the employees were present during that period.
            #
            c_obj = self.pool.get('hr.contract')
            c_ids = c_obj.search(cr, uid, [('date_start', '<=', c_end),
                                           '|', ('date_end', '=', False),
                                                ('date_end', '>=', c_start),
                                           '|', ('job_id.department_id', '=', my_department_id),
                                                ('end_job_id.department_id', '=', my_department_id)])
            ee_ids = []
            ee_data = {}
            att_obj = self.pool.get('hr.attendance')
            dStart = datetime.strptime(c_start, OEDATE_FORMAT).date()
            dEnd = datetime.strptime(c_end, OEDATE_FORMAT).date()
            datas = c_obj.read(cr, uid, c_ids, ['employee_id', 'date_start', 'date_end'])
            for d in datas:
                if d['employee_id'][0] not in ee_ids:
                    ee_ids.append(d['employee_id'][0])
                    punches_list = att_obj.punches_list_init(cr, uid, d['employee_id'][0],
                                                             contract.pps_id, dStart, dEnd, context=context)
                    ee_data.update({d['employee_id'][0]: {'contracts': [], 'punches': punches_list}})
                _dS = datetime.strptime(d['date_start'], OEDATE_FORMAT).date()
                _dE = dEnd
                if d['date_end']:
                    _dE = datetime.strptime(d['date_end'], OEDATE_FORMAT).date()
                ee_data[d['employee_id'][0]]['contracts'].append((_dS, _dE))
            
            # Compute employee's share of over-target for each day in the
            # period and sum it up. Employee share is average of all employees
            # present that day.
            #
            bsl_obj = self.pool.get('hr.bunching.sheet.line')
            my_punches_list = ee_data[contract.employee_id.id]['punches']
            dToday = dStart
            while dToday <= dEnd:
                
                # Compute total number of employees in the department that worked on this day
                total_ee = 0
                for eid, v in ee_data.items():
                    for dCStart, dCEnd in v['contracts']:
                        if dToday >= dCStart and dToday <= dCEnd:
                            hours = att_obj.total_hours_on_day(cr, uid, contract, dToday,
                                                               punches_list=v['punches'], context=context)
                            if hours > 0:
                                total_ee += 1
                            break
                
                # Compute this employee's hours during that day
                ot_hours = 0
                worked_hours = att_obj.total_hours_on_day(cr, uid, contract, dToday,
                                                          punches_list=my_punches_list, context=context)
                if worked_hours == 0:
                    dToday = dToday + timedelta(days= +1)
                    continue
                elif worked_hours > 8.0:
                    ot_hours = worked_hours - 8.0
                    worked_hours = 8
                
                bunching_ids = bsl_obj.search(cr, uid,
                                              [('sheet_id.department_id', '=', my_department_id),
                                               ('sheet_id.state', '=', 'approve'),
                                               ('sheet_id.name', '=', dToday.strftime(OEDATE_FORMAT)),
                                              ],
                                              context=context)
                total_bunches = 0
                for line in bsl_obj.browse(cr, uid, bunching_ids, context=context):
                    total_bunches += (line.difference > 0) and line.difference or 0
                
                avg = float(total_bunches) / float(total_ee) * (float(worked_hours) / 8.0)
                avg_payment = avg * 0.22
                ot = ot_hours * contract.wage_hourly * 1.25
                if avg_payment >= ot:
                    bunch['number_of_days'] += avg
                    bunch['number_of_hours'] += ot_hours
                
                dToday = dToday + timedelta(days= +1)
            
            res += [bunch]
        
        return res
