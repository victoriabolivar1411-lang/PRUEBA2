"""
=============================================================================
SISTEMA EXPERTO PARA APOYO PEDAGÓGICO EN TEA
=============================================================================
Módulo: admin.py
Descripción: Registro de modelos en el panel de administración de Django.
             Permite gestionar reglas, estudiantes y evaluaciones desde /admin/
=============================================================================
"""

from django.contrib import admin
from .models import Instructor, Estudiante, Evaluacion, Regla, Recomendacion


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display  = ['usuario', 'especialidad', 'telefono', 'fecha_registro']
    search_fields = ['usuario__username', 'usuario__first_name', 'especialidad']


@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    list_display  = ['nombre_completo', 'nivel_tea', 'instructor', 'fecha_registro']
    list_filter   = ['nivel_tea', 'instructor']
    search_fields = ['nombre', 'apellido']


@admin.register(Evaluacion)
class EvaluacionAdmin(admin.ModelAdmin):
    list_display = [
        'estudiante', 'instructor', 'dificultad_comunicacion',
        'conductas_repetitivas', 'interaccion_social', 'fecha_evaluacion'
    ]
    list_filter  = ['dificultad_comunicacion', 'conductas_repetitivas', 'interaccion_social']
    date_hierarchy = 'fecha_evaluacion'


@admin.register(Regla)
class ReglaAdmin(admin.ModelAdmin):
    list_display  = ['nombre', 'categoria', 'campo_condicion', 'operador', 'valor_condicion', 'prioridad', 'activa']
    list_filter   = ['categoria', 'activa']
    list_editable = ['activa', 'prioridad']
    search_fields = ['nombre', 'accion']
    ordering      = ['-prioridad']


@admin.register(Recomendacion)
class RecomendacionAdmin(admin.ModelAdmin):
    list_display = ['evaluacion', 'categoria', 'regla', 'fecha_generacion']
    list_filter  = ['categoria']
    date_hierarchy = 'fecha_generacion'
