# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP,
#    Copyright (C) 2009-2011 SYLEAM Info Services (<http://www.syleam.fr/>)
#                  Christophe CHAUVET <christophe.chauvet@syleam.fr>
#
#    This file is a part of jasper_server
#
#    jasper_server is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    jasper_server is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from report.interface import report_int
from report_soap import Report
from osv.osv import except_osv
from report_exception import JasperException
import logging

_logger = logging.getLogger('jasper_server')


class report_jasper(report_int):
    """
    Extend report_int to use Jasper Server
    """
    def create(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}

        _logger.debug('Call %s' % self.name)
        try:
            return Report(self.name, cr, uid, ids, data, context).execute()
        except JasperException, e:
            raise except_osv(e.title, e.message)

report_jasper('report.print.jasper.server')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
