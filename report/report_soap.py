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
from netsvc import Logger, LOG_DEBUG
from tempfile import mkstemp
import os
from subprocess import call
from parser import ParseHTML, ParseXML

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

logger = Logger()
def log_debug(message):
    logger.notifyChannel('jasper_server', LOG_DEBUG, ' %s' % message)

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
        &lt;argument name=&quot;REPORT_LOCALE&quot;&gt;&lt;![CDATA[fr]]&gt;&lt;/argument&gt;
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
        ids = self.data['form']['ids']
        js_obj = self.pool.get('jasper.server')
        js_ids = js_obj.search(self.cr, self.uid, [('enable','=',True)])
        if not len(js_ids):
            raise Exception('Error, no JasperServer found!')

        js = js_obj.read(self.cr, self.uid, js_ids, context=self.context)[0]
        uri = 'http://%s:%d%s' % (js['host'], js['port'], js['repo'])
        log_debug('DATA:')
        log_debug('\n'.join(['%s: %s' % (x, self.data[x]) for x in self.data]))

        ##
        # For each IDS, launch a query, and return only one result
        #
        pdf_list = []
        for ex in ids:
            # Bug found in iReport >= 3.7.x (IN doesn't work in SQL Query)
            # We cannot use $X{IN, field, Collection}
            d_par = {'active_id': ex,
                     'active_ids': ex,
                     'model': self.model}

            # If XML we must compose it
            if self.data['form']['params'][2] == 'xml':
                d_xml = js_obj.generator(self.cr, self.uid, self.model, self.ids[0], 
                        self.data['form']['params'][3], context=self.context)
                d_par['xml_data'] = d_xml

            # Retrieve the company information and send them in parameter
            user = self.pool.get('res.users').browse(self.cr, self.uid, self.uid, context=self.context)
            d_par['company_name'] = user.company_id.name
            d_par['company_logo'] = user.company_id.name.encode('ascii','ignore').replace(' ','_')
            d_par['company_hearder1'] = user.company_id.rml_header1 or ''
            d_par['company_footer1'] = user.company_id.rml_footer1 or ''
            d_par['company_footer2'] = user.company_id.rml_footer2 or ''
            d_par['company_website'] = user.company_id.partner_id.website or ''
            d_par['company_currency'] = user.company_id.currency_id.name or ''

            # Search the default address for the company.
            addr_id = self.pool.get('res.partner').address_get(self.cr, self.uid, [user.company_id.partner_id.id],['default'])['default']
            addr = self.pool.get('res.partner.address').browse(self.cr, self.uid, addr_id, context=self.context)
            d_par['company_street'] = addr.street or ''
            d_par['company_street2'] = addr.street2 or ''
            d_par['company_zip'] = addr.zip or ''
            d_par['company_city'] = addr.city or ''
            d_par['company_country'] = addr.country_id.name or ''
            d_par['company_phone'] = addr.phone or ''
            d_par['company_fax'] = addr.fax or ''
            d_par['company_mail'] = addr.email or ''

            par = self.parameter(self.data['form'], d_par)
            body_args = {
                'format': self.data['form']['params'][0],
                'path': self.data['form']['params'][1],
                'param': par,
                'database': '/openerp/databases/%s' % self.cr.dbname,
            }

            body = BODY_TEMPLATE % body_args
            log_debug('****\n%s\n****' % body)

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
                raise Exception('Error: %s' % str(e))
            log_debug('HTTP -> RESPONSE:')
            log_debug('\n'.join(['%s: %s' % (x, resp[x]) for x in resp]))
            if resp.get('content-type').startswith('text/xml'):
                log_debug('CONTENT: %r' % content)
                raise Exception('Code: %s\nMessage: %s' % ParseXML(content))
            elif resp.get('content-type').startswith('text/html'):
                log_debug('CONTENT: %r' % content)
                raise Exception ('Error: %s' % ParseHTML(content))
            elif resp.get('content-type') == 'application/dime' :
                ##
                # We must decompose the dime record to return the PDF only
                fp = StringIO(content)
                a = Message.load(fp)
                for x in a.records:
                    log_debug('HTTP -> CONTENT -> Type: %r' % x.type.value)
                    if x.type.value == 'application/pdf':
                        content = x.data
                        # Store the PDF in TEMP directory
                        __, f_name = mkstemp(suffix='.pdf', prefix='jasper')
                        pdf_list.append(f_name)
                        fpdf = open(f_name, 'w+b')
                        fpdf.write(content)
                        fpdf.close()
            else:
                raise Exception('Unknown Error: Content-type: %s\nMessage:%s' % (resp.get('content-type'), content))

        ##
        # Create a global file for each PDF file, use Ghostscript to concatenate them
        # Retrieve the global if there is a multiple file
        #
        if len(ids) > 1:
            # -dNOPAUSE -sDEVICE=pdfwrite -sOUTPUTFILE=firstANDsecond.pdf -dBATCH
            __, f_name = mkstemp(suffix='.pdf', prefix='jasper-global')
            cmd = ['gs', '-dNOPAUSE', '-sDEVICE=pdfwrite', '-sOUTPUTFILE=%s' % f_name, '-dBATCH']
            cmd.extend(pdf_list)
            retcode = call(cmd)
            log_debug('PDF -> RETCODE: %r' % retcode)
            if retcode != 0:
                raise Exception('Error: cannot concatenate the PDF file!')
            content = open(f_name, 'r').read()
            os.remove(f_name)
            for f in pdf_list:
                os.remove(f)
        self.obj=external_pdf(content)
        return (self.obj.pdf, 'pdf')

    @staticmethod
    def entities(data):
        """
        Convert XML string to XML entities 

        @type  data: str
        @param data: XML String
        @rtype: str
        @return: XML string converted
        """
        data = data.replace('&','&amp;')
        data = data.replace('<','&lt;')
        data = data.replace('>','&gt;')
        data = data.replace('"','&quot;')
        data = data.replace("'","&apos;")
        return data

    def parameter(self, dico, resource):
        """
        Convert value to a parameter for SOAP query

        @type  dico: dict
        @param dico: Contain parameter starts with OERP_
        @type  resource: dict
        @param resource: Contain parameter starts with WIZARD_
        @rtype: xmlstring
        @return: XML String representation
        """
        res = ''
        for key in resource:
            log_debug('PARAMETER -> RESOURCE: %s' % key)
            if key in 'xml_data':
                continue
            e = Element('parameter')
            e.set('name','OERP_%s' % key.upper())
            e.text = str(resource[key])
            res += tostring(e) + '\n'

        for key in dico:
            log_debug('PARAMETER -> DICO: %s' % key)
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
        res = self.entities(res)
        if resource.get('xml_data'):
            res += '&lt;parameter class=&quot;java.lang.String&quot; name=&quot;XML_DATA&quot;&gt;'
            res += '&lt;![CDATA[&quot;%s&quot;]]&gt;&lt;/parameter&gt;' % resource['xml_data']
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
