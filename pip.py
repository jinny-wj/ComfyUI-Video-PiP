"""Video picture-in-picture. Host libraries are imported only at execution."""
import math

SHAPES = ['圆形', '椭圆', '矩形', '圆角矩形', '菱形']
POSITIONS = ['右下', '左下', '右上', '左上', '居中', '自定义']


def composite_frames(background, foreground, background_fps, foreground_fps,
                     shape='圆形', position='右下', x=0, y=0, width=240, height=240,
                     margin=24, fit='居中裁切', opacity=1.0, feather=1.0,
                     corner_radius=32, border_width=4, border_color='#FFFFFF',
                     short_video='循环'):
    import torch
    import torch.nn.functional as F

    for name, frames in [('背景', background), ('前景', foreground)]:
        if frames.ndim != 4 or frames.shape[-1] != 3 or min(frames.shape[:3]) < 1:
            raise ValueError(name + '必须包含 RGB 视频帧。')
    if shape not in SHAPES or position not in POSITIONS or fit not in ['居中裁切', '拉伸'] or short_video not in ['循环', '保持末帧', '结束后隐藏']:
        raise ValueError('未知的形状、位置、适配或时长选项。')
    if not all(math.isfinite(v) and v > 0 for v in [background_fps, foreground_fps]):
        raise ValueError('视频帧率必须为正数。')
    if not 1 <= width <= 4096 or not 1 <= height <= 4096:
        raise ValueError('小窗宽高必须在 1–4096 像素内。')
    if not math.isfinite(opacity) or not 0 <= opacity <= 1 or not math.isfinite(feather) or not 0 <= feather <= 64:
        raise ValueError('透明度或羽化参数超出范围。')
    if not 0 <= border_width <= 64 or not 0 <= corner_radius <= 2048:
        raise ValueError('描边或圆角参数超出范围。')
    try:
        if len(border_color) != 7 or not border_color.startswith('#'):
            raise ValueError()
        rgb = [int(border_color[j:j+2], 16)/255 for j in (1, 3, 5)]
    except (ValueError, TypeError):
        raise ValueError('描边颜色使用 #RRGGBB，例如 #FFFFFF。') from None

    n, h, w, _ = background.shape
    if shape == '圆形':
        width = height = min(width, height)
    anchors = {'右下': (w-width-margin, h-height-margin), '左下': (margin, h-height-margin),
               '右上': (w-width-margin, margin), '左上': (margin, margin),
               '居中': ((w-width)//2, (h-height)//2), '自定义': (0, 0)}
    left, top = anchors[position]
    left, top = left + x, top + y
    device = background.device
    yy, xx = torch.meshgrid(torch.arange(height, device=device, dtype=torch.float32),
                            torch.arange(width, device=device, dtype=torch.float32), indexing='ij')
    px, py = (xx + .5 - width/2).abs(), (yy + .5 - height/2).abs()
    if shape in ['圆形', '椭圆']:
        distance = (torch.sqrt((px/(width/2))**2 + (py/(height/2))**2)-1)*min(width, height)/2
    elif shape == '菱形':
        distance = (px/(width/2)+py/(height/2)-1)/math.sqrt((2/width)**2+(2/height)**2)
    else:
        radius = min(corner_radius, width/2, height/2) if shape == '圆角矩形' else 0
        qx, qy = px-(width/2-radius), py-(height/2-radius)
        distance = torch.sqrt(qx.clamp(min=0)**2+qy.clamp(min=0)**2) + torch.maximum(qx, qy).clamp(max=0)-radius
    ramp = max(1.0, feather)
    alpha = (.5-distance/ramp).clamp(0, 1)
    inner = (.5-(distance+border_width)/ramp).clamp(0, 1)
    ring = (alpha-inner).clamp(0, 1) if border_width else torch.zeros_like(alpha)
    color = torch.tensor(rgb, device=device, dtype=torch.float32)
    output = background.clone()
    full_mask = torch.zeros((1, h, w), device=device, dtype=torch.float32)
    x0, y0, x1, y1 = max(0, left), max(0, top), min(w, left+width), min(h, top+height)
    if x1 <= x0 or y1 <= y0:
        return output, full_mask
    sx, sy = x0-left, y0-top
    a = alpha[sy:sy+y1-y0, sx:sx+x1-x0, None]
    r = ring[sy:sy+y1-y0, sx:sx+x1-x0, None]
    full_mask[0, y0:y1, x0:x1] = a[..., 0]*opacity
    # Resize one frame at a time: avoids an extra full-resolution foreground batch.
    previous_index, resized = None, None
    for i in range(n):
        index = math.floor(i * foreground_fps / background_fps + 1e-7)
        if index >= len(foreground):
            if short_video == '结束后隐藏':
                continue
            index = index % len(foreground) if short_video == '循环' else len(foreground)-1
        if index != previous_index:
            source = foreground[index:index+1].to(device=device, dtype=torch.float32).movedim(-1, 1)
            if fit == '居中裁切':
                ratio = max(width/source.shape[3], height/source.shape[2])
                nh, nw = max(height, math.ceil(source.shape[2]*ratio)), max(width, math.ceil(source.shape[3]*ratio))
                source = F.interpolate(source, size=(nh, nw), mode='bilinear', align_corners=False)
                source = source[:, :, (nh-height)//2:(nh-height)//2+height, (nw-width)//2:(nw-width)//2+width]
            else:
                source = F.interpolate(source, size=(height, width), mode='bilinear', align_corners=False)
            resized = source[0].movedim(0, -1)[sy:sy+y1-y0, sx:sx+x1-x0]
            previous_index = index
        base = background[i, y0:y1, x0:x1].float()
        output[i, y0:y1, x0:x1] = (base*(1-a*opacity) + (resized*(a-r)+color*r)*opacity).to(output.dtype)
    return output, full_mask


class VideoPictureInPicture:
    CATEGORY = 'Video/Picture in Picture'
    FUNCTION = 'compose'
    RETURN_TYPES = ('VIDEO', 'MASK')
    RETURN_NAMES = ('合成视频', '静态小窗蒙版')
    DESCRIPTION = '背景为底层并决定输出时长/帧率；前景在上层。直接连接两个 VIDEO，输出连接保存视频。'

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'background_video': ('VIDEO', {'tooltip': '背景视频（底层）：决定输出画布、时长和帧率。'}),
            'foreground_video': ('VIDEO', {'tooltip': '前景视频（上层）：显示在蒙版小窗内。'}),
            'shape': (SHAPES,), 'position': (POSITIONS,),
            'x': ('INT', {'default': 0, 'min': -4096, 'max': 4096, 'tooltip': '相对位置预设的水平偏移；自定义时为左上角 x。'}),
            'y': ('INT', {'default': 0, 'min': -4096, 'max': 4096, 'tooltip': '相对位置预设的垂直偏移；自定义时为左上角 y。'}),
            'width': ('INT', {'default': 240, 'min': 1, 'max': 4096}),
            'height': ('INT', {'default': 240, 'min': 1, 'max': 4096, 'tooltip': '圆形取宽高较小值作为直径；椭圆分别使用宽高。'}),
            'margin': ('INT', {'default': 24, 'min': 0, 'max': 2048}),
            'fit': (['居中裁切', '拉伸'],),
            'opacity': ('FLOAT', {'default': 1.0, 'min': 0.0, 'max': 1.0, 'step': .05}),
            'feather': ('FLOAT', {'default': 1.0, 'min': 0.0, 'max': 64.0, 'step': 1.0}),
            'corner_radius': ('INT', {'default': 32, 'min': 0, 'max': 2048, 'tooltip': '仅圆角矩形生效。'}),
            'border_width': ('INT', {'default': 4, 'min': 0, 'max': 64}),
            'border_color': ('STRING', {'default': '#FFFFFF'}),
            'short_video': (['循环', '保持末帧', '结束后隐藏'], {'tooltip': '前景比背景短时的处理方式；按两路各自帧率对齐时间。'}),
            'audio_source': (['背景声音', '静音'],),
        }}

    def compose(self, background_video, foreground_video, audio_source='背景声音', **settings):
        from comfy_api.latest import InputImpl, Types
        background = background_video.get_components()
        foreground = foreground_video.get_components()
        frames, mask = composite_frames(background.images, foreground.images,
                                        float(background.frame_rate), float(foreground.frame_rate), **settings)
        video = InputImpl.VideoFromComponents(Types.VideoComponents(
            images=frames, audio=background.audio if audio_source == '背景声音' else None,
            frame_rate=background.frame_rate))
        return video, mask
