from . import models


def post_init_hook(env):
    """Remove duplicate root menu after migration."""
    menu = env.ref('leulit_partis.menu_leulit_partis_root', raise_if_not_found=False)
    if menu:
        menu.unlink()
