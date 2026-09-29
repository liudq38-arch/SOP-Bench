# 审核界面唯一入口

当前地址：http://10.112.70.171:7863

默认展示连续2秒视频＋history结果。其他标签页为事件QA对照、逐帧描述、ATR双视角、早期生成。全部页面由同一Gradio进程服务，原各轮数据和审核记录保留。

启动命令：`.venv-review/bin/python -u scripts/serve_unified_review.py`。

7860、7861、7862、7864已关闭。旧实验报告中的地址是历史记录，当前统一使用7863。旧审核脚本直接启动也进入同一统一服务。后续更新此页面，不再新增审核端口。内部模型推理服务不属于审核前端。

验证记录：outputs/impact_qa/unified_review_check.json。界面修改没有重新生成QA。
