# -*- encoding: utf-8 -*-
##############################################################################
#
#    Clock Reader for OpenERP
#    Copyright (C) 2004-2009 Moldeo Interactive CT
#    (<http://www.moldeointeractive.com.ar>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from datetime import datetime, timedelta
from pytz import timezone, utc
from .. import timeutils as tu

import netsvc
import pooler
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT

_negative_action = {
    'sign_in': 'sign_out',
    'sign_out': 'sign_in',
}

class MultipleAssignedCardError:
    def __init__(self, empl_id, card_id):
        self.empl_id = empl_id
        self.card_id = card_id

    def __str__(self):
        return 'Employees with ids %s have the same card id: %i' % \
                (repr(self.empl_id), self.card_id)

class NotAssignedCardError:
    def __init__(self, card_id):
        self.card_id = card_id

    def __str__(self):
        return 'Card [%i] is not assigned.' % self.card_id

class AttendanceCreator:
    logger = netsvc.Logger()

    OK = -1
    IGNORED = 0
    ERROR = 1

    def __init__(self, cr, uid, context=None):
        self.emp_id_ok = {}
        self.emp_id_err = {}
        self.emp_id_notexists = []
        self.err = []
        self.c = 0

        self.cr = cr
        self.uid = uid
        self.context = context
        self.pool = pooler.get_pool(cr.dbname)
        self.emp_pool = self.pool.get('hr.employee')
        self.att_pool = self.pool.get('hr.attendance')
        self.con_pool = self.pool.get('hr.contract')
        self.cal_pool = self.pool.get('resource.calendar')
        self.detail_pool = self.pool.get('hr.schedule.detail')

    def employee_id(self, card_id):
        emp_ids = self.emp_pool.search(self.cr, self.uid,
                                       [('clock_login_id', '=', card_id)],
                                       context=self.context)
        if len(emp_ids) > 1:
            raise MultipleAssignedCardError(emp_ids, card_id)
        elif len(emp_ids) == 0:
            raise NotAssignedCardError(card_id)

        return emp_ids[0]

    def exists_attendance(self, empl_id, dt, action):
        assert isinstance(dt, tu.datetime)
        
        # if we are using a rounding policy the original clock time
        # will be found in the 'clock_time' field.
        #
        field_name = 'name'
        if hasattr(self.att_pool, 'clock_time'):
            field_name = 'clock_time'
        
        att_ids = self.att_pool.search(self.cr, self.uid,
                                 [('employee_id', '=', empl_id),
                                  (field_name, '=', tu.dt2s(dt))],
                                       context=self.context)
        return len(att_ids) > 0

    def get_schedule(self, empl_id, dt, contract):
        
        sched_hours = []
        if contract:
            sched_hours = self.detail_pool.scheduled_begin_end_times(self.cr, self.uid, empl_id,
                                                                     contract.id, dt.date(),
                                                                     context=self.context)
        return sched_hours
        
    def get_contract(self, empl_id, dt ):

        con_ids = self.con_pool.search(self.cr, self.uid,
                                       [('employee_id', '=', empl_id),
                                        ('date_start', '<=', dt.strftime(OE_DFORMAT)),
                                        '|', ('date_end', '=', False),
                                             ('date_end', '>=', dt.strftime(OE_DFORMAT))],
                                       context=self.context)

        if len(con_ids)>0:
            con_obj = self.con_pool.browse( self.cr, self.uid, con_ids[0] )
            return con_obj
        else:
            return False

    def get_calendar(self, turn_id ):
        cal_obj = self.cal_pool.browse(self.cr, self.uid, turn_id)

        if (cal_obj):
            return cal_obj
        else:
            return False

    def create_employee(self, card_id):
        self.emp_pool.create(self.cr, self.uid, {
            'name': 'Unknown Employee with card id %i' % card_id,
            'clock_login_id': card_id,
        })
        return self.employee_id(card_id)

    def previous_action(self, empl_id, dt, action=False):
        assert isinstance(dt, tu.datetime)
        if action:
            sql_action = "AND action = '%s'" % action
        else:
            sql_action = ""
        sql = """
SELECT employee_id, name, action, auto_status
FROM hr_attendance
WHERE
name::timestamp <= '%s'::timestamp AND
   employee_id = '%s'
   %s
ORDER BY name desc
""" % (tu.dt2s(dt), empl_id, sql_action)
        self.cr.execute(sql)
        r = self.cr.dictfetchall()
        if len(r)>0:
            return (empl_id, tu.dt(r[0]['name']), r[0]['action'], r[0]['auto_status'])
        else:
            return False

    def next_action(self, empl_id, dt, action=False):
        assert isinstance(dt, tu.datetime)
        if action:
            sql_action = "AND action = '%s'" % action
        else:
            sql_action = ""
        sql = """
SELECT employee_id, name as name, action, auto_status
FROM hr_attendance
WHERE
   name::timestamp > '%s'::timestamp AND
   employee_id = '%s'
   %s
ORDER BY name asc
""" % (tu.dt2s(dt), empl_id, sql_action)
        self.cr.execute(sql)
        r = self.cr.dictfetchall()
        if len(r)>0:
            return (empl_id, tu.dt(r[0]['name']), r[0]['action'], r[0]['auto_status'])
        else:
            return False

    def is_start_of_contract( self, empl_id, dt, sched_hours, prev_punch, margin):
        #la fichada inmmediatamente anterior no puede ser un OK_START, FORCED_OK_START o CREATED_OK_START
        
        #if dt > (prev_punch[1] - margin) and dt < (prev_punch[1] + margin):
            
        #r = self.previous_action( empl_id, dt )
        #cal_obj = self.get_calendar( cont.turn_id.id )
        #self.logger.notifyChannel('wizard.hr_clock_reader', netsvc.LOG_INFO,
        #           'is_start_of_contract: contract: %s turn_id: %s' %
        #                                  ( cont.name, cal_obj.name ))
        start_time = tu.datetime( dt.year, dt.month, dt.day, 6, 0, 0)
        #if cal_obj and cal_obj.name == "Noche Jornal 6pm a 6am":
        #    if dt > tu.datetime( dt.year, dt.month, dt.day, 18, 0, 0) - margin:
        #        start_time = tu.datetime( dt.year, dt.month, dt.day, 18, 0, 0)
        #    elif dt < tu.datetime( dt.year, dt.month, dt.day, 6, 0, 0) + margin:
        #        start_time = tu.datetime( dt.year, dt.month, dt.day, 18, 0, 0) + tu.timedelta(days=-1)

        #if ( r and (r[3]=='OK_START' or r[3]=='FORCED_OK_START' or r[3]=='CREATED_OK_START') ):
        #    return False                
        #cal_obj = cont.turn_id
        #TODO use resouce.calendar.attendance to check real hour_from and hour_to times
        
        dt_distance = start_time - dt
        return abs(dt_distance) < abs(margin)

        return False

    def is_end_of_contract( self, empl_id, dt, margin ):
        #la fichada inmmediatamente anterior no puede ser un OK_END, FORCED_OK_END o CREATED_OK_END
        cont = self.get_contract(empl_id, dt)
        if cont:
            cal_obj = self.get_calendar( cont.turn_id.id )
            end_time = tu.datetime( dt.year, dt.month, dt.day, 18, 0, 0)
            if cal_obj and cal_obj.name == "Noche Jornal 6pm a 6am":
                if dt > tu.datetime( dt.year, dt.month, dt.day, 18, 0, 0) - margin:
                    end_time = tu.datetime( dt.year, dt.month, dt.day, 6, 0, 0) + tu.timedelta(days=1)
                elif dt < tu.datetime( dt.year, dt.month, dt.day, 6, 0, 0) + margin:
                    end_time = tu.datetime( dt.year, dt.month, dt.day, 6, 0, 0)

            #TODO use resouce.calendar.attendance to check real hour_from and hour_to times            
            dt_distance = end_time - dt
            return abs(dt_distance) < abs(margin)

        return False

    def is_intermezzo( self, empl_id, dt, margin ):
        #TODO ya debe existir un OK_START,FORCED_START o CREATED_START, o (FORCED|CREATED)_START_I, (FORCED|CREATED)_END_I, ese dia anterior a esta fichada
        #r = self.previous_action( empl_id, dt )
        cont = self.get_contract(empl_id, dt)
        if cont:
            cal_obj = self.get_calendar( cont.turn_id.id )
            start_time = tu.datetime( dt.year, dt.month, dt.day, 6, 0, 0)
            end_time = tu.datetime( dt.year, dt.month, dt.day, 18, 0, 0)

            if cal_obj and cal_obj.name == "Noche Jornal 6pm a 6am":
                if dt > tu.datetime( dt.year, dt.month, dt.day, 18, 0, 0) - margin:
                    start_time = tu.datetime( dt.year, dt.month, dt.day, 18, 0, 0)
                    end_time = tu.datetime( dt.year, dt.month, dt.day, 6, 0, 0) + tu.timedelta(days=1)
                elif dt < tu.datetime( dt.year, dt.month, dt.day, 6, 0, 0) + margin:
                    start_time = tu.datetime( dt.year, dt.month, dt.day, 18, 0, 0) + tu.timedelta(days=-1)
                    end_time = tu.datetime( dt.year, dt.month, dt.day, 6, 0, 0)

            #TODO use resouce.calendar.attendance to check real hour_from and hour_to times
            
            return (start_time + margin) < dt and dt < (end_time - margin) 
        return False

    def close_previous_attendance( self, empl_id, dt, margin ):

        #TODO: definir todos los casos....
        
        return False
    
    def _get_action(self, empl_id, utcdt):
        '''Get current action (sign-in/sign-out) based on previous action'''
        
        utcdtS = utcdt + timedelta(hours= -12)
        utcdtE = utcdt
        utcdtS_str = utcdtS.strftime('%Y-%m-%d %H:%M:%S')
        utcdtE_str = utcdtE.strftime('%Y-%m-%d %H:%M:%S')
        att_ids = self.att_pool.search(self.cr, self.uid,
                                                           [('employee_id', '=', empl_id),
                                                            ('name', '<', utcdtE_str),
                                                            ('name', '>=',utcdtS_str )],
                                                           order='name desc', context=self.context)
        if len(att_ids) == 0:
            return ('sign_in', 'FORCED_END')
        
        data = self.att_pool.read(self.cr, self.uid, att_ids[0],
                                                      ['action'], self.context)
        res = ('sign_in', 'FORCED_END')
        if data['action'] == 'sign_out':
            res = ('sign_out', 'FORCED_START')
        
        return res

    def create_attendance(self, empl_id, dt, action, method, tolerance=60*5,
                          complete_attendance=False, forgot_action=False,
                          ignore_restrictions=False, auto_status='UNDEFINED'):
        assert isinstance(dt, tu.datetime)

        self.logger.notifyChannel('wizard.hr_clock_reader', netsvc.LOG_DEBUG,
                               'create_attendance: CREATE: %s, %s, %s, %i'%
                                  (tu.dt2s(dt), action, method, empl_id))
        
        prev_punch = self.previous_action(empl_id, dt)

        # Equal attendance
        if prev_punch and prev_punch[1] + tu.timedelta(seconds=tolerance) > dt:
                self.logger.notifyChannel('wizard.hr_clock_reader', netsvc.LOG_INFO,
                   'create_attendance: IGNORED: multiply registries in equivalent time')
                return AttendanceCreator.IGNORED
        
        cont = self.get_contract(empl_id, dt)
        sched_hours = self.get_schedule(empl_id, dt, cont)
        if len(sched_hours) > 0:
            self.logger.notifyChannel('wizard.hr_clock_reader', netsvc.LOG_INFO,
                   'create_attendance: hr.contract: %s scheduled hours: %s' % ( cont and cont.name or 'False', sched_hours ))
        else:
            self.logger.notifyChannel('wizard.hr_clock_reader', netsvc.LOG_INFO,
               'create_attendance: schedule not found for employee: %s' % (empl_id))                     

        #aqui definimos el intervalo de tiempo que usaremos para marcar forzadamente con sign_in
        dt_start_end_margin = tu.timedelta(hours=2)
        dt_intermezzo_margin = tu.timedelta(hours=2)
        dt_newday_margin = tu.timedelta(hours=12)

        #
        # Simple punch type determination:
        #    If there are no previous punches: Sign-in
        #    If there are no punches within the new day margin: Sign-in
        #    If there is a punch within the new day margin: do the opposite of previous punch
        #
        if not prev_punch:
            action = 'sign_in'
            auto_status = 'OK_START'
        
        elif dt > (prev_punch[1] + dt_newday_margin):
            self.logger.notifyChannel('wizard.hr_clock_reader', netsvc.LOG_INFO,
               'create_attendance: previous punch greater than margin: %s' %(prev_punch,))
            action = 'sign_in'
            if prev_punch[2] == 'sign_out':
                auto_status = 'OK_START'
            else:
                auto_status = 'FORCED_START'
        
        else:
            if prev_punch[2] == 'sign_out':
                action = 'sign_in'
                auto_status = 'OK_START'
            else:
                action = 'sign_out'
                auto_status = 'OK_END'

        if auto_status == "UNDEFINED":
            return AttendanceCreator.ERROR

        # Equal accion
        if not ignore_restrictions:
            if prev_punch and prev_punch[2] == action:
                # Employee forgot sign: aka Fichadas Locas ....
                if complete_attendance:
                    self.logger.notifyChannel('wizard.hr_clock_reader', netsvc.LOG_DEBUG,
                       'create_attendance: equal previous action %s %s %i' %
                                              (tu.dt2s(prev_punch[1]), prev_punch[2], prev_punch[0]))
                    vals = {
                        'name': dt + timedelta(seconds= -1),
                        'action': _negative_action[action],
                        'auto_status': _negative_action[action] == 'sign_in' and 'FORCED_START' or 'FORCED_END',
                        'method': 'automatic',
                        'employee_id': empl_id,
                    }
                    self.logger.notifyChannel('wizard.hr_clock_reader', netsvc.LOG_INFO,
                                              'create_attendance: COMPLETE MISSED PUNCH: %s' % (vals,))
                    self.att_pool.create(self.cr, self.uid, vals)
                else:
                    # Missing punch 
                    self.logger.notifyChannel('wizard.hr_clock_reader', netsvc.LOG_INFO,
                       'create_attendance: IGNORE MISSED PUNCH: Employee %s' %(empl_id,))

        vals = {
            'name': tu.dt2s(dt),
            'action': action,
            'auto_status': auto_status,
            'method': method,
            'employee_id': empl_id,
        }
        self.logger.notifyChannel('wizard.hr_clock_reader', netsvc.LOG_INFO,
                                  'create_attendance: VALS: %s' % (vals,))
        
        self.att_pool.create(self.cr, self.uid, vals)

        self.logger.notifyChannel('wizard.hr_clock_reader', netsvc.LOG_DEBUG,
                               'create_attendance: DONE: %s, %s, %s, %i'%
                                  (tu.dt2s(dt), action, method, empl_id))
        return AttendanceCreator.OK

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
