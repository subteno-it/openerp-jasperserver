# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP, 
#    Copyright (C) 2010 SYLEAM Info Services (<http://www.syleam.fr/>)
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

import pooler
from report.render import render
from httplib2 import Http, ServerNotFoundError ,HttpLib2Error
from dime import Message
from lxml.etree import Element, tostring

##
# If cStringIO is available, we use it
#
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

class external_pdf(render):
    def __init__(self, pdf):
        render.__init__(self)
        self.pdf = pdf
        self.output_type='pdf'
    def _render(self):
        return self.pdf


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
        &lt;argument name=&quot;RUN_OUTPUT_FORMAT&quot;&gt;%(format)s&lt;/argument&gt;
        &lt;argument name=&quot;PAGE&quot;&gt;0&lt;/argument&gt;
        &lt;argument name=&quot;USE_DIME_ATTACHMENTS&quot;&gt;
            &lt;![CDATA[1]]&gt;
        &lt;/argument&gt;
        &lt;resourceDescriptor name=&quot;&quot; wsType=&quot;reportUnit&quot; uriString=&quot;%(path)s&quot; isNew=&quot;false&quot;&gt;
            &lt;label&gt;&lt;/label&gt;
            %(param)s
        &lt;/resourceDescriptor&gt;
    &lt;/request&gt;
</request></ns4:runReport>
</SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""

class Report(object):
    """compose the SOAP Query, launch the query and return the value"""
    def __init__(self, name, cr, uid, ids, data, context):
        """Initialise the report"""
        self.name = name
        self.cr = cr
        self.uid = uid
        self.ids = ids
        self.data = data
        self.model = data.get('model', False)
        self.context = context
        self.pool = pooler.get_pool(cr.dbname)
        self.obj = None
        self.outputFormat = 'pdf'

    def execute(self):
        """Launch the report and return it"""
        js_obj = self.pool.get('jasper.server')
        js_ids = js_obj.search(self.cr, self.uid, [('enable','=',True)])
        if not len(js_ids):
            raise Exception('Error, no JasperServer not found!')

        js = js_obj.read(self.cr, self.uid, js_ids, context=self.context)[0]
        uri = 'http://%s:%d%s' % (js['host'], js['port'], js['repo'])
        print 'DATA: %r' % self.data

        par = self.parameter(self.data['form'], 
                {'active_id': self.data['id'],
                 'active_ids': self.data['form']['ids'],
                 'model': self.model})
        body_args = {
            'format': self.data['form']['params'][0],
            'path': self.data['form']['params'][1],
            'param': par,
        }

        body = BODY_TEMPLATE % body_args
        print
        print body
        print

        headers = {'Content-type': 'text/xml', 'charset':'UTF-8',"SOAPAction":"runReport"}
        h = Http()
        h.add_credentials(js['user'], js['pass'])
        try:
            resp, content = h.request(uri, "POST", body, headers)
        except ServerNotFoundError:
            raise Exception('Error, Server not found !')
        except HttpLib2Error, e:
            raise Exception('Error: %r' % e)
        except Exception, e:
            raise Exception('Error: %r' % e)
        print 'RESP: %r' % resp
        if resp.get('content-type') != 'application/dime' :
            raise Exception('Error, Document not found')

        ##
        # We must deconpose the dime record to return the PDF only
        #
        fp = StringIO(content)
        a = Message.load(fp)
        for x in a.records:
            print  'Type: %r' % x.type.value
            if x.type.value == 'application/pdf':
                content = x.data
        self.obj=external_pdf(content)

        return (self.obj.pdf, 'pdf')

    @staticmethod
    def entities(data):
        data = data.replace('&','&amp;')
        data = data.replace('<','&lt;')
        data = data.replace('>','&gt;')
        data = data.replace('"','&quot;')
        data = data.replace("'","&apos;")
        return data

    def parameter(self, dico, resource):
        res = ''
        for key in resource:
            e = Element('parameter')
            e.set('name','OERP_%s' % key.upper())
            e.text = str(resource[key])
            res += tostring(e) + '\n'

        for key in dico:
            if key in 'params':
                continue
            val = dico[key]
            e = Element('parameter')
            e.set('name','WIZARD_%s' % key.upper())
            if isinstance(val, list):
                if isinstance(val[0], tuple):
                    e.text = ','.join(map(str, val[0][2]))
                else:
                    e.text = ','.join(map(str, val))
            else:
                e.text = val and str(val) or ''
            res += tostring(e) + '\n'
        return self.entities(res)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
