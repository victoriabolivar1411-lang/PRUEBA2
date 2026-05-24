"""
=============================================================================
SISTEMA EXPERTO PARA APOYO PEDAGÓGICO EN TEA
=============================================================================
Módulo: experto/urls.py
=============================================================================
"""

from django.urls import path
from . import views

urlpatterns = [
    # ── Inicio ────────────────────────────────────────────────────────────────
    path('', views.inicio, name='inicio'),

    # ── Autenticación ─────────────────────────────────────────────────────────
    path('registro/', views.registro_instructor, name='registro_instructor'),
    path('login/',    views.login_view,          name='login'),
    path('logout/',   views.logout_view,         name='logout'),

    # ── Dashboard ─────────────────────────────────────────────────────────────
    path('dashboard/', views.dashboard, name='dashboard'),
    path('manual-usuario/pdf/', views.descargar_manual_pdf, name='descargar_manual_pdf'),

    # ── Estudiantes ───────────────────────────────────────────────────────────
    path('estudiantes/',                  views.lista_estudiantes,   name='lista_estudiantes'),
    path('estudiantes/nuevo/',            views.registro_estudiante, name='registro_estudiante'),
    path('estudiantes/<int:pk>/',         views.perfil_estudiante,   name='perfil_estudiante'),
    path('estudiantes/<int:pk>/editar/',  views.editar_estudiante,   name='editar_estudiante'),
    path('estudiantes/<int:pk>/borrar/',  views.borrar_estudiante,   name='borrar_estudiante'),

    # ── Representante ─────────────────────────────────────────────────────────
    path('estudiantes/<int:pk>/representante/', views.registro_representante, name='registro_representante'),

    # ── Evaluaciones ──────────────────────────────────────────────────────────
    path('estudiantes/<int:pk>/dsm5/',                            views.evaluacion_dsm5,       name='evaluacion_dsm5'),
    path('estudiantes/<int:pk>/pedagogica/<int:dsm5_pk>/',        views.evaluacion_pedagogica, name='evaluacion_pedagogica'),
    path('evaluaciones/<int:ped_pk>/resultados/',                 views.resultados,            name='resultados'),

    # ── Base de conocimientos ─────────────────────────────────────────────────
    path('base-conocimientos/', views.base_conocimientos, name='base_conocimientos'),

    # ── Perfil del instructor ──────────────────────────────────────────────────
    path('perfil/', views.perfil_instructor, name='perfil_instructor'),
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    path('instructores/<int:pk>/borrar/', views.borrar_instructor, name='borrar_instructor'),

    # ── Recuperación de contraseña personalizada ───────────────────────────────
    path('recuperar-contrasena/', views.recuperar_contrasena, name='recuperar_contrasena'),
    path('verificar-codigo/',     views.verificar_codigo,     name='verificar_codigo'),

    # ── Chatbot NLP ────────────────────────────────────────────────────────────
    path('chatbot/', views.chatbot_api, name='chatbot_api'),

    # ── Tema Claro / Oscuro ────────────────────────────────────────────────────
    path('guardar-tema/', views.guardar_tema, name='guardar_tema'),

    # ── Evolución del Estudiante ───────────────────────────────────────────────
    path('estudiante/<int:pk>/evolucion/',      views.evolucion_estudiante, name='evolucion_estudiante'),
    path('estudiante/<int:pk>/evolucion/data/', views.evolucion_data,       name='evolucion_data'),
    path('estudiante/<int:pk>/evolucion/pdf/',  views.evolucion_pdf,        name='evolucion_pdf'),
]
