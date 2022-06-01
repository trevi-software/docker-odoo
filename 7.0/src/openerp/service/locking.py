# -*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016 Clear ICT Solutions <info@clearict.com>.
#    All Rights Reserved.
#       @author: Michael Telahun Makonnen <miket@clearict.com>
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

import logging
import os
import uuid

_logger = logging.getLogger(__name__)

try:
    from lockfile import LockFile, AlreadyLocked, LockTimeout
except ImportError:
    _logger.info('For file based record locking to work you must '
                 'install the lockfile python module.')

LOCK_DIR = u'/tmp/OdooLock'
DEFAULT_TIMEOUT = 60


# Good analysis of file locking:
# https://loonytek.com/2015/01/15/advisory-file-locking-differences-between-posix-and-bsd-locks/
#
# Usage:
#    try:
#        lock = RecordRLock(cr.dbname, 'model.name', 'id')
#        lock.acquire()
#        ...
#    finally:
#        lock.release()
#
class RecordRLock:

    def __init__(self, dbname, model_name, model_id):

        self.dbname = dbname
        self.model_name = model_name
        self.model_id = model_id
        self.pid = os.getpid()
        self.filename = os.path.join(
            LOCK_DIR, dbname + u'.' + model_name + u'.' + str(model_id))
        self.recurse_count = 0

        # This will create it if it does not exist already
        if not os.path.exists(LOCK_DIR):
            os.makedirs(LOCK_DIR, 0700)

        self.lock = LockFile(self.filename)
        _logger.debug('Initialized lockfile (%s) %s', self.pid, self.filename)

    def acquire(self, blocking=True):

        res = False
        tout = DEFAULT_TIMEOUT
        if not blocking:
            tout = 0

        if self.lock.i_am_locking():
            self.recurse_count += 1
            return True

        while not self.lock.i_am_locking():
            try:
                _logger.debug('Trying to acquire lockfile (%s) %s',
                              self.pid, self.filename)
                self.lock.acquire(timeout=tout)
                res = True
                _logger.debug('Acquired lockfile (%s) %s',
                              self.pid, self.filename)
            except AlreadyLocked:
                assert not blocking, 'Received AlreadyBlocked when blocking'
                res = False
                _logger.debug('Lockfile is locked by someone else (%s) %s',
                              self.pid, self.filename)
                break
            except LockTimeout:
                _logger.debug('Lockfile timeout. Retrying (%s) %s',
                              self.pid, self.filename)
        return res

    def release(self):

        if self.recurse_count > 0:
            self.recurse_count -= 1
            assert self.recurse_count >= 0, "Negative recurse count!"
            _logger.debug('Lockfile unrecurs (%s) %s', self.pid, self.filename)
        else:
            self.lock.release()
            _logger.debug('Lockfile released (%s) %s', self.pid, self.filename)
        return

    def make_recursive_lock(self):

        self.filename = self.filename + '.' + str(uuid.uuid4())
        del self.lock
        self.lock = LockFile(self.filename)
        _logger.debug('Recursion detected. New lockfile (%s) %s',
                      self.pid, self.filename)
