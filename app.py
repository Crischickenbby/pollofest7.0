from flask import Flask, render_template, request, flash, redirect, url_for, session
from config import get_db_connection
import psycopg2
from functools import wraps

app = Flask(__name__, template_folder='app/templates', static_folder='app/static')

# Configurar clave secreta desde variables de entorno
import os
from dotenv import load_dotenv
load_dotenv()

app.secret_key = os.getenv('SECRET_KEY', 'tu-clave-secreta-super-segura-para-pollofest-2024')

# Configuración de sesiones
from datetime import timedelta
app.permanent_session_lifetime = timedelta(hours=2)  # Sesión expira en 2 horas

# Decorador para rutas que requieren autenticación
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# Decorador para rutas que requieren ser admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'error')
            return redirect(url_for('home'))
        if session.get('user_id') != 3:  # Solo el admin (ID 3) puede acceder
            flash('No tienes permisos para acceder a esta página', 'error')
            return redirect(url_for('inside'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/logout')
def logout():
    """Cerrar sesión y limpiar datos de sesión"""
    session.clear()
    flash('Sesión cerrada correctamente', 'success')
    return redirect(url_for('home'))

@app.route('/login', methods=['POST'])
def login():
    """Login simple: email + password, si es correcto → inside.html, si no → mensaje de error"""
    conn = None
    cur = None
    
    try:
        # Obtener email y password del formulario
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validar que ambos campos estén llenos
        if not email or not password:
            flash('Por favor completa todos los campos', 'error')
            return redirect(url_for('home'))
        
        # Conectar a la base de datos
        conn = get_db_connection()
        cur = conn.cursor()

        # Buscar usuario con email Y password en la base de datos y obtener su ID
        query = '''SELECT "Email", "ID_User" FROM "User" WHERE "Email" = %s AND "Password" = %s;'''
        cur.execute(query, (email, password))
        user = cur.fetchone()

        if user:
            email_usuario, id_usuario = user
            # Crear sesión de usuario
            session['user_id'] = id_usuario
            session['email'] = email_usuario
            session.permanent = True  # Hacer la sesión permanente
            
            # Verificar si es admin (ID_User = 3)
            if id_usuario == 3:
                # Es admin → ir a panel de administrador
                return redirect(url_for('admin'))
            else:
                # Usuario normal → ir a inside.html
                return redirect(url_for('inside'))
        else:
            # Usuario no encontrado → mensaje de error y quedarse en la misma página
            flash('Usuario no existe o credenciales incorrectas', 'error')
            return redirect(url_for('home'))

    except psycopg2.Error as e:
        print(f"Error de base de datos: {e}")
        flash('Error de conexión a la base de datos', 'error')
        return redirect(url_for('home'))
    
    except Exception as e:
        print(f"Error inesperado: {e}")
        flash('Error al verificar el usuario', 'error')
        return redirect(url_for('home'))

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.route('/inside')
@login_required
def inside():
    return render_template('inside.html')

@app.route('/admin')
@app.route('/admin/buscar')
@admin_required
def admin():
    """Panel de administrador con lista de todos los usuarios"""
    conn = None
    cur = None
    
    try:
        # Conectar a la base de datos
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Obtener parámetro de búsqueda si existe
        busqueda = request.args.get('busqueda', '').strip()
        
        # Si hay una búsqueda, buscar usuarios que coincidan
        if busqueda:
            query = '''
                SELECT "ID_People", "Name", "Last_Name", "Code", "ID_Status_People"
                FROM "People"
                WHERE LOWER("Name") LIKE LOWER(%s) OR LOWER("Last_Name") LIKE LOWER(%s)
                ORDER BY "Name", "Last_Name"
            '''
            busqueda_param = f'%{busqueda}%'
            cur.execute(query, (busqueda_param, busqueda_param))
            usuarios = cur.fetchall()
            mensaje_busqueda = f"Resultados para: '{busqueda}'"
        else:
            # Si no hay búsqueda, no mostrar usuarios (solo el buscador)
            usuarios = []
            mensaje_busqueda = "Ingresa un nombre o apellido para buscar"
        
        return render_template('admin.html', usuarios=usuarios, busqueda=busqueda, mensaje_busqueda=mensaje_busqueda)

    except psycopg2.Error as e:
        print(f"Error de base de datos: {e}")
        flash('Error de conexión a la base de datos', 'error')
        return redirect(url_for('home'))
    
    except Exception as e:
        print(f"Error inesperado: {e}")
        flash('Error al cargar el panel de administrador', 'error')
        return redirect(url_for('home'))

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/admin/cambiar_estado/<int:id_usuario>', methods=['POST'])
@admin_required
def admin_cambiar_estado(id_usuario):
    """Cambiar estado de usuario desde el panel de admin"""
    conn = None
    cur = None
    
    try:
        nuevo_estado = request.form.get('nuevo_estado')
        
        if not nuevo_estado:
            flash('Error: Estado no especificado', 'error')
            return redirect(url_for('admin'))
        
        # Conectar a la base de datos
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Obtener información del usuario
        cur.execute('SELECT "Name", "Last_Name" FROM "People" WHERE "ID_People" = %s', (id_usuario,))
        usuario = cur.fetchone()
        
        if not usuario:
            flash('Error: Usuario no encontrado', 'error')
            return redirect(url_for('admin'))
        
        nombre, apellido = usuario
        
        # Obtener el ID del nuevo estado
        cur.execute('SELECT "ID_Status_People" FROM "Status_People" WHERE "Status_People" = %s', (nuevo_estado,))
        resultado_estado = cur.fetchone()
        
        if not resultado_estado:
            flash(f'Error: Estado "{nuevo_estado}" no encontrado', 'error')
            return redirect(url_for('admin'))
        
        id_nuevo_estado = resultado_estado[0]
        
        # Actualizar el estado del usuario
        cur.execute('UPDATE "People" SET "ID_Status_People" = %s WHERE "ID_People" = %s', (id_nuevo_estado, id_usuario))
        conn.commit()
        
        if cur.rowcount > 0:
            flash(f'✅ Estado actualizado: {nombre} {apellido} → "{nuevo_estado}"', 'success')
        else:
            flash('Error: No se pudo actualizar el estado', 'error')
        
        return redirect(url_for('admin'))

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Error de base de datos: {e}")
        flash('Error de conexión a la base de datos', 'error')
        return redirect(url_for('admin'))
    
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error inesperado: {e}")
        flash('Error al cambiar el estado', 'error')
        return redirect(url_for('admin'))

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/verificar', methods=['POST'])
@login_required
def verificar():
    """Verificar código y mostrar información del usuario"""
    conn = None
    cur = None
    
    try:
        # Obtener código del formulario
        codigo = request.form.get('codigo')
        
        # Validar que el código esté lleno
        if not codigo:
            flash('Por favor ingresa un código', 'error')
            return redirect(url_for('inside'))
        
        # Limpiar código (quitar espacios y convertir a mayúsculas)
        codigo = codigo.strip().upper()
        
        # Conectar a la base de datos
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Buscar usuario por código con JOIN para obtener el estado
        query = '''
            SELECT p."Name", p."Last_Name", p."Code", s."Status_People"
            FROM "People" p
            JOIN "Status_People" s ON p."ID_Status_People" = s."ID_Status_People"
            WHERE p."Code" = %s
            '''

        cur.execute(query, (codigo,))
        usuario = cur.fetchone()
        
        if usuario:
            nombre, apellido, codigo_usuario, estado = usuario
            
            # Determinar mensaje según el estado
            if estado == "No ha pasado":
                # Primero enviar el mensaje de estado (para que aparezca arriba)
                mensaje = f"{nombre} {apellido} no ha pasado"
                flash(mensaje, 'no-paso')
                # Después enviar el botón (para que aparezca abajo)
                flash(f'<form method="POST" action="/cambiar_estado" style="display:inline;"><input type="hidden" name="codigo" value="{codigo_usuario}"><button type="submit" class="btn-cambiar-estado">Marcar como Ya pasó</button></form>', 'action')
            else:  # "Ya pasó"
                # Usuario ya pasó - solo mostrar mensaje en rojo sin botón adicional
                mensaje = f"{nombre} {apellido} ya pasó"
                flash(mensaje, 'ya-paso')
        else:
            flash('Código no encontrado', 'error')
        
        return redirect(url_for('inside'))

    except psycopg2.Error as e:
        print(f"Error de base de datos: {e}")
        flash('Error de conexión a la base de datos', 'error')
        return redirect(url_for('inside'))
    
    except Exception as e:
        print(f"Error inesperado: {e}")
        flash('Error al verificar el código', 'error')
        return redirect(url_for('inside'))

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/cambiar_estado', methods=['POST'])
@login_required
def cambiar_estado():
    """Cambiar el estado de un usuario de 'No ha pasado' a 'Ya pasó'"""
    conn = None
    cur = None
    
    try:
        # Obtener código del formulario
        codigo = request.form.get('codigo')
        
        if not codigo:
            flash('Error: Código no proporcionado', 'error')
            return redirect(url_for('inside'))
        
        # Conectar a la base de datos
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Primero verificar el estado actual del usuario
        query_verificar = '''
            SELECT p."Name", p."Last_Name", s."Status_People", s."ID_Status_People"
            FROM "People" p
            JOIN "Status_People" s ON p."ID_Status_People" = s."ID_Status_People"
            WHERE p."Code" = %s
        '''
        cur.execute(query_verificar, (codigo,))
        usuario = cur.fetchone()
        
        if not usuario:
            flash('Error: Usuario no encontrado', 'error')
            return redirect(url_for('inside'))
        
        nombre, apellido, estado_actual, id_estado_actual = usuario
        
        # Solo cambiar si el estado actual es "No ha pasado"
        if estado_actual != "No ha pasado":
            flash(f'El usuario {nombre} {apellido} ya tiene el estado: {estado_actual}', 'info')
            return redirect(url_for('inside'))
        
        # Obtener el ID del estado "Ya pasó"
        cur.execute('SELECT "ID_Status_People" FROM "Status_People" WHERE "Status_People" = %s', ('Ya pasó',))
        resultado_estado = cur.fetchone()
        
        if not resultado_estado:
            flash('Error: No se pudo encontrar el estado "Ya pasó" en la base de datos', 'error')
            return redirect(url_for('inside'))
        
        id_ya_paso = resultado_estado[0]
        
        # Actualizar el estado del usuario
        query_actualizar = '''
            UPDATE "People" 
            SET "ID_Status_People" = %s 
            WHERE "Code" = %s
        '''
        cur.execute(query_actualizar, (id_ya_paso, codigo))
        conn.commit()
        
        # Verificar que se actualizó correctamente
        if cur.rowcount > 0:
            flash(f'✅ Estado actualizado: {nombre} {apellido} ahora está marcado como "Ya pasó"', 'success')
        else:
            flash('Error: No se pudo actualizar el estado', 'error')
        
        return redirect(url_for('inside'))

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Error de base de datos: {e}")
        flash('Error de conexión a la base de datos', 'error')
        return redirect(url_for('inside'))
    
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error inesperado: {e}")
        flash('Error al cambiar el estado', 'error')
        return redirect(url_for('inside'))

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/insertar')
@admin_required
def mostrar_insertar():
    """Mostrar formulario para insertar usuarios"""
    return render_template('insertar.html')

@app.route('/insertar-usuario', methods=['POST'])
@admin_required
def insertar_usuario():
    """Insertar nuevo usuario en la tabla People con código único"""
    import random # Para generar código único de letras y números
    import string # Para generar código único de letras y números 
    #estos son diferentes random sirve para generar codigo unico y string para usar letras y numeros

    conn = None
    cur = None
    
    try:
        # Obtener datos del formulario
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        id_status = 1  # Estado por defecto: Activo
        
        # Validar que todos los campos estén llenos
        if not nombre or not apellido:
            flash('Por favor completa todos los campos', 'error')
            return redirect(url_for('mostrar_insertar'))
        
        # Limpiar y validar datos
        nombre = nombre.strip().title()  # Capitalize first letter
        apellido = apellido.strip().title()
        
        # Conectar a la base de datos
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Generar código único
        codigo_unico = generar_codigo_unico(cur)
        
        # Insertar usuario en la tabla People
        query = '''
            INSERT INTO "People" ("Name", "Last_Name", "Code", "ID_Status_People") 
            VALUES (%s, %s, %s, %s)
        '''
        cur.execute(query, (nombre, apellido, codigo_unico, id_status))
        conn.commit()
        
        flash(f'Usuario {nombre} {apellido} registrado exitosamente con código: {codigo_unico}', 'success')
        return redirect(url_for('mostrar_insertar'))

    except psycopg2.IntegrityError as e:
        conn.rollback()
        print(f"Error de integridad: {e}")
        flash('Error: Este usuario ya existe o hay un problema con los datos', 'error')
        return redirect(url_for('mostrar_insertar'))
    
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Error de base de datos: {e}")
        flash('Error de conexión a la base de datos', 'error')
        return redirect(url_for('mostrar_insertar'))
    
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error inesperado: {e}")
        flash('Error al registrar el usuario', 'error')
        return redirect(url_for('mostrar_insertar'))

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def generar_codigo_unico(cursor, longitud=6):
    """Generar código único de letras mayúsculas y números"""
    import random
    import string
    
    max_intentos = 100
    for intento in range(max_intentos):
        # Generar código aleatorio: 4 letras + 4 números
        letras = ''.join(random.choices(string.ascii_uppercase, k=4))
        numeros = ''.join(random.choices(string.digits, k=4))
        codigo = letras + numeros
        
        # Verificar si el código ya existe
        cursor.execute('SELECT 1 FROM "People" WHERE "Code" = %s', (codigo,))
        if not cursor.fetchone():
            return codigo
    
    # Si después de 100 intentos no encuentra código único, generar uno más largo
    letras = ''.join(random.choices(string.ascii_uppercase, k=6))
    numeros = ''.join(random.choices(string.digits, k=6))
    return letras + numeros


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port)
