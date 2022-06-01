#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2011 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT

class attendance_punch_wizard(orm.TransientModel):
    
    _name = 'hr.attendance.weekly.punch.wizard'
    _description = 'Weekly Attendance Punch Wizard'
    
    _columns = {
        'department_ids': fields.many2many('hr.department',
                                           'hr_attendance_weekly_punches_department_rel',
                                           'wizard_id', 'department_id', 'Department'),
        'week_start': fields.date('Start Week', required=True),
        'week_end': fields.date('End Week', required=True),
        'do_recreate': fields.boolean('Re-Create Existing Punches?'),
    }
    
    _defaults = {
        'do_recreate': True,
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
    
    def create_punches(self, cr, uid, ids, context=None):
        
        weekly_obj = self.pool.get('hr.attendance.weekly')
        
        wizard = self.browse(cr, uid, ids[0], context=context)
        dept_ids = [dept.id for dept in wizard.department_ids]
        weekly_ids = weekly_obj.search(cr, uid, [('department_id', 'in', dept_ids),
                                                 '&', ('week_start', '>=', wizard.week_start),
                                                      ('week_start', '<=', wizard.week_end)],
                                       context=context)
        
        for weekly in weekly_obj.browse(cr, uid, weekly_ids, context=context):
            
            # If the user hasn't specifically chosen so, do not re-create punches if
            # they already exist.
            #
            if not wizard.do_recreate and weekly.att_ids and len(weekly.att_ids) > 0:
                continue
            
            weekly_obj.action_delete_hours(cr, uid, [weekly.id], context=context)
            week_vals = weekly_obj.get_weekly_lines(cr, uid, weekly.id, context=context)
            weekly_obj.add_punches(cr, uid, weekly.id, week_vals, context=context)
            weekly_obj.write(cr, uid, weekly.id, {'init_time': datetime.now().strftime(OE_DTFORMAT)},
                       context=context)
        
        return {'type': 'ir.actions.act_window_close'}
            