# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP, Management module for Jasper Server
#    Copyright (C) 2011 SYLEAM (<http://www.syleam.fr/>)
#              Christophe CHAUVET <christophe.chauvet@syleam.fr>
#
#    This file is a part of jasper_server
#
#    jasper_server is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    jasper_server is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv
from common import registered_report
import netsvc
logger = netsvc.Logger()


class IrActionReport(osv.osv):
    _inherit = 'ir.actions.report.xml'

    def __init__(self, pool, cr):
        """
        Extend to add jasper as key for printing service
        """
        super(IrActionReport, self).__init__(pool, cr)
        logger.notifyChannel('init:module jasper_server ', netsvc.LOG_INFO, 'Add jasper as key')
        res = self._columns['report_type'].selection
        if 'jasper' not in [k for k, v in res]:
            self._columns['report_type'].selection.append(('jasper', 'Jasper'))

    def register_all(self, cursor):
        """
        Register all jasper report
        """
        logger.notifyChannel('jasper_server', netsvc.LOG_INFO, '====[REGISTER JASPER REPORT]========================')
        value = super(IrActionReport, self).register_all(cursor)
        cursor.execute("SELECT id, report_name FROM ir_act_report_xml WHERE report_type = 'jasper'")
        records = cursor.dictfetchall()
        for record in records:
            registered_report(record['report_name'])
        logger.notifyChannel('jasper_server', netsvc.LOG_DEBUG, '====[END REGISTER JASPER REPORT]====================')
        return value

IrActionReport()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
