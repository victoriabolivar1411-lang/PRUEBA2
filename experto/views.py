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


@login_required(login_url='login')
def chatbot_query(request):
    import json
    if request.method != 'POST':
        from django.http import JsonResponse
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
    except Exception:
        from django.http import JsonResponse
        return JsonResponse({'error': 'Formato inválido'}, status=400)
    
    from django.http import JsonResponse
    if not user_message:
        return JsonResponse({'response': 'Por favor, escribe un mensaje.'})
    
    # Normalización del mensaje para búsqueda
    import unicodedata
    def normalizar(t):
        return "".join(
            c for c in unicodedata.normalize('NFD', t.lower())
            if unicodedata.category(c) != 'Mn'
        )
    
    msg_norm = normalizar(user_message)
    response = ""
    
    # 1. Crisis / Rabietas / Desregulación
    if any(k in msg_norm for k in ['crisis', 'rabieta', 'agresividad', 'enojo', 'llanto', 'grit', 'pegar', 'desregulacion', 'tranquil', 'calmar']):
        response = """
        <p><strong>🚨 Manejo de Crisis o Desregulación Conductual:</strong></p>
        <p>Cuando un niño con TEA se desregula, suele deberse a sobrecarga sensorial o frustración. Sigue estos pasos clave:</p>
        <ol>
            <li><strong>Mantén la calma y baja la voz:</strong> Tu estado emocional regula al niño. Habla con tono suave y calmado.</li>
            <li><strong>Crea un espacio seguro:</strong> Retira estímulos auditivos, visuales o físicos fuertes (luces intensas, ruidos).</li>
            <li><strong>Usa lenguaje claro y directo:</strong> Evita discursos largos. Usa frases simples de 2 o 3 palabras como: <em>"Estás a salvo"</em>, <em>"Respira"</em>.</li>
            <li><strong>No fuerces el contacto físico:</strong> Algunos niños se calman con un abrazo fuerte, pero otros sienten invasión sensorial. Observa su preferencia.</li>
            <li><strong>Ofrece elementos de calma:</strong> Juguetes sensoriales, mordedores o audífonos canceladores de ruido si hay mucha sobreestimulación.</li>
        </ol>
        """
    
    # 2. Comunicación / Habla / Pictogramas
    elif any(k in msg_norm for k in ['comunicacion', 'habla', 'lenguaje', 'no habla', 'expresar', 'pictograma', 'visual', 'agenda', 'entender']):
        response = """
        <p><strong>💬 Estrategias de Comunicación y Apoyo Visual:</strong></p>
        <p>Las personas con TEA procesan la información visual de forma mucho más efectiva que la auditiva:</p>
        <ul>
            <li><strong>Usa Pictogramas y Agendas Visuales:</strong> Diseña una secuencia diaria con imágenes de las actividades (ej: <em>desayuno ➔ escuela ➔ parque ➔ dormir</em>). Esto reduce significativamente la ansiedad.</li>
            <li><strong>Anticipación constante:</strong> Antes de cambiar de actividad, avísale visualmente: <em>"Faltan 5 minutos para guardar los juguetes"</em>.</li>
            <li><strong>Lenguaje literal y sin metáforas:</strong> Evita modismos, sarcasmos o ironías. Di exactamente lo que quieres decir.</li>
            <li><strong>Tiempo de procesamiento:</strong> Dale al niño entre 5 y 10 segundos para responder a una instrucción antes de repetirla.</li>
        </ul>
        """
        
    # 3. Interacción Social / Socializar / Compartir / Aislamiento
    elif any(k in msg_norm for k in ['social', 'interaccion', 'jugar', 'aisla', 'compartir', 'amigo', 'integracion', 'socializar']):
        response = """
        <p><strong>🤝 Fomento de la Interacción Social:</strong></p>
        <p>El desarrollo de habilidades sociales requiere de un modelaje explícito y estructurado:</p>
        <ul>
            <li><strong>Historias Sociales:</strong> Escribe pequeños cuentos ilustrados donde expliques situaciones comunes y conductas esperadas (ej. cómo saludar, cómo pedir un de juguete prestado).</li>
            <li><strong>Juego Estructurado:</strong> Inicia con juegos de causa y efecto o de turnos simples (lanzar pelota, armar torres por turnos) para enseñar la reciprocidad social de forma amena.</li>
            <li><strong>Respeta sus momentos de juego solitario:</strong> El juego libre individual es necesario para su autorregulación. No lo obligues a socializar continuamente si muestra fatiga social.</li>
        </ul>
        """
        
    # 4. DSM-5 / Niveles / Criterios diagnósticos
    elif any(k in msg_norm for k in ['dsm5', 'dsm-5', 'nivel', 'criterio', 'diagnostico', 'grado', 'evalua', 'clasificacion']):
        response = """
        <p><strong>🏥 Criterios y Niveles del DSM-5 para TEA:</strong></p>
        <p>El Manual DSM-5 clasifica el autismo bajo dos dominios principales:</p>
        <ol>
            <li><strong>Criterio A:</strong> Deficiencias persistentes en la comunicación e interacción social.</li>
            <li><strong>Criterio B:</strong> Patrones repetitivos y restringidos de comportamiento, intereses o actividades.</li>
        </ol>
        <p><strong>Niveles de Gravedad según el Apoyo requerido:</strong></p>
        <ul>
            <li><strong>Nivel 1 (Leve):</strong> Requiere apoyo. Puede comunicarse bien pero tiene problemas para iniciar interacciones o cambiar de tarea.</li>
            <li><strong>Nivel 2 (Moderado):</strong> Requiere apoyo sustancial. Presenta marcadas dificultades de comunicación verbal y no verbal, y gran resistencia a los cambios.</li>
            <li><strong>Nivel 3 (Severo):</strong> Requiere apoyo muy constante/sustancial. Déficit severo en la comunicación y conductas inflexibles que interfieren gravemente con la vida diaria.</li>
        </ul>
        """
        
    # 5. Ayuda general / Funcionalidades del sistema / Instrucciones
    elif any(k in msg_norm for k in ['ayuda', 'sistema', 'que haces', 'funciona', 'evaluar', 'registro', 'recomendacion', 'como uso', 'menu']):
        response = """
        <p><strong>🤖 ¡Hola! Soy tu Asistente Virtual de Apoyo TEA.</strong></p>
        <p>Puedo ayudarte con información pedagógica y a navegar el sistema. Aquí tienes lo que puedes hacer:</p>
        <ul>
            <li><strong>Registrar niños y representantes:</strong> Ve a <em>Gestión > Nuevo estudiante</em> en el menú lateral.</li>
            <li><strong>Realizar Evaluaciones:</strong> Entra al perfil de un estudiante y presiona <em>🏥 Evaluar</em>. Completarás la evaluación DSM-5 y luego la pedagógica para que el sistema experto genere recomendaciones.</li>
            <li><strong>Consultar la Base de Conocimientos:</strong> Visita <em>Sistema Experto > Base de conocimientos</em> para ver las reglas lógicas que rigen el motor de inferencia pedagógica.</li>
        </ul>
        <p>Pregúntame sobre <strong>crisis</strong>, <strong>comunicación</strong>, <strong>habilidades sociales</strong> o el <strong>DSM-5</strong> para recibir pautas educativas de inmediato.</p>
        """

    # 6. Apoyo Emocional / Estrés del Instructor (Pausa Activa / Respiración)
    elif any(k in msg_norm for k in ['estres', 'cansad', 'agobiad', 'triste', 'dificil', 'presion', 'agoto', 'frustrad', 'mal dia']):
        response = """
        <p><strong>🧘 Pausa de Apoyo e Inteligencia Emocional:</strong></p>
        <p>Sé que guiar y apoyar a niños con TEA puede ser física y emocionalmente agotador. ¡Tu dedicación es increíblemente valiosa! ❤️</p>
        <p>Hagamos juntos una breve pausa activa de respiración para liberar tensión:</p>
        <ol>
            <li>Inhala aire profundamente por la nariz durante <strong>4 segundos</strong>...</li>
            <li>Mantén el aire por <strong>4 segundos</strong>...</li>
            <li>Exhala lentamente por la boca durante <strong>4 segundos</strong>...</li>
            <li>Descansa por <strong>4 segundos</strong> y repite una vez más.</li>
        </ol>
        <p>¿Te sientes un poco mejor? Podemos seguir charlando sobre alguna recomendación pedagógica o sobre cómo te ha ido hoy. ¿Qué te gustaría hacer?</p>
        """

    # 7. Humor / Chistes (Interacción simpática)
    elif any(k in msg_norm for k in ['chiste', 'brom', 'gracios', 'divertid', 'reir']):
        response = """
        <p><strong>😄 ¡Un poco de humor para alegrar tu jornada!</strong></p>
        <p>Aquí tienes un chiste pedagógico y positivo:</p>
        <blockquote style="border-left: 3px solid var(--c-accent); padding-left: 10px; margin: 10px 0; color: var(--c-accent2);">
            ¿Qué le dice una pieza de rompecabezas a otra?<br>
            <em>— ¡Hacemos una pareja perfecta! 🧩</em>
        </blockquote>
        <p>O este otro:</p>
        <blockquote style="border-left: 3px solid var(--c-teal); padding-left: 10px; margin: 10px 0; color: var(--c-teal);">
            ¿Por qué los pájaros vuelan al sur en invierno?<br>
            <em>— ¡Porque caminar les tomaría demasiado tiempo! 🐦</em>
        </blockquote>
        <p>Reír un poco libera la tensión del aula. ¿De qué más te gustaría conversar?</p>
        """

    # 8. Motivación / Frases Inspiradoras
    elif any(k in msg_norm for k in ['motivacion', 'frase', 'inspiracion', 'aliento', 'quote', 'reflexion', 'consejo']):
        response = """
        <p><strong>✨ Frase Inspiradora para hoy:</strong></p>
        <blockquote style="border-left: 4px solid var(--c-green); padding-left: 12px; margin: 12px 0; font-style: italic; color: var(--c-text);">
            "El autismo no es una enfermedad que deba curarse, sino una forma diferente de comunicarse y experimentar el mundo que merece ser comprendida."
        </blockquote>
        <p>Y recuerda siempre esta hermosa pauta de Temple Grandin:</p>
        <blockquote style="border-left: 4px solid var(--c-accent); padding-left: 12px; margin: 12px 0; font-style: italic; color: var(--c-text);">
            "El mundo necesita todo tipo de mentes."
        </blockquote>
        <p>¡Gracias por ser ese puente de aprendizaje y comprensión para tus alumnos! ¿Quieres ver alguna estrategia o tienes alguna otra consulta?</p>
        """

    # 9. Compartir el Día / Progreso de Estudiantes
    elif any(k in msg_norm for k in ['jornada', 'clase', 'dia de hoy', 'mis estudiantes', 'alumno', 'avance', 'logro', 'progreso']):
        response = """
        <p><strong>❤️ ¡Gracias por compartirlo conmigo!</strong></p>
        <p>Cada pequeño avance en niños con TEA (como mantener el contacto visual por un segundo más, usar un nuevo pictograma para pedir algo, o calmar una rabieta de manera autónoma) es un paso gigante hacia su independencia.</p>
        <p>Tu paciencia y constancia marcan una diferencia real en sus vidas. ¿Hay algún tema o recomendación específica sobre el que te gustaría conversar ahora?</p>
        """

    # 10. Saludo e Interacción General
    elif any(k in msg_norm for k in ['hola', 'buenos dias', 'buenas tardes', 'buenas noches', 'saludos', 'hey', 'hello', 'como estas', 'que tal', 'como te va', 'todo bien']):
        response = """
        <p>👋 ¡Hola! Qué alegría saludarte. Estoy de maravilla y listo para apoyarte hoy. 😊</p>
        <p>Como tu asistente virtual de apoyo TEA, puedo guiarte con estrategias pedagógicas, responder dudas sobre el DSM-5, o simplemente charlar e intercambiar una frase motivadora si has tenido una jornada agotadora.</p>
        <p>Cuéntame, ¿cómo ha estado tu día con tus estudiantes hoy?</p>
        """
        
    # 11. Agradecimiento / Despedida
    elif any(k in msg_norm for k in ['gracias', 'gracia', 'adios', 'chao', 'despedida', 'ok', 'excelente', 'buenisimo']):
        response = """
        <p>¡De nada! Es un verdadero placer ser tu compañero de apoyo pedagógico. 🧩</p>
        <p>Si necesitas pautas sobre autismo, una pausa activa o solo una palabra de aliento, aquí estaré. ¡Que tengas un excelente día!</p>
        """

    # 12. Fallback general inteligente
    else:
        response = f"""
        <p>Interesante pregunta sobre <em>"{user_message}"</em>.</p>
        <p>Como sugerencia general para el aula o el hogar:</p>
        <ul>
            <li>Establece rutinas claras utilizando apoyos visuales (pictogramas).</li>
            <li>Identifica qué estímulos (ruidos, luces, texturas) pueden estar sobrecargando sensorialmente al niño.</li>
            <li>Refuerza positivamente cada pequeño logro que alcance para fomentar su motivación e independencia.</li>
        </ul>
        <p>Si deseas detalles específicos, prueba preguntándome sobre: <strong>crisis</strong>, <strong>pictogramas</strong>, <strong>habilidades sociales</strong> o <strong>DSM-5</strong>. También puedes pedirme un <strong>chiste</strong>, una <strong>frase de motivación</strong> o contarme cómo estuvo tu <strong>día</strong>. 😊</p>
        """
        
    return JsonResponse({'response': response})
