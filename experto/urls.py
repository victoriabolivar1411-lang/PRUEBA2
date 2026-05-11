"""
=============================================================================
SISTEMA EXPERTO PARA APOYO PEDAGÓGICO EN TEA
=============================================================================
Módulo: experto/urls.py
Descripción: URLs de la aplicación 'experto'. Define las rutas de todas
             las vistas del sistema experto.
=============================================================================
"""

from django.urls import path
from . import views

urlpatterns = [
    # ── Página de inicio ──────────────────────────────────────────────────────
    path('', views.inicio, name='inicio'),

    # ── Autenticación ─────────────────────────────────────────────────────────
    path('registro/', views.registro_instructor, name='registro_instructor'),
    path('login/',    views.login_view,           name='login'),
    path('logout/',   views.logout_view,          name='logout'),

    # ── Dashboard ─────────────────────────────────────────────────────────────
    path('dashboard/', views.dashboard, name='dashboard'),

    # ── Estudiantes ───────────────────────────────────────────────────────────
    path('estudiantes/',             views.lista_estudiantes,  name='lista_estudiantes'),
    path('estudiantes/nuevo/',       views.registro_estudiante, name='registro_estudiante'),
    path('estudiantes/<int:pk>/',    views.detalle_estudiante,  name='detalle_estudiante'),

    # ── Evaluación y motor de inferencia ─────────────────────────────────────
    path('estudiantes/<int:estudiante_pk>/evaluar/', views.nueva_evaluacion, name='nueva_evaluacion'),
    path('evaluaciones/<int:evaluacion_pk>/resultados/', views.resultados, name='resultados'),
    path('evaluaciones/historial/', views.historial_evaluaciones, name='historial_evaluaciones'),

    # ── Base de conocimientos ─────────────────────────────────────────────────
    path('base-conocimientos/', views.base_conocimientos, name='base_conocimientos'),
]
