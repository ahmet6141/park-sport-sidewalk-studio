"""PK01 Park + Sport Studio. Install this directory as a Blender add-on.
Geometry/planning modules are intentionally usable without bpy for validation.
"""
bl_info = {
    'name': 'PK01 | Park + Sport Studio (SW01 Bridge)',
    'author': 'PK01 Studio', 'version': (1, 1, 0),
    'blender': (4, 5, 0), 'location': '3D View > Sidebar > PK01',
    'description': 'Parametric sports parks, planting, ponds, curved FLOW sidewalks and exact SW01 paths; FBX scene bridge.',
    'category': 'Add Mesh',
}
def register():
    from . import ui
    ui.register()
def unregister():
    from . import ui
    ui.unregister()
