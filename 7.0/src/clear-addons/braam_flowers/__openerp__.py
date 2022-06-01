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

{
    'name': 'Braam Flowers Data',
    'version': '1.0',
    'category': 'Generic Modules/Company Data',
    'author':'Michael Telahun Makonnen <mmakonnen@gmail.com>',
    'description': """
Client Data and Module Dependencies
===================================
    - Departments
    - Job Positions
    - Employee Data
    - Contract Data
    - Payroll Period Schedules
    - Payroll rules
    - Payroll structures
    - Schedule Templates
    """,
    'website':'http://miketelahun.wordpress.com',
    'depends': [
        'contacts',
        'ethiopic_calendar',
        'hr_attendance_batch_entry',
        'hr_braam_idcard',
        'hr_bunching',
        'hr_bunching_incentive',
        'hr_contract_reference',
        'hr_contract_state',
        'hr_emergency_contact',
        'hr_employee_education',
        'hr_employee_id',
        'hr_employee_state',
        'hr_family',
        'hr_holidays_by_schedule',
        'hr_infraction',
        'hr_initial_annual_leave',
        'hr_job_hierarchy',
        'hr_labour_recruitment',
        'hr_labour_union',
        'hr_payroll_extension',
        'hr_payroll_period',
        'hr_performance_incentive',
        'hr_policy_accrual',
        'hr_policy_ot',
        'hr_schedule',
        'hr_simplify',
        'hr_transfer',
        'hr_wage_increment',
        'hr_webcam',
        'l10n_et_hr',
        'l10n_et_hr_public_holidays',
        'l10n_et_toponym',
        'l10n_et_tz',
        'report_aeroo',
        'report_aeroo_ooo',
    ],
    'init_xml': [
        'data/leave_types_data.xml',
        'data/braam_flowers_data.xml',
        #'data/res.partner.csv',
        #'data/hr.employee.csv',
        #'data/hr.contract.csv',
        'data/user_data.xml',
    ],
    'update_xml': [
    ],
    'test': [
    ],
    'demo_xml': [
    ],
    'installable': True,
    'active': False,
}
