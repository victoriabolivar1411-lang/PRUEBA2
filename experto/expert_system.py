"""
=============================================================================
SISTEMA EXPERTO PARA APOYO PEDAGÓGICO EN TEA
=============================================================================
Módulo: expert_system.py
Descripción: Motor de inferencia basado en encadenamiento hacia adelante
             (Forward Chaining). Evalúa los hechos de una evaluación
             pedagógica contra la base de conocimientos (reglas SI-ENTONCES)
             y genera recomendaciones automáticas.

Arquitectura del Motor de Inferencia:
  1. Hechos (Working Memory): datos de la evaluación del estudiante.
  2. Base de Conocimientos: reglas almacenadas en la BD (modelo Regla).
  3. Motor de Inferencia: ciclo de match-select-execute (forward chaining).
  4. Salida: lista de Recomendaciones pedagógicas disparadas.
=============================================================================
"""

import logging

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# REGLAS PRECARGADAS (DATOS INICIALES)
# ─────────────────────────────────────────────────────────────────────────────

REGLAS_INICIALES = [
    # ── COMUNICACIÓN ─────────────────────────────────────────────────────────
    {
        'nombre': 'Comunicación alta dificultad → Pictogramas',
        'campo_condicion': 'dificultad_comunicacion',
        'operador': '==',
        'valor_condicion': 'alto',
        'accion': (
            'Implementar un Sistema Aumentativo y Alternativo de Comunicación (SAAC) '
            'basado en pictogramas (PECS). Utilizar imágenes concretas para rutinas '
            'diarias, necesidades básicas y emociones. Colocar tableros de comunicación '
            'accesibles en el aula.'
        ),
        'categoria': 'comunicacion',
        'prioridad': 10,
    },
    {
        'nombre': 'Sin lenguaje verbal → CAA digital',
        'campo_condicion': 'usa_lenguaje_verbal',
        'operador': '==',
        'valor_condicion': 'False',
        'accion': (
            'Introducir aplicaciones de Comunicación Aumentativa y Alternativa (CAA) '
            'como Proloquo2Go, LetMeTalk o ARAWORD. Trabajar con el logopeda para '
            'diseñar un vocabulario personalizado. Capacitar al instructor y la familia '
            'en el uso consistente del sistema CAA.'
        ),
        'categoria': 'comunicacion',
        'prioridad': 9,
    },
    {
        'nombre': 'Comunicación media dificultad → Apoyos visuales',
        'campo_condicion': 'dificultad_comunicacion',
        'operador': '==',
        'valor_condicion': 'medio',
        'accion': (
            'Reforzar la comunicación con apoyos visuales complementarios: '
            'agendas visuales diarias, tarjetas de primero-después, señales '
            'gestuales simples. Practicar turnos conversacionales con apoyo del instructor.'
        ),
        'categoria': 'comunicacion',
        'prioridad': 6,
    },
    # ── CONDUCTA ──────────────────────────────────────────────────────────────
    {
        'nombre': 'Conductas repetitivas altas → Rutinas estructuradas',
        'campo_condicion': 'conductas_repetitivas',
        'operador': '==',
        'valor_condicion': 'alto',
        'accion': (
            'Diseñar un ambiente altamente estructurado con rutinas predecibles y '
            'horarios visuales claros. Incorporar las conductas repetitivas como '
            '"tiempo de stim" controlado dentro del día. Usar temporizadores visuales '
            'para las transiciones entre actividades. Aplicar el enfoque de Análisis '
            'Conductual Aplicado (ABA) para reemplazar conductas disruptivas por '
            'funcionales equivalentes.'
        ),
        'categoria': 'conducta',
        'prioridad': 10,
    },
    {
        'nombre': 'Crisis frecuentes → Plan de manejo de crisis',
        'campo_condicion': 'crisis_frecuentes',
        'operador': '==',
        'valor_condicion': 'True',
        'accion': (
            'Elaborar un Plan Individualizado de Manejo de Crisis con: (1) identificación '
            'de disparadores (triggers), (2) señales tempranas de escalada, (3) estrategias '
            'de desescalada (rincón de calma, herramientas sensoriales), (4) protocolo de '
            'actuación del equipo. Compartir el plan con toda la familia y el equipo docente.'
        ),
        'categoria': 'conducta',
        'prioridad': 10,
    },
    {
        'nombre': 'Reacciones sensoriales altas → Adaptación del entorno',
        'campo_condicion': 'reacciones_sensoriales',
        'operador': '==',
        'valor_condicion': 'alto',
        'accion': (
            'Realizar una evaluación sensorial completa con terapeuta ocupacional. '
            'Adaptar el aula: reducir estímulos visuales y sonoros, ofrecer auriculares '
            'de reducción de ruido, ajustar iluminación. Crear una "zona de calma" con '
            'materiales sensoriales (pelotas anti-estrés, mantas con peso, etc.).'
        ),
        'categoria': 'conducta',
        'prioridad': 9,
    },
    {
        'nombre': 'Reacciones sensoriales medias → Dieta sensorial',
        'campo_condicion': 'reacciones_sensoriales',
        'operador': '==',
        'valor_condicion': 'medio',
        'accion': (
            'Implementar una dieta sensorial personalizada: pausas de movimiento cada '
            '20-30 minutos, actividades propioceptivas (saltar, cargar peso), y objetos '
            'de autorregulación disponibles en el aula (fidgets, cojines de equilibrio).'
        ),
        'categoria': 'conducta',
        'prioridad': 6,
    },
    {
        'nombre': 'Conductas repetitivas medias → Horario visual',
        'campo_condicion': 'conductas_repetitivas',
        'operador': '==',
        'valor_condicion': 'medio',
        'accion': (
            'Implementar horario visual diario con imágenes o fotografías de las actividades. '
            'Anticipar los cambios de rutina con al menos 5 minutos de aviso. '
            'Ofrecer "tiempo libre estructurado" donde el estudiante pueda elegir entre '
            'opciones predeterminadas.'
        ),
        'categoria': 'conducta',
        'prioridad': 5,
    },
    # ── INTERACCIÓN SOCIAL ────────────────────────────────────────────────────
    {
        'nombre': 'Interacción social baja → Dinámicas grupales guiadas',
        'campo_condicion': 'interaccion_social',
        'operador': '==',
        'valor_condicion': 'bajo',
        'accion': (
            'Implementar Entrenamiento en Habilidades Sociales (EHS) con grupos pequeños '
            '(máx. 3 estudiantes). Usar juegos de roles, modelado por video y cuentos '
            'sociales (Social Stories™ de Carol Gray) para enseñar situaciones cotidianas. '
            'Iniciar con actividades paralelas antes de pasar a actividades cooperativas.'
        ),
        'categoria': 'social',
        'prioridad': 10,
    },
    {
        'nombre': 'Sin interés por pares → Actividades motivadoras compartidas',
        'campo_condicion': 'interes_pares',
        'operador': '==',
        'valor_condicion': 'False',
        'accion': (
            'Identificar los intereses específicos del estudiante e incorporarlos '
            'en actividades compartidas con un compañero ("buddy system"). Comenzar '
            'con actividades de 5-10 minutos con un solo compañero seleccionado. '
            'Reforzar positivamente cualquier iniciativa de interacción espontánea.'
        ),
        'categoria': 'social',
        'prioridad': 8,
    },
    {
        'nombre': 'Interacción social media → Habilidades de juego',
        'campo_condicion': 'interaccion_social',
        'operador': '==',
        'valor_condicion': 'medio',
        'accion': (
            'Trabajar habilidades de juego cooperativo y turnos. Enseñar explícitamente '
            'las reglas sociales implícitas mediante historietas en cómic. '
            'Organizar juegos de mesa estructurados en grupos de 2-4 estudiantes '
            'con apoyo del instructor.'
        ),
        'categoria': 'social',
        'prioridad': 5,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# CLASE PRINCIPAL: MOTOR DE INFERENCIA
# ─────────────────────────────────────────────────────────────────────────────

class MotorInferencia:
    """
    Motor de inferencia por encadenamiento hacia adelante (Forward Chaining).

    Algoritmo:
    ----------
    1. Extraer hechos (facts) de la evaluación del estudiante.
    2. Obtener todas las reglas activas de la base de conocimientos.
    3. Para cada regla, verificar si la condición se satisface con los hechos.
    4. Si se cumple, "disparar" la regla y agregar la recomendación a la agenda.
    5. Repetir hasta que no queden reglas por evaluar (ciclo único en esta implementación).
    6. Retornar las recomendaciones generadas.
    """

    def __init__(self, evaluacion):
        """
        Inicializa el motor con la evaluación del estudiante.

        Args:
            evaluacion: instancia del modelo Evaluacion de Django.
        """
        self.evaluacion = evaluacion
        self.hechos = self._extraer_hechos()
        self.agenda = []          # Reglas que se disparan (match)
        self.recomendaciones = [] # Salida del motor

    # ── 1. EXTRACCIÓN DE HECHOS ───────────────────────────────────────────────

    def _extraer_hechos(self) -> dict:
        """
        Construye la memoria de trabajo (Working Memory) a partir de los
        campos de la evaluación. Los booleans se convierten a string para
        facilitar la comparación uniforme con los valores de las reglas.

        Returns:
            dict: {campo: valor_como_string}
        """
        ev = self.evaluacion
        hechos = {
            'dificultad_comunicacion': ev.dificultad_comunicacion,
            'usa_lenguaje_verbal':      str(ev.usa_lenguaje_verbal),
            'conductas_repetitivas':    ev.conductas_repetitivas,
            'reacciones_sensoriales':   ev.reacciones_sensoriales,
            'crisis_frecuentes':        str(ev.crisis_frecuentes),
            'interaccion_social':       ev.interaccion_social,
            'interes_pares':            str(ev.interes_pares),
        }
        logger.debug('Hechos extraídos: %s', hechos)
        return hechos

    # ── 2. EVALUACIÓN DE CONDICIONES ─────────────────────────────────────────

    def _evaluar_condicion(self, regla) -> bool:
        """
        Evalúa si la condición de una regla se cumple con los hechos actuales.

        Soporta los operadores: == != > <
        La comparación se hace como string; si ambos lados son numéricos,
        también realiza comparación numérica.

        Args:
            regla: instancia del modelo Regla.

        Returns:
            bool: True si la condición se satisface.
        """
        campo    = regla.campo_condicion
        operador = regla.operador
        valor_r  = regla.valor_condicion  # valor de la regla

        # El hecho puede no existir si la evaluación no tiene ese campo
        valor_h = self.hechos.get(campo)
        if valor_h is None:
            return False

        # Comparación como strings (case-insensitive para robustez)
        vh_str = str(valor_h).lower()
        vr_str = str(valor_r).lower()

        try:
            # Intenta comparación numérica
            vh_num = float(vh_str)
            vr_num = float(vr_str)
            if operador == '==':
                return vh_num == vr_num
            elif operador == '!=':
                return vh_num != vr_num
            elif operador == '>':
                return vh_num > vr_num
            elif operador == '<':
                return vh_num < vr_num
        except ValueError:
            # Comparación como strings
            if operador == '==':
                return vh_str == vr_str
            elif operador == '!=':
                return vh_str != vr_str

        return False

    # ── 3. CICLO DE INFERENCIA (FORWARD CHAINING) ────────────────────────────

    def ejecutar(self) -> list:
        """
        Ejecuta el ciclo principal de encadenamiento hacia adelante:
          MATCH → SELECT → EXECUTE

        Returns:
            list[dict]: Lista de recomendaciones generadas, cada una con
                        {regla, texto, categoria}.
        """
        from .models import Regla  # Importación local para evitar ciclos

        reglas_activas = Regla.objects.filter(activa=True).order_by('-prioridad')
        logger.info('Motor de inferencia iniciado. Reglas activas: %d', reglas_activas.count())

        # ── FASE MATCH: buscar qué reglas se disparan ────────────────────────
        for regla in reglas_activas:
            if self._evaluar_condicion(regla):
                self.agenda.append(regla)
                logger.debug('Regla disparada: %s', regla.nombre)

        logger.info('Reglas disparadas: %d', len(self.agenda))

        # ── FASE EXECUTE: generar recomendaciones ────────────────────────────
        for regla in self.agenda:
            self.recomendaciones.append({
                'regla':     regla,
                'texto':     regla.accion,
                'categoria': regla.categoria,
            })

        return self.recomendaciones

    # ── 4. PERSISTENCIA ──────────────────────────────────────────────────────

    def guardar_recomendaciones(self) -> int:
        """
        Persiste las recomendaciones generadas en la base de datos,
        eliminando primero las recomendaciones previas de esta evaluación
        para evitar duplicados.

        Returns:
            int: Número de recomendaciones guardadas.
        """
        from .models import Recomendacion  # Importación local

        # Eliminar recomendaciones previas de esta evaluación
        Recomendacion.objects.filter(evaluacion=self.evaluacion).delete()

        guardadas = 0
        for rec in self.recomendaciones:
            Recomendacion.objects.create(
                evaluacion=self.evaluacion,
                regla=rec['regla'],
                texto=rec['texto'],
                categoria=rec['categoria'],
            )
            guardadas += 1

        logger.info('Recomendaciones guardadas: %d', guardadas)
        return guardadas


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN PÚBLICA: PUNTO DE ENTRADA DEL MOTOR
# ─────────────────────────────────────────────────────────────────────────────

def generar_recomendaciones(evaluacion) -> list:
    """
    Función de conveniencia que ejecuta el motor de inferencia completo
    para una evaluación dada y guarda los resultados en la BD.

    Args:
        evaluacion: instancia del modelo Evaluacion.

    Returns:
        list[dict]: Recomendaciones generadas.
    """
    motor = MotorInferencia(evaluacion)
    recomendaciones = motor.ejecutar()
    motor.guardar_recomendaciones()
    return recomendaciones
