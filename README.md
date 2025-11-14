# Scene Buildup Animation - Blender Plugin

A Blender 4.5 plugin that adds utilities for quickly creating animated scene buildup
effects.

## Features

### Animation Effects

1. **Grow From Floor**
   - Object simultaneously scales from 0 to full size
   - Moves up from below the floor to final position
   - Creates the effect of growing out of the floor

2. **Fall Down**
   - Object appears at full size above final position
   - Falls down into final position with small fall distance
   - Gravity-like appearance effect

3. **None**
   - No animation applied
   - Useful for static objects in the scene

**Note**: Child lights are automatically hidden during parent object animations to
prevent lighting artifacts during the buildup effect.

### Lighting Tools

1. **Vertex-Based Light Placement**
   - Create lights from selected vertices in Edit Mode
   - Automatically sizes and positions lights based on vertex selection
   - Area lights match selection dimensions and face orientation
   - Point lights auto-calculate radius from selection size
   - Configure intensity, color temperature, and offset
   - Lights automatically sync with parent object animations
   - Perfect for screens, lamps, and any emissive surfaces

### Material Tools

1. **Apply Mirror Material**
   - Apply perfect reflective material to selected faces
   - Works in Edit Mode on mesh objects
   - Preserves existing materials on non-selected faces
   - Creates reusable "Mirror" material with:
     - Metallic: 1.0 (full metal)
     - Roughness: 0.0 (perfect reflection)
     - Base color: White (chrome mirror)
   - **Note**: Reflections visible in Cycles or Eevee with ray tracing enabled

### Per-Object Configuration

Each object can have independent settings:
- **Effect Type**: Choose from Grow From Floor, Fall Down, or None
- **Start Frame**: When the animation begins
- **Duration**: Length of animation in frames
- **Floor Offset**: Distance below z=0 for grow effect
- **Fall Height**: Distance above final position for fall effect

## Installation

1. Create a zip file of the `blender_scene_buildup` folder:
   ```bash
   cd /path/to/blender-scene-buildup
   zip -r blender_scene_buildup.zip blender_scene_buildup/
   ```

2. In Blender 4.5:
   - Go to `Edit > Preferences > Add-ons`
   - Click `Install...`
   - Select the `blender_scene_buildup.zip` file
   - Enable the "Scene Buildup Animation" addon

## Usage

### Animating Objects

1. **Select an Object**
   - Click on the object you want to animate in the 3D viewport

2. **Open the Scene Buildup Panel**
   - Press `N` to open the sidebar
   - Click the "Scene Buildup" tab

3. **Enable Animation**
   - Check the "Enable Animation" checkbox
   - This adds animation settings to the object without affecting other objects

4. **Configure Settings**
   - Choose your desired **Effect Type**
   - Set the **Start Frame** (when animation begins)
   - Adjust the **Duration** (how long the animation lasts)
   - Fine-tune effect-specific parameters:
     - **Floor Offset** for Grow From Floor effect
     - **Fall Height** for Fall Down effect

5. **Apply Animation**
   - Click the "Apply Animation" button
   - The plugin will create keyframes for the object

6. **Preview**
   - Play the animation in the timeline to see the effect
   - Adjust settings and reapply if needed

7. **Clear Animation** (Optional)
   - Use the "Clear Animation" button to remove all keyframes from the object
   - Also clears animations from any child lights and makes them visible

### Using Lighting Tools

1. **Add Vertex-Based Lights**
   - Select a mesh object (lamp, screen, etc.)
   - Press `Tab` to enter Edit Mode
   - Select vertices that define the light area or position:
     - **For screens/monitors**: Select the face vertices of the screen
     - **For light bulbs**: Select vertices around the bulb
     - **For any emissive surface**: Select the surface area
   - Open the Scene Buildup panel (press `N`, click "Scene Buildup" tab)
   - Scroll to the "Lighting Tools" section
   - The panel shows how many vertices are selected
   - Click **Point Light** or **Area Light** to create that type

2. **Area Light Behavior**
   - Automatically sized to match the bounding box of selected vertices
   - Creates a rectangular area light matching selection dimensions
   - Positioned at the center of selected vertices
   - Automatically rotated to match face normal (if faces selected)
   - Offset slightly along normal for realistic light emission
   - Adjust **Offset** slider before creating
   - Perfect for screens, panels, and flat light sources

3. **Point Light Behavior**
   - Positioned at the center of selected vertices
   - Light radius automatically calculated from selection size
   - Average distance from center to vertices sets soft shadow radius
   - Good for bulbs, small light sources, and spherical emitters

4. **Light Settings**
   - **Intensity**: Light strength
   - **Color Temp**: WARM (yellowish), NEUTRAL (white), COOL (bluish)
   - **Offset**: Distance along surface normal for Area lights

5. **Light Animation Synchronization**
   - Lights created on animated objects automatically sync with parent animation
   - Lights are hidden during parent's buildup animation (GROW_FROM_FLOOR or FALL_DOWN)
   - Lights appear when the parent animation completes
   - Works whether lights are added before or after applying animation

### Using Material Tools

1. **Apply Mirror Material to Faces**
   - Select a mesh object with mirrors
   - Press `Tab` to enter Edit Mode
   - Select the faces that should be reflective (mirror surface)
   - Open the Scene Buildup panel (press `N`, click "Scene Buildup" tab)
   - Scroll to the "Material Tools" section
   - Click **Apply Mirror to Selected Faces**
   - The material is applied only to selected faces
   - Other faces keep their existing materials unchanged

2. **Viewing Reflections**
   - Mirror materials work automatically in **Cycles** render engine
   - For **Eevee** (default), you must enable ray tracing:
     1. Go to Render Properties (camera icon in properties panel)
     2. Under "Ray Tracing", check "Enable Ray Tracing"
     3. Adjust quality settings if needed (Resolution Scale: 2x recommended)
   - Switch viewport shading to **Material Preview** or **Rendered** mode
   - Mirrors need environment to reflect (lights, objects, or world HDRI)
   - If mirror appears grey, ensure ray tracing is enabled (Eevee) or use Cycles

### Multi-Object Selection

You can apply the same animation settings to multiple objects at once:

1. **Select Multiple Objects**
   - Use Shift+Click to select multiple objects
   - The last selected object (orange outline) is the active object

2. **Panel Shows Multi-Selection Info**
   - Displays "X objects selected"
   - Shows which object is active: "Active: [object name]"
   - Message: "Settings apply to all selected"

3. **Configure Once, Apply to All**
   - The panel displays settings from the **active object**
   - When you click "Apply Animation", those settings are copied to **all selected objects**
   - All selected objects get the same effect, timing, and parameters

4. **Clear All at Once**
   - Click "Clear Animation" to remove animation from all selected objects
   - All objects return to unconfigured state

## Development

### Project Structure
```
blender_scene_buildup/
├── blender_manifest.toml    # Addon metadata for Blender 4.5
├── __init__.py              # Main plugin code
```

### Testing
Run from Blender's Text Editor:
1. Open `__init__.py` in Text Editor
2. Click "Run Script"
3. Plugin will be loaded for testing
