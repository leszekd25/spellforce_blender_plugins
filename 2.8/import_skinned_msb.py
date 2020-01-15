bl_info = {
	"name": "Import skinned SpellForce mesh (.msb/.bor)",
	"description": "Import skinned SpellForce mesh (.msb/.bor)",
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

"""
class SFVertex:
	def __init__(self):
		self.pos=[0, 0, 0]
		self.normal = [0, 0, 0]
		self.weight = [0, 0, 0, 0]
		self.uv = [0, 0]
		self.bone = [0, 0, 0, 0]
	def __init__(self, data):
		self.pos = [data[0], data[1], data[2]]
		self.normal = [data[3], data[4], data[5]]
		self.weight = [data[6], data[7], data[8], data[9]]
		self.uv = [data[10], 1.0-data[11]]
		self.bone = [data[12], data[13], data[14], data[15]]"""
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
	def __init__(self, data, offset):
		self.indices = [data[0]+offset, data[1]+offset, data[2]+offset, 0]
		self.material = data[3]
		self.group = 0

class SFMeshBuffer:
	def __init__(self):
		self.vertices = []
		self.triangles = []
		self.material = None
	def merge(self, mb, v_offset):  # only works if they're one after another
		print("MERGING")
		ret = SFMeshBuffer()
		for v in self.vertices:
			ret.vertices.append(v)
		for v in mb.vertices:
			ret.vertices.append(v)
		for t in self.triangles:
			ret.triangles.append(t)
		for t in mb.triangles:
			t.indices[0] += v_offset
			t.indices[1] += v_offset
			t.indices[2] += v_offset
			ret.triangles.append(t)
		ret.material = self.material
		return ret
		
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

		
"""class SFSkinBSI:
	def __init__(self):
		self.remap = []
		self.material_per_segment = []
		
	def load(self, fname):
		bsifile = open(fname, 'rb')
		segcount = unpack("I", bsifile.read(4))[0]
		for i in range(segcount):
			self.remap.append([])
			self.material_per_segment.append(unpack("I", bsifile.read(4)))
			indcount = unpack("I", bsifile.read(4))[0]
			for j in range(indcount):
				self.remap[i].append(unpack("I", bsifile.read(4))[0])
		print(self.remap)
		bsifile.close()
				
	def get_proper_bone(self, seg, ind):
		return self.remap[seg][ind]"""

class SFStateVector:
	def __init__(self):
		self.translation = Vector((0, 0, 0))
		self.orientation = Quaternion((1.0, 0.0, 0.0, 0.0))
	def __init__(self, t, q):
		self.translation = t
		self.orientation = q
	def to_CS(self):
		new_CS = SFCoordinateSystem()
		new_CS.translation = self.translation
		new_CS.orientation = self.orientation.to_matrix()
		return new_CS
	def to_4x4(self):
		mat_trans = Matrix.Translation(self.translation)
		mat_rot = Matrix.Identity(3)
		mat_rot.rotate(self.orientation)
		return (mat_trans @ mat_rot.to_4x4()).transposed()

class SFCoordinateSystem:
	def __init__(self):
		self.translation = mathutils.Vector((0, 0, 0))
		self.orientation = mathutils.Matrix.Identity(3)
	def to_SV(self):
		new_SV = SFStateVector()
		new_SV.translation = self.translation
		new_SV.orientation = self.orientation.normalized().to_quaternion()
		return new_SV
	def multiply_with_vector(self, vec):
		new_vec = [0, 0, 0]
		new_vec[0] = self.orientation[0][0]*vec[0]+self.orientation[1][0]*vec[1]+self.orientation[2][0]*vec[2]
		new_vec[1] = self.orientation[0][1]*vec[0]+self.orientation[1][1]*vec[1]+self.orientation[2][1]*vec[2]
		new_vec[2] = self.orientation[0][2]*vec[0]+self.orientation[1][2]*vec[1]+self.orientation[2][2]*vec[2]
		return mathutils.Vector(new_vec)
	def inverted(self):
		new_cs = SFCoordinateSystem()
		new_cs.orientation = self.orientation.inverted()
		new_cs.translation = new_cs.multiply_with_vector(mathutils.Vector((-self.translation[0], -self.translation[1], -self.translation[2])))
		return new_cs

def SF_MultiplyCoordinateSystems(cs1, cs2):
	new_cs = SFCoordinateSystem()
	translation = [0,  0,  0]
	translation[0] = cs1.orientation[0][0]*cs2.translation[0]+cs1.orientation[1][0]*cs2.translation[1]+cs1.orientation[2][0]*cs2.translation[2]+cs1.translation[0]
	translation[1] = cs1.orientation[0][1]*cs2.translation[0]+cs1.orientation[1][1]*cs2.translation[1]+cs1.orientation[2][1]*cs2.translation[2]+cs1.translation[1]
	translation[2] = cs1.orientation[0][2]*cs2.translation[0]+cs1.orientation[1][2]*cs2.translation[1]+cs1.orientation[2][2]*cs2.translation[2]+cs1.translation[2]
	orientation = mathutils.Matrix.Identity(3)
	orientation[0][0] = cs1.orientation[0][0]*cs2.orientation[0][0]+cs1.orientation[1][0]*cs2.orientation[0][1]+cs1.orientation[2][0]*cs2.orientation[0][2]
	orientation[0][1] = cs1.orientation[0][1]*cs2.orientation[0][0]+cs1.orientation[1][1]*cs2.orientation[0][1]+cs1.orientation[2][1]*cs2.orientation[0][2]
	orientation[0][2] = cs1.orientation[0][2]*cs2.orientation[0][0]+cs1.orientation[1][2]*cs2.orientation[0][1]+cs1.orientation[2][2]*cs2.orientation[0][2]
	orientation[1][0] = cs1.orientation[0][0]*cs2.orientation[1][0]+cs1.orientation[1][0]*cs2.orientation[1][1]+cs1.orientation[2][0]*cs2.orientation[1][2]
	orientation[1][1] = cs1.orientation[0][1]*cs2.orientation[1][0]+cs1.orientation[1][1]*cs2.orientation[1][1]+cs1.orientation[2][1]*cs2.orientation[1][2]
	orientation[1][2] = cs1.orientation[0][2]*cs2.orientation[1][0]+cs1.orientation[1][2]*cs2.orientation[1][1]+cs1.orientation[2][2]*cs2.orientation[1][2]
	orientation[2][0] = cs1.orientation[0][0]*cs2.orientation[2][0]+cs1.orientation[1][0]*cs2.orientation[2][1]+cs1.orientation[2][0]*cs2.orientation[2][2]
	orientation[2][1] = cs1.orientation[0][1]*cs2.orientation[2][0]+cs1.orientation[1][1]*cs2.orientation[2][1]+cs1.orientation[2][1]*cs2.orientation[2][2]
	orientation[2][2] = cs1.orientation[0][2]*cs2.orientation[2][0]+cs1.orientation[1][2]*cs2.orientation[2][1]+cs1.orientation[2][2]*cs2.orientation[2][2]
	new_cs.translation = mathutils.Vector(translation)
	new_cs.orientation = orientation
	return new_cs

def Matrix4FromCS(cs):
	mat = mathutils.Matrix.Translation(cs.translation)
	mat2 = mathutils.Matrix.Identity(3)
	mat2.rotate(cs.orientation.to_quaternion())
	mat2 = mat2.to_4x4()
	return mat*mat2

class SkinVertex:
	def __init__(self):
		self.id = -1
		self.pos = None
		self.weight = 0

class SF_Bone:
	def __init__(self):
		self.id = -1
		self.parent = -1
		self.name = ""
		self.ba_channels = [None]
		self.active_channels = 1
		self.sv = SFStateVector()
		self.blender_set = False
		self.cs_invref = SFCoordinateSystem()
		self.cs_global = SFCoordinateSystem()
		self.cs_skinning = SFCoordinateSystem()
		self.blender_vertices = []
		self.blender_length = 0
	def update_sv(self, t):
		if self.active_channels == 1:
			self.ba_channels[0].update_sv(t)
			self.sv = self.ba_channels[0].sv
		#todo: what if more channels?
	def mix_channels(self): #todo: do this
		return
	def set_animation(self, anim, w, too, toa, tob, av):
		self.ba_channel[0]=anim  #todo: proper channel check
		anim.set_start_time(too)
		anim.sv.translation = anim.interpolate_translation(toa)
		anim.sv.orientation = anim.interpolate_orientation(toa)
		anim.weight = w
		anim.time_of_origin = too
		anim.time_of_activation = toa
		anim.time_of_blnding = tob
		anim.time_of_state = toa
		self.update_sv(toa)

class SF_Skeleton:
	def __init__(self):
		self.bones = []
	def update_statevectors(self, t):
		for b in self.bones:
			b.update_sv(t)
		for b in self.bones:
			b.cs_global = b.sv.to_CS()
			if b.parent != -1:
				b.cs_global = SF_MultiplyCoordinateSystems(self.bones[b.parent].cs_global, b.cs_global)
			b.cs_skinning = SF_MultiplyCoordinateSystems(b.cs_global, b.cs_invref)
	def initialize_bones(self):
		for b in self.bones:
			b.cs_global = self.calculate_bone_cs(b.id)
			b.cs_invref = b.cs_global.inverted()
			b.cs_skinning = SFCoordinateSystem()
			#print(SF_MultiplyCoordinateSystems(b.cs_global, b.cs_invref).orientation)
	def calculate_bone_cs(self, index):
		b = self.bones[index]
		cs = b.sv.to_CS()
		while b.parent != -1:
			b = self.bones[b.parent]
			cs = SF_MultiplyCoordinateSystems(b.sv.to_CS(), cs)

def LoadMSBSkinned(context, filepath):
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
			model.meshbuffers[t].triangles.append(SFTriangle(unpack("4H", msbfile.read(8)), total_v))
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
		"""
		matdata.specular_intensity = 0
		matdata.diffuse_color = [mat.diffCol[2]/255,  mat.diffCol[1]/255,  mat.diffCol[0]/255, 1]
		matdata.specular_color = [mat.specCol[2]/255, mat.specCol[1]/255, mat.specCol[0]/255]
		matdata["SFRenderMode"] = mat.texMain.texRenderMode
		matdata["SFFlags"] = mat.texMain.flag"""
		matdata.blend_method = 'CLIP'
		matdata.use_nodes = True
		"""mtex = matdata.texture_slots.add()
		mtex.texture = tex
		mtex.texture_coords = 'UV'
		mtex.use_map_color_diffuse = True
		mtex.use_map_alpha = True
		mtex.alpha_factor = mat.texMain.texAlpha
		mtex.uv_layer = model.meshbuffers[t].material.texMain.texName#"Material "+str(t+1)"""
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
	
	
	bone_count = 0;
	bone_reference_matrices = []
	bone_inverted_matrices = []
	bone_parents = []   # int
	bone_names = []
	
	bone_pos = []  #vector
	bone_rot = []  #quaternion
	bone_vertices = []
	
	filepath2 = filepath.replace(".msb", ".bor")
	
	borfile = open(filepath2, 'r',)
	while True:
		line = borfile.readline().strip()
		if line == "[AnimData]":
			borfile.readline()
			data = borfile.readline().strip().split()
			bone_count = int(data[2])
			data = borfile.readline().strip().split()
			#num_of_sv = int(data[2])
			for i in range(bone_count):
				#b = SF_Bone()
				borfile.readline()
				borfile.readline()
				data = borfile.readline().strip().split()
				bname = ""
				for k in range(2,len(data)):
					bname = bname+data[k].replace('"','')
					if k != len(data)-1:
						bname += " "
				bone_names.append(bname)#b.name = bname
				data = borfile.readline().strip().split()
				#b.id = int(data[2])
				data = borfile.readline().strip().split()
				bone_parents.append(int(data[2]))#b.parent = int(data[2])
				borfile.readline()
				borfile.readline()
				data = borfile.readline().strip().split()   #not needed?
				data = borfile.readline().strip().split()
				bone_pos.append(Vector((float(data[2].replace(",","")), float(data[3].replace(",","")), float(data[4].replace(",","")))))
				data = borfile.readline().strip().split()
				qt = Quaternion()
				qt.w = float(data[2])
				data = borfile.readline().strip().split()
				qt.x = float(data[2].replace(",",""))
				qt.y = float(data[3].replace(",",""))
				qt.z = float(data[4].replace(",",""))
				bone_rot.append(qt)
				#b.blender_length = b.sv.translation.length
				#print(i, b.sv.translation, b.sv.orientation)
				file = borfile.readline().strip()
				bone_vertices.append([])
				while file != "}":
					#skinvertex = SkinVertex()
					borfile.readline()
					data = borfile.readline().strip().split()
					id = int(data[2])
					data = borfile.readline().strip().split()
					#pos = mathutils.Vector((float(data[2].replace(",","")), float(data[3].replace(",","")), float(data[4].replace(",",""))))
					data = borfile.readline().strip().split()
					w = float(data[2])
					borfile.readline()
					borfile.readline()
					bone_vertices[i].append([id, w])
					#skinvertex.id = id
					#skinvertex.weight = w
					#skinvertex.pos = pos
					#b.blender_vertices.append(skinvertex)
					file = borfile.readline().strip()
				#skeleton.bones.append(b)
				borfile.readline()
				borfile.readline()
				borfile.readline()
			break
	borfile.close()
	
	# create armature 
	armdata = bpy.data.armatures.new("armaturedata")
	ob_new = bpy.data.objects.new(os.path.split(filepath2)[1].replace(".bor","_skeleton"), armdata)
	bpy.context.scene.collection.objects.link(ob_new)
	if bpy.context.active_object:
		bpy.context.active_object.select_set(False)
	ob_new.select_set(True)
	bpy.context.view_layer.objects.active = ob_new
	
	if bpy.ops.object.mode_set.poll():
		bpy.ops.object.mode_set(mode='EDIT')
	
	for i in range(bone_count):
		#bone = skeleton.bones[i]
		#newparent = None
		newbone = ob_new.data.edit_bones.new(bone_names[i])
		newparent = None
		newbone.head = [0, 0, 0]
		if bone_parents[i] != -1:
			newparent = ob_new.data.edit_bones[bone_parents[i]]
			newbone.parent = newparent
		newbone.head = [0, 0, 0]
		newbone.tail = [0, 0.1, 0]
		newbone.use_inherit_rotation = True
		newbone.inherit_scale = 'NONE'
		newbone.use_local_location = False

	bpy.ops.object.mode_set(mode = 'POSE')
	print(ob_new.pose.bones.keys())
	
	for i in range(bone_count):
		posebone = ob_new.pose.bones[bone_names[i]]
		posebone.rotation_mode = 'QUATERNION'
		posebone.location = bone_pos[i]
		posebone.rotation_quaternion = bone_rot[i]
	
	bpy.ops.pose.armature_apply()
	
	bpy.ops.object.mode_set(mode = 'OBJECT')
	for i in range(bone_count):
		group = final_mesh.vertex_groups.new(name = bone_names[i])
		for v in bone_vertices[i]:
			group.add([v[0]], v[1], "ADD")
	
	
	me_ob.update()
	
	ob_new.select_set(False)
	final_mesh.select_set(True)
	bpy.context.view_layer.objects.active = final_mesh
	bpy.ops.object.mode_set(mode = 'EDIT')
	bpy.ops.mesh.select_all(action = 'SELECT')
	bpy.ops.mesh.normals_make_consistent(inside=False)
	
	bpy.ops.object.mode_set(mode = 'OBJECT')
	ob_new.select_set(True)
	final_mesh.select_set(True)
	bpy.context.view_layer.objects.active = ob_new
	bpy.ops.object.parent_set(type="ARMATURE")
	
	
	return 0


class ImportSkinnedMSB(bpy.types.Operator, ImportHelper):
	"""Object Cursor Array"""
	bl_idname = "import.msb_skinned"
	bl_label = "Import SpellForce skinned mesh (.msb)"
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
		if LoadMSBSkinned(context, self.filepath) == 0:
			return {'FINISHED'}
		return {'CANCELLED'}



def menu_func(self, context):
	self.layout.operator(ImportSkinnedMSB.bl_idname, text="Import SpellForce skinned mesh (.msb)")


def register():
	bpy.utils.register_class(ImportSkinnedMSB)
	bpy.types.TOPBAR_MT_file_import.append(menu_func)

def unregister():
	bpy.utils.unregister_class(ImportSkinnedMSB)
	bpy.types.TOPBAR_MT_file_import.remove(menu_func)


if __name__ == "__main__":
	register()