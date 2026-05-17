from django.contrib import admin
from .models import Instructor, Estudiante, Representante, EvaluacionDSM5, EvaluacionPedagogica, Regla, Recomendacion


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'telefono', 'fecha_registro']
    search_fields = ['usuario__first_name', 'usuario__last_name', 'usuario__email']


@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    list_display = ['nombre_completo', 'sexo', 'edad', 'instructor', 'fecha_creacion']
    list_filter = ['sexo', 'instructor']
    search_fields = ['nombre_completo']


@admin.register(Representante)
class RepresentanteAdmin(admin.ModelAdmin):
    list_display = ['nombre_completo', 'estudiante', 'estado_civil', 'correo']
    search_fields = ['nombre_completo', 'correo']


@admin.register(EvaluacionDSM5)
class EvaluacionDSM5Admin(admin.ModelAdmin):
    list_display = ['estudiante', 'fecha', 'nivel_comunicacion_social', 'nivel_conductas_repetitivas']
    list_filter = ['nivel_comunicacion_social', 'nivel_conductas_repetitivas']
    readonly_fields = ['fecha']


@admin.register(EvaluacionPedagogica)
class EvaluacionPedagogicaAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'fecha', 'nivel_comunicacion_social', 'nivel_conductas_repetitivas']
    list_filter = ['nivel_comunicacion_social']
    readonly_fields = ['fecha']


@admin.register(Regla)
class ReglaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'condicion', 'activa']
    list_filter = ['activa']
    list_editable = ['activa']
    search_fields = ['nombre', 'condicion']


@admin.register(Recomendacion)
class RecomendacionAdmin(admin.ModelAdmin):
    list_display = ['evaluacion_pedagogica', 'regla', 'generada_en']
    readonly_fields = ['generada_en']
