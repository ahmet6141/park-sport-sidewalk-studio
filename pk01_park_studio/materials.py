"""Blender materials with reusable SW01 material slots and image PBR maps."""
from pathlib import Path
import bpy
from .geometry import MATERIAL_NAMES
from .surfaces import spec
ROOT=Path(__file__).resolve().parent

def texture_path(tag,suffix,external_sw01='',external_native=''):
    from .vendor.sw01_core import MATERIALS
    sw_tags={s['texture'] for s in MATERIALS}
    if tag in sw_tags and external_sw01:
        p=Path(bpy.path.abspath(external_sw01)).expanduser()
        for d in (p/'Textures',p):
            path=d/tag/f'{tag}_{suffix}.png'
            if path.is_file():return path
    if tag not in sw_tags and external_native:
        p=Path(bpy.path.abspath(external_native)).expanduser()/tag/f'{tag}_{suffix}.png'
        if p.is_file():return p
    return ROOT/'assets'/'textures'/tag/f'{tag}_{suffix}.png'

def ensure_materials(palette='COASTAL',wetness=0.,external_sw01='',external_native=''):
    result=[]
    for key in MATERIAL_NAMES:
        s=spec(key,palette);s['roughness_scale']=max(.12,1-.75*wetness)
        # Reuse the actual SW01 datablock without changing its existing nodes/settings.
        existing=bpy.data.materials.get(key) if s.get('sw01') else None
        if existing and existing.use_nodes:
            result.append(existing);continue
        name=key if s.get('sw01') else key+'_'+palette
        mat=bpy.data.materials.get(name)
        if mat is not None and not mat.get('pk01_material'):
            mat=None  # Never overwrite an unrelated user's material.
        if mat is None:mat=bpy.data.materials.new(name)
        mat['pk01_material']=True;mat['pk01_surface_key']=key;mat['pk01_palette']=palette
        mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links;nodes.clear()
        bsdf=nodes.new('ShaderNodeBsdfPrincipled');bsdf.location=(510,80)
        out=nodes.new('ShaderNodeOutputMaterial');out.location=(840,80);links.new(bsdf.outputs['BSDF'],out.inputs['Surface'])
        tint=nodes.new('ShaderNodeRGB');tint.name='PK01_Tint';tint.outputs[0].default_value=(*s['color'],1);tint.location=(-600,560)
        uv=nodes.new('ShaderNodeUVMap');uv.uv_map='UV0_Tile';uv.location=(-1150,160)
        vc=nodes.new('ShaderNodeVertexColor');vc.layer_name='SW01_Tint';vc.location=(-450,740)
        color=tint.outputs[0]
        paths={};tag=s.get('texture')
        if tag:
            def image(suffix,y,noncolor=False):
                p=texture_path(tag,suffix,external_sw01,external_native)
                if not p.is_file():raise FileNotFoundError(f'PK01 texture missing: {p}. Reinstall the COMPLETE ZIP.')
                im=bpy.data.images.load(str(p),check_existing=True);im.colorspace_settings.name='Non-Color' if noncolor else 'sRGB'
                n=nodes.new('ShaderNodeTexImage');n.image=im;n.location=(-900,y);n.extension='REPEAT';links.new(uv.outputs['UV'],n.inputs['Vector']);paths[suffix]=str(p)
                return n
            bc=image('BaseColor',320);nm=image('NormalGL',-340,True);orm=image('ORM',-20,True)
            mul=nodes.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1.;mul.location=(-300,350)
            links.new(bc.outputs['Color'],mul.inputs[1]);links.new(color,mul.inputs[2]);color=mul.outputs[0]
            sep=nodes.new('ShaderNodeSeparateColor');sep.mode='RGB';sep.location=(-550,-20);links.new(orm.outputs['Color'],sep.inputs[0])
            rough=nodes.new('ShaderNodeMath');rough.operation='MULTIPLY';rough.inputs[1].default_value=max(.12,1-.75*wetness);rough.location=(120,-10)
            links.new(sep.outputs['Green'],rough.inputs[0]);links.new(rough.outputs[0],bsdf.inputs['Roughness'])
            if s.get('sw01'):links.new(sep.outputs['Blue'],bsdf.inputs['Metallic'])
            norm=nodes.new('ShaderNodeNormalMap');norm.location=(150,-260);norm.uv_map='UV0_Tile';norm.inputs['Strength'].default_value=.65 if key.endswith('Water') else .55
            links.new(nm.outputs['Color'],norm.inputs['Color']);links.new(norm.outputs['Normal'],bsdf.inputs['Normal'])
        else:bsdf.inputs['Roughness'].default_value=s.get('roughness',.7)
        mult=nodes.new('ShaderNodeMixRGB');mult.blend_type='MULTIPLY';mult.inputs[0].default_value=1;mult.location=(100,370)
        links.new(color,mult.inputs[1]);links.new(vc.outputs['Color'],mult.inputs[2]);links.new(mult.outputs[0],bsdf.inputs['Base Color'])
        if not s.get('sw01'):bsdf.inputs['Metallic'].default_value=s.get('metallic',0)
        if s.get('transmission'):
            bsdf.inputs['Transmission Weight'].default_value=s['transmission'];bsdf.inputs['IOR'].default_value=1.333 if s.get('water') else 1.45
        if s.get('emission'):
            bsdf.inputs['Emission Color'].default_value=(*s['color'],1);bsdf.inputs['Emission Strength'].default_value=s['emission']
        mat.diffuse_color=(*s['color'],1)
        mat.use_backface_culling=not s.get('two_sided',False)
        import json
        mat['pk01_texture_paths']=json.dumps(paths);mat['pk01_spec']=json.dumps(s)
        result.append(mat)
    return result
