"""Immutable server-graded attempts."""
import uuid
from django.db import models
from django.utils import timezone
class TrainingAttempt(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    task=models.ForeignKey('onboarding.Task',on_delete=models.PROTECT,related_name='training_attempts')
    attempt_number=models.PositiveIntegerField()
    actor=models.ForeignKey('accounts.User',on_delete=models.PROTECT)
    module_version=models.CharField(max_length=80)
    content_sha256=models.CharField(max_length=64)
    answers=models.JSONField()
    score=models.PositiveIntegerField()
    passing_score=models.PositiveIntegerField()
    passed=models.BooleanField()
    submitted_at=models.DateTimeField(default=timezone.now)
    class Meta:
        constraints=[
            models.UniqueConstraint(fields=['task','attempt_number'],name='m4_training_attempt_sequence_unique'),
            models.CheckConstraint(condition=(models.Q(passing_score__gte=1,passing_score__lte=5,score__lte=5)
              & (models.Q(passed=True,score__gte=models.F('passing_score'))
                | models.Q(passed=False,score__lt=models.F('passing_score')))),
                                   name='m4_training_score_bounded'),
        ]
        ordering=['attempt_number']
