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

__name__ = "Upgrade existing reports"
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
        import pooler
        pool = pooler.get_pool(cr.dbname)

        doc_obj = pool.get('jasper.document')
        doc_ids = doc_obj.search(cr, 1, [('report_id', '=', False)])
        if doc_ids:
            _logger.info('Migrate old configuration data to the new one, '
                         'there are %s document' % len(doc_ids))
            for id in doc_ids:
                doc_obj.make_action(cr, 1, id)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
