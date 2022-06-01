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

{
    'name': 'Stock Transfer',
    'version': '1.0',
    'category': 'Generic Modules/Stock',
    'author':'Michael Telahun Makonnen <miket@clearict.com>',
    'description': """
Inter-Store Transfers
=====================
Stock Transfer Orders between warehouses / stock locations.
    """,
    'website':'http://miketelahun.wordpress.com',
    'depends': [
        'stock',
    ],
    'init_xml': [
        'data/stock.xml',
    ],
    'update_xml': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'report/report_stock_move_view.xml',
        'stock_report.xml',
        'stock_sequence.xml',
        'stock_view.xml',
        'stock_picking_view.xml',
        'stock_requisition_view.xml',
        'wizard/goods_consumption.xml',
        'wizard/stock_transfer.xml',
        'stock_workflow.xml',
        'res_users_view.xml',
    ],
    'test': [
    ],
    'demo_xml': [
    ],
    'installable': True,
    'active': False,
}
