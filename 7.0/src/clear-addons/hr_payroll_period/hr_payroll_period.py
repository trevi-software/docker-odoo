#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2011,2013 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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

import calendar
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from pytz import common_timezones, timezone, utc

import netsvc
from openerp.addons.decimal_precision import decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _
from osv import fields, osv

import logging
_logger = logging.getLogger(__name__)

# Obtained from: http://stackoverflow.com/questions/4130922/how-to-increment-datetime-month-in-python
#
def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month / 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime(year,month,day)

def get_period_year(dt, annual_pay_periods):
    
    month_number = 0
    year_number = 0
    if dt.day < 15:
        month_name = dt.strftime('%B')
        month_number = dt.month
        year_number = dt.year
    else:
        dtTmp = add_months(dt, 1)
        if annual_pay_periods > 12:
            # Maybe bi-weekly?
            month_name = dt.strftime('%B')
        else:
            month_name = dtTmp.strftime('%B')
        month_number = dtTmp.month
        year_number = dtTmp.year
    return month_name, month_number, year_number

class hr_payroll_period(osv.osv):
    
    _name = 'hr.payroll.period'
    
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    def _get_pex(self, cr, uid, period, severity, context=None):

        ex_obj = self.pool.get('hr.payslip.exception')
        run_obj = self.pool.get('hr.payslip.run')

        ex_ids = []
        slip_ids = []
        if period.register_id:
            for run_id in period.register_id.run_ids:
                data = run_obj.read(
                    cr, uid, run_id.id, ['slip_ids'], context=context)
                [slip_ids.append(i) for i in data['slip_ids']]
            ex_ids = ex_obj.search(
                cr, uid,
                [('severity', '=', severity), ('slip_id', 'in', slip_ids)],
                context=context)
        return ex_ids

    def _pex_all(self, cr, uid, ids, field_name, args, context=None):

        obj_ids = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=None):
            res = self._get_pex(cr, uid, obj, 'critical', context)
            res += self._get_pex(cr, uid, obj, 'high', context)
            res += self._get_pex(cr, uid, obj, 'medium', context)
            res += self._get_pex(cr, uid, obj, 'low', context)
            obj_ids[obj.id] = res
        return obj_ids

    def _get_denominations(self, cr, uid, ids, field_name, args, context=None):

        res = dict.fromkeys(ids, False)
        for period in self.browse(cr, uid, ids, context=context):
            res[period.id] = []
            if period.register_id is False:
                continue
            den_obj = self.pool.get('hr.payroll.register.denominations')
            res[period.id] = den_obj.search(
                cr, uid, [('register_id', '=', period.register_id.id)],
                context=context)

        return res
    
    _columns = {
        'name': fields.char('Description', size=256, required=True),
        'schedule_id': fields.many2one('hr.payroll.period.schedule', 'Payroll Period Schedule',
                                       required=True),
        'date_start': fields.datetime('Start Date', required=True),
        'date_end': fields.datetime('End Date', required=True),
        'register_id': fields.many2one('hr.payroll.register', 'Payroll Register', readonly=True,
                                       states={'generate': [('readonly', False)]}),
        'state': fields.selection([('open', 'Open'),
                                   ('ended', 'End of Period Processing'),
                                   ('locked', 'Locked'),
                                   ('generate', 'Generating Payslips'),
                                   ('payment', 'Payment'),
                                   ('closed', 'Closed')],
                                  'State', select=True, readonly=True),
        'lock_id': fields.many2one('hr.payroll.lock', 'Payroll Lock'),
        'company_id': fields.many2one('res.company', 'Company', select=True, required=False),
        'denomination_ids': fields.function(
            _get_denominations, type="many2many",
            relation='hr.payroll.register.denominations', readonly=True,
            string='Denomination Quantities'),
        'exact_change': fields.related(
            'register_id', 'exact_change', type='float',  readonly=True,
            string='Net Amount'),
        'psa_ids': fields.one2many(
            'hr.payslip.amendment', 'pay_period_id',
            string="Pay Slip Amendments"),
        'exception_ids': fields.function(
            _pex_all, type='many2many', relation='hr.payslip.exception',
            string='Pay Slip Exceptions')
    }
    
    _order = "date_start, name desc"
    
    _defaults = {
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'hr.payroll.period', context=c),
        'state': 'open',
    }
    
    _track = {
        'state': {
            'hr_payroll_period.mt_state_open': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'open',
            'hr_payroll_period.mt_state_end': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'ended',
            'hr_payroll_period.mt_state_lock': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'locked',
            'hr_payroll_period.mt_state_generate': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'generate',
            'hr_payroll_period.mt_state_payment': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'payment',
            'hr_payroll_period.mt_state_close': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'closed',
        },
    }
    
    def _needaction_domain_get(self, cr, uid, context=None):
        
        users_obj = self.pool.get('res.users')
        domain = []
        
        if users_obj.has_group(cr, uid, 'hr_security.group_payroll_manager'):
            domain = [('state', 'not in', ['open', 'closed'])]
            return domain
        
        return False

    def set_denominations(self, cr, uid, ids, context=None):

        reg_ids = []
        for period in self.browse(cr, uid, ids, context=context):
            if period.register_id:
                reg_ids.append(period.register_id.id)
        return self.pool.get('hr.payroll.register').set_denominations(
            cr, uid, reg_ids, context=context)
    
    def is_ended(self, cr, uid, period_id, context=None):
        
        #
        # XXX - Someone who cares about DST should update this code to handle it.
        #
        
        flag = False
        if period_id:
            utc_tz = timezone('UTC')
            utcDtNow = utc_tz.localize(datetime.now(), is_dst=False)
            period = self.browse(cr, uid, period_id, context=context)
            if period:
                dtEnd = datetime.strptime(period.date_end, '%Y-%m-%d %H:%M:%S')
                utcDtEnd = utc_tz.localize(dtEnd, is_dst=False)
                if utcDtNow > utcDtEnd + timedelta(minutes=(period.schedule_id.ot_max_rollover_hours * 60)):
                    flag = True
        return flag
    
    def try_signal_end_period(self, cr, uid, context=None):
        """Method called, usually by cron, to transition any payroll periods
        that are past their end date.
        """
        
        #
        # XXX - Someone who cares about DST should update this code to handle it.
        #
        
        utc_tz = timezone('UTC')
        utcDtNow = utc_tz.localize(datetime.now(), is_dst=False)
        period_ids = self.search(cr, uid, [
                                           ('state','in',['open']),
                                           ('date_end','<=',utcDtNow.strftime('%Y-%m-%d %H:%M:%S')),
                                          ], context=context)
        if len(period_ids) == 0:
            return
        
        wf_service = netsvc.LocalService('workflow')
        for pid in period_ids:
            wf_service.trg_validate(uid, 'hr.payroll.period', pid, 'end_period', cr)
    
    def get_utc_times(self, cr, uid, period, context=None):
        
        #
        # XXX - Someone who cares about DST should update this code to handle it.
        #
        
        utc_tz = timezone('UTC')
        dt = datetime.strptime(period.date_start, OE_DTFORMAT)
        utcDtStart = utc_tz.localize(dt, is_dst=False)
        dt = datetime.strptime(period.date_end, OE_DTFORMAT)
        utcDtEnd = utc_tz.localize(dt, is_dst=False)
        
        return (utcDtStart, utcDtEnd)
    
    def lock_period(self, cr, uid, periods, employee_ids, context=None):
        
        lock_obj = self.pool.get('hr.payroll.lock')
        for period in periods:
            utcDtStart, utcDtEnd = self.get_utc_times(cr, uid, period, context=context)
            lock_id = lock_obj.create(cr, uid, {'name': period.name,
                                                'start_time': utcDtStart.strftime(OE_DTFORMAT),
                                                'end_time': utcDtEnd.strftime(OE_DTFORMAT),
                                                'tz': period.schedule_id.tz},
                                      context=context)
            self.write(cr, uid, period.id, {'lock_id': lock_id}, context=context)
        
        return
    
    def unlock_period(self, cr, uid, periods, employee_ids, context=None):
        
        lock_obj = self.pool.get('hr.payroll.lock')
        for period in periods:
            
            if period.lock_id:
                lock_obj.unlink(cr, uid, period.lock_id.id, context=context)
        
        return
    
    def set_state_ended(self, cr, uid, ids, context=None):
        
        for period in self.browse(cr, uid, ids, context=context):
            if period.state in ['locked', 'generate']:
                
                employee_ids = []
                for contract in period.schedule_id.contract_ids:
                    if contract.employee_id.id not in employee_ids:
                        employee_ids.append(contract.employee_id.id)
                        
                self.unlock_period(cr, uid, [period], employee_ids, context)
            
            self.write(cr, uid, period.id, {'state': 'ended'}, context=context)
        
        return True
    
    def set_state_locked(self, cr, uid, ids, context=None):
        
        for period in self.browse(cr, uid, ids, context=context):
            
            employee_ids = []
            for contract in period.schedule_id.contract_ids:
                if contract.employee_id.id not in employee_ids:
                    employee_ids.append(contract.employee_id.id)
            
            self.lock_period(cr, uid, [period], employee_ids, context=context)
            
            self.write(cr, uid, period.id, {'state': 'locked'}, context=context)
        
        return True

    def set_state_payment(self, cr, uid, ids, context=None):

        run_obj = self.pool.get('hr.payslip.run')
        slip_obj = self.pool.get('hr.payslip')
        reg_obj = self.pool.get('hr.payroll.register')
        reg_ids = []
        for period in self.browse(cr, uid, ids, context=context):
            run_ids = []
            slip_ids = []
            reg_ids.append(period.register_id.id)
            for ex in period.exception_ids:
                if ex.severity == 'critical' and not ex.accepted:
                    raise osv.except_osv(
                        _('Validation Error'),
                        _('Unaccepted critical exceptions remain in %s.')
                        % (period.name))
            for run in period.register_id.run_ids:
                run_ids.append(run.id)
                for slip in run.slip_ids:
                    slip_ids.append(slip.id)
            slip_obj.hr_verify_sheet(cr, uid, slip_ids, context=context)
            run_obj.close_payslip_run(cr, uid, run_ids, context=context)
        self.set_denominations(cr, uid, ids, context=context)
        reg_obj.write(cr, uid, reg_ids, context=context)
        self.write(cr, uid, ids, {'state': 'payment'}, context=context)

    def set_state_closed(self, cr, uid, ids, context=None):
        
        # When we close a pay period, also de-activate related attendances
        #
        attendance_obj = self.pool.get('hr.attendance')
        for period in self.browse(cr, uid, ids, context=context):
            #
            # XXX - Someone who cares about DST should update this code to handle it.
            #
            utc_tz = timezone('UTC')
            dt = datetime.strptime(period.date_start, '%Y-%m-%d %H:%M:%S')
            utcDtStart = utc_tz.localize(dt, is_dst=False)
            dt = datetime.strptime(period.date_end, '%Y-%m-%d %H:%M:%S')
            utcDtEnd = utc_tz.localize(dt, is_dst=False)
            for contract in period.schedule_id.contract_ids:
                employee = contract.employee_id
                
                # De-activate sign-in and sign-out attendance records
                punch_ids = attendance_obj.search(cr, uid, [
                                                            ('employee_id','=',employee.id),
                                                            '&', ('name','>=', utcDtStart.strftime('%Y-%m-%d %H:%M:%S')),
                                                                 ('name','<=', utcDtEnd.strftime('%Y-%m-%d %H:%M:%S')),
                                                           ], order='name', context=context)
                attendance_obj.write(cr, uid, punch_ids, {'active': False}, context=context)
        
        return self.write(cr, uid, ids, {'state': 'closed'}, context=context)
    
    def create_payslip(self, cr, uid, employee_id, dPeriodStart, dPeriodEnd,
                       payslip_amendments=[], run_id=False, annual_pay_periods=12, context=None):
        
        slip_obj = self.pool.get('hr.payslip')

        found_contracts = []
        dEarliestContractStart = False
        dLastContractEnd = False
        open_contract = False
        ee = self.pool.get('hr.employee').browse(cr, uid, employee_id, context=context)
        for contract in ee.contract_ids:
        
            # Does employee have a contract in this pay period?
            #
            dContractStart = datetime.strptime(contract.date_start, OE_DFORMAT).date()
            dContractEnd = False
            if contract.date_end:
                dContractEnd = datetime.strptime(contract.date_end, OE_DFORMAT).date()
            if dContractStart > dPeriodEnd or (dContractEnd and dContractEnd < dPeriodStart):
                continue
            else:
                found_contracts.append(contract)
                if not dEarliestContractStart or dContractStart < dEarliestContractStart:
                    dEarliestContractStart = dContractStart
                if not dContractEnd:
                    dLastContractEnd = False
                    open_contract = True
                elif not open_contract and dContractEnd and (not dLastContractEnd or dContractEnd > dLastContractEnd):
                    dLastContractEnd = dContractEnd
        
        if len(found_contracts) == 0:
            return False
        
        # If the contract doesn't cover the full pay period use the contract
        # dates as start/end dates instead of the full period.
        #
        period_start_date = dPeriodStart.strftime(OE_DFORMAT)
        period_end_date = dPeriodEnd.strftime(OE_DFORMAT)
        temp_date_start = period_start_date
        temp_date_end = period_end_date
        if dEarliestContractStart > datetime.strptime(period_start_date, OE_DFORMAT).date():
            temp_date_start = dEarliestContractStart.strftime(OE_DFORMAT)
        if dLastContractEnd and dLastContractEnd < datetime.strptime(period_end_date, OE_DFORMAT).date():
            temp_date_end = dLastContractEnd.strftime(OE_DFORMAT)
        
        # If termination procedures have begun within the contract period, use the
        # effective date of the termination as the end date.
        #
        term_obj = self.pool.get('hr.employee.termination')
        term_ids = term_obj.search(cr, uid, [('employee_id', '=', found_contracts[0].employee_id.id),
                                             ('employee_id.status', 'in', ['pending_inactive', 'inactive']),
                                             ('state', 'in', ['draft','confirm', 'done'])],
                                   context=context)
        if len(term_ids) > 0:
            term_data = term_obj.read(cr, uid, term_ids, ['name'], context=context)
            for data in term_data:
                if data['name'] >= temp_date_start and data['name'] < temp_date_end:
                    temp_date_end = data['name']
        
        slip_data = slip_obj.onchange_employee_id(cr, uid, [],
                                                  temp_date_start, temp_date_end,
                                                  ee.id, contract_id=False,
                                                  context=context)
        
        # Make modifications to rule inputs
        #
        for line in slip_data['value'].get('input_line_ids', False):
            
            # Pay Slip Amendment modifications
            for eid, code, amount in payslip_amendments:
                # count the number of times this input rule appears (this
                # is dependent on no. of contracts in pay period), and
                # distribute the total amount equally among them.
                #
                rule_count = 0
                _input_contract_ids =[]
                for _l2 in slip_data['value']['input_line_ids']:
                    if eid == ee.id and _l2['code'] == code and _l2['contract_id'] not in _input_contract_ids:
                        rule_count += 1
                        _input_contract_ids.append(_l2['contract_id'])
                if eid == ee.id and line['code'] == code:
                    if line.get('amount', False):
                        line['amount'] += amount / float(rule_count)
                    else:
                        line['amount'] = amount / float(rule_count)
                    break
        
        month_name, month_no, year_no = get_period_year(dPeriodStart, annual_pay_periods)
        slip_name = _("Pay Slip for %s for %s/%s") % (ee.name, year_no, month_name)
        res = {
            'employee_id': ee.id,
            'name': slip_name,
            'struct_id': slip_data['value'].get('struct_id', False),
            'contract_id': slip_data['value'].get('contract_id', False),
            'payslip_run_id': run_id,
            'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids', False)],
            'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids', False)],
            'date_from': period_start_date,
            'date_to': period_end_date
        }
        
        return slip_obj.create(cr, uid, res, context=context)
    
    def is_payroll_locked(self, cr, uid, employee_id, utcdt_str, context=None):

        lock_obj = self.pool.get('hr.payroll.lock')
        is_locked = lock_obj.is_locked_datetime_utc(cr, uid, utcdt_str,
                                                    context=context)

        return is_locked
    
    def print_payslips(self, cr, uid, ids, context=None):

        p_data = self.pool.get('hr.payroll.period').read(
            cr, uid, ids[0], ['register_id'], context=context)

        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'hr_payroll_register_payslip_report',
            'datas': {'ids': [p_data['register_id'][0]]},
        }

    def print_payroll_summary(self, cr, uid, ids, context=None):

        p_data = self.pool.get('hr.payroll.period').read(
            cr, uid, ids[0], ['register_id'], context=context)

        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'hr.payroll.register.summary',
            'datas': {'ids': [p_data['register_id'][0]]},
        }

    def print_payroll_register(self, cr, uid, ids, context=None):

        p_data = self.pool.get('hr.payroll.period').read(
            cr, uid, ids[0], ['register_id'], context=context)

        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'hr_payroll_register_report2',
            'datas': {'ids': [p_data['register_id'][0]]},
        }

    def print_contribution_registers(self, cr, uid, ids, context=None):

        data = self.pool.get('hr.payroll.period').read(
            cr, uid, ids[0], ['date_start', 'date_end'], context=context)
        register_ids = self.pool.get('hr.contribution.register').\
            search(cr, uid, [], context=context)

        form = {'date_from': data['date_start'],
                'date_to': data['date_end']}

        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'contribution.register.lines',
            'datas': {'ids': register_ids,
                      'form': form,
                      'model': 'hr.contribution.register'},
        }

    def rerun_payslip(self, cr, uid, _id, slip_id, context=None):

        period_obj = self.pool.get('hr.payroll.period')
        psa_obj = self.pool.get('hr.payslip.amendment')
        slip_obj = self.pool.get('hr.payslip')
        slip = slip_obj.browse(cr, uid, slip_id, context=context)
        run = slip.payslip_run_id
        ee = slip.employee_id
        p_data = period_obj.read(
            cr, uid, _id,
            ['company_id', 'name', 'date_start', 'date_end', 'schedule_id',
             'register_id', 'state'], context=context)

        if p_data['state'] in ['payment', 'closed']:
            raise osv.except_osv(
                _('Invalid Action'),
                _('You cannot modify a payroll register once it has been '
                  'marked for payment'))

        if p_data['state'] not in ['open', 'ended', 'locked', 'generate']:
            raise osv.except_osv(
                _('Invalid Action'),
                _('You must lock the payroll period first.'))

        # Get basic data from pay period schedule
        s_data = self.pool.get('hr.payroll.period.schedule').\
            read(cr, uid, p_data['schedule_id'][0],
                 ['annual_pay_periods', 'contract_ids', 'tz'], context=context)

        # DateTime in db is stored as naive UTC. Convert it to explicit UTC
        # and then convert that into the time zone of the pay period schedule.
        #
        local_tz = timezone(s_data['tz'])
        utcDTStart = utc.localize(
                        datetime.strptime(p_data['date_start'], OE_DTFORMAT))
        loclDTStart = utcDTStart.astimezone(local_tz)
        utcDTEnd = utc.localize(datetime.strptime(
                                            p_data['date_end'], OE_DTFORMAT))
        loclDTEnd = utcDTEnd.astimezone(local_tz)

        # Get Pay Slip Amendments, Employee ID, and the amount of the amendment
        #
        psa_codes = []
        psa_ids = psa_obj.search(cr, uid, [('pay_period_id', '=', _id),
                                           ('employee_id', '=', ee.id),
                                           ('state', 'in', ['validate'])],
                                 context=context)
        for psa in self.pool.get('hr.payslip.amendment').browse(
                                            cr, uid, psa_ids, context=context):
            psa_codes.append(
                        (psa.employee_id.id, psa.input_id.code, psa.amount))

        # Remove any pre-existing pay slip
        slip_obj.unlink(cr, uid, [slip.id], context=context)
        slip = None

        # Create a pay slip
        slip_id = period_obj.create_payslip(
            cr, uid, ee.id, loclDTStart.date(), loclDTEnd.date(), psa_codes,
            run.id, s_data['annual_pay_periods'], context=context)

        # Calculate payroll for all the pay slips in this batch (run)
        slip_obj.compute_sheet(cr, uid, [slip_id], context=context)
        period_obj.set_denominations(cr, uid, [_id], context=context)

        return

    def create_payroll_register(self, cr, uid, _id, context=None):

        # Get relevant data from the period object
        period_obj = self.pool.get('hr.payroll.period')
        p_data = period_obj.read(
            cr, uid, _id,
            ['company_id', 'name', 'date_start', 'date_end', 'schedule_id',
             'register_id', 'state'], context=context)

        if p_data['state'] in ['payment', 'closed']:
            raise osv.except_osv(
                _('Invalid Action'),
                _('You cannot modify a payroll register once it has been '
                  'marked for payment'))

        if p_data['state'] not in ['open', 'ended', 'locked', 'generate']:
            raise osv.except_osv(
                _('Invalid Action'),
                _('You must lock the payroll period first.'))

        # Create the payroll register
        register_values = {
            'name': p_data['name'] + ' Payroll Sheet',
            'date_start': p_data['date_start'],
            'date_end': p_data['date_end'],
            'period_id': _id,
            'company_id': p_data['company_id'][0],
        }

        # Get list of departments and list of contracts for this
        # period's schedule
        department_ids = self.pool.get('hr.department').\
            search(cr, uid, [('company_id', '=', p_data['company_id'][0])],
                   context=context)
        s_data = self.pool.get('hr.payroll.period.schedule').\
            read(cr, uid, p_data['schedule_id'][0],
                 ['annual_pay_periods', 'contract_ids', 'tz'], context=context)

        # DateTime in db is stored as naive UTC. Convert it to explicit UTC
        # and then convert that into the time zone of the pay period schedule.
        #
        local_tz = timezone(s_data['tz'])
        utcDTStart = utc.localize(
                        datetime.strptime(p_data['date_start'], OE_DTFORMAT))
        loclDTStart = utcDTStart.astimezone(local_tz)
        utcDTEnd = utc.localize(datetime.strptime(
                                            p_data['date_end'], OE_DTFORMAT))
        loclDTEnd = utcDTEnd.astimezone(local_tz)

        # Create payslips for employees, in all departments, that have
        # a contract in this pay period's schedule
        previous_register_id = p_data['register_id'] \
            and p_data['register_id'][0] or False
        self.create_payslip_runs(
            cr, uid, _id, previous_register_id, register_values,
            department_ids, s_data['contract_ids'],
            loclDTStart.date(), loclDTEnd.date(), s_data['annual_pay_periods'],
            context=context)
        period_obj.set_denominations(cr, uid, [_id], context=context)

        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.payroll.period.end.1',
            'type': 'ir.actions.act_window',
            'target': 'inline',
            'context': context
        }


class hr_payperiod_schedule(osv.osv):
    
    _name = 'hr.payroll.period.schedule'
    
    def _tz_list(self, cr, uid, context=None):
        
        res = tuple()
        for name in common_timezones:
            res += ((name, name),)
        return res
    
    def _calculate_annual_periods(self, cr, uid, ids, field_name, arg, context=None):
        
        res = dict.fromkeys(ids, 0)
        for pps in self.browse(cr, uid, ids, context=context):
            if pps.type == 'manual':
                res[pps.id] = 0
            elif pps.type == 'monthly':
                res[pps.id] = 12
        return res
    
    _columns = {
        'name': fields.char('Description', size=256, required=True),
        'tz': fields.selection(_tz_list, 'Time Zone', required=True),
        'paydate_biz_day': fields.boolean('Pay Date on a Business Day'),
        'ot_week_startday': fields.selection([
                                              ('0', _('Sunday')),
                                              ('1', _('Monday')),
                                              ('2', _('Tuesday')),
                                              ('3', _('Wednesday')),
                                              ('4', _('Thursday')),
                                              ('5', _('Friday')),
                                              ('6', _('Saturday')),
                                             ],
                                             'Start of Week', required=True),
        'ot_max_rollover_hours': fields.integer('OT Max. Continous Hours', required=True),
        'ot_max_rollover_gap': fields.integer('OT Max. Continuous Hours Gap (in Min.)', required=True),
        'type': fields.selection([
                                  ('manual', 'Manual'),
                                  ('monthly', 'Monthly'),
                                 ],
                                 'Type', required=True),
        'annual_pay_periods': fields.function(_calculate_annual_periods, type='integer', string='Annual Pay Periods'),
        'mo_firstday': fields.selection([
                                         ('1', '1'),('2', '2'),('3', '3'),('4', '4'),('5', '5'),('6', '6'),('7', '7'),
                                         ('8', '8'),('9', '9'),('10', '10'),('11', '11'),('12', '12'),('13', '13'),('14', '14'),
                                         ('15', '15'),('16', '16'),('17', '17'),('18', '18'),('19', '19'),('20', '20'),('21', '21'),
                                         ('22', '22'),('23', '23'),('24', '24'),('25', '25'),('26', '26'),('27', '27'),('28', '28'),
                                         ('29', '29'),('30', '30'),('31', '31'),
                                        ],
                                        'Start Day'),
        'mo_paydate': fields.selection([
                                        ('1', '1'),('2', '2'),('3', '3'),('4', '4'),('5', '5'),('6', '6'),('7', '7'),
                                        ('8', '8'),('9', '9'),('10', '10'),('11', '11'),('12', '12'),('13', '13'),('14', '14'),
                                        ('15', '15'),('16', '16'),('17', '17'),('18', '18'),('19', '19'),('20', '20'),('21', '21'),
                                        ('22', '22'),('23', '23'),('24', '24'),('25', '25'),('26', '26'),('27', '27'),('28', '28'),
                                        ('29', '29'),('30', '30'),('31', '31'),
                                       ],
                                       'Pay Date'),
        'contract_ids': fields.one2many('hr.contract', 'pps_id', 'Contracts'),
        'pay_period_ids': fields.one2many('hr.payroll.period', 'schedule_id', 'Pay Periods'),
        'initial_period_date': fields.date('Initial Period Start Date'),
        'active': fields.boolean('Active'),
        'company_ids':fields.many2many('res.company', 'res_paysched_company_rel',
                                       'psched_id', 'cid','Companies'),
    }
    
    _defaults = {
        'ot_week_startday': '1',
        'ot_max_rollover_hours': 6,
        'ot_max_rollover_gap': 60,
        'mo_firstday': '1',
        'mo_paydate': '3',
        'type': 'monthly',
        'active': True,
    }
    
    def _check_initial_date(self, cr, uid, ids, context=None):
        
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.type in ['monthly'] and not obj.initial_period_date:
                return False
        
        return True
    
    _constraints = [
        (_check_initial_date, 'You must supply an Initial Period Start Date', ['type']),
    ]
    
    def button_add_pay_periods(self, cr, uid, ids, context=None):
        
        for sched in self.browse(cr, uid, ids, context=context):
            if len(sched.company_ids) == 0:
                self.add_pay_period(cr, uid, sched.id, context=context)
            else:
                for co in sched.company_ids:
                    self.add_pay_period(cr, uid, sched.id, company_id=co.id, context=context)
        
        return
    
    def add_pay_period(self, cr, uid, sched_id, company_id=None, context=None):
        
        #
        # XXX - Someone who cares about DST should update this code to handle it.
        #
        
        data = None
        sched = self.browse(cr, uid, sched_id, context=context)
        latest = self._get_latest_period(cr, uid, sched.id, company_id=company_id,
                                         context=context)
        local_tz = timezone(sched.tz)
        if not latest:
            # No pay periods have been defined yet for this pay period schedule.
            if sched.type == 'monthly':
                dtStart = datetime.strptime(sched.initial_period_date, '%Y-%m-%d')
                if dtStart.day > int(sched.mo_firstday):
                    dtStart = add_months(dtStart, 1)
                    dtStart = datetime(dtStart.year, dtStart.month, int(sched.mo_firstday), 0, 0, 0)
                elif dtStart.day < int(sched.mo_firstday):
                    dtStart = datetime(dtStart.year, dtStart.month, int(sched.mo_firstday), 0, 0, 0)
                else:
                    dtStart = datetime(dtStart.year, dtStart.month, dtStart.day, 0, 0, 0)
                dtEnd = add_months(dtStart, 1) - timedelta(days=1)
                dtEnd = datetime(dtEnd.year, dtEnd.month, dtEnd.day, 23, 59, 59)
                month_name, month_number, year_number = get_period_year(dtStart, 12)
                
                # Convert from time zone of punches to UTC for storage
                utcStart = local_tz.localize(dtStart, is_dst=None)
                utcStart = utcStart.astimezone(utc)
                utcEnd = local_tz.localize(dtEnd, is_dst=None)
                utcEnd = utcEnd.astimezone(utc)

                data = {
                    'name': 'Pay Period ' + str(month_name) + '/' + str(year_number),
                    'schedule_id': sched.id,
                    'date_start': utcStart.strftime('%Y-%m-%d %H:%M:%S'),
                    'date_end': utcEnd.strftime('%Y-%m-%d %H:%M:%S'),
                    'company_id': company_id != None and company_id or False,
                }
        else:
            if sched.type == 'monthly':
                # Convert from UTC to timezone of punches
                utcStart = datetime.strptime(latest.date_end, '%Y-%m-%d %H:%M:%S')
                utc_tz = timezone('UTC')
                utcStart = utc_tz.localize(utcStart, is_dst=None)
                utcStart += timedelta(seconds=1)
                dtStart = utcStart.astimezone(local_tz)
                
                # Roll forward to the next pay period start and end times
                dtEnd = add_months(dtStart, 1) - timedelta(days=1)
                dtEnd = datetime(dtEnd.year, dtEnd.month, dtEnd.day, 23, 59, 59)
                month_name, month_number, year_number = get_period_year(dtStart, 12)
                
                # Convert from time zone of punches to UTC for storage
                utcStart = dtStart.astimezone(utc_tz)
                utcEnd = local_tz.localize(dtEnd, is_dst=None)
                utcEnd = utcEnd.astimezone(utc)
                
                data = {
                    'name': 'Pay Period ' + str(month_name) + '/' + str(year_number),
                    'schedule_id': sched.id,
                    'date_start': utcStart.strftime('%Y-%m-%d %H:%M:%S'),
                    'date_end': utcEnd.strftime('%Y-%m-%d %H:%M:%S'),
                    'company_id': company_id != None and company_id or False,
                }
        if data != None:
            self.write(cr, uid, sched.id, {'pay_period_ids': [(0, 0, data)]}, context=context)
    
    def _get_latest_period(self, cr, uid, sched_id, company_id=None, context=None):
        
        pp_obj = self.pool.get('hr.payroll.period')
        srch_domain = [('schedule_id', '=', sched_id)]
        if company_id != None:
            srch_domain.append(('company_id', '=', company_id))
        
        pp_ids = pp_obj.search(cr, uid, srch_domain, context=context)
        latest_period = False
        for period in pp_obj.browse(cr, uid, pp_ids, context=context):
            if not latest_period:
                latest_period = period
                continue
            if datetime.strptime(period.date_end, '%Y-%m-%d %H:%M:%S') > datetime.strptime(latest_period.date_end, '%Y-%m-%d %H:%M:%S'):
                latest_period = period
        
        return latest_period
    
    def create_pay_periods_by_company(self, cr, uid, sched, utc_tz, utcDTFuture,
                                      company_id=None, context=None):
        
        if not sched.pay_period_ids:
            self.add_pay_period(cr, uid, sched.id, company_id=company_id, context=context)
        
        latest_period = self._get_latest_period(cr, uid, sched.id, company_id=company_id,
                                                context=context)
        utcDTStart = utc_tz.localize(datetime.strptime(latest_period.date_start, '%Y-%m-%d %H:%M:%S'), is_dst=False)
        while utcDTFuture > utcDTStart:
            self.add_pay_period(cr, uid, sched.id, company_id=company_id, context=context)            
            latest_period = self._get_latest_period(cr, uid, sched.id,
                                                    company_id=company_id, context=context)
            utcDTStart = utc_tz.localize(datetime.strptime(latest_period.date_start, '%Y-%m-%d %H:%M:%S'), is_dst=False)
            
        return
    
    def try_create_new_period(self, cr, uid, context=None):
        '''Try and create pay periods for up to 3 months from now.'''
        
        #
        # XXX - Someone who cares about DST should update this code to handle it.
        #
        
        dtNow = datetime.now()
        utc_tz = timezone('UTC')
        sched_obj = self.pool.get('hr.payroll.period.schedule')
        sched_ids = sched_obj.search(cr, uid, [], context=context)
        for sched in sched_obj.browse(cr, uid, sched_ids, context=context):
            if sched.type == 'monthly':
                firstday = sched.mo_firstday
            else:
                continue
            dtNow = datetime.strptime(dtNow.strftime('%Y-%m-' + firstday + ' 00:00:00'), '%Y-%m-%d %H:%M:%S')
            loclDTNow = timezone(sched.tz).localize(dtNow, is_dst=False)
            utcDTFuture = loclDTNow.astimezone(utc_tz) + relativedelta(months= +3)
            
            if len(sched.company_ids) == 0:
                self.create_pay_periods_by_company(cr, uid, sched, utc_tz,
                                                   utcDTFuture, context=context)
            else:
                for co in sched.company_ids:
                    self.create_pay_periods_by_company(cr, uid, sched, utc_tz, utcDTFuture,
                                                       company_id=co.id, context=context)

class contract_init(osv.Model):
    
    _inherit = 'hr.contract.init'
    
    _columns = {
        'pay_sched_id': fields.many2one('hr.payroll.period.schedule', 'Payroll Period Schedule',
                                        readonly=True, states={'draft': [('readonly', False)]}),
    }

class hr_contract(osv.osv):
    
    _name = 'hr.contract'
    _inherit = 'hr.contract'
    
    _columns = {
        'pps_id': fields.many2one('hr.payroll.period.schedule', 'Payroll Period Schedule', required=True),
    }
    
    def _get_pay_sched(self, cr, uid, context=None):
        
        res = False
        init = self.get_latest_initial_values(cr, uid, context=context)
        if init != None and init.pay_sched_id:
            res = init.pay_sched_id.id
        return res
    
    _defaults = {
        'pps_id': _get_pay_sched,
    }

class hr_payslip(osv.osv):
    
    _name = 'hr.payslip'
    _inherit = 'hr.payslip'
    
    _columns = {
        'exception_ids': fields.one2many('hr.payslip.exception', 'slip_id',
                                         'Exceptions', readonly=True),
    }
    
    def compute_sheet(self, cr, uid, ids, context=None):
        
        super(hr_payslip, self).compute_sheet(cr, uid, ids, context=context)
        
        def _sum_salary_rule_category(localdict, category, amount):
            if category.parent_id:
                localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)
            if category.code in localdict['categories'].dict:
                localdict['categories'].dict[category.code] = localdict['categories'].dict[category.code] + amount
            else:
                localdict['categories'].dict[category.code] = amount
            return localdict
        
        def _sum_salary_rule_line(localdict, line, amount):
            if line.code in localdict['lines'].dict:
                localdict['lines'].dict[line.code] = localdict['lines'].dict[line.code] + amount
            else:
                localdict['lines'].dict[line.code] = amount
            return localdict

        class BrowsableObject(object):
            def __init__(self, pool, cr, uid, employee_id, dict):
                self.pool = pool
                self.cr = cr
                self.uid = uid
                self.employee_id = employee_id
                self.dict = dict

            def __getattr__(self, attr):
                return attr in self.dict and self.dict.__getitem__(attr) or 0.0

        class InputLine(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""
            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = datetime.now().strftime('%Y-%m-%d')
                result = 0.0
                self.cr.execute("SELECT sum(amount) as sum\
                            FROM hr_payslip as hp, hr_payslip_input as pi \
                            WHERE hp.employee_id = %s AND hp.state = 'done' \
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s",
                           (self.employee_id, from_date, to_date, code))
                res = self.cr.fetchone()[0]
                return res or 0.0

        class WorkedDays(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""
            def _sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = datetime.now().strftime('%Y-%m-%d')
                result = 0.0
                self.cr.execute("SELECT sum(number_of_days) as number_of_days, sum(number_of_hours) as number_of_hours\
                            FROM hr_payslip as hp, hr_payslip_worked_days as pi \
                            WHERE hp.employee_id = %s AND hp.state = 'done'\
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s",
                           (self.employee_id, from_date, to_date, code))
                return self.cr.fetchone()

            def sum(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            def sum_hours(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0

        class Payslips(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = datetime.now().strftime('%Y-%m-%d')
                self.cr.execute("SELECT sum(case when hp.credit_note = False then (pl.total) else (-pl.total) end)\
                            FROM hr_payslip as hp, hr_payslip_line as pl \
                            WHERE hp.employee_id = %s AND hp.state = 'done' \
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pl.slip_id AND pl.code = %s",
                            (self.employee_id, from_date, to_date, code))
                res = self.cr.fetchone()
                return res and res[0] or 0.0

        rule_obj = self.pool.get('hr.payslip.exception.rule')
        rule_ids = rule_obj.search(cr, uid, [('active','=',True)], context=context)
        rule_seq = []
        for i in rule_ids:
            data = rule_obj.read(cr, uid, i, ['sequence'], context=context)
            rule_seq.append((i, data['sequence']))
        sorted_rule_ids = [id for id, sequence in sorted(rule_seq, key=lambda x:x[1])]
        
        for payslip in self.browse(cr, uid, ids, context=context):
            payslip_obj = Payslips(self.pool, cr, uid, payslip.employee_id.id, payslip)
            
            categories = {}
            categories_obj = BrowsableObject(self.pool, cr, uid, payslip.employee_id.id, categories)

            payslip_lines = {}
            lines_obj = BrowsableObject(self.pool, cr, uid, payslip.employee_id.id, payslip_lines)
            
            worked_days = {}
            for line in payslip.worked_days_line_ids:
                worked_days[line.code] = line
            worked_days_obj = WorkedDays(self.pool, cr, uid, payslip.employee_id.id, worked_days)
            
            inputs = {}
            for line in payslip.input_line_ids:
                inputs[line.code] = line
            input_obj = InputLine(self.pool, cr, uid, payslip.employee_id.id, inputs)
            
            temp_dict = {}
            utils_dict = self.get_utilities_dict(cr, uid, payslip.contract_id, payslip, context=context)
            for k,v in utils_dict.iteritems():
                k_obj = BrowsableObject(self.pool, cr, uid, payslip.employee_id.id, v)
                temp_dict.update({k: k_obj})
            utils_obj = BrowsableObject(self.pool, cr, uid, payslip.employee_id.id, temp_dict)
            
            localdict = {'categories': categories_obj,
                         'payslip': payslip_obj,
                         'worked_days': worked_days_obj,
                         'inputs': input_obj,
                         'lines': lines_obj,
                         'utils': utils_obj}
            localdict['result'] = None
            
            # Total the sum of the categories
            for line in payslip.details_by_salary_rule_category:
                localdict = _sum_salary_rule_category(localdict, line.salary_rule_id.category_id,
                                                      line.total)

            # Collect the payslip lines
            for line in payslip.line_ids:
                localdict = _sum_salary_rule_line(localdict, line, line.total)
            
            for rule in rule_obj.browse(cr, uid, sorted_rule_ids, context=context):
                if rule_obj.satisfy_condition(cr, uid, rule.id, localdict, context=context):
                    val = {
                        'name': rule.name,
                        'slip_id': payslip.id,
                        'rule_id': rule.id,
                    }
                    self.pool.get('hr.payslip.exception').create(cr, uid, val, context=context)
        
        return True

class hr_payslip_exception(osv.osv):
    
    _name = 'hr.payslip.exception'
    _description = 'Payroll Exception'
    
    _columns = {
        'name':fields.char('Name', size=256, required=True, readonly=True),
        'rule_id': fields.many2one('hr.payslip.exception.rule', 'Rule', ondelete='cascade', readonly=True),
        'slip_id': fields.many2one('hr.payslip', 'Pay Slip', ondelete='cascade', readonly=True),
        'severity': fields.related('rule_id', 'severity', type="char", string="Severity", store=True, readonly=True),
        'accepted': fields.boolean('Accept'),
    }

    _default = {
        'accepted': False,
    }

    def button_accept(self, cr, uid, ids, context=None):

        self.write(cr, uid, ids, {'accepted': True}, context=context)

    def button_unaccept(self, cr, uid, ids, context=None):

        self.write(cr, uid, ids, {'accepted': False}, context=context)

# This is almost 100% lifted from hr_payroll/hr.salary.rule
# I ommitted the parts I don't use.
#
class hr_payslip_exception_rule(osv.osv):
    
    _name = 'hr.payslip.exception.rule'
    _description = 'Rules describing pay slips in an abnormal state'
    
    _columns = {
        'name':fields.char('Name', size=256, required=True),
        'code':fields.char('Code', size=64, required=True),
        'sequence': fields.integer('Sequence', required=True, help='Use to arrange calculation sequence', select=True),
        'active':fields.boolean('Active', help="If the active field is set to false, it will allow you to hide the rule without removing it."),
        'company_id':fields.many2one('res.company', 'Company'),
        'condition_select': fields.selection([('none', 'Always True'), ('python', 'Python Expression')], "Condition Based on", required=True),
        'condition_python':fields.text('Python Condition', readonly=False, help='The condition that triggers the exception.'),
        'severity': fields.selection((
                                      ('low', 'Low'),
                                      ('medium', 'Medium'),
                                      ('high', 'High'),
                                      ('critical', 'Critical'),
                                     ), 'Severity', required=True),
        'note':fields.text('Description'),
    }
    
    _defaults = {
        'active': True,
        'company_id': lambda self, cr, uid, context: self.pool.get('res.company')._company_default_get(cr, uid, 'hr.payslip.exception.rule', context=context),
        'sequence': 5,
        'severity': 'low',
        'condition_select': 'none',
        'condition_python':
'''
# Available variables:
#----------------------
# payslip: object containing the payslips
# contract: hr.contract object
# categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
# worked_days: object containing the computed worked days
# inputs: object containing the computed inputs

# Note: returned value have to be set in the variable 'result'

result = categories.GROSS.amount > categories.NET.amount''',
    }

    def satisfy_condition(self, cr, uid, rule_id, localdict, context=None):
        """
        @param rule_id: id of hr.payslip.exception.rule to be tested
        @param contract_id: id of hr.contract to be tested
        @return: returns True if the given rule match the condition for the given contract. Return False otherwise.
        """
        rule = self.browse(cr, uid, rule_id, context=context)

        if rule.condition_select == 'none':
            return True
        else: #python code
            try:
                eval(rule.condition_python, localdict, mode='exec', nocopy=True)
                return 'result' in localdict and localdict['result'] or False
            except:
                raise osv.except_osv(_('Error!'), _('Wrong python condition defined for payroll exception rule %s (%s).')% (rule.name, rule.code))

class hr_payroll_register(osv.Model):
    
    _inherit = 'hr.payroll.register'
    
    _columns = {
        'period_id': fields.many2one('hr.payroll.period', 'Payroll Period'),
    }

class hr_payslip_run(osv.Model):
    
    _inherit = 'hr.payslip.run'
    
    def _get_confirmed_amendments(self, cr, uid, period_id, context=None):
        
        psa_ids = self.pool.get('hr.payslip.amendment').search(cr, uid, [('pay_period_id', '=', period_id),
                                                                         ('state', 'in', ['validate']),
                                                                        ],
                                                               context=context)
        return psa_ids
    
    def recalculate(self, cr, uid, ids, context=None):
        
        slip_obj = self.pool.get('hr.payslip')
        pp_obj = self.pool.get('hr.payroll.period')
        
        if isinstance(ids, (long, int)):
            ids = [ids]
        
        run = self.browse(cr, uid, ids[0], context=context)
        register_id = run.register_id.id
        period_id = run.register_id.period_id.id
        dept_ids = [d.id for d in run.department_ids]
        
        # Get relevant data from the period object
        p_data = pp_obj.read(cr, uid, period_id,
                                 ['name', 'date_start', 'date_end', 'schedule_id', 'register_id', 'state'],
                                 context=context)
        
        if p_data['state'] not in ['open', 'ended', 'locked', 'generate']:
            raise osv.except_osv(_('Invalid Action'), _('You must lock the payroll period first.'))

        s_data = self.pool.get('hr.payroll.period.schedule').read(cr, uid, p_data['schedule_id'][0],
                                                                  ['annual_pay_periods', 'contract_ids', 'tz'], context=context)
        
        # DateTime in db is stored as naive UTC. Convert it to explicit UTC and then convert
        # that into the time zone of the pay period schedule.
        #
        local_tz = timezone(s_data['tz'])
        utcDTStart = utc.localize(datetime.strptime(p_data['date_start'], OE_DTFORMAT))
        loclDTStart = utcDTStart.astimezone(local_tz)
        utcDTEnd = utc.localize(datetime.strptime(p_data['date_end'], OE_DTFORMAT))
        loclDTEnd = utcDTEnd.astimezone(local_tz)
        
        # Create payslips for employees, in all departments, that have a contract in this
        # pay period's schedule        
        # Remove any pre-existing payroll registers
        for run_id in ids:
            run_data = self.read(cr, uid, run_id, ['slip_ids'], context=context)
            slip_obj.unlink(cr, uid, run_data['slip_ids'], context=context)
            self.create_payslip_runs(cr, uid, period_id, run_id, register_id, dept_ids, s_data['contract_ids'],
                                     loclDTStart.date(), loclDTEnd.date(), s_data['annual_pay_periods'],
                                     context=context)
        
        return True

    def create_payslip_runs(self, cr, uid, period_id, run_id, register_id, dept_ids, contract_ids,
                            date_start, date_end, annual_pay_periods, context=None):
        
        contract_obj = self.pool.get('hr.contract')
        dept_obj = self.pool.get('hr.department')
        ee_obj = self.pool.get('hr.employee')
        slip_obj = self.pool.get('hr.payslip')
        run_obj = self.pool.get('hr.payslip.run')
        pp_obj = self.pool.get('hr.payroll.period')
        
        # Get Pay Slip Amendments, Employee ID, and the amount of the amendment
        #
        psa_codes = []
        psa_ids = self._get_confirmed_amendments(cr, uid, period_id, context=context)
        for psa in self.pool.get('hr.payslip.amendment').browse(cr, uid, psa_ids, context=context):
            psa_codes.append((psa.employee_id.id, psa.input_id.code, psa.amount))
        
        # Keep track of employees that have already been included
        seen_ee_ids = []
        
        # Create payslip batch (run) for each department
        #
        for dept in dept_obj.browse(cr, uid, dept_ids, context=context):
            ee_ids = []
            c_ids = contract_obj.search(cr, uid, [('id', 'in', contract_ids),
                                                  ('date_start', '<=', date_end.strftime(OE_DFORMAT)),
                                                  '|', ('date_end', '=', False),
                                                       ('date_end', '>=', date_start.strftime(OE_DFORMAT)),
                                                  '|', ('department_id.id', '=', dept.id),
                                                       ('employee_id.department_id.id', '=', dept.id),
                                                 ], context=context)
            c2_ids = contract_obj.search(cr, uid, [('id', 'in', contract_ids),
                                                   ('date_start', '<=', date_end.strftime(OE_DFORMAT)),
                                                  '|', ('date_end', '=', False),
                                                       ('date_end', '>=', date_start.strftime(OE_DFORMAT)),
                                                   ('employee_id.status', 'in', ['pending_inactive', 'inactive']),
                                                   '|', ('job_id.department_id.id', '=', dept.id),
                                                        ('end_job_id.department_id.id', '=', dept.id),
                                                  ], context=context)
            _logger.warning('c_ids: %s', c_ids)
            _logger.warning('c2_ids: %s', c2_ids)
            for i in c2_ids:
                if i not in c_ids:
                    c_ids.append(i)
            
            c_data = contract_obj.read(cr, uid, c_ids, ['employee_id'], context=context)
            for data in c_data:
                if data['employee_id'][0] not in ee_ids:
                    ee_ids.append(data['employee_id'][0])

            _logger.warning('ee_ids: %s', ee_ids)
            _logger.warning('Department: %s', dept.complete_name)
            if len(ee_ids) == 0:
                continue
            
            # Alphabetize
            ee_ids = ee_obj.search(cr, uid, [('id', 'in', ee_ids),
                                             '|', ('active', '=', False), ('active', '=', True)],
                                   context=context)
            
            run_res = {
                'name': dept.complete_name,
                'date_start': date_start,
                'date_end': date_end,
                'register_id': register_id,
            }
            run_obj.write(cr, uid, run_id, run_res, context=context)
         
            # Create a pay slip for each employee in each department that has
            # a contract in the pay period schedule of this pay period
            #   
            slip_ids = []
            for ee in ee_obj.browse(cr, uid, ee_ids, context=context):
                
                if ee.id in seen_ee_ids:
                    continue
                
                #_logger.warning('Employee: %s', ee.name)
                slip_id = pp_obj.create_payslip(cr, uid, ee.id, date_start, date_end, psa_codes,
                                                run_id, annual_pay_periods, context=context)
                if slip_id != False:
                    slip_ids.append(slip_id)
                
                seen_ee_ids.append(ee.id)
            
            # Calculate payroll for all the pay slips in this batch (run)
            slip_obj.compute_sheet(cr, uid, slip_ids, context=context)
        
        return
        
class hr_payslip_amendment(osv.osv):
    
    _name = 'hr.payslip.amendment'
    _inherit = 'hr.payslip.amendment'
    
    _columns = {
        'pay_period_id': fields.many2one('hr.payroll.period', 'Pay Period', domain=[('state', 'in', ['open','ended','locked','generate'])], required=False, readonly=True, states={'draft': [('readonly', False)], 'validate': [('readonly', False)]}),
    }

class hr_holidays_status(osv.osv):
    
    _name = 'hr.holidays.status'
    _inherit = 'hr.holidays.status'
    
    _columns = {
        'code': fields.char('Code', size=16, required=True),
    }
    
    _sql_constraints = [('code_unique', 'UNIQUE(code)', 'Codes for leave types must be unique!')]

class hr_attendance(osv.osv):
    
    _name = 'hr.attendance'
    _inherit = 'hr.attendance'
    
    _columns = {
        'active': fields.boolean('Active'),
    }
    
    _defaults = {
        'active': True,
    }

class hr_schedule(osv.osv):

    _inherit = 'hr.schedule'

    def skip_create_detail(self, cr, uid, schedule, dayofweek, dDay,
                           utcdtStart, utcdtEnd, context=None):
        """Override this method in derived classes to say whether the
        described schedule detail should be created or not."""

        plock_obj = self.pool.get('hr.payroll.lock')
        strStart = utcdtStart.strftime(OE_DTFORMAT)
        strEnd = utcdtEnd.strftime(OE_DTFORMAT)
        start_locked = plock_obj.is_locked_datetime_utc(cr, uid, strStart,
                                                        context=context)
        end_locked = plock_obj.is_locked_datetime_utc(cr, uid, strEnd,
                                                        context=context)
        _logger.debug('checking skip_create_detail: %s (%s,%s), %s - %s', dayofweek, start_locked, end_locked, strStart, strEnd)
        if start_locked or end_locked:
            _logger.debug('detail is LOCKED: %s', dayofweek)
            return True

        _logger.debug('detail IS NOT LOCKED: %s', dayofweek)
        return super(hr_schedule, self).skip_create_detail(
            cr, uid, schedule, dayofweek, dDay, utcdtStart, utcdtEnd,
            context=None)
