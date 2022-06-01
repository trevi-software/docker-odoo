# -*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 Clear ICT Solutions <info@clearict.com>.
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

import uuid
from psycopg2.extensions import TransactionRollbackError

from openerp import pooler
from openerp.osv import fields, orm
from openerp.tools.translate import _

import logging
_l = logging.getLogger(__name__)

SESSIONKEY_NAME = 'model_lock_session_key'


class model_lock(orm.Model):

    #
    # Some sort of jury-rigged lock on models.
    #
    # model_id = 0 is used for a global lock on the object. If model is
    # non-zero it is assumed to refer to a single record.
    #
    # When used by a caller the try_lock() and unlock() calls should
    # be enclosed in a try..except..finally block that releases the
    # lock properly.
    #

    _name = 'lock.global'
    _description = 'Model Level Global Lock'

    _columns = {
        'model_name': fields.char('Record Model', required=True),
        'module': fields.char('Module Name'),
        'owner_id': fields.many2one('res.users', 'Owner', required=True),
        'session_key': fields.char('Session Key', required=True),
        'count': fields.integer('Lock Count'),
    }

    _sql_constraints = [
        ('model_name_session_unique',
         'UNIQUE(model_name,session_key)',
         _('Record model and session key must be unique!'))
    ]

    def name_get(self, cr, uid, ids, context=None):

        if isinstance(ids, (long, int)):
            ids = [ids]
        res = []
        for lock in self.browse(cr, uid, ids, context=context):
            res.append((lock.id,
                        lock.model_name + ':' + lock.session_key
                        + ' owned by ' + str(lock.owner_id.name)))
        return res

    def create_session_key(self, cr, uid, context=None):

        # XXX - Does this need to be more random?
        key = uuid.uuid4().hex

        return key

    def persist_session_key(self, cr, uid, key, context=None):

        if context is None:
            context = {}
        context.update({SESSIONKEY_NAME: key})

        return context

    def get_session_key(self, cr, uid, context=None):

        # Session key is obtained from the context if we are recursively
        # locking on an object. WE REQUIRE A SESSION KEY.
        #
        key = (context is not None)                 \
            and context.get(SESSIONKEY_NAME, None)  \
            or None
        if context is None or key is None:
            raise orm.except_orm(_('Programming Error'),
                                 _('Model locking requires a session key.'))

        return key

    def try_lock(self, cr, uid, model_name, module_name='', context=None):

        res = False
        retry = True
        retry_count = 100
        db, pool = pooler.get_db_and_pool(cr.dbname)
        while retry and retry_count > 0:
            retry = False
            retry_count -= 1
            newcr = db.cursor()
            try:
                res = self._try_lock(newcr, uid, model_name,
                                     module_name=module_name, context=context)
                newcr.commit()
            except TransactionRollbackError as exTR:
                newcr.rollback()

                # Record locking conflict. Retry the lock.
                #
                if exTR.pgcode == '40001':
                    _l.warning('TransactionRollbackError: (+)retrying')
                    retry = True
                else:
                    _l.warning('TransactionRollbackError: (+)quiting')
                    raise
            except Exception:
                newcr.rollback()

                # If someone already holds the lock, throw our own exception.
                # Otherwise something else caused the exception so pass it
                # on up the chain.
                #
                l_ids = self.search(newcr, uid,
                                    [('model_name', '=', model_name)],
                                    context=context)
                if len(l_ids) > 0:
                    _o = self.browse(newcr, uid, l_ids[0], context=context)\
                        .owner_id.name
                    raise orm.except_orm(
                        _('Access Temporarily Denied'),
                        _('User %s has temporarily locked access to this '
                          'resource. Please try again later.' % (_o)))

                raise
            finally:
                newcr.close()

        return res

    def _try_lock(self, cr, uid, model_name, module_name='', context=None):

        res = False
        key = self.get_session_key(cr, uid, context=context)

        #
        # My use of a try..except block here is an attempt to make my creation
        # of the lock as atomic as possible. If the _sql_constraint above is
        # applied properly the attempt to create the record should fail.
        # If the user is trying to lock a model s/he already owns the lock for,
        # let the call succeed.
        #

        l_ids = self.search(cr, uid, [('model_name', '=', model_name),
                                      ('owner_id', '=', uid),
                                      ('session_key', '=', key)],
                            context=context)
        if len(l_ids) > 0:
            res = l_ids[0]
            # XXX These two steps should be atomic. According to the
            #     current ORM this thread/worker should be the only one
            #     able to write() or unlink() this record.
            #     NOTE: if the same user opens another window and tries
            #           another operation that requires this lock s/he will
            #           succeed. Warn users not shoot themselves in the foot!
            #
            l = self.browse(cr, uid, res, context=context)
            self.write(cr, uid, res, {'count': l.count + 1})
        else:
            res = self.create(cr, uid, {'model_name': model_name,
                                        'module': module_name,
                                        'owner_id': uid,
                                        'session_key': key},
                              context=context)

        return res

    def unlock(self, cr, uid, lock_id, context=None):

        retry = True
        retry_count = 100
        db, pool = pooler.get_db_and_pool(cr.dbname)
        while retry and retry_count > 0:
            retry = False
            retry_count -= 1
            newcr = db.cursor()
            try:
                self._unlock(newcr, uid, lock_id, context=context)
                newcr.commit()
            except TransactionRollbackError as exTR:
                newcr.rollback()

                # Record locking conflict. Retry the lock.
                #
                if exTR.pgcode == '40001':
                    retry = True
                else:
                    _l.warning('TransactionRollbackError: (-)quiting')
                    raise
            except Exception:
                newcr.rollback()
                raise
            finally:
                newcr.close()

        return

    def _unlock(self, cr, uid, lock_id, context=None):

        key = self.get_session_key(cr, uid, context=context)
        lock = self.browse(cr, uid, lock_id, context=context)
        if lock.owner_id.id == uid and lock.session_key == key:
            if lock.count == 0:
                self.unlink(cr, uid, lock_id, context=context)
            elif lock.count > 0:
                self.write(cr, uid, lock_id, {'count': lock.count - 1},
                           context=context)
            else:
                orm.except_orm('Programming Error',
                               'Negative application level lock count!')
        return

    def has_lock(self, cr, uid, model_name, context=None):

        if not model_name:
            return False

        res = False
        key = self.get_session_key(cr, uid, context=context)
        db, pool = pooler.get_db_and_pool(cr.dbname)
        newcr = db.cursor()
        try:
            l_ids = self.search(newcr, uid, [('model_name', '=', model_name),
                                             ('owner_id', '=', uid),
                                             ('session_key', '=', key)],
                                context=context)
            if len(l_ids) > 0:
                res = True
            newcr.commit()
        except Exception:
            newcr.rollback()
        finally:
            newcr.close()

        return res
