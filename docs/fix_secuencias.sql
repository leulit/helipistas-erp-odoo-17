-- Resincroniza las secuencias de 'id' con el contenido real de cada tabla.
--
-- Tras importar datos con ids explicitos (la migracion desde la base vieja) las secuencias se
-- quedan atras, y el siguiente INSERT que deje que Postgres asigne el id revienta con
-- "duplicate key value violates unique constraint <tabla>_pkey".
--
-- Solo adelanta secuencias que van por detras del max(id); es idempotente y no toca datos.
DO $$
DECLARE
    r     record;
    maxid bigint;
    valor bigint;
BEGIN
    FOR r IN
        SELECT s.oid::regclass AS seq, t.relname AS tabla
        FROM pg_class s
        JOIN pg_depend d  ON d.objid = s.oid AND d.classid = 'pg_class'::regclass
        JOIN pg_class t   ON t.oid = d.refobjid
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = d.refobjsubid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE s.relkind = 'S' AND n.nspname = 'public' AND a.attname = 'id'
        ORDER BY t.relname
    LOOP
        EXECUTE format('SELECT COALESCE(MAX(id), 0) FROM %I', r.tabla) INTO maxid;
        EXECUTE format('SELECT last_value FROM %s', r.seq) INTO valor;
        IF valor < maxid THEN
            RAISE NOTICE '%: secuencia en %, max(id) = % -> corregida', r.tabla, valor, maxid;
            PERFORM setval(r.seq, maxid);
        END IF;
    END LOOP;
END $$;
