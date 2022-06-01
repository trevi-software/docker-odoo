#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Clear ICT Solutions <info@clearict.com>.
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

from time import sleep

from openerp import netsvc
from openerp import pooler
from openerp.addons.connector.queue.job import job, related_action, DONE, FAILED
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.exception import FailedJobError
from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools.translate import _

import logging
_logger = logging.getLogger(__name__)

@job(default_channel='root.payroll')
def payslip_run_by_department(session, model_name, dept_id, register_id, ee_ids,
                              date_start, date_end, annual_pay_periods, psa_codes):
    
    dept_obj = session.pool.get('hr.department')
    ee_obj = session.pool.get('hr.employee')
    slip_obj = session.pool.get('hr.payslip')
    run_obj = session.pool.get('hr.payslip.run')
    pp_obj = session.pool.get('hr.payroll.period')
    
    # First, check to make sure the register exists (it may have been superceded)
    #
    search_reg_id = session.pool.get('hr.payroll.register').search(session.cr,
                                                                   session.uid,
                                                                   [('id', '=', register_id)],
                                                                   context=session.context)
    if len(search_reg_id) == 0:
        _logger.warning('payroll register no longer exists')
        return
    
    dept = dept_obj.browse(session.cr, session.uid, dept_id, context=session.context)
    
    run_res = {
        'name': dept.complete_name,
        'date_start': date_start,
        'date_end': date_end,
        'register_id': register_id,
        'department_ids': [(6, 0, [dept.id])],
    }
    run_id = run_obj.create(session.cr, session.uid, run_res, context=session.context)
 
    # Create a pay slip for each employee in each department that has
    # a contract in the pay period schedule of this pay period
    #   
    slip_ids = []
    for ee in ee_obj.browse(session.cr, session.uid, ee_ids, context=session.context):
        
        #_logger.warning('Employee: %s', ee.name)
        slip_id = pp_obj.create_payslip(session.cr, session.uid, ee.id, date_start, date_end, psa_codes,
                                        run_id, annual_pay_periods, context=session.context)
        if slip_id != False:
            slip_ids.append(slip_id)
    
    # Calculate payroll for all the pay slips in this batch (run)
    slip_obj.compute_sheet(session.cr, session.uid, slip_ids, context=session.context)

class PayrollPeriodEndConnector(orm.TransientModel):
    
    _inherit = 'hr.payroll.period.end.1'
    
    def create_payslip_runs(self, cr, uid, period_id, previous_register_id, register_values, dept_ids, contract_ids,
                            date_start, date_end, annual_pay_periods, context=None):
        
        contract_obj = self.pool.get('hr.contract')
        dept_obj = self.pool.get('hr.department')
        ee_obj = self.pool.get('hr.employee')
        reg_obj = self.pool.get('hr.payroll.register')
        period_obj = self.pool.get('hr.payroll.period')
        
        # Get Pay Slip Amendments, Employee ID, and the amount of the amendment
        #
        psa_codes = []
        psa_ids = self._get_confirmed_amendments(cr, uid, context)
        for psa in self.pool.get('hr.payslip.amendment').browse(cr, uid, psa_ids, context=context):
            psa_codes.append((psa.employee_id.id, psa.input_id.code, psa.amount))
        
        # Keep track of employees that have already been included
        seen_ee_ids = []
        
        # Create payslip batch (run) for each department
        #
        job_uuids = []
        db, pool = pooler.get_db_and_pool(cr.dbname)
        newcr = db.cursor()
        try:
            session = ConnectorSession(newcr, uid, context)
            
            # Remove any pre-existing payroll registers
            if previous_register_id:
                self._remove_register(newcr, uid, previous_register_id, context)
            
            # Create Payroll Register
            register_id = reg_obj.create(newcr, uid, register_values, context=context)
            
            record = reg_obj.browse(newcr, uid, register_id, context=context)
            
            for dept in dept_obj.browse(newcr, uid, dept_ids, context=context):
                ee_ids = []
                c_ids = contract_obj.search(newcr, uid, [('id', 'in', contract_ids),
                                                      ('date_start', '<=', date_end.strftime(OE_DFORMAT)),
                                                      '|', ('date_end', '=', False),
                                                           ('date_end', '>=', date_start.strftime(OE_DFORMAT)),
                                                      '|', ('department_id.id', '=', dept.id),
                                                           ('employee_id.department_id.id', '=', dept.id),
                                                     ], context=context)
                c2_ids = contract_obj.search(newcr, uid, [('id', 'in', contract_ids),
                                                       ('date_start', '<=', date_end.strftime(OE_DFORMAT)),
                                                      '|', ('date_end', '=', False),
                                                           ('date_end', '>=', date_start.strftime(OE_DFORMAT)),
                                                       ('employee_id.status', 'in', ['pending_inactive', 'inactive']),
                                                       '|', ('job_id.department_id.id', '=', dept.id),
                                                            ('end_job_id.department_id.id', '=', dept.id),
                                                      ], context=context)
                for i in c2_ids:
                    if i not in c_ids:
                        c_ids.append(i)
                
                c_data = contract_obj.read(newcr, uid, c_ids, ['employee_id'], context=context)
                for data in c_data:
                    if (data['employee_id'][0] not in ee_ids) and (data['employee_id'][0] not in seen_ee_ids):
                        ee_ids.append(data['employee_id'][0])
                        seen_ee_ids.append(data['employee_id'][0])
    
                _logger.warning('Department: %s', dept.complete_name)
                if len(ee_ids) == 0:
                    continue
                
                # Alphabetize
                ee_ids = ee_obj.search(newcr, uid, [('id', 'in', ee_ids),
                                                 '|', ('active', '=', False), ('active', '=', True)],
                                       context=context)
                
                description = _("Create Pay Slip Run for %s in %s") % \
                                    (dept.complete_name, record.name)
                job_uuid = payslip_run_by_department.delay(session,
                                                           'hr.payroll.register',
                                                           dept.id,
                                                           register_id,
                                                           ee_ids,
                                                           date_start,
                                                           date_end,
                                                           annual_pay_periods,
                                                           psa_codes,
                                                           description=description)
                job_uuids.append(job_uuid)
            
            # Attach payroll register to this pay period
            period_obj.write(newcr, uid, period_id, {'register_id': register_id}, context=context)
            
            # Mark the pay period as being in the payroll generation stage
            netsvc.LocalService('workflow').trg_validate(uid, 'hr.payroll.period', period_id, 'generate_payslips', newcr)
            
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
        _logger.warning('len unfinished uuids: %s', len(unfinished_uuids))
        while len(unfinished_uuids) > 0:
            sleep(10)
            
            newcr = db.cursor()
            try:
                job_ids = job_obj.search(newcr, uid, [('uuid', 'in', unfinished_uuids)],
                                         context=context)
                for job in job_obj.browse(newcr, uid, job_ids, context=context):
                    if job.state == FAILED and job.uuid not in failed_uuids:
                        failed_uuids.append(job.uuid)
                        unfinished_uuids.remove(job.uuid)
                        _logger.warning('Removed failed uuid %s', job.uuid)
                    elif job.state == DONE and job.uuid not in done_uuids:
                        done_uuids.append(job.uuid)
                        unfinished_uuids.remove(job.uuid)
                        _logger.warning('Removed done uuid %s', job.uuid)
                newcr.commit()
            except Exception:
                newcr.rollback()
                raise
            finally:
                newcr.close()    

        return
