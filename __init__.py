from .pip import VideoPictureInPicture
from .version import __version__

NODE_CLASS_MAPPINGS = {"VideoPictureInPicture": VideoPictureInPicture}
NODE_DISPLAY_NAME_MAPPINGS = {"VideoPictureInPicture": "视频画中画 · 形状蒙版 / Video PiP"}
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
