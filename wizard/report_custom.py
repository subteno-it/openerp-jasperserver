# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2007 EVI All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
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
        h.add_credentials('jasperadmin', 'chkvoldsk')
        resp, content = h.request("http://127.0.0.1:8080/jasperserver/services/repository", "POST", body,headers)
        self.obj=external_pdf(content)
        return (self.obj.pdf, 'pdf')

report_custom('report.print.jasper.pdf')
