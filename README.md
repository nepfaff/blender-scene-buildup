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

### Basic Workflow

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
