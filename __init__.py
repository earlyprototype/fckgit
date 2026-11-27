"""fckgit - Auto-commit with AI-generated messages using Gemini"""

__version__ = "0.2.0"
__all__ = ["main"]


def main():
    """Run the CLI when invoked from the source package."""
    from .fckgit import main as run_cli
    return run_cli()
