"""Persistencia del Blog en Neo4j mediante consultas Cypher parametrizadas."""
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
from uuid import uuid4

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError

CARPETA_CYPHER = Path(__file__).with_name('cypher')
URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
USUARIO = os.environ.get('NEO4J_USER', 'neo4j')
BASE = os.environ.get('NEO4J_DATABASE', 'neo4j')

PARAMETROS = {
    'sp_get_user_login': 'email',
    'sp_get_users': '',
    'fn_user_exists': 'email',
    'fn_article_count': 'user_id',
    'sp_create_user': 'name email password_hash',
    'sp_update_user': 'user_id name email password_hash',
    'sp_delete_user': 'user_id',
    'sp_get_articles': '',
    'sp_create_article': 'user_id title text',
    'sp_update_article': 'article_id user_id title text',
    'sp_delete_article': 'article_id user_id',
    'sp_get_comments': 'article_id',
    'sp_create_comment': 'article_id user_id name url comment_text',
    'sp_update_comment': 'comment_id user_id name url comment_text',
    'sp_delete_comment': 'comment_id user_id',
}
for singular, plural in [('category', 'categories'), ('tag', 'tags')]:
    PARAMETROS.update({
        'sp_get_' + plural: '',
        'sp_get_article_' + plural: 'article_id',
        'sp_create_' + singular: 'name url',
        'sp_update_' + singular: 'id name url',
        'sp_delete_' + singular: 'id',
    })

# Cada bloque del archivo tiene un nombre utilizado por la interfaz original.
bloques = re.split(r'^// name: (\w+)\s*$', (CARPETA_CYPHER / 'operaciones.cypher').read_text(encoding='utf-8'), flags=re.M)
CONSULTAS = {clave: cuerpo.strip().removesuffix(';')
             for clave, cuerpo in zip(bloques[1::2], bloques[2::2])}


def conectar(password):
    driver = GraphDatabase.driver(URI, auth=(USUARIO, password), connection_timeout=8,
                                  max_transaction_retry_time=8)
    try:
        driver.verify_connectivity()
        esquema = (CARPETA_CYPHER / 'esquema.cypher').read_text(encoding='utf-8')
        with driver.session(database=BASE) as sesion:
            for sentencia in esquema.split(';'):
                if sentencia.strip():
                    sesion.run(sentencia).consume()
    except Exception:
        driver.close()
        raise
    return driver


def _parametros(nombre, valores):
    return dict(zip(PARAMETROS[nombre].split(), valores, strict=True))


def consultar(conexion, nombre, parametros=()):
    resultado = conexion.execute_query(CONSULTAS[nombre],
                                       parameters_=_parametros(nombre, parametros),
                                       database_=BASE, routing_='r')
    return [registro.data() for registro in resultado.records]


def _escribir(tx, nombre, parametros):
    fila = tx.run(CONSULTAS[nombre], parametros).single()
    if fila is None:
        raise ValueError('El registro ya no existe o no tienes permiso para modificarlo.')
    return fila['id']


def ejecutar(conexion, nombre, parametros, devuelve_id=False):
    valores = _parametros(nombre, parametros)
    if devuelve_id:
        valores['id'] = str(uuid4())
    try:
        with conexion.session(database=BASE) as sesion:
            nuevo_id = sesion.execute_write(_escribir, nombre, valores)
    except Neo4jError as error:
        if error.code == 'Neo.ClientError.Schema.ConstraintValidationFailed':
            if nombre == 'sp_delete_user':
                raise ValueError('Primero elimina tus artículos y comentarios para borrar tu cuenta.') from error
            if nombre in ('sp_create_user', 'sp_update_user'):
                raise ValueError('Ese email ya está registrado.') from error
            raise ValueError('Ese nombre ya está registrado.') from error
        raise
    return nuevo_id if devuelve_id else None


def funcion(conexion, nombre, parametros):
    return consultar(conexion, nombre, parametros)[0]['valor']


def guardar_publicacion(conexion, usuario_id, titulo, texto, categorias, etiquetas, articulo_id=None):
    """Confirma la publicación y sus asociaciones juntas, o revierte los cambios."""
    nueva = articulo_id is None
    clave = str(uuid4()) if nueva else articulo_id

    def guardar(tx):
        nombre = 'sp_create_article' if nueva else 'sp_update_article'
        _escribir(tx, nombre, dict(id=clave, article_id=clave, user_id=usuario_id,
                                   title=titulo, text=texto))
        for plural, elegidos in [('categories', categorias), ('tags', etiquetas)]:
            ids = list(dict.fromkeys(elegidos))
            resultado = tx.run(CONSULTAS['sync_' + plural], article_id=clave, ids=ids)
            if resultado.single()['valor'] != len(ids):
                raise ValueError('Una categoría o etiqueta ya no existe. Actualiza la lista.')
        return clave

    with conexion.session(database=BASE) as sesion:
        return sesion.execute_write(guardar)


# Usamos bibliotecas incluidas en Python para proteger las contraseñas.
# Se guarda: algoritmo$repeticiones$sal$hash. Nunca la contraseña original.
def proteger_password(password):
    if not 8 <= len(password) <= 128:
        raise ValueError('La contraseña debe tener entre 8 y 128 caracteres.')
    sal = secrets.token_hex(16)
    repeticiones = 600000
    resultado = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(sal), repeticiones)
    return f'pbkdf2_sha256${repeticiones}${sal}${resultado.hex()}'


def comprobar_password(password, guardado):
    try:
        algoritmo, repeticiones, sal, esperado = guardado.split('$')
        if algoritmo != 'pbkdf2_sha256' or not 1 <= int(repeticiones) <= 1000000:
            return False
        resultado = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(sal), int(repeticiones))
        return hmac.compare_digest(resultado.hex(), esperado)
    except (ValueError, AttributeError):
        return False
