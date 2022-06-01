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

from datetime import datetime, timedelta

from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT
from openerp.tools.translate import _

import logging
_l = logging.getLogger(__name__)

class attendance_punch_wizard(orm.TransientModel):
    
    _name = 'hr.attendance.weekly.prefill'
    _description = 'Weekly Attendance Pre-Fill'
    
    _columns = {
        'department_ids': fields.many2many('hr.department',
                                           'hr_attendance_weekly_prefill_department_rel',
                                           'wizard_id', 'department_id', 'Department'),
        'week_start': fields.date('Start Week', required=True),
        'week_end': fields.date('End Week', required=True),
        'do_recreate': fields.boolean('Re-Create Existing',
                                      help=_('Check to re-create any existing weekly attendances')),
        'do_punches': fields.boolean('Create Attendance Records',
                                     help=_('Create daily attendance records for each weekly record'))
    }
    
    _defaults = {
        'do_punches': True,
    }
    
    def onchange_week_start(self, cr, uid, ids, newdate, context=None):
        
        return {'value': {'week_start': self.check_week_date(newdate)}}
    
    def onchange_week_end(self, cr, uid, ids, newdate, context=None):
        
        return {'value': {'week_end': self.check_week_date(newdate)}}
    
    def check_week_date(self, newdate):
        '''Returns newdate if it falls on a Monday; False otherwise.'''
        
        res = False
        if newdate:
            d = datetime.strptime(newdate, "%Y-%m-%d")
            if d.weekday() == 0:
                res = newdate
        return res
    
    def create_weekly(self, cr, uid, ids, context=None):
        
        weekly_obj = self.pool.get('hr.attendance.weekly')
        
        wizard = self.browse(cr, uid, ids[0], context=context)
        dept_ids = [dept.id for dept in wizard.department_ids]
        pre_existing = dict.fromkeys(dept_ids, False)
        weekly_ids = weekly_obj.search(cr, uid, [('department_id', 'in', dept_ids),
                                                 '&', ('week_start', '>=', wizard.week_start),
                                                      ('week_start', '<=', wizard.week_end)],
                                       context=context)
        _l.warning('1. weekly_ids: %s', weekly_ids)
        for weekly in weekly_obj.browse(cr, uid, weekly_ids, context=context):
            
            if not pre_existing[weekly.department_id.id]:
                pre_existing[weekly.department_id.id] = [weekly.week_start]
            else:
                pre_existing[weekly.department_id.id].append(weekly.week_start)
        
        for d_id in dept_ids:
            
            dWeek = datetime.strptime(wizard.week_start, OE_DFORMAT).date()
            dWeekEnd = datetime.strptime(wizard.week_end, OE_DFORMAT).date()
            _l.warning('Pre-existing: %s: %s', d_id, pre_existing[d_id])
            while dWeek <= dWeekEnd:
                
                _l.warning('Week: %s', dWeek.strftime(OE_DFORMAT))
                # If the user hasn't specifically chosen so, don't re-create weekly attendance if
                # it already exists.
                #
                if not wizard.do_recreate and pre_existing[d_id] and dWeek.strftime(OE_DFORMAT) in pre_existing[d_id]:
                    dWeek = dWeek + timedelta(days= +7)
                    continue
                
                weekly_id = False
                new_weekly = False
                if not pre_existing[d_id] or dWeek.strftime(OE_DFORMAT) not in pre_existing[d_id]:
                    # Create weekly attendance
                    vals = {
                        'department_id': d_id,
                        'week_start': dWeek.strftime(OE_DFORMAT)
                    }
                    weekly_id = weekly_obj.create(cr, uid, vals, context=context)
                    new_weekly = True
                else:
                    weekly_id = weekly_obj.search(cr, uid, [('department_id', '=', d_id),
                                                            ('week_start', '=', dWeek.strftime(OE_DFORMAT))],
                                                  context=context)[0]
                
                _l.warning('weekly_id: %s', weekly_id)
                # Do not create a record if the department does not have any employees
                #
                ee_ids = weekly_obj.get_employees(cr, uid,
                                                  weekly_obj.browse(cr, uid, weekly_id, context=context),
                                                  context=context)
                if len(ee_ids) == 0 and new_weekly:
                    _l.warning('unlink()')
                    weekly_obj.unlink(cr, uid, weekly_id, context=context)
                else:
                    # Create punches from weekly attendance
                    if wizard.do_punches:
                        weekly_obj.action_delete_hours(cr, uid, [weekly_id], context=context)
                        week_vals = weekly_obj.get_weekly_lines(cr, uid, weekly_id, context=context)
                        weekly_obj.add_records(cr, uid, weekly_id, week_vals, context=context)
                        weekly_obj.write(cr, uid, weekly_id, {'init_time': datetime.now().strftime(OE_DTFORMAT)},
                                   context=context)
                        _l.warning('in punches...')
                
                weekly_obj.clear_caches()
                if wizard.do_punches:
                    self.pool.get('hr.attendance').clear_caches()
            
                dWeek = dWeek + timedelta(days= +7)
        
        return {'type': 'ir.actions.act_window_close'}
            