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
from pytz import common_timezones, timezone, utc

from openerp.addons.hr_employee_id.hr_employee_id import IDLEN
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT
from osv import osv, fields
import timeutils as tu
from lib.models import labels as clock_labels
from lib.models import default as clock_default
from lib.models import classes as clock_class
from lib.attendance_creator import AttendanceCreator, \
        MultipleAssignedCardError, NotAssignedCardError
import netsvc

import logging
logger = logging.getLogger(__name__)

_uri_help = """Determines the URI string to connect to the clock. The URI is
determined by each model watch. In the case of F5, for example is:
udp://localhost:8000/"""

def setSome(A, B):
    return A != None and A or B

class clock_reader_job(osv.Model):
    
    _name = 'hr_clock_reader.job'
    _description = 'Clock Reader Job Run'
    
    _columns = {
        'name': fields.datetime('Date and Time', required=True, readonly=True),
        'clock_id': fields.many2one('hr_clock_reader.clock', 'Clock', required=True),
        'success': fields.boolean('OK'),
        'count': fields.integer('Number of punches'),
        'errors': fields.text('Errors'),
    }
    
    def try_read_clocks(self, cr, uid, context=None):
        
        clock_ids = self.pool.get('hr_clock_reader.clock').search(cr, uid, [('active', '=', True)],
                                                                  context=context)
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        
        for clock_id in clock_ids:
            
            dtStart = False
            
            # Get the last execution timestamp. It will be in naive utc format
            # so, first convert it to our users timezone.
            # 
            # XXX - if the user doesn't have a timezone you will get f*d up results.
            #
            last_ids = self.search(cr, uid, [('clock_id', '=', clock_id), ('success', '=', True)],
                                   order='name desc', limit=1, context=context)
            if len(last_ids) > 0:
                last = self.browse(cr, uid, last_ids[0], context=context)
                utcdtStart = datetime.strptime(last.name, OE_DTFORMAT) + timedelta(seconds= +1)
                utcdtStart = utc.localize(utcdtStart, is_dst=False)
                if user.tz:
                    dtStart = utcdtStart.astimezone(timezone(user.tz))
                    dtStart = dtStart.replace(tzinfo=None)
                
            dtNow = datetime.now()
            dtNow = datetime(dtNow.year, dtNow.month, dtNow.day,
                             dtNow.hour, dtNow.minute, 0)
            
            self.pool.get('hr_clock_reader.clock').read_clocks(cr, uid, clock_ids=[clock_id],
                                                               dtStart=dtStart, dtEnd=dtNow,
                                                               log=True,
                                                               context=context)
        
        return

class hr_clock_reader_clock(osv.osv):
    _name = "hr_clock_reader.clock"
    _description = "Clock"
    
    def _tz_list(self, cr, uid, context=None):
        
        res = tuple()
        for name in common_timezones:
            res += ((name, name),)
        return res

    _columns = {
        'name' : fields.char("Name", size=64, required=True),
        'uri': fields.char('Clock URI', size=128, required=True, help=_uri_help),
        'has_server': fields.boolean('Has Server', help="Check this if communication is with a server, and not directly with the clock."),
        'server_uri': fields.char('Server URI', size=128, required=True,
                                  help="For Biostation, uri of server providing attendance data."),
        'model': fields.selection(clock_labels, 'Model', required=True),
        'location_id': fields.many2one('hr.department', 'Location',
                                       select=True, ondelete='set null'),
        'tz': fields.selection(_tz_list, 'Time Zone', required=True),
        'timeout': fields.integer('Timeout (sec)'),
        'create_unknown_employee': fields.boolean('Create Unknown Employeers'),
        'ignore_sign_inout': fields.boolean('Ignore sign in/outs'),
        'ignore_restrictions': fields.boolean('Ignore DB restrictions',
                                              help='You must remove attendance sign-in/out restrictions before use it.'),
        'complete_attendance': fields.boolean('Autocomplete sign in/out'),
        'clean_at_end': fields.boolean('Clean clock at the end'),
        'tolerance': fields.integer('Tolerance', help='In seconds, distance'
                                    ' bettweeen attendance with same action'
                                    ' understanded as the same attendance.'),
        'active': fields.boolean('Active'),
    }
    _defaults = {
        'tolerance': 60,
        'active': True,
    }
    _sql_constraints = [
        ('uri', 'UNIQUE (uri)', 'The uri of the clock must be unique' )
    ]
    _order = 'uri asc'

    def load_attendances(self, cr, uid, ids=None, dtStart=None, dtEnd=None,
             clean_at_end = None,
             complete_attendance = None,
             create_unknown_employee = None,
             ignore_sign_inout = None,
             ignore_restrictions = None,
             tolerance = None,
             context=None):
        AC = AttendanceCreator(cr, uid, context=context)
        card_err = {}
        empl_err = {}
        empl_id = {}
        err = []
        c = 0

        if ids==None:
            ids = self.search(cr, uid, [])

        from datetime import datetime
        import csv
        DEBUGFILE = open('/tmp/clock.%s.csv' % datetime.today(), 'w')
        DEBUGCSV  = csv.writer(DEBUGFILE)

        for clock in self.browse(cr, uid, ids):

            C = clock_class[clock.model](clock.uri, server_uri=clock.server_uri, timeout=clock.timeout)

            if not C.connect():
                err.append("Can't connect with clock '%s'." % clock.name)
                continue

            for n, card_id, method, action, dt in C.attendances(dtStart=dtStart, dtEnd=dtEnd):
                DEBUGCSV.writerow((n, card_id, method, action, dt))

                assert isinstance(dt, tu.datetime)

                # Set timestamp to UTC
                utcdt = timezone(clock.tz).localize(dt, is_dst=False).astimezone(utc)
                utcdt = utcdt.replace(tzinfo=None)
                
                # Verifico que esta tarjeta no me haya traido problemas
                # previamente.
                if card_id in card_err:
                    DEBUGCSV.writerow((n, card_id, method, action, dt,"in card_err"))
                    logger.notifyChannel('wizard.hr_clock_reader', netsvc.LOG_DEBUG,
                                          '_read_clock: Card %i in the black list.'%card_id)
                    continue

                # Verificar si un empleado usa esa tarjeta
                if not card_id in empl_id:
                    DEBUGCSV.writerow((n, card_id, method, action, dt,"not in empl_id"))
                    try:
                        empl_id[card_id] = AC.employee_id(card_id)

                    except MultipleAssignedCardError, m:
                        DEBUGCSV.writerow((n, card_id, method, action, dt,"MultipleAssignedCardError",m))
                        card_err[card_id] = str(m)
                        continue

                    except NotAssignedCardError, m:
                        DEBUGCSV.writerow((n, card_id, method, action, dt,"NotAssignedCardError",m))
                        if setSome(create_unknown_employee,
                                   clock.create_unknown_employee):
                            empl_id[card_id] = AC.create_employee(card_id)
                        else:
                            card_err[card_id] = str(m)
                            continue

                # Verifico que este empleado no me haya traido problemas
                # previamente.
                if card_id in card_err:
                    DEBUGCSV.writerow((n, card_id, method, action, dt,"Employee in black list"))
                    logger.notifyChannel('wizard.hr_clock_reader', netsvc.LOG_DEBUG,
                                    '_read_clock: Employee %i in the black list.' %
                                                                   empl_id[card_id])
                    continue

                # Si esta todo bien con el empleado, cargo la asistencia.
                if AC.exists_attendance(empl_id[card_id], utcdt, action):
                    DEBUGCSV.writerow((n, card_id, method, action, dt,"Attendance yet loaded"))
                    logger.notifyChannel('hr_clock_reader.clock', netsvc.LOG_DEBUG,
                               'read: Attendance %i:%s:%s(%s) yet loaded.' %
                                    (empl_id[card_id], tu.dt2s(dt), action, method))
                    continue

                r = AC.create_attendance(empl_id[card_id], utcdt, action, method,
                                     tolerance=setSome(tolerance,
                                                       clock.tolerance),
                                     complete_attendance=setSome(complete_attendance, clock.complete_attendance),
                                     forgot_action=setSome(ignore_sign_inout, clock.ignore_sign_inout),
                                     ignore_restrictions=setSome(ignore_restrictions, clock.ignore_restrictions))

                if r == AttendanceCreator.OK:
                    DEBUGCSV.writerow((n, card_id, method, action, dt,"Creation Success"))
                    c = c + 1
                elif r == AttendanceCreator.IGNORED:
                    DEBUGCSV.writerow((n, card_id, method, action, dt,"Ignored"))
                else:
                    DEBUGCSV.writerow((n, card_id, method, action, dt,"Creation Error", r))
                    #logger.notifyChannel('hr_clock_reader.clock',
                    #     netsvc.LOG_INFO,
                    #     'read: Append employee %s to the black list.' %
                    #     str(empl_id[card_id]))
                    #empl_err[empl_id[card_id]] = str(m)

        DEBUGCSV.writerow((-1, -1, -1, -1, -1,"End process"))
        DEBUGFILE.close()

        # Recolección de errores
        cards_err = card_err.keys()
        empls_err = empl_err.keys()

        cards_err.sort()
        empls_err.sort()

        err += map(lambda i: card_err[i], cards_err)
        err += map(lambda i: empl_err[i], empls_err)

        return { 'count': c, 'errors': err }
    
    def read_clocks(self, cr, uid, clock_ids=False, dtStart=False, dtEnd=False, is_utc=False,
                    clean_at_end = None,
                    complete_attendance = None,
                    create_unknown_employee = None,
                    ignore_sign_inout = None,
                    ignore_restrictions = None,
                    tolerance = None,
                    log=False,
                    context=None):
        '''Read all "active" punch clocks for punches within the given parameters
        and return a tuple containing the number of punches and a text string containing
        any errors encountered.'''

        if (dtStart and dtEnd) and dtStart >= dtEnd:
            return (0, 'Start boundary date/time must always occur before the end boundary.')
        
        if context == None:
            context = {}
        
        if not clock_ids:
            clock_ids = self.search(cr, uid, [('active', '=', True)], context=context)

        count_total = 0
        errors = []
        for clock in self.browse(cr, uid, clock_ids, context=context):
            
            # Set timestamp to current user's time zone -> UTC -> clock's timezone
            user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            if user.tz:
                clock_tz = timezone(clock.tz)
                if dtStart:
                    if is_utc:
                        utcdtStart = utc.localize(dtStart, is_dst=False)
                    else:
                        utcdtStart = timezone(user.tz).localize(dtStart, is_dst=False).astimezone(utc)
                    dtStart = utcdtStart.astimezone(clock_tz)
                    dtStart = dtStart.replace(tzinfo=None)
                if dtEnd:
                    if is_utc:
                        utcdtEnd = utc.localize(dtEnd, is_dst=False)
                    else:
                        utcdtEnd = timezone(user.tz).localize(dtEnd, is_dst=False).astimezone(utc)
                    dtEnd = utcdtEnd.astimezone(clock_tz)
                    dtEnd = dtEnd.replace(tzinfo=None)
            
            ret = self.load_attendances(cr, uid, [clock.id], dtStart, dtEnd,
                                  create_unknown_employee=create_unknown_employee,
                                  complete_attendance=complete_attendance,
                                  tolerance=tolerance,
                                  ignore_sign_inout=ignore_sign_inout,
                                  ignore_restrictions=ignore_restrictions,
                                  clean_at_end=clean_at_end,
                                  context=context)
            if log:
                vals = {
                    'name': dtEnd.strftime(OE_DTFORMAT),
                    'clock_id': clock.id,
                    'count': ret['count'],
                    'errors': '\n'.join(ret['errors']),
                    'success': (ret['count'] > 0 or len(ret['errors']) == 0) and True or False 
                }
                self.pool.get('hr_clock_reader.job').create(cr, uid, vals, context=context)
            
            count_total += ret['count']
            errors += ret['errors']

        return (count_total, errors)

hr_clock_reader_clock()

class hr_attendance(osv.osv):
    _inherit = "hr.attendance"
    _columns = {
        'method': fields.selection( [('manual', 'Manual'),
                                    ('automatic', 'Automatic'),
                                    ('keyboard', 'Keyboard'),
                                    ('fingerprint', 'Fingerprint'),
                                    ('rfid', 'RFid'),
                                    ('facerecognition', 'Face recognition'),],
                                   'Authentication method'),
        'auto_status': fields.selection( [('UNDEFINED','Undefined'),
                                        ('OK_START','Ok Start'),
                                        ('OK_START_I','Ok Start Interval'),
                                        ('OK_END_I','Ok End Interval'),
                                        ('OK_END','Ok End'),
                                        ('FORCED_START','Forced Ok Start'),
                                        ('FORCED_START_I','Forced Ok Start Interval'),
                                        ('FORCED_END_I','Forced Ok End Interval'),
                                        ('FORCED_END','Forced Ok End'),
                                        ('CREATED_START','Created Ok Start'),
                                        ('CREATED_START_I','Created Ok Start Interval'),
                                        ('CREATED_END_I','Created Ok End Interval'),
                                        ('CREATED_END','Created Ok End'),],
                                        'Automatic Attendance Status'),
    }

    _defaults = {
        'method': 'manual',
        'auto_status': 'UNDEFINED',
    }

hr_attendance()

class hr_employee(osv.Model):
    
    _inherit = 'hr.employee'
    
    _columns = {
        'clock_login_id': fields.integer('Time Clock ID', readonly=True),
    }
    
    _sql_constraints = [
        ('clock_login_id_uniq', 'unique(clock_login_id)', 'The employee\'s Time Clock ID Number must be unique accross the company(s).'),
    ]
    
    def create(self, cr, uid, vals, context=None):
        
        ee_id = super(hr_employee, self).create(cr, uid, vals, context=context)
        data = self.read(cr, uid, ee_id, ['employee_no'], context=context)
        self.write(cr, uid, ee_id, {'clock_login_id': int(data['employee_no'])}, context=context)
        return ee_id

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
