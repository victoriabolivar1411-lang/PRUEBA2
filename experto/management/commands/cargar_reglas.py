from django.core.management.base import BaseCommand
from experto.models import Regla
from experto.expert_system import REGLAS_INICIALES


def safe(text, length=60):
    """Convierte a ASCII seguro para terminales Windows cp1252."""
    return text[:length].encode('ascii', errors='replace').decode('ascii')


class Command(BaseCommand):
    help = 'Carga las reglas iniciales del sistema experto TEA (DSM-5).'

    def handle(self, *args, **options):
        self.stdout.write('--- Cargando Base de Conocimientos TEA ---')
        creadas = actualizadas = 0

        for i, datos in enumerate(REGLAS_INICIALES, 1):
            regla, created = Regla.objects.update_or_create(
                nombre=datos['nombre'],
                defaults={
                    'condicion':           datos['condicion'],
                    'recomendacion':       datos['recomendacion'],
                    'recursos_didacticos': datos.get('recursos_didacticos', ''),
                    'activa':              True,
                },
            )
            nombre_safe = safe(datos['nombre'])
            if created:
                creadas += 1
                self.stdout.write(self.style.SUCCESS(f'  [CREADA]      Regla {i}: {nombre_safe}'))
            else:
                actualizadas += 1
                self.stdout.write(self.style.WARNING(f'  [ACTUALIZADA] Regla {i}: {nombre_safe}'))

        self.stdout.write('')
        total = Regla.objects.filter(activa=True).count()
        self.stdout.write(self.style.SUCCESS(
            f'Completado: {creadas} creadas, {actualizadas} actualizadas. '
            f'Total activas: {total}'
        ))
