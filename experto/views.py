"""
=============================================================================
SISTEMA EXPERTO PARA APOYO PEDAGÓGICO EN TEA
=============================================================================
Módulo: views.py
Descripción: Controladores (vistas) de Django que manejan el flujo de la
             aplicación: registro, evaluación, ejecución del motor de
             inferencia y visualización de resultados.
=============================================================================
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
import json
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.db.models import Count

from .models import Instructor, Estudiante, Evaluacion, Recomendacion, Regla
from .forms import RegistroInstructorForm, EstudianteForm, EvaluacionForm
from .expert_system import generar_recomendaciones


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_instructor(request):
    """Obtiene el perfil Instructor del usuario autenticado."""
    return get_object_or_404(Instructor, usuario=request.user)


# ─────────────────────────────────────────────────────────────────────────────
# AUTENTICACIÓN
# ─────────────────────────────────────────────────────────────────────────────

def inicio(request):
    """Página de bienvenida / landing page del sistema."""
    return render(request, 'experto/inicio.html')


def registro_instructor(request):
    """
    Registro de un nuevo instructor. Crea el usuario Django y el perfil
    Instructor asociado. Redirige al dashboard tras el registro exitoso.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegistroInstructorForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'¡Bienvenido/a, {user.first_name}! Tu cuenta fue creada correctamente.')
            return redirect('dashboard')
    else:
        form = RegistroInstructorForm()

    return render(request, 'experto/registro_instructor.html', {'form': form})


def login_view(request):
    """Vista de inicio de sesión."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Bienvenido/a de vuelta, {user.first_name}.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
    else:
        form = AuthenticationForm()

    return render(request, 'experto/login.html', {'form': form})


def logout_view(request):
    """Cierra la sesión y redirige a la página de inicio."""
    logout(request)
    messages.info(request, 'Sesión cerrada correctamente.')
    return redirect('inicio')


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def dashboard(request):
    """
    Panel principal del instructor. Muestra estadísticas generales:
    número de estudiantes, evaluaciones realizadas y últimas recomendaciones.
    """
    instructor = get_instructor(request)
    estudiantes = Estudiante.objects.filter(instructor=instructor)
    evaluaciones = Evaluacion.objects.filter(instructor=instructor).order_by('-fecha_evaluacion')[:5]
    total_evaluaciones = Evaluacion.objects.filter(instructor=instructor).count()

    context = {
        'instructor':        instructor,
        'estudiantes':       estudiantes,
        'total_estudiantes': estudiantes.count(),
        'evaluaciones':      evaluaciones,
        'total_evaluaciones': total_evaluaciones,
    }
    return render(request, 'experto/dashboard.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# GESTIÓN DE ESTUDIANTES
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def lista_estudiantes(request):
    """Lista todos los estudiantes del instructor autenticado."""
    instructor = get_instructor(request)
    estudiantes = Estudiante.objects.filter(instructor=instructor).annotate(
        num_evaluaciones=Count('evaluaciones')
    )
    return render(request, 'experto/lista_estudiantes.html', {
        'estudiantes': estudiantes,
        'instructor':  instructor,
    })


@login_required(login_url='login')
def registro_estudiante(request):
    """
    Registra un nuevo estudiante asociado al instructor autenticado.
    El instructor se asigna automáticamente (no aparece en el formulario).
    """
    instructor = get_instructor(request)

    if request.method == 'POST':
        form = EstudianteForm(request.POST)
        if form.is_valid():
            estudiante = form.save(commit=False)
            estudiante.instructor = instructor
            estudiante.save()
            messages.success(request, f'Estudiante {estudiante.nombre_completo} registrado correctamente.')
            return redirect('lista_estudiantes')
    else:
        form = EstudianteForm()

    return render(request, 'experto/registro_estudiante.html', {'form': form, 'instructor': instructor})


@login_required(login_url='login')
def detalle_estudiante(request, pk):
    """Muestra el perfil completo de un estudiante con su historial de evaluaciones."""
    instructor = get_instructor(request)
    estudiante = get_object_or_404(Estudiante, pk=pk, instructor=instructor)
    evaluaciones = estudiante.evaluaciones.all().order_by('-fecha_evaluacion')

    return render(request, 'experto/detalle_estudiante.html', {
        'estudiante':  estudiante,
        'evaluaciones': evaluaciones,
        'instructor':  instructor,
    })


# ─────────────────────────────────────────────────────────────────────────────
# EVALUACIÓN Y MOTOR DE INFERENCIA
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def nueva_evaluacion(request, estudiante_pk):
    """
    Realiza una nueva evaluación pedagógica de un estudiante.
    Tras guardar el formulario, invoca el motor de inferencia para
    generar las recomendaciones automáticamente.
    """
    instructor = get_instructor(request)
    estudiante = get_object_or_404(Estudiante, pk=estudiante_pk, instructor=instructor)

    if request.method == 'POST':
        form = EvaluacionForm(request.POST)
        if form.is_valid():
            evaluacion = form.save(commit=False)
            evaluacion.estudiante = estudiante
            evaluacion.instructor = instructor
            evaluacion.save()

            # ── EJECUTAR MOTOR DE INFERENCIA ─────────────────────────────────
            recomendaciones = generar_recomendaciones(evaluacion)

            messages.success(
                request,
                f'Evaluación guardada. El motor de inferencia generó '
                f'{len(recomendaciones)} recomendación(es).'
            )
            return redirect('resultados', evaluacion_pk=evaluacion.pk)
    else:
        form = EvaluacionForm()

    return render(request, 'experto/evaluacion.html', {
        'form':       form,
        'estudiante': estudiante,
        'instructor': instructor,
    })


@login_required(login_url='login')
def resultados(request, evaluacion_pk):
    """
    Muestra los resultados de una evaluación: los hechos evaluados
    y las recomendaciones pedagógicas generadas por el motor de inferencia,
    agrupadas por categoría.
    """
    instructor  = get_instructor(request)
    evaluacion  = get_object_or_404(
        Evaluacion, pk=evaluacion_pk, instructor=instructor
    )
    recomendaciones = evaluacion.recomendaciones.all().order_by('categoria')

    # Agrupar recomendaciones por categoría para la vista
    grupos = {}
    for rec in recomendaciones:
        cat = rec.get_categoria_display() if hasattr(rec, 'get_categoria_display') else rec.categoria
        grupos.setdefault(cat, []).append(rec)

    # Etiquetas de display para los hechos evaluados
    NIVELES = {'bajo': 'Bajo', 'medio': 'Medio', 'alto': 'Alto'}
    hechos = [
        ('Dificultad de comunicación', NIVELES.get(evaluacion.dificultad_comunicacion, '')),
        ('Usa lenguaje verbal',        'Sí' if evaluacion.usa_lenguaje_verbal else 'No'),
        ('Conductas repetitivas',      NIVELES.get(evaluacion.conductas_repetitivas, '')),
        ('Reacciones sensoriales',     NIVELES.get(evaluacion.reacciones_sensoriales, '')),
        ('Crisis frecuentes',          'Sí' if evaluacion.crisis_frecuentes else 'No'),
        ('Interacción social',         NIVELES.get(evaluacion.interaccion_social, '')),
        ('Interés por pares',          'Sí' if evaluacion.interes_pares else 'No'),
    ]

    # Historial para la gráfica
    historial = Evaluacion.objects.filter(
        estudiante=evaluacion.estudiante,
        fecha_evaluacion__lte=evaluacion.fecha_evaluacion
    ).order_by('fecha_evaluacion')
    
    fechas = []
    comunicacion = []
    conducta = []
    social = []
    mapa_niveles = {'bajo': 1, 'medio': 2, 'alto': 3}
    
    for ev in historial:
        fechas.append(ev.fecha_evaluacion.strftime("%d/%m/%Y"))
        comunicacion.append(mapa_niveles.get(ev.dificultad_comunicacion, 0))
        conducta.append(mapa_niveles.get(ev.conductas_repetitivas, 0))
        social.append(mapa_niveles.get(ev.interaccion_social, 0))
        
    chart_data = json.dumps({
        'fechas': fechas,
        'comunicacion': comunicacion,
        'conducta': conducta,
        'social': social
    })

    return render(request, 'experto/resultados.html', {
        'evaluacion':      evaluacion,
        'estudiante':      evaluacion.estudiante,
        'instructor':      instructor,
        'recomendaciones': recomendaciones,
        'grupos':          grupos,
        'hechos':          hechos,
        'total':           recomendaciones.count(),
        'chart_data':      chart_data,
    })


@login_required(login_url='login')
def historial_evaluaciones(request):
    """Historial completo de evaluaciones realizadas por el instructor."""
    instructor  = get_instructor(request)
    evaluaciones = Evaluacion.objects.filter(instructor=instructor).select_related(
        'estudiante'
    ).order_by('-fecha_evaluacion')

    return render(request, 'experto/historial.html', {
        'evaluaciones': evaluaciones,
        'instructor':   instructor,
    })


# ─────────────────────────────────────────────────────────────────────────────
# BASE DE CONOCIMIENTOS (solo lectura para instructores)
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def base_conocimientos(request):
    """
    Muestra las reglas de la base de conocimientos agrupadas por categoría.
    Permite al instructor consultar qué reglas existen en el sistema experto.
    """
    reglas = Regla.objects.filter(activa=True).order_by('categoria', '-prioridad')

    grupos = {}
    CATEGORIAS = {
        'comunicacion': 'Comunicación',
        'conducta':     'Conducta',
        'social':       'Interacción Social',
        'general':      'General',
    }
    for regla in reglas:
        cat_label = CATEGORIAS.get(regla.categoria, regla.categoria)
        grupos.setdefault(cat_label, []).append(regla)

    return render(request, 'experto/base_conocimientos.html', {
        'grupos':      grupos,
        'total_reglas': reglas.count(),
    })
