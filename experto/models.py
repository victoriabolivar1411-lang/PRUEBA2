"""
=============================================================================
SISTEMA EXPERTO PARA APOYO PEDAGÓGICO EN TEA
=============================================================================
Módulo: models.py
Descripción: Define la estructura de la base de datos del sistema.
             Modelos: Instructor, Estudiante, Representante,
             EvaluacionDSM5, EvaluacionPedagogica, Regla, Recomendacion.
=============================================================================
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


# ─────────────────────────────────────────────────────────────────────────────
# CHOICES COMPARTIDOS
# ─────────────────────────────────────────────────────────────────────────────

SEXO_CHOICES = [
    ('M', 'Masculino'),
    ('F', 'Femenino'),
    ('O', 'Otro'),
]

ESTADO_CIVIL_CHOICES = [
    ('soltero',       'Soltero/a'),
    ('casado',        'Casado/a'),
    ('divorciado',    'Divorciado/a'),
    ('viudo',         'Viudo/a'),
    ('union_libre',   'Unión libre'),
]

PARENTESCO_CHOICES = [
    ('padre',   'Padre'),
    ('madre',   'Madre'),
    ('tutor',   'Tutor/a'),
    ('abuelo',  'Abuelo/a'),
    ('otro',    'Otro'),
]

# Niveles para Criterio A (Comunicación Social)
NIVEL_COMUNICACION_CHOICES = [
    ('necesita_apoyo',          'Nivel 1 — Necesita apoyo'),
    ('apoyo_sustancial',        'Nivel 2 — Apoyo sustancial'),
    ('apoyo_constante',         'Nivel 3 — Necesita apoyo constante'),
]

# Niveles para Criterio B (Conductas Repetitivas)
NIVEL_CONDUCTAS_CHOICES = [
    ('necesita_ayuda',          'Nivel 1 — Necesita ayuda'),
    ('ayuda_notable',           'Nivel 2 — Necesita ayuda notable'),
    ('ayuda_muy_notable',       'Nivel 3 — Necesita ayuda muy notable'),
]


# ─────────────────────────────────────────────────────────────────────────────
# 1. INSTRUCTOR
# ─────────────────────────────────────────────────────────────────────────────

class Instructor(models.Model):
    """
    Perfil extendido vinculado al usuario de autenticación Django.
    Representa al instructor que usa el sistema para gestionar sus estudiantes.
    """
    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='instructor',
        verbose_name='Usuario del sistema',
    )
    sexo = models.CharField(
        max_length=1, choices=SEXO_CHOICES, verbose_name='Sexo', blank=True, null=True
    )
    edad = models.PositiveIntegerField(
        verbose_name='Edad', validators=[MinValueValidator(0), MaxValueValidator(120)], blank=True, null=True
    )
    estado_civil = models.CharField(
        max_length=20, choices=ESTADO_CIVIL_CHOICES, verbose_name='Estado civil', blank=True, null=True
    )
    cedula = models.CharField(
        max_length=15, verbose_name='Cédula', unique=True, blank=True, null=True
    )
    estado = models.CharField(max_length=100, blank=True, null=True, verbose_name='Estado')
    municipio = models.CharField(max_length=100, blank=True, null=True, verbose_name='Municipio')
    direccion = models.TextField(verbose_name='Dirección detallada', blank=True, null=True)
    telefono = models.CharField(
        max_length=20, blank=True, verbose_name='Teléfono'
    )
    foto_perfil = models.ImageField(
        upload_to='fotos_instructores/',
        blank=True,
        null=True,
        verbose_name='Foto de perfil',
    )
    respuesta_1 = models.CharField(
        max_length=200, blank=True, null=True, verbose_name='Respuesta a pregunta 1: Mascota'
    )
    respuesta_2 = models.CharField(
        max_length=200, blank=True, null=True, verbose_name='Respuesta a pregunta 2: Ciudad natal'
    )
    respuesta_3 = models.CharField(
        max_length=200, blank=True, null=True, verbose_name='Respuesta a pregunta 3: Comida favorita'
    )
    reset_code = models.CharField(
        max_length=6, blank=True, null=True, verbose_name='Código de recuperación'
    )
    reset_code_expires = models.DateTimeField(
        blank=True, null=True, verbose_name='Expiración del código'
    )
    fecha_registro = models.DateTimeField(
        auto_now_add=True, verbose_name='Fecha de registro'
    )

    class Meta:
        verbose_name        = 'Instructor'
        verbose_name_plural = 'Instructores'

    def __str__(self):
        return self.usuario.get_full_name() or self.usuario.username

    @property
    def nombre_completo(self):
        return self.usuario.get_full_name()

    @property
    def email(self):
        return self.usuario.email


# ─────────────────────────────────────────────────────────────────────────────
# 2. ESTUDIANTE
# ─────────────────────────────────────────────────────────────────────────────

class Estudiante(models.Model):
    """
    Niño o niña con TEA registrado en el sistema.
    Incluye foto tipo carnet procesada con Pillow.
    """
    instructor = models.ForeignKey(
        Instructor,
        on_delete=models.CASCADE,
        related_name='estudiantes',
        verbose_name='Instructor responsable',
    )
    nombre_completo = models.CharField(
        max_length=150, verbose_name='Nombre completo'
    )
    sexo = models.CharField(
        max_length=1, choices=SEXO_CHOICES, verbose_name='Sexo'
    )
    edad = models.PositiveIntegerField(
        verbose_name='Edad',
        validators=[MinValueValidator(0), MaxValueValidator(120)],
    )
    foto_carnet = models.ImageField(
        upload_to='fotos_estudiantes/',
        blank=True,
        null=True,
        verbose_name='Foto carnet',
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True, verbose_name='Fecha de registro'
    )

    class Meta:
        verbose_name        = 'Estudiante'
        verbose_name_plural = 'Estudiantes'
        ordering            = ['nombre_completo']

    def __str__(self):
        return self.nombre_completo

    @property
    def tiene_foto(self):
        return bool(self.foto_carnet and self.foto_carnet.name)

    @property
    def tiene_representante(self):
        return hasattr(self, 'representante')

    @property
    def ultima_evaluacion_dsm5(self):
        return self.evaluaciones_dsm5.order_by('-fecha').first()

    @property
    def ultima_evaluacion_pedagogica(self):
        return self.evaluaciones_pedagogicas.order_by('-fecha').first()


# ─────────────────────────────────────────────────────────────────────────────
# 3. REPRESENTANTE
# ─────────────────────────────────────────────────────────────────────────────

class Representante(models.Model):
    """
    Representante legal o familiar del estudiante.
    Relación uno a uno: cada estudiante tiene un único representante.
    """
    estudiante = models.OneToOneField(
        Estudiante,
        on_delete=models.CASCADE,
        related_name='representante',
        verbose_name='Estudiante',
    )
    nombre_completo = models.CharField(
        max_length=150, verbose_name='Nombre completo'
    )
    sexo = models.CharField(
        max_length=1, choices=SEXO_CHOICES, verbose_name='Sexo'
    )
    edad = models.PositiveIntegerField(
        verbose_name='Edad',
        validators=[MinValueValidator(0), MaxValueValidator(120)],
    )
    estado_civil = models.CharField(
        max_length=20,
        choices=ESTADO_CIVIL_CHOICES,
        verbose_name='Estado civil',
    )
    correo = models.EmailField(verbose_name='Correo electrónico', blank=True)
    telefono = models.CharField(max_length=20, verbose_name='Teléfono', blank=True, null=True)
    cedula = models.CharField(
        max_length=15,
        verbose_name='Cédula',
        unique=True,
    )
    parentesco = models.CharField(
        max_length=10,
        choices=PARENTESCO_CHOICES,
        verbose_name='Parentesco con el estudiante',
    )
    estado = models.CharField(max_length=100, blank=True, null=True, verbose_name='Estado')
    municipio = models.CharField(max_length=100, blank=True, null=True, verbose_name='Municipio')
    direccion = models.TextField(verbose_name='Dirección detallada')
    foto_carnet = models.ImageField(
        upload_to='fotos_representantes/',
        blank=True,
        null=True,
        verbose_name='Foto carnet',
    )

    class Meta:
        verbose_name        = 'Representante'
        verbose_name_plural = 'Representantes'

    def __str__(self):
        return f'{self.nombre_completo} (rep. de {self.estudiante})'


# ─────────────────────────────────────────────────────────────────────────────
# 4. EVALUACIÓN DSM-5
# ─────────────────────────────────────────────────────────────────────────────

class EvaluacionDSM5(models.Model):
    """
    Evaluación clínica basada en los criterios diagnósticos del DSM-5 para TEA.

    Criterio A — Comunicación Social (3 subcriterios obligatorios)
    Criterio B — Comportamientos restringidos/repetitivos (≥ 2 de 4)
    Criterio C — Inicio en las primeras fases del desarrollo
    Criterio D — Causa deterioro clínicamente significativo
    Criterio E — No explicado por discapacidad intelectual aislada
    """
    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name='evaluaciones_dsm5',
        verbose_name='Estudiante',
    )
    fecha = models.DateTimeField(auto_now_add=True, verbose_name='Fecha')

    # ── CRITERIO A: Comunicación Social ──────────────────────────────────────
    nivel_comunicacion_social = models.CharField(
        max_length=30,
        choices=NIVEL_COMUNICACION_CHOICES,
        verbose_name='Nivel de comunicación social (Criterio A)',
    )
    # A.1 Reciprocidad socioemocional
    obs_reciprocidad = models.TextField(
        blank=True,
        verbose_name='A.1 — Reciprocidad socioemocional (observaciones)',
    )
    # A.2 Comunicación no verbal
    obs_comunicacion_no_verbal = models.TextField(
        blank=True,
        verbose_name='A.2 — Comunicación no verbal (observaciones)',
    )
    # A.3 Desarrollo y comprensión de relaciones
    obs_desarrollo_relaciones = models.TextField(
        blank=True,
        verbose_name='A.3 — Desarrollo y comprensión de relaciones (observaciones)',
    )

    # ── CRITERIO B: Comportamientos Restringidos y Repetitivos ───────────────
    nivel_conductas_repetitivas = models.CharField(
        max_length=30,
        choices=NIVEL_CONDUCTAS_CHOICES,
        verbose_name='Nivel de conductas repetitivas (Criterio B)',
    )
    # B.1 Movimientos estereotipados
    movimientos_repetitivos = models.BooleanField(
        default=False,
        verbose_name='B.1 — Movimientos, uso de objetos o habla estereotipada',
    )
    # B.2 Inflexibilidad de rutinas
    inflexibilidad_rutinas = models.BooleanField(
        default=False,
        verbose_name='B.2 — Insistencia en la monotonía / inflexibilidad de rutinas',
    )
    # B.3 Intereses fijos
    intereses_restringidos = models.BooleanField(
        default=False,
        verbose_name='B.3 — Intereses muy restringidos y fijos',
    )
    # B.4 Alteraciones sensoriales
    alteraciones_sensoriales = models.BooleanField(
        default=False,
        verbose_name='B.4 — Hiper o hiporreactividad sensorial',
    )

    # ── CRITERIO C, D, E ─────────────────────────────────────────────────────
    inicio_temprano = models.BooleanField(
        default=False,
        verbose_name='C — Síntomas presentes en las primeras fases del desarrollo',
    )
    deterioro_significativo = models.BooleanField(
        default=False,
        verbose_name='D — Causa deterioro clínicamente significativo',
    )
    no_explicado_otra_condicion = models.BooleanField(
        default=False,
        verbose_name='E — No se explica mejor por discapacidad intelectual aislada',
    )

    # ── ESPECIFICADORES ───────────────────────────────────────────────────────
    discapacidad_intelectual = models.BooleanField(
        default=False,
        verbose_name='Con discapacidad intelectual acompañante',
    )
    deterioro_lenguaje = models.BooleanField(
        default=False,
        verbose_name='Con deterioro del lenguaje acompañante',
    )
    condicion_medica_asociada = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Afección médica o genética asociada (opcional)',
    )

    class Meta:
        verbose_name        = 'Evaluación DSM-5'
        verbose_name_plural = 'Evaluaciones DSM-5'
        ordering            = ['-fecha']

    def __str__(self):
        return f'DSM-5 de {self.estudiante} — {self.fecha}'

    def cumple_criterio_b(self) -> bool:
        """
        Retorna True si el estudiante cumple el Criterio B del DSM-5,
        es decir, si presenta al menos 2 de las 4 conductas B.1–B.4.
        """
        marcados = sum([
            self.movimientos_repetitivos,
            self.inflexibilidad_rutinas,
            self.intereses_restringidos,
            self.alteraciones_sensoriales,
        ])
        return marcados >= 2

    @property
    def total_criterio_b(self) -> int:
        """Número total de conductas B marcadas."""
        return sum([
            self.movimientos_repetitivos,
            self.inflexibilidad_rutinas,
            self.intereses_restringidos,
            self.alteraciones_sensoriales,
        ])


# ─────────────────────────────────────────────────────────────────────────────
# 5. EVALUACIÓN PEDAGÓGICA
# ─────────────────────────────────────────────────────────────────────────────

class EvaluacionPedagogica(models.Model):
    """
    Evaluación pedagógica simplificada en 2 áreas, alineada con el DSM-5.
    Alimenta directamente al motor de inferencia para generar recomendaciones.
    Requiere una EvaluacionDSM5 previa del mismo estudiante.
    """
    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name='evaluaciones_pedagogicas',
        verbose_name='Estudiante',
    )
    evaluacion_dsm5 = models.ForeignKey(
        EvaluacionDSM5,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evaluaciones_pedagogicas',
        verbose_name='Evaluación DSM-5 asociada',
    )
    fecha = models.DateTimeField(auto_now_add=True, verbose_name='Fecha')

    # ── Área 1: Comunicación Social ───────────────────────────────────────────
    nivel_comunicacion_social = models.CharField(
        max_length=30,
        choices=NIVEL_COMUNICACION_CHOICES,
        verbose_name='Nivel — Área comunicación social',
    )
    observaciones_comunicacion = models.TextField(
        blank=True,
        verbose_name='Observaciones — Comunicación social',
    )

    # ── Área 2: Comportamientos Restringidos ──────────────────────────────────
    nivel_conductas_repetitivas = models.CharField(
        max_length=30,
        choices=NIVEL_CONDUCTAS_CHOICES,
        verbose_name='Nivel — Área conductas repetitivas',
    )
    observaciones_conductas = models.TextField(
        blank=True,
        verbose_name='Observaciones — Conductas repetitivas',
    )

    class Meta:
        verbose_name        = 'Evaluación Pedagógica'
        verbose_name_plural = 'Evaluaciones Pedagógicas'
        ordering            = ['-fecha']

    def __str__(self):
        return f'Pedagógica de {self.estudiante} — {self.fecha}'


# ─────────────────────────────────────────────────────────────────────────────
# 6. REGLA (Base de Conocimientos)
# ─────────────────────────────────────────────────────────────────────────────

class Regla(models.Model):
    """
    Regla SI-ENTONCES de la base de conocimientos del sistema experto.
    Evaluada por el motor de inferencia (forward chaining).
    """
    nombre = models.CharField(
        max_length=200, verbose_name='Nombre de la regla'
    )
    condicion = models.TextField(
        verbose_name='Condición (SI...)',
        help_text='Descripción legible de la condición que activa esta regla.',
    )
    recomendacion = models.TextField(
        verbose_name='Recomendación pedagógica (ENTONCES...)'
    )
    recursos_didacticos = models.TextField(
        blank=True,
        verbose_name='Recursos didácticos sugeridos',
    )
    activa = models.BooleanField(default=True, verbose_name='¿Regla activa?')

    class Meta:
        verbose_name        = 'Regla'
        verbose_name_plural = 'Reglas'
        ordering            = ['nombre']

    def __str__(self):
        return self.nombre


# ─────────────────────────────────────────────────────────────────────────────
# 7. RECOMENDACIÓN (Resultado del Motor)
# ─────────────────────────────────────────────────────────────────────────────

class Recomendacion(models.Model):
    """
    Recomendación pedagógica generada automáticamente por el motor de inferencia
    para una evaluación pedagógica específica.
    """
    evaluacion_pedagogica = models.ForeignKey(
        EvaluacionPedagogica,
        on_delete=models.CASCADE,
        related_name='recomendaciones',
        verbose_name='Evaluación pedagógica origen',
    )
    regla = models.ForeignKey(
        Regla,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recomendaciones_generadas',
        verbose_name='Regla que la generó',
    )
    texto = models.TextField(verbose_name='Texto de la recomendación')
    generada_en = models.DateTimeField(
        auto_now_add=True, verbose_name='Fecha de generación'
    )

    class Meta:
        verbose_name        = 'Recomendación'
        verbose_name_plural = 'Recomendaciones'
        ordering            = ['generada_en']

    def __str__(self):
        return f'Recomendación para {self.evaluacion_pedagogica.estudiante}'
