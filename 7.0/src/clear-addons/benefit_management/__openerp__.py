#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2013,2014 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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
    'name': 'Benefit Management',
    'version': '1.0',
    'category': 'Generic Modules/Human Resources',
    'description': """
Manage Employee Benefits
========================

    * Create benefits and their respective advantages and premiums
    * Advantages and Premiums have effective dates to reflect changes over time
    * Benefits can be linked to payroll
        * Choose the 'Allowance' type for advantages
        * Choose the 'Deduction' type for premiums
        * Use Salary Rules to integrate them in to Payroll Structures
        * Information about the benefits are available to Salary Rules in a top-level 'benefits' dictionary
            - Example: result = benefits.<CODE>.premium_amount
        * The available fields are:
            - qty: the number of policies of this type found
            - advantage_amount: the money to add
            - premium_amount: the money to deduct
            - ppf: 1 if the policy was active for the entire payroll period; less than 1 if it was active only for a fraction of the payroll period.
    """,
    'author':'Michael Telahun Makonnen <mmakonnen@gmail.com>',
    'website':'http://miketelahun.wordpress.com',
    'depends': [
        'decimal_precision',
        'hr',
        'hr_payroll_extension',
        'hr_security',
    ],
    'init_xml': [
    ],
    'update_xml': [
        'security/ir.model.access.csv',
        'wizard/end_policy.xml',
        'wizard/enroll_employee_view.xml',
        'wizard/enroll_multi_employee_view.xml',
        'benefit_view.xml',
        'benefit_sequence.xml',
        'benefit_claim_workflow.xml',
        'benefit_policy_workflow.xml',
        'premium_payment_workflow.xml',
    ],
    'test': [
    ],
    'demo_xml': [
    ],
    'installable': True,
    'active': False,
}
