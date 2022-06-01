# -*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Clear ICT Solutions <info@clearict.com>.
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify it
#    under the terms of the GNU Affero General Public License as published by
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

import random
import string
import time
from datetime import datetime, timedelta
from pytz import timezone, utc
from time import sleep

from openerp import pooler
from openerp.addons.connector.queue.job import job, DONE, FAILED
from openerp.addons.connector.session import ConnectorSession
from openerp.osv import fields, orm
from openerp.service.locking import RecordRLock
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT
from openerp.tools.translate import _

import logging
_l = logging.getLogger(__name__)


def create_dirty_records(session, proc_ids, weekly_id):

    assert len(proc_ids) == 1, "Payroll processing ids elements != 1"

    w_obj = session.pool.get('hr.attendance.weekly')
    mod_obj = session.pool.get('hr.payroll.processing.weekly.employees')
    dirty_ee_ids = w_obj.get_attendance_dirty_employees(
        session.cr, session.uid, weekly_id, context=session.context
    )

    for ee_id in dirty_ee_ids:
        mod_obj.create(
            session.cr, session.uid,
            {
                'employee_id': ee_id,
                'weekly_id': weekly_id,
                'processing_id': proc_ids[0],
            },
            context=session.context)

        # If the employee was transferred to another department in the
        # middle of the week we need to adjust the weekly attendance
        # in that department as well.
        #
        w = w_obj.browse(session.cr, session.uid, weekly_id,
                         context=session.context)
        other_w_ids = w_obj.get_other_weeklies(
            session.cr, session.uid, ee_id, w.week_start,
            context=session.context)
        for w_id in other_w_ids:
            if w_id != weekly_id:
                mod_obj.create(
                    session.cr, session.uid,
                    {
                        'employee_id': ee_id,
                        'weekly_id': w_id,
                        'processing_id': proc_ids[0],
                    },
                    context=session.context)

    return (len(dirty_ee_ids) > 0 and True or False)


@job
def check_weekly_attendance(session, model, proc_ids, department_id, dStart, dEnd, key):

    w_obj = session.pool.get('hr.attendance.weekly')

    dirty_weekly = False
    dTemp = dStart
    while dTemp.weekday() != 0:
        dTemp += timedelta(days=-1)
    _l.warning('dept_id: %s', department_id)
    while dTemp <= dEnd:
        tmp_ids = w_obj.search(
            session.cr, session.uid,
            [('department_id', '=', department_id),
             ('week_start', '=', dTemp.strftime(OE_DFORMAT))],
            context=session.context)
        if len(tmp_ids) == 0:
            tmp_id = w_obj.create(session.cr, session.uid,
                                  {'department_id': department_id,
                                   'week_start': dTemp.strftime(OE_DFORMAT)},
                                  context=session.context)

            # Do not create a record if the department does not have
            # any employees
            #
            ee_ids = w_obj.get_employees(
                session.cr, session.uid,
                w_obj.browse(session.cr, session.uid, tmp_id,
                             context=session.context),
                context=session.context)
            if len(ee_ids) == 0:
                w_obj.unlink(
                    session.cr, session.uid, tmp_id, context=session.context)
            else:
                dirty_weekly = create_dirty_records(session, proc_ids, tmp_id)
        else:
            tmp_id = tmp_ids[0]
            dirty_weekly = create_dirty_records(session, proc_ids, tmp_id)

        if dirty_weekly:
            tmp_obj = session.pool.get('hr.payroll.process.tmp.dirtyatt')
            tmp_obj.create(session.cr, session.uid,
                           {'name': key,
                            'weekly_ids': [(4, tmp_id, 0)]},
                           context=session.context)

        dTemp += timedelta(days=+7)

    return


@job
def adjustment_by_weekly(session, model_name, weekly_id, employee_ids,
                         only_weeks_list=None, do_sched=True,
                         do_reset_rest=True):

    lock = RecordRLock(session.cr.dbname, 'hr.attendance.weekly', weekly_id)
    lock.acquire()
    try:
        proc_obj = session.pool.get('hr.payroll.processing')
        for employee_id in employee_ids:
            proc_obj.create_adjustments(
                session.cr, session.uid, weekly_id, employee_id,
                only_weeks_list=only_weeks_list, do_sched=do_sched,
                do_reset_rest=do_reset_rest, context=session.context
            )
            session.pool.get('hr.attendance.weekly').write(
                session.cr, session.uid, [weekly_id],
                {'init_time': datetime.now().strftime(OE_DTFORMAT)},
                context=session.context)
    finally:
        lock.release()


def generate_random_string():

    rnd = random.SystemRandom()
    digit1 = ''.join(rnd.choice(['1', '2', '3', '4', '5', '6', '7', '8', '9']))
    digits = ''.join(rnd.choice(string.digits) for _ in range(12 - 1))
    rndstr = digit1 + digits
    return rndstr


class ProcessingWizardConnector(orm.TransientModel):

    _inherit = 'hr.payroll.processing'

    def state_doweekly(self, cr, uid, ids, context=None):

        self._populate_weekly(cr, uid, ids, context=context)

        db, pool = pooler.get_db_and_pool(cr.dbname)
        newcr = db.cursor()
        try:
            self.write(newcr, uid, ids, {'state': 'doweekly'}, context=context)
            newcr.commit()
        except Exception:
            newcr.rollback()
            raise
        finally:
            newcr.close()

    def _populate_weekly(self, cr, uid, ids, context=None):

        pp_id = self._get_pp(cr, uid, context=context)
        if pp_id:
            pp = self.pool.get('hr.payroll.period').browse(cr, uid, pp_id,
                                                           context=context)
            company_id = pp.company_id and pp.company_id.id or False
            if not company_id:
                user = self.pool.get('res.users').browse(cr, uid, uid,
                                                         context=context)
                company_id = user.company_id.id
            department_ids = self.pool.get('hr.department').search(
                cr, uid, [('company_id', '=', company_id)], context=context
            )

            local_tz = timezone(pp.schedule_id.tz)
            utcdtStart = utc.localize(
                datetime.strptime(pp.date_start, OE_DTFORMAT),
                is_dst=False
            )
            dtStart = utcdtStart.astimezone(local_tz)
            utcdtEnd = utc.localize(
                datetime.strptime(pp.date_end, OE_DTFORMAT),
                is_dst=False
            )
            dtEnd = utcdtEnd.astimezone(local_tz)
            dStart = dtStart.date()
            dEnd = dtEnd.date()
            key = generate_random_string()
            job_uuids = []

            db, pool = pooler.get_db_and_pool(cr.dbname)
            newcr = db.cursor()
            try:
                self.write(newcr, uid, ids,
                           {'weekly_ids': [(6, 0, [])],
                            'weekly_modified_ids': [(6, 0, [])]},
                           context=context)
                session = ConnectorSession(newcr, uid, context)
                for dept_id in department_ids:
                    description = \
                        _("Check Weekly Attendance for department id %s") % \
                        (dept_id)
                    job_uuid = check_weekly_attendance.delay(
                        session, 'hr.payroll.processing',
                        ids, dept_id, dStart, dEnd, key,
                        description=description
                    )
                    job_uuids.append(job_uuid)

                newcr.commit()
            except Exception:
                newcr.rollback()
                raise
            finally:
                newcr.close()

        unfinished_uuids = job_uuids
        done_uuids = []
        failed_uuids = []
        job_obj = self.pool.get('queue.job')
        while len(unfinished_uuids) > 0:
            sleep(5)

            newcr = db.cursor()
            try:
                job_ids = job_obj.search(newcr, uid,
                                         [('uuid', 'in', unfinished_uuids)],
                                         context=context)
                for _job in job_obj.browse(newcr, uid, job_ids,
                                           context=context):
                    if _job.state == FAILED and _job.uuid not in failed_uuids:
                        failed_uuids.append(_job.uuid)
                        unfinished_uuids.remove(_job.uuid)
                    elif _job.state == DONE and _job.uuid not in done_uuids:
                        done_uuids.append(_job.uuid)
                        unfinished_uuids.remove(_job.uuid)
                newcr.commit()
            except Exception:
                newcr.rollback()
                raise
            finally:
                newcr.close()

        newcr = db.cursor()
        try:
            dirty_weekly_ids = []
            tmp_obj = self.pool.get('hr.payroll.process.tmp.dirtyatt')
            tmp_ids = tmp_obj.search(newcr, uid, [('name', '=', key)],
                                     context=context)
            if len(tmp_ids) > 0:
                for tmprec in tmp_obj.browse(newcr, uid, tmp_ids,
                                             context=context):
                    for w in tmprec.weekly_ids:
                        if w.id in dirty_weekly_ids:
                            continue
                        dirty_weekly_ids.append(w.id)
                tmp_obj.unlink(newcr, uid, tmp_ids, context=context)
    
            if len(dirty_weekly_ids) > 0:
                self.write(newcr, uid, ids,
                           {'weekly_ids': [(6, 0, dirty_weekly_ids)]},
                           context=context)
            newcr.commit()
        except Exception:
            newcr.rollback()
            raise
        finally:
            newcr.close()

        return

    def do_weekly_attendance(self, cr, uid, ids, context=None):

        wizard = self.browse(cr, uid, ids[0], context=context)

        job_uuids = []
        weekly_by_uuids = {}
        wm_by_weekly = {}
        for wm in wizard.weekly_modified_ids:
            if wm.weekly_id.id not in wm_by_weekly.keys():
                wm_by_weekly.update(
                    {
                        wm.weekly_id.id:
                            {
                                'name':
                                wm.weekly_id.department_id.complete_name
                                + ' ' + wm.weekly_id.week_start,
                                'employee_ids': [wm.employee_id.id]
                            }
                    }
                )
            else:
                wm_by_weekly[wm.weekly_id.id]['employee_ids'].\
                    append(wm.employee_id.id)

        db, pool = pooler.get_db_and_pool(cr.dbname)
        newcr = db.cursor()
        try:
            session = ConnectorSession(newcr, uid, context=context)
            for w_id, value in wm_by_weekly.items():
                description = \
                    _("Convert Weekly Attendance %s") % (value['name'])
                job_uuid = adjustment_by_weekly.delay(session,
                                                      'hr.payroll.processing',
                                                      w_id,
                                                      value['employee_ids'],
                                                      only_weeks_list=None,
                                                      do_sched=True,
                                                      do_reset_rest=True,
                                                      description=description)
                job_uuids.append(job_uuid)
                weekly_by_uuids.update({job_uuid: [w_id]})
            newcr.commit()
        except Exception:
            newcr.rollback()
            raise
        finally:
            newcr.close()

        unfinished_uuids = job_uuids
        done_uuids = []
        failed_uuids = []
        job_obj = self.pool.get('queue.job')
        while len(unfinished_uuids) > 0:
            sleep(5)

            newcr = db.cursor()
            try:
                job_ids = job_obj.search(newcr, uid,
                                         [('uuid', 'in', unfinished_uuids)],
                                         context=context)
                for _job in job_obj.browse(newcr, uid, job_ids,
                                           context=context):
                    if _job.state == FAILED and _job.uuid not in failed_uuids:
                        failed_uuids.append(_job.uuid)
                        unfinished_uuids.remove(_job.uuid)
                    elif _job.state == DONE and _job.uuid not in done_uuids:
                        done_uuids.append(_job.uuid)
                        unfinished_uuids.remove(_job.uuid)
                newcr.commit()
            except Exception:
                newcr.rollback()
                raise
            finally:
                newcr.close()

        weekly_ids = []
        for uuid in done_uuids:
            weekly_ids += weekly_by_uuids[uuid]

        newcr = db.cursor()
        try:
            if len(weekly_ids) > 0:
                self._populate_weekly(newcr, uid, ids, context=context)
            newcr.commit()
        except Exception:
            newcr.rollback()
            raise
        finally:
            newcr.close()

        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.payroll.processing',
            'res_id': ids[0],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context,
        }


class dirty_attendances(orm.TransientModel):

    _name = 'hr.payroll.process.tmp.dirtyatt'
    _description = 'Temporary Tables for holding dirty weekly attendance'

    _columns = {
        'name': fields.char('Key'),
        'weekly_ids': fields.many2many('hr.attendance.weekly',
                                       'hr_payroll_processing_tmpweekly_rel',
                                       'wizard_id', 'weekly_id',
                                       'Weekly Attendances',
                                       readonly=True),
    }
