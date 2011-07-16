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
from jasper_server.common import registered_report
import logging

_logger = logging.getLogger('jasper_server')


class IrActionReport(osv.osv):
    _inherit = 'ir.actions.report.xml'

    def register_all(self, cursor):
        """
        Register all jasper report
        """
        _logger.info('====[REGISTER JASPER REPORT]========================')
        value = super(IrActionReport, self).register_all(cursor)
        cursor.execute("SELECT id, report_name FROM ir_act_report_xml WHERE report_type = 'jasper'")
        records = cursor.dictfetchall()
        for record in records:
            registered_report(record['report_name'])
        _logger.info('====[END REGISTER JASPER REPORT]====================')
        return value

IrActionReport()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
