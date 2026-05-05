from dataclasses import dataclass, field


@dataclass(slots=True)
class Model:
    name: str | None = None
    architecture: str | None = None
    basename: str | None = None
    context_length: int | None = None
    parameter_count: int | None = None
    quantization_version: int | None = None
    finetune: str | None = None
    license: str | None = None
    license_link: str | None = None
    sampling_temp: float | None = None
    sampling_top_k: int | None = None
    sampling_top_p: float | None = None
    size_label: str | None = None
    model_type: str | None = None
    block_count: int | None = None
    file_size: int | None = None
    filename: str = ""
    full_path: str = ""


@dataclass(slots=True)
class ScanResult:
    models: list[Model] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
