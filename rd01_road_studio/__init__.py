"""RD01 Road Studio — quad-topology road & sidewalk generator for Substance and UE5.

Install this directory as a Blender 4.5+ add-on. The geometry kernel in `core/` is pure Python
and importable without Blender; the Blender layer in `blender/` is imported only on register().
"""
bl_info = {
    'name': 'RD01 | Road Studio',
    'author': 'RD01 Studio',
    'version': (0, 1, 0),
    'blender': (4, 5, 0),
    'location': '3D View > Sidebar > RD01',
    'description': 'Quad-topology roads, curbs and sidewalks with Substance-ready UVs and UE5 FBX export.',
    'category': 'Add Mesh',
}


def register():
    from .blender import ui
    ui.register()


def unregister():
    from .blender import ui
    ui.unregister()
