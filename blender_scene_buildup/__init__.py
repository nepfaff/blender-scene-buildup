"""
Scene Buildup Animation Plugin for Blender 4.5
Creates animated scene buildup effects matching 3D-Generalist rendering style.
"""

bl_info = {
    "name": "Scene Buildup Animation",
    "author": "Scene Buildup Team",
    "version": (1, 0, 0),
    "blender": (4, 5, 0),
    "location": "View3D > Sidebar > Scene Buildup",
    "description": "Create animated scene buildup effects",
    "category": "Animation",
}

import bpy
import mathutils
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
)
from bpy.types import Operator, Panel, PropertyGroup


# ============================================================================
# Compatibility Helpers
# ============================================================================

def get_fcurves_collection(action):
    """Get fcurves collection from action, compatible with Blender 4.x and 5.0+

    Returns the fcurves collection object (supports iteration and .remove())
    """
    # Check for legacy action (Blender 5.0 can have both types)
    if hasattr(action, 'is_action_legacy') and action.is_action_legacy:
        return action.fcurves
    # Old Blender versions without is_action_legacy property
    elif not hasattr(action, 'is_action_legacy') and hasattr(action, 'fcurves'):
        return action.fcurves
    # Layered action (Blender 5.0+)
    elif hasattr(action, 'layers') and action.layers:
        for layer in action.layers:
            if hasattr(layer, 'strips') and layer.strips:
                for strip in layer.strips:
                    if hasattr(strip, 'channelbags') and strip.channelbags:
                        for channelbag in strip.channelbags:
                            if channelbag.fcurves:
                                return channelbag.fcurves
    return None


# ============================================================================
# Property Group
# ============================================================================

class SceneBuildupProperties(PropertyGroup):
    """Custom properties for scene buildup animation"""

    effect_type: EnumProperty(
        name="Effect Type",
        description="Type of buildup animation to apply",
        items=[
            (
                'GROW_FROM_FLOOR',
                "Grow From Floor",
                "Object grows from small to large and moves up from floor"
            ),
            (
                'GROW_OVERSHOOT',
                "Grow with Overshoot",
                "Object grows from floor, overshoots target size, then settles back"
            ),
            (
                'FALL_DOWN',
                "Fall Down",
                "Object appears above and falls down into final position"
            ),
            ('NONE', "None", "No animation effect applied"),
        ],
        default='NONE'
    )

    enabled: BoolProperty(
        name="Enable Animation",
        description="Enable scene buildup animation for this object",
        default=False
    )

    start_frame: IntProperty(
        name="Start Frame",
        description="Frame when the animation starts",
        default=0,
        min=0,
        soft_max=1000
    )

    duration: IntProperty(
        name="Duration",
        description="Number of frames for the animation (default ~1.3s at 30fps)",
        default=15,
        min=1,
        soft_max=300
    )

    floor_offset: FloatProperty(
        name="Floor Offset",
        description="Distance below z=0 where object starts (Grow effect)",
        default=-0.05,
        soft_min=-5.0,
        soft_max=0.0,
        unit='LENGTH'
    )

    overshoot_amount: FloatProperty(
        name="Overshoot Amount",
        description="How much to overshoot target size (0.15 = 115%)",
        default=0.15,
        min=0.01,
        soft_max=0.5,
    )

    overshoot_settle_ratio: FloatProperty(
        name="Settle Ratio",
        description="Fraction of duration used for the settle-back phase",
        default=0.2,
        min=0.05,
        max=0.5,
    )

    fall_height: FloatProperty(
        name="Fall Height",
        description="Distance above final position (Fall Down effect)",
        default=0.5,
        min=0.0,
        soft_max=10.0,
        unit='LENGTH'
    )

    # Light tool settings
    light_offset: FloatProperty(
        name="Offset",
        description="Distance to offset area light along surface normal",
        default=0.01,
        min=0.0,
        max=1.0,
        soft_max=0.5,
        unit='LENGTH'
    )

    light_intensity: FloatProperty(
        name="Intensity",
        description="Light intensity in Watts",
        default=100.0,
        min=0.0,
        soft_max=500.0
    )

    light_color_temp: EnumProperty(
        name="Color",
        description="Light color temperature preset",
        items=[
            ('WARM', "Warm White", "Incandescent (yellowish)"),
            ('NEUTRAL', "Neutral White", "LED neutral white"),
            ('COOL', "Cool White", "Fluorescent (bluish)"),
        ],
        default='WARM'
    )


# ============================================================================
# Operators
# ============================================================================

class SCENEBUILD_OT_ApplyAnimation(Operator):
    """Apply scene buildup animation to the selected object"""
    bl_idname = "scene_buildup.apply_animation"
    bl_label = "Apply Animation"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        # Get settings from active object
        active_obj = context.active_object
        active_props = active_obj.scene_buildup

        if not active_props.enabled:
            msg = f"Animation not enabled for '{active_obj.name}'."
            self.report({'WARNING'}, msg)
            return {'CANCELLED'}

        # Apply to all selected objects
        success_count = 0
        for obj in context.selected_objects:
            # Copy settings from active object to this object
            props = obj.scene_buildup
            props.enabled = active_props.enabled
            props.effect_type = active_props.effect_type
            props.start_frame = active_props.start_frame
            props.duration = active_props.duration
            props.floor_offset = active_props.floor_offset
            props.fall_height = active_props.fall_height
            props.overshoot_amount = active_props.overshoot_amount
            props.overshoot_settle_ratio = active_props.overshoot_settle_ratio

            # Apply animation using copied settings
            self._apply_animation_to_object(obj, props)
            success_count += 1

        msg = f"Animation applied to {success_count} object(s)"
        self.report({'INFO'}, msg)
        return {'FINISHED'}

    def _apply_animation_to_object(self, obj, props):
        """Apply animation to a single object"""
        # Calculate frame range
        start_frame = props.start_frame
        end_frame = start_frame + props.duration

        # Store original transforms
        original_location_z = obj.location.z
        original_scale = obj.scale.copy()

        # Clear existing keyframes for the properties we'll animate
        if obj.animation_data:
            action = obj.animation_data.action
            if action:
                # Ensure object has its own action (not shared with other objects)
                if action.users > 1:
                    obj.animation_data.action = action.copy()
                    action = obj.animation_data.action

                # Remove existing keyframes for location.z and scale
                fcurves = get_fcurves_collection(action)
                if fcurves:
                    fcurves_to_remove = []
                    for fcurve in fcurves:
                        if fcurve.data_path == "location" and fcurve.array_index == 2:
                            fcurves_to_remove.append(fcurve)
                        elif fcurve.data_path == "scale":
                            fcurves_to_remove.append(fcurve)

                    for fcurve in fcurves_to_remove:
                        fcurves.remove(fcurve)

        # Apply animation based on effect type
        if props.effect_type == 'GROW_FROM_FLOOR':
            # Effect 1: Grow from floor - scale from 0 and move up from below floor

            # Hide object before animation starts (for faster rendering)
            if start_frame > 0:
                obj.hide_viewport = True
                obj.hide_render = True
                obj.keyframe_insert(
                    data_path="hide_viewport",
                    frame=start_frame - 1
                )
                obj.keyframe_insert(
                    data_path="hide_render",
                    frame=start_frame - 1
                )

            # Show object at animation start
            obj.hide_viewport = False
            obj.hide_render = False
            obj.keyframe_insert(data_path="hide_viewport", frame=start_frame)
            obj.keyframe_insert(data_path="hide_render", frame=start_frame)

            # Start keyframes (below floor, scale 0)
            obj.location.z = props.floor_offset
            obj.scale = (0.0, 0.0, 0.0)
            obj.keyframe_insert(data_path="location", index=2, frame=start_frame)
            obj.keyframe_insert(data_path="scale", frame=start_frame)

            # End keyframes (original position and scale)
            obj.location.z = original_location_z
            obj.scale = original_scale
            obj.keyframe_insert(data_path="location", index=2, frame=end_frame)
            obj.keyframe_insert(data_path="scale", frame=end_frame)

            # Set interpolation to Bezier for smooth animation
            if obj.animation_data and obj.animation_data.action:
                fcurves = get_fcurves_collection(obj.animation_data.action)
                if fcurves:
                    for fcurve in fcurves:
                        if fcurve.data_path == "location" or fcurve.data_path == "scale":
                            for keyframe in fcurve.keyframe_points:
                                keyframe.interpolation = 'BEZIER'

        elif props.effect_type == 'GROW_OVERSHOOT':
            # Effect: Grow from floor with overshoot - scale past target then settle

            # Hide object before animation starts
            if start_frame > 0:
                obj.hide_viewport = True
                obj.hide_render = True
                obj.keyframe_insert(
                    data_path="hide_viewport",
                    frame=start_frame - 1
                )
                obj.keyframe_insert(
                    data_path="hide_render",
                    frame=start_frame - 1
                )

            # Show object at animation start
            obj.hide_viewport = False
            obj.hide_render = False
            obj.keyframe_insert(data_path="hide_viewport", frame=start_frame)
            obj.keyframe_insert(data_path="hide_render", frame=start_frame)

            # Calculate overshoot frame
            settle_frames = max(1, int(props.duration * props.overshoot_settle_ratio))
            overshoot_frame = end_frame - settle_frames
            overshoot_scale = tuple(
                s * (1.0 + props.overshoot_amount) for s in original_scale
            )

            # Start keyframes (below floor, scale 0)
            obj.location.z = props.floor_offset
            obj.scale = (0.0, 0.0, 0.0)
            obj.keyframe_insert(data_path="location", index=2, frame=start_frame)
            obj.keyframe_insert(data_path="scale", frame=start_frame)

            # Overshoot keyframes (original position, overshot scale)
            obj.location.z = original_location_z
            obj.scale = overshoot_scale
            obj.keyframe_insert(data_path="location", index=2, frame=overshoot_frame)
            obj.keyframe_insert(data_path="scale", frame=overshoot_frame)

            # Settle keyframes (original position, original scale)
            obj.location.z = original_location_z
            obj.scale = original_scale
            obj.keyframe_insert(data_path="location", index=2, frame=end_frame)
            obj.keyframe_insert(data_path="scale", frame=end_frame)

            # Set interpolation to Bezier for smooth animation
            if obj.animation_data and obj.animation_data.action:
                fcurves = get_fcurves_collection(obj.animation_data.action)
                if fcurves:
                    for fcurve in fcurves:
                        if fcurve.data_path == "location" or fcurve.data_path == "scale":
                            for keyframe in fcurve.keyframe_points:
                                keyframe.interpolation = 'BEZIER'

        elif props.effect_type == 'FALL_DOWN':
            # Effect: Fall down - appear at full size above and fall to position

            # Hide object before animation starts
            if start_frame > 0:
                obj.hide_viewport = True
                obj.hide_render = True
                obj.keyframe_insert(
                    data_path="hide_viewport",
                    frame=start_frame - 1
                )
                obj.keyframe_insert(
                    data_path="hide_render",
                    frame=start_frame - 1
                )

            # Show object at animation start (above final position, full size)
            obj.hide_viewport = False
            obj.hide_render = False
            obj.keyframe_insert(data_path="hide_viewport", frame=start_frame)
            obj.keyframe_insert(data_path="hide_render", frame=start_frame)

            # Convert world-Z fall offset to parent-local space
            world_fall = mathutils.Vector((0, 0, props.fall_height))
            if obj.parent:
                inv_rot = obj.parent.matrix_world.to_3x3().inverted()
                local_fall = inv_rot @ world_fall
            else:
                local_fall = world_fall

            original_location = obj.location.copy()
            obj.location = original_location + local_fall
            obj.keyframe_insert(data_path="location", frame=start_frame)

            # End keyframe (original position, keep full size)
            obj.location = original_location
            obj.keyframe_insert(data_path="location", frame=end_frame)

            # Restore original scale (no scaling animation for fall effect)
            obj.scale = original_scale

            # Set interpolation to Bezier for smooth animation
            if obj.animation_data and obj.animation_data.action:
                fcurves = get_fcurves_collection(obj.animation_data.action)
                if fcurves:
                    for fcurve in fcurves:
                        if fcurve.data_path == "location":
                            for keyframe in fcurve.keyframe_points:
                                keyframe.interpolation = 'BEZIER'

        elif props.effect_type == 'NONE':
            # Effect 3: None - just restore original transforms
            obj.location.z = original_location_z
            obj.scale = original_scale

        # Hide child lights during animation
        if props.effect_type in ('GROW_FROM_FLOOR', 'GROW_OVERSHOOT', 'FALL_DOWN'):
            self._hide_child_lights_during_animation(obj, start_frame, end_frame)

    def _hide_child_lights_during_animation(self, obj, start_frame, end_frame):
        """Hide child light objects during parent's animation"""
        for child in obj.children:
            # Check if child is a light object
            if child.type == 'LIGHT':
                # Hide from start until animation ends
                if start_frame > 0:
                    # Before animation starts
                    child.hide_viewport = True
                    child.hide_render = True
                    child.keyframe_insert(
                        data_path="hide_viewport",
                        frame=start_frame - 1
                    )
                    child.keyframe_insert(
                        data_path="hide_render",
                        frame=start_frame - 1
                    )

                # Keep hidden during animation
                child.hide_viewport = True
                child.hide_render = True
                child.keyframe_insert(
                    data_path="hide_viewport",
                    frame=start_frame
                )
                child.keyframe_insert(
                    data_path="hide_render",
                    frame=start_frame
                )
                child.keyframe_insert(
                    data_path="hide_viewport",
                    frame=end_frame - 1
                )
                child.keyframe_insert(
                    data_path="hide_render",
                    frame=end_frame - 1
                )

                # Show when animation completes
                child.hide_viewport = False
                child.hide_render = False
                child.keyframe_insert(
                    data_path="hide_viewport",
                    frame=end_frame
                )
                child.keyframe_insert(
                    data_path="hide_render",
                    frame=end_frame
                )


class SCENEBUILD_OT_ClearAnimation(Operator):
    """Clear scene buildup animation from all selected objects"""
    bl_idname = "scene_buildup.clear_animation"
    bl_label = "Clear Animation"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        # Clear animation from all selected objects
        cleared_count = 0
        for obj in context.selected_objects:
            props = obj.scene_buildup

            if obj.animation_data:
                # Remove all animation data
                obj.animation_data_clear()
                cleared_count += 1

            # Clear child light animations
            for child in obj.children:
                if child.type == 'LIGHT' and child.animation_data:
                    child.animation_data_clear()
                    # Ensure lights are visible after clearing
                    child.hide_viewport = False
                    child.hide_render = False

            # Reset all properties to defaults
            props.enabled = False
            props.effect_type = 'NONE'

        if cleared_count > 0:
            msg = f"Animation cleared from {cleared_count} object(s)"
            self.report({'INFO'}, msg)
        else:
            self.report({'WARNING'}, "No animation data found")

        return {'FINISHED'}


class SCENEBUILD_OT_AddLightToLamp(Operator):
    """Create light based on selected vertices in Edit Mode"""
    bl_idname = "scene_buildup.add_light_to_lamp"
    bl_label = "Add Light from Vertices"
    bl_options = {'REGISTER', 'UNDO'}

    light_type: EnumProperty(
        name="Light Type",
        items=[
            ('POINT', "Point", "Omnidirectional point light"),
            ('AREA', "Area", "Area light with soft shadows"),
        ],
        default='POINT'
    )

    @classmethod
    def poll(cls, context):
        return (
            context.mode == 'EDIT_MESH' and
            context.edit_object is not None and
            context.edit_object.type == 'MESH'
        )

    def execute(self, context):
        import bmesh
        from mathutils import Vector

        obj = context.edit_object
        props = obj.scene_buildup  # Read settings from PropertyGroup
        bm = bmesh.from_edit_mesh(obj.data)

        # Get selected vertices
        selected_verts = [v for v in bm.verts if v.select]

        if not selected_verts:
            self.report({'WARNING'}, "No vertices selected")
            return {'CANCELLED'}

        # Calculate bounds in world space
        matrix_world = obj.matrix_world
        coords = [matrix_world @ v.co for v in selected_verts]

        min_x = min(co.x for co in coords)
        max_x = max(co.x for co in coords)
        min_y = min(co.y for co in coords)
        max_y = max(co.y for co in coords)
        min_z = min(co.z for co in coords)
        max_z = max(co.z for co in coords)

        # Calculate center
        center = Vector((
            (min_x + max_x) / 2.0,
            (min_y + max_y) / 2.0,
            (min_z + max_z) / 2.0
        ))

        # Calculate sizes
        size_x = max(max_x - min_x, 0.1)
        size_y = max(max_y - min_y, 0.1)
        size_z = max(max_z - min_z, 0.1)

        # Get average normal from selected faces (if any)
        selected_faces = [f for f in bm.faces if f.select]
        avg_normal = None

        if selected_faces:
            avg_normal = Vector((0, 0, 0))
            for f in selected_faces:
                avg_normal += f.normal
            avg_normal.normalize()
            # Transform to world space
            avg_normal = matrix_world.to_3x3() @ avg_normal
            avg_normal.normalize()

        # Color mapping
        colors = {
            'WARM': (1.0, 0.95, 0.8),
            'NEUTRAL': (1.0, 1.0, 1.0),
            'COOL': (0.9, 1.0, 1.0),
        }

        # Create light data
        light_name = f"{obj.name}_Light"
        light_data = bpy.data.lights.new(
            name=light_name,
            type=self.light_type
        )
        light_data.energy = props.light_intensity
        light_data.color = colors[props.light_color_temp]

        # Configure based on light type
        if self.light_type == 'AREA':
            light_data.shape = 'RECTANGLE'

            # Use two largest dimensions from bounding box
            # Works correctly for any rotation
            dimensions = sorted([size_x, size_y, size_z], reverse=True)
            light_data.size = dimensions[0]  # Largest dimension
            light_data.size_y = dimensions[1]  # Second largest
        elif self.light_type == 'POINT':
            # Calculate average radius for soft shadow size
            avg_radius = (
                sum((co - center).length for co in coords) / len(coords)
            )
            light_data.shadow_soft_size = max(avg_radius, 0.1)

        # Create light object
        light_obj = bpy.data.objects.new(
            name=light_name,
            object_data=light_data
        )
        context.collection.objects.link(light_obj)

        # Position light in world space (before parenting)
        if self.light_type == 'AREA' and avg_normal:
            # Offset along normal for area lights (uses settings value)
            light_obj.location = center + (avg_normal * props.light_offset)
        else:
            # Point light or no normal: place at center
            light_obj.location = center

        # Rotate area light to match surface normal
        if self.light_type == 'AREA' and avg_normal:
            # Area lights point down their local -Z axis
            default_dir = Vector((0, 0, -1))
            rotation_quat = default_dir.rotation_difference(avg_normal)
            light_obj.rotation_mode = 'QUATERNION'
            light_obj.rotation_quaternion = rotation_quat

        # Parent light to source mesh (preserves world transform)
        light_obj.parent = obj
        light_obj.matrix_parent_inverse = obj.matrix_world.inverted()

        # Sync with parent animation if it exists
        if (props.enabled and
            props.effect_type in ('GROW_FROM_FLOOR', 'GROW_OVERSHOOT', 'FALL_DOWN')):
            start_frame = props.start_frame
            end_frame = start_frame + props.duration

            # Hide light during parent's animation
            if start_frame > 0:
                light_obj.hide_viewport = True
                light_obj.hide_render = True
                light_obj.keyframe_insert(
                    data_path="hide_viewport", frame=start_frame - 1
                )
                light_obj.keyframe_insert(
                    data_path="hide_render", frame=start_frame - 1
                )

            # Keep hidden during animation
            light_obj.hide_viewport = True
            light_obj.hide_render = True
            light_obj.keyframe_insert(
                data_path="hide_viewport", frame=start_frame
            )
            light_obj.keyframe_insert(
                data_path="hide_render", frame=start_frame
            )
            light_obj.keyframe_insert(
                data_path="hide_viewport", frame=end_frame - 1
            )
            light_obj.keyframe_insert(
                data_path="hide_render", frame=end_frame - 1
            )

            # Show when animation completes
            light_obj.hide_viewport = False
            light_obj.hide_render = False
            light_obj.keyframe_insert(
                data_path="hide_viewport", frame=end_frame
            )
            light_obj.keyframe_insert(
                data_path="hide_render", frame=end_frame
            )

        msg = f"Created {self.light_type} light from {len(selected_verts)} verts"
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class SCENEBUILD_OT_ApplyMirrorMaterial(Operator):
    """Apply mirror material to selected faces in Edit Mode"""
    bl_idname = "scene_buildup.apply_mirror_material"
    bl_label = "Apply Mirror Material"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (
            context.mode == 'EDIT_MESH' and
            context.edit_object is not None and
            context.edit_object.type == 'MESH'
        )

    def execute(self, context):
        import bmesh

        obj = context.edit_object

        # Get or create mirror material
        mat_name = "Mirror"
        if mat_name in bpy.data.materials:
            mirror_mat = bpy.data.materials[mat_name]
        else:
            mirror_mat = self.create_mirror_material(mat_name)

        # Ensure material is in object's slots
        if mirror_mat.name not in obj.data.materials:
            obj.data.materials.append(mirror_mat)

        # Get material index
        mat_index = obj.data.materials.find(mirror_mat.name)

        # Get BMesh and assign to selected faces
        bm = bmesh.from_edit_mesh(obj.data)

        selected_faces = [f for f in bm.faces if f.select]
        if not selected_faces:
            self.report({'WARNING'}, "No faces selected")
            return {'CANCELLED'}

        # Assign material index to selected faces
        for face in selected_faces:
            face.material_index = mat_index

        # Update mesh
        bmesh.update_edit_mesh(obj.data)

        msg = f"Applied mirror material to {len(selected_faces)} face(s)"
        self.report({'INFO'}, msg)
        return {'FINISHED'}

    def create_mirror_material(self, name):
        """Create perfect chrome mirror material using Principled BSDF"""
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Clear default nodes for clean setup
        nodes.clear()

        # Create Principled BSDF node
        bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
        bsdf.location = (0, 0)

        # Create Material Output node
        output = nodes.new(type='ShaderNodeOutputMaterial')
        output.location = (300, 0)

        # Configure for perfect chrome mirror
        bsdf.inputs['Base Color'].default_value = (1.0, 1.0, 1.0, 1.0)
        bsdf.inputs['Metallic'].default_value = 1.0
        bsdf.inputs['Roughness'].default_value = 0.0
        # Specular uses default 0.5 which is correct for mirrors

        # Link shader to output
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

        return mat


# ============================================================================
# UI Panels
# ============================================================================

class SCENEBUILD_PT_MainPanel(Panel):
    """Main panel for scene buildup animation in 3D viewport sidebar"""
    bl_label = "Scene Buildup"
    bl_idname = "SCENEBUILD_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Scene Buildup"

    @classmethod
    def poll(cls, context):
        """Only show panel when an object is selected"""
        return context.active_object is not None

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        props = obj.scene_buildup
        selected_count = len(context.selected_objects)

        # Header with object/selection info
        box = layout.box()
        if selected_count > 1:
            box.label(text=f"{selected_count} objects selected", icon='OUTLINER')
            box.label(text=f"Active: {obj.name}", icon='OBJECT_DATA')
            box.separator()
            row = box.row()
            row.label(text="Settings apply to all selected", icon='INFO')
        else:
            box.label(text=f"Object: {obj.name}", icon='OBJECT_DATA')

        # Enable toggle
        layout.separator()
        layout.prop(props, "enabled", toggle=True)

        # Only show settings if enabled
        if props.enabled:
            layout.separator()

            # Effect settings box
            box = layout.box()
            box.label(text="Effect Settings:", icon='ANIM')
            box.prop(props, "effect_type")

            # Timing controls
            col = box.column(align=True)
            col.prop(props, "start_frame")
            col.prop(props, "duration")

            # Effect-specific parameters
            if props.effect_type == 'GROW_FROM_FLOOR':
                box.separator()
                box.prop(props, "floor_offset", slider=True)

            elif props.effect_type == 'GROW_OVERSHOOT':
                box.separator()
                box.prop(props, "floor_offset", slider=True)
                box.prop(props, "overshoot_amount", slider=True)
                box.prop(props, "overshoot_settle_ratio", slider=True)

            elif props.effect_type == 'FALL_DOWN':
                box.separator()
                box.prop(props, "fall_height", slider=True)

            # Action buttons
            layout.separator()
            col = layout.column(align=True)
            col.scale_y = 1.5

            row = col.row(align=True)
            row.operator(
                "scene_buildup.apply_animation",
                icon='PLAY',
                text="Apply Animation"
            )

            row = col.row(align=True)
            row.operator(
                "scene_buildup.clear_animation",
                icon='X',
                text="Clear Animation"
            )

        else:
            # Show hint when not enabled
            box = layout.box()
            box.label(text="Enable animation to configure", icon='INFO')

        # Lighting Tools section (always visible)
        layout.separator()
        layout.separator()
        box = layout.box()
        box.label(text="Lighting Tools:", icon='LIGHT')

        # Only show in Edit Mode with mesh
        if context.mode == 'EDIT_MESH' and context.edit_object:
            import bmesh
            bm = bmesh.from_edit_mesh(context.edit_object.data)
            vert_count = sum(1 for v in bm.verts if v.select)

            if vert_count > 0:
                box.label(
                    text=f"{vert_count} vertices selected",
                    icon='VERTEXSEL'
                )

                # Get properties for adjustable settings
                light_props = context.edit_object.scene_buildup

                # Light settings (adjustable before creating)
                col = box.column(align=True)
                col.prop(light_props, "light_intensity")
                col.prop(light_props, "light_color_temp")
                col.prop(light_props, "light_offset", slider=True)

                box.separator()

                # Point Light button
                op = box.operator(
                    "scene_buildup.add_light_to_lamp",
                    icon='LIGHT_POINT',
                    text="Point Light"
                )
                op.light_type = 'POINT'

                # Area Light button
                op = box.operator(
                    "scene_buildup.add_light_to_lamp",
                    icon='LIGHT_AREA',
                    text="Area Light"
                )
                op.light_type = 'AREA'
            else:
                box.label(text="Select vertices to place light", icon='INFO')
        else:
            box.label(text="Enter Edit Mode to use", icon='INFO')

        # Material Tools section (always visible)
        layout.separator()
        box = layout.box()
        box.label(text="Material Tools:", icon='MATERIAL')

        # Only show for mesh in edit mode
        if context.mode == 'EDIT_MESH' and context.edit_object:
            box.operator(
                "scene_buildup.apply_mirror_material",
                icon='MATSPHERE',
                text="Apply Mirror to Selected Faces"
            )
        else:
            box.label(
                text="Enter Edit Mode to use",
                icon='INFO'
            )


# ============================================================================
# Registration
# ============================================================================

classes = (
    SceneBuildupProperties,
    SCENEBUILD_OT_ApplyAnimation,
    SCENEBUILD_OT_ClearAnimation,
    SCENEBUILD_OT_AddLightToLamp,
    SCENEBUILD_OT_ApplyMirrorMaterial,
    SCENEBUILD_PT_MainPanel,
)

def register():
    """Register all classes and attach properties"""
    # Register classes in dependency order
    for cls in classes:
        bpy.utils.register_class(cls)

    # Attach properties to Object type (after PropertyGroup is registered)
    bpy.types.Object.scene_buildup = PointerProperty(type=SceneBuildupProperties)

def unregister():
    """Unregister all classes and remove properties"""
    # Remove attached properties first (if they exist)
    if hasattr(bpy.types.Object, 'scene_buildup'):
        del bpy.types.Object.scene_buildup

    # Unregister classes in reverse order (with error handling)
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass  # Class wasn't registered, skip it

# Allow running as standalone script for testing
if __name__ == "__main__":
    # Unregister first if already registered (for script re-runs)
    try:
        unregister()
    except:
        pass
    # Register fresh
    register()
