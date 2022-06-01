# -*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 Clear ICT Solutions <info@clearict.com>.
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify it
#    it under the terms of the GNU Affero General Public License as published
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
    'name': 'Model Locking Mechanism',
    'version': '1.0',
    'category': 'Generic Modules',
    'author': 'Clear ICT Solutions <info@clearict.com>',
    'description': """
Locking System for Models
=========================
Helper module for other modules to synchronize modification of objects.
This module is not intended for end-users. It is for developers to use in
their own modules.

USAGE:
======
At the beginning of the current session/transaction:
    key = model_lock_obj.create_session_key(cr, uid, context=context)
    context = model_lock_obj.persist_session_key(cr, uid, key, context=context)

From this point on passing context as you normally would will propagate the
session key so that the locking code can properly figure out if you are
entitled to lock/unlock an object or not. If it cannot find a session key it
will raise an Exception.

To lock and unlock objects:
    lock = False
    db, pool = pooler.get_db_and_pool(cr.dbname)
    newcr = db.cursor()
    try:
        lock = model_lock_obj.try_lock(newcr, uid, 'model.name',
                                       module_name='module_name',
                                       context=context)
    except:
        if lock:
            model_lock_obj.unlock(newcr, uid, lock, context=context)
    ...
    do_something
    ...
    model_lock_obj.unlock(newcr, uid, lock, context=context)

To check if you currently own a lock on a model:
    if model_lock_obj.has_lock(cr, uid, 'model.name', context=context):
        do_something
        ...
    """,
    'website': 'http://www.clearict.com',
    'depends': [
        'base',
    ],
    'init_xml': [
    ],
    'update_xml': [
        'security/ir.model.access.csv',
        'lock_view.xml',
    ],
    'test': [
    ],
    'demo_xml': [
    ],
    'installable': True,
    'active': False,
}
