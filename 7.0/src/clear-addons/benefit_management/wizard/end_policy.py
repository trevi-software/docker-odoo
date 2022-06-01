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

from datetime import datetime

import netsvc
from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.translate import _

class employee_set_inactive(orm.TransientModel):
    
    _name = 'hr.benefit.policy.end'
    _description = 'Benefit Policy Termination Wizard'
    
    _columns = {
        'date': fields.date('End Date', required=True),
    }
    
    _defaults = {
        'date': datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)
    }
    
    def _get_policy(self, cr, uid, context=None):
        
        if context == None:
            context = {}
        
        return context.get('end_benefit_policy_id', False)
    
    def end_policy(self, cr, uid, ids, context=None):
        
        policy_id = self._get_policy(cr, uid, context=context)
        if not policy_id:
            raise orm.except_orm(_('Programming Error'), _('Unable to determine Policy ID.'))
        
        data = self.read(cr, uid, ids[0], ['date'],
                         context=context)
        self.pool.get('hr.benefit.policy').write(cr, uid, policy_id, {'end_date': data['date']},
                                                 context=context)
        wkf = netsvc.LocalService('workflow')
        wkf.trg_validate(uid, 'hr.benefit.policy', policy_id, 'signal_done', cr)
        return {'type': 'ir.actions.act_window_close'}
