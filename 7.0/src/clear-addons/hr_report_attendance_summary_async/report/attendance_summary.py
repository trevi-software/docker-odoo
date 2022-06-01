# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016 Clear ICT Solutions <info@clearict.com>.
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

import csv
import uuid
import os
from datetime import datetime
from time import sleep

from openerp import pooler
from openerp.addons.connector.queue.job import job, DONE, FAILED
from openerp.addons.connector.session import ConnectorSession
from openerp.service.locking import RecordRLock
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DATEFORMAT
from openerp.tools import float_is_zero
from openerp.tools.translate import _
from openerp.report import report_sxw

TMPDIR = '/tmp'
TMPFILE_EE_IDS = TMPDIR + '/employee_ids'
TMPFILE_EE_SEEN_IDS = TMPDIR + '/employee_seen_ids'
TMPFILE_EE_DICT = TMPDIR + '/employee_dict'

g_employee_dictionary = {}


def get_employee_ids(session, department_id, start_date, end_date,
                     csv_ee_list, csv_seen_ids):

    lock = RecordRLock(session.cr.dbname, 'g_seen_employee_ids', 0)

    cr = session.cr
    uid = session.uid
    c_obj = session.pool.get('hr.contract')
    ee_obj = session.pool.get('hr.employee')
    c_ids = c_obj.search(cr, uid,
                         ['|', ('job_id.department_id', '=', department_id),
                               ('end_job_id.department_id', '=', department_id),
                          ('date_start', '<=', end_date),
                          '|', ('date_end', '=', False),
                               ('date_end', '>=', start_date)])
    ee_ids = []
    ee_seen_ids = []
    cdata = c_obj.read(cr, uid, c_ids, ['employee_id'])
    lock.acquire()
    try:
        with open(csv_seen_ids, 'rb') as csvfile:
            seen_ids_reader = csv.reader(csvfile)
            for row in seen_ids_reader:
                ee_seen_ids.append(int(row[0]))
    
        ee_ids = [data['employee_id'][0] for data in cdata
                  if ((data['employee_id'][0] not in ee_ids)
                      and (data['employee_id'][0] not in ee_seen_ids))]
    
        with open(csv_seen_ids, 'a+') as csvfile:
            seen_ids_writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
            for _id in ee_ids:
                seen_ids_writer.writerow(str(_id))
    finally:
        lock.release()

    lock = RecordRLock(session.cr.dbname, 'g_employee_list', 0)
    lock.acquire()
    try:
        with open(csv_ee_list, 'a+') as csvfile:
            ids_writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
            str_ee_ids = ';'.join(map(str, ee_ids))
            ids_writer.writerow([str(department_id)] + [str_ee_ids])
    finally:
        lock.release()

    # re-order
    return ee_obj.search(cr, uid, [('id', 'in', ee_ids),
                                   '|', ('active', '=', True),
                                        ('active', '=', False)])


@job
def get_employee_data(session, model_name, department_id,
                      start_date, end_date,
                      csv_ee_list, csv_seen_ids, csv_ee_dict):

    cr = session.cr
    uid = session.uid
    payslip_obj = session.pool.get('hr.payslip')
    ee_obj = session.pool.get('hr.employee')
    lock = RecordRLock(session.cr.dbname, 'g_employee_dictionary', 0)

    dtStart = datetime.strptime(start_date, OE_DATEFORMAT).date()
    dtEnd = datetime.strptime(end_date, OE_DATEFORMAT).date()
    ee_ids = get_employee_ids(session, department_id, start_date, end_date,
                              csv_ee_list, csv_seen_ids)
    for ee in ee_obj.browse(cr, uid, ee_ids):
        datas = []
        for c in ee.contract_ids:
            dtCStart = False
            dtCEnd = False
            if c.date_start: dtCStart = datetime.strptime(c.date_start, OE_DATEFORMAT).date()
            if c.date_end: dtCEnd = datetime.strptime(c.date_end, OE_DATEFORMAT).date()
            if (dtCStart and dtCStart <= dtEnd) and ((dtCEnd and dtCEnd >= dtStart) or not dtCEnd):
                datas.append({'contract_id': c.id,
                              'date_start': dtCStart > dtStart and dtCStart.strftime(OE_DATEFORMAT) or dtStart.strftime(OE_DATEFORMAT),
                              'date_end': (dtCEnd and dtCEnd < dtEnd) and dtCEnd.strftime(OE_DATEFORMAT) or dtEnd.strftime(OE_DATEFORMAT)})
        wd_lines = []
        for d in datas:
            wd = payslip_obj.get_worked_day_lines(
                cr, uid, [d['contract_id']], d['date_start'], d['date_end'])
            wd_lines += wd

        lock.acquire()
        try:
            with open(csv_ee_dict, 'a+') as csvfile:
                fnames = ['ee_id', 'code', 'number_of_days', 'number_of_hours',
                          'name', 'sequence', 'rate', 'contract_id']
                ee_writer = csv.DictWriter(csvfile, fieldnames=fnames,
                                           extrasaction='raise',
                                           quoting=csv.QUOTE_MINIMAL)
                for wd in wd_lines:
                    wd.update({'ee_id': ee.id})
                    ee_writer.writerow(wd)
        finally:
            lock.release()

    return


class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'init_employee_data': self.init_employee_data,
            'delete_employee_data': self.delete_employee_data,
            'get_worked_days': self.get_worked_days,
            'get_daily_ot': self.get_daily_ot,
            'get_nightly_ot': self.get_nightly_ot,
            'get_restday_ot': self.get_restday_ot,
            'get_holiday_ot': self.get_holiday_ot,
            'get_bunch_no': self.get_bunch_no,
            'get_awol': self.get_awol,
            'get_sickleave': self.get_sickleave,
            'get_no': self.get_no,
            'get_start': self.get_start,
            'get_end': self.get_end,
            'lose_bonus': self.lose_bonus,
            'get_paid_leave': self.get_paid_leave,
            'get_employee_list': self.get_employee_list,
        })

        self.start_date = False
        self.end_date = False
        self.ee_lines = {}
        self.no = 0
        self.department_id = False
        self.regular_hours = 8.0
        self.get_employee_data_ids = []
        self.key = uuid.uuid4().hex
        self.employee_ids_csv = False
        self.employee_seen_ids_csv = False
        self.employee_dict_csv = False

    def set_context(self, objects, data, ids, report_type=None):
        if data.get('form', False) and data['form'].get('start_date', False):
            self.start_date = data['form']['start_date']
        if data.get('form', False) and data['form'].get('end_date', False):
            self.end_date = data['form']['end_date']

        return super(Parser, self).set_context(objects, data, ids, report_type=report_type)

    def init_employee_data(self, departments):

        # Create files to store data
        #
        self.csv_ee_list = \
            '.'.join(map(str, [TMPFILE_EE_IDS, str(self.key), 'txt']))
        self.csv_seen_ids = \
            '.'.join(map(str, [TMPFILE_EE_SEEN_IDS, str(self.key), 'txt']))
        self.csv_ee_dict = \
            '.'.join(map(str, [TMPFILE_EE_DICT, str(self.key), 'txt']))
        f_ee_list = open(self.csv_ee_list, 'w+')
        f_seen_ids = open(self.csv_seen_ids, 'w+')
        f_ee_dict = open(self.csv_ee_dict, 'w+')
        f_ee_list.close()
        f_seen_ids.close()
        f_ee_dict.close()

        # Enqueue the jobs to read employee data per department
        #
        job_uuids = []
        db, pool = pooler.get_db_and_pool(self.cr.dbname)
        newcr = db.cursor()
        try:
            session = ConnectorSession(newcr, self.uid, None)
            for dept in departments:
                description = \
                    _("Read attendance summary for %s") % (dept.complete_name)
                job_uuid = get_employee_data.delay(
                    session, 'hr.department',
                    dept.id, self.start_date, self.end_date, self.csv_ee_list,
                    self.csv_seen_ids, self.csv_ee_dict,
                    description=description
                )
                job_uuids.append(job_uuid)

            newcr.commit()
        except Exception:
            newcr.rollback()
            raise
        finally:
            newcr.close()

        # Wait for all the jobs to finish
        #
        unfinished_uuids = job_uuids
        done_uuids = []
        failed_uuids = []
        job_obj = self.pool.get('queue.job')
        while len(unfinished_uuids) > 0:
            sleep(3)

            newcr = db.cursor()
            try:
                job_ids = job_obj.search(newcr, self.uid,
                                         [('uuid', 'in', unfinished_uuids)],
                                         context=None)
                for _job in job_obj.browse(newcr, self.uid, job_ids,
                                           context=None):
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

        # Read back data from files into global dict
        # It's not necessary to hold a lock because the writers are
        # finished at this point.
        #
        global g_employee_dictionary
        with open(self.csv_ee_dict, 'r') as csvfile:
            fnames = ['ee_id', 'code', 'number_of_days', 'number_of_hours',
                      'name', 'sequence', 'rate', 'contract_id']
            ee_reader = csv.DictReader(csvfile, fieldnames=fnames,
                                       quoting=csv.QUOTE_MINIMAL)
            for row_dict in ee_reader:
                if int(row_dict['ee_id']) not in g_employee_dictionary.keys():
                    g_employee_dictionary.update({
                        int(row_dict['ee_id']): []
                    })
                g_employee_dictionary[int(row_dict['ee_id'])].append({
                    'code': row_dict['code'],
                    'number_of_days': row_dict['number_of_days'],
                    'number_of_hours': row_dict['number_of_hours'],
                    'name': row_dict['name'],
                    'sequence': row_dict['sequence'],
                    'rate': row_dict['rate'],
                    'contract_id': row_dict['contract_id'],
                })

        return

    def delete_employee_data(self):

        if os.path.isfile(self.csv_ee_dict):
            os.remove(self.csv_ee_dict)
        if os.path.isfile(self.csv_ee_list):
            os.remove(self.csv_ee_list)
        if os.path.isfile(self.csv_seen_ids):
            os.remove(self.csv_seen_ids)
        return

    def get_employee_ids(self, department_id):

        # We don't need a lock to read the global variable because
        # all writes will have ended by now. No chance of inconsistent state.
        #
        ee_ids = []
        with open(self.csv_ee_list, 'r') as csvfile:
            ids_reader = csv.reader(csvfile)
            for row in ids_reader:
                if int(row[0]) == department_id:
                    ee_ids = row[1].split(';')
                    if len(ee_ids) == 1 and ee_ids[0] == '':
                        ee_ids.remove('')

        import logging
        _l = logging.getLogger(__name__)
        _l.warning('ee_ids: %s,%s', ee_ids, type(ee_ids))
        if len(ee_ids) == 0:
            return ee_ids


        # re-order
        ee_obj = self.pool.get('hr.employee')
        return ee_obj.search(self.cr, self.uid, [('id', 'in', ee_ids),
                                                 '|', ('active', '=', True),
                                                      ('active', '=', False)])

    def get_employee_list(self, department_id):

        ee_ids = self.get_employee_ids(department_id)
        return self.pool.get('hr.employee').browse(self.cr, self.uid, ee_ids)

    def get_start(self):
        return datetime.strptime(self.start_date, OE_DATEFORMAT).strftime('%B %d, %Y')

    def get_end(self):
        return datetime.strptime(self.end_date, OE_DATEFORMAT).strftime('%B %d, %Y')

    def get_no(self, department_id):

        if not self.department_id or self.department_id != department_id:
            self.department_id = department_id
            self.no = 1
        else:
            self.no += 1

        return self.no

    def _round(self, num):

        return round(num, 1)

    def get_worked_days(self, employee_id):

        global g_employee_dictionary
        total = 0
        for line in g_employee_dictionary[employee_id]:
            if line['code'] in ['WORK100']:
                total += float(line['number_of_hours']) / self.regular_hours
        return self._round(total)

    def get_paid_leave(self, employee_id):

        global g_employee_dictionary
        total = 0
        paid_leaves = ['LVANNUAL', 'LVBEREAVEMENT', 'LVCIVIC', 'LVMATERNITY',
                       'LVMMEDICAL', 'LVPTO', 'LVWEDDING', 'LVTRAIN']
        for line in g_employee_dictionary[employee_id]:
            if line['code'] in paid_leaves:
                total += (not float_is_zero(float(line['number_of_days']),
                                            precision_digits=1)) \
                            and float(line['number_of_days']) or 0
        return total

    def get_daily_ot(self, employee_id):

        global g_employee_dictionary
        total = 0
        for line in g_employee_dictionary[employee_id]:
            if line['code'] in ['WORKOTD']:
                total += (not float_is_zero(float(line['number_of_hours']),
                                            precision_digits=1)) \
                            and float(line['number_of_hours']) or 0
        return total

    def get_nightly_ot(self, employee_id):

        global g_employee_dictionary
        total = 0
        for line in g_employee_dictionary[employee_id]:
            if line['code'] in ['WORKOTN']:
                total += (not float_is_zero(float(line['number_of_hours']),
                                            precision_digits=1)) \
                            and float(line['number_of_hours']) or 0
        return total

    def get_restday_ot(self, employee_id):

        global g_employee_dictionary
        total = 0
        for line in g_employee_dictionary[employee_id]:
            if line['code'] in ['WORKRST', 'WORKOTR']:
                total += (not float_is_zero(float(line['number_of_hours']),
                                            precision_digits=1)) \
                            and float(line['number_of_hours']) or 0
        return total

    def get_holiday_ot(self, employee_id):

        global g_employee_dictionary
        total = 0
        for line in g_employee_dictionary[employee_id]:
            if line['code'] in ['WORKHOL', 'WORKOTH']:
                total += (not float_is_zero(float(line['number_of_hours']),
                                            precision_digits=1)) \
                            and float(line['number_of_hours']) or 0
        return total

    def get_bunch_no(self, employee_id):

        global g_employee_dictionary
        total = 0
        for line in g_employee_dictionary[employee_id]:
            if line['code'] in ['BUNCH']:
                total += int(float(line['number_of_hours']))
        return total

    def get_awol(self, employee_id):

        global g_employee_dictionary
        total = 0
        for line in g_employee_dictionary[employee_id]:
            if line['code'] in ['AWOL']:
                total += float(line['number_of_hours']) / self.regular_hours
        return self._round(total)

    def get_sickleave(self, employee_id):

        global g_employee_dictionary
        total = 0
        for line in g_employee_dictionary[employee_id]:
            if line['code'] in ['LVSICK', 'LVSICK50']:
                total += (not float_is_zero(float(line['number_of_days']),
                                            precision_digits=1)) \
                            and float(line['number_of_days']) or 0
            leave_obj = self.pool.get('hr.holidays')
            leave_ids = leave_obj.search(self.cr, self.uid, [('employee_id', '=', employee_id),
                                                             ('date_from', '<=', self.end_date),
                                                             ('date_to', '>=', self.start_date),
                                                             ('type', '=', 'remove'),
                                                             ('state', 'in', ['validate', 'validate1'])])
            lv_days = 0
            for leave in leave_obj.browse(self.cr, self.uid, leave_ids):
                lv_days += abs(leave.number_of_days)
            if lv_days < total:
                total = lv_days
        return total

    def lose_bonus(self, employee_id):

        global g_employee_dictionary
        loseit = False
        for line in g_employee_dictionary[employee_id]:
            if line['code'] in ['AWOL', 'TARDY', 'NFRA', 'WARNW'] \
                and not float_is_zero(float(line['number_of_hours']),
                                      precision_digits=1):
                loseit = True
        return loseit
