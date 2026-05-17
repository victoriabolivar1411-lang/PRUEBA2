"""
=============================================================================
SISTEMA EXPERTO PARA APOYO PEDAGÓGICO EN TEA
=============================================================================
Módulo: expert_system.py
Motor de inferencia por encadenamiento hacia adelante (Forward Chaining).
=============================================================================
"""

import logging
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# REGLAS INICIALES PRECARGADAS (10 reglas DSM-5)
# ─────────────────────────────────────────────────────────────────────────────

REGLAS_INICIALES = [
    {
        'nombre': 'R01 — Comunicación constante → SAAC + Pictogramas',
        'condicion': 'nivel_comunicacion_social == "apoyo_constante"',
        'recomendacion': (
            'Implementar un Sistema Aumentativo y Alternativo de Comunicación (SAAC) '
            'basado en pictogramas (PECS). Utilizar tableros de comunicación con imágenes '
            'concretas para rutinas diarias, necesidades básicas y emociones. Colocar '
            'tableros accesibles en todos los espacios del aula. Solicitar evaluación '
            'por fonoaudiólogo/logopeda.'
        ),
        'recursos_didacticos': (
            'Tableros PECS impresos laminados · Aplicación LetMeTalk (Android, gratuita) '
            '· App Proloquo2Go · Pictogramas ARASAAC (arasaac.org)'
        ),
    },
    {
        'nombre': 'R02 — Conductas muy notables → Rutinas visuales + avisos de transición',
        'condicion': 'nivel_conductas_repetitivas == "ayuda_muy_notable"',
        'recomendacion': (
            'Diseñar ambiente estructurado con rutinas predecibles y horarios visuales fijos. '
            'Usar temporizadores visuales (Time Timer) para transiciones con avisos a los 10, 5 '
            'y 2 minutos. Incorporar "tiempo de stim" controlado. Aplicar ABA para reemplazar '
            'conductas disruptivas por funcionales equivalentes. Crear estaciones de trabajo '
            'claras con materiales diferenciados por color.'
        ),
        'recursos_didacticos': (
            'Temporizador visual Time Timer · Tablero de horario con velcro · '
            'Tarjetas "AHORA → DESPUÉS" · Kit de herramientas sensoriales'
        ),
    },
    {
        'nombre': 'R03 — Criterio B cumplido (≥2 conductas) → Estaciones de trabajo TEACCH',
        'condicion': 'cumple_criterio_b == True',
        'recomendacion': (
            'Organizar el aula en estaciones de trabajo claramente delimitadas con materiales '
            'específicos. Usar modelo TEACCH con cajas de tareas secuenciadas. Implementar '
            'actividades estructuradas con inicio, desarrollo y cierre explícitos. '
            'Proporcionar instrucciones paso a paso con soporte visual.'
        ),
        'recursos_didacticos': (
            'Cajas de trabajo TEACCH · Separadores visuales · '
            'Etiquetas de colores para cada estación · Guías TEACCH de Schopler'
        ),
    },
    {
        'nombre': 'R04 — Discapacidad intelectual → Materiales pre-simbólicos',
        'condicion': 'discapacidad_intelectual == True',
        'recomendacion': (
            'Adaptar materiales al nivel pre-simbólico usando objetos concretos y reales '
            'antes que imágenes o palabras. Implementar aprendizaje sin error (errorless '
            'learning) con ayudas físicas graduales. Trabajar tareas de causa-efecto simple. '
            'Reducir el número de pasos a 1-2 acciones máximo. Coordinar con equipo '
            'interdisciplinario.'
        ),
        'recursos_didacticos': (
            'Objetos reales y miniaturas · Juguetes de causa-efecto · '
            'Materiales sensoriales (texturas, masas) · Guía PBS'
        ),
    },
    {
        'nombre': 'R05 — Deterioro del lenguaje → PECS prioritario',
        'condicion': 'deterioro_lenguaje == True',
        'recomendacion': (
            'Priorizar PECS (Sistema de Comunicación por Intercambio de Imágenes) como '
            'principal medio de comunicación. Iniciar con Fase I e ir avanzando. Usar '
            'vocabulario de alta frecuencia: comer, agua, baño, jugar, ayuda. No forzar '
            'producción verbal. Integrar pictogramas en todos los momentos del día.'
        ),
        'recursos_didacticos': (
            'Kit PECS oficial · Pictogramas ARASAAC · Álbum de comunicación con velcro · '
            'App "Snap Core First"'
        ),
    },
    {
        'nombre': 'R06 — Inicio temprano + deterioro significativo → Derivación interdisciplinaria',
        'condicion': 'inicio_temprano == True AND deterioro_significativo == True',
        'recomendacion': (
            'Derivar a evaluación interdisciplinaria completa: neurología pediátrica, '
            'psicología clínica, fonoaudiología y terapia ocupacional. Solicitar informe '
            'escolar detallado con evidencias observacionales. Comunicar a la familia la '
            'importancia de la intervención temprana. Documentar observaciones con fechas '
            'y descripciones específicas.'
        ),
        'recursos_didacticos': (
            'Protocolo de derivación interdisciplinaria · Formulario de consentimiento '
            '· Escala CARS-2 · Directorio de especialistas en TEA'
        ),
    },
    {
        'nombre': 'R07 — Comunicación sustancial → Lenguaje visual + rutinas sociales',
        'condicion': 'nivel_comunicacion_social == "apoyo_sustancial"',
        'recomendacion': (
            'Implementar apoyos visuales complementarios: agendas visuales, tarjetas '
            '"primero-después", señales gestuales acordadas. Usar Historias Sociales™ '
            '(Carol Gray) para situaciones cotidianas. Establecer grupos pequeños (2-3 '
            'estudiantes) para práctica de habilidades sociales. Reforzar positivamente '
            'cada intento comunicativo.'
        ),
        'recursos_didacticos': (
            'Tarjetas "primero-después" laminadas · Libro "Historias Sociales" de Carol Gray '
            '· App "Social Story Creator" · Pictogramas de emociones'
        ),
    },
    {
        'nombre': 'R08 — Alteraciones sensoriales → Ambiente sensorialmente amigable',
        'condicion': 'alteraciones_sensoriales == True',
        'recomendacion': (
            'Realizar evaluación sensorial con terapeuta ocupacional. Adaptar el aula: '
            'reducir estímulos visuales, controlar ruido, usar iluminación regulable. '
            'Crear "zona de calma" con herramientas sensoriales. Implementar dieta sensorial '
            'personalizada con pausas de movimiento cada 20-30 min y actividades propioceptivas. '
            'Anticipar situaciones sensorialmente desafiantes.'
        ),
        'recursos_didacticos': (
            'Auriculares de reducción de ruido · Pelotas de presión y fidgets · '
            'Mantas con peso · Cojines de equilibrio · Lámparas LED regulables'
        ),
    },
    {
        'nombre': 'R09 — Comunicación nivel 1 → Habilidades conversacionales',
        'condicion': 'nivel_comunicacion_social == "necesita_apoyo"',
        'recomendacion': (
            'Reforzar habilidades conversacionales con práctica de turnos. Usar juegos '
            'de mesa estructurados para practicar inicio y mantenimiento de conversación. '
            'Enseñar reglas sociales implícitas mediante role-playing y modelado en video. '
            'Trabajar comprensión de metáforas y lenguaje figurado.'
        ),
        'recursos_didacticos': (
            'Juegos de mesa: Dixit, Dobble, Conecta 4 · Tarjetas de habilidades sociales '
            '· App "Social Express"'
        ),
    },
    {
        'nombre': 'R10 — Conductas notables (nivel 2) → Horario visual + anticipación',
        'condicion': 'nivel_conductas_repetitivas == "ayuda_notable"',
        'recomendacion': (
            'Implementar horario visual diario con fotografías o pictogramas. Anticipar '
            'cambios con 5 minutos de aviso verbal y visual. Ofrecer "tiempo libre '
            'estructurado" con opciones predeterminadas. Reforzar flexibilidad gradualmente '
            'con cambios planeados pequeños.'
        ),
        'recursos_didacticos': (
            'Tablero de horario semanal con velcro · Temporizador Time Timer · '
            'Tarjetas "cambio sorpresa" · Ruleta de actividades libres'
        ),
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# MOTOR DE INFERENCIA
# ─────────────────────────────────────────────────────────────────────────────

class MotorInferencia:
    """Motor forward chaining para el sistema experto TEA."""

    # Evaluadores de condición segura (sin eval)
    EVALUADORES = {
        'nivel_comunicacion_social == "apoyo_constante"':
            lambda h: h.get('nivel_comunicacion_social') == 'apoyo_constante',
        'nivel_comunicacion_social == "apoyo_sustancial"':
            lambda h: h.get('nivel_comunicacion_social') == 'apoyo_sustancial',
        'nivel_comunicacion_social == "necesita_apoyo"':
            lambda h: h.get('nivel_comunicacion_social') == 'necesita_apoyo',
        'nivel_conductas_repetitivas == "ayuda_muy_notable"':
            lambda h: h.get('nivel_conductas_repetitivas') == 'ayuda_muy_notable',
        'nivel_conductas_repetitivas == "ayuda_notable"':
            lambda h: h.get('nivel_conductas_repetitivas') == 'ayuda_notable',
        'nivel_conductas_repetitivas == "necesita_ayuda"':
            lambda h: h.get('nivel_conductas_repetitivas') == 'necesita_ayuda',
        'cumple_criterio_b == True':
            lambda h: h.get('cumple_criterio_b') is True,
        'discapacidad_intelectual == True':
            lambda h: h.get('discapacidad_intelectual') is True,
        'deterioro_lenguaje == True':
            lambda h: h.get('deterioro_lenguaje') is True,
        'alteraciones_sensoriales == True':
            lambda h: h.get('alteraciones_sensoriales') is True,
        'inicio_temprano == True AND deterioro_significativo == True':
            lambda h: h.get('inicio_temprano') is True and h.get('deterioro_significativo') is True,
    }

    def __init__(self, evaluacion_pedagogica):
        self.eval_ped  = evaluacion_pedagogica
        self.eval_dsm5 = evaluacion_pedagogica.evaluacion_dsm5
        self.hechos    = self._extraer_hechos()
        self.agenda    = []

    def _extraer_hechos(self) -> dict:
        hechos = {
            'nivel_comunicacion_social':   self.eval_ped.nivel_comunicacion_social,
            'nivel_conductas_repetitivas': self.eval_ped.nivel_conductas_repetitivas,
        }
        if self.eval_dsm5:
            hechos.update({
                'cumple_criterio_b':        self.eval_dsm5.cumple_criterio_b(),
                'discapacidad_intelectual': self.eval_dsm5.discapacidad_intelectual,
                'deterioro_lenguaje':       self.eval_dsm5.deterioro_lenguaje,
                'alteraciones_sensoriales': self.eval_dsm5.alteraciones_sensoriales,
                'inicio_temprano':          self.eval_dsm5.inicio_temprano,
                'deterioro_significativo':  self.eval_dsm5.deterioro_significativo,
            })
        else:
            hechos.update({k: False for k in [
                'cumple_criterio_b', 'discapacidad_intelectual', 'deterioro_lenguaje',
                'alteraciones_sensoriales', 'inicio_temprano', 'deterioro_significativo',
            ]})
        logger.debug('Working Memory: %s', hechos)
        return hechos

    def _evaluar_condicion(self, condicion_texto: str) -> bool:
        evaluador = self.EVALUADORES.get(condicion_texto.strip())
        if evaluador:
            return evaluador(self.hechos)
        return False

    def ejecutar(self) -> list:
        from .models import Regla
        reglas_activas = Regla.objects.filter(activa=True)
        logger.info('Motor iniciado — Reglas activas: %d', reglas_activas.count())
        for regla in reglas_activas:
            if self._evaluar_condicion(regla.condicion):
                self.agenda.append(regla)
                logger.debug('Regla disparada: %s', regla.nombre)
        logger.info('Reglas disparadas: %d', len(self.agenda))
        return self.agenda

    def guardar_recomendaciones(self) -> int:
        from .models import Recomendacion
        Recomendacion.objects.filter(evaluacion_pedagogica=self.eval_ped).delete()
        for regla in self.agenda:
            Recomendacion.objects.create(
                evaluacion_pedagogica=self.eval_ped,
                regla=regla,
                texto=regla.recomendacion,
            )
        logger.info('Recomendaciones guardadas: %d', len(self.agenda))
        return len(self.agenda)


def generar_recomendaciones(evaluacion_pedagogica) -> list:
    """Punto de entrada público del motor de inferencia."""
    motor = MotorInferencia(evaluacion_pedagogica)
    reglas = motor.ejecutar()
    motor.guardar_recomendaciones()
    return reglas
