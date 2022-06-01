#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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

import threading

import openerp

def new_cr(db_name):
    
    db = openerp.sql_db.db_connect(db_name)
    threading.current_thread().dbname = db_name
    cr = db.cursor()
    
    return cr

def start_transaction(cr):
    
    db_name = cr.dbname
    openerp.modules.registry.RegistryManager.check_registry_signaling(db_name)
    registry = openerp.pooler.get_pool(db_name)
    
    return registry

def close_transaction(cr):
    
    db_name = cr.dbname
    cr.commit()
    openerp.modules.registry.RegistryManager.signal_caches_change(db_name)
    return

def rollback_transaction(cr):
    
    cr.rollback()
    return

def close_cr(cr):
    
    cr.close()
    if hasattr(threading.current_thread(), 'dbname'): # cron job could have removed it as side-effect
        del threading.current_thread().dbname
    return
