"""
=============================================================================
SISTEMA EXPERTO PARA APOYO PEDAGÓGICO EN TEA
=============================================================================
Módulo: models.py
Descripción: Define la estructura de la base de datos del sistema.
             Incluye los modelos Instructor, Estudiante, Evaluacion,
             Regla y Recomendacion con sus relaciones y campos.
=============================================================================
"""

from django.db import models
from django.contrib.auth.models import User


# ─────────────────────────────────────────────
# NIVELES UTILIZADOS EN LAS EVALUACIONES
# ─────────────────────────────────────────────
NIVEL_CHOICES = [
    ('bajo', 'Bajo'),
    ('medio', 'Medio'),
    ('alto', 'Alto'),
]


class Instructor(models.Model):
    """
    Representa a un instructor o terapeuta que trabaja
    con estudiantes con TEA en el centro educativo.
    """
    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='instructor',
        verbose_name='Usuario del sistema',
    )
    telefono = models.CharField(max_length=20, blank=True, verbose_name='Teléfono')
    especialidad = models.CharField(max_length=100, blank=True, verbose_name='Especialidad')
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de registro')

    class Meta:
        verbose_name = 'Instructor'
        verbose_name_plural = 'Instructores'

    def __str__(self):
        return f'{self.usuario.get_full_name()} ({self.usuario.username})'


class Estudiante(models.Model):
    """
    Representa a un niño o niña con TEA que es evaluado
    y apoyado por un instructor en el sistema.
    """
    instructor = models.ForeignKey(
        Instructor,
        on_delete=models.CASCADE,
        related_name='estudiantes',
        verbose_name='Instructor responsable',
    )
    nombre = models.CharField(max_length=100, verbose_name='Nombre')
    apellido = models.CharField(max_length=100, verbose_name='Apellido')
    fecha_nacimiento = models.DateField(verbose_name='Fecha de nacimiento')
    nivel_tea = models.CharField(
        max_length=20,
        choices=[('1', 'Nivel 1 - Necesita apoyo'), ('2', 'Nivel 2 - Necesita apoyo sustancial'), ('3', 'Nivel 3 - Necesita apoyo muy sustancial')],
        verbose_name='Nivel TEA',
    )
    observaciones = models.TextField(blank=True, verbose_name='Observaciones generales')
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de registro')

    class Meta:
        verbose_name = 'Estudiante'
        verbose_name_plural = 'Estudiantes'
        ordering = ['apellido', 'nombre']

    def __str__(self):
        return f'{self.nombre} {self.apellido}'

    @property
    def nombre_completo(self):
        return f'{self.nombre} {self.apellido}'


class Evaluacion(models.Model):
    """
    Evaluación pedagógica de un estudiante en tres áreas clave:
    comunicación, conducta e interacción social.
    El motor de inferencia utiliza estos datos para generar recomendaciones.
    """
    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name='evaluaciones',
        verbose_name='Estudiante evaluado',
    )
    instructor = models.ForeignKey(
        Instructor,
        on_delete=models.CASCADE,
        related_name='evaluaciones_realizadas',
        verbose_name='Instructor que evalúa',
    )

    # ── Área 1: Comunicación ──────────────────
    dificultad_comunicacion = models.CharField(
        max_length=10,
        choices=NIVEL_CHOICES,
        verbose_name='Dificultad de comunicación',
    )
    usa_lenguaje_verbal = models.BooleanField(
        default=True,
        verbose_name='¿Usa lenguaje verbal?',
    )

    # ── Área 2: Conducta ─────────────────────
    conductas_repetitivas = models.CharField(
        max_length=10,
        choices=NIVEL_CHOICES,
        verbose_name='Conductas repetitivas',
    )
    reacciones_sensoriales = models.CharField(
        max_length=10,
        choices=NIVEL_CHOICES,
        verbose_name='Reacciones sensoriales intensas',
    )
    crisis_frecuentes = models.BooleanField(
        default=False,
        verbose_name='¿Presenta crisis frecuentes?',
    )

    # ── Área 3: Interacción Social ────────────
    interaccion_social = models.CharField(
        max_length=10,
        choices=NIVEL_CHOICES,
        verbose_name='Nivel de interacción social',
    )
    interes_pares = models.BooleanField(
        default=False,
        verbose_name='¿Muestra interés por sus pares?',
    )

    # ── Metadatos ────────────────────────────
    fecha_evaluacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de evaluación')
    notas_adicionales = models.TextField(blank=True, verbose_name='Notas adicionales')

    class Meta:
        verbose_name = 'Evaluación'
        verbose_name_plural = 'Evaluaciones'
        ordering = ['-fecha_evaluacion']

    def __str__(self):
        return f'Evaluación de {self.estudiante} — {self.fecha_evaluacion.strftime("%d/%m/%Y")}'


class Regla(models.Model):
    """
    Representa una regla del tipo SI-ENTONCES (IF-THEN) de la base de conocimientos.
    Las reglas son evaluadas por el motor de inferencia (forward chaining)
    para generar recomendaciones pedagógicas.

    Estructura lógica:
        SI  campo_condicion OP valor_condicion
        ENTONCES  accion (recomendación)

    Ejemplo:
        SI  dificultad_comunicacion == 'alto'
        ENTONCES  'Usar pictogramas como sistema de comunicación alternativa'
    """
    OPERADOR_CHOICES = [
        ('==', 'Igual a'),
        ('!=', 'Distinto de'),
        ('>', 'Mayor que'),
        ('<', 'Menor que'),
    ]

    nombre = models.CharField(max_length=200, verbose_name='Nombre de la regla')
    campo_condicion = models.CharField(
        max_length=100,
        verbose_name='Campo a evaluar',
        help_text='Nombre exacto del campo del modelo Evaluacion (ej: dificultad_comunicacion)',
    )
    operador = models.CharField(
        max_length=5,
        choices=OPERADOR_CHOICES,
        default='==',
        verbose_name='Operador de comparación',
    )
    valor_condicion = models.CharField(
        max_length=100,
        verbose_name='Valor esperado',
        help_text='Valor con el que se compara (ej: alto, True, False)',
    )
    accion = models.TextField(verbose_name='Recomendación pedagógica (acción)')
    categoria = models.CharField(
        max_length=50,
        choices=[
            ('comunicacion', 'Comunicación'),
            ('conducta', 'Conducta'),
            ('social', 'Interacción Social'),
            ('general', 'General'),
        ],
        default='general',
        verbose_name='Categoría',
    )
    prioridad = models.PositiveIntegerField(
        default=1,
        verbose_name='Prioridad',
        help_text='Mayor número = mayor prioridad en la presentación',
    )
    activa = models.BooleanField(default=True, verbose_name='¿Regla activa?')

    class Meta:
        verbose_name = 'Regla'
        verbose_name_plural = 'Reglas'
        ordering = ['-prioridad', 'nombre']

    def __str__(self):
        return f'[{self.get_categoria_display()}] {self.nombre}'


class Recomendacion(models.Model):
    """
    Almacena las recomendaciones pedagógicas generadas por el motor de inferencia
    para una evaluación específica. Cada recomendación está vinculada a la regla
    que la produjo, lo que permite trazabilidad y explicabilidad del sistema experto.
    """
    evaluacion = models.ForeignKey(
        Evaluacion,
        on_delete=models.CASCADE,
        related_name='recomendaciones',
        verbose_name='Evaluación origen',
    )
    regla = models.ForeignKey(
        Regla,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recomendaciones_generadas',
        verbose_name='Regla que la generó',
    )
    texto = models.TextField(verbose_name='Texto de la recomendación')
    categoria = models.CharField(max_length=50, verbose_name='Categoría')
    fecha_generacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de generación')

    class Meta:
        verbose_name = 'Recomendación'
        verbose_name_plural = 'Recomendaciones'
        ordering = ['-fecha_generacion']

    def __str__(self):
        return f'Recomendación para {self.evaluacion.estudiante} — {self.categoria}'
