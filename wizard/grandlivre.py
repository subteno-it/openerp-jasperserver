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

import wizard
import pooler
import report_custom
dates_form = '''<?xml version="1.0"?>
<form string="Select period">
    <field name="periods" colspan="4"/>
    <field name="comptes" colspan="4"/>
    <field name="racine" colspan="4"/>
    <field name="lettrer" colspan="4"/>
    <field name="nonmouvemente" colspan="4"/>
</form>'''

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

dates_fields = {
    'periods': {'string': 'Periodes', 'type': 'many2many', 'relation': 'account.period', 'help': 'All periods if empty'},
    'comptes': {'string': 'Comptes', 'type': 'many2many', 'relation': 'account.account', 'help': 'Tout les comptes si vide'},
    'racine': {'string': 'racine de compte', 'type': 'char','size':12, 'help': 'Racine de comptes'},
    'lettrer': {'string': 'ecritures non reconcilié seules', 'type': 'boolean', 'help': 'Ecritures non reconciliés'},
    'nonmouvemente': {'string': 'ecritures non mouvementées ?', 'type': 'boolean', 'help': 'Ecritures non mouvementées'}
}


class wizard_report(wizard.interface):
    def _get_defaults(self, cr, uid, data, context):
        data['form']['template']=BODY_TEMPLATE
        data['form']['params']=('PDF','/reports/'+cr.dbname+'/GrandLivre')
        print cr.dbname
       
        return data['form']    
    states = { 
                'init': {'actions': [_get_defaults], 'result': {'type':'form', 'arch':dates_form, 'fields':dates_fields, 'state':[('end','Cancel'),('report','GL')]}},
                'report' :{'actions':[],'result':{'type':'print','report':'print.jasper.pdf', 'state':'end'}},

}

wizard_report('jasper.server.grandlivre.report')
