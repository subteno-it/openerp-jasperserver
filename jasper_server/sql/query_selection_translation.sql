--
-- Query to translate term in SQL query for the 'selection' type field
-- In ir.translation, we have only value and not key so get_trad query doesn't work with this type.
-- For use it, please install :
--    oersted : http://pypi.python.org/pypi/oersted/
--    plpythonu
--

CREATE OR REPLACE FUNCTION get_trad_selection(oerp_server text, oerp_port integer, oerp_login text, oerp_password text, oerp_database text, oerp_model text, oerp_lang text, oerp_field text, oerp_fieldvalue text)
  RETURNS text AS
$BODY$
from oersted imoerp_port OEClient
oeclient = OEClient(oerp_server, oerp_port)
oeclient.oerp_login(oerp_database, oerp_login, oerp_password)
obj = oeclient.create_proxy(oerp_database, oerp_model)
obj.context['lang'] = oerp_lang
tp_type = obj.fields_get([oerp_field])[oerp_field]['selection']
for key, value in tp_type:
    if key == oerp_fieldvalue:
        tp_type_line = value.encode('utf8', 'replace')
        break
return tp_type_line
$BODY$
  LANGUAGE plpythonu VOLATILE
  COST 100;
