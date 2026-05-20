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
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from .chatbot_engine import detectar_intencion, mensaje_bienvenida, generar_respuesta

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
        import unicodedata
        
        def normalizar(t):
            if not t:
                return ""
            return "".join(
                c for c in unicodedata.normalize('NFD', t.lower())
                if unicodedata.category(c) != 'Mn'
            ).strip()
            
        palabras_busqueda = normalizar(query).split()
        estudiantes_filtrados = []
        for est in estudiantes_all:
            nom_norm = normalizar(est.nombre_completo)
            rep_norm = normalizar(est.representante.nombre_completo) if hasattr(est, 'representante') else ""
            if all(p in nom_norm or p in rep_norm for p in palabras_busqueda):
                estudiantes_filtrados.append(est)
        estudiantes = estudiantes_filtrados
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
                from django.utils.dateparse import parse_date
                from datetime import datetime, time
                from django.utils.timezone import make_aware
                d = parse_date(fecha)
                if d:
                    start = make_aware(datetime.combine(d, time.min))
                    end = make_aware(datetime.combine(d, time.max))
                    reportes = reportes.filter(fecha__range=(start, end))
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
            instructor.sexo = form.cleaned_data['sexo']
            instructor.edad = form.cleaned_data['edad']
            instructor.estado_civil = form.cleaned_data['estado_civil']
            instructor.cedula = form.cleaned_data['cedula']
            instructor.estado = form.cleaned_data['estado']
            instructor.municipio = form.cleaned_data['municipio']
            instructor.direccion = form.cleaned_data['direccion']
            instructor.respuesta_1 = form.cleaned_data['respuesta_1'].strip()
            instructor.respuesta_2 = form.cleaned_data['respuesta_2'].strip()
            instructor.respuesta_3 = form.cleaned_data['respuesta_3'].strip()
            
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
            'sexo': instructor.sexo,
            'edad': instructor.edad,
            'estado_civil': instructor.estado_civil,
            'cedula': instructor.cedula,
            'estado': instructor.estado,
            'municipio': instructor.municipio,
            'direccion': instructor.direccion,
            'respuesta_1': instructor.respuesta_1,
            'respuesta_2': instructor.respuesta_2,
            'respuesta_3': instructor.respuesta_3,
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
    Recuperación de contraseña en 2 pasos por Preguntas de Seguridad.
    Paso 1: Identificar al usuario con su Nombre de usuario o Cédula.
    Paso 2: Responder 3 preguntas de seguridad.
    """
    from django.contrib.auth.models import User
    from .models import Instructor

    step = request.session.get('recovery_step', 'identify')
    user_id = request.session.get('recovery_user_id')
    
    # Si por alguna razón estamos en paso de preguntas pero no hay id de usuario en sesión
    if step == 'questions' and not user_id:
        step = 'identify'
        request.session['recovery_step'] = 'identify'

    form_identify = None
    instructor = None

    if step == 'identify':
        form_identify = RecuperarContrasenaForm(request.POST or None)
        if request.method == 'POST' and form_identify.is_valid():
            usuario_o_cedula = form_identify.cleaned_data['usuario_o_cedula'].strip()
            user = None
            
            # Buscar por username
            try:
                user = User.objects.get(username=usuario_o_cedula)
            except User.DoesNotExist:
                # Intentar buscar por cédula
                try:
                    instructor_obj = Instructor.objects.get(cedula=usuario_o_cedula)
                    user = instructor_obj.usuario
                except Instructor.DoesNotExist:
                    pass
            
            if user and hasattr(user, 'instructor'):
                request.session['recovery_user_id'] = user.pk
                request.session['recovery_step'] = 'questions'
                messages.success(request, 'Usuario identificado. Responde las siguientes preguntas de seguridad.')
                return redirect('recuperar_contrasena')
            else:
                form_identify.add_error('usuario_o_cedula', 'El usuario o cédula ingresado no está registrado en el sistema.')

    elif step == 'questions':
        try:
            user = User.objects.get(pk=user_id)
            instructor = user.instructor
        except Exception:
            messages.error(request, 'Ocurrió un error. Intenta de nuevo.')
            request.session['recovery_step'] = 'identify'
            return redirect('recuperar_contrasena')

        if request.method == 'POST':
            r1 = request.POST.get('respuesta_1', '').strip()
            r2 = request.POST.get('respuesta_2', '').strip()
            r3 = request.POST.get('respuesta_3', '').strip()
            
            # Helper to normalize strings for comparison (lowercase, spaces, accents)
            import unicodedata
            def normalizar(text):
                if not text:
                    return ""
                # Normalize NFD to remove accents, lower case, strip
                text_norm = "".join(
                    c for c in unicodedata.normalize('NFD', text.lower())
                    if unicodedata.category(c) != 'Mn'
                )
                return text_norm.replace(" ", "")

            ans1_db = normalizar(instructor.respuesta_1)
            ans2_db = normalizar(instructor.respuesta_2)
            ans3_db = normalizar(instructor.respuesta_3)

            ans1_input = normalizar(r1)
            ans2_input = normalizar(r2)
            ans3_input = normalizar(r3)

            # Verificar si el instructor no tiene configuradas las respuestas
            if not ans1_db or not ans2_db or not ans3_db:
                messages.error(request, 'Tu cuenta no tiene configuradas las preguntas de seguridad. Por favor, contacta al soporte técnico o administrador del sistema.')
                return redirect('recuperar_contrasena')

            if ans1_db == ans1_input and ans2_db == ans2_input and ans3_db == ans3_input:
                # Generar código de 6 dígitos
                codigo = str(random.randint(100000, 999999))
                instructor.reset_code = codigo
                instructor.reset_code_expires = timezone.now() + timedelta(minutes=5)
                instructor.save()

                # Limpiar datos de identificación de la sesión y guardar reset_user_id
                request.session['reset_user_id'] = user.pk
                if 'recovery_user_id' in request.session:
                    del request.session['recovery_user_id']
                if 'recovery_step' in request.session:
                    del request.session['recovery_step']

                messages.success(request, '¡Preguntas respondidas correctamente! El código de recuperación se muestra a continuación.')
                return redirect('verificar_codigo')
            else:
                messages.error(request, 'Una o más respuestas son incorrectas. Inténtalo de nuevo.')

    # Si se pide reiniciar el flujo
    reset_flow = request.GET.get('reiniciar')
    if reset_flow == '1':
        if 'recovery_user_id' in request.session:
            del request.session['recovery_user_id']
        if 'recovery_step' in request.session:
            del request.session['recovery_step']
        return redirect('recuperar_contrasena')

    return render(request, 'experto/recuperar_contrasena.html', {
        'step': step,
        'form': form_identify,
        'instructor': instructor
    })


def verificar_codigo(request):
    """
    Paso 3: El sistema muestra el código generado y el usuario ingresa dicho código y su nueva contraseña.
    """
    user_id = request.session.get('reset_user_id')
    if not user_id:
        messages.error(request, 'Sesión expirada. Por favor, inicia el proceso de recuperación de nuevo.')
        return redirect('recuperar_contrasena')

    from django.contrib.auth.models import User
    try:
        user = User.objects.get(pk=user_id)
        instructor = user.instructor
    except Exception:
        messages.error(request, 'Ocurrió un error. Intenta de nuevo.')
        return redirect('recuperar_contrasena')

    # Regenerar código automáticamente cuando se solicite
    if request.GET.get('regenerar') == '1':
        import random
        codigo = str(random.randint(100000, 999999))
        instructor.reset_code = codigo
        instructor.reset_code_expires = timezone.now() + timedelta(minutes=5)
        instructor.save()
        messages.info(request, 'Código de recuperación renovado automáticamente.')
        return redirect('verificar_codigo')

    form = VerificarCodigoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        codigo_ingresado = form.cleaned_data['codigo']
        nueva = form.cleaned_data['nueva_contrasena']

        # Validar código y expiración
        if instructor.reset_code != codigo_ingresado:
            form.add_error('codigo', 'El código ingresado no es correcto.')
        elif instructor.reset_code_expires and instructor.reset_code_expires < timezone.now():
            messages.error(request, 'El código ha expirado. Generando uno nuevo.')
            return redirect('verificar_codigo')
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
                '¡Contraseña actualizada correctamente! Ahora puedes iniciar sesión.'
            )
            return redirect('login')

    # Calcular segundos restantes
    remaining_seconds = 0
    if instructor.reset_code_expires:
        delta = instructor.reset_code_expires - timezone.now()
        remaining_seconds = max(0, int(delta.total_seconds()))

    return render(request, 'experto/verificar_codigo.html', {
        'form': form,
        'reset_code': instructor.reset_code,
        'remaining_seconds': remaining_seconds,
    })


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


@csrf_exempt
@require_POST
def chatbot_api(request):
    """
    Endpoint JSON para el chatbot NLP.
    Recibe: { "mensaje": str, "bienvenida": bool (opcional) }
    Retorna: { "texto": str, "botones": list, "intencion": str }
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, Exception):
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    # ── Mensaje de bienvenida inicial ──────────────────────────────────────
    if data.get('bienvenida'):
        nombre = ''
        if request.user.is_authenticated:
            nombre = request.user.first_name or request.user.username
        respuesta = mensaje_bienvenida(nombre)
        # Inicializar historial de sesión
        request.session['chat_historial'] = []
        return JsonResponse(respuesta)

    mensaje_usuario = data.get('mensaje', '').strip()
    if not mensaje_usuario:
        return JsonResponse({'error': 'Mensaje vacío'}, status=400)

    # ── Recuperar historial de sesión (últimos 5 intercambios) ────────────
    historial = request.session.get('chat_historial', [])

    # ── Detectar intención ────────────────────────────────────────────────
    intencion = detectar_intencion(mensaje_usuario, historial)

    # ── Contexto del usuario autenticado y mensaje original ───────────────
    contexto = {
        'autenticado': request.user.is_authenticated,
        'mensaje': mensaje_usuario
    }
    if request.user.is_authenticated:
        contexto['nombre'] = request.user.first_name or request.user.username

    # ── Generar respuesta ─────────────────────────────────────────────────
    respuesta = generar_respuesta(intencion, contexto)

    # ── Guardar en historial de sesión ────────────────────────────────────
    historial.append({'role': 'user', 'text': mensaje_usuario})
    historial.append({
        'role': 'bot',
        'text': respuesta['texto'],
        'intencion': intencion,
    })
    # Mantener solo los últimos 10 mensajes (5 intercambios)
    request.session['chat_historial'] = historial[-10:]
    request.session.modified = True

    return JsonResponse(respuesta)
