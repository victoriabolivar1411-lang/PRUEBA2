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


def enviar_codigo_sms(telefono, codigo):
    """
    Envía el código de recuperación mediante SMS usando la API de Twilio.
    """
    import urllib.request
    import urllib.parse
    import base64

    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
    from_number = getattr(settings, 'TWILIO_FROM_NUMBER', '')
    
    if not account_sid or not auth_token or not from_number:
        logger.warning("Twilio SMS no está configurado.")
        return False, "Twilio SMS no está configurado en settings o .env"
        
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    
    # Formatear el número de teléfono de destino
    to_number = telefono.strip()
    # Eliminar cualquier carácter que no sea dígito ni '+'
    to_number = '+' + ''.join(filter(str.isdigit, to_number)) if to_number.startswith('+') else ''.join(filter(str.isdigit, to_number))
    
    if not to_number.startswith('+'):
        # Si es de Venezuela (por ejemplo, empieza por 0412, 0414, 0416, 0424, 0426 o 412...)
        if to_number.startswith('0'):
            to_number = '+58' + to_number[1:]
        elif to_number.startswith('4'):
            to_number = '+58' + to_number
        else:
            to_number = '+' + to_number

    body = f"[TEA] Tu codigo de recuperacion de contrasena es: {codigo}"
    
    data = urllib.parse.urlencode({
        'From': from_number,
        'To': to_number,
        'Body': body
    }).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, method='POST')
    
    # Autenticación Básica
    auth_str = f"{account_sid}:{auth_token}"
    auth_b64 = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
    req.add_header("Authorization", f"Basic {auth_b64}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = response.read().decode('utf-8')
            logger.info("SMS enviado correctamente: %s", res_data)
            return True, "SMS enviado correctamente."
    except Exception as e:
        logger.error("Error al enviar SMS por Twilio: %s", e)
        return False, str(e)


def enviar_codigo_whatsapp(telefono, codigo):
    """
    Envía el código de recuperación mediante WhatsApp usando la API de Twilio o UltraMsg.
    """
    import urllib.request
    import urllib.parse
    import base64

    # 1. Intentar con UltraMsg
    instance_id = getattr(settings, 'ULTRAMSG_INSTANCE_ID', '')
    token = getattr(settings, 'ULTRAMSG_TOKEN', '')
    
    # Formatear el número de teléfono
    to_number = telefono.strip()
    to_number = '+' + ''.join(filter(str.isdigit, to_number)) if to_number.startswith('+') else ''.join(filter(str.isdigit, to_number))
    
    if not to_number.startswith('+'):
        if to_number.startswith('0'):
            to_number = '58' + to_number[1:]
        elif to_number.startswith('4'):
            to_number = '58' + to_number
        else:
            to_number = to_number
    else:
        to_number = to_number.replace('+', '')

    body_text = f"[TEA] Tu código de recuperación de contraseña es: {codigo}. Expira en 10 minutos."

    if instance_id and token:
        url = f"https://api.ultramsg.com/{instance_id}/messages/chat"
        data = urllib.parse.urlencode({
            'token': token,
            'to': to_number,
            'body': body_text
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = response.read().decode('utf-8')
                logger.info("WhatsApp enviado correctamente por UltraMsg: %s", res_data)
                return True, "WhatsApp enviado por UltraMsg."
        except Exception as e:
            logger.error("Error al enviar WhatsApp por UltraMsg: %s", e)
            return False, f"UltraMsg error: {e}"

    # 2. Intentar con Twilio WhatsApp
    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
    whatsapp_from = getattr(settings, 'TWILIO_WHATSAPP_FROM', '')

    if account_sid and auth_token and whatsapp_from:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        
        to_number_formatted = to_number
        if not to_number_formatted.startswith('+'):
            to_number_formatted = '+' + to_number_formatted
        to_number_whatsapp = f"whatsapp:{to_number_formatted}"
        
        data = urllib.parse.urlencode({
            'From': whatsapp_from,
            'To': to_number_whatsapp,
            'Body': body_text
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, method='POST')
        
        auth_str = f"{account_sid}:{auth_token}"
        auth_b64 = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
        req.add_header("Authorization", f"Basic {auth_b64}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = response.read().decode('utf-8')
                logger.info("WhatsApp enviado correctamente por Twilio: %s", res_data)
                return True, "WhatsApp enviado por Twilio."
        except Exception as e:
            logger.error("Error al enviar WhatsApp por Twilio: %s", e)
            return False, f"Twilio WhatsApp error: {e}"

    return False, "WhatsApp no está configurado (UltraMsg o Twilio WhatsApp)."
