# ComfyUI Video PiP · 视频画中画

单个节点完成前景/背景视频叠加、形状蒙版、位置尺寸、羽化与描边。开发版 **0.2.0**。

## 安装

在 ComfyUI 的 `custom_nodes` 目录执行：

```bash
git clone https://github.com/jinny-wj/ComfyUI-Video-PiP.git
```

保存工作流后重启 ComfyUI。无需安装或升级依赖，使用宿主 PyTorch 和标准 ComfyUI VIDEO API。
未提供自动安装脚本。与旧合并原型的迁移见 [MAINTENANCE.md](MAINTENANCE.md)。

## 使用与参数


搜索「Video PiP」或「视频画中画」。背景视频接 `background_video`，前景视频接 `foreground_video`，合成视频接「Save Video」。加载和保存之外，形状蒙版、缩放、定位与叠加都由一个节点完成。

| 参数 | 功能 |
| --- | --- |
| shape | 圆形、椭圆、矩形、圆角矩形、菱形 |
| position | 四角、居中、自定义 |
| x / y | 相对预设的偏移；自定义时为小窗左上角坐标 |
| width / height | 小窗像素尺寸；圆形取较小值作直径 |
| margin | 四角预设距画布边缘的像素距离 |
| fit | 居中裁切或拉伸 |
| opacity / feather | 透明度 / 边缘羽化，羽化为 0 时仍做约 1 像素抗锯齿 |
| corner_radius | 圆角矩形的圆角半径 |
| border_width / border_color | 内描边宽度及 #RRGGBB 颜色；宽度 0 关闭 |
| short_video | 前景较短时循环、保持末帧、结束后隐藏 |
| audio_source | 保留背景音轨或静音 |

背景决定输出画布、时长和帧率。两路输入会完整解码，当前适合短视频，不是长视频流式处理器。没有关键帧、前景音频混合或自动抠像。静态蒙版输出表示位置/几何/透明度，不包含逐帧隐藏状态。


## 示例与验证

导入 [示例工作流](examples/video-pip.json)，在两个 Load Video 节点上传自己的背景和前景视频，再运行。
素材不随仓库分发。示例只有两个加载节点、一个画中画节点和一个保存节点。

已在 ComfyUI 0.33.1 / Python 3.13.12 / PyTorch 2.10.0 / macOS ARM64 上进行 CPU 合成测试。
五种形状均导出 960×540、24 fps、144 帧的视频；A100/CUDA 尚未实测。
运行本仓库测试（使用 ComfyUI Python）：

```bash
python -B -m unittest discover -s tests -v
```

不包含字幕避让节点；它独立发布在 [ComfyUI-Subtitle-Safe-Zone](https://github.com/jinny-wj/ComfyUI-Subtitle-Safe-Zone)。
