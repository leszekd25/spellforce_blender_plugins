bl_info = {
	"name": "Export static SpellForce mesh (.msb)",
	"description": "Export static SpellForce mesh (.msb)",
	"author": "leszekd25",
	"blender": (2, 80, 0),
	"location": "Import/Export",
	"warning": "totally untested...", # used for warning icon and text in addons panel
	"category": "Import-Export",
}

import bpy
from bpy.props import (
	StringProperty,
	FloatProperty,
	IntProperty,
	BoolProperty,
	EnumProperty,
)
from bpy_extras.io_utils import (
	ImportHelper,
	ExportHelper,
	orientation_helper,
	axis_conversion,
)
from mathutils import *
from struct import unpack, pack
import os.path
	
class SFMap:
	def __init__(self):
		self.texID = -1		  #32 bit
		self.unknown1 = 0	  #8 bit
		self.texUVMode = 0	  #8 bit
		self.unused = 0		  #16 bit
		self.texRenderMode = 0#8 bit
		self.texAlpha = 255	  #8 bit
		self.flag = 7		  #8 bit
		self.depthbias = 0	  #8 bit
		self.tiling = 1.0	#float
		self.texName = ""	  #64 char string
	def get(self):
		charray = []
		for i in range(64):
			if i >= len(self.texName):
				charray.append(0)
			else:
				charray.append(ord(self.texName[i]))
		charray = bytes(charray)
		return pack("1i2B1H4B1f64s", self.texID, self.unknown1, self.texUVMode, self.unused, self.texRenderMode, self.texAlpha, self.flag, self.depthbias, self.tiling, charray)

		
class SFMaterial:
	def __init__(self):
		self.texMain = SFMap()
		self.texSecondary = SFMap()
		self.diffCol = []
		self.emitCol = []
		self.specCol = []
		

def VertIndexOf(l, v):
	for i, _v in enumerate(l):
		if CompareVerts(v, _v):
			return i
	return -1
	
def CompareVerts(v1, v2):	  # [vert_id, vert_normal, vert_uv]
	if (v1[0] != v2[0]):
		return False
	# instead of comparing vectors, compare distances (0.001 is 0.1 angular)
	if(((v1[1][0]-v2[1][0])**2 + (v1[1][1] - v2[1][1])**2 + (v1[1][2] - v2[1][2])**2) ** 0.5) > 0.001:
		return False
	if (v1[2][0] != v2[2][0]) or (v1[2][1] != v2[2][1]):
		return False
	
	return True
	
	

def SaveMSBStatic(context, filepath):
	object = bpy.context.object
	obname=object.name
	mesh = object.data
	
	msbfile = open(filepath.replace(".msb", "")+".msb",'wb')
	modelnum = len(mesh.materials)
	
	
	bpy.ops.object.mode_set(mode = 'OBJECT')
	mesh.use_auto_smooth = True
	mesh.calc_normals_split()
	
	uv_layer = mesh.uv_layers[mesh.name]
	uvs = []
	for d in uv_layer.data:
		uvs.append(d.uv)
	
	bpy.ops.object.mode_set(mode = 'EDIT')
	# generate vertex map	(vertex ID -> vertex position)
	vertex_map = []
	for v in mesh.vertices:
		vertex_map.append(v.co)
		
	# generate polygon table
	polygons = []							 # vertex ids, vertex normals, vertex uvs, material
	uv_layer = mesh.uv_layers[mesh.name]
	for i in range(len(mesh.polygons)):
		p = mesh.polygons[i]
		t = []
		
		t.append([p.vertices[0], p.vertices[2], p.vertices[1]])
		
		t2 = []
		if mesh.has_custom_normals:
			for j in [0, 2, 1]:
				t2.append(mesh.loops[i*3+j].normal)
		else:
			for j in [0, 2, 1]:
				t2.append(mesh.vertices[t[0][j]].normal)
		t.append(t2)
		
		t3 = []
		for j in [0, 2, 1]:
			t3.append(uvs[i*3+j])
		t.append(t3)
		
		t.append(p.material_index)
		#print("POLYGON", i, t)
		
		polygons.append(t)
	
	bpy.ops.object.mode_set(mode = 'EDIT')
	
	# remove unused materials
	material_map = {}
	for p in polygons:
		material_map[p[3]] = 1
	
	for i in [j for j in range(modelnum)]:	   # not sure if this is needed, maybe `for i in range(modelnum)` would work as well
		if not(i in material_map):
			for p in polygons:
				if(p[3] > i):
					p[3] -= 1
			modelnum -= 1
	
	# split polygons per material
	# each polygon belongs to exactly one material
	polygons_per_material = [[] for i in range(modelnum)]
	for p in polygons:
		polygons_per_material[p[3]].append(p)
	
	# generate vertex buffer for the file, and fix triangle buffer for the file
	vertices_per_material = [[] for i in range(modelnum)]	  # vertex ids, vertex normals, vertex uvs
		
	for i, ppm in enumerate(polygons_per_material):	   
		vpm = vertices_per_material[i]
		for p in ppm:
			for j in range(3):
				v = [p[0][j], p[1][j], p[2][j]]
				#print("VERTEX", v)
				v_ind = VertIndexOf(vpm, v)
				if(v_ind == -1):
					vpm.append(v)
					p[0][j] = len(vpm)-1
				else:
					p[0][j] = v_ind
		
	
	# bounding box
	bbox_per_model = [[10000, 10000, 10000, -10000, -10000, -10000] for i in range(modelnum)]
	bbox_total = [10000, 10000, 10000, -10000, -10000, -10000]
	
	# calculate bounding boxes
	for i in range(modelnum):
		for v in vertices_per_material[i]:
			pos = vertex_map[v[0]]
			bbox_per_model[i][0] = min(bbox_per_model[i][0], pos[0])
			bbox_per_model[i][1] = min(bbox_per_model[i][1], pos[1])
			bbox_per_model[i][2] = min(bbox_per_model[i][2], pos[2])
			bbox_per_model[i][3] = max(bbox_per_model[i][3], pos[0])
			bbox_per_model[i][4] = max(bbox_per_model[i][4], pos[1])
			bbox_per_model[i][5] = max(bbox_per_model[i][5], pos[2])
			
	for i in range(modelnum):
		bbox_total[0] = min(bbox_total[0], bbox_per_model[i][0])
		bbox_total[1] = min(bbox_total[1], bbox_per_model[i][1])
		bbox_total[2] = min(bbox_total[2], bbox_per_model[i][2])
		bbox_total[3] = max(bbox_total[3], bbox_per_model[i][3])
		bbox_total[4] = max(bbox_total[4], bbox_per_model[i][4])
		bbox_total[5] = max(bbox_total[5], bbox_per_model[i][5])

			
	# write header
	outdata = pack("BBHBB", 0, 2, modelnum, 0, 0)
	msbfile.write(outdata)
	
	for i in range(modelnum):
		outdata2 = pack("2b4H", 0, 2, len(vertices_per_material[i]), 0, len(polygons_per_material[i]), 0)
		msbfile.write(outdata2)
		
		for k, v in enumerate(vertices_per_material[i]):
			pos = vertex_map[v[0]]
			normal = v[1]
			col = [255, 255, 255, 255]
			uv = v[2]
			ind = v[0]
			outdata3 = pack('6f4B2fI', pos[0], pos[1], pos[2], normal[0], normal[1], normal[2], col[0], col[1], col[2], col[3], uv[0], 1-uv[1], ind)
			msbfile.write(outdata3)
		
		for k, f in enumerate(polygons_per_material[i]):
			outdata4 = pack("4H", f[0][0], f[0][1], f[0][2], f[3])
			msbfile.write(outdata4)
		
		# handle materials
		material = SFMaterial()
		diffuse_color = mesh.materials[i].node_tree.nodes.get('Diffuse Color').outputs[0].default_value
		material.diffCol = [int(diffuse_color[2]*255), int(diffuse_color[1]*255), int(diffuse_color[0]*255), 0]
		specular_color = mesh.materials[i].node_tree.nodes.get('Specular Color').outputs[0].default_value
		material.specCol = [int(specular_color[2]*255), int(specular_color[1]*255), int(specular_color[0]*255), 0]
		material.emitCol = [0, 0, 0, 0]
		if mesh.materials[i].get('SFRenderMode') is not None:
			material.texMain.texRenderMode = mesh.materials[i]["SFRenderMode"]
		else:
			material.texMain.texRenderMode = 0
		if mesh.materials[i].get("SFFlags") is not None:
			material.texMain.flag = mesh.materials[i]["SFFlags"]
		else:
			material.texMain.flag = 7
		material.texMain.texName = mesh.materials[i].node_tree.nodes.get('Image Texture').image.name
		# write to file
		msbfile.write(pack("2B", 0, 2))
		msbfile.write(material.texMain.get())
		msbfile.write(material.texSecondary.get())
		msbfile.write(pack("4B", material.diffCol[0], material.diffCol[1], material.diffCol[2], material.diffCol[3]))
		msbfile.write(pack("4B", material.emitCol[0], material.emitCol[1], material.emitCol[2], material.emitCol[3]))
		msbfile.write(pack("4B", material.specCol[0], material.specCol[1], material.specCol[2], material.specCol[3]))
		msbfile.write(pack("6f", bbox_per_model[i][0], bbox_per_model[i][1], bbox_per_model[i][2], bbox_per_model[i][3], bbox_per_model[i][4], bbox_per_model[i][5]))
		msbfile.write(pack("2f", 1.0, 0.0))
	#write footer
	
	msbfile.write(pack("6f", bbox_total[0],bbox_total[1],bbox_total[2],bbox_total[3],bbox_total[4],bbox_total[5]))
	msbfile.close()
	return 0


class ExportStaticMSB(bpy.types.Operator, ExportHelper):
	"""Object Cursor Array"""
	bl_idname = "export.msb_static"
	bl_label = "Export SpellForce static mesh (.msb)"
	bl_options = {'REGISTER'}
	
	filepath: StringProperty(
		name="Output mesh",
		subtype='FILE_PATH'
		)

	filename_ext = ".msb"

	filter_glob: StringProperty(
			default="*.msb",
			options={'HIDDEN'},
			)
	
	@classmethod
	def poll(cls, context):
		obj = context.object
		return obj and obj.type == 'MESH'

	def execute(self, context):
		if SaveMSBStatic(context, self.filepath) == 0:
			return {'FINISHED'}
		return {'CANCELLED'}



def menu_func(self, context):
	self.layout.operator(ExportStaticMSB.bl_idname, text="Export SpellForce static mesh (.msb)")


def register():
	bpy.utils.register_class(ExportStaticMSB)
	bpy.types.TOPBAR_MT_file_export.append(menu_func)

def unregister():
	bpy.utils.unregister_class(ExportStaticMSB)
	bpy.types.TOPBAR_MT_file_export.remove(menu_func)


if __name__ == "__main__":
	register()