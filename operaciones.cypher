// name: sp_get_user_login
MATCH (u:BlogUser {email:$email}) RETURN u.user_id AS user_id, u.name AS name, u.email AS email, u.password_hash AS password_hash;

// name: sp_get_users
MATCH (u:BlogUser) RETURN u.user_id AS user_id, u.name AS name, u.email AS email ORDER BY u.created_at, u.user_id;

// name: fn_user_exists
MATCH (u:BlogUser {email:$email}) RETURN count(u) AS valor;

// name: fn_article_count
MATCH (:BlogUser {user_id:$user_id})-[:PUBLICA]->(a:BlogArticle) RETURN count(a) AS valor;

// name: sp_create_user
CREATE (u:BlogUser {user_id:$id, name:$name, email:$email, password_hash:$password_hash, created_at:datetime()}) RETURN u.user_id AS id;

// name: sp_update_user
MATCH (u:BlogUser {user_id:$user_id}) SET u.name=$name, u.email=$email, u.password_hash=coalesce($password_hash,u.password_hash) RETURN u.user_id AS id;

// name: sp_delete_user
MATCH (u:BlogUser {user_id:$user_id}) WITH u, u.user_id AS id DELETE u RETURN id;

// name: sp_get_articles
MATCH (u:BlogUser)-[:PUBLICA]->(a:BlogArticle)
RETURN a.article_id AS article_id, u.user_id AS user_id, u.name AS author,
       a.title AS title, a.article_date AS article_date, a.text AS text
ORDER BY a.article_date DESC, a.article_id DESC;

// name: sp_create_article
MATCH (u:BlogUser {user_id:$user_id})
CREATE (u)-[:PUBLICA]->(a:BlogArticle {article_id:$id, title:$title, text:$text, article_date:datetime()})
RETURN a.article_id AS id;

// name: sp_update_article
MATCH (:BlogUser {user_id:$user_id})-[:PUBLICA]->(a:BlogArticle {article_id:$article_id})
SET a.title=$title, a.text=$text RETURN a.article_id AS id;

// name: sp_delete_article
MATCH (:BlogUser {user_id:$user_id})-[:PUBLICA]->(a:BlogArticle {article_id:$article_id})
SET a._lock=true REMOVE a._lock
WITH a, a.article_id AS id
OPTIONAL MATCH (c:BlogComment)-[:COMENTA_EN]->(a)
WITH a, id, collect(c) AS comentarios
FOREACH (c IN comentarios | DETACH DELETE c)
DETACH DELETE a RETURN id;

// name: sp_get_comments
MATCH (u:BlogUser)-[:ESCRIBE]->(c:BlogComment)-[:COMENTA_EN]->(:BlogArticle {article_id:$article_id})
RETURN c.comment_id AS comment_id, $article_id AS article_id, u.user_id AS user_id,
       c.name AS name, c.url AS url, c.comment_text AS comment_text
ORDER BY c.created_at DESC, c.comment_id DESC;

// name: sp_create_comment
MATCH (u:BlogUser {user_id:$user_id}), (a:BlogArticle {article_id:$article_id})
SET a._lock=true REMOVE a._lock
CREATE (u)-[:ESCRIBE]->(c:BlogComment {comment_id:$id, name:$name, url:$url, comment_text:$comment_text, created_at:datetime()})-[:COMENTA_EN]->(a)
RETURN c.comment_id AS id;

// name: sp_update_comment
MATCH (:BlogUser {user_id:$user_id})-[:ESCRIBE]->(c:BlogComment {comment_id:$comment_id})
SET c.name=$name, c.url=$url, c.comment_text=$comment_text RETURN c.comment_id AS id;

// name: sp_delete_comment
MATCH (:BlogUser {user_id:$user_id})-[:ESCRIBE]->(c:BlogComment {comment_id:$comment_id})
WITH c, c.comment_id AS id DETACH DELETE c RETURN id;

// name: sp_get_categories
MATCH (n:BlogCategory) RETURN n.category_id AS category_id, n.name AS name, n.url AS url ORDER BY n.name;

// name: sp_get_article_categories
MATCH (:BlogArticle {article_id:$article_id})-[:EN_CATEGORIA]->(n:BlogCategory)
RETURN n.category_id AS category_id, n.name AS name, n.url AS url ORDER BY n.name;

// name: sp_create_category
CREATE (n:BlogCategory {category_id:$id, name:$name, url:$url}) RETURN n.category_id AS id;

// name: sp_update_category
MATCH (n:BlogCategory {category_id:$id}) SET n.name=$name, n.url=$url RETURN n.category_id AS id;

// name: sp_delete_category
MATCH (n:BlogCategory {category_id:$id}) WITH n, n.category_id AS id DETACH DELETE n RETURN id;

// name: sync_categories
MATCH (a:BlogArticle {article_id:$article_id})
OPTIONAL MATCH (a)-[r:EN_CATEGORIA]->(old:BlogCategory)
WHERE NOT old.category_id IN $ids
DELETE r
WITH DISTINCT a
UNWIND $ids AS id
MATCH (n:BlogCategory {category_id:id})
MERGE (a)-[:EN_CATEGORIA]->(n)
RETURN count(n) AS valor;

// name: sp_get_tags
MATCH (n:BlogTag) RETURN n.tag_id AS tag_id, n.name AS name, n.url AS url ORDER BY n.name;

// name: sp_get_article_tags
MATCH (:BlogArticle {article_id:$article_id})-[:CON_ETIQUETA]->(n:BlogTag)
RETURN n.tag_id AS tag_id, n.name AS name, n.url AS url ORDER BY n.name;

// name: sp_create_tag
CREATE (n:BlogTag {tag_id:$id, name:$name, url:$url}) RETURN n.tag_id AS id;

// name: sp_update_tag
MATCH (n:BlogTag {tag_id:$id}) SET n.name=$name, n.url=$url RETURN n.tag_id AS id;

// name: sp_delete_tag
MATCH (n:BlogTag {tag_id:$id}) WITH n, n.tag_id AS id DETACH DELETE n RETURN id;

// name: sync_tags
MATCH (a:BlogArticle {article_id:$article_id})
OPTIONAL MATCH (a)-[r:CON_ETIQUETA]->(old:BlogTag)
WHERE NOT old.tag_id IN $ids
DELETE r
WITH DISTINCT a
UNWIND $ids AS id
MATCH (n:BlogTag {tag_id:id})
MERGE (a)-[:CON_ETIQUETA]->(n)
RETURN count(n) AS valor;
