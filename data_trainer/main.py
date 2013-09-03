# BASED ON: 
# bl_info = {    
#    "name"       : "Save Layers and Passes in respectively named folders.",
#    "author"     : "Tamir Lousky (Original Author), Luciano Muñoz (added folder creation functionality)",
#    "version"    : (0, 0, 3),
#    "blender"    : (2, 68, 0),
#    "category"   : "Render",
#    "location"   : "Node Editor >> Tools",
#    "wiki_url"   : "https://github.com/Tlousky/production_scripts/wiki/save_all_renderlayers_And_passes.py",
#    "tracker_url": "https://github.com/Tlousky/production_scripts/blob/master/save_all_renderlayers_and_passes.py",
#    "description": "Save all render layers and passes to files in respectively named folders."
# }

import bpy, re, os, sys, random, math, mathutils
from mathutils import Vector
import xml.sax

class RenderBlock():
    def __init__(self):
        self.name = 0
        self.camera = RenderCamera()
        self.models = []
    def debug(self):
        print( "name", self.name )
        print( "\tmodel", self.modelname )
        print( "\tscale", self.scale )
        print( "\trotation", self.rotation )
        print( "\ttranslation", self.translation )

class RenderModel():
    def __init__(self):
        self.name = 0
        self.scale = Vector([1,1,1])
        self.rotation = Vector([0,0,0])
        self.translation = Vector([0,0,0])
        self.bvh = 0

class RenderCamera():
    def __init__(self):
        self.name = 0
        self.rotation = Vector([0,0,0])
        self.translation = Vector([0,0,0])

class RenderConfigurationHandler(xml.sax.handler.ContentHandler):
    
    def __init__(self):
        self.outputdir = 0
        self.mist_min = 0
        self.mist_max = 0
        self.statics = []
        self.camera = RenderCamera()
        self.currentcam = 0
        self.currentblock = 0
        self.currentmodel = 0

    def startElement(self, name, attributes):
        
        if name == "static":
            self.statics.append( attributes["name"] )
        
        elif name == "camera":
            type = attributes["type"]
            if ( type == "default" ):
                self.camera.name = attributes["objectname"]
                self.currentcam = self.camera
            else:
                self.currentcam = 0
            self.currentblock = 0
            self.currentmodel = 0
            
        if name == "renderblocks":
#             self.buffer = ""
            self.outputdir = attributes["outputdir"]
            self.mist_min = attributes["mist_min"]
            self.mist_max = attributes["mist_max"]
            self.renderblocks = []
            self.currentblock = 0
            self.currentcam = 0
            self.currentmodel = 0
            
        elif name == "renderblock":
            tmp = RenderBlock()
            tmp.name = attributes["name"]
            self.renderblocks.append( tmp )
            self.currentblock = tmp
            self.currentcam = 0
            self.currentmodel = 0
            
        elif name == "model" and self.currentblock != 0:
            tmp = RenderModel()
            tmp.name = attributes["name"]
            self.currentblock.models.append( tmp )
            self.currentmodel = tmp
            self.currentcam = 0
            
        elif name == "camera_offset" and self.currentblock != 0:
            self.currentcam = self.currentblock.camera
        # MODELS RELATED
        elif name == "scale" and self.currentmodel != 0:
            self.currentmodel.scale = Vector( [ float(attributes["x"]), float(attributes["y"]), float(attributes["z"]) ] )
        elif name == "rotation" and self.currentmodel != 0:
            self.currentmodel.rotation = Vector( [ float(attributes["x"]), float(attributes["y"]), float(attributes["z"]) ] )
        elif name == "translation" and self.currentmodel != 0:
            self.currentmodel.translation = Vector( [ float(attributes["x"]), float(attributes["y"]), float(attributes["z"]) ] )
        
        # CAMERA RELATED
        elif name == "rotation" and self.currentcam != 0:
            self.currentcam.rotation = Vector( [ float(attributes["x"]), float(attributes["y"]), float(attributes["z"]) ] )
        elif name == "translation" and self.currentcam != 0:
            self.currentcam.translation = Vector( [ float(attributes["x"]), float(attributes["y"]), float(attributes["z"]) ] )
            

    def characters(self, data):
        self

    def endElement(self, name):
        self

# Get blender version
version = bpy.app.version[1]
context = bpy.context
rl = context.scene.render.layers
tree  = bpy.context.scene.node_tree
links = tree.links

# GLOBALS
xmlconfpath = "data_trainer/conf/render.xml"
configuration = RenderConfigurationHandler()
outputdir = ""
basename = ""
layers = {}
pass_attr_str = 'use_pass_'

def loadxml():
    global xmlconfpath
    global outputdir
    global configuration
    controlv = 0
    workfolder = ""
    needle = '/'
    
    firsts = xmlconfpath.find( '/' )
    if ( sys.platform =='win32' ):
        needle = '\\'
    if sys.platform != 'win32':
        firsts = xmlconfpath.find( ':' )
        controlv = 1
    
    if ( firsts != controlv ):
        blp = bpy.data.filepath
        blps = blp.rfind( needle )
        if ( blps == 0 ):
            print( "IMPOSSIBLE TO LOAD XML!" )
            return
        workfolder = blp[:blps]
        xmlconfpath = workfolder + needle + xmlconfpath
    else:
        blp = xmlconfpath
        blps = blp.rfind( needle )
        if ( blps == 0 ):
            print( "IMPOSSIBLE TO LOAD XML!" )
            return
        workfolder = blp[:blps]
    parser = xml.sax.make_parser()
    parser.setContentHandler( configuration )
    parser.parse( xmlconfpath )

def cleantreenode():
    global tree
    for n in tree.nodes:
        tree.nodes.remove(n)

def find_base_name():
    blendfile = bpy.path.basename(bpy.data.filepath)
    pattern   = '^([\d\w_-]+)(\.blend)$'
    re_match  = re.match(pattern, blendfile)
    basename  = 'scene'  # Default to avoid empty strings
    if re_match:
        if len( re_match.groups() ) > 0:
            basename  = re_match.groups()[0]
    return( basename )

def collectlayers( rendername ):
    global layers
    global pass_attr_str
    for l in rl:
        imagebase = basename + "_" + l.name
        layers[l.name] = []
        passes = [ p for p in dir(l) if pass_attr_str in p ]
        for p in passes:
            if getattr( l, p ):
                pass_name = p[len(pass_attr_str):]
                file_path = imagebase + "_" + rendername + "_" + pass_name
                pass_info = {
                    'filename' : file_path,
                    'output'   : pass_name
                }
                layers[l.name].append( pass_info )

def preparenodes():
    
    global basename
    global layers
    global pass_attr_str
    
    passes = {}
    
    rl_nodes_y   = 0
    file_nodes_x = 0
    
    output_number = 0
    node = ''  # Initialize node so that it would exist outside the loop
    
    node_types = {
        67 : {
            'RL' : 'CompositorNodeRLayers',
            'OF' : 'CompositorNodeOutputFile',
            'OC' : 'CompositorNodeComposite'
        },
        66 : {
            'RL' : 'R_LAYERS',
            'OF' : 'OUTPUT_FILE',
            'OC' : 'COMPOSITE'
        },
    }
    
    # Renderlayer pass names and renderlayer node output names do not match
    # which is why we're using this dictionary (and some regular expressions
    # later to match the two)
    output_dict = {
        'ambient_occlusion' : 'AO',
        'material_index'    : 'IndexMA',
        'object_index'      : 'IndexOB',
        'reflection'        : 'Reflect',
        'refraction'        : 'Refract',
        'combined'          : 'Image'
    }
    
    
    
    for rl in layers:
        # Create a new render layer node
        node = ''
        if version > 66:
            node = tree.nodes.new( type = node_types[67]['RL'] )
        else:
            node = tree.nodes.new( type = node_types[66]['RL'] )
    
        # Set node location, label and name
        node.location = 0, rl_nodes_y
        node.label    = rl
        node.name     = rl
        
        # Select the relevant render layer
        node.layer = rl
        
        for rpass in layers[rl]:
            ## Create a new file output node
            
            # Create file output node
            output_node = ''
            if version > 66:
                output_node = tree.nodes.new( type = node_types[67]['OF'] )
            else:
                output_node = tree.nodes.new( type = node_types[66]['OF'] )
    
            # Select and activate file output node
            output_node.select = True
            tree.nodes.active  = output_node
    
            # Set node position x,y values
            file_node_x = 500 
            file_node_y = 200 * output_number
            
            name = rl + "_" + rpass['output']
            
            # Set node location, label and name
            output_node.location = file_node_x, file_node_y
            output_node.label    = name
            output_node.name     = name                
            
            # Set up file output path
            output_node.file_slots[0].path = rpass['filename']
            output_node.base_path          = context.scene.render.filepath
    
            output  = ''
            passout = rpass['output']
    
            if passout in output_dict.keys():
                output = output_dict[ passout ]
            elif "_" in passout:
                wl = passout.split("_") # Split to list of words
                # Capitalize first char in each word and rejoin with spaces
                output = " ".join( s[0].capitalize() + s[1:] for s in wl )
            else: # If one word, just capitlaize first letter
                output = passout[0].capitalize() + passout[1:]
    
            # Set up links
            if output:
                links.new( node.outputs[ output ], output_node.inputs[0] )
    
            output_number += 1
            
        rl_nodes_y += 300
        
        # Create composite node, just to enable rendering
        cnode = ''
        if version > 66:
            cnode = tree.nodes.new( type = node_types[67]['OC'] )
        else:
            cnode = tree.nodes.new( type = node_types[66]['OC'] )
    
    
        # Link composite node with the last render layer created
        links.new( node.outputs[ 'Image' ], cnode.inputs[0] )

def process():
    global basename
    global configuration
    basename = find_base_name()
    # loading xml
    loadxml()
    cam = context.scene.objects[ configuration.camera.name ]
    for rb in configuration.renderblocks:
        # camera setup
        fulltranslate = configuration.camera.translation + rb.camera.translation
        fullrotation = configuration.camera.rotation + rb.camera.rotation
        cam.location = fulltranslate
        cam.rotation_euler = ( fullrotation.x / 180 * math.pi,fullrotation.y / 180 * math.pi,fullrotation.z / 180 * math.pi )
        # object setup
        # by default, hidden everything in the scene
        for o in context.scene.objects:
            if o == cam:
                continue
            found = False
            for s in configuration.statics:
                if o.name == s:
                    found = True
                    break
            if found:
                continue
            o.hide_render = True
        
        for s in configuration.statics:
            try :
                o = context.scene.objects[ s ]
                o.hide_render = False
            except:
                continue
        
        for mod in rb.models:
            try :
                o = context.scene.objects[ mod.name ]
                o.hide_render = False
                o.location = mod.translation
                o.rotation_euler = ( mod.rotation.x / 180 * math.pi,mod.rotation.y / 180 * math.pi,mod.rotation.z / 180 * math.pi )
            except:
                print( "WARNING: in renderblock '", rb.name, "' impossible to locate object named '", mod.name, "' !!!!" )
        # cleaning nodes
        cleantreenode()
        # identifying all layers & passes
        collectlayers( rb.name )
        # creating all the required nodes
        preparenodes()
        # let's save!
        bpy.ops.render.render()

process()

