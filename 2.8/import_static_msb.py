bl_info = {
	"name": "Import static SpellForce mesh (.msb)",
	"description": "Import static SpellForce mesh (.msb)",
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
from struct import unpack
import os.path

class SFVertex:
	def __init__(self):
		self.pos=[0, 0, 0]
		self.normal = [0, 0, 0]
		self.col = [0, 0, 0, 0]
		self.uv = [0, 0]
		self.ind = 0
	def __init__(self, data):
		self.pos = [data[0], data[1], data[2]]
		self.normal = [data[3], data[4], data[5]]
		self.col = [data[6], data[7], data[8], data[9]]
		self.uv = [data[10], 1.0-data[11]]
		self.ind = data[12]

class SFTriangle:
	def __init__(self):
		self.indices = [0, 0, 0, 0]
		self.material = 0
		self.group = 0
	def __init__(self, data, offset, mat):
		self.indices = [data[0]+offset, data[1]+offset, data[2]+offset, 0]
		self.material = mat
		self.group = 0

class SFMeshBuffer:
	def __init__(self):
		self.vertices = []
		self.triangles = []
		self.material = None
		
class SFMesh:
	def __init__(self):
		self.meshbuffers = []
	
class SFMap:
	def __init__(self):
		self.texID = -1		  #32 bit
		self.unknown1 = 0	  #8 bit
		self.texUVMode = 0	  #8 bit
		self.unused = 0		  #16 bit
		self.texRenderMode = 0#8 bit
		self.texAlpha = 1	  #8 bit
		self.flag = 7		  #8 bit
		self.depthbias = 0	  #8 bit
		self.tiling = 1.0	#float
		self.texName = ""	  #64 char string
	def set(self, table):
		print(table)
		self.texID = table[0]	  #always -1?
		self.unknown1 = table[1]  #idk
		self.texUVMode = table[2] #probably always 0
		self.unused = table[3]	  #anything goes here
		self.texRenderMode = table[4]	#depends, usually 0
		self.texAlpha = table[5]/255
		self.flag = table[6]	  #should be 7 except noted otherwise
		self.depthbias = table[7] #always 0?
		self.tiling = table[8]	  #always 1.0?
		ntable = []
		for c in table[9]:
			if c == 0:
				break
			ntable.append(c)
		self.texName = str(bytearray(ntable), "utf-8")
		
class SFMaterial:
	def __init__(self):
		self.texMain = SFMap()
		self.texSecondary = SFMap()
		self.diffCol = []
		self.emitCol = []
		self.specCol = []


def LoadMSBStatic(context, filepath):
	print(filepath)
	
	msbfile = open(filepath,'rb')
			
	model = SFMesh()
	
	indata = unpack("4H", msbfile.read(8))
	modelnum=indata[1]
	
	total_v = 0
	max_v = 0
	total_t = 0
	
	for t in range(modelnum):
		model.meshbuffers.append(SFMeshBuffer())
		indata2 = unpack("2I", msbfile.read(8))
		print(t, indata2[0], indata2[1])
		for i in range(indata2[0]):
			model.meshbuffers[t].vertices.append(SFVertex(unpack("6f4B2f2H", msbfile.read(40))))
			max_v = max(model.meshbuffers[t].vertices[i].ind, max_v)
		for i in range(indata2[1]):
			model.meshbuffers[t].triangles.append(SFTriangle(unpack("4H", msbfile.read(8)), total_v, t))
		mat = SFMaterial()
		unpack("1H", msbfile.read(2))
		mat.texMain.set(unpack("1i2B1H4B1f64s", msbfile.read(80)))
		mat.texSecondary.set(unpack("1i2B1H4B1f64s", msbfile.read(80)))
		mat.diffCol = list(unpack("4B", msbfile.read(4)))
		mat.emitCol = list(unpack("4B", msbfile.read(4)))
		mat.specCol = list(unpack("4B", msbfile.read(4)))
		#divide colors by 255
		model.meshbuffers[t].material = mat
		#not important data
		indata6 = unpack("8f", msbfile.read(32))
		indata7 = []
		if t == modelnum-1:
			indata7 = unpack("6f", msbfile.read(24))
		else:
			indata7 = unpack("2B", msbfile.read(2))
		total_v += len(model.meshbuffers[t].vertices)
		total_t += len(model.meshbuffers[t].triangles)
		#FIX HERE: if a model contains garbage (0 vertices, 0 faces), blender fails to load whole mesh
		#fix for equipment_weapon_spear01
		if indata2[0] == 0 and indata2[1] == 0:
			del model.meshbuffers[-1]
			modelnum -= 1
	
	msbfile.close()
	
	#create materials
	tex = None
	texind = 0
	texnames = []
	textures = []
	materials = []
	tex_per_material = []
	for t in range(modelnum):
		tex = None
		texname = model.meshbuffers[t].material.texMain.texName
		if not(texname in texnames):
			texind = len(texnames)
			texnames.append(texname)
			tex = bpy.data.textures.new(name = texname, type = 'IMAGE')
			image = None
			imagepath=os.path.split(filepath)[0] + "\\" + texname + ".dds"
			image = bpy.data.images.load(imagepath)
			image.name = texname
			if image is not None:
				tex.image = image
			textures.append(tex)
		else:
			texind = texnames.index(texname)
			tex = textures[texind]
		tex_per_material.append(tex)
		
		mat = model.meshbuffers[t].material
		materialname = "Material "+str(t+1)
		matdata = bpy.data.materials.new(materialname)
		matdata["SFRenderMode"] = mat.texMain.texRenderMode
		matdata["SFFlags"] = mat.texMain.flag
		matdata.blend_method = 'CLIP'
		matdata.use_nodes = True
		materials.append(matdata)	
	
	correct_vertex_pos = [[0, 0, 0] for i in range(max_v+1)]
	correct_vertex_normal = [[0, 1, 0] for i in range(max_v+1)]
	
	for m in model.meshbuffers:
		for v in m.vertices:
			correct_vertex_pos[v.ind] = v.pos
			correct_vertex_normal[v.ind] = v.normal
	
	vertices = []
	for p in correct_vertex_pos:
		vertices.append(p[0])
		vertices.append(p[1])
		vertices.append(p[2])
	normals = []
	for n in correct_vertex_normal:
		normals.append(n[0])
		normals.append(n[1])
		normals.append(n[2])
	vertex_indices = []
	uvs = []
	material_indices = []
	total_v = 0
	for m in model.meshbuffers:
		for t in m.triangles:
			vertex_indices.append(m.vertices[t.indices[0]-total_v].ind)
			vertex_indices.append(m.vertices[t.indices[1]-total_v].ind)
			vertex_indices.append(m.vertices[t.indices[2]-total_v].ind)
			uvs.append(m.vertices[t.indices[0]-total_v].uv[0])
			uvs.append(m.vertices[t.indices[0]-total_v].uv[1])
			uvs.append(m.vertices[t.indices[1]-total_v].uv[0])
			uvs.append(m.vertices[t.indices[1]-total_v].uv[1])
			uvs.append(m.vertices[t.indices[2]-total_v].uv[0])
			uvs.append(m.vertices[t.indices[2]-total_v].uv[1])
			material_indices.append(t.material)
		total_v += len(m.vertices)
	loop_start = [3*i for i in range(len(vertex_indices)//3)]
	loop_total = [3 for i in range(len(vertex_indices)//3)]
	

	# generate geometry and vertex data in blender
	objName = (os.path.split(filepath)[1].replace(".msb",""))
	
	me_ob = bpy.data.meshes.new(objName)
	for m in materials:
		me_ob.materials.append(m)
	
	me_ob.vertices.add(len(vertices)//3)
	me_ob.vertices.foreach_set("co", vertices)
	me_ob.vertices.foreach_set("normal", normals)
	
	me_ob.loops.add(len(vertex_indices))
	me_ob.loops.foreach_set("vertex_index", vertex_indices)
	
	me_ob.polygons.add(len(loop_start))
	me_ob.polygons.foreach_set("loop_start", loop_start)
	me_ob.polygons.foreach_set("loop_total", loop_total)
	me_ob.polygons.foreach_set("material_index", material_indices)
	
	uv_layer = me_ob.uv_layers.new(name = objName)
	for i, uv in enumerate(uv_layer.data):
		uv.uv = uvs[2*i:2*i+2]
	
	# set up materials
	for i, m in enumerate(materials):
		# reset tree
		nodes = m.node_tree.nodes
		links = m.node_tree.links
		for node in nodes:
			nodes.remove(node) 
		for link in links:
			links.remove(link)
		
		# create nodes
		uvmap_node = nodes.new(type = 'ShaderNodeUVMap')
		imtex_node = nodes.new(type = 'ShaderNodeTexImage')
		imtex_node.name = 'Image Texture'
		tbsdf_node = nodes.new(type = 'ShaderNodeBsdfTransparent')
		dbsdf_node = nodes.new(type = 'ShaderNodeBsdfDiffuse')
		mixsh_node = nodes.new(type = 'ShaderNodeMixShader')
		output_node = nodes.new(type = 'ShaderNodeOutputMaterial')
		diffuse_node = nodes.new(type = 'ShaderNodeRGB')
		diffuse_node.name = 'Diffuse Color'
		specular_node = nodes.new(type = 'ShaderNodeRGB')
		specular_node.name = 'Specular Color'
		# set node parameters
		mat = model.meshbuffers[i].material
		uvmap_node.uv_map = objName
		imtex_node.image = tex_per_material[i].image
		diffuse_color = [mat.diffCol[2]/255,  mat.diffCol[1]/255,  mat.diffCol[0]/255, 1]
		diffuse_node.outputs[0].default_value = diffuse_color
		specular_color = [mat.specCol[2]/255, mat.specCol[1]/255, mat.specCol[0]/255, 1]
		specular_node.outputs[0].default_value = specular_color
		# connect nodes
		links.new(uvmap_node.outputs['UV'], imtex_node.inputs['Vector'])
		links.new(imtex_node.outputs['Color'], dbsdf_node.inputs['Color'])
		links.new(imtex_node.outputs['Alpha'], mixsh_node.inputs['Fac'])
		links.new(tbsdf_node.outputs['BSDF'], mixsh_node.inputs[1])
		links.new(dbsdf_node.outputs['BSDF'], mixsh_node.inputs[2])
		links.new(mixsh_node.outputs['Shader'], output_node.inputs['Surface'])
		
	
	me_ob.update()
	
	#create object which uses the geometry
	final_mesh = bpy.data.objects.new(name = objName, object_data = me_ob)
	bpy.context.scene.collection.objects.link(final_mesh)	
	
	final_mesh.select_set(True)
	bpy.context.view_layer.objects.active = final_mesh
	bpy.ops.object.editmode_toggle()
	bpy.ops.mesh.select_all(action = 'SELECT')
	bpy.ops.mesh.normals_make_consistent(inside=False)
	bpy.ops.object.editmode_toggle()
	
	return 0


class ImportStaticMSB(bpy.types.Operator, ImportHelper):
	"""Object Cursor Array"""
	bl_idname = "import.msb_static"
	bl_label = "Import SpellForce static mesh (.msb)"
	bl_options = {'REGISTER', 'UNDO'}
	
	filepath: StringProperty(
		name="Input mesh",
		subtype='FILE_PATH'
		)

	filename_ext = ".msb"

	filter_glob: StringProperty(
			default="*.msb",
			options={'HIDDEN'},
			)

	def execute(self, context):
		if LoadMSBStatic(context, self.filepath) == 0:
			return {'FINISHED'}
		return {'CANCELLED'}



def menu_func(self, context):
	self.layout.operator(ImportStaticMSB.bl_idname, text="Import SpellForce static mesh (.msb)")


def register():
	bpy.utils.register_class(ImportStaticMSB)
	bpy.types.TOPBAR_MT_file_import.append(menu_func)

def unregister():
	bpy.utils.unregister_class(ImportStaticMSB)
	bpy.types.TOPBAR_MT_file_import.remove(menu_func)


if __name__ == "__main__":
	register()