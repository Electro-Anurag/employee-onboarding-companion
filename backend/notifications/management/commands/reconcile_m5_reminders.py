"""Explicit bounded initial M5 reconciliation until periodic scheduling qualifies."""
from django.core.management.base import BaseCommand
from backend.notifications.services import reconcile_batch


class Command(BaseCommand):
    help='Reconcile <=100 cases from persisted current state; supports restart cursor'
    def add_arguments(self,parser):
        parser.add_argument('--after')
        parser.add_argument('--limit',type=int,default=100)
    def handle(self,*args,**options):
        result=reconcile_batch(after=options['after'],limit=options['limit'])
        self.stdout.write('M5_RECONCILE '+str(result))
