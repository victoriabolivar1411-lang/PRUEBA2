from django.core.management.base import BaseCommand
from experto.models import Regla
from experto.expert_system import REGLAS_INICIALES


class Command(BaseCommand):
    help = 'Carga las reglas iniciales del sistema experto TEA en la base de datos.'

    def handle(self, *args, **options):
        self.stdout.write('--- SISTEMA EXPERTO TEA: Carga de Base de Conocimientos ---')

        creadas      = 0
        actualizadas = 0

        for i, datos in enumerate(REGLAS_INICIALES, 1):
            regla, created = Regla.objects.update_or_create(
                nombre=datos['nombre'],
                defaults={
                    'campo_condicion': datos['campo_condicion'],
                    'operador':        datos['operador'],
                    'valor_condicion': datos['valor_condicion'],
                    'accion':          datos['accion'],
                    'categoria':       datos['categoria'],
                    'prioridad':       datos['prioridad'],
                    'activa':          True,
                },
            )
            estado = 'CREADA' if created else 'ACTUALIZADA'
            # Usamos encode/decode para evitar UnicodeEncodeError en terminales cp1252
            msg = f'  [{estado}] Regla {i}: {datos["categoria"].upper()}'
            if created:
                creadas += 1
                self.stdout.write(self.style.SUCCESS(msg))
            else:
                actualizadas += 1
                self.stdout.write(self.style.WARNING(msg))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Completado: {creadas} reglas creadas, {actualizadas} actualizadas.'
        ))
