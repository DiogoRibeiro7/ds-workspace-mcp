from __future__ import annotations


class DsWorkspaceError(Exception):
    """Base exception for user-facing ds-workspace-mcp failures."""


class InvalidDatasetNameError(DsWorkspaceError, ValueError):
    """Raised when a dataset or database name is missing or malformed."""


class UnsupportedFileTypeError(DsWorkspaceError, ValueError):
    """Raised when a file does not match a supported dataset type."""


class PathTraversalError(DsWorkspaceError, ValueError):
    """Raised when a requested path escapes the configured data root."""


class DatasetNotFoundError(DsWorkspaceError, FileNotFoundError):
    """Raised when a requested dataset or database cannot be found."""


class InvalidSQLError(DsWorkspaceError, ValueError):
    """Raised when a SQL statement is invalid or unsafe."""


class ProfilingError(DsWorkspaceError, RuntimeError):
    """Raised when dataset profiling cannot be completed safely."""


class InsufficientDataError(DsWorkspaceError, ValueError):
    """Raised when an operation requires more usable rows or classes."""
