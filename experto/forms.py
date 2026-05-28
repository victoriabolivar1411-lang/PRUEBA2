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
from .models import Instructor, Estudiante, Representante, EvaluacionDSM5, EvaluacionPedagogica, SEXO_CHOICES, ESTADO_CIVIL_CHOICES


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
        # Añadir atributo HTML required para todos los campos obligatorios
        # (activa la validación nativa del navegador antes de enviar)
        if field.required and not isinstance(widget, forms.CheckboxInput):
            widget.attrs['required'] = True


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
    sexo       = forms.ChoiceField(choices=SEXO_CHOICES, label='Sexo', required=True)
    edad       = forms.IntegerField(label='Edad (años)', min_value=18, required=True)
    estado_civil = forms.ChoiceField(choices=ESTADO_CIVIL_CHOICES, label='Estado civil', required=True)
    cedula     = forms.CharField(max_length=15, label='Cédula', required=True, widget=forms.TextInput(attrs={'placeholder': 'Ej: 12345678'}))
    email      = forms.EmailField(label='Correo electrónico', required=True)
    telefono   = forms.CharField(max_length=20, label='Teléfono', required=True)
    foto_perfil = forms.ImageField(label='Foto de perfil', required=True, widget=forms.ClearableFileInput(attrs={'accept': 'image/*'}))
    estado     = forms.CharField(label='Estado', required=True, widget=forms.Select(attrs={'class': 'form-input estado-select'}))
    municipio  = forms.CharField(label='Municipio / Ciudad', required=True, widget=forms.Select(attrs={'class': 'form-input municipio-select'}))
    direccion  = forms.CharField(label='Dirección detallada', required=True, widget=forms.Textarea(attrs={'rows': 3}))
    respuesta_1 = forms.CharField(max_length=200, label='¿Cuál es el nombre de tu primera mascota? *', required=True, widget=forms.TextInput(attrs={'placeholder': 'Respuesta a la pregunta 1'}))
    respuesta_2 = forms.CharField(max_length=200, label='¿En qué ciudad naciste? *', required=True, widget=forms.TextInput(attrs={'placeholder': 'Respuesta a la pregunta 2'}))
    respuesta_3 = forms.CharField(max_length=200, label='¿Cuál es tu comida favorita? *', required=True, widget=forms.TextInput(attrs={'placeholder': 'Respuesta a la pregunta 3'}))

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

    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula', '').strip()
        if not cedula.isdigit():
            raise forms.ValidationError('La cédula debe contener solo números.')
        if Instructor.objects.filter(cedula=cedula).exists():
            raise forms.ValidationError('Ya existe una cuenta registrada con esta cédula.')
        return cedula

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name  = self.cleaned_data['last_name']
        user.email      = self.cleaned_data['email']
        if commit:
            user.save()
            Instructor.objects.create(
                usuario=user,
                sexo=self.cleaned_data['sexo'],
                edad=self.cleaned_data['edad'],
                estado_civil=self.cleaned_data['estado_civil'],
                cedula=self.cleaned_data['cedula'],
                estado=self.cleaned_data['estado'],
                municipio=self.cleaned_data['municipio'],
                direccion=self.cleaned_data['direccion'],
                telefono=self.cleaned_data['telefono'],
                foto_perfil=self.cleaned_data.get('foto_perfil'),
                respuesta_1=self.cleaned_data['respuesta_1'].strip(),
                respuesta_2=self.cleaned_data['respuesta_2'].strip(),
                respuesta_3=self.cleaned_data['respuesta_3'].strip(),
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
            'foto_carnet':     'Foto carnet',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['foto_carnet'].required = True
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
            'correo', 'telefono', 'estado', 'municipio', 'direccion', 'foto_carnet',
        ]
        widgets = {
            'estado':      forms.Select(attrs={'class': 'form-input estado-select'}),
            'municipio':   forms.Select(attrs={'class': 'form-input municipio-select'}),
            'direccion':   forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Ej. Calle principal, Casa #123, Urb. Centro',
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
            'correo':          'Correo electrónico',
            'telefono':        'Teléfono',
            'estado':          'Estado',
            'municipio':       'Municipio / Ciudad',
            'direccion':       'Dirección detallada',
            'foto_carnet':     'Foto carnet',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['correo'].required = True
        self.fields['telefono'].required = True
        self.fields['foto_carnet'].required = True
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
            'condicion_medica_asociada':  forms.TextInput(),
        }
        labels = {
            'nivel_comunicacion_social':   'Nivel general de afectación — Comunicación Social',
            'a1_reciprocidad':             'A.1 — Deficiencias en la reciprocidad socioemocional',
            'a1_observaciones':            'A.1 Observaciones (Opcional)',
            'a2_comunicacion_no_verbal':   'A.2 — Deficiencias en conductas comunicativas no verbales',
            'a2_observaciones':            'A.2 Observaciones (Opcional)',
            'a3_relaciones':               'A.3 — Deficiencias en desarrollo, mantenimiento y comprensión de relaciones',
            'a3_observaciones':            'A.3 Observaciones (Opcional)',
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
            'asociado_trastorno_neurodesarrollo': 'Asociado a otro trastorno del neurodesarrollo, mental o del comportamiento',
            'con_catatonia':               'Con catatonía',
            'perdida_habilidades':         'Pérdida de habilidades previamente adquiridas',
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


# ─────────────────────────────────────────────────────────────────────────────
# 6. EDITAR PERFIL DEL INSTRUCTOR
# ─────────────────────────────────────────────────────────────────────────────

class EditarPerfilInstructorForm(forms.Form):
    first_name = forms.CharField(
        max_length=80, label='Nombre(s)',
        widget=forms.TextInput(attrs={'placeholder': 'Tu nombre'}),
    )
    last_name = forms.CharField(
        max_length=80, label='Apellido(s)',
        widget=forms.TextInput(attrs={'placeholder': 'Tus apellidos'}),
    )
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={'placeholder': 'tu@correo.com'}),
        required=False,
    )
    sexo = forms.ChoiceField(choices=SEXO_CHOICES, label='Sexo', required=True)
    edad = forms.IntegerField(label='Edad (años)', min_value=18, required=True)
    estado_civil = forms.ChoiceField(choices=ESTADO_CIVIL_CHOICES, label='Estado civil', required=True)
    cedula = forms.CharField(max_length=15, label='Cédula', required=True)
    telefono = forms.CharField(
        max_length=20, label='Teléfono', required=False,
        widget=forms.TextInput(attrs={'placeholder': '+58 412 000 0000'}),
    )
    estado = forms.CharField(label='Estado', required=True, widget=forms.Select(attrs={'class': 'form-input estado-select'}))
    municipio = forms.CharField(label='Municipio / Ciudad', required=True, widget=forms.Select(attrs={'class': 'form-input municipio-select'}))
    direccion = forms.CharField(label='Dirección detallada', required=True, widget=forms.Textarea(attrs={'rows': 3}))
    foto_perfil = forms.ImageField(
        label='Foto de perfil', required=False,
        widget=forms.FileInput(),
    )
    respuesta_1 = forms.CharField(
        max_length=200, label='¿Cuál es el nombre de tu primera mascota? *', required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Respuesta a la pregunta 1'}),
    )
    respuesta_2 = forms.CharField(
        max_length=200, label='¿En qué ciudad naciste? *', required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Respuesta a la pregunta 2'}),
    )
    respuesta_3 = forms.CharField(
        max_length=200, label='¿Cuál es tu comida favorita? *', required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Respuesta a la pregunta 3'}),
    )
    eliminar_foto = forms.BooleanField(
        label='Eliminar foto actual', required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_css(self)
        # El input de archivo no necesita la clase form-input
        self.fields['foto_perfil'].widget.attrs['class'] = ''
        self.fields['eliminar_foto'].widget.attrs['class'] = 'form-checkbox'


# ─────────────────────────────────────────────────────────────────────────────
# 7. RECUPERAR CONTRASEÑA — Solicitar código
# ─────────────────────────────────────────────────────────────────────────────

class RecuperarContrasenaForm(forms.Form):
    usuario_o_cedula = forms.CharField(
        label='Nombre de usuario o Cédula',
        widget=forms.TextInput(attrs={'placeholder': 'Tu nombre de usuario o cédula'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_css(self)


# ─────────────────────────────────────────────────────────────────────────────
# 7. VERIFICAR CÓDIGO Y NUEVA CONTRASEÑA
# ─────────────────────────────────────────────────────────────────────────────

class VerificarCodigoForm(forms.Form):
    codigo = forms.CharField(
        max_length=6,
        label='Código de verificación (6 dígitos)',
        widget=forms.TextInput(attrs={'placeholder': '123456', 'maxlength': '6'}),
    )
    nueva_contrasena = forms.CharField(
        label='Nueva contraseña',
        widget=forms.PasswordInput(attrs={'placeholder': 'Mínimo 8 caracteres'}),
        min_length=8,
    )
    confirmar_contrasena = forms.CharField(
        label='Confirmar nueva contraseña',
        widget=forms.PasswordInput(attrs={'placeholder': 'Repite la contraseña'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_css(self)

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('nueva_contrasena')
        p2 = cleaned.get('confirmar_contrasena')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Las contraseñas no coinciden.')
        return cleaned
