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
	def __init__(self, data):
		self.pos = [data[0], data[1], data[2]]
		self.normal = [data[3], data[4], data[5]]
		self.col = [data[6], data[7], data[8], data[9]]
		self.uv = [data[10], 1.0-data[11]]
		self.ind = data[12]

class SFTriangle:
	def __init__(self, data):
		#self.indices = [data[0]+offset, data[1]+offset, data[2]+offset, 0]
		self.indices = [data[0], data[1], data[2], 0]
		self.material = data[3]
		self.group = data[4]

class SFMeshBuffer:
	def __init__(self):
		self.vertices = []
		self.triangles = []
		self.material = None
		
class SFMesh:
	def __init__(self):
		self.meshbuffers = []
	
class SFMap:
	def __init__(self, table):
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
		self.texMain = None
		self.texSecondary = None
		self.diffCol = []
		self.emitCol = []
		self.specCol = []


def LoadMSBStatic(context, filepath):
	# open file and load in mesh data
	msbfile = open(filepath,'rb')
			
	model = SFMesh()
	
	indata = unpack("4H", msbfile.read(8))
	modelnum=indata[1]
	
	total_v = 0
	max_v = 0
	total_f = 0
	
	for t in range(modelnum):
		model.meshbuffers.append(SFMeshBuffer())
		
		indata2 = unpack("2I", msbfile.read(8))
		
		for i in range(indata2[0]):
			model.meshbuffers[t].vertices.append(SFVertex(unpack("6f4B2f2H", msbfile.read(40))))
			max_v = max(max_v, model.meshbuffers[t].vertices[-1].ind)
			
		for i in range(indata2[1]):
			model.meshbuffers[t].triangles.append(SFTriangle(unpack("3HBB", msbfile.read(8))))
		
		
		msbfile.read(2)
		
		mat = SFMaterial()
		mat.texMain = SFMap(unpack("1i2B1H4B1f64s", msbfile.read(80)))
		mat.texSecondary = SFMap(unpack("1i2B1H4B1f64s", msbfile.read(80)))
		mat.diffCol = list(unpack("4B", msbfile.read(4)))
		mat.emitCol = list(unpack("4B", msbfile.read(4)))
		mat.specCol = list(unpack("4B", msbfile.read(4)))
		model.meshbuffers[t].material = mat
		
		#not important data
		msbfile.read(34)
		
		total_v += len(model.meshbuffers[t].vertices)
		total_f += len(model.meshbuffers[t].triangles)
		#FIX HERE: if a model contains garbage (0 vertices, 0 faces), blender fails to load whole mesh
		#fix for equipment_weapon_spear01
		if indata2[0] == 0 and indata2[1] == 0:
			del model.meshbuffers[-1]
			modelnum -= 1
	
	msbfile.close()
	
	#create materials from mesh material data
	img_dict = {}
	materials = []
	img_per_material = []
	
	for t in range(modelnum):
		image = None
		texname = model.meshbuffers[t].material.texMain.texName
		if not(texname in img_dict):
			imagepath=os.path.split(filepath)[0] + "\\" + texname + ".dds"
			image = bpy.data.images.load(imagepath)
			if image is not None:
				image.name = texname
			img_dict[texname] = image
		else:
			image = img_dict[texname]
		img_per_material.append(image)
		
		mat = model.meshbuffers[t].material
		materialname = "Material "+str(t+1)
		matdata = bpy.data.materials.new(materialname)
		matdata["SFRenderMode"] = mat.texMain.texRenderMode
		matdata["SFFlags"] = mat.texMain.flag
		matdata.blend_method = 'CLIP'
		matdata.use_nodes = True
		materials.append(matdata)	
	
	polygons = [[[0, 0, 0], [[0, 0, 1], [0, 0, 1], [0, 0, 1]], [[0, 0], [0, 0], [0, 0]], 0] for i in range(total_f)]  # vertex ids, vertex normals, vertex uvs, material
	vertex_map = [[0, 0, 0] for i in range(max_v + 1)]
	
	total_f = 0
	for t in range(modelnum):
		for f in range(len(model.meshbuffers[t].triangles)):
			polygons[total_f+f][0][0] = model.meshbuffers[t].vertices[model.meshbuffers[t].triangles[f].indices[0]].ind
			polygons[total_f+f][0][1] = model.meshbuffers[t].vertices[model.meshbuffers[t].triangles[f].indices[2]].ind
			polygons[total_f+f][0][2] = model.meshbuffers[t].vertices[model.meshbuffers[t].triangles[f].indices[1]].ind
			polygons[total_f+f][1][0] = model.meshbuffers[t].vertices[model.meshbuffers[t].triangles[f].indices[0]].normal
			polygons[total_f+f][1][1] = model.meshbuffers[t].vertices[model.meshbuffers[t].triangles[f].indices[2]].normal
			polygons[total_f+f][1][2] = model.meshbuffers[t].vertices[model.meshbuffers[t].triangles[f].indices[1]].normal
			polygons[total_f+f][2][0] = model.meshbuffers[t].vertices[model.meshbuffers[t].triangles[f].indices[0]].uv
			polygons[total_f+f][2][1] = model.meshbuffers[t].vertices[model.meshbuffers[t].triangles[f].indices[2]].uv
			polygons[total_f+f][2][2] = model.meshbuffers[t].vertices[model.meshbuffers[t].triangles[f].indices[1]].uv
			polygons[total_f+f][3] = model.meshbuffers[t].triangles[f].material
		total_f += len(model.meshbuffers[t].triangles)
	
		for v in range(len(model.meshbuffers[t].vertices)):
			vertex_map[model.meshbuffers[t].vertices[v].ind] = model.meshbuffers[t].vertices[v].pos
	
	
	
	
	# pre-process part 2, generate buffers to feed directly to blender
	vertices = []
	for p in vertex_map:
		vertices.extend(p)
	
	vertex_indices = []
	for t in polygons:
		vertex_indices.extend(t[0])
	
	loop_start = [3*i for i in range(len(vertex_indices)//3)]
	loop_total = [3 for i in range(len(vertex_indices)//3)]
	
	material_indices = []
	for t in polygons:
		material_indices.append(t[3])
	
	uvs = []
	for t in polygons:
		uvs.extend(t[2][0])
		uvs.extend(t[2][1])
		uvs.extend(t[2][2])
	
	vertex_normals = []
	for t in polygons:
		vertex_normals.append(t[1][0])
		vertex_normals.append(t[1][1])
		vertex_normals.append(t[1][2])
		
		

	# generate geometry and vertex data in blender
	objName = (os.path.split(filepath)[1].replace(".msb",""))
	
	me_ob = bpy.data.meshes.new(objName)
	me_ob.use_auto_smooth = True
	
	for m in materials:
		me_ob.materials.append(m)
	
	me_ob.vertices.add(len(vertices)//3)
	me_ob.vertices.foreach_set("co", vertices)
	
	me_ob.loops.add(len(vertex_indices))
	me_ob.loops.foreach_set("vertex_index", vertex_indices)
	
	#me_ob.normals_split_custom_set([(0, 0, 1) for e in me_ob.loops])
	
	me_ob.polygons.add(len(loop_start))
	me_ob.polygons.foreach_set("loop_start", loop_start)
	me_ob.polygons.foreach_set("loop_total", loop_total)
	me_ob.polygons.foreach_set("material_index", material_indices)
	
	#me_ob.normals_split_custom_set([(0, 0, 1) for e in me_ob.loops])
	
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
		imtex_node.image = img_per_material[i]
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
		
	# final set up, all is ready
	me_ob.update()
	
	# split normal test
	me_ob.normals_split_custom_set(vertex_normals)
	
	me_ob.update()
	
	#create object which uses the geometry
	final_mesh = bpy.data.objects.new(name = objName, object_data = me_ob)
	bpy.context.scene.collection.objects.link(final_mesh)	
	
	final_mesh.select_set(True)
	bpy.context.view_layer.objects.active = final_mesh
	bpy.ops.object.editmode_toggle()
	bpy.ops.mesh.select_all(action = 'SELECT')
	#bpy.ops.mesh.normals_make_consistent(inside=False)
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