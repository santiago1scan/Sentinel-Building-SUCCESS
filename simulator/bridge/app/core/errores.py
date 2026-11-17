"""Excepciones que lanza la verificación de Firebase. Las traduce a HTTP la capa de presentación."""


class UnauthorizedError(Exception):
    """Token ausente, inválido o expirado."""


class ForbiddenError(Exception):
    """Token válido, pero el usuario no está en la lista de administradores."""
