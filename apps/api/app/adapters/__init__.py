"""Registro de adapters: añadir un proveedor = una clase + una línea aquí."""

from app.adapters.azuredevops import AzureDevOpsAdapter
from app.adapters.generic import GenericAdapter
from app.adapters.github import GitHubAdapter

ADAPTERS: dict[str, type] = {
    "github": GitHubAdapter,
    "azuredevops": AzureDevOpsAdapter,
    "generic": GenericAdapter,
}
