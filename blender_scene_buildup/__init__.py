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
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
)
from bpy.types import Operator, Panel, PropertyGroup


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

    fall_height: FloatProperty(
        name="Fall Height",
        description="Distance above final position (Fall Down effect)",
        default=0.5,
        min=0.0,
        soft_max=10.0,
        unit='LENGTH'
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
                fcurves_to_remove = []
                for fcurve in action.fcurves:
                    if fcurve.data_path == "location" and fcurve.array_index == 2:
                        fcurves_to_remove.append(fcurve)
                    elif fcurve.data_path == "scale":
                        fcurves_to_remove.append(fcurve)

                for fcurve in fcurves_to_remove:
                    action.fcurves.remove(fcurve)

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
                for fcurve in obj.animation_data.action.fcurves:
                    if fcurve.data_path == "location" or fcurve.data_path == "scale":
                        for keyframe in fcurve.keyframe_points:
                            keyframe.interpolation = 'BEZIER'

        elif props.effect_type == 'FALL_DOWN':
            # Effect 2: Fall down - appear at full size above and fall to position

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

            obj.location.z = original_location_z + props.fall_height
            obj.keyframe_insert(data_path="location", index=2, frame=start_frame)

            # End keyframe (original position, keep full size)
            obj.location.z = original_location_z
            obj.keyframe_insert(data_path="location", index=2, frame=end_frame)

            # Restore original scale (no scaling animation for fall effect)
            obj.scale = original_scale

            # Set interpolation to Bezier for smooth animation
            if obj.animation_data and obj.animation_data.action:
                for fcurve in obj.animation_data.action.fcurves:
                    if fcurve.data_path == "location" and fcurve.array_index == 2:
                        for keyframe in fcurve.keyframe_points:
                            keyframe.interpolation = 'BEZIER'

        elif props.effect_type == 'NONE':
            # Effect 3: None - just restore original transforms
            obj.location.z = original_location_z
            obj.scale = original_scale


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

            # Reset all properties to defaults
            props.enabled = False
            props.effect_type = 'NONE'

        if cleared_count > 0:
            msg = f"Animation cleared from {cleared_count} object(s)"
            self.report({'INFO'}, msg)
        else:
            self.report({'WARNING'}, "No animation data found")

        return {'FINISHED'}


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


# ============================================================================
# Registration
# ============================================================================

classes = (
    SceneBuildupProperties,
    SCENEBUILD_OT_ApplyAnimation,
    SCENEBUILD_OT_ClearAnimation,
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
