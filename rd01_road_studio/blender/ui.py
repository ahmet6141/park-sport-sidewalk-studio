"""RD01 sidebar: build a road from the active curve, build the modular kit, validate and export."""
from __future__ import annotations
import math
import traceback
import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, PointerProperty, StringProperty
from ..core import kit, standards, section, sweep, validate
from . import export_fbx, scene

PRESET_ITEMS = [
    ('URBAN_2L', 'Urban street, 2 lanes', 'Lanes, gutter, barrier curb, sidewalk'),
    ('URBAN_4L', 'Urban street, 4 lanes', 'Two lanes per side with a dashed lane line'),
    ('URBAN_4L_MEDIAN', 'Urban 4 lanes + median', 'Flush 2 m median between the carriageways'),
    ('RURAL_2L', 'Rural road (embankment)', 'Edge lines, gravel bankett, 1:1.5 embankment'),
    ('RURAL_2L_DITCH', 'Rural road (ditch)', 'Edge lines, bankett, drainage ditch'),
    ('HIGHWAY_4L', 'Highway, 2×2 lanes', 'Flush median, hard shoulders, embankment'),
]
REGION_ITEMS = [(r, r, '') for r in sorted(standards.REGIONS)]


class RD01_Settings(bpy.types.PropertyGroup):
    section_preset: EnumProperty(name='Cross-section', items=PRESET_ITEMS, default='URBAN_2L')
    region: EnumProperty(name='Region', items=REGION_ITEMS, default='EU',
                         description='Dimension defaults and drive side (UK = left-hand traffic)')
    markings: BoolProperty(name='Raised markings', default=True)
    max_step: FloatProperty(name='Edge spacing (m)', default=1.0, min=0.25, max=4.0,
                            description='Longitudinal loop spacing on straights; curves are refined automatically')
    chunk_length: FloatProperty(name='Chunk length (m)', default=32.0, min=0.0, max=128.0,
                                description='Split long roads into chunks (0 = one object). Keeps UVs half-float safe in UE')
    export_dir: StringProperty(name='Export folder', subtype='DIR_PATH', default='//RD01_Export')
    export_profile: EnumProperty(name='Profile', items=[('UE', 'Unreal Engine', 'FBX per piece with SOCKET_ empties'),
                                                        ('PAINTER', 'Substance Painter', '*_low meshes, ID colours first')])
    status: StringProperty(name='Status', default='')


def _settings(context) -> RD01_Settings:
    return context.scene.rd01


def _fail(op, context, err) -> set:
    _settings(context).status = f'ERROR: {err}'
    op.report({'ERROR'}, str(err))
    traceback.print_exc()
    return {'CANCELLED'}


def _check_scene(context) -> None:
    if abs(context.scene.unit_settings.scale_length - 1.0) > 1e-6:
        raise ValueError('RD01 needs Unit Scale 1.0 (metres): Scene Properties → Units.')
    if context.object and context.object.mode != 'OBJECT':
        raise ValueError('Switch to Object Mode first.')


class RD01_OT_build_road(bpy.types.Operator):
    bl_idname = 'rd01.build_road'
    bl_label = 'Build Road from Curve'
    bl_description = 'Sweep the cross-section along every spline of the active curve (rebuilds previous output)'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        s = _settings(context)
        try:
            _check_scene(context)
            curve = context.active_object
            if curve is None or curve.type != 'CURVE':
                raise ValueError('Select a curve object (Add → Curve → Bézier) to build a road from.')
            tpl = section.compile_section(standards.preset(s.section_preset, s.region))
            all_pieces = []
            base = 'SM_RD01_Road_' + ''.join(ch for ch in curve.name.title() if ch.isalnum())[:32]
            for k, (rail, cyclic) in enumerate(scene.curve_rails(curve)):
                opts = sweep.RoadOptions(name=f'{base}_S{k:02d}', max_step=s.max_step, chunk_length=s.chunk_length,
                                         markings=s.markings, port_start=cyclic, port_end=cyclic)
                all_pieces += sweep.build_road(rail, tpl, opts)
            problems = [i for p in all_pieces for i in validate.errors(validate.validate_mesh(p.mesh))]
            if problems:
                raise ValueError(f'{len(problems)} topology errors, first: {problems[0]}')
            scene.remove_generated(curve)
            coll = scene.output_collection(context, 'RD01_Roads')
            objs = scene.link_pieces(context, curve, all_pieces, coll, curve.matrix_world.copy())
            faces = sum(len(p.mesh.faces) for p in all_pieces)
            s.status = f'{len(objs)} road objects, {faces:,} quads ({tpl.section.name}, {s.region})'
            self.report({'INFO'}, s.status)
            return {'FINISHED'}
        except Exception as e:
            return _fail(self, context, e)


class RD01_OT_build_kit(bpy.types.Operator):
    bl_idname = 'rd01.build_kit'
    bl_label = 'Build Modular Kit'
    bl_description = 'Generate straight and curved kit pieces of the current cross-section, laid out in a row'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        s = _settings(context)
        try:
            _check_scene(context)
            root_name = f'RD01_Kit_{s.section_preset}_{s.region}'
            root = bpy.data.objects.get(root_name)
            if root is None:
                root = bpy.data.objects.new(root_name, None)
                scene.output_collection(context, 'RD01_Kit').objects.link(root)
            scene.remove_generated(root)
            pieces = [kit.build_piece(d, s.section_preset, s.region, s.markings) for d in kit.catalogue(s.section_preset)]
            coll = scene.output_collection(context, 'RD01_Kit')
            gap = 4.0
            y = 0.0
            for p in pieces:
                (x0, y0, _), (x1, y1, _) = p.mesh.bounds()
                p.origin = (0.0, y - y0, 0.0)
                y += (y1 - y0) + gap
            scene.link_pieces(context, root, pieces, coll, root.matrix_world.copy())
            s.status = f'{len(pieces)} kit pieces ({s.section_preset}, {s.region})'
            self.report({'INFO'}, s.status)
            return {'FINISHED'}
        except Exception as e:
            return _fail(self, context, e)


def _selected_pieces(context):
    """Re-derive piece records from selected RD01 objects (mesh read back, sockets from the object frame)."""
    from ..core.piece import Piece, Socket
    from .readback import bpy_to_qmesh
    out = []
    for ob in context.selected_objects:
        if ob.type == 'MESH' and ob.get('rd01_piece'):
            q = bpy_to_qmesh(ob)
            sockets = [Socket(c.name.split('.')[0].removeprefix('SOCKET_'), tuple(c.location),
                              math.degrees(c.rotation_euler.z)) for c in ob.children if c.name.startswith('SOCKET_')]
            out.append(Piece(ob['rd01_piece'], q, tuple(ob.matrix_world.translation),
                             math.degrees(ob.matrix_world.to_euler().z), sockets))
    return out


class RD01_OT_export(bpy.types.Operator):
    bl_idname = 'rd01.export'
    bl_label = 'Export Selected (FBX + manifest)'
    bl_description = 'One FBX per selected RD01 piece plus RD01_manifest.json'

    def execute(self, context):
        s = _settings(context)
        try:
            pieces = _selected_pieces(context)
            if not pieces:
                raise ValueError('Select RD01 road or kit objects to export.')
            out = export_fbx.export_pieces(pieces, s.export_dir, s.export_profile)
            s.status = f'Exported {len(pieces)} FBX to {out}'
            self.report({'INFO'}, s.status)
            return {'FINISHED'}
        except Exception as e:
            return _fail(self, context, e)


class RD01_OT_validate(bpy.types.Operator):
    bl_idname = 'rd01.validate'
    bl_label = 'Validate Selected'
    bl_description = 'Run the RD01 topology and UV checks on the selected RD01 objects'

    def execute(self, context):
        s = _settings(context)
        try:
            pieces = _selected_pieces(context)
            issues = [i for p in pieces for i in validate.validate_mesh(p.mesh)]
            for i in issues:
                print('[RD01]', i)
            s.status = f'{len(pieces)} objects: {len(validate.errors(issues))} errors, {len(issues)} issues (see console)'
            self.report({'WARNING' if issues else 'INFO'}, s.status)
            return {'FINISHED'}
        except Exception as e:
            return _fail(self, context, e)


class RD01_PT_panel(bpy.types.Panel):
    bl_label = 'RD01 Road Studio'
    bl_idname = 'RD01_PT_panel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'RD01'

    def draw(self, context):
        s = _settings(context)
        col = self.layout.column()
        box = col.box(); box.label(text='Cross-section', icon='MOD_ARRAY')
        box.prop(s, 'section_preset'); box.prop(s, 'region'); box.prop(s, 'markings')
        box = col.box(); box.label(text='Spline road', icon='CURVE_BEZCURVE')
        box.prop(s, 'max_step'); box.prop(s, 'chunk_length')
        box.operator('rd01.build_road', icon='MOD_CURVE')
        box = col.box(); box.label(text='Modular kit', icon='MESH_GRID')
        box.operator('rd01.build_kit', icon='ADD')
        box = col.box(); box.label(text='Validate & export', icon='EXPORT')
        box.prop(s, 'export_profile'); box.prop(s, 'export_dir')
        box.operator('rd01.validate', icon='CHECKMARK'); box.operator('rd01.export', icon='EXPORT')
        if s.status:
            col.label(text=s.status[:90], icon='INFO')


CLASSES = (RD01_Settings, RD01_OT_build_road, RD01_OT_build_kit, RD01_OT_export, RD01_OT_validate, RD01_PT_panel)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.rd01 = PointerProperty(type=RD01_Settings)


def unregister():
    if hasattr(bpy.types.Scene, 'rd01'):
        del bpy.types.Scene.rd01
    for cls in reversed(CLASSES):
        if cls.is_registered:
            bpy.utils.unregister_class(cls)
