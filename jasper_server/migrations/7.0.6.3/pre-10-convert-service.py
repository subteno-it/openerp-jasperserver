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
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
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

import logging

__name__ = "Upgrade existing reports, service name changed"
_logger = logging.getLogger(__name__)


def migrate(cr, v):
    """
    Put your explanation here

    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""SELECT count(*)
                  FROM   pg_tables
                  WHERE  schemaname = current_schema()
                  AND    tablename = 'jasper_document'""")
    if cr.fetchone()[0]:

        # We change all service defined on ir.action.report.xml
        cr.execute("""SELECT report_id, 'jasper.report_'||id as id, name
                        FROM jasper_document WHERE report_id IS NOT NULL""")
        for line in cr.fetchall():
            cr.execute("""UPDATE ir_act_report_xml
                             SET report_name=%s WHERE id=%s""",
                       (line[1], line[0]))
            _logger.info('Upgrade jasper report %s' % line[2])

        cr.commit()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
