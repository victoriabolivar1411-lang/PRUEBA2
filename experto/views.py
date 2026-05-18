"""
=============================================================================
SISTEMA EXPERTO PARA APOYO PEDAGÓGICO EN TEA
=============================================================================
Módulo: views.py  — Controladores de Django
=============================================================================
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.contrib import messages
from django.db.models import Count, Q

from .models import (
    Instructor, Estudiante, Representante,
    EvaluacionDSM5, EvaluacionPedagogica, Recomendacion, Regla
)
from .forms import (
    RegistroInstructorForm, EstudianteForm, RepresentanteForm,
    EvaluacionDSM5Form, EvaluacionPedagogicaForm,
    RecuperarContrasenaForm, VerificarCodigoForm,
    EditarPerfilInstructorForm,
)
from .expert_system import generar_recomendaciones
from .utils import enviar_bienvenida


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_instructor(request):
    return get_object_or_404(Instructor, usuario=request.user)


# ─────────────────────────────────────────────────────────────────────────────
# AUTENTICACIÓN
# ─────────────────────────────────────────────────────────────────────────────

def inicio(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'experto/inicio.html')


def registro_instructor(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegistroInstructorForm(request.POST)
        if form.is_valid():
            user = form.save()
            enviar_bienvenida(user)
            login(request, user)
            messages.success(request, f'¡Bienvenido/a, {user.first_name}! Cuenta creada correctamente.')
            return redirect('dashboard')
    else:
        form = RegistroInstructorForm()
    return render(request, 'experto/registro_instructor.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Bienvenido/a, {user.first_name or user.username}.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
    else:
        form = AuthenticationForm()
    return render(request, 'experto/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'Sesión cerrada correctamente.')
    return redirect('inicio')


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def dashboard(request):
    instructor   = _get_instructor(request)
    estudiantes_all = Estudiante.objects.filter(instructor=instructor)
    
    query = request.GET.get('search', '').strip()
    if query:
        estudiantes = estudiantes_all.filter(
            Q(nombre_completo__icontains=query) |
            Q(representante__nombre_completo__icontains=query)
        ).distinct()
    else:
        estudiantes = estudiantes_all

    total_est    = estudiantes_all.count()
    total_dsm5   = EvaluacionDSM5.objects.filter(estudiante__instructor=instructor).count()
    total_ped    = EvaluacionPedagogica.objects.filter(estudiante__instructor=instructor).count()
    total_rec    = Recomendacion.objects.filter(
        evaluacion_pedagogica__estudiante__instructor=instructor
    ).count()
    ultimas_eval = EvaluacionPedagogica.objects.filter(
        estudiante__instructor=instructor
    ).select_related('estudiante').order_by('-fecha')[:5]

    return render(request, 'experto/dashboard.html', {
        'instructor':    instructor,
        'total_est':     total_est,
        'total_dsm5':    total_dsm5,
        'total_ped':     total_ped,
        'total_rec':     total_rec,
        'ultimas_eval':  ultimas_eval,
        'estudiantes':   estudiantes if query else estudiantes[:6],
        'search_query':  query,
    })


# ─────────────────────────────────────────────────────────────────────────────
# GESTIÓN DE ESTUDIANTES
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def lista_estudiantes(request):
    instructor  = _get_instructor(request)
    estudiantes = Estudiante.objects.filter(instructor=instructor).annotate(
        total_eval=Count('evaluaciones_pedagogicas')
    ).order_by('nombre_completo')

    # Buscador de reportes por estudiante, fecha y año, o reporte de instructores
    reportes = None
    instructores_report = None
    total_instructores = 0
    total_ninos_global = 0

    if request.GET.get('buscar_reportes'):
        ver_instructores = request.GET.get('ver_instructores')
        
        if ver_instructores == '1':
            instructores_report = Instructor.objects.annotate(
                total_ninos=Count('estudiantes')
            ).order_by('-total_ninos')
            total_instructores = instructores_report.count()
            total_ninos_global = Estudiante.objects.count()
        else:
            fecha = request.GET.get('fecha')
            ano = request.GET.get('ano')
            estudiante_id = request.GET.get('estudiante')

            reportes = EvaluacionPedagogica.objects.filter(
                estudiante__instructor=instructor
            ).select_related('estudiante', 'evaluacion_dsm5').order_by('-fecha')

            if estudiante_id:
                reportes = reportes.filter(estudiante_id=estudiante_id)
            if fecha:
                reportes = reportes.filter(fecha__date=fecha)
            if ano:
                reportes = reportes.filter(fecha__year=ano)

    return render(request, 'experto/lista_estudiantes.html', {
        'instructor':  instructor,
        'estudiantes': estudiantes,
        'reportes':    reportes,
        'instructores_report': instructores_report,
        'total_instructores': total_instructores,
        'total_ninos_global': total_ninos_global,
        'get_fecha':   request.GET.get('fecha', ''),
        'get_ano':     request.GET.get('ano', ''),
        'get_estudiante': request.GET.get('estudiante', ''),
        'get_ver_instructores': request.GET.get('ver_instructores', ''),
    })


@login_required(login_url='login')
def registro_estudiante(request):
    instructor = _get_instructor(request)
    if request.method == 'POST':
        form = EstudianteForm(request.POST, request.FILES)
        if form.is_valid():
            est = form.save(commit=False)
            est.instructor = instructor
            est.save()
            messages.success(request, f'Estudiante "{est.nombre_completo}" registrado correctamente.')
            return redirect('lista_estudiantes')
    else:
        form = EstudianteForm()
    return render(request, 'experto/registro_estudiante.html', {
        'form': form, 'instructor': instructor
    })


@login_required(login_url='login')
def editar_estudiante(request, pk):
    instructor = _get_instructor(request)
    est = get_object_or_404(Estudiante, pk=pk, instructor=instructor)
    if request.method == 'POST':
        form = EstudianteForm(request.POST, request.FILES, instance=est)
        if form.is_valid():
            form.save()
            messages.success(request, 'Datos del estudiante actualizados.')
            return redirect('perfil_estudiante', pk=est.pk)
    else:
        form = EstudianteForm(instance=est)
    return render(request, 'experto/registro_estudiante.html', {
        'form': form, 'instructor': instructor, 'editando': True, 'estudiante': est
    })


@login_required(login_url='login')
def borrar_estudiante(request, pk):
    instructor = _get_instructor(request)
    est = get_object_or_404(Estudiante, pk=pk, instructor=instructor)
    if request.method == 'POST':
        nombre = est.nombre_completo
        est.delete()
        messages.success(request, f'Estudiante "{nombre}" eliminado correctamente.')
        return redirect('lista_estudiantes')
    return render(request, 'experto/confirmar_borrar.html', {
        'instructor': instructor, 'estudiante': est
    })


@login_required(login_url='login')
def perfil_estudiante(request, pk):
    instructor = _get_instructor(request)
    est = get_object_or_404(Estudiante, pk=pk, instructor=instructor)
    rep = getattr(est, 'representante', None)
    eval_dsm5 = est.evaluaciones_dsm5.order_by('-fecha').first()
    eval_ped  = est.evaluaciones_pedagogicas.order_by('-fecha').first()
    recomendaciones = []
    if eval_ped:
        recomendaciones = eval_ped.recomendaciones.select_related('regla').all()
    return render(request, 'experto/perfil_estudiante.html', {
        'instructor':       instructor,
        'estudiante':       est,
        'representante':    rep,
        'eval_dsm5':        eval_dsm5,
        'eval_ped':         eval_ped,
        'recomendaciones':  recomendaciones,
    })


# ─────────────────────────────────────────────────────────────────────────────
# REPRESENTANTE
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def registro_representante(request, pk):
    instructor = _get_instructor(request)
    est = get_object_or_404(Estudiante, pk=pk, instructor=instructor)
    rep = getattr(est, 'representante', None)

    if request.method == 'POST':
        form = RepresentanteForm(request.POST, request.FILES, instance=rep)
        if form.is_valid():
            rep_obj = form.save(commit=False)
            rep_obj.estudiante = est
            rep_obj.save()
            messages.success(request, 'Datos del representante guardados.')
            return redirect('perfil_estudiante', pk=est.pk)
    else:
        form = RepresentanteForm(instance=rep)
    return render(request, 'experto/registro_representante.html', {
        'form': form, 'instructor': instructor, 'estudiante': est, 'editando': rep is not None
    })


# ─────────────────────────────────────────────────────────────────────────────
# EVALUACIÓN DSM-5
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def evaluacion_dsm5(request, pk):
    instructor = _get_instructor(request)
    est = get_object_or_404(Estudiante, pk=pk, instructor=instructor)

    if request.method == 'POST':
        form = EvaluacionDSM5Form(request.POST)
        if form.is_valid():
            ev = form.save(commit=False)
            ev.estudiante = est
            ev.save()
            messages.success(request, 'Evaluación DSM-5 guardada. Ahora complete la evaluación pedagógica.')
            return redirect('evaluacion_pedagogica', pk=est.pk, dsm5_pk=ev.pk)
    else:
        form = EvaluacionDSM5Form()
    return render(request, 'experto/evaluacion_dsm5.html', {
        'form': form, 'instructor': instructor, 'estudiante': est
    })


# ─────────────────────────────────────────────────────────────────────────────
# EVALUACIÓN PEDAGÓGICA
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def evaluacion_pedagogica(request, pk, dsm5_pk):
    instructor = _get_instructor(request)
    est = get_object_or_404(Estudiante, pk=pk, instructor=instructor)
    ev_dsm5 = get_object_or_404(EvaluacionDSM5, pk=dsm5_pk, estudiante=est)

    if request.method == 'POST':
        form = EvaluacionPedagogicaForm(request.POST)
        if form.is_valid():
            ev_ped = form.save(commit=False)
            ev_ped.estudiante = est
            ev_ped.evaluacion_dsm5 = ev_dsm5
            ev_ped.save()
            reglas = generar_recomendaciones(ev_ped)
            messages.success(
                request,
                f'Evaluación completada. El sistema generó {len(reglas)} recomendación(es).'
            )
            return redirect('resultados', ped_pk=ev_ped.pk)
    else:
        form = EvaluacionPedagogicaForm()
    return render(request, 'experto/evaluacion_pedagogica.html', {
        'form': form, 'instructor': instructor, 'estudiante': est, 'eval_dsm5': ev_dsm5
    })


# ─────────────────────────────────────────────────────────────────────────────
# RESULTADOS DEL MOTOR DE INFERENCIA
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def resultados(request, ped_pk):
    instructor  = _get_instructor(request)
    ev_ped = get_object_or_404(
        EvaluacionPedagogica, pk=ped_pk, estudiante__instructor=instructor
    )
    recomendaciones = ev_ped.recomendaciones.select_related('regla').all()
    ev_dsm5 = ev_ped.evaluacion_dsm5

    return render(request, 'experto/resultados.html', {
        'instructor':      instructor,
        'estudiante':      ev_ped.estudiante,
        'eval_ped':        ev_ped,
        'eval_dsm5':       ev_dsm5,
        'recomendaciones': recomendaciones,
        'total':           recomendaciones.count(),
    })


# ─────────────────────────────────────────────────────────────────────────────
# BASE DE CONOCIMIENTOS
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def base_conocimientos(request):
    instructor = _get_instructor(request)
    reglas = Regla.objects.filter(activa=True).order_by('nombre')
    return render(request, 'experto/base_conocimientos.html', {
        'instructor': instructor,
        'reglas':     reglas,
        'total':      reglas.count(),
    })


# ─────────────────────────────────────────────────────────────────────────────
# PERFIL DEL INSTRUCTOR
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def perfil_instructor(request):
    instructor = _get_instructor(request)
    total_estudiantes  = instructor.estudiantes.count()
    total_evaluaciones = EvaluacionPedagogica.objects.filter(
        estudiante__instructor=instructor
    ).count()
    return render(request, 'experto/perfil_instructor.html', {
        'instructor':        instructor,
        'total_estudiantes':  total_estudiantes,
        'total_evaluaciones': total_evaluaciones,
    })

@login_required(login_url='login')
def editar_perfil(request):
    instructor = _get_instructor(request)
    user = request.user

    if request.method == 'POST':
        form = EditarPerfilInstructorForm(request.POST, request.FILES)
        if form.is_valid():
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.save()

            instructor.telefono = form.cleaned_data['telefono']
            
            if form.cleaned_data['eliminar_foto']:
                instructor.foto_perfil.delete()
            elif 'foto_perfil' in request.FILES:
                instructor.foto_perfil = request.FILES['foto_perfil']
                
            instructor.save()
            messages.success(request, '¡Perfil actualizado correctamente!')
            return redirect('perfil_instructor')
    else:
        form = EditarPerfilInstructorForm(initial={
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'telefono': instructor.telefono,
        })

    return render(request, 'experto/editar_perfil.html', {
        'form': form,
        'instructor': instructor
    })


# ─────────────────────────────────────────────────────────────────────────────
# RECUPERACIÓN DE CONTRASEÑA PERSONALIZADA
# ─────────────────────────────────────────────────────────────────────────────

import random
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings as django_settings


def recuperar_contrasena(request):
    """
    Paso 1: El usuario ingresa su correo.
    Se genera un código de 6 dígitos, se guarda en Instructor y se envía por email.
    """
    form = RecuperarContrasenaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        correo = form.cleaned_data['correo']
        from django.contrib.auth.models import User
        try:
            user = User.objects.get(email=correo)
            instructor = user.instructor
        except (User.DoesNotExist, Exception):
            # Mensaje genérico por seguridad (no revelar si el correo existe)
            messages.success(
                request,
                'Si ese correo está registrado, recibirás un código en breve.'
            )
            return redirect('recuperar_contrasena')

        # Generar código de 6 dígitos
        codigo = str(random.randint(100000, 999999))
        instructor.reset_code = codigo
        instructor.reset_code_expires = timezone.now() + timedelta(minutes=10)
        instructor.save()

        # Enviar correo
        send_mail(
            subject='[TEA] Código de recuperación de contraseña',
            message=(
                f'Hola {user.first_name or user.username},\n\n'
                f'Tu código de recuperación es: {codigo}\n\n'
                f'Este código expira en 10 minutos.\n\n'
                f'Si no solicitaste este cambio, ignora este mensaje.'
            ),
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            recipient_list=[correo],
            fail_silently=False,
        )

        # Guardar user id en sesión para el paso 2
        request.session['reset_user_id'] = user.pk
        messages.success(
            request,
            'Si ese correo está registrado, recibirás un código en breve.'
        )
        return redirect('verificar_codigo')

    return render(request, 'experto/recuperar_contrasena.html', {'form': form})


def verificar_codigo(request):
    """
    Paso 2: El usuario ingresa el código y su nueva contraseña.
    """
    user_id = request.session.get('reset_user_id')
    if not user_id:
        messages.error(request, 'Sesión expirada. Solicita un nuevo código.')
        return redirect('recuperar_contrasena')

    form = VerificarCodigoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        codigo_ingresado = form.cleaned_data['codigo']
        nueva = form.cleaned_data['nueva_contrasena']

        from django.contrib.auth.models import User
        try:
            user = User.objects.get(pk=user_id)
            instructor = user.instructor
        except Exception:
            messages.error(request, 'Ocurrió un error. Intenta de nuevo.')
            return redirect('recuperar_contrasena')

        # Validar código y expiración
        if instructor.reset_code != codigo_ingresado:
            form.add_error('codigo', 'El código ingresado no es correcto.')
        elif instructor.reset_code_expires < timezone.now():
            messages.error(request, 'El código ha expirado. Solicita uno nuevo.')
            return redirect('recuperar_contrasena')
        else:
            # Actualizar contraseña y limpiar código
            user.set_password(nueva)
            user.save()
            instructor.reset_code = None
            instructor.reset_code_expires = None
            instructor.save()
            del request.session['reset_user_id']
            messages.success(
                request,
                '\u00a1Contraseña actualizada correctamente! Ahora puedes iniciar sesión.'
            )
            return redirect('login')

    return render(request, 'experto/verificar_codigo.html', {'form': form})


# ─────────────────────────────────────────────────────────────────────────────
# GESTIÓN DE INSTRUCTORES
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def borrar_instructor(request, pk):
    instructor_auth = _get_instructor(request)
    inst_to_delete = get_object_or_404(Instructor, pk=pk)
    
    if request.method == 'POST':
        nombre = inst_to_delete.usuario.username
        user_to_delete = inst_to_delete.usuario
        is_self = (inst_to_delete == instructor_auth)
        
        user_to_delete.delete()
        
        if is_self:
            messages.success(request, 'Tu cuenta ha sido eliminada correctamente.')
            return redirect('login')
            
        messages.success(request, f'Instructor "{nombre}" eliminado correctamente.')
        return redirect('/estudiantes/?buscar_reportes=1&ver_instructores=1')
        
    return render(request, 'experto/confirmar_borrar_instructor.html', {
        'instructor': instructor_auth, 
        'inst_to_delete': inst_to_delete
    })
