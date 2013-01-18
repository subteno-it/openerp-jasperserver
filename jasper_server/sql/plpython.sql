--
-- Add some function
--
CREATE OR REPLACE FUNCTION get_field(
    server   text,
    port     integer,
    login    text,
    password text,
    database text,
    model    text,
    obj_id   integer,
    field    text)
RETURNS text AS 
$BODY$

if obj_id is None:
    return '0'
else :
    from oersted import OEClient

    res = {}
    try:
        oeclient = OEClient(server, port)
        oeclient.login(database, login, password)
        obj = oeclient.create_proxy(database, model)

        res = obj.read(obj_id, [field])

    except AssertionError, e:
        plpy.error('Authentification error')
    except Exception, e:
        import traceback
        plpy.error(traceback.format_exc())
        raise

    return res[field]

$BODY$
LANGUAGE plpythonu;

ALTER FUNCTION get_field(text, integer, text, text, text, text, integer, text)
  OWNER TO %(db_user)s;

-- vim:ft=pgsql
