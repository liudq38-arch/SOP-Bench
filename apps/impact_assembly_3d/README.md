# IMPACT 3D 拆装观察室

入口：<http://10.112.70.171:7864>。本地静态页面，Three.js 0.160.1 与 OrbitControls 已随项目保存，运行时不访问 CDN。

从项目根目录启动：

```sh
.venv-review/bin/python -u scripts/serve_assembly_3d.py
```

A 型：14 个观察/拆装步骤、15 个可点选组件组，安装与拆卸切换、播放/暂停、速度、逐步跳转、任意进度、分解程度、壳体透视、部件名称、旋转/缩放/平移。三类工具接触示意：银色扳手、红黄十字、绿黑 Torx。拨杆/弹簧/垫圈合为一组，因此组件组数量不等于原 ASR 组件数。

B 型：12 步、11 个可点选组件组，支持安装/拆卸及与A相同的播放、暂停、逐步、进度、分解和视角控制。[直接打开B型](http://10.112.70.171:7864/?model=B)。独立几何和流程见 `model_b.js`。右侧可展开B项目原图对照。

B按官方爆炸图补齐两颗壳体连接螺丝、银灰壳体及轴承板、带铜色换向器的转子和图示支承法兰、远端适配板、两颗轴承板螺丝和较细侧手柄。未加入A的拨杆/弹簧/垫圈或适配板M4螺母。壳体连接螺丝用红黄十字的示意有局部B拆卸帧佐证；轴承板连接采用已观察B样例的一字工具，不代表排他性工具规范。

## 正确性边界

这是程序化几何示意，不是实测模型、精确 CAD 或经过机械验证的装配模拟。部件尺寸、移动路径、螺纹、齿形啮合、工具转数和扭矩未校准；A的70秒/B的60秒是演示时长。A拨杆/弹簧/垫圈的摆放仅表示配套关系，不表示已确认的内部叠放。B远端适配板保持方式未核实，仅演示对位；B装拆步骤是按图示连接编排的示意，非官方逐步工艺。B轴承板螺丝槽口按实际一字工具样例简化，不是精确复刻，保持螺母工具为六角接口示意。独立步骤可合法换序；不能将本动画用作唯一正确顺序或异常 GT。当前不绘制手部与施力。

连接与工具映射复用 `configs/impact_qa/review_reference_v1.json`、`reports/impact_qa/impact_object_knowledge.md` 中已核对资料。原始图像依据：

- [A 型官方手册](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/website/assets/figures/Manual_Book.svg)
- [A/B 官方结构图](https://github.com/Kratos-Wen/IMPACT/blob/4fed5faa5f05f7aece55712e458defa1f372b248/website/assets/figures/2anglegrinderconfig.svg)

## 验证

`scripts/check_assembly_3d_browser.py` 用 Firefox/WebDriver 验证实际 WebGL 渲染、A/B播放/暂停稳定性、进度、逐步、装拆切换、四类工具、B十个运动组件/正反终态、B直达链接、A/B/A切换和移动端溢出。当前结果和截图位于 `outputs/impact_qa/assembly_3d/b_animation_v2/`；来源及图像在 `b_reference/`，旧A版本仍保存在 `revisions/a_only/`。服务器无头 Firefox 缺少 GL 上下文时，使用 Xvfb 显示环境：

```sh
.cache/assembly-browser/extracted/usr/bin/Xvfb :95 -screen 0 1600x1200x24 -ac -nolisten tcp
DISPLAY=:95 ASSEMBLY_BROWSER_HEADED=1 .venv-review/bin/python scripts/check_assembly_3d_browser.py
```

页面渲染在访问者浏览器执行，不调用 VLM，也不占用服务器推理卡；7863 QA 审核和审核数据保持独立。

## 完整原视频

[完整安装视频页](http://10.112.70.171:7864/videos.html)提供A/B原片、安装阶段和原异常标注定位。`scripts/select_complete_assembly_videos.py`扫描55份front安装标注并核对派生ATR；数据、SHA和首尾/阶段抽帧存于`outputs/impact_qa/assembly_3d/complete_videos/`。选中原MP4通过media下两个明确软链接提供，无重编码、无剪接。Starlette静态服务支持HTTP Range定位，继续使用7864。
