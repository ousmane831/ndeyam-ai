import os
import secrets

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core import demo_data


class Command(BaseCommand):
    help = (
        "Charge le jeu de données de DÉMONSTRATION (comptes, exploitations, animaux, pesées, "
        "référentiel fictif, formules, rations, alertes, document). Toutes ces données sont "
        "marquées DEMO et ne sont jamais validées. "
        "Aucune donnée réelle n'est modifiée."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset", action="store_true", help="Supprime d'abord le jeu DEMO existant (et lui seul)."
        )
        parser.add_argument("--remove", action="store_true", help="Supprime le jeu DEMO sans le recharger.")
        parser.add_argument(
            "--password",
            help="Mot de passe des comptes DEMO (sinon variable DEMO_PASSWORD, sinon généré aléatoirement).",
        )
        parser.add_argument(
            "--allow-production", action="store_true", help="Autorise l'exécution lorsque DEBUG=False."
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["allow_production"]:
            raise CommandError(
                "DEBUG=False : ajoutez --allow-production pour charger des données de démonstration "
                "sur ce serveur."
            )
        if options["reset"] or options["remove"]:
            counts = demo_data.remove_demo_data()
            self.stdout.write(
                f"Jeu DEMO supprimé : {counts['comptes']} compte(s), "
                f"{counts['exploitations']} exploitation(s)."
            )
            if options["remove"]:
                return
        elif demo_data.is_loaded():
            raise CommandError("Le jeu DEMO est déjà chargé. Utilisez --reset pour le recharger.")

        password = options["password"] or os.environ.get("DEMO_PASSWORD")
        generated = not password
        if generated:
            password = secrets.token_urlsafe(12)
        summary = demo_data.load_demo_data(password)

        self.stdout.write(self.style.SUCCESS("Jeu de données DEMO chargé."))
        self.stdout.write(
            f"  {summary.accounts} comptes, {summary.farms} exploitations, {summary.animals} animaux, "
            f"{summary.weighings} pesées, {summary.ingredients} ingrédients "
            f"({summary.compositions} valeurs), "
            f"{summary.formulas} formules, {summary.feeding_records} distributions, "
            f"{summary.alerts} alertes ouvertes, "
            f"{summary.documents} document."
        )
        self.stdout.write("  Comptes de démonstration :")
        for account in demo_data.ACCOUNTS:
            self.stdout.write(f"    {account['email']:<34} {account['role']}")
        if generated:
            self.stdout.write(
                self.style.WARNING(f"  Mot de passe généré (affiché une seule fois) : {password}")
            )
        else:
            self.stdout.write("  Mot de passe : celui fourni (non affiché).")
        self.stdout.write(
            self.style.WARNING(
                "  Rappel : valeurs nutritionnelles FICTIVES, jamais validées, exclues de tout calcul réel."
            )
        )
