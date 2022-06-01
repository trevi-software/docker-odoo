# -*- coding: utf-8 -*-
# Copyright 2017 Michael Telahun Makonnen
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp.osv import fields, osv


class HrDepartment(osv.Model):

    _inherit = 'hr.department'

    _columns = {
            'active': fields.boolean('Active'),
    }

    _defaults = {
            'active': True,
    }
