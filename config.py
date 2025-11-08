import psycopg2
import os
from dotenv import load_dotenv #esto es para cargar las variables de entorno desde un archivo .env

# Cargar variables de entorno
load_dotenv()

# Configuración de la base de datos
# Para Railway/Render, usar DATABASE_URL si existe, sino usar variables individuales
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    # Producción: usar DATABASE_URL completa
    DATABASE_CONFIG = DATABASE_URL
else:
    # Desarrollo: usar variables individuales
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_NAME = os.getenv('DB_NAME', 'pollofest')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DATABASE_CONFIG = {
        'host': DB_HOST,
        'database': DB_NAME,
        'user': DB_USER,
        'password': DB_PASSWORD
    }

# Clave secreta para Flask
SECRET_KEY = os.getenv('SECRET_KEY', 'clave-por-defecto') #esto sirve para que no se vea la clave en el código de la aplicación y se mantenga segura osea en palabras mas sencillas es para que no se vea la clave en el código de la aplicación y se mantenga segura
#con codigo de la aplicación me refiero a que es el código que se ejecuta en el servidor

# Función para obtener una conexión a la base de datos
def get_db_connection():
    if isinstance(DATABASE_CONFIG, str):
        # Producción: usar DATABASE_URL
        return psycopg2.connect(DATABASE_CONFIG)
    else:
        # Desarrollo: usar diccionario de configuración
        return psycopg2.connect(**DATABASE_CONFIG)
