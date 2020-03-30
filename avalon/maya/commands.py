"""Used for scripting

These are used in other scripts and mostly require explicit input,
such as which specific nodes they apply to.

For interactive use, see :mod:`interactive.py`

"""

from maya import cmds

from .. import io, api


def reset_frame_range():
    """Set frame range to current asset"""
    # Set FPS first
    fps = {15: 'game',
           24: 'film',
           25: 'pal',
           30: 'ntsc',
           48: 'show',
           50: 'palf',
           60: 'ntscf',
           23.98: '23.976fps',
           23.976: '23.976fps',
           29.97: '29.97fps',
           47.952: '47.952fps',
           47.95: '47.952fps',
           59.94: '59.94fps',
           44100: '44100fps',
           48000: '48000fps'
           }.get(float(api.Session.get("AVALON_FPS", 25)), "pal")

    cmds.currentUnit(time=fps)

    # Set frame start/end
    asset_name = api.Session["AVALON_ASSET"]
    asset = io.find_one({"name": asset_name, "type": "asset"})

    frame_start = asset["data"].get(
        "frameStart",
        # backwards compatibility
        asset["data"].get("edit_in")
    )
    frame_end = asset["data"].get(
        "frameEnd",
        # backwards compatibility
        asset["data"].get("edit_out")
    )

    if frame_start is None or frame_end is None:
        cmds.warning("No edit information found for %s" % asset_name)
        return

    handles = int(asset["data"].get("handles", 0))
    handle_start = int(asset["data"].get("handleStart", handles))
    handle_end = int(asset["data"].get("handleEnd", handles))

    frame_start -= handle_start
    frame_end += handle_end

    cmds.playbackOptions(minTime=frame_start)
    cmds.playbackOptions(maxTime=frame_end)
    cmds.playbackOptions(animationStartTime=frame_start)
    cmds.playbackOptions(animationEndTime=frame_end)
    cmds.playbackOptions(minTime=frame_start)
    cmds.playbackOptions(maxTime=frame_end)
    cmds.currentTime(frame_start)

    cmds.setAttr("defaultRenderGlobals.startFrame", frame_start)
    cmds.setAttr("defaultRenderGlobals.endFrame", frame_end)


def reset_resolution():
    project = io.find_one({"type": "project"})

    try:
        resolution_width = project["data"].get(
            "resolutionWidth",
            # backwards compatibility
            project["data"].get("resolution_width", 1920)
        )
        resolution_height = project["data"].get(
            "resolutionHeight",
            # backwards compatibility
            project["data"].get("resolution_height", 1080)
        )
    except KeyError:
        cmds.warning("No resolution information found for %s"
                     % project["name"])
        return

    cmds.setAttr("defaultResolution.width", resolution_width)
    cmds.setAttr("defaultResolution.height", resolution_height)
