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
]
