from django.core.management.base import BaseCommand

from alerts.engine import evaluate_all


class Command(BaseCommand):
    help = (
        "Évalue les règles d'alerte de toutes les exploitations actives et les rappels de validation. "
        "À planifier une fois par jour (Planificateur de tâches Windows ou cron)."
    )

    def handle(self, *args, **options):
        totals = evaluate_all()
        self.stdout.write(
            self.style.SUCCESS(
                f"{totals['farms']} exploitation(s) évaluée(s) : {totals['created']} alerte(s) créée(s), "
                f"{totals['updated']} mise(s) à jour, {totals['resolved']} résolue(s) automatiquement."
            )
        )
