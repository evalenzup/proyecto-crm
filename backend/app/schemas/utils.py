from typing import Type, Optional
from pydantic import BaseModel, create_model


def make_optional(model: Type[BaseModel]) -> Type[BaseModel]:
    """
    Crea un nuevo modelo Pydantic donde todos los campos del modelo original son opcionales.
    """
    fields = {}
    for field_name, field_info in model.model_fields.items():
        # Hacer el campo opcional
        fields[field_name] = (Optional[field_info.annotation], None)

    return create_model(f"{model.__name__}Optional", **fields)
