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

{
    'name': 'Post-Closing Payroll Amendment',
    'category': 'Human Resources',
    'author': 'Michael Telahun Makonnen',
    'website':'http://miketelahun.wordpress.com',
    'version': '1.0',
    'description': """
Payroll Period Post-Closing Payroll Amendment
=============================================

This module allows the modification or payroll inputs, such as attendances and
leaves, and re-calculation of an employee's payslip. The modified amount is then
added to a future payroll period as a payslip amendment.
    """,
    'depends': [
        'hr_payroll',
        'hr_payroll_period',
        'hr_payslip_amendment',
        'hr_security',
    ],
    'init_xml': [],
    'update_xml': [
        'security/hr_security.xml',
        'security/ir.model.access.csv',
        'data/payroll_data.xml',
        'postclose_amendment_workflow.xml',
        'hr_payroll_view.xml',
        'wizard/batch_adjustment_view.xml',
        'report.xml',
     ],
    'test': [
    ],
    'demo_xml': [],
    'active': False,
    'installable': True,
}
