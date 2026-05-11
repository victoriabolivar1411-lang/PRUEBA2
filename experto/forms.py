"""
=============================================================================
SISTEMA EXPERTO PARA APOYO PEDAGÓGICO EN TEA
=============================================================================
Módulo: forms.py
Descripción: Formularios Django para el registro de instructores, estudiantes
             y la realización de evaluaciones pedagógicas.
=============================================================================
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Instructor, Estudiante, Evaluacion


# ─────────────────────────────────────────────
# FORMULARIO DE REGISTRO DE INSTRUCTOR
# ─────────────────────────────────────────────

class RegistroInstructorForm(UserCreationForm):
    """
    Formulario combinado: crea el User de Django y el perfil Instructor
    asociado en un solo paso. Extiende UserCreationForm para incluir
    validación de contraseña nativa de Django.
    """
    first_name   = forms.CharField(max_length=100, label='Nombre', required=True)
    last_name    = forms.CharField(max_length=100, label='Apellido', required=True)
    email        = forms.EmailField(label='Correo electrónico', required=True)
    telefono     = forms.CharField(max_length=20, label='Teléfono', required=False)
    especialidad = forms.CharField(max_length=100, label='Especialidad / Cargo', required=False)

    class Meta:
        model  = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalización de labels y ayudas
        self.fields['username'].label      = 'Nombre de usuario'
        self.fields['username'].help_text  = 'Solo letras, dígitos y @/./+/-/_'
        self.fields['password1'].label     = 'Contraseña'
        self.fields['password2'].label     = 'Confirmar contraseña'
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''
        # Clases CSS para estilizar con Bootstrap-like en la plantilla
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-input'

    def save(self, commit=True):
        """Guarda el User y crea automáticamente el perfil Instructor."""
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name  = self.cleaned_data['last_name']
        user.email      = self.cleaned_data['email']
        if commit:
            user.save()
            Instructor.objects.create(
                usuario=user,
                telefono=self.cleaned_data.get('telefono', ''),
                especialidad=self.cleaned_data.get('especialidad', ''),
            )
        return user


# ─────────────────────────────────────────────
# FORMULARIO DE REGISTRO DE ESTUDIANTE
# ─────────────────────────────────────────────

class EstudianteForm(forms.ModelForm):
    """
    Formulario para registrar o editar un estudiante con TEA.
    El campo 'instructor' se asigna automáticamente en la vista.
    """

    class Meta:
        model  = Estudiante
        fields = ['nombre', 'apellido', 'fecha_nacimiento', 'nivel_tea', 'observaciones']
        widgets = {
            'fecha_nacimiento': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-input'}
            ),
            'observaciones': forms.Textarea(
                attrs={'rows': 3, 'class': 'form-input', 'placeholder': 'Observaciones generales del estudiante...'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'observaciones' and 'fecha_nacimiento' not in name:
                field.widget.attrs['class'] = 'form-input'


# ─────────────────────────────────────────────
# FORMULARIO DE EVALUACIÓN PEDAGÓGICA
# ─────────────────────────────────────────────

NIVEL_CHOICES_FORM = [
    ('', '--- Seleccionar ---'),
    ('bajo', 'Bajo'),
    ('medio', 'Medio'),
    ('alto', 'Alto'),
]


class EvaluacionForm(forms.ModelForm):
    """
    Formulario para registrar la evaluación de un estudiante en las tres
    áreas clave: comunicación, conducta e interacción social.
    Este formulario alimenta directamente al motor de inferencia.
    """

    class Meta:
        model  = Evaluacion
        fields = [
            'dificultad_comunicacion',
            'usa_lenguaje_verbal',
            'conductas_repetitivas',
            'reacciones_sensoriales',
            'crisis_frecuentes',
            'interaccion_social',
            'interes_pares',
            'notas_adicionales',
        ]
        widgets = {
            'notas_adicionales': forms.Textarea(
                attrs={'rows': 3, 'class': 'form-input', 'placeholder': 'Observaciones adicionales de la evaluación...'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Selects con placeholder
        for campo in ['dificultad_comunicacion', 'conductas_repetitivas', 'reacciones_sensoriales', 'interaccion_social']:
            self.fields[campo].widget = forms.Select(
                choices=NIVEL_CHOICES_FORM,
                attrs={'class': 'form-input'},
            )
        # Checkboxes estilizados
        for campo in ['usa_lenguaje_verbal', 'crisis_frecuentes', 'interes_pares']:
            self.fields[campo].widget.attrs['class'] = 'form-checkbox'
