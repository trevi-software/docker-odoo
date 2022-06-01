#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyrigth (C) 2013 Michael Telahun Makonnen <mmakonnen@gmail.com>
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    d$
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

from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from report import report_sxw

import logging
_l = logging.getLogger(__name__)

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'summarize': self.summerize,
            'sum_total_bunches': self.sum_total_bunches,
            'avg_bunch': self.avg_bunch,
            'avg_ee': self.avg_ee,
            'avg_payment': self.avg_payment,
            'total_payment': self.total_payment,
            'reset_stats': self.reset_stats,
            'average_stats': self.average_stats,
            'get_top': self.get_top,
            'get_bottom': self.get_bottom,
        })
        
        self.start_date = False
        self.end_date = False
        self.state = 'all'
        self.period_avg_bunch = 0
        self.period_avg_employee = 0
        self.period_total_bunch = 0
        self.period_avg_payment = 0.00
        self.period_total_payment = 0.00
        self.price = 0.00
        self.quota = 0
        self.bunch_days = 0
        self.total_days = 0
        self.leader_board = {}
        self.leader_board_ids = []
        self.leader_board_sorted = False
    
    def set_context(self, objects, data, ids, report_type=None):
        if data.get('form', False) and data['form'].get('start_date', False):
            self.start_date = data['form']['start_date']
        if data.get('form', False) and data['form'].get('end_date', False):
            self.end_date = data['form']['end_date']
        if data.get('form', False) and data['form'].get('state', 'all'):
            self.state = data['form']['state']
        if data.get('form', False) and data['form'].get('quota', 0):
            self.quota = data['form']['quota']
        if data.get('form', False) and data['form'].get('price', 0.00):
            self.price = data['form']['price']
        
        dStart = datetime.strptime(self.start_date, OE_DFORMAT)
        dEnd = datetime.strptime(self.end_date, OE_DFORMAT)
        self.total_days = (dEnd - dStart).days
        
        return super(Parser, self).set_context(objects, data, ids, report_type=report_type)
    
    def reset_stats(self):
        
        self.period_avg_bunch = 0
        self.period_avg_employee = 0
        self.period_total_bunch = 0
        self.period_avg_payment = 0.00
        self.period_total_payment = 0.00
        self.bunch_days = 0
        self.total_days = 0
        self.leader_board = {}
        self.leader_board_ids = []
        self.leader_board_sorted = False
    
    def get_departments(self):
        
        # Get all departments that have a bunching sheet within
        # the period.
        #
        bs_obj = self.pool.get('hr.bunching.sheet')
        sheet_ids = bs_obj.search(self.cr, self.uid,
                                  [('state', '=', 'approve'),
                                   '&', ('name', '>=', self.start_date),
                                        ('name', '<=', self.end_date),
                                  ])
        dept_ids = []
        for bs in bs_obj.browse(self.cr, self.uid, sheet_ids):
            if bs.department_id.id not in dept_ids:
                dept_ids.append(bs.department_id.id)
        
        return dept_ids
    
    def get_eligible_positions(self):
        
        job_ids = []
        dept_ids = self.get_departments()
        job_obj = self.pool.get('hr.job')
        if len(dept_ids) > 0:
            job_ids += job_obj.search(self.cr, self.uid, [('department_id', 'in', dept_ids)])
        return job_ids
    
    def summerize(self, department_id):
        
        cr = self.cr
        uid = self.uid
        c_start = self.start_date
        c_end = self.end_date
        eligible_job_ids = self.get_eligible_positions()
        domain = []
        if self.state != 'all':
            domain = [('sheet_id.state', '=', self.state)]
        
        # First, get the number of employees with a contract during the period
        #
        c_obj = self.pool.get('hr.contract')
        c_ids = c_obj.search(cr, uid, [('date_start', '<=', c_end),
                                       '|', ('date_end', '=', False),
                                            ('date_end', '>=', c_start),
                                       '|', ('job_id.department_id', '=', department_id),
                                            ('end_job_id.department_id', '=', department_id)])
        ee_ids = []
        ee_data = {}
        att_obj = self.pool.get('hr.attendance')
        dStart = datetime.strptime(c_start, OE_DFORMAT).date()
        dEnd = datetime.strptime(c_end, OE_DFORMAT).date()
        datas = c_obj.read(cr, uid, c_ids, ['employee_id', 'date_start', 'date_end'])
        for d in datas:
            if d['employee_id'][0] not in ee_ids:
                ee_ids.append(d['employee_id'][0])
                contract = c_obj.browse(cr, uid, d['id'])
                punches_list = att_obj.punches_list_init(cr, uid, d['employee_id'][0],
                                                         contract.pps_id, dStart, dEnd)
                ee_data.update({d['employee_id'][0]: {'c_obj': contract, 'contracts': [], 'punches': punches_list}})
                _dS = datetime.strptime(d['date_start'], OE_DFORMAT).date()
                _dE = dEnd
                if d['date_end']:
                    _dE = datetime.strptime(d['date_end'], OE_DFORMAT).date()
                ee_data[d['employee_id'][0]]['contracts'].append((_dS, _dE))
        
        # Re-arrange employee ids in alphabetical order
        ee_ids = self.pool.get('hr.employee').search(cr, uid, [('id', 'in', ee_ids)])
        
        # Compute employee's share of over-target for each day in the
        # period. Employee share is average of all employees present that day.
        #
        res = []
        att_obj = self.pool.get('hr.attendance')
        bsl_obj = self.pool.get('hr.bunching.sheet.line')
        dStart = datetime.strptime(c_start, OE_DFORMAT).date()
        dEnd = datetime.strptime(c_end, OE_DFORMAT).date()
        dToday = dStart
        while dToday <= dEnd:
            
            _rec = {
                'date': dToday.strftime(OE_DFORMAT),
                'total_bunches': 0,
                'present_employees': 0,
                'avg_bunch': 0,
                'avg_payment': 0.00,
                'total_payment': 0.00,
                'employees': [],
            }
            
            bunch_totals = {}
            bunch_totals_ids = []
            total_bunches = 0
            bunching_ids = bsl_obj.search(cr, uid, domain +
                                          [('sheet_id.department_id', '=', department_id),
                                           ('sheet_id.name', '=', dToday.strftime(OE_DFORMAT)),
                                          ])
            for line in bsl_obj.browse(cr, uid, bunching_ids):
                total_bunches += ((line.total - self.quota) > 0) and (line.total - self.quota) or 0
                if line.employee_id.id not in bunch_totals_ids:
                    bunch_totals_ids.append(line.employee_id.id)
                    bunch_totals.update({line.employee_id.id: 0})
                bunch_totals[line.employee_id.id] += line.total
                
                # Update Leader Board
                if line.employee_id.id not in self.leader_board_ids:
                    self.leader_board_ids.append(line.employee_id.id)
                    self.leader_board.update({line.employee_id.id: {'bunches': 0, 'days': 0}})
                self.leader_board[line.employee_id.id]['bunches'] += line.total
                self.leader_board[line.employee_id.id]['days'] += 1
            
            # Compute total number of employees in the department that worked on this day
            total_ee = 0
            for eid, v in ee_data.items():
            
                _ee = {
                    'no': '',
                    'name': False,
                    'ee_id': '',
                    'above_quota': 0,
                    'hours': 0,
                    'ot_hours': 0,
                    'ot_payment': 0.00,
                    'avg_bunch': 0,
                    'avg_payment': 0.00,
                }
                for dCStart, dCEnd in v['contracts']:
                    if dToday >= dCStart and dToday <= dCEnd:
                        hours = att_obj.total_hours_on_day(cr, uid, v['c_obj'], dToday,
                                                           punches_list=v['punches'])
                        if hours > 0:
                            _ee['no'] = total_ee + 1
                            _ee['name'] = v['c_obj'].employee_id.name
                            _ee['ee_id'] = v['c_obj'].employee_id.f_employee_no
                            _ee['hours'] = hours > 8 and 8 or hours
                            _ee['ot_hours'] = (hours - 8.0) > 0 and (hours - 8.0) or 0
                            _ee['ot_payment'] = _ee['ot_hours'] * v['c_obj'].wage_hourly * 1.25
                            _ee['above_quota'] = bunch_totals.get(eid, 0) - self.quota
                            if bunch_totals.get(eid, 0) or v['c_obj'].job_id.id in eligible_job_ids:
                                total_ee += 1
                                _rec['employees'].append(_ee)
                        break
            
            if total_ee > 0:
                avg = float(total_bunches) / float(total_ee)
            else:
                avg = 0
            _rec['total_bunches'] = total_bunches
            _rec['present_employees'] = total_ee
            _rec['avg_bunch'] = avg
            _rec['avg_payment'] = '{0:.2f}'.format(avg * self.price)
            _real_payment = 0.00
            for _r in _rec['employees']:
                _hours = _r['hours'] > 8 and 8 or _r['hours']
                _r['avg_bunch'] = _rec['avg_bunch'] * (float(_r['hours']) / 8.0)
                _r['avg_payment'] = _r['avg_bunch'] * self.price
                _real_payment += _r['avg_payment']
                # Format for output
                _r['avg_bunch'] = '{0:.1f}'.format(_r['avg_bunch'])
                _r['avg_payment'] = '{0:.2f}'.format(_r['avg_payment'])
                _r['ot_payment'] = '{0:.2f}'.format(_r['ot_payment'])
            _rec['total_payment'] = '{0:.2f}'.format(_real_payment)

            # Format for output
            _rec['avg_bunch'] = '{0:.1f}'.format(_rec['avg_bunch'])
                        
            # Sum period stats
            self.period_avg_bunch += float(_rec['avg_bunch'])
            self.period_avg_employee += float(_rec['present_employees'])
            self.period_total_bunch += float(_rec['total_bunches'])
            self.period_avg_payment += float(_rec['avg_payment'])
            self.period_total_payment += float(_rec['total_payment'])
            
            res.append(_rec)
            if total_bunches > 0:
                self.bunch_days += 1
            dToday = dToday + timedelta(days= +1)
        
        return res
    
    def sort_leader_board(self):
        
        if self.leader_board_sorted:
            return
        
        _sorted = []
        for eid, v in self.leader_board.items():
            total = v['bunches']
            days = v['days']
            avg = total / days
            if len(_sorted) == 0:
                _sorted.append((eid, total, days))
            elif avg > _sorted[0]:
                _sorted.insert(0, (eid, total, days))
            else:
                for srt in _sorted:
                    srt_eid, srt_total, srt_days = srt
                    if avg > srt_total / srt_days:
                        idx = _sorted.index(srt)
                        _sorted.insert(idx, (eid, total, days))
                        break;
        
        self.leader_board = _sorted
        self.leader_board_sorted = True
        return
    
    def get_top(self, no=10):
        
        self.sort_leader_board()
        
        res = []
        no = int(no)
        if no < 1:
            return res
        
        count = 0
        last_total = -1
        ee_obj = self.pool.get('hr.employee')
        for eid, total, days in self.leader_board:
            if count >= no and last_total != total:
                break
            ee = ee_obj.browse(self.cr, self.uid, eid)
            res.append({
                        'name': ee.name,
                        'id': ee.f_employee_no,
                        'dept': ee.department_id.complete_name,
                        'total': total,
                        'days': days,
                        'avg': (total/days)
                        })
            last_total = total
            count += 1
        
        return res
    
    def get_bottom(self, no=10):
        
        self.sort_leader_board()
        
        res = []
        no = int(no)
        if no < 1:
            return res
        
        # Adjust count based on total entries on leader board
        if (len(self.leader_board) - no) < no:
            no = len(self.leader_board) - no
        if no < 1:
            return res
        
        count = 0
        last_total = -1
        ee_obj = self.pool.get('hr.employee')
        _board = self.leader_board
        _board.reverse()
        for eid, total, days in self.leader_board:
            if count >= no and last_total != total:
                break
            ee = ee_obj.browse(self.cr, self.uid, eid)
            res.append({
                        'name': ee.name,
                        'id': ee.f_employee_no,
                        'dept': ee.department_id.complete_name,
                        'total': total,
                        'days': days,
                        'avg': (total/days)
                        })
            last_total = total
            count += 1
        
        return res
    
    def average_stats(self):
        
        # Average the period stats
        self.period_avg_payment = self.period_avg_payment
        if self.bunch_days > 0:
            self.period_avg_bunch = float(self.period_avg_bunch) / float(self.bunch_days)
        if self.total_days == 0:
            self.total_days = 1
        self.period_avg_employee = float(self.period_avg_employee) / float(self.total_days)
    
    def sum_total_bunches(self):
        return self.period_total_bunch
    
    def avg_bunch(self):
        return '{0:.1f}'.format(self.period_avg_bunch)
    
    def avg_ee(self):
        return round(self.period_avg_employee, 0)
    
    def avg_payment(self):
        return '{0:.2f}'.format(self.period_avg_payment)
    
    def total_payment(self):
        return '{0:.2f}'.format(self.period_total_payment)
