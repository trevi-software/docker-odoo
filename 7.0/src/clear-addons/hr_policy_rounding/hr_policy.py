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
from dateutil.relativedelta import relativedelta
from pytz import common_timezones, timezone, utc

import openerp.addons.decimal_precision as dp
from openerp import netsvc
from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT
from openerp.tools.translate import _

class hr_policy(orm.Model):
    
    _name = 'hr.policy.rounding'
    _description = 'Attendance Rounding Policy'
    
    def _tz_list(self, cr, uid, context=None):
        
        res = tuple()
        for name in common_timezones:
            res += ((name, name),)
        return res
    
    _columns = {
        'name': fields.char('Name', size=128, required=True),
        'date': fields.date('Effective Date', required=True),
        'tz': fields.selection(_tz_list, 'Time Zone', required=True),
        'line_ids': fields.one2many('hr.policy.line.rounding', 'policy_id', 'Policy Lines'),
    }
    
    # Return records with latest date first
    _order = 'date desc'
    
    def get_latest_policy(self, cr, uid, policy_group, dToday, context=None):
        '''Return a rounding policy with an effective date before dToday but
        greater than all the others'''
        
        if not policy_group or not policy_group.rounding_policy_ids or not dToday:
            return None
        
        res = None
        for policy in policy_group.rounding_policy_ids:
            dPolicy = datetime.strptime(policy.date, OE_DFORMAT).date()
            if dPolicy <= dToday:
                if res == None:
                    res = policy
                elif dPolicy > datetime.strptime(res.date, OE_DFORMAT).date():
                    res = policy
        
        return res

class policy_line(orm.Model):
    
    _name = 'hr.policy.line.rounding'
    _description = 'Attendance Rounding Policy Line'
    
    _columns = {
        'policy_id': fields.many2one('hr.policy.rounding', 'Policy'),
        'attendance_type': fields.selection([('in', 'Sign-in'),
                                             ('out', 'Sign-out')],
                                            'Attendance Type', required=True),
        'grace': fields.integer('Grace Period'),
        'round_interval': fields.integer('Round Interval'),
        'round_type': fields.selection([('up', 'Up'), ('down', 'Down'), ('avg', 'Average')],
                                       'Round Type', required=True),
        'preauth_ot': fields.boolean('Pre-authorized OT'),
    }
    
    _rec_name = 'attendance_type'
    
    _sql_constraints = [('uniq_id_att_type', 'UNIQUE(id,attendance_type)',
                         _('Attendance types must be unique per rounding policy line'))]

class policy_group(orm.Model):
    
    _name = 'hr.policy.group'
    _inherit = 'hr.policy.group'
    
    _columns = {
        'rounding_policy_ids': fields.many2many('hr.policy.rounding', 'hr_policy_group_rounding_rel',
                                                'group_id', 'rounding_id', 'Rounding Policy'),
    }

class hr_contract(orm.Model):
    
    _inherit = 'hr.contract'
    
    def get_contract_by_date(self, cr, uid, ee_id, d, context=None):

        con_ids = self.search(cr, uid,
                              [('employee_id', '=', ee_id),
                               ('date_start', '<=', d.strftime(OE_DFORMAT)),
                               '|', ('date_end', '=', False),
                                    ('date_end', '>=', d.strftime(OE_DFORMAT))],
                              context=context)

        if len(con_ids) > 0:
            con = self.browse(cr, uid, con_ids[0])
            return con
        else:
            return False

class hr_attendance(orm.Model):
    
    _inherit = 'hr.attendance'
    
    _columns = {
        'clock_time': fields.datetime('Clock Time', readonly=True),
    }

    def _get_schedule(self, cr, uid, ee_id, d, contract, context=None):
        
        sched_hours = []
        if contract:
            detail_obj = self.pool.get('hr.schedule.detail')
            sched_hours = detail_obj.scheduled_begin_end_times(cr, uid, ee_id,
                                                               contract.id, d,
                                                               context=context)
        return sched_hours
    
    def _get_closest_approximation(self, action, dt, sched_times):
        
        leftDelta = relativedelta(hours= -12)
        rightDelta = relativedelta(hours= +12)
        dtBottom = dt + leftDelta
        dtTop = dt + rightDelta
        
        bestDelta = False
        for dtIn, dtOut in  sched_times:
            if action == 'sign_in':
                _dt = dtIn
                if dtIn == dt:
                    # exact match
                    return (relativedelta(dtIn, dt), sched_times)
                elif dtBottom <= dtIn and dtIn <= dt:
                    _delta = relativedelta(dt, dtIn)
                    if not bestDelta or (_delta < bestDelta):
                        bestDelta = _delta
                elif dt <= dtIn and dtIn <= dtTop:
                    _delta = relativedelta(dtIn, dt)
                    if not bestDelta or (_delta < bestDelta):
                        bestDelta = _delta
            elif action == 'sign_out':
                _dt = dtOut
                if dtOut == dt:
                    # exact match
                    return (relativedelta(dtOut, dt), sched_times)
                elif dtBottom <= dtOut and dtOut <= dt:
                    _delta = relativedelta(dt, dtOut)
                    if not bestDelta or (_delta < bestDelta):
                        bestDelta = _delta
                elif dt <= dtOut and dtOut <= dtTop:
                    _delta = relativedelta(dtOut, dt)
                    if not bestDelta or (_delta < bestDelta):
                        bestDelta = _delta
        
        return (bestDelta, sched_times)
    
    def _get_schedule_by_approximation(self, cr, uid, ee_id, action, utcdt, contract, context=None):
        
        # Since we don't know which dayofweek this particular time will fall on in
        # the schedule we have to look one day back and one day forward and
        # search for a similar scheduled punch of the same type and within a 
        # reasonable approximation of the actual punch time.
        
        utcdtBack = utcdt + relativedelta(days= -1)
        utcdtForward = utcdt + relativedelta(days= +1)
        
        schedBack = self._get_schedule(cr, uid, ee_id, utcdtBack.date(), contract, context=context)
        schedNow = self._get_schedule(cr, uid, ee_id, utcdt.date(), contract, context=context)
        schedForward = self._get_schedule(cr, uid, ee_id, utcdtForward.date(), contract, context=context)
        
        deltaBack = self._get_closest_approximation(action, utcdt, schedBack)
        deltaNow = self._get_closest_approximation(action, utcdt, schedNow)
        deltaForward = self._get_closest_approximation(action, utcdt, schedForward)
        sched_list = []
        for _e in [deltaBack, deltaNow, deltaForward]:
            if _e[0]:
                sched_list.append(_e)
        
        best = False
        for delta, sched in sched_list:
            if not best or delta < best[0]:
                best = (delta, sched)
        
        if not best:
            return schedNow
        
        return best[1]
    
    def process_rounding_policy(self, cr, uid, utcdt, rp, vals, sched_times,
                                context=None):
        
        new_time = False
        for line in rp.line_ids:
            
            # 1. Check if this is an entry type that applies to this line
            #
            if (line.attendance_type == 'in') and (vals['action'] != 'sign_in'):
                continue
            elif (line.attendance_type == 'out') and (vals['action'] != 'sign_out'):
                continue
            
            # 2. Check if it's within the grace period
            #
            in_grace = False
            if len(sched_times) > 0:
                count = 0
                for utcdtIn, utcdtOut in sched_times:
                    if line.attendance_type == 'in':
                        if (utcdtIn < utcdt)                                         \
                          and (count == 0 or (utcdtIn >= sched_times[count - 1][1])) \
                          and (utcdtIn + timedelta(minutes= +(line.grace))) > utcdt:
                            in_grace = True
                            new_time = utcdtIn.strftime(OE_DTFORMAT)
                            break
                    if line.attendance_type == 'out':
                        if (utcdtOut > utcdt) \
                          and (utcdtOut + timedelta(minutes= -(line.grace))) < utcdt:
                            in_grace = True
                            new_time = utcdtOut.strftime(OE_DTFORMAT)
                            break;
                    count += 1
            if in_grace:
                continue
            
            # 3. Check if OT has to be pre-authorized
            #
            in_preauth_ot = False
            if line.preauth_ot and len(sched_times) > 0:
                count = 0
                for utcdtIn, utcdtOut in sched_times:
                    if line.attendance_type == 'in' and vals['action'] == 'sign_in':
                        if utcdt < utcdtIn \
                          and (count == 0 or (utcdt >= sched_times[count - 1][1])):
                            in_preauth_ot = True
                            new_time = utcdtIn.strftime(OE_DTFORMAT)
                            break
                    
                    if line.attendance_type == 'out' and vals['action'] == 'sign_out':
                        if (utcdt > utcdtOut) \
                          and (count == (len(sched_times) - 1) or utcdt <= sched_times[count + 1][0]):
                            in_preauth_ot = True
                            new_time = utcdtOut.strftime(OE_DTFORMAT)
                            break
                    
                    count += 1
            if in_preauth_ot:
                continue
            
            # 4. Do any rounding specified
            #
            if line.round_interval > 0:
                
                if line.attendance_type == 'in' and vals['action'] == 'sign_in':
                    for utcdtIn, utcdtOut in sched_times:
                        
                        # Sign-in: punch time is less than scheduled time
                        if utcdt <= utcdtIn:
                            if line.round_type in ['down', 'avg'] and not line.preauth_ot:
                                utcdtBottom = utcdtIn
                                while utcdtBottom > utcdt:
                                    utcdtBottom += timedelta(minutes= -(line.round_interval))
                            if line.round_type in ['up', 'avg']:
                                utcdtPrevTop = utcdtIn
                                utcdtTop = utcdtIn
                                while utcdtTop >= utcdt:
                                    utcdtPrevTop = utcdtTop
                                    utcdtTop += timedelta(minutes= -(line.round_interval))
                                utcdtTop = utcdtPrevTop
                        
                        # Sign-in: punch time is greater than scheduled time
                        if (utcdt > utcdtIn) and (utcdt < utcdtOut):
                            if line.round_type in ['down', 'avg']:
                                utcdtPrevBottom = utcdtIn
                                utcdtBottom = utcdtIn
                                while utcdtBottom <= utcdt:
                                    utcdtPrevBottom = utcdtBottom
                                    utcdtBottom += timedelta(minutes= +(line.round_interval))
                                utcdtBottom = utcdtPrevBottom
                            if line.round_type in ['up', 'avg']:
                                utcdtTop = utcdtIn
                                while utcdtTop < utcdt:
                                    utcdtTop += timedelta(minutes= +(line.round_interval))
                        
                    # Calculate the new rounded time
                    if line.round_type == 'down':
                        new_time = utcdtBottom.strftime(OE_DTFORMAT)
                    elif line.round_type == 'up':
                        new_time = utcdtTop.strftime(OE_DTFORMAT)
                    elif line.round_type == 'avg':
                        delta = relativedelta(utcdtTop, utcdtBottom)
                        deltaS = 0
                        deltaS1 = ((float(delta.minutes) * 100.0) / 2.0) / 100.0
                        deltaS += int(deltaS1 * 60.0)
                        deltaM = delta.minutes // 2
                        deltaM1 = ((float(delta.hours) * 100.0) / 2.0) / 100.0
                        deltaM += int(deltaM1 * 60.0)
                        deltaH = delta.hours / 2
                        delta = relativedelta(hours= +(deltaH), minutes= +(deltaM), seconds= +(deltaS))
                        utcdtMiddle = utcdtBottom + delta
                        new_time = (utcdt < utcdtMiddle)                  \
                                    and utcdtBottom.strftime(OE_DTFORMAT) \
                                    or utcdtTop.strftime(OE_DTFORMAT)
                    
                    break
                
                if line.attendance_type == 'out' and vals['action'] == 'sign_out':
                    count = 0
                    for utcdtIn, utcdtOut in sched_times:
                        
                        # Sign-out: punch time is less than scheduled time
                        if utcdt <= utcdtOut:
                            if line.round_type in ['down', 'avg'] and not line.preauth_ot:
                                utcdtBottom = utcdtOut
                                while utcdtBottom > utcdt:
                                    utcdtBottom += timedelta(minutes= -(line.round_interval))
                            if line.round_type in ['up', 'avg']:
                                utcdtPrevTop = utcdtOut
                                utcdtTop = utcdtOut
                                while utcdtTop >= utcdt:
                                    utcdtPrevTop = utcdtTop
                                    utcdtTop += timedelta(minutes= -(line.round_interval))
                                utcdtTop = utcdtPrevTop
                        
                        # Sign-out: punch time is greater than scheduled time
                        if (utcdt > utcdtOut) and ((count == len(sched_times) - 1) or utcdt < sched_times[count + 1][0]):
                            if line.round_type in ['down', 'avg']:
                                utcdtPrevBottom = utcdtIn
                                utcdtBottom = utcdtIn
                                while utcdtBottom <= utcdt:
                                    utcdtPrevBottom = utcdtBottom
                                    utcdtBottom += timedelta(minutes= +(line.round_interval))
                                utcdtBottom = utcdtPrevBottom
                            if line.round_type in ['up', 'avg']:
                                utcdtTop = utcdtIn
                                while utcdtTop < utcdt:
                                    utcdtTop += timedelta(minutes= +(line.round_interval))
                        
                        count += 1
                    
                    # Calculate the new rounded time
                    if line.round_type == 'down':
                        new_time = utcdtBottom.strftime(OE_DTFORMAT)
                    elif line.round_type == 'up':
                        new_time = utcdtTop.strftime(OE_DTFORMAT)
                    elif line.round_type == 'avg':
                        delta = relativedelta(utcdtTop, utcdtBottom)
                        deltaS = 0
                        deltaS1 = ((float(delta.minutes) * 100.0) / 2.0) / 100.0
                        deltaS += int(deltaS1 * 60.0)
                        deltaM = delta.minutes // 2
                        deltaM1 = ((float(delta.hours) * 100.0) / 2.0) / 100.0
                        deltaM += int(deltaM1 * 60.0)
                        deltaH = delta.hours / 2
                        delta = relativedelta(hours= +(deltaH), minutes= +(deltaM), seconds= +(deltaS))
                        utcdtMiddle = utcdtBottom + delta
                        new_time = (utcdt < utcdtMiddle)                  \
                                    and utcdtBottom.strftime(OE_DTFORMAT) \
                                    or utcdtTop.strftime(OE_DTFORMAT)
                    
                    break
        
        return new_time
    
    def _get_localized_date(self, cr, uid, ee_id, utcdt, context=None):
        
        res = False
        contract = self.pool.get('hr.contract').get_contract_by_date(cr, uid, ee_id, utcdt.date(),
                                                                     context=context)
        if contract:
            rp_obj = self.pool.get('hr.policy.rounding')
            rp = rp_obj.get_latest_policy(cr, uid, contract.policy_group_id, utcdt.date(),
                                          context=context)
            res = utc.localize(utcdt).astimezone(timezone(rp.tz))
            res = res.replace(tzinfo=None)
            
        if not res:
            res = utcdt
        
        return res
    
    def create(self, cr, uid, vals, context=None):
        
        contract = False
        rp = None
        if vals.get('name', False):
            vals.update({'clock_time': vals['name']})
            utcdt = datetime.strptime(vals['name'], OE_DTFORMAT)
            dt = self._get_localized_date(cr, uid, vals['employee_id'], utcdt, context=context)
            contract = self.pool.get('hr.contract').get_contract_by_date(cr, uid,
                                                                         vals['employee_id'],
                                                                         dt.date(),
                                                                         context=context)
            if contract:
                rp_obj = self.pool.get('hr.policy.rounding')
                rp = rp_obj.get_latest_policy(cr, uid, contract.policy_group_id, dt.date(),
                                              context=context)
        if rp != None:
            sched_times = self._get_schedule_by_approximation(cr, uid, vals['employee_id'],
                                                              vals['action'], utcdt, contract,
                                                              context=context)
            if sched_times:
                new_time = self.process_rounding_policy(cr, uid, utcdt, rp, vals.copy(), sched_times,
                                                        context=context)
                if new_time:
                    vals.update({'name': new_time})
        
        return super(hr_attendance, self).create(cr, uid, vals, context=context)
