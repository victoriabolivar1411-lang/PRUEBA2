"""
=============================================================================
SISTEMA EXPERTO PARA APOYO PEDAGÓGICO EN TEA
=============================================================================
Módulo: utils.py
Descripción: Funciones auxiliares para el envío de correos electrónicos:
             bienvenida al registrarse y recuperación de contraseña.
=============================================================================
"""

import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

logger = logging.getLogger(__name__)


def enviar_bienvenida(user):
    """
    Envía un correo de bienvenida al instructor recién registrado.

    Args:
        user: instancia de django.contrib.auth.models.User
    """
    asunto = 'Bienvenido al Sistema Experto TEA'
    contexto = {
        'nombre': user.get_full_name() or user.username,
        'username': user.username,
        'email': user.email,
    }

    # Intenta renderizar el template HTML; si no existe, usa texto plano
    try:
        html_mensaje = render_to_string('experto/email/bienvenida.html', contexto)
        mensaje_texto = strip_tags(html_mensaje)
    except Exception:
        mensaje_texto = (
            f'Hola {contexto["nombre"]},\n\n'
            'Bienvenido al sistema experto TEA. Tu cuenta ha sido creada exitosamente.\n\n'
            f'Usuario: {contexto["username"]}\n\n'
            'Ahora puedes iniciar sesión y comenzar a registrar y evaluar a tus estudiantes.\n\n'
            '— Equipo del Sistema Experto TEA'
        )
        html_mensaje = None

    try:
        send_mail(
            subject=asunto,
            message=mensaje_texto,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_mensaje,
            fail_silently=False,
        )
        logger.info('Correo de bienvenida enviado a %s', user.email)
    except Exception as exc:
        logger.warning('No se pudo enviar correo de bienvenida: %s', exc)
