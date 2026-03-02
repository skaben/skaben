from structure_example.repository import MathRepository


class ExampleMathService:
    """This service performs math operations."""

    def __init__(self, repository: MathRepository | None = None) -> None:
        self.repository = repository or MathRepository()

    def multiply(self, a: int, b: int) -> int:
        """Returns the product of two integers."""
        return a * b

    def process_entry(self, entry: int) -> None:
        """Processes an entry by squaring it and saving the result."""
        result = self.multiply(entry, entry)
        self.repository.save_result(result)
