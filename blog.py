"""Blog de escritorio: ejecutar con python blog.py.

Tkinter dibuja las ventanas. Neo4j guarda los datos mediante Cypher.
La clase agrupa las pantallas y conserva el usuario que inicio sesion.
"""
import re
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from tkinter.scrolledtext import ScrolledText
from urllib.parse import urlsplit
import os
from importlib.util import find_spec
from pathlib import Path
import subprocess
import sys

if __name__ == '__main__' and find_spec('neo4j') is None:
    archivo = Path(__file__).resolve()
    interprete = archivo.parent / '.venv' / 'Scripts' / 'python.exe'
    if interprete.is_file() and interprete.resolve() != Path(sys.executable).resolve():
        raise SystemExit(subprocess.call([str(interprete), str(archivo), *sys.argv[1:]]))
    raise SystemExit('Falta el controlador de Neo4j. En la carpeta del Blog ejecuta: '
                     'python -m pip install -r requirements.txt')

from neo4j.exceptions import DriverError, Neo4jError
from conexion import conectar, consultar, ejecutar, funcion, proteger_password, comprobar_password, guardar_publicacion


def validar_texto(valor, nombre, limite):
    valor = valor.strip()
    if not valor or len(valor) > limite:
        raise ValueError(f'{nombre}: escribe entre 1 y {limite} caracteres.')
    return valor


def validar_email(valor):
    valor = validar_texto(valor, 'Email', 254).lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', valor):
        raise ValueError('Escribe un email valido, por ejemplo nombre@correo.com.')
    return valor


def validar_url(valor):
    valor = valor.strip()
    if valor:
        url = urlsplit(valor)
        if len(valor) > 500 or url.scheme not in ('http', 'https') or not url.netloc:
            raise ValueError('La URL debe empezar con http:// o https:// (maximo 500 caracteres).')
    return valor or None


class BlogApp:
    def __init__(self, ventana, conexion):
        self.ventana = ventana
        self.conexion = conexion
        self.usuario = None
        ventana.title('Blog · Proyecto de Base de Datos')
        ventana.geometry(f'{min(1220, ventana.winfo_screenwidth() - 50)}x{min(820, ventana.winfo_screenheight() - 70)}')
        ventana.minsize(1000, 650)
        ventana.protocol('WM_DELETE_WINDOW', self.cerrar)
        ventana.report_callback_exception = self.error_callback
        estilo = ttk.Style()
        estilo.theme_use('clam')
        estilo.configure('.', font=('Segoe UI', 10), background='#f4f5f0', foreground='#263d36')
        estilo.configure('TFrame', background='#f4f5f0')
        estilo.configure('Panel.TFrame', background='#ffffff')
        estilo.configure('TButton', padding=(10, 8), background='#edf1ea', borderwidth=0)
        estilo.map('TButton', background=[('active', '#dce6d8')])
        estilo.configure('Compacto.TButton', padding=(5, 5), font=('Segoe UI', 9))
        estilo.configure('Principal.TButton', background='#285b47', foreground='white')
        estilo.map('Principal.TButton', background=[('active', '#1b4332')], foreground=[('active', 'white')])
        for nombre, fuente, color in [('Marca', ('Segoe UI', 20, 'bold'), '#285b47'),
                ('Seccion', ('Segoe UI', 10, 'bold'), '#6b7a70'),
                ('Tarjeta', ('Segoe UI', 19, 'bold'), '#263d36'),
                ('Lectura', ('Segoe UI', 25, 'bold'), '#263d36'),
                ('Nombre', ('Segoe UI', 11, 'bold'), '#263d36'),
                ('Cuerpo', ('Segoe UI', 11), '#35473e'),
                ('TextoLectura', ('Segoe UI', 12), '#35473e'),
                ('Suave', ('Segoe UI', 10), '#68766e')]:
            estilo.configure(nombre + '.TLabel', font=fuente, background='#ffffff', foreground=color)
        estilo.configure('FondoSuave.TLabel', font=('Segoe UI', 11), foreground='#68766e')
        ventana.bind_all('<MouseWheel>', self.rueda)
        estilo.configure('Treeview', rowheight=28)
        estilo.configure('Titulo.TLabel', font=('Segoe UI', 20, 'bold'))
        self.pantalla_login()

    def mostrar_error(self, error, padre=None):
        mensaje = str(error)
        if isinstance(error, (DriverError, Neo4jError)):
            mensaje = 'No se pudo completar la operación en Neo4j.\n\n' + mensaje
        messagebox.showerror('Revisa la operacion', mensaje, parent=padre or self.ventana)

    def error_callback(self, tipo, error, traceback):
        self.mostrar_error(error, self.ventana.grab_current())

    def limpiar(self):
        # Tambien cierra las ventanas de articulos al cerrar sesion.
        for widget in self.ventana.winfo_children():
            widget.destroy()

    def formulario(self, titulo, campos, guardar, padre=None):
        """Un formulario reutilizable para no repetir las mismas ventanas.

        Cada campo es (nombre, tipo, valor). Tipos: entrada, password y texto.
        """
        dialogo = tk.Toplevel(padre or self.ventana)
        dialogo.title(titulo)
        dialogo.transient(padre or self.ventana)
        dialogo.geometry('570x520' if any(c[1] == 'texto' for c in campos) else '480x420')
        dialogo.minsize(430, 350)
        marco = ttk.Frame(dialogo, padding=20)
        marco.pack(fill='both', expand=True)
        entradas = {}
        for nombre, tipo, valor in campos:
            ttk.Label(marco, text=nombre).pack(anchor='w', pady=(8, 3))
            if tipo == 'texto':
                entrada = ScrolledText(marco, height=8, wrap='word', font=('Segoe UI', 11))
                entrada.insert('1.0', valor or '')
                entrada.pack(fill='both', expand=True)
            else:
                entrada = ttk.Entry(marco, show='*' if tipo == 'password' else '')
                entrada.insert(0, valor or '')
                entrada.pack(fill='x')
            entradas[nombre] = (entrada, tipo)

        def confirmar():
            datos = {n: e.get('1.0', 'end-1c') if t == 'texto' else e.get() for n, (e, t) in entradas.items()}
            try:
                guardar(datos)
            except Exception as error:
                self.mostrar_error(error, dialogo)
                return
            if dialogo.winfo_exists():
                dialogo.destroy()

        botones = ttk.Frame(marco)
        botones.pack(fill='x', pady=(16, 0))
        ttk.Button(botones, text='Guardar', command=confirmar).pack(side='left')
        ttk.Button(botones, text='Cancelar', command=dialogo.destroy).pack(side='right')
        dialogo.grab_set()
        next(iter(entradas.values()))[0].focus_set()

    # ---------------- USUARIOS E INICIO DE SESION ----------------
    def pantalla_login(self):
        self.limpiar()
        self.usuario = None
        marco = ttk.Frame(self.ventana, padding=35)
        marco.place(relx=.5, rely=.5, anchor='center', width=420)
        ttk.Label(marco, text='Mi blog', style='Titulo.TLabel').pack(pady=10)
        ttk.Label(marco, text='Inicia sesion o crea tu cuenta del blog.').pack(pady=10)
        ttk.Label(marco, text='Email').pack(anchor='w')
        email = ttk.Entry(marco)
        email.pack(fill='x', pady=(3, 12))
        ttk.Label(marco, text='Password').pack(anchor='w')
        password = ttk.Entry(marco, show='*')
        password.pack(fill='x', pady=(3, 12))

        def entrar():
            filas = consultar(self.conexion, 'sp_get_user_login', [validar_email(email.get())])
            if not filas or not comprobar_password(password.get(), filas[0]['password_hash']):
                raise ValueError('Email o contraseña incorrectos.')
            self.usuario = filas[0]
            self.pantalla_principal()

        ttk.Button(marco, text='Entrar', command=entrar).pack(fill='x', pady=4)
        ttk.Button(marco, text='Crear cuenta', command=self.registrar_usuario).pack(fill='x', pady=4)
        password.bind('<Return>', lambda evento: entrar())
        email.focus_set()

    def registrar_usuario(self):
        def guardar(datos):
            nombre = validar_texto(datos['Name'], 'Name', 100)
            email = validar_email(datos['Email'])
            if funcion(self.conexion, 'fn_user_exists', [email]):
                raise ValueError('Ese email ya esta registrado.')
            password_hash = proteger_password(datos['Password'])
            ejecutar(self.conexion, 'sp_create_user', [nombre, email, password_hash], True)
            messagebox.showinfo('Cuenta creada', 'Ya puedes entrar con tu email y contraseña.', parent=self.ventana)
        self.formulario('Crear cuenta', [('Name', 'entrada', ''), ('Email', 'entrada', ''), ('Password', 'password', '')], guardar)

    def comprobar_password_actual(self, password):
        filas = consultar(self.conexion, 'sp_get_user_login', [self.usuario['email']])
        if not filas or not comprobar_password(password, filas[0]['password_hash']):
            raise ValueError('La contraseña actual no es correcta.')

    def editar_perfil(self):
        def guardar(datos):
            self.comprobar_password_actual(datos['Current password'])
            nombre = validar_texto(datos['Name'], 'Name', 100)
            email = validar_email(datos['Email'])
            password_hash = proteger_password(datos['New password (opcional)']) if datos['New password (opcional)'] else None
            ejecutar(self.conexion, 'sp_update_user', [self.usuario['user_id'], nombre, email, password_hash])
            self.usuario.update(name=nombre, email=email)
            self.saludo.configure(text='Mi blog · ' + nombre)
            self.refrescar_vista()
        self.formulario('Mi perfil', [('Name', 'entrada', self.usuario['name']), ('Email', 'entrada', self.usuario['email']),
            ('Current password', 'password', ''), ('New password (opcional)', 'password', '')], guardar)

    def borrar_cuenta(self):
        password = simpledialog.askstring('Eliminar mi cuenta', 'Confirma tu contraseña del blog:', show='*', parent=self.ventana)
        if password is None:
            return
        self.comprobar_password_actual(password)
        if messagebox.askyesno('Confirmar', '¿Eliminar tu cuenta? Primero debes borrar tus articulos y comentarios.', parent=self.ventana):
            ejecutar(self.conexion, 'sp_delete_user', [self.usuario['user_id']])
            self.pantalla_login()

    # ---------------- MENU: TRES COLUMNAS ----------------
    def pantalla_principal(self):
        self.limpiar()
        self.filtro = None
        self.vista = 'inicio'
        self.actual_id = None
        self.ventana.configure(bg='#f4f5f0')
        cabecera = ttk.Frame(self.ventana, padding=(24, 16), style='Panel.TFrame')
        cabecera.pack(fill='x')
        self.saludo = ttk.Label(cabecera, text='Mi blog · ' + self.usuario['name'], style='Marca.TLabel')
        self.saludo.pack(side='left')
        ttk.Label(cabecera, text='Un espacio para tus ideas', style='Suave.TLabel').pack(side='right')
        cuerpo = ttk.Frame(self.ventana, padding=16)
        cuerpo.pack(fill='both', expand=True)
        cuerpo.columnconfigure(1, weight=1)
        cuerpo.rowconfigure(0, weight=1)

        izquierda = ttk.Frame(cuerpo, padding=14, style='Panel.TFrame', width=215)
        izquierda.grid(row=0, column=0, sticky='nsew', padx=(0, 14))
        izquierda.grid_propagate(False)
        ttk.Label(izquierda, text='EXPLORAR', style='Seccion.TLabel').pack(anchor='w', pady=(0, 12))
        ttk.Button(izquierda, text='Todas las publicaciones', command=self.inicio).pack(fill='x', pady=(0, 18))
        self.arboles = {}
        for singular, plural, titulo in [('category', 'categories', 'Categorías'), ('tag', 'tags', 'Etiquetas')]:
            arbol = ttk.Treeview(izquierda, show='tree', selectmode='browse', height=4)
            arbol.column('#0', width=175, minwidth=100)
            arbol.pack(fill='x', pady=(0, 5))
            self.arboles[singular] = arbol
            arbol.bind('<<TreeviewSelect>>', lambda evento, s=singular: self.filtrar_catalogo(s))
            arbol.bind('<ButtonRelease-1>', lambda evento, a=arbol: self.desplegar_grupo(evento, a))
            fila = ttk.Frame(izquierda, style='Panel.TFrame')
            fila.pack(fill='x', pady=(0, 20))
            ttk.Button(fila, text='+ Agregar', style='Compacto.TButton', command=lambda s=singular: self.editar_catalogo(s)).pack(fill='x', pady=2)
            ttk.Button(fila, text='Editar selección', style='Compacto.TButton', command=lambda s=singular: self.editar_catalogo(s, True)).pack(fill='x', pady=2)
            ttk.Button(fila, text='Eliminar selección', style='Compacto.TButton', command=lambda s=singular: self.borrar_catalogo(s)).pack(fill='x', pady=2)

        self.centro = ttk.Frame(cuerpo)
        self.centro.grid(row=0, column=1, sticky='nsew')
        derecha = ttk.Frame(cuerpo, padding=14, style='Panel.TFrame', width=170)
        derecha.grid(row=0, column=2, sticky='nsew', padx=(14, 0))
        derecha.grid_propagate(False)
        ttk.Label(derecha, text='TU ESPACIO', style='Seccion.TLabel').pack(anchor='w', pady=(0, 12))
        for texto, comando in [('Mi perfil', self.editar_perfil), ('Usuarios', self.cargar_usuarios), ('Cerrar sesión', self.pantalla_login)]:
            ttk.Button(derecha, text=texto, command=comando).pack(fill='x', pady=5)
        ttk.Separator(derecha).pack(fill='x', pady=18)
        ttk.Button(derecha, text='+ Escribir', style='Principal.TButton', command=self.editar_articulo).pack(fill='x')
        ttk.Button(derecha, text='Mis publicaciones', command=self.mis_publicaciones).pack(fill='x', pady=10)
        ttk.Button(derecha, text='Actualizar', command=self.refrescar_todo).pack(fill='x', pady=5)
        self.cargar_catalogos()
        self.inicio()

    def panel_scroll(self, padre):
        """Una zona desplazable para publicaciones, texto y comentarios."""
        marco = ttk.Frame(padre)
        marco.pack(fill='both', expand=True)
        canvas = tk.Canvas(marco, bg='#f4f5f0', highlightthickness=0)
        barra = ttk.Scrollbar(marco, orient='vertical', command=canvas.yview)
        barra.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        canvas.configure(yscrollcommand=barra.set)
        interior = ttk.Frame(canvas)
        interior._scroll_canvas = canvas
        ventana = canvas.create_window((0, 0), window=interior, anchor='nw')
        interior.bind('<Configure>', lambda evento: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda evento: canvas.itemconfigure(ventana, width=evento.width))
        return interior

    def rueda(self, evento):
        widget = evento.widget
        # Busca el panel al que pertenece el control situado bajo el cursor.
        while widget is not None:
            canvas = getattr(widget, '_scroll_canvas', None)
            if canvas is not None:
                if canvas.yview() != (0.0, 1.0):
                    canvas.yview_scroll(-int(evento.delta / 120), 'units')
                return 'break'
            widget = getattr(widget, 'master', None)

    def texto_flexible(self, padre, texto, estilo='Cuerpo.TLabel'):
        etiqueta = ttk.Label(padre, text=texto, style=estilo, wraplength=430, justify='left')
        etiqueta.pack(fill='x', anchor='w', pady=4)
        etiqueta.bind('<Configure>', lambda evento: etiqueta.configure(wraplength=max(100, evento.width - 8)))
        return etiqueta

    def limpiar_centro(self):
        for widget in self.centro.winfo_children():
            widget.destroy()

    def fecha(self, valor):
        return valor.strftime('%d/%m/%Y') if hasattr(valor, 'strftime') else str(valor or '')

    def inicio(self):
        self.filtro = None
        self.cargar_articulos()

    def mis_publicaciones(self):
        self.filtro = ('mine', None, 'Mis publicaciones')
        self.cargar_articulos()

    def refrescar_todo(self):
        self.cargar_catalogos()
        self.refrescar_vista()

    def refrescar_vista(self):
        if self.vista == 'articulo':
            self.abrir_articulo(self.actual_id)
        elif self.vista == 'usuarios':
            self.cargar_usuarios()
        else:
            self.cargar_articulos()

    def cargar_articulos(self):
        articulos = consultar(self.conexion, 'sp_get_articles')
        if self.filtro:
            tipo, clave, nombre = self.filtro
            if tipo == 'mine':
                articulos = [a for a in articulos if a['user_id'] == self.usuario['user_id']]
            else:
                plural = 'categories' if tipo == 'category' else 'tags'
                articulos = [a for a in articulos if any(str(c[tipo + '_id']) == clave for c in
                    consultar(self.conexion, 'sp_get_article_' + plural, [a['article_id']]))]
        self.vista = 'inicio'
        self.limpiar_centro()
        cabecera = ttk.Frame(self.centro, padding=(4, 4, 4, 16))
        cabecera.pack(fill='x')
        ttk.Label(cabecera, text=self.filtro[2] if self.filtro else 'Últimas publicaciones', style='Titulo.TLabel').pack(anchor='w')
        ttk.Label(cabecera, text='Lee, comparte y conversa.', style='FondoSuave.TLabel').pack(anchor='w', pady=5)
        contenido = self.panel_scroll(self.centro)
        if not articulos:
            self.texto_flexible(contenido, 'Todavía no hay publicaciones aquí. Comparte la primera idea.', 'FondoSuave.TLabel')
        for articulo in articulos:
            tarjeta = ttk.Frame(contenido, padding=22, style='Panel.TFrame')
            tarjeta.pack(fill='x', pady=(0, 14), padx=(0, 6))
            titulo = self.texto_flexible(tarjeta, articulo['title'], 'Tarjeta.TLabel')
            titulo.configure(cursor='hand2')
            titulo.bind('<Button-1>', lambda evento, clave=articulo['article_id']: self.abrir_articulo(clave))
            self.texto_flexible(tarjeta, articulo['author'] + '  ·  ' + self.fecha(articulo['article_date']), 'Suave.TLabel')
            previa = ' '.join(articulo['text'].split())
            self.texto_flexible(tarjeta, previa[:240] + ('…' if len(previa) > 240 else ''))
            ttk.Button(tarjeta, text='Leer publicación →', command=lambda clave=articulo['article_id']: self.abrir_articulo(clave)).pack(anchor='w', pady=(12, 0))

    # ---------------- CATALOGOS DE LA BARRA IZQUIERDA ----------------
    def desplegar_grupo(self, evento, arbol):
        # La flecha funciona con Tkinter; el nombre tambien abre la cascada.
        if arbol.identify_row(evento.y) == 'grupo' and 'text' in arbol.identify_element(evento.x, evento.y):
            arbol.item('grupo', open=not arbol.item('grupo', 'open'))

    def cargar_catalogos(self):
        self.catalogos = {}
        for singular, plural, titulo in [('category', 'categories', 'Categorías'), ('tag', 'tags', 'Etiquetas')]:
            filas = consultar(self.conexion, 'sp_get_' + plural)
            self.catalogos[singular] = filas
            arbol = self.arboles[singular]
            abierto = arbol.item('grupo', 'open') if arbol.exists('grupo') else False
            arbol.delete(*arbol.get_children())
            arbol.insert('', 'end', iid='grupo', text=titulo, open=abierto)
            # Sin registros, no se agregan hijos: no hay cascada vacia ni ID visible.
            for fila in filas:
                arbol.insert('grupo', 'end', iid=str(fila[singular + '_id']), text=fila['name'])

    def filtrar_catalogo(self, singular):
        seleccion = self.arboles[singular].selection()
        if not seleccion or seleccion[0] == 'grupo':
            return
        clave = seleccion[0]
        nombre = self.arboles[singular].item(seleccion[0], 'text')
        self.filtro = (singular, clave, nombre)
        self.cargar_articulos()

    def item_catalogo(self, singular):
        seleccion = self.arboles[singular].selection()
        if not seleccion or seleccion[0] == 'grupo':
            raise ValueError('Despliega la sección y selecciona primero un nombre.')
        clave = seleccion[0]
        return next(f for f in self.catalogos[singular] if str(f[singular + '_id']) == clave)

    def editar_catalogo(self, singular, editar=False):
        item = self.item_catalogo(singular) if editar else None
        titulo = 'categoría' if singular == 'category' else 'etiqueta'
        def guardar(datos):
            nombre = validar_texto(datos['Nombre'], 'Nombre', 80)
            url = validar_url(datos['URL (opcional)'])
            if item:
                ejecutar(self.conexion, 'sp_update_' + singular, [item[singular + '_id'], nombre, url])
                if self.filtro and self.filtro[:2] == (singular, str(item[singular + '_id'])):
                    self.filtro = (singular, item[singular + '_id'], nombre)
            else:
                ejecutar(self.conexion, 'sp_create_' + singular, [nombre, url], True)
            self.refrescar_todo()
        self.formulario(('Editar ' if editar else 'Agregar ') + titulo,
            [('Nombre', 'entrada', item['name'] if item else ''), ('URL (opcional)', 'entrada', item['url'] if item else '')], guardar)

    def borrar_catalogo(self, singular):
        item = self.item_catalogo(singular)
        if not messagebox.askyesno('Eliminar', f'¿Eliminar «{item["name"]}»?\nSe quitará de las publicaciones, sin borrar los artículos.', parent=self.ventana):
            return
        ejecutar(self.conexion, 'sp_delete_' + singular, [item[singular + '_id']])
        if self.filtro and self.filtro[:2] == (singular, str(item[singular + '_id'])):
            self.filtro = None
        self.refrescar_todo()

    # ---------------- LECTURA COMO PUBLICACION ----------------
    def abrir_articulo(self, articulo_id):
        articulo = next((a for a in consultar(self.conexion, 'sp_get_articles') if a['article_id'] == articulo_id), None)
        if articulo is None:
            self.inicio()
            raise ValueError('Esta publicación ya no existe.')
        categorias = consultar(self.conexion, 'sp_get_article_categories', [articulo_id])
        etiquetas = consultar(self.conexion, 'sp_get_article_tags', [articulo_id])
        comentarios = consultar(self.conexion, 'sp_get_comments', [articulo_id])
        self.vista, self.actual_id = 'articulo', articulo_id
        self.limpiar_centro()
        ttk.Button(self.centro, text='← Volver a las publicaciones', command=self.cargar_articulos).pack(anchor='w', pady=(0, 12))
        contenido = self.panel_scroll(self.centro)
        papel = ttk.Frame(contenido, padding=24, style='Panel.TFrame')
        papel.pack(fill='x', padx=(0, 6), pady=(0, 12))
        cabecera = ttk.Frame(papel, style='Panel.TFrame')
        cabecera.pack(fill='x')
        cabecera.columnconfigure(0, weight=1)
        titulo = ttk.Label(cabecera, text=articulo['title'], style='Lectura.TLabel', wraplength=380, justify='left')
        titulo.grid(row=0, column=0, sticky='ew')
        titulo.bind('<Configure>', lambda e: titulo.configure(wraplength=max(100, e.width - 8)))
        if articulo['user_id'] == self.usuario['user_id']:
            ttk.Button(cabecera, text='Editar', command=lambda: self.editar_articulo(articulo)).grid(row=0, column=1, sticky='ne', padx=(12, 0))
        self.texto_flexible(papel, articulo['author'] + '  ·  ' + self.fecha(articulo['article_date']), 'Suave.TLabel')
        ttk.Separator(papel).pack(fill='x', pady=18)
        self.texto_flexible(papel, articulo['text'], 'TextoLectura.TLabel')
        if categorias or etiquetas:
            ttk.Separator(papel).pack(fill='x', pady=18)
            self.texto_flexible(papel, ' · '.join([c['name'] for c in categorias] + ['#' + t['name'] for t in etiquetas]), 'Suave.TLabel')
        ttk.Label(contenido, text=f'Comentarios ({len(comentarios)})', style='Titulo.TLabel').pack(anchor='w', pady=(18, 10))
        if not comentarios:
            self.texto_flexible(contenido, 'Sé la primera persona en comentar.', 'FondoSuave.TLabel')
        for comentario in comentarios:
            tarjeta = ttk.Frame(contenido, padding=18, style='Panel.TFrame')
            tarjeta.pack(fill='x', padx=(0, 6), pady=(0, 10))
            self.texto_flexible(tarjeta, comentario['name'], 'Nombre.TLabel')
            self.texto_flexible(tarjeta, comentario['comment_text'])
            if comentario['url']:
                self.texto_flexible(tarjeta, comentario['url'], 'Suave.TLabel')
            if comentario['user_id'] == self.usuario['user_id']:
                botones = ttk.Frame(tarjeta, style='Panel.TFrame')
                botones.pack(fill='x', pady=(8, 0))
                ttk.Button(botones, text='Editar', command=lambda c=comentario: self.editar_comentario(c, articulo_id)).pack(side='left')
                ttk.Button(botones, text='Eliminar', command=lambda c=comentario: self.borrar_comentario(c, articulo_id)).pack(side='left', padx=6)
        formulario = ttk.Frame(contenido, padding=18, style='Panel.TFrame')
        formulario.pack(fill='x', padx=(0, 6), pady=(12, 20))
        ttk.Label(formulario, text='Escribe tu comentario...', style='Nombre.TLabel').pack(anchor='w', pady=(0, 8))
        entrada = tk.Text(formulario, height=4, wrap='word', font=('Segoe UI', 11), relief='solid', bd=1,
                          highlightthickness=0, padx=12, pady=10, fg='#263d36', bg='#fafcf9')
        entrada.pack(fill='x')
        ttk.Label(formulario, text='Hasta 2,000 caracteres', style='Suave.TLabel').pack(anchor='w', pady=5)
        def comentar():
            texto = validar_texto(entrada.get('1.0', 'end-1c'), 'Comentario', 2000)
            ejecutar(self.conexion, 'sp_create_comment', [articulo_id, self.usuario['user_id'], self.usuario['name'], None, texto], True)
            self.abrir_articulo(articulo_id)
        ttk.Button(formulario, text='Publicar comentario', style='Principal.TButton', command=comentar).pack(anchor='e', pady=(8, 0))

    def editar_comentario(self, comentario, articulo_id):
        def guardar(datos):
            texto = validar_texto(datos['Comentario'], 'Comentario', 2000)
            url = validar_url(datos['URL (opcional)'])
            ejecutar(self.conexion, 'sp_update_comment', [comentario['comment_id'], self.usuario['user_id'], self.usuario['name'], url, texto])
            self.abrir_articulo(articulo_id)
        self.formulario('Editar comentario', [('URL (opcional)', 'entrada', comentario['url']), ('Comentario', 'texto', comentario['comment_text'])], guardar)

    def borrar_comentario(self, comentario, articulo_id):
        if messagebox.askyesno('Eliminar comentario', '¿Eliminar tu comentario?', parent=self.ventana):
            ejecutar(self.conexion, 'sp_delete_comment', [comentario['comment_id'], self.usuario['user_id']])
            self.abrir_articulo(articulo_id)

    # ---------------- EDITOR COMPLETO ----------------
    def editar_articulo(self, articulo=None):
        if articulo and articulo['user_id'] != self.usuario['user_id']:
            raise ValueError('Solo puedes editar tus publicaciones.')
        categorias = consultar(self.conexion, 'sp_get_categories')
        etiquetas = consultar(self.conexion, 'sp_get_tags')
        articulo_id = articulo['article_id'] if articulo else None
        elegidas_c = {c['category_id'] for c in consultar(self.conexion, 'sp_get_article_categories', [articulo_id])} if articulo else set()
        elegidas_t = {t['tag_id'] for t in consultar(self.conexion, 'sp_get_article_tags', [articulo_id])} if articulo else set()
        dialogo = tk.Toplevel(self.ventana)
        dialogo.title('Editar publicación' if articulo else 'Nueva publicación')
        dialogo.geometry('800x680')
        dialogo.minsize(660, 550)
        dialogo.transient(self.ventana)
        dialogo.configure(bg='#f4f5f0')
        # Botones fijos: siguen visibles aunque la lista de etiquetas sea larga.
        botones = ttk.Frame(dialogo, padding=16)
        botones.pack(side='bottom', fill='x')
        area = self.panel_scroll(dialogo)
        marco = ttk.Frame(area, padding=22)
        marco.pack(fill='both', expand=True)
        ttk.Label(marco, text='Tu publicación', style='Titulo.TLabel').pack(anchor='w', pady=(0, 14))
        ttk.Label(marco, text='Título').pack(anchor='w')
        titulo = ttk.Entry(marco, font=('Segoe UI', 13))
        titulo.insert(0, articulo['title'] if articulo else '')
        titulo.pack(fill='x', pady=(5, 16))
        ttk.Label(marco, text='Contenido').pack(anchor='w')
        texto = ScrolledText(marco, height=12, wrap='word', font=('Segoe UI', 11), padx=12, pady=12, relief='solid', bd=1)
        texto.insert('1.0', articulo['text'] if articulo else '')
        texto.pack(fill='x', pady=(5, 16))
        variables = {}
        for singular, nombre, filas, elegidos in [('category', 'Categorías', categorias, elegidas_c), ('tag', 'Etiquetas', etiquetas, elegidas_t)]:
            ttk.Label(marco, text=nombre, font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=(10, 6))
            variables[singular] = {}
            if not filas:
                ttk.Label(marco, text='Aún no hay registros. Puedes agregarlos desde la barra izquierda.').pack(anchor='w')
            for fila in filas:
                clave = fila[singular + '_id']
                variable = tk.BooleanVar(value=clave in elegidos)
                variables[singular][clave] = variable
                ttk.Checkbutton(marco, text=fila['name'], variable=variable).pack(anchor='w', pady=2)
        def guardar():
            try:
                nuevo_id = guardar_publicacion(self.conexion, self.usuario['user_id'],
                    validar_texto(titulo.get(), 'Título', 200), validar_texto(texto.get('1.0', 'end-1c'), 'Contenido', 100000),
                    [k for k, v in variables['category'].items() if v.get()],
                    [k for k, v in variables['tag'].items() if v.get()], articulo_id)
            except Exception as error:
                self.mostrar_error(error, dialogo)
                return
            dialogo.destroy()
            self.abrir_articulo(nuevo_id)
        ttk.Button(botones, text='Guardar publicación', style='Principal.TButton', command=guardar).pack(side='right')
        ttk.Button(botones, text='Cancelar', command=dialogo.destroy).pack(side='right', padx=10)
        if articulo:
            def borrar():
                if messagebox.askyesno('Eliminar publicación', '¿Eliminar esta publicación y sus comentarios?', parent=dialogo):
                    ejecutar(self.conexion, 'sp_delete_article', [articulo_id, self.usuario['user_id']])
                    dialogo.destroy()
                    self.cargar_articulos()
            ttk.Button(botones, text='Eliminar publicación', command=borrar).pack(side='left')
        dialogo.grab_set()
        titulo.focus_set()

    def cargar_usuarios(self):
        filas = consultar(self.conexion, 'sp_get_users')
        self.vista = 'usuarios'
        self.limpiar_centro()
        ttk.Label(self.centro, text='Nuestra comunidad', style='Titulo.TLabel').pack(anchor='w', pady=(4, 18))
        contenido = self.panel_scroll(self.centro)
        for usuario in filas:
            tarjeta = ttk.Frame(contenido, padding=20, style='Panel.TFrame')
            tarjeta.pack(fill='x', pady=(0, 12), padx=(0, 6))
            self.texto_flexible(tarjeta, usuario['name'], 'Tarjeta.TLabel')
            cantidad = funcion(self.conexion, 'fn_article_count', [usuario['user_id']])
            self.texto_flexible(tarjeta, f'{cantidad} publicaciones', 'Suave.TLabel')
            if usuario['user_id'] == self.usuario['user_id']:
                ttk.Button(tarjeta, text='Editar mi perfil', command=self.editar_perfil).pack(anchor='w', pady=8)
        ttk.Button(contenido, text='Eliminar mi cuenta', command=self.borrar_cuenta).pack(anchor='w', pady=16)

    def cerrar(self):
        try:
            self.conexion.close()
        finally:
            self.ventana.destroy()



def main():
    ventana = tk.Tk()
    ventana.withdraw()
    # La contraseña puede venir del entorno o del diálogo de conexión.
    # Documents\Codex\2026-11-18\nec\Neo4j
    #5cad72c412c54f8aab3b7f941a92ae7f
    password = os.environ.get('NEO4J_PASSWORD')
    while True:
        if not password:
            password = simpledialog.askstring('Conexión Neo4j', 'Contraseña de Neo4j:', show='*', parent=ventana)
        if password is None:
            ventana.destroy()
            return
        try:
            conexion = conectar(password)
            del password
            break
        except (DriverError, Neo4jError, ValueError) as error:
            messagebox.showerror('No se pudo conectar', 'Verifica que Neo4j esté encendido y revisa los datos de conexión.\n\n' + str(error), parent=ventana)
            password = None
    BlogApp(ventana, conexion)
    ventana.deiconify()
    ventana.mainloop()


if __name__ == '__main__':
    main()
