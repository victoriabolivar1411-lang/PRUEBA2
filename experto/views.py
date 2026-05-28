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
from django.db.models import Count, Q, Avg
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
import os
import base64
from django.conf import settings
from io import BytesIO
from django.template.loader import get_template
from xhtml2pdf import pisa
from .chatbot_engine import detectar_intencion, mensaje_bienvenida, generar_respuesta

from .models import (
    Instructor, Estudiante, Representante,
    EvaluacionDSM5, EvaluacionPedagogica, Recomendacion, Regla, Evaluacion
)
from .forms import (
    RegistroInstructorForm, EstudianteForm, RepresentanteForm,
    EvaluacionDSM5Form, EvaluacionPedagogicaForm,
    RecuperarContrasenaForm, VerificarCodigoForm,
    EditarPerfilInstructorForm,
)
from .expert_system import generar_recomendaciones
from .utils import buscar_logo_infocentro, generar_data_uri_imagen, enviar_bienvenida, render_reporte_con_membrete


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


def jugar_evaluar(request):
    return render(request, 'experto/jugar_evaluar.html')


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
def descargar_manual_pdf(request):
    logo_b64 = get_logo_b64()
    template_path = 'experto/manual_usuario_pdf.html'
    context = {
        'fecha': timezone.now().strftime('%d/%m/%Y'),
        'instructor': request.user.first_name or request.user.username,
        'logo_b64': logo_b64
    }
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="Manual_de_Uso_Sistema_TEA.pdf"'
    
    template = get_template(template_path)
    html = template.render(context)
    
    pisa_status = pisa.CreatePDF(
        html, dest=response, link_callback=link_callback
    )
    
    if pisa_status.err:
        return HttpResponse('Tuvimos errores generando el PDF <pre>' + html + '</pre>')
    return response


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

    logo_data_uri = None
    ruta_logo = buscar_logo_infocentro()
    if ruta_logo:
        logo_data_uri = generar_data_uri_imagen(ruta_logo)

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
        'logo_data_uri': logo_data_uri,
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
    logo_data_uri = None
    ruta_logo = buscar_logo_infocentro()
    if ruta_logo:
        logo_data_uri = generar_data_uri_imagen(ruta_logo)

    return render(request, 'experto/perfil_estudiante.html', {
        'instructor':       instructor,
        'estudiante':       est,
        'representante':    rep,
        'eval_dsm5':        eval_dsm5,
        'eval_ped':         eval_ped,
        'recomendaciones':  recomendaciones,
        'logo_data_uri':    logo_data_uri,
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
            
            # Generar evaluación de evolución automática para reflejar en el timeline
            pct_com = _nivel_a_puntaje(ev_ped.nivel_comunicacion_social)
            pct_con = _nivel_a_puntaje(ev_ped.nivel_conductas_repetitivas)
            
            Evaluacion.objects.create(
                estudiante=est,
                fecha=timezone.now().date(),
                nombre="Evaluación Pedagógica",
                tipo='TEA',
                puntaje_obtenido=float(pct_com + pct_con),
                puntaje_maximo=150.0,
                observaciones=f"Generada automáticamente a partir de la Evaluación Pedagógica #{ev_ped.pk}.\n"
                              f"Comunicación Social: {ev_ped.get_nivel_comunicacion_social_display()}.\n"
                              f"Conductas Repetitivas: {ev_ped.get_nivel_conductas_repetitivas_display()}."
            )
            
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

@login_required(login_url='login')
def editar_evaluacion_dsm5(request, pk, dsm5_pk):
    instructor = _get_instructor(request)
    est = get_object_or_404(Estudiante, pk=pk, instructor=instructor)
    ev_dsm5 = get_object_or_404(EvaluacionDSM5, pk=dsm5_pk, estudiante=est)

    if request.method == 'POST':
        form = EvaluacionDSM5Form(request.POST, instance=ev_dsm5)
        if form.is_valid():
            form.save()
            messages.success(request, 'Evaluación DSM-5 actualizada correctamente.')
            # Si hay una evaluación pedagógica asociada, ir a sus resultados
            ped = ev_dsm5.evaluaciones_pedagogicas.first()
            if ped:
                return redirect('resultados', ped_pk=ped.pk)
            return redirect('perfil_estudiante', pk=est.pk)
    else:
        form = EvaluacionDSM5Form(instance=ev_dsm5)
    return render(request, 'experto/evaluacion_dsm5.html', {
        'form': form, 'instructor': instructor, 'estudiante': est, 'editando': True
    })

@login_required(login_url='login')
def editar_evaluacion_pedagogica(request, pk, ped_pk):
    instructor = _get_instructor(request)
    est = get_object_or_404(Estudiante, pk=pk, instructor=instructor)
    ev_ped = get_object_or_404(EvaluacionPedagogica, pk=ped_pk, estudiante=est)

    if request.method == 'POST':
        form = EvaluacionPedagogicaForm(request.POST, instance=ev_ped)
        if form.is_valid():
            ev_ped = form.save()
            
            pct_com = _nivel_a_puntaje(ev_ped.nivel_comunicacion_social)
            pct_con = _nivel_a_puntaje(ev_ped.nivel_conductas_repetitivas)
            
            ev_evolucion = Evaluacion.objects.filter(
                estudiante=est,
                observaciones__startswith=f"Generada automáticamente a partir de la Evaluación Pedagógica #{ev_ped.pk}."
            ).first()

            if ev_evolucion:
                ev_evolucion.puntaje_obtenido = float(pct_com + pct_con)
                ev_evolucion.observaciones = f"Generada automáticamente a partir de la Evaluación Pedagógica #{ev_ped.pk}.\n" \
                                             f"Comunicación Social: {ev_ped.get_nivel_comunicacion_social_display()}.\n" \
                                             f"Conductas Repetitivas: {ev_ped.get_nivel_conductas_repetitivas_display()}."
                ev_evolucion.save()
            else:
                Evaluacion.objects.create(
                    estudiante=est,
                    fecha=ev_ped.fecha.date(),
                    nombre="Evaluación Pedagógica",
                    tipo='TEA',
                    puntaje_obtenido=float(pct_com + pct_con),
                    puntaje_maximo=150.0,
                    observaciones=f"Generada automáticamente a partir de la Evaluación Pedagógica #{ev_ped.pk}.\n"
                                  f"Comunicación Social: {ev_ped.get_nivel_comunicacion_social_display()}.\n"
                                  f"Conductas Repetitivas: {ev_ped.get_nivel_conductas_repetitivas_display()}."
                )

            ev_ped.recomendaciones.all().delete()
            reglas = generar_recomendaciones(ev_ped)
            messages.success(
                request,
                f'Evaluación pedagógica actualizada. Se generaron {len(reglas)} recomendación(es) actualizadas.'
            )
            return redirect('resultados', ped_pk=ev_ped.pk)
    else:
        form = EvaluacionPedagogicaForm(instance=ev_ped)
    return render(request, 'experto/evaluacion_pedagogica.html', {
        'form': form, 'instructor': instructor, 'estudiante': est, 'eval_dsm5': ev_ped.evaluacion_dsm5, 'editando': True
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

    logo_data_uri = None
    ruta_logo = buscar_logo_infocentro()
    if ruta_logo:
        logo_data_uri = generar_data_uri_imagen(ruta_logo)

    return render(request, 'experto/resultados.html', {
        'instructor':      instructor,
        'estudiante':      ev_ped.estudiante,
        'eval_ped':        ev_ped,
        'eval_dsm5':       ev_dsm5,
        'recomendaciones': recomendaciones,
        'total':           recomendaciones.count(),
        'logo_data_uri':   logo_data_uri,
    })


@login_required(login_url='login')
def reporte_pedagogico_html(request, ped_pk):
    """Genera una vista HTML imprimible con membrete para una evaluación pedagógica."""
    instructor = _get_instructor(request)
    ev_ped = get_object_or_404(
        EvaluacionPedagogica, pk=ped_pk, estudiante__instructor=instructor
    )
    recomendaciones = ev_ped.recomendaciones.select_related('regla').all()

    lineas = [
        f'Estudiante: {ev_ped.estudiante.nombre_completo}',
        f'Instructor: {instructor}',
        f'Fecha de evaluación: {ev_ped.fecha.strftime("%d/%m/%Y")}',
        '',
        'Datos de la evaluación pedagógica:',
        f'- Comunicación social: {ev_ped.get_nivel_comunicacion_social_display()}',
        f'- Observaciones comunicación: {ev_ped.observaciones_comunicacion or "Sin observaciones"}',
        f'- Conductas repetitivas: {ev_ped.get_nivel_conductas_repetitivas_display()}',
        f'- Observaciones conductas: {ev_ped.observaciones_conductas or "Sin observaciones"}',
        '',
        'Recomendaciones generadas:',
    ]

    if recomendaciones.exists():
        for rec in recomendaciones:
            regla_nombre = rec.regla.nombre if rec.regla else 'Recomendación'
            lineas.append(f'- {regla_nombre}: {rec.texto}')
    else:
        lineas.append('- No se encontraron recomendaciones generadas para esta evaluación.')

    contenido = '\n'.join(lineas)
    html = render_reporte_con_membrete(
        contenido,
        f'Reporte pedagógico — {ev_ped.estudiante.nombre_completo}'
    )
    return HttpResponse(html)


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


from django.contrib.staticfiles import finders

def link_callback(uri, rel):
    """
    Convierte URIs de HTML a rutas absolutas del sistema para que xhtml2pdf
    pueda acceder a los recursos estáticos.
    """
    result = finders.find(uri)
    if result:
        if not isinstance(result, (list, tuple)):
            result = [result]
        result = list(result)[0]
    else:
        sUrl = settings.STATIC_URL
        sRoot = settings.STATIC_ROOT
        mUrl = settings.MEDIA_URL
        mRoot = settings.MEDIA_ROOT

        if uri.startswith(mUrl):
            path = os.path.join(mRoot, uri.replace(mUrl, ""))
        elif uri.startswith(sUrl):
            path = os.path.join(sRoot, uri.replace(sUrl, ""))
        else:
            return uri
        result = path

    if not os.path.isfile(result):
        raise Exception(f'media URI must start with {sUrl} or {mUrl}')
    return result

def get_logo_b64():
    logo_path = os.path.join(settings.BASE_DIR, 'experto', 'static', 'images', 'logo_infocentro.jpeg')
    try:
        with open(logo_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return f"data:image/jpeg;base64,{encoded_string}"
    except Exception:
        return ""

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


def restablecer_contrasena(request):
    """
    Vista para manejar el flujo de restablecimiento de contraseña con código de 6 dígitos.
    """
    if request.method == 'POST':
        # --- PASO 1: El usuario solicita enviar el código a su correo ---
        if 'solicitar_codigo' in request.POST:
            email = request.POST.get('email')
            from django.contrib.auth.models import User
            
            usuarios = User.objects.filter(email__iexact=email)
            if not usuarios.exists():
                messages.error(request, 'No existe ningún usuario registrado con ese correo electrónico.')
                return render(request, 'experto/restablecer.html', {'paso': 'solicitar'})
            
            usuario = usuarios.first()
            if usuario:
                
                # Generar código de 6 dígitos
                codigo_verificacion = str(random.randint(100000, 999999))
                
                # Guardar el código y el email en la sesión (temporal)
                request.session['reset_codigo'] = codigo_verificacion
                request.session['reset_email'] = email
                
                # Configurar y enviar el correo
                from .utils import buscar_logo_infocentro
                from django.core.mail import EmailMultiAlternatives
                from email.mime.image import MIMEImage
                import os

                ruta_logo = buscar_logo_infocentro()
                
                nombre = usuario.first_name or usuario.username
                # Asunto único por envío y cálculo de hora usando la hora real del sistema
                from datetime import datetime
                ahora = datetime.now()
                hora_actual = ahora.strftime("%H:%M:%S")
                hora_expiracion = (ahora + timedelta(minutes=5)).strftime("%I:%M %p")
                asunto = f'Tu código de verificación - Sistema TEA ({hora_actual})'
                
                mensaje_texto = f'Hola {nombre},\n\nTu código de verificación para restablecer la contraseña es: {codigo_verificacion}\n\nEste código expira a las {hora_expiracion}.\n\nSi no solicitaste este cambio, ignora este correo.'
                
                # Generar las celdas individuales para cada dígito del código
                digitos_html = ''
                for digito in codigo_verificacion:
                    digitos_html += f'''<td align="center" style="width:40px;height:48px;background-color:#0c1628;border:1.5px solid #1e3a5f;border-radius:8px;font-size:22px;font-weight:700;color:#ffffff;font-family:'Courier New',Courier,monospace;letter-spacing:0;">{digito}</td>
                    <td width="6"></td>'''
                # Quitar el último separador
                digitos_html = digitos_html.rsplit('<td width="6"></td>', 1)[0]
                
                # HTML idéntico al diseño de referencia
                mensaje_html = f'''
                <div style="margin:0;padding:0;background-color:#070d1a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
                    <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color:#070d1a;">
                        <tr>
                            <td align="center" style="padding:30px 10px;">
                                
                                <table width="380" border="0" cellspacing="0" cellpadding="0" style="background-color:#0b1120;border-radius:16px;overflow:hidden;">
                                    
                                    <!-- LOGO INFOCENTRO con fondo oscuro -->
                                    <tr>
                                        <td align="center" style="background-color:#0b1120;padding:30px 30px 10px;border-radius:16px 16px 0 0;">
                                            <img src="cid:logo_infocentro" alt="INFOCENTRO" style="max-height:50px;display:block;border:0;background-color:transparent;border-radius:8px;" />
                                        </td>
                                    </tr>
                                    
                                    <!-- TÍTULO -->
                                    <tr>
                                        <td align="center" style="padding:28px 30px 20px;">
                                            <h1 style="color:#ffffff;font-size:20px;font-weight:700;margin:0;letter-spacing:-0.3px;">Tu código de verificación</h1>
                                        </td>
                                    </tr>
                                    
                                    <!-- CONTENIDO PRINCIPAL -->
                                    <tr>
                                        <td align="center" style="padding:0 30px;">
                                            
                                            <!-- Ícono candado -->
                                            <table border="0" cellspacing="0" cellpadding="0">
                                                <tr>
                                                    <td align="center" style="width:52px;height:52px;background-color:#1e6cb5;border-radius:50%;text-align:center;vertical-align:middle;">
                                                        <span style="font-size:22px;line-height:52px;">&#128274;</span>
                                                    </td>
                                                </tr>
                                            </table>
                                            
                                            <!-- Saludo -->
                                            <p style="font-size:15px;color:#e2e8f0;margin:18px 0 6px;">Hola <strong>{nombre}</strong>,</p>
                                            
                                            <!-- Descripción -->
                                            <p style="font-size:13px;color:#7a8ba5;margin:0 0 28px;line-height:1.6;">
                                                Recibimos una solicitud para restablecer<br>
                                                tu contraseña.<br>
                                                Ingresa el siguiente código en la pantalla<br>
                                                de verificación:
                                            </p>
                                            
                                        </td>
                                    </tr>
                                    
                                    <!-- CÓDIGO EN CAJAS INDIVIDUALES -->
                                    <tr>
                                        <td align="center" style="padding:0 25px 22px;">
                                            <table border="0" cellspacing="0" cellpadding="0" style="border:1.5px solid #1a2d4a;border-radius:10px;padding:12px 14px;background-color:#0a0f1e;">
                                                <tr>
                                                    {digitos_html}
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>
                                    
                                    <!-- BADGE DE EXPIRACIÓN -->
                                    <tr>
                                        <td align="center" style="padding:0 30px 30px;">
                                            <table border="0" cellspacing="0" cellpadding="0">
                                                <tr>
                                                    <td style="background-color:#0d1a2e;border:1px solid #1a2d4a;border-radius:20px;padding:8px 18px;">
                                                        <span style="font-size:12px;color:#4da6e8;font-weight:600;">&#9201; Este código expira a las {hora_expiracion}</span>
                                                    </td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>
                                    
                                    <!-- SEPARADOR Y PIE -->
                                    <tr>
                                        <td style="padding:0 30px;">                                            <div style="border-top:1px solid #1a2640;margin:0 0 18px;"></div>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td align="center" style="padding:0 30px 28px;">
                                            <p style="font-size:12px;color:#506070;margin:0;line-height:1.5;">
                                                ¿No solicitaste este cambio? No te preocupes,<br>
                                                puedes ignorar este correo de forma segura.
                                            </p>
                                        </td>
                                    </tr>
                                    
                                </table>
                                
                            </td>
                        </tr>
                    </table>
                </div>
                '''

                remitente = django_settings.EMAIL_HOST_USER
                destinatario = [email]
                
                # Usar EmailMultiAlternatives para incrustar la imagen del logo
                msg = EmailMultiAlternatives(asunto, mensaje_texto, remitente, destinatario)
                msg.attach_alternative(mensaje_html, "text/html")
                
                # Adjuntar la imagen con Content-ID para que Gmail la muestre inline
                if ruta_logo and os.path.isfile(ruta_logo):
                    with open(ruta_logo, 'rb') as f:
                        img_data = f.read()
                    img = MIMEImage(img_data)
                    img.add_header('Content-ID', '<logo_infocentro>')
                    img.add_header('Content-Disposition', 'inline', filename='logo_infocentro.jpeg')
                    msg.attach(img)
                
                msg.send(fail_silently=False)
                
                messages.success(request, 'Código enviado a tu correo. Por favor, revisa tu bandeja de entrada o spam.')
                return render(request, 'experto/restablecer.html', {'paso': 'verificar'})

        # --- PASO 2: El usuario ingresa el código y la nueva contraseña ---
        elif 'cambiar_contrasena' in request.POST:
            codigo_ingresado = request.POST.get('codigo')
            nueva_contrasena = request.POST.get('nueva_contrasena')
            confirmar_contrasena = request.POST.get('confirmar_contrasena')
            
            codigo_guardado = request.session.get('reset_codigo')
            email_guardado = request.session.get('reset_email')
            
            if not codigo_guardado or not email_guardado:
                messages.error(request, 'La sesión ha expirado o es inválida. Solicita un nuevo código.')
                return render(request, 'experto/restablecer.html', {'paso': 'solicitar'})
                
            if codigo_ingresado != codigo_guardado:
                messages.error(request, 'El código ingresado es incorrecto.')
                return render(request, 'experto/restablecer.html', {'paso': 'verificar'})
                
            if nueva_contrasena != confirmar_contrasena:
                messages.error(request, 'Las contraseñas no coinciden.')
                return render(request, 'experto/restablecer.html', {'paso': 'verificar'})
                
            # Todo correcto: Actualizar la contraseña
            from django.contrib.auth.models import User
            from django.contrib.auth.hashers import make_password
            
            usuarios = User.objects.filter(email__iexact=email_guardado)
            nueva_pass_hash = make_password(nueva_contrasena)
            for u in usuarios:
                u.password = nueva_pass_hash
                u.save()
                
            # Limpiar la sesión por seguridad
            if 'reset_codigo' in request.session:
                del request.session['reset_codigo']
            if 'reset_email' in request.session:
                del request.session['reset_email']
            
            messages.success(request, '¡Contraseña actualizada exitosamente! Ya puedes iniciar sesión.')
            return redirect('login')

    # Si es GET, mostramos el formulario inicial para solicitar el código
    return render(request, 'experto/restablecer.html', {'paso': 'solicitar'})


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


def _nivel_a_puntaje(nivel_str):
    """Convierte un nivel DSM-5 a un puntaje numérico inverso (mayor = mejor)."""
    mapa = {
        'necesita_apoyo':     75,   # Nivel 1 — leve
        'apoyo_sustancial':   50,   # Nivel 2 — moderado
        'apoyo_constante':    25,   # Nivel 3 — severo
        'necesita_ayuda':     75,
        'ayuda_notable':      50,
        'ayuda_muy_notable':  25,
    }
    return mapa.get(nivel_str, 50)


def _construir_timeline(estudiante):
    """
    Combina las evaluaciones de evolución del estudiante en un timeline unificado.
    Fuente única: Evaluacion (evolución).
    Retorna una lista de dicts ordenados por fecha.
    """
    timeline = []

    # ── 1. Evaluaciones de Evolución ───────────────────────────
    for ev in estudiante.evaluaciones_evolucion.all().order_by('fecha'):
        timeline.append({
            'fecha': ev.fecha,
            'nombre': ev.nombre,
            'tipo': ev.get_tipo_display(),
            'tipo_badge': 'badge-blue',
            'porcentaje': ev.porcentaje,
            'detalle': f'{ev.puntaje_obtenido}/{ev.puntaje_maximo}',
            'observaciones': ev.observaciones[:120] if ev.observaciones else '—',
            'pk': ev.pk,
            'modelo': 'evolucion',
        })

    # Ordenar cronológicamente
    timeline.sort(key=lambda x: x['fecha'])

    # Calcular tendencias
    prev_pct = None
    for item in timeline:
        if prev_pct is None:
            item['tendencia'] = 'Inicial'
            item['diff'] = 0.0
            item['color'] = '#3b82f6'
        else:
            diff = item['porcentaje'] - prev_pct
            item['diff'] = diff
            if diff >= 3:
                item['tendencia'] = f'+{diff:.1f}%'
                item['color'] = '#10b981'
            elif diff <= -3:
                item['tendencia'] = f'{diff:.1f}%'
                item['color'] = '#ef4444'
            else:
                item['tendencia'] = 'Estable'
                item['color'] = '#f59e0b'
        prev_pct = item['porcentaje']

    return timeline


@login_required(login_url='login')
def evolucion_estudiante(request, pk):
    """Vista principal: dashboard de evolución con gráfica Chart.js (sólo lectura)."""
    instructor  = _get_instructor(request)
    estudiante  = get_object_or_404(Estudiante, pk=pk, instructor=instructor)
    representante = getattr(estudiante, 'representante', None)

    # Construir timeline unificado
    timeline = _construir_timeline(estudiante)
    total_evals = len(timeline)

    # Métricas de resumen
    if total_evals > 0:
        puntajes = [item['porcentaje'] for item in timeline]
        promedio = round(sum(puntajes) / len(puntajes), 1)
        mejor_pct = max(puntajes)
        peor_pct = min(puntajes)
    else:
        promedio = 0
        mejor_pct = 0
        peor_pct = 0

    tendencia_general = "Sin datos"
    if total_evals >= 2:
        diff_total = timeline[-1]['porcentaje'] - timeline[0]['porcentaje']
        if diff_total >= 5:
            tendencia_general = "Positiva"
        elif diff_total <= -5:
            tendencia_general = "Negativa"
        else:
            tendencia_general = "Estable"
    elif total_evals == 1:
        tendencia_general = "Inicial"

    # Conteo por fuente
    n_dsm5 = 0
    n_ped  = 0
    n_evo  = total_evals

    logo_data_uri = None
    ruta_logo = buscar_logo_infocentro()
    if ruta_logo:
        logo_data_uri = generar_data_uri_imagen(ruta_logo)

    return render(request, 'experto/evolucion.html', {
        'instructor':       instructor,
        'estudiante':       estudiante,
        'representante':    representante,
        'timeline':         timeline,
        'total_evals':      total_evals,
        'promedio':         promedio,
        'mejor_pct':         mejor_pct,
        'peor_pct':         peor_pct,
        'tendencia_general': tendencia_general,
        'n_dsm5':           n_dsm5,
        'n_ped':            n_ped,
        'n_evo':            n_evo,
        'logo_data_uri':    logo_data_uri,
    })


@login_required(login_url='login')
def evolucion_data(request, pk):
    """API JSON: devuelve los datos para pintar la gráfica Chart.js."""
    instructor = _get_instructor(request)
    estudiante = get_object_or_404(Estudiante, pk=pk, instructor=instructor)
    timeline   = _construir_timeline(estudiante)

    data = {
        'fechas':     [item['fecha'].strftime('%d/%m') for item in timeline],
        'nombres':    [item['nombre']                      for item in timeline],
        'puntajes':   [item['porcentaje']                  for item in timeline],
        'colores':    [item['color']                       for item in timeline],
        'tendencias': [item['tendencia']                   for item in timeline],
        'tipos':      [item['tipo']                        for item in timeline],
        'promedio':   round(sum(i['porcentaje'] for i in timeline) / max(len(timeline), 1), 2),
    }
    return JsonResponse(data)


@login_required(login_url='login')
def evolucion_pdf(request, pk):
    """Genera y descarga el PDF del reporte de evolución."""
    instructor  = _get_instructor(request)
    estudiante  = get_object_or_404(Estudiante, pk=pk, instructor=instructor)
    representante = getattr(estudiante, 'representante', None)

    chart_image = request.POST.get('chart_image', '')

    timeline     = _construir_timeline(estudiante)
    total_evals  = len(timeline)

    if total_evals > 0:
        puntajes = [item['porcentaje'] for item in timeline]
        promedio = round(sum(puntajes) / len(puntajes), 1)
        mejor_pct = max(puntajes)
        peor_pct = min(puntajes)
    else:
        promedio = 0
        mejor_pct = 0
        peor_pct = 0

    tendencia_general = "Sin datos"
    if total_evals >= 2:
        diff_total = timeline[-1]['porcentaje'] - timeline[0]['porcentaje']
        tendencia_general = "Positiva" if diff_total >= 5 else ("Negativa" if diff_total <= -5 else "Estable")
    elif total_evals == 1:
        tendencia_general = "Inicial"

    logo_data_uri = None
    ruta_logo = buscar_logo_infocentro()
    if ruta_logo:
        logo_data_uri = generar_data_uri_imagen(ruta_logo)

    context = {
        'instructor':        instructor,
        'estudiante':        estudiante,
        'representante':     representante,
        'timeline':          timeline,
        'total_evals':       total_evals,
        'promedio':          promedio,
        'mejor_pct':         mejor_pct,
        'peor_pct':          peor_pct,
        'tendencia_general': tendencia_general,
        'chart_image':       chart_image,
        'fecha_reporte':     timezone.now().strftime('%d/%m/%Y %H:%M'),
        'logo_data_uri':     logo_data_uri,
    }

    template     = get_template('experto/evolucion_pdf.html')
    html_content = template.render(context)
    pdf_buffer   = BytesIO()
    pisa_status  = pisa.CreatePDF(html_content, dest=pdf_buffer, link_callback=link_callback)

    if pisa_status.err:
        return HttpResponse('Error al generar el PDF', status=500)

    pdf_buffer.seek(0)
    nombre_archivo = f"Evolucion_{estudiante.nombre_completo.replace(' ', '_')}.pdf"
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nombre_archivo}"'
    return response



@login_required
@require_POST
def guardar_tema(request):
    try:
        data = json.loads(request.body)
        tema = data.get('tema')
        if tema in ['light', 'dark']:
            instructor = _get_instructor(request)
            instructor.tema = tema
            instructor.save()
            return JsonResponse({'status': 'ok', 'tema': tema})
        return JsonResponse({'status': 'error', 'message': 'Tema invalido'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

