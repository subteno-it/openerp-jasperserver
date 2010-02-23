# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP, 
#    Copyright (C) 2009 SYLEAM Info Services (<http://www.syleam.fr/>) Christophe CHAUVET
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

from report.render import render
from report.interface import report_int
from httplib2 import *
# TODO: use netsvc to debug
#from netsvc import

##
# Construct the body template for SOAP
#
BODY_TEMPLATE = """<SOAP-ENV:Envelope
 xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/"
 xmlns:ns4="http://www.jaspersoft.com/client"
 SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
<SOAP-ENV:Body>
<ns4:runReport>
<request xsi:type="xsd:string">
    &lt;request operationName=&quot;runReport&quot;&gt;
        &lt;argument name=&quot;RUN_OUTPUT_FORMAT&quot;&gt;%s&lt;/argument&gt;
        &lt;argument name=&quot;PAGE&quot;&gt;0&lt;/argument&gt;
        &lt;argument name=&quot;USE_DIME_ATTACHMENTS&quot;&gt;
            &lt;![CDATA[1]]&gt;
        &lt;/argument&gt;
        &lt;resourceDescriptor name=&quot;&quot; wsType=&quot;reportUnit&quot; uriString=&quot;%s&quot; isNew=&quot;false&quot;&gt;
            &lt;label&gt;&lt;/label&gt;
            &lt;parameter name="parameter1"&gt;test&lt;/parameter&gt;
        &lt;/resourceDescriptor&gt;
    &lt;/request&gt;
</request></ns4:runReport>
</SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""



class external_pdf(render):
    def __init__(self, pdf):
        render.__init__(self)
        self.pdf = pdf
        self.output_type='pdf'
    def _render(self):
        return self.pdf

class report_jasper(report_int):
    """
    Extend report_int to use Jasper Server
    """
    def create(self, cr, uid, ids, data, context={}):
        print data
        headers = {'Content-type': 'text/xml', 'charset':'UTF-8',"SOAPAction":"runReport"}
        h = Http()
        body = BODY_TEMPLATE % data['form']['params']
        print
        print body
        print
        h.add_credentials('jasperadmin', 'jasperadmin')
        resp, content = h.request("http://127.0.0.1:8080/jasperserver/services/repository", "POST", body,headers)
        self.obj=external_pdf(content)
        return (self.obj.pdf, 'pdf')

report_jasper('report.print.jasper.pdf')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
