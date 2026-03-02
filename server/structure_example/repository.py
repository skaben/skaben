from django.db import models


class MathModel(models.Model):
    """Stores mathematical results."""
    result = models.IntegerField()


class MathRepository:
    """Repository for saving math results."""

    def save_result(self, result: int) -> None:
        """Saves the result to the database."""
        MathModel.objects.create(result=result)

    def get_all_results_flat(self) -> list[int]:
        """Retrieves all saved results from the database."""
        return list(MathModel.objects.values_list('result', flat=True))
