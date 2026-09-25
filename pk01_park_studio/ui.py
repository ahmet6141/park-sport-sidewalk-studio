"""Blender sidebar, explicit build buttons, guarded integration and export actions."""
import bpy,json,traceback,uuid
from dataclasses import fields
from bpy.props import StringProperty,EnumProperty,FloatProperty,IntProperty,BoolProperty,FloatVectorProperty,PointerProperty
from .planner import ParkConfig,build_park,add_facility
from .geometry import ScenePlan
from . import runtime,bridge,exporter,props

TYPES=[('BASKETBALL','Basketbol',''),('TENNIS','Tenis',''),('FOOTBALL','Futbol / 105 x 68',''),('FUTSAL','Futsal',''),('VOLLEYBALL','Voleybol',''),('BADMINTON','Badminton',''),('PICKLEBALL','Pickleball',''),('TABLE_TENNIS','Masa tenisi',''),('FITNESS','Acik hava fitness',''),('BENCH','Bank',''),('PERGOLA','Pergola',''),('PICNIC','Piknik masasi',''),('PLANTER','Ciceklik',''),('TREE','Agac','')]

class PK01_Settings(bpy.types.PropertyGroup):
    tab:EnumProperty(name='Bolum',items=[('PLAN','Yerlesim',''),('SPORT','Spor',''),('GREEN','Peyzaj',''),('PATH','SW01',''),('EXPORT','Aktarim','')],default='PLAN')
    preset:EnumProperty(name='Masterplan',items=[('CAMPUS','Aster / Spor Kampusu','270 x 224 m, 400 m pist, tum tesisler'),('COMMUNITY','Mira / Mahalle Parki','164 x 144 m, 200 m kosu halkasi'),('GARDEN','Liva / Golet Bahcesi','142 x 112 m, bahce agirlikli')],default='CAMPUS')
    scene_name:StringProperty(name='Proje adi',default='PK01_Aster_Park')
    seed:IntProperty(name='Varyasyon tohumu',default=41,min=0,max=100000)
    origin:FloatVectorProperty(name='Baslangic / m',size=3,default=(0,0,0),subtype='TRANSLATION')
    yaw:FloatProperty(name='Yon / derece',default=0,min=-360,max=360)
    height:FloatProperty(name='Yuzey kotu / m',default=.18,min=.08,max=.4,precision=3)
    detail:EnumProperty(name='Geometri detayi',items=[('DRAFT','Draft / hizli','Daha az agac yapragi ve pist segmenti'),('BALANCED','Balanced / dengeli','Varsayilan'),('HERO','Hero / yakin plan temeli','Daha yogun yaprak geometri; taranmis model degildir')],default='BALANCED')
    palette:EnumProperty(name='Malzeme paleti',items=[('COASTAL','Coastal / petrol + kiremit',''),('WOODLAND','Woodland / yesil + ahsap',''),('URBAN','Urban / mavi + grafit','')],default='COASTAL')
    wetness:FloatProperty(name='Islaklik',default=0,min=0,max=1)
    path_width:FloatProperty(name='Yol genisligi / m',default=3.2,min=2,max=5)
    path_pattern:EnumProperty(name='SW01 doseme',items=[(p,p,'') for p in ('SLABS','RUNNING','HERRINGBONE','BASKET','STACK')],default='SLABS')
    paver_length:FloatProperty(name='Tas boyu / m',default=.8,min=.1,max=2)
    paver_width:FloatProperty(name='Tas eni / m',default=.4,min=.08,max=1.2)
    joint:FloatProperty(name='Derz / m',default=.006,min=.001,max=.025,precision=3)
    border_width:FloatProperty(name='Kenar seridi / m',default=.12,min=0,max=.4)
    tactile:BoolProperty(name='Hissedilebilir serit (gorsel)',default=False)
    variation:FloatProperty(name='Tas renk varyasyonu',default=.075,min=0,max=.25)
    paver_tint:FloatVectorProperty(name='Doseme tonu',subtype='COLOR',size=3,min=0,max=1,default=(.94,.96,.96))
    curb_tint:FloatVectorProperty(name='Bordur tonu',subtype='COLOR',size=3,min=0,max=1,default=(1,1,1))
    border_tint:FloatVectorProperty(name='Kenar tonu',subtype='COLOR',size=3,min=0,max=1,default=(.32,.35,.39))
    tree_count:IntProperty(name='Agac adedi',default=140,min=0,max=550)
    tree_spacing:FloatProperty(name='Agac min. araligi / m',default=4.8,min=3,max=15)
    tree_scale:FloatProperty(name='Agac olcegi',default=1,min=.5,max=1.6)
    pond_depth:FloatProperty(name='Golet derinligi / m',default=2.2,min=.6,max=4)
    forest:BoolProperty(name='Agaclik / orman kusagi',default=True)
    pond:BoolProperty(name='Golet + iskele',default=True)
    gardens:BoolProperty(name='Ciceklikler + calilar',default=True)
    furniture:BoolProperty(name='Oturma + kent mobilyalari',default=True)
    lights:BoolProperty(name='Aydinlatma armaturleri',default=True)
    fencing:BoolProperty(name='Saha cevre telleri',default=True)
    basketball:BoolProperty(name='Basketbol',default=True)
    tennis:BoolProperty(name='Tenis',default=True)
    volleyball:BoolProperty(name='Voleybol',default=True)
    futsal:BoolProperty(name='Futsal',default=True)
    badminton:BoolProperty(name='Badminton',default=True)
    pickleball:BoolProperty(name='Pickleball',default=True)
    table_tennis:BoolProperty(name='Masa tenisi',default=True)
    fitness:BoolProperty(name='Acik hava fitness',default=True)
    football:BoolProperty(name='Futbol',default=True)
    running_track:BoolProperty(name='Kosu pisti',default=True)
    track_lanes:IntProperty(name='Pist serit adedi',default=6,min=2,max=8)
    component:EnumProperty(name='Tekil tesis / model',items=TYPES,default='BASKETBALL')
    attach_to_active:BoolProperty(name='Aktif parka bagla',default=True)
    active_root:PointerProperty(name='Aktif park',type=bpy.types.Object)
    tree_source:PointerProperty(name='Harici agac mesh',type=bpy.types.Object)
    socket_a:PointerProperty(name='Baslangic portu',type=bpy.types.Object)
    socket_b:PointerProperty(name='Bitis portu',type=bpy.types.Object)
    handle_length:FloatProperty(name='Kavis kolu / m (0=oto)',default=0,min=0,max=80)
    flip_start:BoolProperty(name='Baslangic yonunu tersle',default=False)
    flip_end:BoolProperty(name='Bitis yonunu tersle',default=False)
    sw01_folder:StringProperty(name='Mevcut SW01 klasoru (istege bagli)',subtype='DIR_PATH',default='')
    texture_folder:StringProperty(name='Harici PBR klasoru (istege bagli)',subtype='DIR_PATH',default='')
    export_directory:StringProperty(name='Export klasoru',subtype='DIR_PATH',default='//PK01_Export')
    include_selected_sw01:BoolProperty(name='Secili SW01 modullerini de aktar',default=True)
    status:StringProperty(name='Durum',default='PK01 1.0.0 hazir. Ilk denemeyi bos sahnede yapin.')


def config(s):return ParkConfig(**{f.name:tuple(getattr(s,f.name)) if f.name.endswith('_tint') else getattr(s,f.name) for f in fields(ParkConfig)})
def active_root(context):return runtime.root_from_object(context.active_object) or context.scene.pk01.active_root

def report_error(op,context,error):
    context.scene.pk01.status='HATA: '+str(error);op.report({'ERROR'},str(error));traceback.print_exc();return {'CANCELLED'}

def instantiate(plan,context,**kwargs):
    s=context.scene.pk01
    root,c=runtime.instantiate(plan,context,external_sw01=s.sw01_folder,external_native=s.texture_folder,wetness=s.wetness,**kwargs)
    return root,c

def attach(child,c,parent,context):
    target=runtime.collection_from_root(parent)
    if not target:return
    world=child.matrix_world.copy();child.parent=parent;child.matrix_world=world;child['pk01_root']=False;child['pk01_zone']=True
    old=c.get('pk01_owner');owner=parent['pk01_owner']
    for o in c.all_objects:
        if o.get('pk01_owner')==old:o['pk01_owner']=owner
    c['pk01_owner']=owner
    if 'pk01_project' in c:del c['pk01_project']
    target.children.link(c)
    if c.name in context.scene.collection.children:context.scene.collection.children.unlink(c)

class PK01_OT_build(bpy.types.Operator):
    bl_idname='pk01.build';bl_label='Parki Olustur / Yeniden Uret';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        s=context.scene.pk01
        try:
            plan=build_park(config(s));root,c=instantiate(plan,context,origin=s.origin,yaw=s.yaw);s.active_root=root
            st=plan.stats();s.status=f"{st['assets']} mesh | {st['placements']} instance | {st['unique_triangles']:,} benzersiz ucgen"
            self.report({'INFO'},s.status)
            for note in plan.notes:print('[PK01]',note)
            return {'FINISHED'}
        except Exception as e:return report_error(self,context,e)

class PK01_OT_copy_style(bpy.types.Operator):
    bl_idname='pk01.copy_sw01_style';bl_label='Acik SW01 Panelinden Stili Al';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        try:bridge.copy_sw01_style(context,context.scene.pk01);self.report({'INFO'},'SW01 stili kopyalandi; park yeniden uretildiginde uygulanir.');return {'FINISHED'}
        except Exception as e:return report_error(self,context,e)

class PK01_OT_add_component(bpy.types.Operator):
    bl_idname='pk01.add_component';bl_label='3D Cursor Konumuna Ekle';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        s=context.scene.pk01;parent=active_root(context)
        try:
            cfg=config(s);plan=ScenePlan('PK01_'+s.component+'_'+uuid.uuid4().hex[:6]);plan.settings={'palette':cfg.palette};kind=s.component
            if kind in dict((x[0],x[1]) for x in TYPES[:9]):add_facility(plan,cfg,kind,(0,0))
            else:
                mesh={'BENCH':props.bench,'PERGOLA':props.pergola,'PICNIC':props.picnic,'PLANTER':props.planter,'TREE':lambda:props.tree('BROADLEAF',cfg.seed,cfg.detail)}[kind]()
                plan.place(mesh,category='Trees' if kind=='TREE' else 'Furniture')
            root,c=instantiate(plan,context,origin=tuple(context.scene.cursor.location),yaw=s.yaw,replace_existing=False)
            if s.attach_to_active and parent:attach(root,c,parent,context);s.active_root=parent
            else:s.active_root=root
            self.report({'INFO'},'Eklendi. Zone Empty ile grubun tamamini tasi / dondur.');return {'FINISHED'}
        except Exception as e:return report_error(self,context,e)

class PK01_OT_connect(bpy.types.Operator):
    bl_idname='pk01.connect_sw01';bl_label='Portlari SW01 Kaldirimla Birlestir';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        s=context.scene.pk01;parent=active_root(context)
        try:
            plan=bridge.connection_plan(s.socket_a,s.socket_b,config(s),s.handle_length,s.flip_start,s.flip_end)
            plan.name+='_'+uuid.uuid4().hex[:6];root,c=instantiate(plan,context,replace_existing=False)
            if s.attach_to_active and parent:attach(root,c,parent,context);s.active_root=parent
            else:s.active_root=root
            self.report({'INFO'},'SW01 cekirdegiyle baglanti olusturuldu. Kaynak moduller degistirilmedi.');return {'FINISHED'}
        except Exception as e:return report_error(self,context,e)

class PK01_OT_replace_trees(bpy.types.Operator):
    bl_idname='pk01.replace_trees';bl_label='Agaclari Kaynak Mesh ile Degistir';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        try:
            count=runtime.replace_tree_mesh(context,context.scene.pk01.tree_source,active_root(context));self.report({'INFO'},f'{count} agac degistirildi. UE materyalleri ayrica atanmalidir.');return {'FINISHED'}
        except Exception as e:return report_error(self,context,e)

class PK01_OT_preview(bpy.types.Operator):
    bl_idname='pk01.preview';bl_label='Kamera + Gunes Olustur';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        try:runtime.create_preview(context,active_root(context));self.report({'INFO'},'Cycles onizleme hazir. F12 ile render al.');return {'FINISHED'}
        except Exception as e:return report_error(self,context,e)

class PK01_OT_export(bpy.types.Operator):
    bl_idname='pk01.export_unreal';bl_label='UE Kutuphanesi + Yerlesimi Export Et'
    def execute(self,context):
        try:
            s=context.scene.pk01;path=exporter.export_park(context,active_root(context),s.export_directory,s.include_selected_sw01)
            s.status='Export: '+str(path);self.report({'INFO'},s.status);return {'FINISHED'}
        except Exception as e:return report_error(self,context,e)

class PK01_OT_freeze(bpy.types.Operator):
    bl_idname='pk01.freeze_selected';bl_label='Secilenleri Yeniden Uretimden Koru';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        coll=bpy.data.collections.get('PK01_Preserved')
        if coll is None:coll=bpy.data.collections.new('PK01_Preserved');context.scene.collection.children.link(coll)
        objs=set(context.selected_objects)
        for o in tuple(objs):
            if o.type=='EMPTY':objs.update(o.children_recursive)
        count=0
        for o in objs:
            if o.get('pk01_root'):continue
            if 'pk01_owner' not in o:continue
            world=o.matrix_world.copy();o.parent=None;o.matrix_world=world
            for old in list(o.users_collection):old.objects.unlink(o)
            coll.objects.link(o);del o['pk01_owner'];o['pk01_generated']=False;count+=1
        self.report({'INFO'},f'{count} obje korundu. Korunan objeler aktif park export kapsamindan cikar.');return {'FINISHED'}

class PK01_PT_panel(bpy.types.Panel):
    bl_label='PK / 01 — Park + Sport Studio';bl_idname='PK01_PT_panel';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='PK01'
    def draw(self,context):
        l=self.layout;s=context.scene.pk01
        l.label(text='LANDSCAPE ATELIER   /   SW01 BRIDGE',icon='WORLD')
        l.prop(s,'tab',expand=True)
        if s.tab=='PLAN':
            box=l.box();box.label(text='01 / Masterplan');box.prop(s,'preset');box.prop(s,'scene_name');box.prop(s,'origin');box.prop(s,'yaw');box.prop(s,'seed');box.prop(s,'detail');box.prop(s,'palette');box.prop(s,'height')
            box=l.box();box.label(text='02 / Kent mobilyalari');box.prop(s,'furniture');box.prop(s,'gardens');box.prop(s,'lights')
            l.operator('pk01.build',icon='MOD_BUILD')
            l.operator('pk01.preview',icon='CAMERA_DATA')
            l.label(text='Yeniden uretim bu projedeki duzenlemeleri yeniler.',icon='INFO')
            l.operator('pk01.freeze_selected',icon='LOCKED')
        elif s.tab=='SPORT':
            b=l.box();b.label(text='Masterplanda yer alan sahalar')
            names=['basketball','tennis']
            if s.preset in ('CAMPUS','COMMUNITY'):names+=['volleyball','fitness','running_track']
            if s.preset=='CAMPUS':names+=['football','futsal','badminton','pickleball','table_tennis']
            for key in names:b.prop(s,key)
            if s.preset!='GARDEN':b.prop(s,'track_lanes')
            b.prop(s,'fencing');l.operator('pk01.build',icon='MOD_BUILD')
            b=l.box();b.label(text='Bagimsiz moduler tesis');b.prop(s,'component');b.prop(s,'attach_to_active');b.operator('pk01.add_component',icon='ADD')
            b.label(text='Spor olculeri gorsel referanstir.',icon='INFO')
        elif s.tab=='GREEN':
            b=l.box();b.label(text='Bitkilendirme / dislama alanlari');b.prop(s,'forest');b.prop(s,'tree_count');b.prop(s,'tree_spacing');b.prop(s,'tree_scale');b.prop(s,'gardens');b.prop(s,'pond');b.prop(s,'pond_depth')
            l.operator('pk01.build',icon='MOD_BUILD')
            b=l.box();b.label(text='Kendi yuksek kaliteli agacini kullan');b.prop(s,'tree_source');b.operator('pk01.replace_trees',icon='FILE_REFRESH')
            b.label(text='Kaynak: tek Mesh, dogru metre olcegi.',icon='INFO')
            b.label(text='Yeniden uretim, bu degistirmeyi sifirlar.')
        elif s.tab=='PATH':
            b=l.box();b.label(text='Ortak SW01 geometri + UV duzeni');b.operator('pk01.copy_sw01_style',icon='IMPORT')
            for key in ('path_width','height','path_pattern','paver_length','paver_width','joint','border_width','tactile','variation','paver_tint','curb_tint','border_tint'):b.prop(s,key)
            b=l.box();b.label(text='Iki soket arasinda kavisli kaldirim');b.prop(s,'socket_a');b.prop(s,'socket_b');b.prop(s,'handle_length');b.prop(s,'flip_start');b.prop(s,'flip_end');b.prop(s,'attach_to_active');b.operator('pk01.connect_sw01',icon='LINKED')
            b.label(text='Iki ucta genislik ve yuzey kotu esit olmali.',icon='INFO')
        else:
            b=l.box();b.label(text='PBR kaynaklari / opsiyonel');b.prop(s,'sw01_folder');b.prop(s,'texture_folder');b.prop(s,'wetness')
            b.label(text='Bos birak: ZIP icindeki dokular kullanilir.')
            b=l.box();b.label(text='Unreal / FBX + manifest');b.prop(s,'active_root');b.prop(s,'export_directory');b.prop(s,'include_selected_sw01');b.operator('pk01.export_unreal',icon='EXPORT')
            b.label(text='Export klasorundeki PK01_Import.py UE icindir.')
            b.label(text='UE editor calismasi bu ortamda test edilmedi.',icon='INFO')
        l.separator();l.label(text=s.status[:72])

CLASSES=(PK01_Settings,PK01_OT_build,PK01_OT_copy_style,PK01_OT_add_component,PK01_OT_connect,PK01_OT_replace_trees,PK01_OT_preview,PK01_OT_export,PK01_OT_freeze,PK01_PT_panel)
def register():
    if hasattr(bpy.types.Scene,'pk01'):del bpy.types.Scene.pk01
    for cls in reversed(CLASSES):
        old=getattr(bpy.types,cls.__name__,None)
        if old:
            try:bpy.utils.unregister_class(old)
            except RuntimeError:pass
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.Scene.pk01=PointerProperty(type=PK01_Settings)

def unregister():
    if hasattr(bpy.types.Scene,'pk01'):del bpy.types.Scene.pk01
    for cls in reversed(CLASSES):
        old=getattr(bpy.types,cls.__name__,None)
        if old:
            try:bpy.utils.unregister_class(old)
            except RuntimeError:pass
