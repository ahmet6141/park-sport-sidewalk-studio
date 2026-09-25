"""Shared surface contract for the Blender, glTF and UE bridges."""
from .geometry import MATERIAL_NAMES
from .vendor import sw01_core as sw
SURFACES={s['name']:dict(texture=s['texture'],color=(1.,1.,1.),roughness=s['roughness'],metallic=s['metallic'],sw01=True) for s in sw.MATERIALS}
def _put(name,texture,color,roughness=.7,metallic=0,**extra):
    SURFACES['M_PK01_'+name]=dict(texture=texture,color=color,roughness=roughness,metallic=metallic,**extra)
_put('Grass','Grass',(.78,.90,.65),.94)
_put('GrassDark','Grass',(.58,.77,.50),.95)
_put('EPDM_Teal','EPDM',(.12,.40,.42),.84)
_put('EPDM_Terracotta','EPDM',(.60,.245,.145),.87)
_put('EPDM_Sage','EPDM',(.29,.39,.32),.88)
_put('CourtBlue','EPDM',(.115,.27,.41),.86)
_put('Line',None,(.91,.925,.86),.64)
_put('Timber','Timber',(1.,.94,.83),.64)
_put('Steel',None,(.065,.08,.08),.42,.85)
_put('Bark','Bark',(1.,.91,.77),.96)
_put('Leaf','Leaf',(.68,.91,.48),.86,two_sided=True)
_put('Mulch','Mulch',(.76,.70,.59),.96)
_put('Stone','Stone',(1.,.98,.92),.89)
_put('Water','Water',(.24,.62,.60),.14,transmission=.65,water=True,two_sided=True)
_put('Glass',None,(.74,.86,.85),.10,transmission=.92,two_sided=True)
_put('Emission',None,(1.,.78,.46),.35,emission=4.)
_put('Flower',None,(.68,.19,.37),.78,two_sided=True)
_put('Net',None,(.38,.42,.39),.81)
_put('Gravel','Gravel',(.90,.85,.75),.92)
_put('Soil','Mulch',(.68,.67,.51),.97)

PALETTES={
 'COASTAL':{},
 'WOODLAND':{'M_PK01_EPDM_Teal':(.22,.33,.22),'M_PK01_CourtBlue':(.21,.35,.29),'M_PK01_EPDM_Terracotta':(.51,.26,.16),'M_PK01_Flower':(.60,.36,.65)},
 'URBAN':{'M_PK01_EPDM_Teal':(.11,.29,.42),'M_PK01_CourtBlue':(.16,.24,.38),'M_PK01_EPDM_Sage':(.30,.33,.34),'M_PK01_Flower':(.78,.48,.17)},
}
def spec(key,palette='COASTAL'):
    result=dict(SURFACES[key]);result['color']=PALETTES.get(palette,{}).get(key,result['color']);return result
