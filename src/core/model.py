from dataclasses import dataclass, field


@dataclass(slots=True)
class Model:
    name: str | None = None
    architecture: str | None = None
    context_length: int | None = None
    parameter_count: int | None = None
    quantization: int | None = None
    file_size: int | None = None
    filename: str = ""
    full_path: str = ""


@dataclass(slots=True)
class ScanResult:
    models: list[Model] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
