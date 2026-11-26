// Modelo del Blog con relaciones. No devuelve propiedades de autenticación.
MATCH (u:BlogUser)-[r:PUBLICA]->(a:BlogArticle)
OPTIONAL MATCH (a)-[s:EN_CATEGORIA|CON_ETIQUETA]->(catalogo)
OPTIONAL MATCH (comentario:BlogComment)-[t:COMENTA_EN]->(a)
RETURN u.name AS autor, a.title AS articulo, type(r) AS autoria,
       collect(DISTINCT catalogo.name) AS catalogos, count(DISTINCT comentario) AS comentarios;

MATCH (n) WHERE n:BlogUser OR n:BlogArticle OR n:BlogComment OR n:BlogCategory OR n:BlogTag
UNWIND labels(n) AS tipo RETURN tipo, count(*) AS total ORDER BY tipo;
