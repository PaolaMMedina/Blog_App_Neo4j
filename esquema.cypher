CREATE CONSTRAINT blog_user_user_id IF NOT EXISTS FOR (n:BlogUser) REQUIRE n.user_id IS UNIQUE;
CREATE CONSTRAINT blog_article_article_id IF NOT EXISTS FOR (n:BlogArticle) REQUIRE n.article_id IS UNIQUE;
CREATE CONSTRAINT blog_comment_comment_id IF NOT EXISTS FOR (n:BlogComment) REQUIRE n.comment_id IS UNIQUE;
CREATE CONSTRAINT blog_category_category_id IF NOT EXISTS FOR (n:BlogCategory) REQUIRE n.category_id IS UNIQUE;
CREATE CONSTRAINT blog_tag_tag_id IF NOT EXISTS FOR (n:BlogTag) REQUIRE n.tag_id IS UNIQUE;
CREATE CONSTRAINT blog_user_email IF NOT EXISTS FOR (n:BlogUser) REQUIRE n.email IS UNIQUE;
CREATE CONSTRAINT blog_category_name IF NOT EXISTS FOR (n:BlogCategory) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT blog_tag_name IF NOT EXISTS FOR (n:BlogTag) REQUIRE n.name IS UNIQUE;
