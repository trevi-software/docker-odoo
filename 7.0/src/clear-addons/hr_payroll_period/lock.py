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
from pytz import common_timezones, timezone, utc

from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT
from openerp.tools.translate import _

class payroll_lock(orm.Model):
    
    _name = 'hr.payroll.lock'
    _description = 'Payroll Lock Object'
    
    def _tz_list(self, cr, uid, context=None):
        
        res = tuple()
        for name in common_timezones:
            res += ((name, name),)
        return res
    
    _columns = {
        'name': fields.char('Name', size=256, required=True),
        'start_time': fields.datetime('Start Time', required=True),
        'end_time': fields.datetime('End Time', required=True),
        'tz': fields.selection(_tz_list, 'Time Zone', required=True),
        'company_id': fields.many2one('res.company', 'Company', select=True, required=True),
    }

    _defaults = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'hr.payroll', context=c),
    }
    
    def is_locked_datetime_utc(self, cr, uid, dt_str, context=None):
        '''Determines whether a DateTime (string) value falls within a locked period.
        The DateTime string is assumed to be a naive UTC (straight from DB).'''
        
        lock_ids = self.search(cr, uid, [('start_time', '<=', dt_str),
                                         ('end_time', '>=', dt_str)], context=context)
        if len(lock_ids) > 0:
            return True
        
        return False
    
    def is_locked_date(self, cr, uid, d_str, tz_str=None, context=None):
        '''Determine if the date (string) is locked. If a time zone is
        specified it will check for midnight according to it, otherwise,
        it is assumed to be UTC'''
        
        dt_str = d_str + ' 00:00:00'
        if tz_str:
            dt_tz = timezone(tz_str)
            dt = datetime.strptime(dt_str, OE_DTFORMAT)
            tzdt = dt_tz.localize(dt, is_dst=False)
            utcdt = tzdt.astimezone(utc)
            dt_str = utcdt.strftime(OE_DTFORMAT)
        
        return self.is_locked_datetime_utc(cr, uid, dt_str, context=context)
    
class hr_attendance(orm.Model):
    
    _inherit = 'hr.attendance'
    
    def is_locked(self, cr, uid, employee_id, utcdt_str, context=None):
        
        lock_obj = self.pool.get('hr.payroll.lock')
        return lock_obj.is_locked_datetime_utc(cr, uid, utcdt_str, context=context)
    
    def is_attendance_locked(self, cr, uid, att_id, context=None):
        '''Determine if the attendance record with id attendance_id falls within
        a locked period'''
        
        att = self.browse(cr, uid, att_id, context=context)
        lock_obj = self.pool.get('hr.payroll.lock')
        return lock_obj.is_locked_datetime_utc(cr, uid, att.name, context=context)
    
    def create(self, cr, uid, vals, context=None):
        
        pp_obj = self.pool.get('hr.payroll.period')
        if pp_obj.is_payroll_locked(cr, uid, vals['employee_id'], vals['name'], context=context):
            ee_data = self.pool.get('hr.employee').read(cr, uid, vals['employee_id'], ['name'],
                                                        context=context)
            raise orm.except_orm(_('The period is Locked!'),
                                 _('You may not add an attendance record to a locked period.\nEmployee: %s\nTime: %s') %(ee_data['name'], vals['name']))
        
        return super(hr_attendance, self).create(cr, uid, vals, context=context)
    
    def unlink(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (long, int)):
            ids = [ids]
        
        for att in self.browse(cr, uid, ids, context=context):
            if self.is_attendance_locked(cr, uid, att.id, context=context) and not (context and context.get('force_delete', False)):
                raise orm.except_orm(_('The Record cannot be deleted!'),
                                     _('You may not delete a record that is locked:\nEmployee: %s, Date: %s, Action: %s') %(att.employee_id.name, att.name, att.action))
        
        return super(hr_attendance, self).unlink(cr, uid, ids, context=context)
    
    def write(self, cr, uid, ids, vals, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        for att in self.browse(cr, uid, ids, context=context):
            if self.is_attendance_locked(cr, uid, att.id, context=context) and (vals.get('name', False) or vals.get('action', False) or vals.get('employee_id', False)):
                raise orm.except_orm(_('The record cannot be modified!'),
                                     _('You may not write to a record that is locked:\nEmployee: %s, Date: %s, Action: %s') %(att.employee_id.name, att.name, att.action))
        
        return super(hr_attendance, self).write(cr, uid, ids, vals, context=context)

class hr_schedule(orm.Model):
    
    _inherit = 'hr.schedule'
    
    def is_schedule_locked(self, cr, uid, sched_id, context=None):
        '''Determine if the schedule record with id sched_id falls within
        a locked period'''
        
        sched = self.browse(cr, uid, sched_id, context=context)
        lock_obj = self.pool.get('hr.payroll.lock')
        tz_str = sched.template_id.series_id.tz and sched.template_id.series_id.tz or False
        start_lock = lock_obj.is_locked_date(cr, uid, sched.date_start, tz_str=tz_str, context=context)
        end_lock = lock_obj.is_locked_date(cr, uid, sched.date_end, tz_str=tz_str, context=context)
        
        return (start_lock or end_lock)
    
    def deletable(self, cr, uid, sched_id, context=None):
        
        res = super(hr_schedule, self).deletable(cr, uid, sched_id, context=context)
        
        if self.is_schedule_locked(cr, uid, sched_id, context=context) and not (context and context.get('force_delete', False)):
            res = False
        
        return res
    
    def _check_modify(self, cr, uid, ids, vals=None, context=None):
        
        if isinstance(ids, (long, int)):
            ids = [ids]
        
        for sched in self.browse(cr, uid, ids, context=context):
            if self.is_schedule_locked(cr, uid, sched.id, context=context) and not (context and context.get('force_delete', False)):
                raise orm.except_orm(_('The record cannot be modified or deleted!'),
                                     _('You may not change a record that is locked:\nEmployee: %s, Start: %s') %(sched.employee_id.name, sched.date_start))
        
        return
    
    def create(self, cr, uid, vals, context=None):

        # Do not allow creation if it is locked for the entire schedule.
        # However, if a portion of it is *NOT* locked allow the creation
        # of the schedule and let the check in the individual schedule details
        # deal with which specific dates are allowed to be created.
        #
        pp_obj = self.pool.get('hr.payroll.period')
        if pp_obj.is_payroll_locked(
            cr, uid, vals['employee_id'], vals['date_start'], context=context) \
           and pp_obj.is_payroll_locked(
                cr, uid, vals['employee_id'], vals['date_end'], context=context):
            ee_data = self.pool.get('hr.employee').read(cr, uid, vals['employee_id'], ['name'],
                                                        context=context)
            raise orm.except_orm(_('The period is Locked!'),
                                 _('You may not add a schedule to a locked period.\nEmployee: %s\nTime: %s - %s') %(ee_data['name'], vals['date_start'], vals['date_end']))
        
        return super(hr_schedule, self).create(cr, uid, vals, context=context)
    
    def write(self, cr, uid, ids, vals, context=None):
        
        self._check_modify(cr, uid, ids, vals=vals, context=context)
        return super(hr_schedule, self).write(cr, uid, ids, vals, context=context)
    
    def unlink(self, cr, uid, ids, context=None):
        
        self._check_modify(cr, uid, ids, context=context)
        return super(hr_schedule, self).unlink(cr, uid, ids, context=context)

    def skip_create_detail(self, cr, uid, schedule, dayofweek, dDay,
                           utcdtStart, utcdtEnd, context=None):
        """Override this method in derived classes to say whether the
        described schedule detail should be created or not."""

        res = super(hr_schedule, self).skip_create_detail(
            cr, uid, schedule, dayofweek, dDay, utcdtStart, utcdtEnd,
            context=context)

        # If some other module wants to prevent creation of this detail
        # do not process any further
        if res:
            return res

        lock_obj = self.pool.get('hr.payroll.lock')
        start_lock = lock_obj.is_locked_datetime_utc(
            cr, uid, utcdtStart.strftime(OE_DTFORMAT), context=context)
        end_lock = lock_obj.is_locked_datetime_utc(
            cr, uid, utcdtEnd.strftime(OE_DTFORMAT), context=context)
        return (start_lock or end_lock)


class hr_schedule_detail(orm.Model):
    
    _inherit = 'hr.schedule.detail'
    
    def is_detail_locked(self, cr, uid, det_id, context=None):
        '''Determine if the schedule detail with id det_id falls within
        a locked period'''
        
        lock_obj = self.pool.get('hr.payroll.lock')
        detail = self.browse(cr, uid, det_id, context=context)
        start_lock = lock_obj.is_locked_datetime_utc(cr, uid, detail.date_start, context=context)
        end_lock = lock_obj.is_locked_datetime_utc(cr, uid, detail.date_end, context=context)
        
        return (start_lock or end_lock)
    
    def deletable(self, cr, uid, detail_id, context=None):
        
        res = super(hr_schedule_detail, self).deletable(cr, uid, detail_id, context=context)
        
        if self.is_detail_locked(cr, uid, detail_id, context=context) and not (context and context.get('force_delete', False)):
            res = False
        
        return res
    
    def _check_modify(self, cr, uid, ids, vals=None, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        for detail in self.browse(cr, uid, ids, context=context):
            if self.is_detail_locked(cr, uid, detail.id, context=context) and not (context and context.get('force_delete', False)):
                raise orm.except_orm(_('The record cannot be modified or deleted!'),
                                     _('You may not change a record that is locked:\nEmployee: %s, Start: %s') %(detail.schedule_id.employee_id.name, detail.date_start))
        
        return
    
    def create(self, cr, uid, vals, context=None):
        
        pp_obj = self.pool.get('hr.payroll.period')
        sched = self.pool.get('hr.schedule').browse(cr, uid, vals['schedule_id'], context=context)
        if pp_obj.is_payroll_locked(cr, uid, sched.employee_id.id, vals['date_start'], context=context):
            raise orm.except_orm(_('The period is Locked!'),
                                 _('You may not add a schedule day to a locked period.\nEmployee: %s\nTime: %s') %(sched.employee_id.name, vals['date_start']))
        elif pp_obj.is_payroll_locked(cr, uid, sched.employee_id.id, vals['date_end'], context=context):
            raise orm.except_orm(_('The period is Locked!'),
                                 _('You may not add a schedule day to a locked period.\nEmployee: %s\nTime: %s') %(sched.employee_id.id, vals['date_end']))
        
        return super(hr_schedule_detail, self).create(cr, uid, vals, context=context)
    
    def write(self, cr, uid, ids, vals, context=None):
        
        self._check_modify(cr, uid, ids, vals=vals, context=context)
        return super(hr_schedule_detail, self).write(cr, uid, ids, vals, context=context)
    
    def unlink(self, cr, uid, ids, context=None):
        
        self._check_modify(cr, uid, ids, context=context)
        return super(hr_schedule_detail, self).unlink(cr, uid, ids, context=context)

class hr_holidays(orm.Model):
    
    _inherit = 'hr.holidays'
    
    def is_holiday_locked(self, cr, uid, lv_id, context=None):
        '''Determine if the leave record with id lv_id falls within
        a locked period'''
        
        lv = self.browse(cr, uid, lv_id, context=context)
        lock_obj = self.pool.get('hr.payroll.lock')
        start_lock = lock_obj.is_locked_datetime_utc(cr, uid, lv.date_from, context=context)
        end_lock = lock_obj.is_locked_datetime_utc(cr, uid, lv.date_to, context=context)
        
        return (start_lock or end_lock)
    
    def _check_modify(self, cr, uid, ids, vals=None, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        for lv in self.browse(cr, uid, ids, context=context):
            if self.is_holiday_locked(cr, uid, lv.id, context=context):
                raise orm.except_orm(_('The record cannot be modified or deleted!'),
                                     _('You may not change a record that is locked:\nEmployee: %s, Start: %s') %(lv.employee_id.name, lv.date_from))
        
        return
    
    def create(self, cr, uid, vals, context=None):
        
        pp_obj = self.pool.get('hr.payroll.period')
        if vals.get('type', False) and vals.get('type') == 'remove':
            if pp_obj.is_payroll_locked(cr, uid, vals['employee_id'], vals['date_from'], context=context):
                ee_data = self.pool.get('hr.employee').read(cr, uid, vals['employee_id'], ['name'],
                                                            context=context)
                raise orm.except_orm(_('The period is Locked!'),
                                     _('You may not add a leave to a locked period.\nEmployee: %s\nTime: %s') %(ee_data['name'], vals['date_from']))
            elif pp_obj.is_payroll_locked(cr, uid, vals['employee_id'], vals['date_to'], context=context):
                ee_data = self.pool.get('hr.employee').read(cr, uid, vals['employee_id'], ['name'],
                                                            context=context)
                raise orm.except_orm(_('The period is Locked!'),
                                     _('You may not add a leave to a locked period.\nEmployee: %s\nTime: %s') %(ee_data['name'], vals['date_to']))
        
        return super(hr_holidays, self).create(cr, uid, vals, context=context)
    
    def write(self, cr, uid, ids, vals, context=None):
        
        self._check_modify(cr, uid, ids, vals=vals, context=context)
        return super(hr_holidays, self).write(cr, uid, ids, vals, context=context)
    
    def unlink(self, cr, uid, ids, context=None):
        
        self._check_modify(cr, uid, ids, context=context)
        return super(hr_holidays, self).unlink(cr, uid, ids, context=context)
