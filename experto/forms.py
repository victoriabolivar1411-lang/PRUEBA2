"""
=============================================================================
SISTEMA EXPERTO PARA APOYO PEDAGÓGICO EN TEA
=============================================================================
Módulo: forms.py
Descripción: Formularios Django para el sistema experto TEA.
=============================================================================
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Instructor, Estudiante, Representante, EvaluacionDSM5, EvaluacionPedagogica


CSS = 'form-input'
CSS_AREA = 'form-textarea'
CSS_CHECK = 'form-checkbox'
CSS_FILE = 'form-file'


def _apply_css(form):
    for name, field in form.fields.items():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            widget.attrs.setdefault('class', CSS_CHECK)
        elif isinstance(widget, forms.Textarea):
            widget.attrs.setdefault('class', CSS_AREA)
        elif isinstance(widget, forms.ClearableFileInput):
            widget.attrs.setdefault('class', CSS_FILE)
        else:
            widget.attrs.setdefault('class', CSS)


# ─────────────────────────────────────────────────────────────────────────────
# 1. REGISTRO DE INSTRUCTOR
# ─────────────────────────────────────────────────────────────────────────────

class RegistroInstructorForm(UserCreationForm):
    """
    Crea el User de Django y el perfil Instructor.
    Envía correo de bienvenida al registrarse.
    """
    first_name = forms.CharField(max_length=100, label='Nombre', required=True)
    last_name  = forms.CharField(max_length=100, label='Apellido', required=True)
    email      = forms.EmailField(label='Correo electrónico', required=True)
    telefono   = forms.CharField(max_length=20, label='Teléfono (opcional)', required=False)

    class Meta:
        model  = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label     = 'Nombre de usuario'
        self.fields['username'].help_text = 'Solo letras, dígitos y @/./+/-/_'
        self.fields['password1'].label    = 'Contraseña'
        self.fields['password2'].label    = 'Confirmar contraseña'
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''
        _apply_css(self)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con este correo electrónico.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name  = self.cleaned_data['last_name']
        user.email      = self.cleaned_data['email']
        if commit:
            user.save()
            Instructor.objects.create(
                usuario=user,
                telefono=self.cleaned_data.get('telefono', ''),
            )
        return user


# ─────────────────────────────────────────────────────────────────────────────
# 2. REGISTRO DE ESTUDIANTE
# ─────────────────────────────────────────────────────────────────────────────

class EstudianteForm(forms.ModelForm):
    class Meta:
        model  = Estudiante
        fields = ['nombre_completo', 'sexo', 'edad', 'foto_carnet']
        widgets = {
            'foto_carnet': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }
        labels = {
            'nombre_completo': 'Nombre completo',
            'sexo':            'Sexo',
            'edad':            'Edad (años)',
            'foto_carnet':     'Foto carnet (opcional)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_css(self)


# ─────────────────────────────────────────────────────────────────────────────
# 3. REGISTRO DE REPRESENTANTE
# ─────────────────────────────────────────────────────────────────────────────

class RepresentanteForm(forms.ModelForm):
    class Meta:
        model  = Representante
        fields = [
            'nombre_completo', 'sexo', 'edad', 'estado_civil',
            'cedula', 'parentesco',
            'correo', 'telefono', 'direccion', 'foto_carnet',
        ]
        widgets = {
            'direccion':   forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Calle principal #123, Ciudad, País',
                'class': 'form-textarea direccion-field',
            }),
            'cedula':      forms.TextInput(attrs={
                'placeholder': 'Ej: 1234567890',
                'maxlength': '15',
            }),
            'foto_carnet': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }
        labels = {
            'nombre_completo': 'Nombre completo',
            'sexo':            'Sexo',
            'edad':            'Edad (años)',
            'estado_civil':    'Estado civil',
            'cedula':          'Cédula',
            'parentesco':      'Parentesco con el estudiante',
            'correo':          'Correo electrónico (opcional)',
            'telefono':        'Teléfono',
            'direccion':       'Dirección',
            'foto_carnet':     'Foto carnet (opcional)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_css(self)
        # Sobrescribir clase del textarea dirección para mantener estilos personalizados
        self.fields['direccion'].widget.attrs['class'] = 'form-textarea direccion-field'

    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula', '').strip()
        if not cedula.isdigit():
            raise forms.ValidationError('La cédula debe contener solo números.')
        qs = Representante.objects.filter(cedula=cedula)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Ya existe un representante registrado con esta cédula.')
        return cedula


# ─────────────────────────────────────────────────────────────────────────────
# 4. EVALUACIÓN DSM-5
# ─────────────────────────────────────────────────────────────────────────────

class EvaluacionDSM5Form(forms.ModelForm):
    class Meta:
        model  = EvaluacionDSM5
        exclude = ['estudiante', 'fecha']
        widgets = {
            'obs_reciprocidad':          forms.Textarea(attrs={'rows': 3}),
            'obs_comunicacion_no_verbal': forms.Textarea(attrs={'rows': 3}),
            'obs_desarrollo_relaciones':  forms.Textarea(attrs={'rows': 3}),
            'condicion_medica_asociada':  forms.TextInput(),
        }
        labels = {
            'nivel_comunicacion_social':   'Nivel de afectación — Comunicación Social',
            'obs_reciprocidad':            'A.1 Reciprocidad socioemocional (observaciones)',
            'obs_comunicacion_no_verbal':  'A.2 Comunicación no verbal (observaciones)',
            'obs_desarrollo_relaciones':   'A.3 Desarrollo, mantenimiento y comprensión de relaciones',
            'nivel_conductas_repetitivas': 'Nivel de afectación — Conductas repetitivas',
            'movimientos_repetitivos':     'B.1 Movimientos, uso de objetos o habla estereotipada',
            'inflexibilidad_rutinas':      'B.2 Insistencia en la monotonía / inflexibilidad de rutinas',
            'intereses_restringidos':      'B.3 Intereses muy restringidos y fijos',
            'alteraciones_sensoriales':    'B.4 Hiper o hiporreactividad sensorial',
            'inicio_temprano':             'C — Síntomas presentes en las primeras fases del desarrollo',
            'deterioro_significativo':     'D — Causa deterioro clínicamente significativo',
            'no_explicado_otra_condicion': 'E — No se explica mejor por discapacidad intelectual',
            'discapacidad_intelectual':    'Con discapacidad intelectual acompañante',
            'deterioro_lenguaje':          'Con deterioro del lenguaje acompañante',
            'condicion_medica_asociada':   'Afección médica o genética asociada (opcional)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_css(self)

    def clean(self):
        cleaned = super().clean()
        total_b = sum([
            cleaned.get('movimientos_repetitivos', False),
            cleaned.get('inflexibilidad_rutinas', False),
            cleaned.get('intereses_restringidos', False),
            cleaned.get('alteraciones_sensoriales', False),
        ])
        if total_b < 2:
            self.add_error(
                None,
                'El Criterio B requiere que al menos 2 de los 4 comportamientos estén presentes.'
            )
        return cleaned


# ─────────────────────────────────────────────────────────────────────────────
# 5. EVALUACIÓN PEDAGÓGICA
# ─────────────────────────────────────────────────────────────────────────────

class EvaluacionPedagogicaForm(forms.ModelForm):
    class Meta:
        model  = EvaluacionPedagogica
        fields = [
            'nivel_comunicacion_social', 'observaciones_comunicacion',
            'nivel_conductas_repetitivas', 'observaciones_conductas',
        ]
        widgets = {
            'observaciones_comunicacion': forms.Textarea(attrs={'rows': 3}),
            'observaciones_conductas':    forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'nivel_comunicacion_social':   'Nivel — Área 1: Comunicación Social',
            'observaciones_comunicacion':  'Observaciones de comunicación social',
            'nivel_conductas_repetitivas': 'Nivel — Área 2: Conductas repetitivas',
            'observaciones_conductas':     'Observaciones de conductas repetitivas',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_css(self)
