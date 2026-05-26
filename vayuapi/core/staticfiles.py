"""
Static files support for VayuAPI

Provides static file serving capabilities.
"""

from starlette.staticfiles import StaticFiles as StarletteStaticFiles


class StaticFiles(StarletteStaticFiles):
    """
    Static file server for VayuAPI.

    Wraps Starlette's StaticFiles with additional features.

    Example:
        ```python
        from vayuapi import VayuAPI
        from vayuapi.staticfiles import StaticFiles

        app = VayuAPI()

        # Mount static files
        app.mount("/static", StaticFiles(directory="static"), name="static")
        ```
    """

    def __init__(
        self,
        directory: str = None,
        packages: list = None,
        html: bool = False,
        check_dir: bool = True,
        follow_symlink: bool = False
    ):
        """
        Initialize static files server.

        Args:
            directory: Directory containing static files
            packages: List of package names for static files
            html: Serve index.html for directories
            check_dir: Check if directory exists on startup
            follow_symlink: Follow symbolic links
        """
        super().__init__(
            directory=directory,
            packages=packages,
            html=html,
            check_dir=check_dir,
            follow_symlink=follow_symlink
        )


__all__ = ["StaticFiles"]
