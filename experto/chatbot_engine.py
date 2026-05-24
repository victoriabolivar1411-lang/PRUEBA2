"""
=============================================================================
SISTEMA EXPERTO PARA APOYO PEDAGÓGICO EN TEA
=============================================================================
Módulo: experto/chatbot_engine.py
Descripción: Motor NLP ligero (sin dependencias externas) para el chatbot
             del Sistema Experto TEA. Ofrece respuestas de dominio experto
             en TEA, desarrollo infantil, señales de alerta, terapias,
             estrategias educativas, apoyos visuales y mitos.
=============================================================================
"""

import unicodedata
import re
import os

try:
    import google.generativeai as genai
    # Si hay clave en el entorno, configurarla
    _api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if _api_key:
        genai.configure(api_key=_api_key)
        GEMINI_AVAILABLE = True
    else:
        GEMINI_AVAILABLE = False
except ImportError:
    GEMINI_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# NORMALIZACIÓN DE TEXTO
# ─────────────────────────────────────────────────────────────────────────────

def _normalizar(texto: str) -> str:
    """
    Convierte el texto a minúsculas, elimina tildes y caracteres especiales.
    Retorna solo letras y espacios para facilitar la comparación.
    """
    texto = texto.lower().strip()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    texto = re.sub(r'[^a-z0-9\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto


# ─────────────────────────────────────────────────────────────────────────────
# AVISO MÉDICO ESTÁNDAR DE ADVERTENCIA Y EMPATÍA
# ─────────────────────────────────────────────────────────────────────────────

AVISO_MEDICO = (
    '<br><br><small style="color: var(--c-muted); display: block; line-height: 1.4; '
    'border-top: 1px dashed rgba(255,255,255,0.15); padding-top: 10px; margin-top: 10px;">'
    '⚠️ <strong>Nota de orientación:</strong> Soy un asistente informativo del sistema. '
    'Esta información es con fines netamente educativos y de apoyo, y bajo ningún concepto '
    'reemplaza una evaluación médica, clínica o psicopedagógica profesional. Si tienes dudas '
    'sobre el desarrollo de tu hijo, te sugerimos consultar con un pediatra, neuropediatra '
    'o psicólogo infantil clínico.'
    '</small>'
)


# ─────────────────────────────────────────────────────────────────────────────
# BASE DE CONOCIMIENTO DE INTENCIONES Y PALABRAS CLAVE
# ─────────────────────────────────────────────────────────────────────────────

INTENCIONES = {
    'saludo': [
        ('hola', 3), ('buenas', 2), ('buenos dias', 3), ('buenas tardes', 3),
        ('buenas noches', 3), ('hey', 2), ('que tal', 2), ('como estas', 2),
        ('saludos', 2), ('ola', 2), ('buen dia', 3),
    ],
    'despedida': [
        ('adios', 3), ('chao', 3), ('hasta luego', 3), ('hasta pronto', 3),
        ('nos vemos', 2), ('bye', 3), ('gracias por todo', 2),
    ],
    'horarios': [
        ('horario', 4), ('hora', 3), ('atienden', 3), ('atencion', 3),
        ('abren', 3), ('cierran', 3), ('a que hora', 4),
    ],
    'contacto': [
        ('telefono', 4), ('correo', 4), ('email', 4), ('contacto', 4),
        ('contactar', 3), ('whatsapp', 3), ('llamar', 3),
        ('como puedo contactarlos', 5),
    ],
    'ubicacion': [
        ('donde', 3), ('direccion', 4), ('ubicacion', 4), ('donde estan', 5),
        ('municipio', 3), ('sede', 3),
        ('donde estan ubicados', 5),
    ],
    'funcionalidades': [
        ('que puedo hacer', 5), ('para que sirve', 5), ('que hace', 4),
        ('funciones', 4), ('funcionalidades', 4), ('que ofrece', 4),
        ('que puedo hacer en el sistema', 5),
    ],
    'ayuda': [
        ('ayuda', 4), ('help', 4), ('no se', 3), ('no entiendo', 3),
        ('como funciona', 4), ('como se usa', 4), ('tutorial', 4),
        ('necesito ayuda para usar el sistema', 5),
    ],
    'problemas_tecnicos': [
        ('no puedo entrar', 5), ('olvide contrasena', 5), ('olvide mi contrasena', 5),
        ('contrasena', 4), ('no recuerdo', 3), ('no funciona', 4),
        ('error', 3), ('recuperar contrasena', 5),
        ('no puedo entrar al sistema', 5),
    ],
    'registro_estudiante': [
        ('registrar estudiante', 5), ('nuevo estudiante', 5),
        ('agregar estudiante', 5), ('como registro', 4),
        ('como registro un estudiante', 5),
    ],
    'registro_usuario': [
        ('registrarme', 4), ('como me registro', 5), ('crear cuenta', 5),
        ('nueva cuenta', 4),
    ],
    'evaluacion': [
        ('evaluacion', 4), ('evaluar', 4), ('dsm5', 5), ('dsm-5', 5), ('dsm 5', 5), ('diagnostico', 4),
        ('como evaluo', 5), ('evaluacion dsm 5', 5),
        ('como hago una evaluacion', 5),
    ],
    'resultados': [
        ('resultados', 4), ('recomendaciones', 4), ('informe', 4),
        ('ver resultados', 5), ('ver recomendaciones', 5),
    ],
    'perfil': [
        ('perfil', 4), ('mi perfil', 5), ('mis datos', 4),
        ('editar perfil', 5),
    ],

    # ── INTENCIONES DE DOMINIO EDUCATIVO / CLÍNICO ──────────────────────────
    'que_es_tea': [
        ('que es tea', 5), ('que es el tea', 5), ('que es autismo', 5),
        ('que es el autismo', 5), ('definicion de tea', 5), ('definicion de autismo', 5),
        ('es lo mismo autismo que tea', 5), ('el autismo tiene cura', 5),
        ('tiene cura', 4), ('tiene cura el autismo', 5), ('es una enfermedad', 4),
        ('niveles de apoyo', 4), ('grados de autismo', 4), ('nivel 1', 3),
        ('nivel 2', 3), ('nivel 3', 3), ('grado de apoyo', 4),
        ('que es el trastorno del espectro autista', 5),
    ],
    'sintomas_tea': [
        ('sintomas', 4), ('caracteristicas', 4), ('senales de autismo', 5),
        ('rasgos de autismo', 4), ('como se manifiesta', 4), ('conductas', 3),
        ('comportamiento de autismo', 4), ('criterios de autismo', 4),
        ('cuales son los criterios del dsm-5', 5),
        ('cuales son los criterios del dsm5', 5),
        ('criterios dsm 5', 5),
        ('criterios dsm-5', 5),
        ('criterios dsm5', 5),
        ('dsm 5', 4),
        ('dsm-5', 4),
        ('dsm5', 4),
    ],
    'diagnostico_tea': [
        ('como se diagnostica', 5), ('diagnostico de autismo', 5),
        ('diagnostico de tea', 5), ('quien diagnostica', 4),
        ('a que edad se detecta', 5), ('edad de deteccion', 5),
        ('edad para diagnostico', 4), ('pruebas de autismo', 4),
    ],
    'alertas_tempranas': [
        ('como saber si mi hijo tiene', 5), ('primeros signos', 5),
        ('primeras senales', 4), ('senales en bebes', 5),
        ('mi hijo no habla', 5), ('no habla nada', 4),
        ('regresion', 4), ('perdio palabras', 5), ('dejo de hablar', 5),
        ('no hace contacto visual', 4), ('no mira', 3),
        ('cuando ir al especialista', 4),
        ('como saber si mi hijo tiene autismo', 5),
    ],
    'otros_trastornos': [
        ('tdah', 5), ('hiperactividad', 4), ('deficit de atencion', 4),
        ('trastorno del lenguaje', 5), ('tdl', 5), ('discapacidad intelectual', 5),
        ('procesamiento sensorial', 5), ('sensibilidad sensorial', 5),
        ('dislexia', 5), ('discalculia', 5), ('disgrafia', 5),
        ('asperger', 4),
        ('diferencia con otros trastornos de desarrollo', 5),
    ],
    'terapias_tea': [
        ('terapias', 4), ('terapia de lenguaje', 4), ('terapia ocupacional', 4),
        ('metodo aba', 5), ('aba', 5), ('teacch', 5), ('metodo denver', 5),
        ('esdm', 4), ('tratamiento de autismo', 4),
        ('que terapias existen para el autismo', 5),
        ('que terapias existen', 5),
        ('que es el metodo aba y teacch', 5),
    ],
    'estrategias_aula_casa': [
        ('estrategias en el aula', 5), ('estrategias escolares', 4),
        ('que hacer si tiene crisis', 5), ('crisis de autismo', 5),
        ('berrinche o rabieta', 4), ('rabietas', 4), ('comunicacion no verbal', 5),
        ('apoyos visuales', 5), ('pictogramas', 4),
        ('que estrategias funcionan en el aula', 5),
    ],
    'desarrollo_infantil': [
        ('hitos del desarrollo', 5), ('desarrollo infantil', 4),
        ('cuando empezar a hablar', 5), ('juego simbolico', 5),
        ('no gatea', 4), ('gatear', 3), ('hitos', 3),
        ('hitos del desarrollo infantil', 5),
    ],
    'apoyo_padres': [
        ('ayuda para padres', 4), ('ayudar en casa', 4), ('derechos escolares', 5),
        ('discapacidad en la escuela', 5), ('piee', 5), ('plan individualizado', 5),
        ('sobrecarga del cuidador', 5), ('cuidador cansado', 4),
        ('donde encontrar especialistas', 5), ('psicologos en', 3),
    ],
    'mitos_realidades': [
        ('vacunas causan', 5), ('vacunas y autismo', 5),
        ('habilidades especiales', 4), ('todos son sabios', 4),
        ('savant', 4), ('es una enfermedad mental', 4),
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# DETECCIÓN DE INTENCIÓN Y RESOLUCIÓN
# ─────────────────────────────────────────────────────────────────────────────

def detectar_intencion(texto: str, historial: list) -> str:
    """
    Analiza el texto del usuario y retorna la intención más probable.
    """
    texto_norm = _normalizar(texto)
    palabras = set(texto_norm.split())

    puntuaciones = {}
    for intencion, keywords in INTENCIONES.items():
        max_score = 0
        for kw, peso in keywords:
            kw_norm = _normalizar(kw)
            
            # 1. Coincidencia exacta de toda la entrada
            if kw_norm == texto_norm:
                score = peso * 1.5
            # 2. Coincidencia exacta de subfrase
            elif kw_norm in texto_norm:
                score = peso
            # 3. Coincidencia de palabras individuales
            else:
                kw_palabras = set(kw_norm.split())
                coincidencia = kw_palabras & palabras
                if coincidencia:
                    ratio = len(coincidencia) / len(kw_palabras)
                    # Penalizar si solo coinciden palabras genéricas del dominio ("autismo", "tea")
                    # en keywords de múltiples palabras, para evitar falsos positivos constantes.
                    palabras_comunes = {'autismo', 'tea', 'el', 'la', 'lo', 'los', 'las', 'un', 'una', 'de', 'del', 'que'}
                    coincidencia_sin_comunes = coincidencia - palabras_comunes
                    if not coincidencia_sin_comunes and len(kw_palabras) > 1:
                        ratio *= 0.25  # Penalización fuerte si solo coinciden palabras comunes

                    score = ratio * peso * 0.6
                else:
                    score = 0
            
            if score > max_score:
                max_score = score

        if max_score > 0:
            puntuaciones[intencion] = max_score

    mejor = max(puntuaciones, key=puntuaciones.get) if puntuaciones else None

    # Umbral mínimo de confianza ajustado a 0.8
    if mejor and puntuaciones[mejor] >= 0.8:
        return mejor

    # Si ninguna intención supera el umbral, intentamos buscar en la base de conocimientos
    # usando la duda como posible síntoma o comportamiento.
    if buscar_reglas_por_palabras(texto):
        return 'comportamiento_duda'

    return _resolver_por_contexto(historial)


def _resolver_por_contexto(historial: list) -> str:
    """
    Si no hay intención clara, intenta inferirla del contexto previo.
    """
    if not historial:
        return 'fallback'

    ultimos_bot = [m for m in historial[-4:] if m.get('role') == 'bot']
    if ultimos_bot:
        ultimo_intencion = ultimos_bot[-1].get('intencion', '')
        if ultimo_intencion in ('registro_estudiante', 'evaluacion', 'ayuda', 'que_es_tea', 'alertas_tempranas'):
            return ultimo_intencion

    return 'fallback'


# ─────────────────────────────────────────────────────────────────────────────
# BÚSQUEDA DINÁMICA DE REGLAS (BASE DE CONOCIMIENTO)
# ─────────────────────────────────────────────────────────────────────────────

def buscar_reglas_por_palabras(query_texto: str) -> list:
    """
    Busca en la base de datos de reglas del sistema experto (Regla)
    aquellas que coincidan con palabras clave de la consulta del usuario.
    """
    try:
        from experto.models import Regla
    except ImportError:
        return []

    palabras = [p for p in _normalizar(query_texto).split() if len(p) > 3]
    if not palabras:
        return []

    reglas = Regla.objects.filter(activa=True)
    coincidencias = []

    for regla in reglas:
        puntuacion = 0
        texto_busqueda = _normalizar(f"{regla.nombre} {regla.condicion} {regla.recomendacion} {regla.recursos_didacticos}")
        for palabra in palabras:
            if palabra in texto_busqueda:
                puntuacion += 1
        if puntuacion > 0:
            coincidencias.append((regla, puntuacion))

    coincidencias.sort(key=lambda x: x[1], reverse=True)
    return [r[0] for r in coincidencias[:2]]


# ─────────────────────────────────────────────────────────────────────────────
# GENERADOR DE RESPUESTAS
# ─────────────────────────────────────────────────────────────────────────────

def generar_respuesta(intencion: str, contexto: dict) -> dict:
    """
    Genera la respuesta del bot según la intención detectada.
    """
    nombre = contexto.get('nombre', '')
    saludo_nombre = f', {nombre}' if nombre else ''

    respuestas = {

        # ── SALUDOS Y OPERATIVOS ───────────────────────────────────────────
        'saludo': {
            'texto': (
                f'¡Hola{saludo_nombre}! 👋 Soy <strong>TEAbot</strong> 🧩, tu asesor virtual '
                f'sobre desarrollo infantil, crianza y Trastorno del Espectro Autista.<br><br>'
                f'Estoy diseñado para ayudarte tanto a usar este sistema experto '
                f'como a resolver tus dudas sobre comportamiento y neurodesarrollo. ¿Qué te gustaría consultar?'
            ),
            'botones': [
                {'label': '🧩 ¿Qué es el TEA?', 'value': '¿Qué es el Trastorno del Espectro Autista?'},
                {'label': '👶 Señales de Alerta', 'value': '¿Cómo saber si mi hijo tiene autismo?'},
                {'label': '🛠️ Terapias y Estrategias', 'value': '¿Qué terapias existen para el autismo?'},
                {'label': '📋 Funcionalidades', 'value': '¿Qué puedo hacer en el sistema?'},
            ],
        },

        'despedida': {
            'texto': (
                '👋 ¡Hasta luego! Espero haberte orientado de manera útil. '
                'Recuerda que estoy aquí siempre que tengas dudas sobre el desarrollo infantil '
                'o el uso del sistema. ¡Mucho éxito en tu labor de apoyo pedagógico! 🧩'
            ),
            'botones': [],
        },

        'horarios': {
            'texto': (
                '🕐 <strong>Horario de atención de soporte:</strong><br><br>'
                '• Lunes a Viernes: 7:00 AM – 5:00 PM<br>'
                '• Sábados: 8:00 AM – 12:00 PM<br><br>'
                '💡 La plataforma de evaluaciones está disponible <strong>24/7</strong> '
                'para instructores y representantes.'
            ),
            'botones': [
                {'label': '📞 Contacto', 'value': '¿Cómo puedo contactarlos?'},
            ],
        },

        'contacto': {
            'texto': (
                '📞 <strong>Medios de contacto y orientación técnica:</strong><br><br>'
                '• Correo electrónico: soporte@sistema-tea.edu.ve<br>'
                '• Teléfono: +58 412-555-0001<br>'
                '• Canal de WhatsApp: +58 412-555-0002<br>'
            ),
            'botones': [
                {'label': '📍 Ubicación', 'value': '¿Dónde están ubicados?'},
            ],
        },

        'ubicacion': {
            'texto': (
                '📍 <strong>Nuestra Sede de Orientación:</strong><br><br>'
                '• Estado Bolívar, Municipio Caroní, Av. Principal de Puerto Ordaz.<br>'
                '• Instalaciones de la Unidad Educativa Especializada.'
            ),
            'botones': [
                {'label': '📞 Contactar', 'value': '¿Cómo puedo contactarlos?'},
            ],
        },

        'funcionalidades': {
            'texto': (
                '⚙️ <strong>¿Qué te permite hacer este Sistema Experto?</strong><br><br>'
                '• 👨‍🎓 <strong>Registro y Ficha de Estudiantes:</strong> Administrar datos básicos e historial pedagógico.<br>'
                '• 📋 <strong>Evaluación DSM-5:</strong> Evaluar criterios de Comunicación Social (A) y Conductas Repetitivas (B).<br>'
                '• 📚 <strong>Evaluación Pedagógica:</strong> Determinar el nivel de apoyo escolar necesario.<br>'
                '• 🤖 <strong>Motor de Recomendaciones:</strong> Generación automática de planes de apoyo y recursos didácticos específicos.'
            ),
            'botones': [
                {'label': '➕ Registrar estudiante', 'value': '¿Cómo registro un estudiante?'},
                {'label': '📋 Hacer evaluación', 'value': '¿Cómo hago una evaluación?'},
            ],
        },

        'ayuda': {
            'texto': (
                '❓ <strong>¿Cómo empezar a usar la plataforma?</strong><br><br>'
                '1️⃣ Crea tu cuenta como **Instructor**.<br>'
                '2️⃣ Ingresa a **Mis Estudiantes** y haz clic en *Nuevo Estudiante*.<br>'
                '3️⃣ Haz clic en *Nueva Evaluación DSM-5* en el perfil del estudiante.<br>'
                '4️⃣ Rellena el diagnóstico pedagógico y obtendrás las recomendaciones automáticas creadas por el sistema experto.'
            ),
            'botones': [
                {'label': '➕ Registrar Estudiante', 'value': '¿Cómo registro un estudiante?'},
                {'label': '🔑 Problemas de Acceso', 'value': 'No puedo entrar al sistema'},
            ],
        },

        'problemas_tecnicos': {
            'texto': (
                '🔑 <strong>Recuperación de Contraseña y Acceso:</strong><br><br>'
                'Si olvidaste tus credenciales:<br>'
                '1️⃣ En la pantalla de login, haz clic en <strong>¿Olvidaste tu contraseña?</strong>.<br>'
                '2️⃣ Ingresa tu correo para recibir un código de verificación.<br>'
                '3️⃣ Digita el código e introduce tu nueva contraseña.'
            ),
            'botones': [
                {'label': '🔑 Recuperar Contraseña', 'value': 'recuperar_pass_action'},
                {'label': '📞 Soporte técnico', 'value': '¿Cómo puedo contactarlos?'},
            ],
        },

        'registro_estudiante': {
            'texto': (
                '➕ <strong>Pasos para agregar un estudiante:</strong><br><br>'
                '1️⃣ Inicia sesión y ve a **Mis Estudiantes**.<br>'
                '2️⃣ Haz clic en **➕ Nuevo Estudiante**.<br>'
                '3️⃣ Ingresa nombre, edad, género y los datos de su representante.<br>'
                '4️⃣ Haz clic en Guardar. ¡Listo!'
            ),
            'botones': [
                {'label': '📋 Hacer evaluación', 'value': '¿Cómo hago una evaluación?'},
            ],
        },

        'registro_usuario': {
            'texto': (
                '📝 <strong>Creación de cuenta de Instructor:</strong><br><br>'
                'Haz clic en el botón *Registrarse* de la barra superior. Introduce tu nombre, '
                'cédula/identificación, correo de contacto y contraseña para tener acceso total al panel de evaluaciones.'
            ),
            'botones': [
                {'label': '🚀 Registrarme', 'value': 'registro_action'},
                {'label': '🔑 Iniciar Sesión', 'value': 'login_action'},
            ],
        },

        'evaluacion': {
            'texto': (
                '📋 <strong>Flujo de Evaluación en el Sistema:</strong><br><br>'
                'El sistema cuenta con dos fases evaluativas vinculadas:<br>'
                '1. **Fase Clínica (DSM-5):** Valora déficits en comunicación socioemocional y presencia de patrones conductuales restringidos.<br>'
                '2. **Fase Pedagógica:** Define el nivel de ayuda que el estudiante requiere en el entorno educativo.'
            ),
            'botones': [
                {'label': '➕ Registrar Estudiante', 'value': '¿Cómo registro un estudiante?'},
            ],
        },

        'resultados': {
            'texto': (
                '📊 <strong>Ver Informes y Planes Pedagógicos:</strong><br><br>'
                'Una vez completadas las fases de la evaluación, dirígete a la pestaña del estudiante '
                'y haz clic en **Ver Resultados**. Podrás visualizar e imprimir el plan de apoyo pedagógico '
                'y descargar las sugerencias didácticas.'
            ),
            'botones': [
                {'label': '📊 Ir al Dashboard', 'value': 'dashboard_action'},
            ],
        },

        'perfil': {
            'texto': (
                '👤 <strong>Gestión del perfil del Instructor:</strong><br><br>'
                'En el menú superior derecho, haz clic en tu nombre → **Mi Perfil**. Podrás actualizar '
                'tus datos personales, cambiar la contraseña, definir tu área y subir tu firma digital.'
            ),
            'botones': [],
        },

        'que_es_tea': {
            'texto': (
                '🧩 <strong>Trastorno del Espectro Autista (TEA):</strong><br><br>'
                'El autismo o TEA es una **condición del neurodesarrollo** de base neurobiológica que '
                'afecta la configuración del sistema nervioso y el funcionamiento cerebral. Afecta principalmente '
                'la comunicación social y la flexibilidad de la conducta.<br><br>'
                '• <strong>¿Es lo mismo autismo que TEA?</strong> Sí. Anteriormente se clasificaban por separado '
                '(Autismo clásico, Asperger, TGD no especificado), pero desde el manual DSM-5 se unificaron bajo '
                'el término "Espectro" debido a la gran variabilidad de casos.<br>'
                '• <strong>¿Tiene cura?</strong> Al ser una condición de vida y no una enfermedad, **no tiene "cura"**. '
                'Sin embargo, con una intervención psicoeducativa y terapéutica temprana se logran avances increíbles en autonomía y calidad de vida.<br>'
                '• <strong>Grados/Niveles de apoyo:</strong><br>'
                '&nbsp;&nbsp;• <em>Nivel 1:</em> Requiere apoyo (anteriormente asociado a Asperger).<br>'
                '&nbsp;&nbsp;• <em>Nivel 2:</em> Requiere apoyo sustancial.<br>'
                '&nbsp;&nbsp;• <em>Nivel 3:</em> Requiere apoyo muy sustancial.'
                f'{AVISO_MEDICO}'
            ),
            'botones': [
                {'label': '👶 Señales de Alerta', 'value': '¿Cómo saber si mi hijo tiene autismo?'},
                {'label': '📚 Criterios DSM-5', 'value': '¿Cuáles son los criterios del DSM-5?'},
                {'label': '🛠️ Terapias', 'value': '¿Qué terapias existen para el autismo?'},
            ],
        },

        'sintomas_tea': {
            'texto': (
                '📋 <strong>Criterios Diagnósticos del DSM-5 para TEA:</strong><br><br>'
                'El Manual Diagnóstico y Estadístico de los Trastornos Mentales (DSM-5) establece dos áreas principales de afectación para el diagnóstico del TEA:<br><br>'
                '• <strong>A. Déficits en Comunicación Social e Interacción Social:</strong><br>'
                '&nbsp;&nbsp;1. Dificultades en reciprocidad socioemocional (ej. iniciar/responder interacciones, compartir intereses).<br>'
                '&nbsp;&nbsp;2. Déficits en conductas comunicativas no verbales (ej. contacto visual, lenguaje corporal, uso de gestos).<br>'
                '&nbsp;&nbsp;3. Dificultades para desarrollar, mantener y comprender relaciones (ej. adaptar el comportamiento, compartir juego imaginativo).<br><br>'
                '• <strong>B. Patrones Restringidos y Repetitivos de Comportamiento o Actividades:</strong><br>'
                '&nbsp;&nbsp;1. Movimientos, uso de objetos o habla estereotipada (ej. aleteos, ecolalia, alinear juguetes).<br>'
                '&nbsp;&nbsp;2. Insistencia en la monotonía y excesiva inflexibilidad a rutinas (ej. angustia ante pequeños cambios).<br>'
                '&nbsp;&nbsp;3. Intereses muy restrictivos y fijos con intensidad anormal.<br>'
                '&nbsp;&nbsp;4. Hiper- o hiporreactividad sensorial (ej. indiferencia al dolor, rechazo a ruidos específicos).'
                f'{AVISO_MEDICO}'
            ),
            'botones': [
                {'label': '📋 Hacer evaluación', 'value': '¿Cómo hago una evaluación?'},
                {'label': '👶 Señales de Alerta', 'value': '¿Cómo saber si mi hijo tiene autismo?'},
                {'label': '🛠️ Terapias de Apoyo', 'value': '¿Qué terapias existen para el autismo?'},
            ],
        },

        'diagnostico_tea': {
            'texto': (
                '🔍 <strong>Diagnóstico del Trastorno del Espectro Autista:</strong><br><br>'
                'El diagnóstico del TEA es **100% clínico**, basado en la observación del comportamiento, '
                'el historial de desarrollo y la entrevista con los representantes por parte de un equipo multidisciplinar:<br><br>'
                '• <strong>¿Quién lo realiza?</strong> Neuropediatras, psiquiatras infantiles, psicólogos clínicos '
                'o psicopedagogos especializados.<br>'
                '• <strong>¿A qué edad se detecta?</strong> Aunque las señales pueden ser evidentes a los 12-18 meses, '
                'un diagnóstico confiable suele realizarse a partir de los 2 años.<br>'
                '• <strong>Herramientas estándar:</strong> Escalas de observación como ADOS-2 y entrevistas diagnósticas como ADI-R.<br><br>'
                '💡 *En este sistema puedes aplicar un despistaje inicial basado en los criterios del DSM-5 y perfil pedagógico para diseñar un plan de apoyo.*'
                f'{AVISO_MEDICO}'
            ),
            'botones': [
                {'label': '📋 Criterios DSM-5', 'value': '¿Cuáles son los criterios del DSM-5?'},
                {'label': '👶 Señales de Alerta', 'value': '¿Cómo saber si mi hijo tiene autismo?'},
            ],
        },

        # ── DOMINIO 2: SEÑALES DE ALERTA Y DETECCIÓN TEMPRANA ───────────────
        'alertas_tempranas': {
            'texto': (
                '👶 <strong>Detección Temprana y Señales de Alerta:</strong><br><br>'
                'Las sospechas de desarrollo suelen aparecer entre los 12 y 24 meses. Las señales más frecuentes son:<br><br>'
                '• <strong>Interacción Social:</strong> No responde a su nombre, evita el contacto visual, no señala para pedir '
                'cosas ni muestra interés por compartir juegos.<br>'
                '• <strong>Comunicación:</strong> Retraso o ausencia del lenguaje verbal, ecolalia (repetir palabras como eco), '
                'o no realizar balbuceo comunicativo a los 12 meses.<br>'
                '• <strong>¿Qué es la regresión?</strong> Cuando un infante que ya había adquirido palabras o gestos sociales '
                '(como decir adiós) los pierde repentinamente. Esto requiere **consulta prioritaria** con un especialista.<br><br>'
                '💡 Si observas varias de estas señales, te recomendamos acudir con un psicólogo del desarrollo, neuropediatra o pediatra.'
                f'{AVISO_MEDICO}'
            ),
            'botones': [
                {'label': '🧩 ¿Qué es el TEA?', 'value': '¿Qué es el Trastorno del Espectro Autista?'},
                {'label': '🧸 Desarrollo Infantil', 'value': 'Hitos del desarrollo infantil'},
                {'label': '🧠 Otros Trastornos', 'value': 'Diferencia con otros trastornos de desarrollo'},
            ],
        },

        # ── DOMINIO 3: OTROS TRASTORNOS RELACIONADOS ──────────────────────────
        'otros_trastornos': {
            'texto': (
                '🧠 <strong>Otros Trastornos del Neurodesarrollo y Dificultades:</strong><br><br>'
                'Es fundamental distinguir el TEA de otras condiciones, aunque en ocasiones pueden coexistir (comorbilidad):<br><br>'
                '• <strong>TDAH:</strong> Caracterizado por inatención, hiperactividad e impulsividad que impactan la vida cotidiana.<br>'
                '• <strong>Trastorno del Desarrollo del Lenguaje (TDL):</strong> Afecta la adquisición y uso del lenguaje sin presentar los patrones repetitivos o dificultades de interacción social típicas del autismo.<br>'
                '• <strong>Trastorno de Procesamiento Sensorial:</strong> Dificultad para organizar la información que proviene de los sentidos (hipersensibilidad al ruido, texturas de ropa o comida).<br>'
                '• <strong>Dificultades de Aprendizaje:</strong> Dislexia (lectura), discalculia (matemáticas) y disgrafía (escritura).<br>'
                '• <strong>Discapacidad Intelectual:</strong> Limitaciones significativas en el funcionamiento intelectual y la conducta adaptativa.'
                f'{AVISO_MEDICO}'
            ),
            'botones': [
                {'label': '🧩 ¿Qué es el TEA?', 'value': '¿Qué es el Trastorno del Espectro Autista?'},
                {'label': '🛠️ Terapias', 'value': '¿Qué terapias existen?'},
            ],
        },

        # ── DOMINIO 4: TERAPIAS Y ESTRATEGIAS ──────────────────────────────
        'terapias_tea': {
            'texto': (
                '🛠️ <strong>Terapias con Evidencia Científica:</strong><br><br>'
                'Los enfoques de apoyo más reconocidos por la comunidad clínica internacional son:<br><br>'
                '1️⃣ <strong>ABA (Análisis Conductual Aplicado):</strong> Enfoque estructurado para enseñar habilidades sociales, '
                'comunicativas y de autonomía descomponiendo tareas en pasos simples y reforzando las conductas positivas.<br>'
                '2️⃣ <strong>TEACCH:</strong> Basado en estructurar visualmente el espacio y las actividades del aula para brindar '
                'previsibilidad y reducir la ansiedad.<br>'
                '3️⃣ <strong>Método Denver (ESDM):</strong> Intervención conductual evolutiva temprana dirigida a niños de 12 a 48 meses '
                'enfocada en el juego estructurado y la relación socioafectiva.<br>'
                '4️⃣ <strong>Terapia de Lenguaje / Terapia Ocupacional:</strong> Para la integración sensorial y la mejora del lenguaje verbal y no verbal.'
                f'{AVISO_MEDICO}'
            ),
            'botones': [
                {'label': '🏫 Estrategias en el Aula', 'value': '¿Qué estrategias funcionan en el aula?'},
                {'label': '👶 Señales de Alerta', 'value': '¿Cómo saber si mi hijo tiene autismo?'},
            ],
        },

        # ── DOMINIO 5: ESTRATEGIAS EDUCATIVAS EN AULA Y CRISIS ────────────────
        'estrategias_aula_casa': {
            'texto': (
                '🏫 <strong>Estrategias de Apoyo Pedagógico y Manejo de Crisis:</strong><br><br>'
                '<strong>En el aula y el hogar:</strong><br>'
                '• 📸 <strong>Apoyos Visuales:</strong> Agendas con pictogramas que anticipan la secuencia de la rutina diaria. '
                'Los niños con TEA procesan mejor la información visual.<br>'
                '• 🗣️ <strong>Comunicación Alternativa:</strong> Si el niño no es verbal, usar sistemas como PECS '
                '(Intercambio de imágenes) o comunicadores digitales.<br><br>'
                '<strong>¿Qué hacer ante una crisis o berrinche?</strong><br>'
                '💡 Distingue un berrinche (busca conseguir algo) de una **crisis sensorial/emocional** (sobrecarga del sistema nervioso):<br>'
                '1️⃣ Mantén la calma y mantén seguro al niño frente a golpes.<br>'
                '2️⃣ Reduce el ruido, la luz y las personas alrededor.<br>'
                '3️⃣ No intentes razonar ni regañar en plena crisis; espera a que su sistema se regule.<br>'
                '4️⃣ Usa una "zona de calma" o juguetes sensoriales de presión si el niño los acepta.'
                f'{AVISO_MEDICO}'
            ),
            'botones': [
                {'label': '🛠️ Ver Terapias', 'value': '¿Qué es el método ABA y TEACCH?'},
                {'label': '🧩 ¿Qué es el TEA?', 'value': '¿Qué es el Trastorno del Espectro Autista?'},
            ],
        },

        # ── DOMINIO 6: HITOS DEL DESARROLLO GENERAL ──────────────────────────
        'desarrollo_infantil': {
            'texto': (
                '🧸 <strong>Hitos del Desarrollo Infantil General:</strong><br><br>'
                'El desarrollo tiene rangos, pero hay hitos esperados que sirven de referencia:<br><br>'
                '• <strong>6 meses:</strong> Balbucea, se gira sobre sí mismo, responde a sonidos, sonríe socialmente.<br>'
                '• <strong>12 meses:</strong> Dice palabras simples ("mamá", "papá"), gatea o intenta ponerse en pie, señala con el dedo, responde al "no".<br>'
                '• <strong>18 meses:</strong> Camina sin ayuda, dice al menos 6-10 palabras sueltas, imita acciones de juego simple.<br>'
                '• <strong>24 meses:</strong> Une dos palabras ("quiero agua"), sigue instrucciones de dos pasos, corre y sube peldaños.<br><br>'
                '💡 <strong>¿Cuándo preocuparse?</strong> Si no balbucea a los 12 meses, no hace gestos (señalar, saludar) a los 12 meses, '
                'no camina a los 18 meses o no produce frases de dos palabras a los 24 meses.'
                f'{AVISO_MEDICO}'
            ),
            'botones': [
                {'label': '👶 Señales de Alerta', 'value': '¿Cómo saber si mi hijo tiene autismo?'},
                {'label': '📋 Criterios Diagnósticos', 'value': '¿Cuáles son los criterios del DSM-5?'},
            ],
        },

        # ── DOMINIO 7: APOYO A PADRES, REPRESENTANTES Y DERECHOS ─────────────
        'apoyo_padres': {
            'texto': (
                '👨‍👩‍👧 <strong>Apoyo a Padres, Representantes y Derechos:</strong><br><br>'
                'La crianza de un niño con TEA requiere una red de soporte integral:<br><br>'
                '• <strong>¿Cómo apoyar en casa?</strong> Establece rutinas estructuradas, anticipa siempre los planes '
                'utilizando imágenes y celebra cada pequeño logro de autonomía diaria.<br>'
                '• 🏫 <strong>PIEE (Plan Individualizado de Educación Especial):</strong> Es el documento donde la escuela adapta curricularmente '
                'las materias para el estudiante con necesidades educativas especiales. Es tu derecho solicitarlo.<br>'
                '• 🧘 <strong>Sobrecarga del cuidador:</strong> Cuidar a quien cuida es vital. El estrés sostenido produce desgaste '
                'emocional. Busca grupos de apoyo de padres, delega tareas y tómate pequeños descansos.<br>'
                '• 🔍 <strong>¿Dónde encontrar especialistas?</strong> Puedes acudir a las Unidades de Educación Especial, '
                'centros de salud infantil del municipio Caroní o redes de fundaciones de apoyo al autismo.'
                f'{AVISO_MEDICO}'
            ),
            'botones': [
                {'label': '🏫 Estrategias Escolares', 'value': '¿Qué estrategias funcionan en el aula?'},
                {'label': '🧩 ¿Qué es el TEA?', 'value': '¿Qué es el Trastorno del Espectro Autista?'},
            ],
        },

        # ── DOMINIO 8: MITOS Y REALIDADES ────────────────────────────────────
        'mitos_realidades': {
            'texto': (
                '🧐 <strong>Mitos y Realidades del Autismo:</strong><br><br>'
                '🚫 <strong>Mito:</strong> Las vacunas causan autismo.<br>'
                '✅ <strong>Realidad:</strong> **FALSO.** El estudio original de Andrew Wakefield fue completamente desmentido, '
                'perdiendo su licencia. Numerosos estudios globales demuestran que **no existe vínculo alguno** entre vacunas y autismo.<br><br>'
                '🚫 <strong>Mito:</strong> Todas las personas con TEA tienen habilidades de genio (Síndrome de Savant).<br>'
                '✅ <strong>Realidad:</strong> Solo un pequeño porcentaje posee habilidades extraordinarias en áreas como música, cálculo o memoria. '
                'La mayoría tiene un perfil cognitivo variado.<br><br>'
                '🚫 <strong>Mito:</strong> El autismo es una enfermedad mental o es contagioso.<br>'
                '✅ <strong>Realidad:</strong> El autismo **no es una enfermedad mental ni se contagia**. Es una condición neurológica '
                'y una forma diferente de procesar la información del entorno.'
                f'{AVISO_MEDICO}'
            ),
            'botones': [
                {'label': '🧩 ¿Qué es el TEA?', 'value': '¿Qué es el Trastorno del Espectro Autista?'},
                {'label': '👶 Señales de Alerta', 'value': '¿Cómo saber si mi hijo tiene autismo?'},
            ],
        },

        # ── FALLBACK Y SUGERENCIAS ──────────────────────────────────────────
        'fallback': {
            'texto': (
                '🧩 <strong>Asistente Especializado en TEA:</strong><br><br>'
                'Disculpa, pero como orientador de esta plataforma, <strong>solo puedo responder preguntas '
                'relacionadas con el Trastorno del Espectro Autista (TEA)</strong>, señales de alerta en el desarrollo '
                'infantil, pautas de intervención pedagógica y el uso de este sistema.<br><br>'
                'Por favor, reformula tu consulta con palabras clave como <em>"autismo"</em>, <em>"aleteo"</em>, '
                '<em>"agenda visual"</em>, <em>"ABA"</em> o selecciona una opción rápida:'
            ),
            'botones': [
                {'label': '🧩 ¿Qué es el TEA?', 'value': '¿Qué es el Trastorno del Espectro Autista?'},
                {'label': '👶 Señales de Alerta', 'value': '¿Cómo saber si mi hijo tiene autismo?'},
                {'label': '🏫 Apoyo en Aula', 'value': '¿Qué estrategias funcionan en el aula?'},
                {'label': '📋 Guía del Sistema', 'value': 'Necesito ayuda para usar el sistema'},
            ],
        },
    }

    # ── Mapeo dinámico de dudas sobre comportamientos específicos en la BD ────
    if intencion == 'comportamiento_duda':
        mensaje = contexto.get('mensaje', '')
        reglas_coincidentes = buscar_reglas_por_palabras(mensaje)

        if reglas_coincidentes:
            texto_reglas = ""
            for r in reglas_coincidentes:
                texto_reglas += (
                    f"🧠 <strong>{r.nombre}:</strong><br>"
                    f"💡 <em>Recomendación pedagógica:</em> {r.recomendacion}<br>"
                    f"🛠️ <em>Recursos didácticos sugeridos:</em> {r.recursos_didacticos or 'No especificados'}<br><br>"
                )
            texto_res = (
                f"🔍 He consultado la <strong>Base de Conocimientos del Sistema Experto</strong> "
                f"y encontré pautas recomendadas para tu consulta:<br><br>{texto_reglas}"
                f"¿Deseas registrar a tu estudiante o realizar su evaluación diagnóstica para un plan detallado?"
            )
        else:
            texto_res = (
                "🧩 <strong>Dudas sobre comportamientos en autismo:</strong><br><br>"
                "Los niños dentro del espectro pueden presentar comportamientos como aleteos, resistencia severa al cambio, "
                "fijación por ciertos objetos, rabietas por sobrecarga sensorial o ecolalias.<br><br>"
                "• Si crees que un niño muestra conductas de este tipo, te sugerimos registrarlo en la sección "
                "<strong>Mis Estudiantes</strong> y aplicarle la <strong>Evaluación DSM-5</strong> y pedagógica. El sistema "
                "diseñará un perfil único con apoyos visuales y didácticos personalizados."
                f'{AVISO_MEDICO}'
            )

        respuestas['comportamiento_duda'] = {
            'texto': texto_res,
            'botones': [
                {'label': '📋 Hacer evaluación', 'value': '¿Cómo hago una evaluación?'},
                {'label': '🧩 ¿Qué es el TEA?', 'value': '¿Qué es el Trastorno del Espectro Autista?'},
                {'label': '➕ Registrar estudiante', 'value': '¿Cómo registro un estudiante?'},
            ]
        }

    respuesta = respuestas.get(intencion, respuestas['fallback'])
    respuesta['intencion'] = intencion

    # ── INTEGRACIÓN CON GEMINI IA ──────────────────────────────────────────
    # Si la intención es de dominio general o clínica (no operativa) o es un fallback
    intenciones_operativas = [
        'saludo', 'despedida', 'horarios', 'contacto', 'ubicacion', 
        'funcionalidades', 'ayuda', 'problemas_tecnicos', 
        'registro_estudiante', 'registro_usuario', 'evaluacion', 
        'resultados', 'perfil'
    ]
                              
    if GEMINI_AVAILABLE and intencion not in intenciones_operativas:
        mensaje_original = contexto.get('mensaje', '')
        if mensaje_original:
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = (
                    f"Eres TEAbot, un asistente experto en Trastorno del Espectro Autista (TEA) y desarrollo infantil. "
                    f"El usuario te pregunta: '{mensaje_original}'. "
                    f"Responde de forma empática, clara, exacta y directa a la pregunta en menos de 120 palabras. "
                    f"Usa formato HTML básico para negritas (<strong>) o listas si es necesario. "
                    f"No uses markdown clásico como ** o *."
                )
                response = model.generate_content(prompt)
                if response and response.text:
                    texto_ia = response.text.replace('\n', '<br>')
                    texto_ia += f'{AVISO_MEDICO}'
                    # Reemplazamos el texto predefinido por el de la IA, pero mantenemos los botones
                    respuesta['texto'] = texto_ia
            except Exception as e:
                pass # Si falla la IA por conexión o algo, cae silenciosamente al texto predefinido.

    return respuesta


# ─────────────────────────────────────────────────────────────────────────────
# MENSAJE DE BIENVENIDA
# ─────────────────────────────────────────────────────────────────────────────

def mensaje_bienvenida(nombre: str = '') -> dict:
    """Genera el mensaje inicial del bot al abrir el chat."""
    saludo = f'¡Hola, <strong>{nombre}</strong>! 👋' if nombre else '¡Hola! 👋'
    return {
        'texto': (
            f'{saludo} Soy <strong>TEAbot</strong> 🧩, tu asistente informativo '
            f'en autismo, desarrollo infantil y uso del sistema.<br><br>'
            f'Puedo orientarte sobre los hitos de crecimiento de los niños, '
            f'estrategias educativas en el aula, terapias validadas científicamente, y '
            f'guiarte en el registro y evaluaciones pedagógicas del sistema.<br><br>'
            f'¿De qué te gustaría hablar hoy?'
        ),
        'botones': [
            {'label': '🧩 ¿Qué es el TEA?', 'value': '¿Qué es el Trastorno del Espectro Autista?'},
            {'label': '👶 Señales de Alerta', 'value': '¿Cómo saber si mi hijo tiene autismo?'},
            {'label': '🛠️ Terapias de Apoyo', 'value': '¿Qué terapias existen para el autismo?'},
            {'label': '⚙️ Usar el Sistema', 'value': '¿Qué puedo hacer en el sistema?'},
        ],
        'intencion': 'bienvenida',
    }
