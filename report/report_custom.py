# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP
#    Copyright (c) 2008-2009 EVERLIBRE (http://everlibre.fr) Eric VERNICHON
#    Copyright (C) 2009 SYLEAM ([http://www.syleam.fr]) Christophe CHAUVET
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
#    along with this program.  If not, see [http://www.gnu.org/licenses/].
#
##############################################################################

from report.render import render
from report.interface import report_int
from httplib2 import *

class external_pdf(render):
    def __init__(self, pdf):
        render.__init__(self)
        self.pdf = pdf
        self.output_type='pdf'
    def _render(self):
        return self.pdf
        
class report_custom(report_int):
    def create(self, cr, uid, ids, data, context={}):
        print data
        headers = {'Content-type': 'text/xml', 'charset':'UTF-8',"SOAPAction":"runReport"}
        h = Http()
        body =data['form']['template']%data['form']['params']
        print
        print body
        print
        h.add_credentials('jasperadmin', 'jasperadmin')
        resp, content = h.request("http://127.0.0.1:8080/jasperserver/services/repository", "POST", body,headers)
        self.obj=external_pdf(content)
        return (self.obj.pdf, 'pdf')

report_custom('report.print.jasper.pdf')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
